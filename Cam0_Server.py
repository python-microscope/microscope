"""Configuration file for deviceserver.
"""

from microscope.devices import device

# Import required device classes
from microscope.cameras.andorsdk3 import AndorSDK3


# host is the IP address (or hostname) from where the device will be
# accessible.  If everything is on the same computer, then host will
# be '127.0.0.1'.  If devices are to be available on the network,
# then it will be the IP address on that network.
host = '10.6.19.30'

# Each element in the DEVICES list identifies a device that will be
# served on the network.  Each device is defined like so:
#
# device(cls, host, port, conf)
#     cls: class of the device that will be served
#     host: ip or hostname where the device will be accessible.
#         This will be the same value for all devices.
#     port: port number where the device will be accessible.
#         Each device must have its own port.
#     conf: a dict with the arguments to construct the device
#         instance.  See the individual class documentation.
#

DEVICES = [
    device(AndorSDK3, host, 8001, uid="VSC-01604")  # {'transform': (0, 1, 1)}),  # timeout=1, buffer_length=, index=0,
    # device(TestCamera, host, 8005, otherargs=1,),
    # device(TestCamera, host, 8006, otherargs=1,),
    ]
