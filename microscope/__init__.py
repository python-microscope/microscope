#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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

import enum
import typing


class MicroscopeError(Exception):
    """Base class for Python Microscope exceptions.
    """

    pass


class DeviceError(MicroscopeError):
    """Raised when there is an issue controlling a device.

    This exception is raised when there is an issue with controlling
    the device, be it with its programming interface or with the
    physical hardware.  It is most common when commands to the device
    fail or return something unexpected.

    .. note::

       The subclasses `DisabledDeviceError`, `IncompatibleStateError`,
       `InitialiseError`, and `UnsupportedFeatureError` provide more
       fine grained exceptions.

    """

    pass


class IncompatibleStateError(DeviceError):
    """Raised when an operation is incompatible with the current device
    state.

    This exception is raised when the device is in a state
    incompatible with an attempted operation, e.g., calling
    :mod:`TriggerTargetMixin.trigger` on a device that is set for
    hardware triggers.  The subclass `DisabledDeviceError` provides an
    exception specific to the case where the issue is the device being
    disabled.

    .. note::

       This exception is for attempting to perform some action but
       device is wrong state.  If the issue is about a setting that is
       incompatible with some other setting that this specific device
       does not support, then `UnsupportedFeatureError` should be
       raised.

    """

    pass


class DisabledDeviceError(IncompatibleStateError):
    """Raised when an operation requires an enabled device but the device is
    disabled.
    """

    pass


class InitialiseError(DeviceError):
    """Raised when a device fails to initialise.

    This exception is raised when there is a failure connecting to a
    device, typically because the device is not connected, or the serial
    number or port address is incorrect.

    """

    pass


class UnsupportedFeatureError(DeviceError):
    """Raised when some operation requires a feature that is not supported.

    This exception is raised when an operation requires some feature
    that is not supported, either because the physical device does not
    provide it, or Python Microscope has not yet implemented it.  For
    example, most devices do not support all trigger modes.

    """

    pass


class LibraryLoadError(MicroscopeError):
    """Raised when the loading and initialisation of a device library fails.

    This exception is raised when a shared library or DLL fails to load,
    typically because the required library is not found or is missing
    some required symbol.

    If there is a module that is a straight wrapper to the C library
    (there should be one on the `microscope._wrappers` package) then
    this exception can easily be used chained with the exception that
    originated it like so::

    .. code-block:: python

        try:
            import microscope._wrappers.libname
        except Exception as e:
            raise microscope.LibraryLoadError(e) from e

    """

    pass


class AxisLimits(typing.NamedTuple):
    """Limits of a :class:`microscope.abc.StageAxis`."""

    lower: float
    upper: float


class Binning(typing.NamedTuple):
    """A tuple containing parameters for horizontal and vertical binning. """

    h: int
    v: int


class ROI(typing.NamedTuple):
    """A tuple that defines a region of interest."""

    left: int
    top: int
    width: int
    height: int


class TriggerType(enum.Enum):
    """Type of a trigger for a :class:`microscope.abc.TriggerTargetMixin`.

    The trigger type defines what constitutes a trigger, as opposed to
    the trigger mode which defines a type of action when the trigger
    is received.

    :const:`TriggerType.SOFTWARE`
        when :meth:`microscope.abc.TriggerTargetMixin.trigger` is called
    :const:`TriggerType.RISING_EDGE`
        when level changes to high
    :const:`TriggerType.FALLING_EDGE`
        when level changes to low
    """

    SOFTWARE = 0
    RISING_EDGE = 1
    FALLING_EDGE = 2
    PULSE = 3


class TriggerMode(enum.Enum):
    """Mode of a trigger for a :class:`microscope.abc.TriggerTargetMixin`.

    The trigger mode defines what type of action when a trigger is
    received, as opposed to the trigger type which defines what
    constitutes a trigger.  The exact type of action is highly
    dependent on device type, so check their documentation.

    :const:`TriggerMode.ONCE`
        Act once.  For example, acquire a single image when a camera
        is triggered.
    :const:`TriggerMode.BULB`
        Act while device is being triggered.  For example, a laser
        keeps emitting emit light or a camera keeps exposing while the
        trigger line is high.  This trigger mode is incompatible with
        :attr:`TriggerType.SOFTWARE`.
    :const:`TriggerMode.STROBE`
        Act repeatably while device is being triggered.  For example,
        a camera keep acquiring multiple images while the trigger line
        is high.
    """

    ONCE = 1
    BULB = 2
    STROBE = 3
    START = 4
