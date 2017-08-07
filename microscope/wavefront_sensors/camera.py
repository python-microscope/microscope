# This is Eric Branlund's code for the Zyla camera

import memhandler
import neo

import numpy
import numpy.ctypeslib
import Pyro4

import ctypes
import gc
import Queue
import threading
import time
import traceback

## Needed to keep the daemon from only listening to requests originating
# from the local host.
MY_IP_ADDRESS = '10.0.0.2'

## Cropping modes
(CROP_FULL, CROP_HALF, CROP_512, CROP_256, CROP_128) = range(5)

## Trigger modes
(TRIGGER_INTERNAL, TRIGGER_EXTERNAL, TRIGGER_EXTERNAL_EXPOSURE) = range(3)

STATIC_BLACK = numpy.zeros((512, 512), dtype = numpy.uint16)

## Save an array as an image. Copied from 
# http://stackoverflow.com/questions/902761/saving-a-numpy-array-as-an-image
# Mostly this just makes it easier to view images for debugging. The image
# uses false color and thus isn't really useful for actual work.
def imsave(filename, array, vmin=None, vmax=None, cmap=None,
           format=None, origin=None):
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure

    fig = Figure(figsize=array.shape[::-1], dpi=1, frameon=False)
    canvas = FigureCanvas(fig)
    fig.figimage(array, cmap=cmap, vmin=vmin, vmax=vmax, origin=origin)
    fig.savefig(filename, dpi=1, format=format)


## Because all functions in the neo module a) accept a camera handle as a
# first argument, and b) return an error code as the primary return value,
# we make this wrapper around the entire library to make interacting with
# it cleaner. It initializes the library, connects to the camera, and
# wraps every API function to handle error conditions.
# We also handle a couple of other functions through the memhandler.dll
# library via ctypes. They behave broadly similarly. 
class WrappedAndor:
    def __init__(self):
        self.errorCodes = dict()
        for key, value in neo.__dict__.iteritems():
            if callable(value):
                self.__dict__[key] = self.wrapFunction(value)
            # Also capture the error codes at this time so we can
            # provide their names instead of bare numbers.
            elif 'AT_ERR' == key[:6] or 'ERR_' == key[:4]:
                self.errorCodes[value] = key

        ## Loaded object for memhandler.dll.
        self.memLib = self.initMemhandler()

        startTime = time.time()
        print "Initializing Andor library...",
        error = neo.AT_InitialiseLibrary()
        if error:
            raise RuntimeException("Failed to initialize Andor library: %s" % self.errorCodes[error])
        print "done in %.2f seconds" % (time.time() - startTime)
        error, numDevices = neo.AT_GetInt(neo.AT_HANDLE_SYSTEM, "DeviceCount")
        if error:
            raise RuntimeError("Failed to get number of devices: %s" % self.errorCodes[error])
        print "There are %d connected devices" % numDevices
        error, self.handle = neo.AT_Open(0)
        if error:
            raise RuntimeError("Failed to connect to camera: %s" % self.errorCodes[error])
        elif self.handle == -1:
            raise RuntimeError("Got an invalid handle from the camera")
        else:
            print "Connected to camera with handle",self.handle


    ## Clean up after ourselves.
    def __del__(self):
        print "Close:",neo.AT_Close(self.handle)
        print "Finalize:",neo.AT_FinaliseLibrary()


    ## For the high-throughput functions AT_QueueBuffer and AT_WaitBuffer, we use
    # ctypes instead of SWIG, in an attempt to avoid weird throughput issues we
    # have otherwise. 
    def initMemhandler(self):
        memLib = ctypes.CDLL('memhandler.dll')
        # Args are handle, numBuffers, numElements
        memLib.allocMemory.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_int)
        # Returns an error code.
        memLib.allocMemory.restype = ctypes.c_int
        # Construct the return type that's a point to a buffer of memory.
        bufType = numpy.ctypeslib.ndpointer(dtype = numpy.uint16, ndim = 1,
                flags = ('C_CONTIGUOUS', 'ALIGNED', 'WRITEABLE'))
        # Args are output buffer, timeout
        memLib.getImage.argtypes = (bufType, ctypes.c_int, ctypes.c_double)
        # Returns an error code.
        memLib.getImage.restype = ctypes.c_int
        return memLib


    ## Manual wrapper around the memhandler.allocMemory() function.
    def allocMemory(self, numBuffers, numElements):
        return self.processReturn(self.memLib.allocMemory(
                self.handle, numBuffers, numElements))


    ## Manual wrapper around the memhandler.getImage() function.
    def getImage(self, numElements, timeout):
        imageBuffer = numpy.ndarray(numElements, dtype = numpy.uint16,
                order = 'C')
        # Multiply by 2 because there's 2 bytes per uint16.
        error = self.memLib.getImage(imageBuffer, numElements * 2, .5)
        if error:
            raise RuntimeError("getImage failed")
        return imageBuffer


    ## Manual decorator function -- call the passed-in function with our
    # handle, and raise an exception if an error occurs.
    def wrapFunction(self, func):
        def wrappedFunction(*args, **kwargs):
            result = func(self.handle, *args, **kwargs)
            return self.processReturn(result)
        return wrappedFunction


    ## Handle function return values.
    # result may be a single value, a length-2 list, or a
    # length-3+ list. We return None, the second value, or
    # a tuple in those respective cases.
    def processReturn(self, result):
        errorCode = result
        returnVal = None
        if type(result) in [tuple, list]: # Type paranoia
            errorCode = result[0]
            if len(result) == 2:
                returnVal = result[1]
            else:
                returnVal = tuple(result[1:])
        if errorCode:
            errorString = "unknown error %s" % errorCode
            if errorCode in self.errorCodes:
                errorString = "error %s" % self.errorCodes[errorCode]
            raise RuntimeError("An %s occurred." % errorString)
        return returnVal



wrappedAndor = WrappedAndor()




## Decorator function to put the camera in a mode where it can be
# interacted with. Mostly needed to stop acquisitions.
def resetCam(func):
    def wrappedFunc(*args, **kwargs):
        if wrappedAndor.AT_GetBool('CameraAcquiring'):
            wrappedAndor.AT_Command('AcquisitionStop')
        wrappedAndor.AT_SetEnumString('TriggerMode', 'Internal')
        wrappedAndor.AT_SetEnumString('CycleMode', 'Fixed')
        wrappedAndor.AT_SetInt('FrameCount', 1)
        func(*args, **kwargs)
    return wrappedFunc


## This class exposes various Andor library functions to outside clients,
# and handles collecting and transferring data.
class Camera:
    def __init__(self):
        ## Cached copy of the sensor width, since we need to access this
        # regularly.
        self.width = wrappedAndor.AT_GetInt('SensorWidth')
        ## See self.width.
        self.height = wrappedAndor.AT_GetInt('SensorHeight')
        ## Current crop mode (e.g. CROP_FULL, CROP_512, etc.)
        self.curCropMode = CROP_FULL
        
        print "Firmware version:",wrappedAndor.AT_GetString('FirmwareVersion')
        print "Camera serial number:",wrappedAndor.AT_GetString('SerialNumber')
        print "CCD sensor shape:",self.width,self.height
        print "Bit depth:",wrappedAndor.AT_GetEnumIndex('BitDepth')
        print "Pixel encoding:",wrappedAndor.AT_GetEnumIndex('PixelEncoding')
        print "Shutter mode:",wrappedAndor.AT_GetEnumIndex('ElectronicShutteringMode')
        print "Fan speed:",wrappedAndor.AT_GetEnumIndex('FanSpeed')
        print "Sensor cooling:",wrappedAndor.AT_GetBool('SensorCooling')
        print "Temp status:",wrappedAndor.AT_GetEnumIndex('TemperatureStatus')
        print "Sensor temperature",self.getSensorTemperature()
        print "Baseline level:",wrappedAndor.AT_GetInt('BaselineLevel')

        wrappedAndor.AT_SetEnumString("FanSpeed", "Off")
        wrappedAndor.AT_SetBool("SensorCooling", True)
        print "Pre-amp gain options:"
        for i in xrange(wrappedAndor.AT_GetEnumCount("SimplePreAmpGainControl")):
            print "%d:" % i, wrappedAndor.AT_GetEnumStringByIndex("SimplePreAmpGainControl", i)
        wrappedAndor.AT_SetEnumString("SimplePreAmpGainControl", "16-bit (low noise & high well capacity)")
        wrappedAndor.AT_SetEnumString("PixelReadoutRate", "280 MHz")

        self.setExposureTime(.1)

        self.dataThread = DataThread(self, self.width, self.height)

        self.setCrop(CROP_512)
        self.setShutterMode(True)
        self.dataThread.start()


    ## Get told who we should be sending image data to, and how we
    # should mark ourselves when we do.
    def receiveClient(self, uri):
        print "Receiving new client",uri
        if uri is None:
            self.dataThread.setClient(None)
            self.dataThread.shouldSendImages = False
        else:
            connection = Pyro4.Proxy(uri)
            connection._pyroTimeout = 5
            self.dataThread.setClient(connection)
            self.dataThread.shouldSendImages = True


    ## Stop sending images to the client, even if we still
    # receive them.
    def goSilent(self):
        print "Switching to quiet mode"
        self.dataThread.shouldSendImages = False


    ## Start sending new images to the client again.
    def goLoud(self):
        print "Switching to loud mode"
        self.dataThread.shouldSendImages = True


    ## Stop acquiring images.
    def abort(self):
        wrappedAndor.AT_Command("AcquisitionStop")


    ## Retrieve the specified number of images. This may fail
    # if we ask for more images than we have, so the caller
    # should be prepared to catch exceptions.
    def getImages(self, numImages):
        result = []
        for i in xrange(numImages):
            image = self.extractOneImage()
            result.append(image)
        return result


    ## Discard the specified number of images from the queue,
    # defaulting to all of them.
    def discardImages(self, numImages = None):
        count = 0
        while count != numImages:
            try:
                self.extractOneImage()
                count += 1
            except Exception, e:
                # Got an exception, probably because the
                # queue is empty, so we're all done here.
                return


    ## Set the exposure time, in seconds.
    @resetCam
    def setExposureTime(self, seconds = .01):
        print "Set exposure time to", seconds, "seconds"
        wrappedAndor.AT_SetFloat('ExposureTime', seconds)


    ## Simple getter.
    def getExposureTime(self):
        return wrappedAndor.AT_GetFloat('ExposureTime')


    ## Set the cropping mode to one of a few presets. In version
    # 2 of the SDK, these were the only valid crop modes; in
    # version 3, we can set any crop mode we want, but these
    # presets are still convenient.
    def setCrop(self, mode):
        self.curCropMode = mode
        width = [2560, 1392, 540, 240, 144][mode]
        left = [1, 601, 1033, 1177, 1225][mode]
        height = [2160, 1040, 512, 256, 128][mode]
        top = [1, 561, 825, 953, 1017][mode]
        self.setCropArbitrary(left, top, width, height)


    ## Get the current crop mode.
    def getCropMode(self):
        return self.curCropMode


    ## Set our cropping to an arbitrary region of interest.
    def setCropArbitrary(self, left, top, width, height):
        wrappedAndor.AT_SetInt('AOIWidth', width)
        wrappedAndor.AT_SetInt('AOILeft', left)
        wrappedAndor.AT_SetInt('AOIHeight', height)
        wrappedAndor.AT_SetInt('AOITop', top)
        
        self.width = width
        self.height = height
        self.dataThread.setImageDimensions(width, height)

        # Reset the memory used to transfer images from the camera.
        # We allocate about 500MB of RAM to the image buffer. Allocating
        # too much memory seems to cause slowdowns and crashes, oddly enough.
        imageBytes = wrappedAndor.AT_GetInt('ImageSizeBytes')
        numImages = (500 * 1024 * 1024) / imageBytes
        print "Allocating",numImages,"images at",imageBytes,"bytes per image"
        wrappedAndor.allocMemory(numImages, imageBytes)
        
        stride = wrappedAndor.AT_GetInt('AOIStride')
        div = float(stride) / width
        print "Got stride",stride,"compare",width,"giving div",div
        return (stride, width, int(div) == div)


    ## Set an offset correction image to use.
    def setOffsetCorrection(self, image):
        self.dataThread.setOffsetCorrection(image)


    ## Return true if a correction file is loaded
    # for the current image dimensions.
    def getIsOffsetCorrectionOn(self):
        correction = self.dataThread.getOffsetCorrection()
        return correction is not None and correction.shape == (self.height, self.width)


    ## Retrieve the current sensor temperature in degrees Celsius.
    def getSensorTemperature(self):
        return wrappedAndor.AT_GetFloat('SensorTemperature')


    ## Get the shape of the images we generate
    def getImageShape(self):
        return (self.width, self.height)


    ## Set the trigger mode. 
    @resetCam
    def setTrigger(self, triggerMode):
        wrappedAndor.AT_SetEnumString('CycleMode', 'Continuous')
        modeString = ''
        if triggerMode == TRIGGER_INTERNAL:
            wrappedAndor.AT_SetEnumString('TriggerMode', 'Internal')
            modeString = 'internal trigger'
        elif triggerMode == TRIGGER_EXTERNAL:
            wrappedAndor.AT_SetEnumString('TriggerMode', 'External')
            wrappedAndor.AT_Command('AcquisitionStart')
            modeString = 'external trigger'
        elif triggerMode == TRIGGER_EXTERNAL_EXPOSURE:
            wrappedAndor.AT_SetEnumString('TriggerMode', 'External Exposure')
            wrappedAndor.AT_Command('AcquisitionStart')
            modeString = 'external exposure'
        print "Set trigger mode to",modeString


    ## Set the shutter mode.
    def setShutterMode(self, isGlobal):
        # 0 is rolling shutter; 1 is global.
        wrappedAndor.AT_SetEnumIndex('ElectronicShutteringMode', int(isGlobal))


    ## Get the current shutter mode.
    def getIsShutterModeGlobal(self):
        return wrappedAndor.AT_GetEnumIndex('ElectronicShutteringMode') == 1


    ## Get the time needed to read out the image.
    def getReadoutTime(self):
        return wrappedAndor.AT_GetFloat('ReadoutTime')


    ## Below this point lie debugging functions.

    
    ## Acquire some number of images with internal trigger.
    def triggerInternally(self, imageCount, exposureTime):
        wrappedAndor.AT_Command('AcquisitionStop')
        print "Acquiring %d images with exposure time %d" % (imageCount, exposureTime)
        wrappedAndor.AT_SetEnumString('TriggerMode', 'Internal')
        wrappedAndor.AT_SetEnumString('CycleMode', 'Fixed')
        wrappedAndor.AT_SetInt('FrameCount', imageCount)
        wrappedAndor.AT_SetFloat('ExposureTime', exposureTime / 1000.0)
        # Hardcoded for now.
        wrappedAndor.AT_SetFloat('FrameRate', 125)
        wrappedAndor.AT_Command("AcquisitionStart")


    ## Generate synthetic images at the specified framerate (in FPS).
    def generateSequence(self, imageCount, frameRate):
        threading.Thread(target = self.generateSequence2, args = [imageCount, frameRate]).start()


    ## As above, but in a new thread.
    def generateSequence2(self, imageCount, frameRate):
        waitTime = 1 / float(frameRate)
        image = numpy.zeros((self.width, self.height), dtype = numpy.uint16)
        for i in xrange(imageCount):
            curTime = time.clock()
            self.dataThread.imageQueue.put((image, curTime))
            nextTime = time.clock()
            putDelta = nextTime - curTime
            if putDelta > waitTime * 1.25:
                print "Putting is slow!",putDelta,waitTime
            time.sleep(waitTime)
            finalTime = time.clock()
            if finalTime - nextTime > max(.02, waitTime * 1.25):
                print "Sleeping is slow!",(finalTime - nextTime), waitTime


    ## Set the gain mode as an index into the enums. Again, you generally
    # shouldn't need to call this from outside.
    def setGainEnum(self, val):
        wrappedAndor.AT_SetEnumIndex('SimplePreAmpGainControl', val)


    ## Set the readout rate as an index into the enums. Also for debugging.
    def setReadoutEnum(self, val):
        wrappedAndor.AT_SetEnumIndex('PixelReadoutRate', val)


    ## Set the frame count to a different value and go into external
    # trigger mode. Just for debugging.
    def setFrameCount(self, val):
        if wrappedAndor.AT_GetBool('CameraAcquiring'):
            wrappedAndor.AT_Command('AcquisitionStop')
        wrappedAndor.AT_SetEnumString('TriggerMode', 'Internal')
        wrappedAndor.AT_SetEnumString('CycleMode', 'Fixed')
        wrappedAndor.AT_SetInt('FrameCount', val)
        wrappedAndor.AT_SetEnumString('TriggerMode', 'External')
        wrappedAndor.AT_SetEnumString('CycleMode', 'Continuous')
        wrappedAndor.AT_Command('AcquisitionStart')



## This class retrieves images from the camera, and sends them to our
# client. 
class DataThread(threading.Thread):
    def __init__(self, parent, width, height):
        threading.Thread.__init__(self)

        ## Loop back to parent to be able to communicate with it.
        self.parent = parent

        ## Image dimensions, which we need for when we retrieve image
        # data. Our parent is responsible for updating these for us
        # via setImageDimensions().
        self.width = self.height = 0
        ## Lock on modifying the above.
        self.sensorLock = threading.Lock()

        ## Connection to client
        self.clientConnection = None

        ## Whether or not we should unload images from the camera
        self.shouldSendImages = True

        ## Initial timestamp that we will use in conjunction with time.clock()
        # to generate high-time-resolution timestamps. Just using time.time()
        # straight-up on Windows only has accuracy of ~15ms.
        self.initialTimestamp = time.time() + time.clock()

        ## Offset image array to subtract off of each image we
        # receive.
        self.offsetImage = None


    ## Pull images from self.imageQueue and send them to the client.   
    def run(self):
        count = 0
        gTime = None
        getTime = 0
        fixTime = 0
        sendTime = 0
        while True:
            # This will block indefinitely until images are available.
            with self.sensorLock:
                try:
                    start = time.clock()
                    image = wrappedAndor.getImage(self.width * self.height, .5)
                    getTime += (time.clock() - start)
                except Exception, e:
                    if 'getImage failed' not in e:
                        print "Error in getImage:",e
                    # Probably a timeout; just try again.
                    continue
            # \todo This timestamp is potentially bogus if we get behind in
            # processing images.
            timestamp = time.clock() + self.initialTimestamp
#            print "Image has shape",image.shape,"min/max",image.min(),image.max()
            start = time.clock()
            image = self.fixImage(image)
            fixTime += time.clock() - start
            count += 1
            if count % 100 == 0:
                # Periodically manually invoke the garbage collector, to
                # ensure that we don't build up a giant pile of work that
                # would interfere with our average write speed.
                if gTime is None:
                    gTime = time.time()
                delta = time.time() - gTime
                print count, delta, getTime, fixTime, sendTime
                gTime = time.time()
                getTime = fixTime = sendTime = 0
                gc.collect()

            if self.shouldSendImages and self.clientConnection is not None:
                try:
                    start = time.clock()
                    self.clientConnection.receiveData('new image', image, timestamp)
                    cost = time.clock() - start
                    if cost > .5:
                        print "Took %.2fs to send to client" % cost
                    sendTime += cost
                except Exception, e:
                    print "Failed to send image to client: %s", e
                    traceback.print_exc()


    ## Fix an image -- set its shape and apply any relevant correction.
    def fixImage(self, image):
        image.shape = self.height, self.width
        if self.offsetImage is not None and self.offsetImage.shape == image.shape:
            # Apply offset correction.
            image -= self.offsetImage
        return image


    ## Update who we send image data to.
    def setClient(self, connection):
        self.clientConnection = connection


    ## Update our image dimensions.
    def setImageDimensions(self, width, height):
        with self.sensorLock:
            self.width = width
            self.height = height


    ## Update the image we use for offset correction.
    def setOffsetCorrection(self, image):
        self.offsetImage = image


    ## Retrieve our offset correction image.
    def getOffsetCorrection(self):
        return self.offsetImage

        

try:
    cam = Camera()
    daemon = Pyro4.Daemon(port = 7000, host = MY_IP_ADDRESS)
    Pyro4.Daemon.serveSimple(
        {
            cam: 'Andorcam',
        },
        daemon = daemon, ns = False, verbose = True
    )
    
except Exception, e:
    traceback.print_exc()

del wrappedAndor # Clean up after ourselves.
