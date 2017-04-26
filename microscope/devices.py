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
"""
import abc
import itertools
import logging
import time
from ast import literal_eval
from collections import OrderedDict
from threading import Thread
import Pyro4
import numpy

# Python 2.7 and 3 compatibility.
try:
    import queue
except:
    # noinspection PyPep8Naming
    import Queue as queue

from six import iteritems

# Trigger types.
(TRIGGER_AFTER, TRIGGER_BEFORE, TRIGGER_DURATION, TRIGGER_SOFT) = range(4)

# Device types.
(UGENERIC, USWITCHABLE, UDATA, UCAMERA, ULASER, UFILTER) = range(6)

# Mapping of setting data types to descriptors allowed-value description types.
# For python 2 and 3 compatibility, we convert the type into a descriptor string.
# This avoids problems with, say a python 2 client recognising a python 3
# <class 'int'> as a python 2 <type 'int'>.
DTYPES = {'int': ('int', tuple),
          'float': ('float', tuple),
          'bool': ('bool', type(None)),
          'enum': ('enum', list),
          'str': ('str', int),
          int: ('int', tuple),
          float: ('float', tuple),
          bool: ('bool', type(None)),
          str: ('str', int)}

# A utility function to call callables or return value of non-callables.
# noinspection PyPep8
_call_if_callable = lambda f: f() if callable(f) else f


# A device definition for use in config files.
def device(cls, host, port, uid=None, **kwargs):
    """Define a device and where to serve it.

    Defines a device of type cls, served on host:port.
    UID is used to identify 'floating' devices (see below).
    kwargs can be used to pass any other parameters to cls.__init__.
    """
    return dict(cls=cls, host=host, port=int(port), uid=None, **kwargs)


# === FloatingDeviceMixin ===
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


# === Device ===
class Device(object):
    __metaclass__ = abc.ABCMeta
    """A base device class. All devices should subclass this class."""

    def __init__(self, *args, **kwargs):
        self.enabled = None
        # A list of settings. (Can't serialize OrderedDict, so use {}.)
        self.settings = OrderedDict()
        # We fetch a logger here, but it can't log anything until
        # a handler is attached after we've identified this device.
        self._logger = logging.getLogger(self.__class__.__name__)
        self._index = kwargs['index'] if 'index' in kwargs else None
        self._utype = UGENERIC

    def __del__(self):
        self.shutdown()


    @Pyro4.expose
    def get_device_type(self):
        return self._utype


    @Pyro4.expose
    def get_is_enabled(self):
        return self.enabled


    def _on_disable(self):
        """Do any device-specific work on disable.

        Subclasses should override this method, rather than modify
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
        try:
            self.enabled = self._on_enable()
        except Exception as err:
            self._logger.debug("Error in _on_enable:", exc_info=err)

    @abc.abstractmethod
    def _on_shutdown(self):
        """Subclasses over-ride this with tasks to do on shutdown."""
        pass

    @abc.abstractmethod
    @Pyro4.expose
    def initialize(self, *args, **kwargs):
        """Initialize the device."""
        pass

    @Pyro4.expose
    def shutdown(self):
        """Shutdown the device for a prolonged period of inactivity."""
        self.enabled = False
        self._logger.info("Shutting down ... ... ...")
        self._on_shutdown()
        self._logger.info("... ... ... ... shut down completed.")

    @Pyro4.expose
    def make_safe(self):
        """Put the device into a safe state."""
        pass

    # Methods for manipulating settings.
    def add_setting(self, name, dtype, get_func, set_func, values, readonly=False):
        """Add a setting definition.

        :param name: the setting's name
        :param dtype: a data type from ('int', 'float', 'bool', 'enum', 'str')
        :param get_func: a function to get the current value
        :param set_func: a function to set the value
        :param values: a description of allowed values dependent on dtype,
                       or function that returns a description
        :param readonly: an optional flag to indicate a read-only setting.

        A client needs some way of knowing a setting name and data type,
        retrieving the current value and, if settable, a way to retrieve
        allowable values, and set the value.
        We store this info in an OrderedDict. I considered having a Setting
        class with getter, setter, etc., and adding Setting instances as
        device attributes, but Pyro does not support dot notation to access
        the functions we need (e.g. Device.some_setting.set ), so I'd have to
        write access functions, anyway.
        """
        if dtype not in DTYPES:
            raise Exception('Unsupported dtype.')
        elif not (isinstance(values, DTYPES[dtype][1]) or callable(values)):
            raise Exception('Invalid values type for %s: expected function or %s' %
                            (dtype, DTYPES[dtype][1]))
        else:
            self.settings.update({name: {'type': DTYPES[dtype][0],
                                         'get': get_func,
                                         'set': set_func,
                                         'values': values,
                                         'current': None,
                                         'readonly': readonly}})

    @Pyro4.expose
    def get_setting(self, name):
        """Return the current value of a setting."""
        try:
            return self.settings[name]['get']()
        except Exception as err:
            self._logger.error("in get_setting(%s):" % (name), exc_info=err)
            raise

    @Pyro4.expose
    def get_all_settings(self):
        """Return ordered settings as a list of dicts."""
        try:
            return {k: v['get']() if v['get'] else None
                    for k, v in iteritems(self.settings)}
        except Exception as err:
            self._logger.error("in get_all_settings:", exc_info=err)
            raise

    @Pyro4.expose
    def set_setting(self, name, value):
        """Set a setting."""
        if self.settings[name]['set'] is None:
            raise NotImplementedError
        # TODO further validation.
        try:
            self.settings[name]['set'](value)
        except Exception as err:
            self._logger.error("in set_setting(%s):" % (name), exc_info=err)


    @Pyro4.expose
    def describe_setting(self, name):
        """Return ordered setting descriptions as a list of dicts."""
        v = self.settings.get(name, None)
        if v is None:
            return v
        else:
            return {  # wrap type in str since can't serialize types
                'type': str(v['type']),
                'values': _call_if_callable(v['values']),
                'readonly': _call_if_callable(v['readonly']), }

    @Pyro4.expose
    def describe_settings(self):
        """Return ordered setting descriptions as a list of dicts."""
        return [(k, {  # wrap type in str since can't serialize types
            'type': str(v['type']),
            'values': _call_if_callable(v['values']),
            'readonly': _call_if_callable(v['readonly']), })
                for (k, v) in iteritems(self.settings)]

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


# === DataDevice ===

# Wrapper to preserve acquiring state of data capture devices.
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
        # A flag to indicate that this class uses a fetch callback.
        self._using_callback = False
        # A client to which we send data.
        self._client = None
        # A thread to dispatch data.
        self._dispatch_thread = None
        # A buffer for data dispatch.
        self._dispatch_buffer = queue.Queue(maxsize=buffer_length)
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
        self._logger.debug("Enabling ...")
        if self._using_callback:
            if self._fetch_thread:
                self._fetch_thread_run = False
        else:
            if not self._fetch_thread or not self._fetch_thread.is_alive():
                self._fetch_thread = Thread(target=self._fetch_loop)
                self._fetch_thread.daemon = True
                self._fetch_thread.start()
        if not self._dispatch_thread or not self._dispatch_thread.is_alive():
            self._dispatch_thread = Thread(target=self._dispatch_loop)
            self._dispatch_thread.daemon = True
            self._dispatch_thread.start()
        # Call device-specific code.
        try:
            result = self._on_enable()
        except Exception as err:
            self._logger.debug("Error in _on_enable:", exc_info=err)
            self.enabled = False
            raise err
        if not result:
            self.enabled = False
        else:
            self.enabled = True
        self._logger.debug("... enabled.")
        return self.enabled

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
            data, timestamp = self._dispatch_buffer.get(block=True)
            err = None
            if isinstance(data, Exception):
                standard_exception = Exception(str(data).encode('ascii'))
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
                self._logger.error("in _dispatch_loop:", exc_info=err)
            self._dispatch_buffer.task_done()

    def _fetch_loop(self):
        """Poll source for data and put it into dispatch buffer."""
        self._fetch_thread_run = True

        while self._fetch_thread_run:
            try:
                data = self._fetch_data()
            except Exception as e:
                self._logger.error("in _fetch_loop:", exc_info=e)
                # Raising an exception will kill the fetch loop. We need another
                # way to notify the client that there was a problem.
                timestamp = time.time()
                self._dispatch_buffer.put((e, timestamp))
                data = None
            if data is not None:
                # ***TODO*** Add support for timestamp from hardware.
                timestamp = time.time()
                self._dispatch_buffer.put((data, timestamp))
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
        super(DataDevice, self).update_settings(settings, init)

    # noinspection PyPep8Naming
    @Pyro4.expose
    def receiveClient(self, client_uri):
        """A passthrough for compatibility."""
        self.set_client(client_uri)


# === CameraDevice ===
class CameraDevice(DataDevice):
    ALLOWED_TRANSFORMS = [p for p in itertools.product(*3 * [range(2)])]
    """Adds functionality to DataDevice to support cameras.

    Defines the interface for cameras.
    Applies a transform to acquired data in the processing step.
    """

    def __init__(self, *args, **kwargs):
        super(CameraDevice, self).__init__(**kwargs)
        # A list of readout mode descriptions.
        self._readout_modes = ['default']
        # The current readout mode.
        self._readout_mode = 'default'
        # Transforms to apply to data (fliplr, flipud, rot90)
        # Transform to correct for readout order.
        self._readout_transform = (0, 0, 0)
        # Transform supplied by client to correct for system geometry.
        self._transform = (0, 0, 0)
        # A transform provided by the client.
        self.add_setting('transform', 'enum',
                         self.get_transform,
                         self.set_transform,
                         lambda: CameraDevice.ALLOWED_TRANSFORMS)
        self.add_setting('readout mode', 'enum',
                         lambda: self._readout_mode,
                         self.set_readout_mode,
                         lambda: self._readout_modes)


    def _process_data(self, data):
        """Apply self._transform to data."""
        flips = (self._transform[0], self._transform[1])
        rot = self._transform[2]

        # Choose appropriate transform based on (flips, rot).
        return {(0, 0): numpy.rot90(data, rot),
                (0, 1): numpy.flipud(numpy.rot90(data, rot)),
                (1, 0): numpy.fliplr(numpy.rot90(data, rot)),
                (1, 1): numpy.fliplr(numpy.flipud(numpy.rot90(data, rot)))
                }[flips]


    @Pyro4.expose
    def set_readout_mode(self, description):
        """Set the readout mode and _readout_transform.

        Takes a description string from _readout_modes."""
        pass


    @Pyro4.expose
    def get_transform(self):
        """Return the current transform without readout transform."""
        return tuple(self._readout_transform[i] ^ self._transform[i]
                     for i in range(3))

    @Pyro4.expose
    def set_transform(self, transform):
        """Combine provided transform with readout transform."""
        if isinstance(transform, (str, unicode)):
            transform = literal_eval(transform)
        self._transform = tuple(self._readout_transform[i] ^ transform[i]
                                for i in range(3))


    def _set_readout_transform(self, new_transform):
        """Update readout transform and update resultant transform."""
        client_transform = self.get_transform()
        self._readout_transform = new_transform
        self.set_transform(client_transform)


    @abc.abstractmethod
    @Pyro4.expose
    def set_exposure_time(self, value):
        pass

    @Pyro4.expose
    def get_exposure_time(self):
        pass

    @Pyro4.expose
    def get_cycle_time(self):
        pass

    @Pyro4.expose
    def get_sensor_temperature(self):
        """Return the sensor temperature."""
        pass

    @abc.abstractmethod
    def _get_sensor_shape(self):
        """Return a tuple of (width, height)"""
        pass

    @Pyro4.expose
    def get_sensor_shape(self):
        """Return a tuple of (width, height), corrected for transform."""
        shape = self._get_sensor_shape()
        if self._transform[2]:
            # 90 degree rotation
            shape = (shape[1], shape[0])
        return shape

    @abc.abstractmethod
    def _get_binning(self):
        """Return a tuple of (horizontal, vertical)"""
        pass

    @Pyro4.expose
    def get_binning(self):
        """Return a tuple of (horizontal, vertical), corrected for transform."""
        binning = self._get_binning()
        if self._transform[2]:
            # 90 degree rotation
            binning = (binning[1], binning[0])
        return binning

    @abc.abstractmethod
    def _set_binning(self, h_bin, v_bin):
        """Set binning along both axes. Return True if successful."""
        pass

    @Pyro4.expose
    def set_binning(self, h_bin, v_bin):
        """Set binning along both axes. Return True if successful."""
        if self._transform[2]:
            # 90 degree rotation
            binning = (v_bin, h_bin)
        else:
            binning = (h_bin, v_bin)
        return self._set_binning(*binning)

    @abc.abstractmethod
    def _get_roi(self):
        """Return the ROI as it is on hardware."""
        return left, top, width, height

    @Pyro4.expose
    def get_roi(self):
        """Return ROI as a rectangle (left, top, width, height).

        Chosen this rectangle format as it completely defines the ROI without
        reference to the sensor geometry."""
        roi = self._get_roi()
        if self._transform[2]:
            # 90 degree rotation
            roi = (roi[1], roi[0], roi[3], roi[2])
        return roi

    @abc.abstractmethod
    def _set_roi(self, left, top, width, height):
        """Set the ROI on the hardware, return True if successful."""
        return False

    @Pyro4.expose
    def set_roi(self, left, top, width, height):
        """Set the ROI according to the provided rectangle.

        Return True if ROI set correctly, False otherwise."""
        if self._transform[2]:
            roi = (top, left, height, width)
        else:
            roi = (left, top, width, height)
        return self._set_roi(*roi)

    @Pyro4.expose
    def get_trigger_type(self):
        """Return the current trigger mode.

        One of
            TRIGGER_AFTER,
            TRIGGER_BEFORE or
            TRIGGER_DURATION (bulb exposure.)
        """
        pass

    @Pyro4.expose
    def get_meta_data(self):
        """Return metadata."""
        pass

    @Pyro4.expose
    def soft_trigger(self):
        """Optional software trigger - implement if available."""
        pass


# === LaserDevice ===
class LaserDevice(Device):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        super(LaserDevice, self).__init__(*args, **kwargs)
        self.connection = None
        self._set_point = None

    def _read(self, num_chars):
        """Simple passthrough to read numChars from connection."""
        return self.connection.read(num_chars)

    def _readline(self):
        """Simple passthrough to read one line from connection."""
        return self.connection.readline().strip()

    def _write(self, command):
        """Send a command to the device."""
        # Override if a specific format is required.
        response = self.connection.write(command + '\r\n')
        return response

    @abc.abstractmethod
    def get_status(self):
        """Query and return the laser status."""
        result = []
        # ...
        return result

    @abc.abstractmethod
    def get_is_on(self):
        """Return True if the laser is currently able to produce light."""
        pass

    @abc.abstractmethod
    def get_max_power_mw(self):
        """Return the max. power in mW."""
        pass

    @abc.abstractmethod
    def get_power_mw(self):
        """"" Return the current power in mW."""
        pass

    @Pyro4.expose
    def get_set_power_mw(self):
        """Return the power set point."""
        return self._set_point

    @abc.abstractmethod
    def _set_power_mw(self, mw):
        """Set the power on the device in mW."""
        pass

    @Pyro4.expose
    def set_power_mw(self, mw):
        """Set the power from an argument in mW and save the set point."""
        self._set_point = mw
        self._set_power_mw(mw)

