# Simple python script to use Pyth0n-Microscope
# https://github.com/python-microscope/microscope
# to produce a time laspe image series.

# Example code for a time-series experiment with hardware
# triggers.  In the hardware, this experiment requires the camera
# digital output line to be connected to the laser digital input
# line, so that the camera emits a high TTL
# signal while its sensor is being exposed.  In the code, the laser
# is configured as to emit light only while receiving a high TTL
# input signal.  The example triggers the camera a specific number
# times with a time interval between exposures.  The acquired
# images are put in the buffer asynchronously.  The images are taken
# from the queue at the end of the experiment and saved to a file.

import time
from queue import Queue
from microscope import TriggerMode, TriggerType
from microscope.cameras.pvcam import PVCamera
from microscope.lights.toptica import TopticaiBeam
from tifffile import TiffWriter

#set parameters
n_repeats = 10
interval_seconds = 15
exposure_seconds = .5
power_level = .5

#create devices
camera = PVCamera()
laser = TopticaiBeam(port="COM1")

#initialise buffer as a queue
image_buffer = Queue()

#configure camera, pass the buffer queue and enable.
camera.set_client(image_buffer)
camera.exposure_time = exposure_seconds
camera.set_trigger(TriggerType.SOFTWARE, TriggerMode.ONCE)
camera.enable()

#configure laser
laser.power = power_level
laser.set_trigger(TriggerType.HIGH, TriggerMode.BULB)
laser.enable()

#main loop to collect images.
for i in range(n_repeats):
    camera.trigger()
    time.sleep(interval_seconds)

#shutdown hardware devices
laser.shutdown()
camera.shutdown()

#write out image data to a file.
writer = TiffWriter("data.tif")
for i in range(n_repeats):
    writer.save(image_buffer.get())
writer.close()
