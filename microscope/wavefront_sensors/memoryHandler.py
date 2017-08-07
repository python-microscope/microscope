'''
This program is intended to provide a pure-C "client" for interacting with
the camera, for use in debugging issues we've been having with running
long, high-speed acquisitions. It's basically a copy of the memhandler
code with some preambles and code to actually deal with the image data. 
'''

import AndorSDK3 as SDK3
import threading
import Queue
import numpy as np
import ctypes
from time import sleep
from numpy import dtype

class MemoryHandler():
    '''
    MemoryHandler doc
    '''
    def __init__(self, handle):
        self.handle = handle
        self.buffersQueue = Queue.Queue() # Queue of buffers where images will be stored
        self.imageBytes = 0 # Number of bytes used by one image
        self.imagesQueue = Queue.Queue() # Queue of images waiting to be consumed
        self.imageQueueLock = threading.Lock() # a lock for the image queue
        self.readThread = threading.Thread() # initialize an empty thread. This one will be replaced as soon as first memory is allocated
        self.readThreadLock = threading.Lock() # a lock for the readThread
        self.shouldReadImages = False
        
    def stop(self):
        '''
        Stops any active threads
        '''
        # Halt any active read thread
        if self.readThread.isAlive():
            with self.readThreadLock:
                self.shouldReadImages = False
            self.readThread.join()

        # Wipe the list of images waiting to be read out
        with self.imageQueueLock:
            while not self.imagesQueue.empty():
                self.imagesQueue.get()

        # Flush the camera buffer and wipe the buffersQueue, if it exists
        if not self.buffersQueue.empty():
            try:
                SDK3.Flush(self.handle)
            except SDK3.CameraError as e:
                print(e)
                return 1
            while not self.buffersQueue.empty():
                self.buffersQueue.get()
        

    def allocMemory(self, numBuffers, imageBytes, imageWidth, imageHeight, strides, timeout, dtype = '<u2'):
        '''
        Clear the current array of memory and allocate a new one. Kill off the 
        old image-retrieval thread. Empty the imageQueue. Spawn a new thread to 
        replace the old one. We do this as the image size may have changed, which
        makes the old readImages() function invalid.
        '''
        # Stop the thread
        self.stop()
        
        # Correct imageBytes size to match the datatype
        if dtype == '<u2':
            imageShape = (imageHeight, (strides/2))
        
        # Recreate the buffer
        for i in range(numBuffers):
            imageArray = np.zeros(imageShape, dtype='<u2', order='C')
#             imageArray = np.ndarray(shape= imageShape,
#                                     dtype= '<u2',
#                                     order= 'C')
            # We rather do this than creating the array using zeros.
            # Time is consumed at memory allocation but faster when recovering the images.
            imageArray.fill(0)
            self.buffersQueue.put(imageArray)
            try:
                SDK3.QueueBuffer(self.handle, imageArray.ctypes.data_as(SDK3.POINTER(SDK3.AT_U8)), imageBytes)
            except SDK3.CameraError as e:
                print('ERROR: Cannot queue buffers')
                print(e)

        # Starts the image polling thread
        self.shouldReadImages = True
        # a thread that is reading the images out of the buffers
        self.readThread = threading.Thread(target = self.readImages, 
                                           args = (imageWidth, 
                                                   imageHeight,
                                                   strides, 
                                                   imageBytes, 
                                                   timeout))
        self.readThread.start()


    def getUpdatedMemory(self, imageWidth, imageHeight, strides, imageBytes, timeout):
        '''Wraps around AT_WaitBuffer. Retrieve a buffer of image data from Andor,
        then copy it to the provided buffer. The buffer from Andor consists of 
        either 11-bit or 16-bit pixels (in the 11-bit case, padded
        to 12 bits with a 0).
        Once we've copied the data out to outputBuffer, we re-zero the buffer
        that Andor wrote to, and then enqueue it so it can be re-used.
        '''
        try:
            bufferLocation, bufferLength = SDK3.WaitBuffer(self.handle, timeout)
        except SDK3.TimeoutError as e:
            # Both AT_ERR_TIMEDOUT and AT_ERR_NODATA get caught as TimeoutErrors
            if e.errNo == SDK3.AT_ERR_TIMEDOUT:
                pass
            return
        except SDK3.CameraError as e:
            print(e)
            if not e.errNo == SDK3.AT_ERR_NODATA:
                print('No data error') # TODO: add up log error report
                pass
            return
        
        # Get next element in the bufferQueue an verify that is the same as the one gotten by WaitBuffer
        newImage = self.buffersQueue.get()
        if bufferLocation and not newImage.ctypes.data == ctypes.addressof(bufferLocation.contents):
            # Buffers are not the same. Raise error
            # TODO: add a clear buffers
            raise RuntimeError('Returned buffer not equal to expected buffer')
        else: 
            # Buffers are correct
            # Copy the np Array into a fresh array that will be returned
            imageArray = np.copy(newImage[:imageHeight,:imageWidth])
            
            # Re-zero data in the buffer
            newImage.fill(0)
            
            # requeue the image
            self.buffersQueue.put(newImage)
            
            # requeue to andors buffer
            SDK3.QueueBuffer(self.handle, 
                             newImage.ctypes.data_as(SDK3.POINTER(SDK3.AT_U8)), 
                             imageBytes)
        
        return imageArray


    def readImages(self, imageWidth, imageHeight, strides, imageBytes, timeout):
        '''
        This function is intended to be created in a separate thread. It continually
        calls getUpdatedMemory and sticks the results (if any) into imageQueue.
        '''
        while self.shouldReadImages:
            newImage = self.getUpdatedMemory(imageWidth = imageWidth, 
                                             imageHeight = imageHeight,
                                             strides = strides, 
                                             imageBytes = imageBytes, 
                                             timeout = timeout)
            
            if newImage is not None:
                self.imagesQueue.put(newImage)
            
            
    def canRead(self):
        with self.readThreadLock:
            return self.shouldReadImages
    
    def getImage(self, timeout):
        '''
        This function consumes an image from imagesQueue and returns it by
        pointer. It blocks indefinitely, until an image is available.
        It is assumed that the provided buffer is big enough to store
        the image into
        '''
        for i in range(100):
            if not self.imagesQueue.empty(): # We have an image. retrieve it.
                return self.imagesQueue.get()
                 
            else: # images queue is empty. Wait and retry
                sleep(timeout / 100) # Try 100 times within the timeout period.
                
        # Timeout was passed. 
            
            
# Run some test code

if __name__ == "__main__":
    pass
