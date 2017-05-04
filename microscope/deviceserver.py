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

import collections
import imp # this has been deprecated, we should be using importlib
import logging
import multiprocessing
import signal
import sys
import time
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from threading import Thread

import Pyro4
from six import iteritems

from microscope.devices import FloatingDeviceMixin

# Pyro configuration. Use pickle because it can serialize numpy ndarrays.
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2

# Logging formatter.
LOG_FORMATTER = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:'
                                  'PID %(process)s: %(message)s')

class Filter(logging.Filter):
    def __init__(self):
        self.last = None
        self.count = 1
        self.aggregate_at = 3
        self.repeat_at = 5
        self.stop_at = self.aggregate_at + 3 * self.repeat_at


    def filter(self, record):
        """Pass, aggregate or suppress consecutive repetitions of a log message.
        """
        if self.last == record.msg:
            # Repeated message. Increment count.
            self.count += 1
        else:
            # New message. We've seen 1 instance of it.
            self.count = 1
        # Update self.last - no further reference to last message
        # needed in this call.
        self.last = record.msg
        if self.count < self.aggregate_at:
            return True
        elif self.count == self.aggregate_at:
            record.msg = "Aggregating reps. of: %s" % (record.msg)
            return True
        elif (self.stop_at > self.count > self.aggregate_at
              and ((self.count-self.aggregate_at) % self.repeat_at) == 0):
            record.msg = "%d times: %s" % (self.repeat_at, record.msg)
            return True
        elif self.count == self.stop_at:
            record.msg = "Suppressing reps. of: %s" % (record.msg)
            return True
        else:
            return False


class DeviceServer(multiprocessing.Process):
    def __init__(self, device_def, id_to_host, id_to_port, count=0,
                 exit_event=None):
        """Initialise a device and serve at host/port according to its id.

        :param device_def: definition of the device
        :param id_to_host: host or mapping of device identifiers to hostname
        :param id_to_port: map or mapping of device identifiers to port number
        :param count:      this is the countth process serving this class
        :param exit_event: a shared event to signal that the process
            should quit.
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
        logger = logging.getLogger(self._device_def['cls'].__name__)
        if __debug__:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        # Later, we'll log to one file per server, with a filename
        # based on a unique identifier for the device. Some devices
        # don't have UIDs available until after initialization, so
        # log to stderr until then.
        stderr_handler = StreamHandler(sys.stderr)
        stderr_handler.setFormatter(LOG_FORMATTER)
        logger.addHandler(stderr_handler)
        logger.addFilter(Filter())
        logger.debug("Debugging messages on.")
        self._device = self._device_def['cls'](index=self.count,
                                               **self._device_def)
        while True:
            try:
                self._device.initialize()
            except Exception as e:
                logger.info("Failed to start device. Retrying in 5s.",
                            exc_info=e)
                time.sleep(5)
            else:
                break
        if (isinstance(self._device, FloatingDeviceMixin)
            and len(self._id_to_host) > 1):
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
                                          (type(self._device).__name__,
                                           host, port))
        log_handler.setFormatter(LOG_FORMATTER)
        logger.addHandler(log_handler)
        logger.info('Device initialized; starting daemon.')

        # Run the Pyro daemon in a separate thread so that we can do
        # clean shutdown under Windows.
        pyro_thread = Thread(target=Pyro4.Daemon.serveSimple,
                             args=({self._device:
                                    type(self._device).__name__},),
                             kwargs={'daemon': pyro_daemon, 'ns':
                                     False})
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
    logger = logging.getLogger(__name__)
    if __debug__:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    stderr_handler = StreamHandler(sys.stderr)
    stderr_handler.setFormatter(LOG_FORMATTER)
    logger.addHandler(stderr_handler)
    logger.addFilter(Filter())

    # An event to trigger clean termination of subprocesses. This is the
    # only way to ensure devices are shut down properly when processes
    # exit, as __del__ is not necessarily called when the interpreter exits.
    exit_event = multiprocessing.Event()

    servers = [] # DeviceServers instances that we need to wait for when exiting

    ## Child processes inherit signal handling from the parent so we
    ## need to make sure that only the parent process sets the exist
    ## event and waits for the DeviceServers to exit.  See issue #9.
    parent = multiprocessing.current_process ()
    def term_func(sig, frame):
        """Terminate subprocesses cleanly."""
        if parent == multiprocessing.current_process ():
            exit_event.set()
            for this_server in servers:
                this_server.join()
            sys.exit()

    signal.signal(signal.SIGTERM, term_func)
    signal.signal(signal.SIGINT, term_func)

    devices = None
    if len(sys.argv) == 2:
        config = imp.load_source ('microscope.config', sys.argv[1])
        devices = getattr(config, 'DEVICES', None)
        if not devices:
            logger.critical("No 'DEVICES=...' in config file. Exiting.")
        elif not isinstance(devices, collections.Iterable):
            logger.critical("Error in config: DEVICES should be an iterable."
                            " Exiting.")
            devices = None
    else:
        logger.critical("No config file specified. Exiting.")

    if not devices:
        sys.exit()

    # Group devices by class.
    by_class = {}
    for dev in devices:
        by_class[dev['cls']] = by_class.get(dev['cls'], []) + [dev]

    # Group devices by class.
    if not by_class:
        logger.critical("No valid devices specified. Exiting")
        sys.exit()

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

    # Main thread must be idle to process signals correctly, so use another
    # thread to check DeviceServers, restarting them where necessary. Define
    # the thread target here so that it can access variables in __main__ scope.
    def keep_alive():
        """Keep DeviceServers alive."""
        while not exit_event.is_set():
            time.sleep(1)
            for s in servers:
                if not s.is_alive() and s.exitcode < 0:
                    logger.info(("DeviceServer Failure. Process %s is dead with"
                                 " exitcode %s. Restarting...")
                                % (s.pid, s.exitcode))
                    servers.remove(s)
                    servers.append(DeviceServer(s._device_def,
                                                s._id_to_host,
                                                s._id_to_port,
                                                exit_event=exit_event,
                                                count=s.count))

                    try:
                        s.join(30)
                    except:
                        logger.error("... could not join PID %s." % (old_pid))
                    else:
                        old_pid = s.pid
                        del (s)
                        servers[-1].start()
                        logger.info(("... DeviceServer with PID %s restarted"
                                     " as PID %s.")
                                    % (old_pid, servers[-1].pid))
            if len(servers) == 0:
                # Log and exit if no servers running. May want to change this
                # if we add some interface to interactively restart servers.
                logger.info("No servers running. Exiting.")
                exit_event.set()


    keep_alive_thread = Thread(target=keep_alive)
    keep_alive_thread.start()

    for s in servers:
        # This will iterate over all servers: those present when the loop
        # is entered, and any added to the list later.
        s.join()


if __name__ == '__main__':
    """Serve devices via Pyro.

    Usage:  deviceserver [config]
    """
    __main__()
