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

"""Classes for control of microscope components.

This module provides base classes for experiment control and data
acquisition devices that can be served over Pyro. This means that each
device may be served from a separate process, or even from a different PC.

When called from the command line, this module will serve devices defined
in a config file.

"""
import abc
import distutils.version
import logging
from logging.handlers import RotatingFileHandler
import multiprocessing
import numpy as np
from collections import OrderedDict
import Pyro4
import Queue
from threading import Thread
import time

# Pyro4 configuration.
if (distutils.version.LooseVersion(Pyro4.__version__) >=
    distutils.version.LooseVersion('4.22')):
    Pyro4.config.SERIALIZERS_ACCEPTED.discard('serpent')
    Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
    Pyro4.config.SERIALIZER = 'pickle'


LOG_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s PID %(process)s: %(message)s')

# Mapping of setting data types to allowed-value description types.
DTYPES = {'int': tuple,
          'float': tuple,
          'bool': type(None),
          'enum': list,
          'str': int,
          int: tuple,
          float: tuple,
          bool: type(None),
          str: int}

# A utility function
_call_if_callable = lambda f: f() if callable(f) else f

# A device definition for use in config files.
def device(cls, host, port, uid=None, **kwargs):
    """Define a device and where to serve it.

    Defines a device of type cls, served on host:port.
    UID is used to identify 'floating' devices (see below).
    kwargs can be used to pass any other parameters to cls.__init__.
    """
    return dict(cls=cls, host=host, port=int(port), uid=None, **kwargs)


class FloatingDeviceMixin(object):
    __metaclass__ = abc.ABCMeta
    """A mixin for devices that 'float'.

    Some SDKs handling multiple devices do not allow for explicit
    selection of a specific device: instead, a device must be
    initialized and then queried to determine its ID. This class is
    a mixin which identifies a subclass as floating, and enforces
    the implementation of a 'get_id' method.
    """
    @abc.abstractmethod
    @Pyro4.expose
    def get_id(self):
        """Return a unique hardware identifier, such as a serial number."""
        pass


class Device(object):
    #__metaclass__ = abc.ABCMeta
    """A base device class. All devices should sublcass this class."""
    def __init__(self, *args, **kwargs):
        self.enabled = None
        # A list of settings. (Can't serialize OrderedDict, so use {}.)
        self.settings = OrderedDict()
        # We fetch a logger here, but it can't log anything until
        # a handler is attached after we've identified this device.
        self._logger = logging.getLogger()
        self._index = kwargs['index'] if 'index' in kwargs else None


    def __del__(self):
        self.shutdown()


    def add_setting(self, name, dtype, get_func, set_func, values, readonly=False):
        """Add a setting definition.

        :param name: the setting's name
        :param dtype: a data type from ('int', 'float', 'bool', 'enum', 'str')
        :param get_func: a function to get the current value
        :param set_func: a function to set the value
        :param values: a description of allowed values dependent on dtype,
                       or function that returns a description.

        A client needs some way of knowing a setting name and data type,
        retrieving the current value and, if settable, a way to retrieve
        allowable values, and set the value.
        We store this info in an OrderedDict. I considered having a Setting
        class with getter, setter, etc., and adding Setting instances as
        device attributes, but Pyro does not support dot notation to access
        the functions we need (e.g. Device.some_setting.set ), so I'd have to
        write access functions, anyway.
        """
        # Mapping of dtype to type(values)
        if dtype not in DTYPES:
            raise Exception('Unsupported dtype.')
        elif not (isinstance(values, DTYPES[dtype]) or callable(values)):
            raise Exception('Invalid values type for %s: expected function or %s' %
                            (dtype, DTYPES[dtype]))
        else:
            self.settings.update({name:{'type':dtype,
                                        'get':get_func,
                                        'set':set_func,
                                        'values':values,
                                        'current':None,
                                        'readonly': readonly}})

    def _on_disable(self):
        """Do any device-specific work on disable.

        Subclasses should override this method, rather than modfiy
        disable(self).
        """
        return True


    @Pyro4.expose
    def disable(self):
        """Disable the device for a short period for inactivity."""
        self._on_disable()
        self.enabled = False



    def _on_enable(self):
        """Do any device-specific work on enable.

        Subclasses should override this method, rather than modify
        enable(self).
        """
        return True


    @Pyro4.expose
    def enable(self):
        """Enable the device."""
        self.enabled = self._on_enable()


    @Pyro4.expose
    def get_setting(self, name):
        """Return the current value of a setting."""
        return self.settings[name]['get']()


    @Pyro4.expose
    def describe_settings(self):
        """Return ordered setting descriptions as a list of dicts."""
        return [(k, {  # wrap type in str since can't serialize types
            'type': str(v['type']),
            'values': _call_if_callable(v['values']),
            'readonly': _call_if_callable(v['readonly']),})
                for (k, v) in self.settings.iteritems()]


    @Pyro4.expose
    def get_all_settings(self):
        """Return ordered settings as a list of dicts."""
        return{k : v['get']() if v['get'] else None
               for k, v in self.settings.iteritems()}


    @Pyro4.expose
    def set_setting(self, name, value):
        """Set a setting."""
        if self.settings[name]['set'] is None:
            raise NotImplementedError
        ### TODO ### further validation.
        self.settings[name]['set'](value)


    @abc.abstractmethod
    @Pyro4.expose
    def initialize(self, *args, **kwargs):
        """Initialize the device."""
        pass


    @Pyro4.expose
    def make_safe(self):
        """Put the device into a safe state."""
        pass


    @abc.abstractmethod
    @Pyro4.expose
    def shutdown(self):
        """Shutdown the device for a prolonged period of inactivity."""
        self.enabled = False
        self._logger.info("Shutting down device.")


    @Pyro4.expose
    def update_settings(self, incoming, init=False):
        """Update settings based on dict of settings and values."""
        if init:
            # Assume nothing about state: set everything.
            my_keys = set(self.settings.keys())
            their_keys = set(incoming.keys())
            update_keys = my_keys & their_keys
            if update_keys != my_keys:
                missing = ', '.join([k for k in my_keys - their_keys])
                msg = 'update_settings init=True but missing keys: %s.' % missing
                self._logger.debug(msg)
                raise Exception(msg)
        else:
            # Only update changed values.
            my_keys = set(self.settings.keys())
            their_keys = set(incoming.keys())
            update_keys = set(key for key in my_keys & their_keys
                              if self.settings[key]['current'] != incoming[key])
        results = {}
        # Update values.
        for key in update_keys:
            if key not in my_keys or not self.settings[key]['set']:
                # Setting not recognised or no set function implemented
                results[key] = NotImplemented
                update_keys.remove(key)
                continue
            self.settings[key]['set'](incoming[key])
        # Read back values in second loop.
        for key in update_keys:
            results[key] = self.settings[key]['get']()
        return results


# Wrapper to preserve acquiring state.
def keep_acquiring(func):
    def wrapper(self, *args, **kwargs):
        if self._acquiring:
            self.abort()
            result = func(self, *args, **kwargs)
            self._on_enable()
        else:
            result = func(self, *args, **kwargs)
        return result
    return wrapper


class DataDevice(Device):
    __metaclass__ = abc.ABCMeta
    """A data capture device.

    This class handles a thread to fetch data from a device and dispatch
    it to a client.  The client is set using set_client(uri) or (legacy)
    receiveClient(uri).
    Derived classed should implement:
        abort(self)                ---  required
        start_acquisition(self)    ---  required
        _fetch_data(self)          ---  required
        _process_data(self, data)  ---  optional
    Derived classes may override __init__, enable and disable, but must
    ensure to call this class's implementations as indicated in the docstrings.
    """
    def __init__(self, buffer_length=0, **kwargs):
        """Derived.__init__ must call this at some point."""
        super(DataDevice, self).__init__(**kwargs)
        # A length-1 buffer for fetching data.
        self._data = None
        # A thread to fetch and dispatch data.
        self._fetch_thread = None
        # A flag to control the _fetch_thread.
        self._fetch_thread_run = False
        # A client to which we send data.
        self._client = None
        # A thread to dispatch data.
        self._dispatch_thread = None
        # A buffer for data dispatch.
        self._buffer = Queue.Queue(maxsize = buffer_length)
        # A flag to indicate if device is ready to acquire.
        self._acquiring = False


    def __del__(self):
        self.disable()

    # Wrap set_setting to pause and resume acquisition.
    set_setting = Pyro4.expose(keep_acquiring(Device.set_setting))

    @abc.abstractmethod
    @Pyro4.expose
    def abort(self):
        """Stop acquisition as soon as possible."""
        self._acquiring = False


    @Pyro4.expose
    def enable(self):
        """Enable the data capture device.

        Ensures that a data handling threads are running.
        Implement device-specific code in _on_enable .
        """
        # Call device-specific code before starting threads.
        if not self._on_enable():
            self.enabled = False
            return False
        if not self._fetch_thread or not self._fetch_thread.is_alive():
            self._fetch_thread = Thread(target=self._fetch_loop)
            self._fetch_thread.daemon = True
            self._fetch_thread.start()
        if not self._dispatch_thread or not self._dispatch_thread.is_alive():
            self._dispatch_thread = Thread(target=self._dispatch_loop)
            self._dispatch_thread.daemon = True
            self._dispatch_thread.start()
        self.enabled = True

    @Pyro4.expose
    def disable(self):
        """Disable the data capture device.

        Implement device-specific code in _on_disable ."""
        self.enabled = False
        if self._fetch_thread:
            if self._fetch_thread.is_alive():
                self._fetch_thread_run = False
                self._fetch_thread.join()
        super(DataDevice, self).disable()


    @abc.abstractmethod
    def _fetch_data(self):
        """Poll for data and return it, with minimal processing.

        If the device uses buffering in software, this function should copy
        the data from the buffer, release or recycle the buffer, then return
        a reference to the copy. Otherwise, if the SDK returns a data object
        that will not be written to again, this function can just return a
        reference to the object.
        If no data is available, return None.
        """
        return None


    def _process_data(self, data):
        """Do any data processing and return data."""
        return data


    def _send_data(self, data, timestamp):
        """Dispatch data to the client."""
        if self._client:
            try:
                # Currently uses legacy receiveData. Would like to pass
                # this function name as an argument to set_client, but
                # not sure how to subsequently resolve this over Pyro.
                self._client.receiveData(data, timestamp)
            except Pyro4.errors.ConnectionClosedError:
                # Nothing is listening
                self._client = None
            except:
                raise


    def _dispatch_loop(self):
        """Process data and send results to any client."""
        while True:
            if self._buffer.empty():
                time.sleep(0.01)
                continue
            data, timestamp = self._buffer.get()
            err = None
            if isinstance(data, Exception):
                standard_exception = Exception(str(data))
                try:
                    self._send_data(standard_exception, timestamp)
                except Exception as e:
                    err = e
            else:
                try:
                    self._send_data(self._process_data(data), timestamp)
                except Exception as e:
                    err = e

            if err:
                # Raising an exception will kill the dispatch loop. We need another
                # way to notify the client that there was a problem.
                self._logger.error("in _dispatch_loop: %s." % err)
            self._buffer.task_done()


    def _fetch_loop(self):
        """Poll source for data and put it into dispatch buffer."""
        self._fetch_thread_run = True
        while self._fetch_thread_run:
            try:
                data = self._fetch_data()
            except Exception as e:
                self._logger.error("in _fetch_loop: %s." % e)
                # Raising an exception will kill the fetch loop. We need another
                # way to notify the client that there was a problem.
                timestamp = time.time()
                self._buffer.put((e, timestamp))
                data = None
            if data is not None:
                # ***TODO*** Add support for timestamp from hardware.
                timestamp = time.time()
                self._buffer.put((data, timestamp))
            else:
                time.sleep(0.001)


    @Pyro4.expose
    def set_client(self, client_uri):
        """Set up a connection to our client."""
        self._logger.info("Setting client to %s." % client_uri)
        if client_uri is not None:
            self._client = Pyro4.Proxy(client_uri)
        else:
            self._client = None


    @Pyro4.expose
    @keep_acquiring
    def update_settings(self, settings, init=False):
        """Update settings, toggling acquisition if necessary."""
        was_acquiring = self._acquiring
        if was_acquiring:
            self.abort()
        super(DataDevice, self).update_settings(settings, init)
        if was_acquiring:
            self.start_acquisition()


    @Pyro4.expose
    def receiveClient(self, client_uri):
        """A passthrough for compatibility."""
        self.set_client(client_uri)


class DeviceServer(multiprocessing.Process):
    def __init__(self, device_def, id_to_host, id_to_port, count=0, exit_event=None):
        """Initialise a device and serve at host/port according to its id.

        :param device_def:  definition of the device
        :param host_or_map: host or mapping of device identifiers to hostname
        :param port_or_map: map or mapping of device identifiers to port number
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
        logger.setLevel(logging.INFO)
        logger.info('Device initialized; starting daemon.')

        # Run the Pyro daemon in a separate thread so that we can do
        # clean shutdown under Windows.
        pyro_thread = Thread(target=Pyro4.Daemon.serveSimple,
                             args=({self._device: type(self).__name__},),
                             kwargs={'daemon':pyro_daemon, 'ns':False})
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
    # exit, as __del__ is not necessarily called when the intepreter exits.
    exit_event = multiprocessing.Event()
    def term_func(sig, frame):
        """Terminate subprocesses cleanly."""
        exit_event.set()
        for s in servers:
            s.join()
        sys.exit()

    signal.signal(signal.SIGTERM, term_func)
    signal.signal(signal.SIGINT, term_func)

    if len(sys.argv) == 1:
        import config
    else:
        config = __import__(os.path.splitext(sys.argv[1])[0])

    # Group devices by class.
    by_class = {}
    for r in config.DEVICES:
        by_class[r['cls']] = by_class.get(r['cls'], []) + [r]

    servers = []
    for cls, rs in by_class.iteritems():
        # Keep track of how many of these classes we have set up.
        # Some SDKs need this information to index devices.
        count = 0
        if issubclass(cls, FloatingDeviceMixin):
            # Need to provide maps of uid to host and port.
            uid_to_host = {}
            uid_to_port = {}
            for r in rs:
                uid = r['uid']
                uid_to_host[uid] = r['host']
                uid_to_port[uid] = r['port']
        else:
            uid_to_host = None
            uid_to_port = None

        for r in rs:
            servers.append(DeviceServer(r,
                                        uid_to_host, uid_to_port,
                                        exit_event=exit_event, count=count))
            servers[-1].start()
            count += 1
    for s in servers:
        s.join()


if __name__ == '__main__':
    """Serve devices via pyro.

    Usage:  devicebase [config]
    """
    import signal, sys
    import os
    __main__()