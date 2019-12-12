#!/usr/bin/python
"""Win32 specific microscope classes.
"""
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

class MicroscopeWindowsService(win32serviceutil.ServiceFramework):
    """ Serves microscope devices via a Windows service.

    Win32 service manipulation relies on fetching _svc_name_ without
    instantiating any object, so _svc_name_ must be a class
    attribute. This means that only one MicroscopeService may be
    installed on any one system, and will be responsible for serving
    all microscope devices on that system.
    """
    _svc_name_ = 'MicroscopeService'
    _svc_display_name_ = 'Microscope device servers'
    _svc_description_ = 'Serves microscope devices.'

    @classmethod
    def set_config_file(cls, path):
        win32serviceutil.SetServiceCustomOption(cls._svc_name_,
                                                'config',
                                                os.path.abspath(path))

    @classmethod
    def get_config_file(cls):
        return win32serviceutil.GetServiceCustomOption(cls._svc_name_, 'config')


    def log(self, message, error=False):
        if error:
            logFunc = servicemanager.LogErrorMsg
        else:
            logFunc = servicemanager.LogInfoMsg
        logFunc("%s: %s" % (self._svc_name_, message))


    def __init__(self, args):
        # Initialise service framework.
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = multiprocessing.Event()


    def SvcDoRun(self):
        configfile = win32serviceutil.GetServiceCustomOption(self._svc_name_, 'config')
        os.chdir(os.path.dirname(configfile))
        self.log("Using config file %s." % configfile)
        self.log("Logging at %s." % os.getcwd())
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        from microscope.deviceserver import serve_devices, validate_devices
        try:
            devices = validate_devices(configfile)
            serve_devices(devices, self.stop_event)
        except Exception as e:
            servicemanager.LogErrorMsg(str(e))
            # Exit with non-zero error code so Windows will attempt to restart.
            sys.exit(-1)
        self.log('Service shutdown complete.')
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_event.set()


def handle_command_line():
    if len(sys.argv) == 1:
        print("\nNo action specified.\n", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1].lower() in ['install', 'update']:
        if len(sys.argv) == 2:
            print("\nNo config file specified.\n")
            sys.exit(1)
        configfile = sys.argv.pop()
        win32serviceutil.HandleCommandLine(MicroscopeWindowsService)
        # Set persistent data on service
        MicroscopeWindowsService.set_config_file(configfile)
    else:
        win32serviceutil.HandleCommandLine(MicroscopeWindowsService)
