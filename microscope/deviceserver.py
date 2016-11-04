#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""A class for serving microscope components.

This module provides a server to make microscope control objects available
over Pyro. When called from the command line, this module will serve devices
defined in a specified config file, any 'config.py' found at the current
working directory, or default test objects found in microscope.config.
"""

import imp
import importlib
import logging
import multiprocessing
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler
from threading import Thread

import Pyro4
from future.utils import iteritems

from microscope.devices import FloatingDeviceMixin

# Pyro configuration. Use pickle because it can serialize numpy ndarrays.
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2

# Logging formatter.
LOG_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s PID %(process)s: %(message)s')


class DeviceServer(multiprocessing.Process):
    def __init__(self, device_def, id_to_host, id_to_port, count=0, exit_event=None):
        """Initialise a device and serve at host/port according to its id.

        :param device_def:  definition of the device
        :param id_to_host: host or mapping of device identifiers to hostname
        :param id_to_port: map or mapping of device identifiers to port number
        :param count:       this is the countth process serving this class
        :param exit_event:  a shared event to signal that the process should quit.
        """
        # The device to serve.
        self._device_def = device_def
        self._device = None
        # Where to serve it.
        self._id_to_host = id_to_host
        self._id_to_port = id_to_port
        # A shared event to allow clean shutdown.
        self.exit_event = exit_event
        super(DeviceServer, self).__init__()
        self.daemon = True
        # Some SDKs need an index to access more than one device.
        self.count = count

    def run(self):
        self._device = self._device_def['cls'](index=self.count, **self._device_def)
        while True:
            try:
                self._device.initialize()
            except:
                time.sleep(5)
            else:
                break
        if isinstance(self._device, FloatingDeviceMixin):
            uid = self._device.get_id()
            if uid not in self._id_to_host or uid not in self._id_to_port:
                raise Exception("Host or port not found for device %s" % (uid,))
            host = self._id_to_host[uid]
            port = self._id_to_port[uid]
        else:
            host = self._device_def['host']
            port = self._device_def['port']
        pyro_daemon = Pyro4.Daemon(port=port, host=host)
        log_handler = RotatingFileHandler("%s_%s_%s.log" %
                                          (type(self._device).__name__, host, port))
        log_handler.setFormatter(LOG_FORMATTER)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        if __debug__:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        logger.info('Device initialized; starting daemon.')
        logger.debug('Debugging messages on.')

        # Run the Pyro daemon in a separate thread so that we can do
        # clean shutdown under Windows.
        pyro_thread = Thread(target=Pyro4.Daemon.serveSimple,
                             args=({self._device: type(self).__name__},),
                             kwargs={'daemon': pyro_daemon, 'ns': False})
        pyro_thread.daemon = True
        pyro_thread.start()
        if self.exit_event:
            # This tread waits for the termination event.
            try:
                self.exit_event.wait()
            except:
                pass
            pyro_daemon.shutdown()
            pyro_thread.join()
            # Termination condition triggered.
        else:
            # This is the main process. Sleep until interrupt.
            pyro_thread.join()
        self._device.shutdown()


def __main__():
    # An event to trigger clean termination of subprocesses. This is the
    # only way to ensure devices are shut down properly when processes
    # exit, as __del__ is not necessarily called when the interpreter exits.
    exit_event = multiprocessing.Event()

    def term_func(sig, frame):
        """Terminate subprocesses cleanly."""
        exit_event.set()
        for this_server in servers:
            this_server.join()
        sys.exit()

    signal.signal(signal.SIGTERM, term_func)
    signal.signal(signal.SIGINT, term_func)

    config_file = None

    if len(sys.argv) == 1:
        # No config file specified. Check cwd.
        if os.path.isfile('config.py'):
            config_file = 'config.py'
    else:
        # Config file specified.
        config_file = sys.argv[1]

    if config_file is not None:
        with open(config_file) as fh:
            config = imp.load_module('config', fh, config_file, ('py', 'r', imp.PY_SOURCE))
    else:
        # Fall back to default test config.
        import microscope.config as config

    # Group devices by class.
    by_class = {}
    for dev in config.DEVICES:
        by_class[dev['cls']] = by_class.get(dev['cls'], []) + [dev]

    servers = []
    for cls, devs in iteritems(by_class):
        # Keep track of how many of these classes we have set up.
        # Some SDKs need this information to index devices.
        count = 0
        if issubclass(cls, FloatingDeviceMixin):
            # Need to provide maps of uid to host and port.
            uid_to_host = {}
            uid_to_port = {}
            for dev in devs:
                uid = dev['uid']
                uid_to_host[uid] = dev['host']
                uid_to_port[uid] = dev['port']
        else:
            uid_to_host = None
            uid_to_port = None

        for dev in devs:
            servers.append(DeviceServer(dev,
                                        uid_to_host, uid_to_port,
                                        exit_event=exit_event, count=count))
            servers[-1].start()
            count += 1
    for s in servers:
        s.join()


if __name__ == '__main__':
    """Serve devices via Pyro.

    Usage:  deviceserver [config]
    """

    __main__()
