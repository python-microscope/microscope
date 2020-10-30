#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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

"""Abstract Base Classes for the different device types.
"""

import abc
import functools
import itertools
import logging
import queue
import threading
import time
import typing
from ast import literal_eval
from collections import OrderedDict
from enum import EnumMeta
from threading import Thread

import numpy
import Pyro4

import microscope

_logger = logging.getLogger(__name__)


# Trigger types.
(TRIGGER_AFTER, TRIGGER_BEFORE, TRIGGER_DURATION, TRIGGER_SOFT) = range(4)

# Mapping of setting data types descriptors to allowed-value types.
#
# We use a descriptor for the type instead of the actual type because
# there may not be a unique proper type as for example in enum.
DTYPES = {
    "int": (tuple,),
    "float": (tuple,),
    "bool": (type(None),),
    "enum": (list, EnumMeta, dict, tuple),
    "str": (int,),
    "tuple": (type(None),),
}


def _call_if_callable(f):
    """Call callables, or return value of non-callables."""
    return f() if callable(f) else f


class _Setting:
    # TODO: refactor into subclasses to avoid if isinstance .. elif .. else.
    # Settings classes should be private: devices should use a factory method
    # rather than instantiate settings directly; most already use add_setting
    # for this.
    def __init__(
        self, name, dtype, get_func, set_func=None, values=None, readonly=False
    ):
        """Create a setting.

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

        Setters and getters accept or return:
            the setting value for int, float, bool and str;
            the setting index into a list, dict or Enum type for enum.
        """
        self.name = name
        if dtype not in DTYPES:
            raise ValueError("Unsupported dtype.")
        elif not (isinstance(values, DTYPES[dtype]) or callable(values)):
            raise TypeError(
                "Invalid values type for %s '%s': expected function or %s"
                % (dtype, name, DTYPES[dtype])
            )
        self.dtype = dtype
        self._get = get_func
        self._values = values
        self._readonly = readonly
        self._last_written = None
        if self._get is not None:
            self._set = set_func
        else:
            # Cache last written value for write-only settings.
            def w(value):
                self._last_written = value
                set_func(value)

            self._set = w

    def describe(self):
        return {
            "type": self.dtype,
            "values": self.values(),
            "readonly": self.readonly(),
            "cached": self._last_written is not None,
        }

    def get(self):
        if self._get is not None:
            value = self._get()
        else:
            value = self._last_written
        if isinstance(self._values, EnumMeta):
            return self._values(value).value
        else:
            return value

    def readonly(self):
        return _call_if_callable(self._readonly)

    def set(self, value):
        """Set a setting."""
        if self._set is None:
            raise NotImplementedError()
        # TODO further validation.
        if isinstance(self._values, EnumMeta):
            value = self._values(value)
        self._set(value)

    def values(self):
        if isinstance(self._values, EnumMeta):
            return [(v.value, v.name) for v in self._values]
        values = _call_if_callable(self._values)
        if values is not None:
            if self.dtype == "enum":
                if isinstance(values, dict):
                    return list(values.items())
                else:
                    # self._values is a list or tuple
                    return list(enumerate(values))
            elif self._values is not None:
                return values


class FloatingDeviceMixin(metaclass=abc.ABCMeta):
    """A mixin for devices that 'float'.

    Some SDKs handling multiple devices do not allow for explicit
    selection of a specific device: instead, a device must be
    initialized and then queried to determine its ID. This class is
    a mixin which identifies a subclass as floating, and enforces
    the implementation of a 'get_id' method.
    """

    @abc.abstractmethod
    def get_id(self):
        """Return a unique hardware identifier, such as a serial number."""
        pass


class Device(metaclass=abc.ABCMeta):
    """A base device class. All devices should subclass this class.

    Args:
        index (int): the index of the device on a shared library.
            This argument is added by the deviceserver.
    """

    def __init__(self, index=None):
        self.enabled = None
        # A list of settings. (Can't serialize OrderedDict, so use {}.)
        self._settings = OrderedDict()
        self._index = index

    def __del__(self):
        self.shutdown()

    def get_is_enabled(self):
        return self.enabled

    def _on_disable(self):
        """Do any device-specific work on disable.

        Subclasses should override this method, rather than modify
        disable(self).
        """
        return True

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

    def enable(self):
        """Enable the device."""
        try:
            self.enabled = self._on_enable()
        except Exception as err:
            _logger.debug("Error in _on_enable:", exc_info=err)

    @abc.abstractmethod
    def _on_shutdown(self):
        """Subclasses over-ride this with tasks to do on shutdown."""
        pass

    @abc.abstractmethod
    def initialize(self):
        """Initialize the device."""
        pass

    def shutdown(self):
        """Shutdown the device for a prolonged period of inactivity."""
        try:
            self.disable()
        except Exception as e:
            _logger.warning("Exception in disable() during shutdown: %s", e)
        _logger.info("Shutting down ... ... ...")
        self._on_shutdown()
        _logger.info("... ... ... ... shut down completed.")

    def make_safe(self):
        """Put the device into a safe state."""
        pass

    def add_setting(
        self, name, dtype, get_func, set_func, values, readonly=False
    ):
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
            raise ValueError("Unsupported dtype.")
        elif not (isinstance(values, DTYPES[dtype]) or callable(values)):
            raise TypeError(
                "Invalid values type for %s '%s': expected function or %s"
                % (dtype, name, DTYPES[dtype])
            )
        else:
            self._settings[name] = _Setting(
                name, dtype, get_func, set_func, values, readonly
            )

    def get_setting(self, name):
        """Return the current value of a setting."""
        try:
            return self._settings[name].get()
        except Exception as err:
            _logger.error("in get_setting(%s):", name, exc_info=err)
            raise

    def get_all_settings(self):
        """Return ordered settings as a list of dicts."""
        # Fetching some settings may fail depending on device state.
        # Report these values as 'None' and continue fetching other settings.
        def catch(f):
            try:
                return f()
            except Exception as err:
                _logger.error("getting %s: %s", f.__self__.name, err)
                return None

        return {k: catch(v.get) for k, v in self._settings.items()}

    def set_setting(self, name, value):
        """Set a setting."""
        try:
            self._settings[name].set(value)
        except Exception as err:
            _logger.error("in set_setting(%s):", name, exc_info=err)
            raise

    def describe_setting(self, name):
        """Return ordered setting descriptions as a list of dicts."""
        return self._settings[name].describe()

    def describe_settings(self):
        """Return ordered setting descriptions as a list of dicts."""
        return [(k, v.describe()) for (k, v) in self._settings.items()]

    def update_settings(self, incoming, init=False):
        """Update settings based on dict of settings and values."""
        if init:
            # Assume nothing about state: set everything.
            my_keys = set(self._settings.keys())
            their_keys = set(incoming.keys())
            update_keys = my_keys & their_keys
            if update_keys != my_keys:
                missing = ", ".join([k for k in my_keys - their_keys])
                msg = (
                    "update_settings init=True but missing keys: %s." % missing
                )
                _logger.debug(msg)
                raise Exception(msg)
        else:
            # Only update changed values.
            my_keys = set(self._settings.keys())
            their_keys = set(incoming.keys())
            update_keys = set(
                key
                for key in my_keys & their_keys
                if self.get_setting(key) != incoming[key]
            )
        results = {}
        # Update values.
        for key in update_keys:
            if key not in my_keys or not self._settings[key].set:
                # Setting not recognised or no set function implemented
                results[key] = NotImplemented
                update_keys.remove(key)
                continue
            if _call_if_callable(self._settings[key].readonly):
                continue
            self._settings[key].set(incoming[key])
        # Read back values in second loop.
        for key in update_keys:
            results[key] = self._settings[key].get()
        return results


def keep_acquiring(func):
    """Wrapper to preserve acquiring state of data capture devices."""

    def wrapper(self, *args, **kwargs):
        if self._acquiring:
            self.abort()
            result = func(self, *args, **kwargs)
            self._on_enable()
        else:
            result = func(self, *args, **kwargs)
        return result

    return wrapper


class DataDevice(Device, metaclass=abc.ABCMeta):
    """A data capture device.

    This class handles a thread to fetch data from a device and dispatch
    it to a client.  The client is set using set_client(uri) or (legacy)
    receiveClient(uri).

    Derived classed should implement::
      * abort(self)                ---  required
      * _fetch_data(self)          ---  required
      * _process_data(self, data)  ---  optional

    Derived classes may override __init__, enable and disable, but must
    ensure to call this class's implementations as indicated in the docstrings.
    """

    def __init__(self, buffer_length=0, **kwargs):
        """Derived.__init__ must call this at some point."""
        super().__init__(**kwargs)
        # A thread to fetch and dispatch data.
        self._fetch_thread = None
        # A flag to control the _fetch_thread.
        self._fetch_thread_run = False
        # A flag to indicate that this class uses a fetch callback.
        self._using_callback = False
        # Clients to which we send data.
        self._clientStack = []
        # A set of live clients to avoid repeated dispatch to disconnected client.
        self._liveClients = set()
        # A thread to dispatch data.
        self._dispatch_thread = None
        # A buffer for data dispatch.
        self._dispatch_buffer = queue.Queue(maxsize=buffer_length)
        # A flag to indicate if device is ready to acquire.
        self._acquiring = False
        # A condition to signal arrival of a new data and unblock grab_next_data
        self._new_data_condition = threading.Condition()

    def __del__(self):
        self.disable()
        super().__del__()

    # Wrap set_setting to pause and resume acquisition.
    set_setting = keep_acquiring(Device.set_setting)

    @abc.abstractmethod
    def abort(self):
        """Stop acquisition as soon as possible."""
        self._acquiring = False

    def enable(self):
        """Enable the data capture device.

        Ensures that a data handling threads are running.
        Implement device-specific code in _on_enable .
        """
        _logger.debug("Enabling ...")
        # Call device-specific code.
        try:
            result = self._on_enable()
        except Exception as err:
            _logger.debug("Error in _on_enable:", exc_info=err)
            self.enabled = False
            raise err
        if not result:
            self.enabled = False
        else:
            self.enabled = True
            # Set up data fetching
            if self._using_callback:
                if self._fetch_thread:
                    self._fetch_thread_run = False
            else:
                if not self._fetch_thread or not self._fetch_thread.is_alive():
                    self._fetch_thread = Thread(target=self._fetch_loop)
                    self._fetch_thread.daemon = True
                    self._fetch_thread.start()
            if (
                not self._dispatch_thread
                or not self._dispatch_thread.is_alive()
            ):
                self._dispatch_thread = Thread(target=self._dispatch_loop)
                self._dispatch_thread.daemon = True
                self._dispatch_thread.start()
            _logger.debug("... enabled.")
        return self.enabled

    def disable(self):
        """Disable the data capture device.

        Implement device-specific code in _on_disable ."""
        self.enabled = False
        if self._fetch_thread:
            if self._fetch_thread.is_alive():
                self._fetch_thread_run = False
                self._fetch_thread.join()
        super().disable()

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

    def _send_data(self, client, data, timestamp):
        """Dispatch data to the client."""
        try:
            # Currently uses legacy receiveData. Would like to pass
            # this function name as an argument to set_client, but
            # not sure how to subsequently resolve this over Pyro.
            client.receiveData(data, timestamp)
        except (
            Pyro4.errors.ConnectionClosedError,
            Pyro4.errors.CommunicationError,
        ):
            # Client not listening
            _logger.info(
                "Removing %s from client stack: disconnected.", client._pyroUri
            )
            self._clientStack = list(filter(client.__ne__, self._clientStack))
            self._liveClients = self._liveClients.difference([client])

    def _dispatch_loop(self):
        """Process data and send results to any client."""
        while True:
            client, data, timestamp = self._dispatch_buffer.get(block=True)
            if client not in self._liveClients:
                continue
            err = None
            if isinstance(data, Exception):
                standard_exception = Exception(str(data).encode("ascii"))
                try:
                    self._send_data(client, standard_exception, timestamp)
                except Exception as e:
                    err = e
            else:
                try:
                    self._send_data(client, self._process_data(data), timestamp)
                except Exception as e:
                    err = e
            if err:
                # Raising an exception will kill the dispatch loop. We need
                # another way to notify the client that there was a problem.
                _logger.error("in _dispatch_loop:", exc_info=err)
            self._dispatch_buffer.task_done()

    def _fetch_loop(self):
        """Poll source for data and put it into dispatch buffer."""
        self._fetch_thread_run = True

        while self._fetch_thread_run:
            try:
                data = self._fetch_data()
            except Exception as e:
                _logger.error("in _fetch_loop:", exc_info=e)
                # Raising an exception will kill the fetch loop. We need
                # another way to notify the client that there was a problem.
                timestamp = time.time()
                self._put(e, timestamp)
                data = None
            if data is not None:
                # TODO Add support for timestamp from hardware.
                timestamp = time.time()
                self._put(data, timestamp)
            else:
                time.sleep(0.001)

    @property
    def _client(self):
        """A getter for the current client."""
        return (self._clientStack or [None])[-1]

    @_client.setter
    def _client(self, val):
        """Push or pop a client from the _clientStack."""
        if val is None:
            self._clientStack.pop()
        else:
            self._clientStack.append(val)
        self._liveClients = set(self._clientStack)

    def _put(self, data, timestamp):
        """Put data and timestamp into dispatch buffer with target dispatch client."""
        self._dispatch_buffer.put((self._client, data, timestamp))

    def set_client(self, new_client):
        """Set up a connection to our client.

        Clients now sit in a stack so that a single device may send
        different data to multiple clients in a single experiment.
        The usage is currently::

            device.set_client(client) # Add client to top of stack
            # do stuff, send triggers, receive data
            device.set_client(None)   # Pop top client off stack.

        There is a risk that some other client calls ``None`` before
        the current client is finished.  Avoiding this will require
        rework here to identify the caller and remove only that caller
        from the client stack.
        """
        if new_client is not None:
            if isinstance(new_client, (str, Pyro4.core.URI)):
                self._client = Pyro4.Proxy(new_client)
            else:
                self._client = new_client
        else:
            self._client = None
        # _client uses a setter. Log the result of assignment.
        if self._client is None:
            _logger.info("Current client is None.")
        else:
            _logger.info("Current client is %s.", str(self._client))

    @keep_acquiring
    def update_settings(self, settings, init=False):
        """Update settings, toggling acquisition if necessary."""
        super().update_settings(settings, init)

    # noinspection PyPep8Naming
    def receiveClient(self, client_uri):
        """A passthrough for compatibility."""
        self.set_client(client_uri)

    def grab_next_data(self, soft_trigger=True):
        """Returns results from next trigger via a direct call.

        :param soft_trigger: calls soft_trigger if True,
                               waits for hardware trigger if False.
        """
        if not self.enabled:
            raise microscope.DisabledDeviceError("Camera not enabled.")
        self._new_data_condition.acquire()
        # Push self onto client stack.
        self.set_client(self)
        # Wait for data from next trigger.
        if soft_trigger:
            self.soft_trigger()
        self._new_data_condition.wait()
        # Pop self from client stack
        self.set_client(None)
        # Return the data.
        return self._new_data

    # noinspection PyPep8Naming
    def receiveData(self, data, timestamp):
        """Unblocks grab_next_frame so it can return."""
        with self._new_data_condition:
            self._new_data = (data, timestamp)
            self._new_data_condition.notify()


class Camera(DataDevice):
    """Adds functionality to DataDevice to support cameras.

    Defines the interface for cameras.
    Applies a transform to acquired data in the processing step.
    """

    ALLOWED_TRANSFORMS = [p for p in itertools.product(*3 * [[False, True]])]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # A list of readout mode descriptions.
        self._readout_modes = ["default"]
        # The index of the current readout mode.
        self._readout_mode = 0
        # Transforms to apply to data (fliplr, flipud, rot90)
        # Transform to correct for readout order.
        self._readout_transform = (False, False, False)
        # Transform supplied by client to correct for system geometry.
        self._client_transform = (False, False, False)
        # Result of combining client and readout transforms
        self._transform = (False, False, False)
        # A transform provided by the client.
        self.add_setting(
            "transform",
            "enum",
            lambda: Camera.ALLOWED_TRANSFORMS.index(self._transform),
            lambda index: self.set_transform(Camera.ALLOWED_TRANSFORMS[index]),
            Camera.ALLOWED_TRANSFORMS,
        )
        self.add_setting(
            "readout mode",
            "enum",
            lambda: self._readout_mode,
            self.set_readout_mode,
            lambda: self._readout_modes,
        )
        self.add_setting("roi", "tuple", self.get_roi, self.set_roi, None)

    def _process_data(self, data):
        """Apply self._transform to data."""
        flips = (self._transform[0], self._transform[1])
        rot = self._transform[2]

        # Choose appropriate transform based on (flips, rot).
        # Do rotation
        data = numpy.rot90(data, rot)
        # Flip
        data = {
            (0, 0): lambda d: d,
            (0, 1): numpy.flipud,
            (1, 0): numpy.fliplr,
            (1, 1): lambda d: numpy.fliplr(numpy.flipud(d)),
        }[flips](data)
        return super()._process_data(data)

    def set_readout_mode(self, description):
        """Set the readout mode and _readout_transform."""
        pass

    def get_transform(self):
        """Return the current transform without readout transform."""
        return self._client_transform

    def set_transform(self, transform):
        """Combine provided transform with readout transform."""
        if isinstance(transform, str):
            transform = literal_eval(transform)
        self._client_transform = transform
        lr, ud, rot = (
            self._readout_transform[i] ^ transform[i] for i in range(3)
        )
        if self._readout_transform[2] and self._client_transform[2]:
            lr = not lr
            ud = not ud
        self._transform = (lr, ud, rot)

    def _set_readout_transform(self, new_transform):
        """Update readout transform and update resultant transform."""
        self._readout_transform = [bool(int(t)) for t in new_transform]
        self.set_transform(self._client_transform)

    @abc.abstractmethod
    def set_exposure_time(self, value):
        """Set the exposure time on the device.

        :param value: exposure time in seconds
        """
        pass

    def get_exposure_time(self):
        """Return the current exposure time, in seconds."""
        pass

    def get_cycle_time(self):
        """Return the cycle time, in seconds."""
        pass

    def get_sensor_temperature(self):
        """Return the sensor temperature."""
        pass

    @abc.abstractmethod
    def _get_sensor_shape(self):
        """Return a tuple of (width, height) indicating shape in pixels."""
        pass

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

    def get_binning(self):
        """Return a tuple of (horizontal, vertical) corrected for transform."""
        binning = self._get_binning()
        if self._transform[2]:
            # 90 degree rotation
            binning = (binning[1], binning[0])
        return binning

    @abc.abstractmethod
    def _set_binning(self, binning):
        """Set binning along both axes. Return True if successful."""
        pass

    def set_binning(self, binning):
        """Set binning along both axes. Return True if successful."""
        h_bin, v_bin = binning
        if self._transform[2]:
            # 90 degree rotation
            binning = microscope.Binning(v_bin, h_bin)
        else:
            binning = microscope.Binning(h_bin, v_bin)
        return self._set_binning(binning)

    @abc.abstractmethod
    def _get_roi(self):
        """Return the ROI as it is on hardware."""
        raise NotImplementedError()

    def get_roi(self):
        """Return ROI as a rectangle (left, top, width, height).

        Chosen this rectangle format as it completely defines the ROI without
        reference to the sensor geometry."""
        roi = self._get_roi()
        if self._transform[2]:
            # 90 degree rotation
            roi = microscope.ROI(roi[1], roi[0], roi[3], roi[2])
        return roi

    @abc.abstractmethod
    def _set_roi(self, roi):
        """Set the ROI on the hardware, return True if successful."""
        return False

    def set_roi(self, roi):
        """Set the ROI according to the provided rectangle.
        ROI is a tuple (left, right, width, height)
        Return True if ROI set correctly, False otherwise."""
        maxw, maxh = self.get_sensor_shape()
        binning = self.get_binning()
        left, top, width, height = roi
        if not width:  # 0 or None
            width = maxw // binning.h
        if not height:  # 0 or None
            height = maxh // binning.v
        if self._transform[2]:
            roi = microscope.ROI(left, top, height, width)
        else:
            roi = microscope.ROI(left, top, width, height)
        return self._set_roi(roi)

    def get_trigger_type(self):
        """Return the current trigger mode.

        One of
            TRIGGER_AFTER,
            TRIGGER_BEFORE or
            TRIGGER_DURATION (bulb exposure.)
        """
        pass

    def get_meta_data(self):
        """Return metadata."""
        pass

    def soft_trigger(self):
        """Optional software trigger - implement if available."""
        pass


class TriggerTargetMixin(metaclass=abc.ABCMeta):
    """Mixin for a device that may be the target of a hardware trigger.

    TODO: need some way to retrieve the supported trigger types and
        modes.  This is not just two lists, one for types and another
        for modes, because some modes can only be used with certain
        types and vice-versa.

    """

    @property
    @abc.abstractmethod
    def trigger_mode(self) -> microscope.TriggerMode:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def trigger_type(self) -> microscope.TriggerType:
        raise NotImplementedError()

    @abc.abstractmethod
    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        """Set device for a specific trigger.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _do_trigger(self) -> None:
        """Actual trigger of the device.

        Classes implementing this interface should implement this
        method instead of `trigger`.

        """
        raise NotImplementedError()

    def trigger(self) -> None:
        """Trigger device.

        The actual effect is device type dependent.  For example, on a
        `Camera` it triggers image acquisition while on a
        `DeformableMirror` it applies a queued pattern.  See
        documentation for the devices implementing this interface for
        details.

        Raises:
            microscope.IncompatibleStateError: if trigger type is not
                set to `TriggerType.SOFTWARE`.

        """
        if self.trigger_type is not microscope.TriggerType.SOFTWARE:
            raise microscope.IncompatibleStateError(
                "trigger type is not software"
            )
        _logger.debug("trigger by software")
        self._do_trigger()


class SerialDeviceMixin(metaclass=abc.ABCMeta):
    """Mixin for devices that are controlled via serial.

    Currently handles the flushing and locking of the comms channel
    until a command has finished, and the passthrough to the serial
    channel.

    TODO: add more logic to handle the code duplication of serial
    devices.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # TODO: We should probably construct the connection here but
        #       the Serial constructor takes a lot of arguments, and
        #       it becomes tricky to separate those from arguments to
        #       the constructor of other parent classes.
        self.connection = None  # serial.Serial (to be constructed by child)
        self._comms_lock = threading.RLock()

    def _readline(self):
        """Read a line from connection without leading and trailing whitespace.
        """
        return self.connection.readline().strip()

    def _write(self, command):
        """Send a command to the device.

        This is not a simple passthrough to ``serial.Serial.write``,
        it will append ``b'\\r\\n'`` to command.  Override this method
        if a device requires a specific format.
        """
        return self.connection.write(command + b"\r\n")

    @abc.abstractmethod
    def is_alive(self):
        """Query if device is alive and we can send messages."""
        pass

    @staticmethod
    def lock_comms(func):
        """Decorator to flush input buffer and lock communications.

        There have been problems with the DeepStar lasers returning
        junk characters after the expected response, so it is
        advisable to flush the input buffer prior to running a command
        and subsequent readline.  It also locks the comms channel so
        that a function must finish all its communications before
        another can run.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with self._comms_lock:
                self.connection.flushInput()
                return func(self, *args, **kwargs)

        return wrapper


class DeformableMirror(TriggerTargetMixin, Device, metaclass=abc.ABCMeta):
    """Base class for Deformable Mirrors.

    There is no method to reset or clear a deformable mirror.  While
    different vendors provide functions to do that, it is unclear
    exactly what it does the actuators.  Does it set all actuators
    back to something based on a calibration file?  Does it apply a
    voltage of zero to each?  Does it set the values to zero and what
    does that mean since different deformable mirrors expect values in
    a different range?  For the sake of uniformity, it is better for
    python-microscope users to pass the pattern they want, probably a
    pattern that flattens the mirror.

    It is also unclear what the use case for a reset.  If it just to
    set the mirror to an initial state and not a specific shape, then
    destroying and re-constructing the DeformableMirror object
    provides the most obvious solution.
    """

    @abc.abstractmethod
    def __init__(self, **kwargs) -> None:
        """Constructor.

        The private properties `_patterns` and `_pattern_idx` are
        initialized to `None` to support the queueing of patterns and
        software triggering.
        """
        super().__init__(**kwargs)

        self._patterns: typing.Optional[numpy.ndarray] = None
        self._pattern_idx: int = -1

    @property
    @abc.abstractmethod
    def n_actuators(self) -> int:
        raise NotImplementedError()

    def _validate_patterns(self, patterns: numpy.ndarray) -> None:
        """Validate the shape of a series of patterns.

        Only validates the shape of the patterns, not if the values
        are actually in the [0 1] range.  If some hardware is unable
        to handle values outside their defined range (most will simply
        clip them), then it's the responsability of the subclass to do
        the clipping before sending the values.
        """
        if patterns.ndim > 2:
            raise ValueError(
                "PATTERNS has %d dimensions (must be 1 or 2)" % patterns.ndim
            )
        elif patterns.shape[-1] != self.n_actuators:
            raise ValueError(
                (
                    "PATTERNS length of second dimension '%d' differs"
                    " from number of actuators '%d'"
                    % (patterns.shape[-1], self.n_actuators)
                )
            )

    @abc.abstractmethod
    def _do_apply_pattern(self, pattern: numpy.ndarray) -> None:
        raise NotImplementedError()

    def apply_pattern(self, pattern: numpy.ndarray) -> None:
        """Apply this pattern.

        Raises:
            microscope.IncompatibleStateError: if device trigger type is
            not set to software.

        """
        if self.trigger_type is not microscope.TriggerType.SOFTWARE:
            # An alternative to error is to change the trigger type,
            # apply the pattern, then restore the trigger type, but
            # that would clear the queue on the device.  It's better
            # to have the user specifically do it.  See issue #61.
            raise microscope.IncompatibleStateError(
                "apply_pattern requires software trigger type"
            )
        self._validate_patterns(pattern)
        self._do_apply_pattern(pattern)

    def queue_patterns(self, patterns: numpy.ndarray) -> None:
        """Send values to the mirror.

        Parameters
        ----------
        patterns : numpy.array
            An KxN elements array of values in the range [0 1], where N
            equals the number of actuators, and K is the number of
            patterns.

        A convenience fallback is provided for software triggering is
        provided.
        """
        self._validate_patterns(patterns)
        self._patterns = patterns
        self._pattern_idx = -1  # none is applied yet

    def next_pattern(self) -> None:
        """Apply the next pattern in the queue.

        DEPRECATED: this is the same as calling :meth:`trigger`.
        """
        self.trigger()

    def initialize(self) -> None:
        pass

    def _on_shutdown(self) -> None:
        pass

    def _do_trigger(self) -> None:
        """Convenience fallback.

        This only provides a convenience fallback for devices that
        don't support queuing multiple patterns and software trigger,
        i.e., devices that take only one pattern at a time.  This is
        not the case of most devices.

        Devices that support queuing patterns, should override this
        method.

        .. todo:: instead of a convenience fallback, we should have a
           separate mixin for this.
        """
        if self._patterns is None:
            raise microscope.DeviceError("no pattern queued to apply")
        self._pattern_idx += 1
        self.apply_pattern(self._patterns[self._pattern_idx, :])

    def trigger(self) -> None:
        """Apply the next pattern in the queue."""
        # This is just a passthrough to the TriggerTargetMixin class
        # and only exists for the docstring.
        return super().trigger()


class LightSource(Device, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._set_point = 0.0

    @abc.abstractmethod
    def get_status(self):
        """Query and return the light source status."""
        result = []
        # ...
        return result

    @abc.abstractmethod
    def get_is_on(self):
        """Return True if the light source is currently able to produce light."""
        pass

    @abc.abstractmethod
    def _do_get_power(self) -> float:
        """Internal function that actually returns the light source power."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _do_set_power(self, power: float) -> None:
        """Internal function that actually sets the light source power.

        This function will be called by the `power` attribute setter
        after clipping the argument to the [0, 1] interval.
        """
        raise NotImplementedError()

    @property
    def power(self) -> float:
        """Light source power in the [0, 1] interval."""
        return self._do_get_power()

    @power.setter
    def power(self, power: float) -> None:
        """Light source power in the [0, 1] interval.

        The power value will be clipped to [0, 1] interval.
        """
        clipped_power = max(min(power, 1.0), 0.0)
        self._do_set_power(clipped_power)
        self._set_point = clipped_power

    def get_set_power(self) -> float:
        """Return the power set point."""
        return self._set_point


class FilterWheel(Device, metaclass=abc.ABCMeta):
    def __init__(self, positions: int, **kwargs) -> None:
        super().__init__(**kwargs)
        if positions < 1:
            raise ValueError(
                "positions must be a positive number (was %d)" % positions
            )
        self._positions = positions
        # The position as an integer.
        # Deprecated: clients should call get_position and set_position;
        # still exposed as a setting until cockpit uses set_position.
        self.add_setting(
            "position",
            "int",
            self.get_position,
            self.set_position,
            lambda: (0, self.get_num_positions()),
        )

    @property
    def n_positions(self) -> int:
        """Number of wheel positions."""
        return self._positions

    @property
    def position(self) -> int:
        """Number of wheel positions (zero-based)."""
        return self._do_get_position()

    @position.setter
    def position(self, new_position: int) -> None:
        if 0 <= new_position < self.n_positions:
            return self._do_set_position(new_position)
        else:
            raise ValueError(
                "can't move to position %d, limits are [0 %d]"
                % (new_position, self.n_positions - 1)
            )

    @abc.abstractmethod
    def _do_get_position(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def _do_set_position(self, position: int) -> None:
        raise NotImplementedError()

    # Deprecated and kept for backwards compatibility.
    def get_num_positions(self) -> int:
        return self.n_positions

    def get_position(self) -> int:
        return self.position

    def set_position(self, position: int) -> None:
        self.position = position


class Controller(Device, metaclass=abc.ABCMeta):
    """Device that controls multiple devices.

    Controller devices usually control multiple stage devices,
    typically a XY and Z stage, a filterwheel, and a light source.
    Controller devices also include multi light source engines.

    Each of the controlled devices requires a name.  The choice of
    name and its documentation is left to the concrete class.

    Initialising and shutting down a controller device must initialise
    and shutdown the controlled devices.  Concrete classes should be
    careful to prevent that the shutdown of a controlled device does
    not shutdown the controller and the other controlled devices.
    This might require that controlled devices do nothing as part of
    their shutdown and initialisation.

    """

    def initialize(self) -> None:
        super().initialize()
        for d in self.devices.values():
            d.initialize()

    @property
    @abc.abstractmethod
    def devices(self) -> typing.Mapping[str, Device]:
        """Map of names to the controlled devices."""
        raise NotImplementedError()

    def _on_shutdown(self) -> None:
        for d in self.devices.values():
            d.shutdown()
        super()._on_shutdown()


class StageAxis(metaclass=abc.ABCMeta):
    """A single dimension axis for a :class:`StageDevice`.

    A `StageAxis` represents a single axis of a stage and is not a
    :class:`Device` instance on itself.  Even stages with a single
    axis, such as Z-axis piezos, are implemented as a `StageDevice`
    composed of a single `StageAxis` instance.

    The interface for `StageAxis` maps to that of `StageDevice` so
    refer to its documentation.

    """

    @abc.abstractmethod
    def move_by(self, delta: float) -> None:
        """Move axis by given amount."""
        raise NotImplementedError()

    @abc.abstractmethod
    def move_to(self, pos: float) -> None:
        """Move axis to specified position."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def position(self) -> float:
        """Current axis position."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def limits(self) -> microscope.AxisLimits:
        """Upper and lower limits values for position."""
        raise NotImplementedError()


class Stage(Device, metaclass=abc.ABCMeta):
    """A stage device, composed of :class:`StageAxis` instances.

    A stage device can have any number of axes and dimensions.  For a
    single `StageDevice` instance each axis has a name that uniquely
    identifies it.  The names of the individual axes are hardware
    dependent and will be part of the concrete class documentation.
    They are typically strings such as `"x"` or `"y"`.

    .. code-block:: python

        stage = SomeStageDevice()
        stage.initialize()
        stage.enable() # may trigger a stage move

        # move operations
        stage.move_to({'x': 42.0, 'y': -5.1})
        stage.move_by({'x': -5.3, 'y': 14.6})

        # Individual StageAxis can be controlled directly.
        x_axis = stage.axes['x']
        y_axis = stage.axes['y']
        x_axis.move_to(42.0)
        y_axis.move_by(-5.3)

    Not all stage devices support simultaneous move of multiple axes.
    Because of this, there is no guarantee that move operations with
    multiple axes are done simultaneously.  Refer to the concrete
    class documentation for hardware specific details.

    If a move operation involves multiple axes and there is no support
    for simultaneous move, the order of the moves is undefined.  If a
    specific order is required, one can either call the move functions
    multiple times in the expected order, or do so via the individual
    axes, like so:

    .. code-block:: python

        # Move the x axis first, then mvoe the y axis:
        stage.move_by({'x': 10})
        stage.move_by({'y': 4})

        # The same thing but via the individual axes:
        stage.axes['x'].move_by(10)
        stage.axes['y'].move_by(4)

    Move operations will not attempt to move a stage beyond its
    limits.  If a call to the move functions would require the stage
    to move beyond its limits the move operation is clipped to the
    axes limits.  No exception is raised.

    .. code-block:: python

        # Moves x axis to the its upper limit:
        x_axis.move_to(x_axis.limits.upper)

        # The same as above since the move operations are clipped to
        # the axes limits automatically.
        import math
        x_axis.move_to(math.inf)
        x_axis.move_by(math.inf)

    Some stages need to find a reference position, home, before being
    able to be moved.  If required, this happens automatically during
    :func:`enable`.

    """

    @property
    @abc.abstractmethod
    def axes(self) -> typing.Mapping[str, StageAxis]:
        """Map of axis names to the corresponding :class:`StageAxis`.

        .. code-block:: python

            for name, axis in stage.axes.items():
                print(f'moving axis named {name}')
                axis.move_by(1)

        If an axis is not available then it is not included, i.e.,
        given a stage with optional axes the missing axes will *not*
        appear on the returned dict with a value of `None` or some
        other special `StageAxis` instance.

        """
        raise NotImplementedError()

    @property
    def position(self) -> typing.Mapping[str, float]:
        """Map of axis name to their current position.

        .. code-block:: python

            for name, position in stage.position.items():
                print(f'{name} axis is at position {position}')

        The units of the position is the same as the ones being
        currently used for the absolute move (:func:`move_to`)
        operations.

        """
        return {name: axis.position for name, axis in self.axes.items()}

    @property
    def limits(self) -> typing.Mapping[str, microscope.AxisLimits]:
        """Map of axis name to its upper and lower limits.

        .. code-block:: python

            for name, limits in stage.limits.items():
                print(f'{name} axis lower limit is {limits.lower}')
                print(f'{name} axis upper limit is {limits.upper}')

        These are the limits currently imposed by the device or
        underlying software and may change over the time of the
        `StageDevice` object.

        The units of the limits is the same as the ones being
        currently used for the move operations.

        """
        return {name: axis.limits for name, axis in self.axes.items()}

    @abc.abstractmethod
    def move_by(self, delta: typing.Mapping[str, float]) -> None:
        """Move axes by the corresponding amounts.

        Args:
            delta: map of axis name to the amount to be moved.

        .. code-block:: python

            # Move 'x' axis by 10.2 units and the y axis by -5 units:
            stage.move_by({'x': 10.2, 'y': -5})

            # The above is equivalent, but possibly faster than:
            stage.axes['x'].move_by(10.2)
            stage.axes['y'].move_by(-5)

        The axes will not move beyond :func:`limits`.  If `delta`
        would move an axis beyond it limit, no exception is raised.
        Instead, the stage will move until the axis limit.

        """
        # TODO: implement a software fallback that moves the
        # individual axis, for stages that don't have provide
        # simultaneous move of multiple axes.
        raise NotImplementedError()

    @abc.abstractmethod
    def move_to(self, position: typing.Mapping[str, float]) -> None:
        """Move axes to the corresponding positions.

        Args:
            position: map of axis name to the positions to move to.

        .. code-block:: python

            # Move 'x' axis to position 8 and the y axis to position -5.3
            stage.move_to({'x': 8, 'y': -5.3})

            # The above is equivalent to
            stage.axes['x'].move_to(8)
            stage.axes['y'].move_to(-5.3)

        The axes will not move beyond :func:`limits`.  If `positions`
        is beyond the limits, no exception is raised.  Instead, the
        stage will move until the axes limit.

        """
        raise NotImplementedError()
