#!/usr/bin/python
"""Config file for devicebase.

Import device classes, then define entries in DEVICES as:
   devices(CLASS, HOST, PORT, other_args)
"""
# Function to create record for each device.
from devicebase import device
# Import device modules/classes here.
import devicebase

DEVICES = [
	device(devicebase.Device, '127.0.0.1', 8000),
	device(devicebase.Device, '127.0.0.1', 8001, com=6, baud=115200),
	device(devicebase.FloatingDevice, '127.0.0.1', 8002, uid=None),
]
