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
defined in a specified config file.
"""

from collections.abc import Iterable
import importlib.util
import logging
import multiprocessing
import signal
import sys
import time
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from threading import Thread

import Pyro4

import microscope.devices


_logger = logging.getLogger(__name__)


# Needed for Python<3.8 in MacOSX High Sierra (issue #106)
# FIXME: remove this once we are dependent on Python>=3.8
if sys.platform == 'darwin' and sys.version_info < (3,8):
    _logger.info("changing multiprocessing start method to 'spawn'")
    multiprocessing = multiprocessing.get_context('spawn')


# Pyro configuration. Use pickle because it can serialize numpy ndarrays.
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'

## We effectively expose all attributes of the classes since our
## devices don't hold any private data.  The private methods are to
## signal an interface not meant for public usage, not because there's
## anything secret or unsafe.  So disable REQUIRE_EXPOSE which avoids
## requiring Pyro4.expose all over the code (see issue #49)
Pyro4.config.REQUIRE_EXPOSE = False


def _create_log_formatter(name: str):
    """Create a logging.Formatter for the device server.

    Each device is served on its own process and each device has its
    own log file.  But the logs from all device servers also appear on
    stderr where it will be difficult to figure out from which device
    server a log message comes.  This creates a logging.Formatter
    which includes the device server name.

    Args:
        name (str): device name to be used on the log output.

    """
    return logging.Formatter('%%(asctime)s:%s (%%(name)s):%%(levelname)s'
                             ':PID %%(process)s: %%(message)s' % name)


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
    def __init__(self, device_def, id_to_host, id_to_port, exit_event=None):
        """Initialise a device and serve at host/port according to its id.

        :param device_def: definition of the device
        :param id_to_host: host or mapping of device identifiers to hostname
        :param id_to_port: map or mapping of device identifiers to port number
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
        super().__init__()
        self.daemon = True

    def clone(self):
        """Create new instance with same settings.

        This is useful to restart a device server.
        """
        return DeviceServer(self._device_def, self._id_to_host,
                            self._id_to_port, exit_event=self.exit_event)

    def run(self):
        cls_name = self._device_def['cls'].__name__

        # If the multiprocessing start method is fork, the child
        # process gets a copy of the root logger.  The copy is
        # configured to sign the messages as "device-server", and
        # write to the main log file and stderr.  We remove those
        # handlers so that this DeviceServer is logged to a separate
        # file and the messages are signed with the device name.
        root_logger = logging.getLogger()
        # Get a new list of handlers because otherwise we are
        # iterating over the same list as removeHandler().
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

        if __debug__:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.INFO)


        # Later, we'll log to one file per server, with a filename
        # based on a unique identifier for the device. Some devices
        # don't have UIDs available until after initialization, so
        # log to stderr until then.
        stderr_handler = StreamHandler(sys.stderr)
        stderr_handler.setFormatter(_create_log_formatter(cls_name))
        root_logger.addHandler(stderr_handler)
        root_logger.debug("Debugging messages on.")

        root_logger.addFilter(Filter())

        self._device = self._device_def['cls'](**self._device_def['conf'])
        while not self.exit_event.is_set():
            try:
                self._device.initialize()
            except Exception as e:
                _logger.info("Failed to start device. Retrying in 5s.",
                             exc_info=e)
                time.sleep(5)
            else:
                break
        if (isinstance(self._device, microscope.devices.FloatingDeviceMixin)
            and len(self._id_to_host) > 1):
            uid = str(self._device.get_id())
            if uid not in self._id_to_host or uid not in self._id_to_port:
                raise Exception("Host or port not found for device %s" % (uid,))
            host = self._id_to_host[uid]
            port = self._id_to_port[uid]
        else:
            host = self._device_def['host']
            port = self._device_def['port']
        pyro_daemon = Pyro4.Daemon(port=port, host=host)

        log_handler = RotatingFileHandler('%s_%s_%s.log'
                                          % (cls_name, host, port))
        log_handler.setFormatter(_create_log_formatter(cls_name))
        root_logger.addHandler(log_handler)

        _logger.info('Device initialized; starting daemon.')

        pyro_daemon.register(self._device, cls_name)
        if isinstance(self._device, microscope.devices.ControllerDevice):
            # AUTOPROXY should be enabled by default.  If we find it
            # disabled, there must be a reason why, so raise an error
            # instead of silently enabling it.
            if not Pyro4.config.AUTOPROXY:
                raise RuntimeError('serving of a ControllerDevice requires'
                                   ' Pyro4 AUTOPROXY option enabled')

            # Autoproxy does not work with marshal serializer.
            Pyro4.config.SERIALIZERS_ACCEPTED.discard('marshal')

            for sub_device in self._device.devices.values():
                pyro_daemon.register(sub_device)

        # Run the Pyro daemon in a separate thread so that we can do
        # clean shutdown under Windows.
        pyro_thread = Thread(target = pyro_daemon.requestLoop)
        pyro_thread.daemon = True
        pyro_thread.start()
        _logger.info('Serving %s' % pyro_daemon.uriFor(self._device))
        if isinstance(self._device, microscope.devices.FloatingDeviceMixin):
            _logger.info('Device UID on port %s is %s'
                         % (port, self._device.get_id()))

        # Wait for termination event. We should just be able to call
        # wait() on the exit_event, but this causes issues with locks
        # in multiprocessing - see http://bugs.python.org/issue30975 .
        while self.exit_event and not self.exit_event.is_set():
            # This tread waits for the termination event.
            try:
                time.sleep(5)
            except (KeyboardInterrupt, IOError):
                pass
        pyro_daemon.shutdown()
        pyro_thread.join()
        self._device.shutdown()


def serve_devices(devices, exit_event=None):
    root_logger = logging.getLogger()

    log_handler = RotatingFileHandler("__MAIN__.log")
    log_handler.setFormatter(_create_log_formatter('device-server'))
    root_logger.addHandler(log_handler)

    root_logger.setLevel(logging.DEBUG)

    # An event to trigger clean termination of subprocesses. This is the
    # only way to ensure devices are shut down properly when processes
    # exit, as __del__ is not necessarily called when the interpreter exits.
    if exit_event is None:
        exit_event = multiprocessing.Event()

    servers = [] # DeviceServers instances that we need to wait for when exiting

    ## Child processes inherit signal handling from the parent so we
    ## need to make sure that only the parent process sets the exit
    ## event and waits for the DeviceServers to exit.  See issue #9.
    ## This won't work behind a Windows service wrapper, so we deal with
    ## clean shutdown on win32 elsewhere.
    parent = multiprocessing.current_process ()
    def term_func(sig, frame):
        """Terminate subprocesses cleanly."""
        if parent == multiprocessing.current_process ():
            _logger.debug("Shutting down all servers.")
            exit_event.set()
            # Join keep_alive_thread so that it can't modify the list
            # of servers.
            keep_alive_thread.join()
            for this_server in servers:
                this_server.join()
            sys.exit()

    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, term_func)
        signal.signal(signal.SIGINT, term_func)

    # Group devices by class.
    by_class = {}
    for dev in devices:
        by_class[dev['cls']] = by_class.get(dev['cls'], []) + [dev]

    # Group devices by class.
    if not by_class:
        _logger.critical("No valid devices specified. Exiting")
        sys.exit()

    for cls, devs in by_class.items():
        # Keep track of how many of these classes we have set up.
        # Some SDKs need this information to index devices.
        count = 0
        if issubclass(cls, microscope.devices.FloatingDeviceMixin):
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
            dev['conf']['index'] = count
            servers.append(DeviceServer(dev, uid_to_host, uid_to_port,
                                        exit_event=exit_event))
            servers[-1].start()
            count += 1

    # Main thread must be idle to process signals correctly, so use another
    # thread to check DeviceServers, restarting them where necessary. Define
    # the thread target here so that it can access variables in __main__ scope.
    def keep_alive():
        """Keep DeviceServers alive."""
        while not exit_event.is_set():
            for s in servers:
                if s.is_alive():
                    continue
                else:
                    _logger.info("DeviceServer Failure. Process %s is dead with"
                                 " exitcode %s. Restarting..."
                                 % (s.pid, s.exitcode))
                    servers.remove(s)
                    servers.append(s.clone())

                    try:
                        s.join(30)
                    except:
                        _logger.error("... could not join PID %s." % (old_pid))
                    else:
                        old_pid = s.pid
                        del (s)
                        servers[-1].start()
                        _logger.info("... DeviceServer with PID %s restarted"
                                     " as PID %s." % (old_pid, servers[-1].pid))
            if len(servers) == 0:
                # Log and exit if no servers running. May want to change this
                # if we add some interface to interactively restart servers.
                _logger.info("No servers running. Exiting.")
                exit_event.set()
            try:
                time.sleep(5)
            except (KeyboardInterrupt, IOError):
                pass

    keep_alive_thread = Thread(target=keep_alive)
    keep_alive_thread.start()

    while not exit_event.is_set():
        try:
            time.sleep(5)
        except (KeyboardInterrupt, IOError):
            _logger.debug("KeyboardInterrupt or IOError")
            exit_event.set()

    _logger.debug("Shutting down servers ...")
    while len(servers) > 0:
        for s in servers:
            if not s.is_alive():
                servers.remove(s)
                del(s)
        time.sleep(1)
    _logger.info(" ... No more servers running.")
    _logger.debug("Joining threads ...")
    keep_alive_thread.join()
    _logger.debug("... Threads joined. Exiting.")
    return


def __main__():
    """Serve devices via Pyro.

    To run in the terminal, use::

        deviceserver CONFIG

    To configure and run as a Windows service use::

        deviceserver [install,remove,update,start,stop,restart,status] CONFIG

    ``CONFIG`` is a ``.py`` file that exports ``DEVICES = [device(...), ...]``
    """

    if len(sys.argv) == 1:
        print("\nToo few arguments.\n", file=sys.stderr)
        print(__main__.__doc__, file=sys.stderr)
        sys.exit(1)

    if sys.argv[1].lower() in ['install', 'update',
                               'start', 'stop', 'restart',
                               'remove', 'status']:
        __winservice__()
    else:
        __console__()


def _load_source(filepath):
    spec = importlib.util.spec_from_file_location('config', filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_devices(configfile):
    config = _load_source(configfile)
    devices = getattr(config, 'DEVICES', None)
    if not devices:
        raise Exception("No 'DEVICES=...' in config file.")
    elif not isinstance(devices, Iterable):
        raise Exception("Error in config: DEVICES should be an iterable.")
    return devices


def __console__():
    """Serve devices from a console process."""
    root_logger = logging.getLogger()
    if __debug__:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    stderr_handler = StreamHandler(sys.stderr)
    stderr_handler.setFormatter(_create_log_formatter('device-server'))
    root_logger.addHandler(stderr_handler)

    root_logger.addFilter(Filter())

    if len(sys.argv) < 2:
        _logger.critical("No config file specified. Exiting.")
        devices = []
    else:
        try:
            devices = validate_devices(sys.argv[1])
        except Exception as e:
            _logger.critical(e)
            devices = []

    if not devices:
        sys.exit(1)

    serve_devices(devices)


def __winservice__():
    """Configure and control a Windows service to serve devices."""
    from microscope.win32 import handle_command_line
    handle_command_line()


if __name__ == '__main__':
    __main__()
