#!/usr/bin/python
"""Example to serve devices from a Windows service..

Import device classes, then define entries in DEVICES as:
   devices(CLASS, HOST, PORT, other_args)

The folder containing the python.exe to use must be added
to the system's PATH variable.
"""
# Function to create record for each device.
from microscope.devices import device

# Import device modules/classes here.
import microscope.testsuite.devices as testdevices

DEVICES = [
    device(testdevices.TestCamera, '127.0.0.1', 8000,),
    device(testdevices.TestCamera, '127.0.0.1', 8001, com=6, baud=115200),
    device(testdevices.TestLaser, '127.0.0.1', 8002),
    device(testdevices.TestLaser, '127.0.0.1', 8003),
    device(testdevices.TestFilterWheel, '127.0.0.1', 8004),
    device(testdevices.DummyDSP, '127.0.0.1', 8005),    
    device(testdevices.DummySLM, '127.0.0.1', 8006),
]

import os
import sys

try:
    import win32api
except:
    # Add executable path to DLL search PATH.
    os.environ['PATH'] += ';' + os.path.split(sys.executable)[0]
    import win32api

import multiprocessing
import servicemanager
import win32api
import win32event
from win32process import DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP, CREATE_NEW_CONSOLE
import win32serviceutil
import win32service

# We need the full path to this file in order to chdir to put log files
# where they can be found.
# config files in the same folder when invoked as a service.
PATH = os.path.dirname(os.path.abspath(__file__))


class MicroscopeWindowsService(win32serviceutil.ServiceFramework):
    """ Serves microscope devices via a Windows service.

    """
    _svc_name_ = 'MicroscopeService'
    _svc_display_name_ = 'Microscope device servers'
    _svc_description_ = 'Serves microscope devices.'


    def log(self, message, error=False):
        if error:
            logFunc = servicemanager.LogErrorMsg
        else:
            logFunc = servicemanager.LogInfoMsg
        logFunc("%s: %s" % (self._svc_name_, message))


    def __init__(self, args):
        # Initialise service framework.
        self.log('__init__')
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = multiprocessing.Event()


    def SvcDoRun(self):
        os.chdir(PATH)
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.log("Logging at %s." % PATH)
        from microscope.deviceserver import serve_devices
        try:
            serve_devices(DEVICES, self.stop_event)
        except Exception as e:
            servicemanager.LogErrorMsg(e)
            # Exit with non-zero error code so Windows will attempt to restart.
            sys.exit(-1)
        self.log('%s.server shutdown complete.')
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_event.set()


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(MicroscopeWindowsService)