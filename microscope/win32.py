#!/usr/bin/env python3

## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
##
## This file is part of Microscope.
##
## Microscope is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Microscope is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""Win32 specific microscope classes.

If called as a program, it will configure and control a Windows
service to serve devices, similar to the device-server program.

To configure and run as a Windows service use::

    python -m microscope.win32 \
        [install,remove,update,start,stop,restart,status] \
        CONFIG-FILE

"""


import multiprocessing
import os
import sys

import servicemanager


# These win32* modules both import win32api which is a pyd file.
# Importing win32api can be problematic because of Windows things
# specially when running as a Windows.  So if it fails, add the
# executable path to the DLL search PATH.
try:
    import win32service
    import win32serviceutil
except:
    os.environ["PATH"] += ";" + os.path.split(sys.executable)[0]
    import win32service
    import win32serviceutil


class MicroscopeWindowsService(win32serviceutil.ServiceFramework):
    """ Serves microscope devices via a Windows service.

    Win32 service manipulation relies on fetching _svc_name_ without
    instantiating any object, so _svc_name_ must be a class
    attribute. This means that only one MicroscopeService may be
    installed on any one system, and will be responsible for serving
    all microscope devices on that system.
    """

    _svc_name_ = "MicroscopeService"
    _svc_display_name_ = "Microscope device servers"
    _svc_description_ = "Serves microscope devices."

    @classmethod
    def set_config_file(cls, path):
        win32serviceutil.SetServiceCustomOption(
            cls._svc_name_, "config", os.path.abspath(path)
        )

    @classmethod
    def get_config_file(cls):
        return win32serviceutil.GetServiceCustomOption(
            cls._svc_name_, "config"
        )

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
        configfile = win32serviceutil.GetServiceCustomOption(
            self._svc_name_, "config"
        )
        os.chdir(os.path.dirname(configfile))
        self.log("Using config file %s." % configfile)
        self.log("Logging at %s." % os.getcwd())
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        from microscope.device_server import serve_devices, validate_devices

        try:
            devices = validate_devices(configfile)
            serve_devices(devices, self.stop_event)
        except Exception as e:
            servicemanager.LogErrorMsg(str(e))
            # Exit with non-zero error code so Windows will attempt to restart.
            sys.exit(-1)
        self.log("Service shutdown complete.")
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_event.set()


def handle_command_line():
    if len(sys.argv) == 1:
        print("\nNo action specified.\n", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1].lower() in ["install", "update"]:
        if len(sys.argv) == 2:
            print("\nNo config file specified.\n")
            sys.exit(1)
        configfile = sys.argv.pop()
        win32serviceutil.HandleCommandLine(MicroscopeWindowsService)
        # Set persistent data on service
        MicroscopeWindowsService.set_config_file(configfile)
    else:
        win32serviceutil.HandleCommandLine(MicroscopeWindowsService)


if __name__ == "__main__":
    handle_command_line()
