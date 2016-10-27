#!/usr/bin/python
"""Config file for devicebase.

Import device classes, then define entries in DEVICES as:
   devices(CLASS, HOST, PORT, other_args)
"""
# Function to create record for each device.
from microscope.devices import device
# Import device modules/classes here.
from microscope.cameras import testcamera

DEVICES = [
  device(testcamera.TestCamera, '127.0.0.1', 8001, otherargs=1,),
]
