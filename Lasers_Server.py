"""Config file for devicebase.

Import device classes, then define entries in DEVICES as:
 devices(CLASS, HOST, PORT, other_args)
"""
## Function to create record for each device.
from microscope.devices import device
## Import device modules/classes here.
from microscope.lights.deepstar import DeepstarLaser
# from microscope.lasers.deepstar import DeepstarLaser
from microscope.lasers.obis import ObisLaser

DEVICES = [
           device(DeepstarLaser, '10.6.19.21', 9011, conf={'com': 'COM9', 'baud': 9600, 'timeout': 0.5}),  # Deepstar 488
           # device(ObisLaser, '10.6.19.21', 9012, conf={'com': 'COM6', 'baud': 115200, 'timeout': 2.0}),  # Obis 561
           # device(ObisLaser, '10.6.19.21', 9013, conf={'com': 'COM7', 'baud': 115200, 'timeout': 2.0}),  # Obis 642
           ]
