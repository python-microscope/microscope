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

import ctypes
import os
import sys
import threading
import typing

import serial

import microscope
import microscope.abc


# Both pySerial and serial distribution packages install an import
# package named serial.  If both are installed we may have imported
# the wrong one.  Check it to provide a better error message.  See
# issue #232.
if not hasattr(serial, "Serial"):
    if hasattr(serial, "marshall"):
        raise microscope.MicroscopeError(
            "incorrect imported package serial.  It appears that the serial"
            " package from the distribution serial, instead of pyserial, was"
            " imported.  Consider uninstalling serial and installing pySerial."
        )
    else:
        raise microscope.MicroscopeError(
            "imported package serial does not have Serial class"
        )


def library_loader(
    libname: str, dlltype: typing.Type[ctypes.CDLL] = ctypes.CDLL, **kwargs
) -> ctypes.CDLL:
    """Load shared library.

    This exists mainly to search for DLL in Windows using a standard
    search path, i.e, search for dlls in ``PATH``.

    Args:
        libname: file name or path of the library to be loaded as
            required by `dlltype`
        dlltype: the class of shared library to load.  Typically,
            `ctypes.CDLL` but sometimes `ctypes.WinDLL` in windows.
        kwargs: other arguments passed on to `dlltype`.
    """
    # Python 3.8 in Windows uses an altered search path.  Their
    # reasons is security and I guess it would make sense if we
    # installed the DLLs we need ourselves but we don't.  `winmode=0`
    # restores the use of the standard search path.  See issue #235.
    if (
        os.name == "nt"
        and sys.version_info >= (3, 8)
        and "winmode" not in kwargs
    ):
        winmode_kwargs = {"winmode": 0}
    else:
        winmode_kwargs = {}
    return dlltype(libname, **winmode_kwargs, **kwargs)


class OnlyTriggersOnceOnSoftwareMixin(microscope.abc.TriggerTargetMixin):
    """Utility mixin for devices that only trigger "once" with software.

    This mixin avoids code duplication for the many devices whose only
    supported trigger type and trigger mode are `TriggerType.SOFTWARE`
    and `TriggerMode.ONCE`.

    """

    @property
    def trigger_type(self) -> microscope.TriggerType:
        return microscope.TriggerType.SOFTWARE

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return microscope.TriggerMode.ONCE

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if ttype is not microscope.TriggerType.SOFTWARE:
            raise microscope.UnsupportedFeatureError(
                "the only trigger type supported is software"
            )
        if tmode is not microscope.TriggerMode.ONCE:
            raise microscope.UnsupportedFeatureError(
                "the only trigger mode supported is 'once'"
            )


class OnlyTriggersBulbOnSoftwareMixin(microscope.abc.TriggerTargetMixin):
    """Utility mixin for devices that only trigger "bulb" with software.

    This mixin avoids code duplication for the many devices whose only
    supported trigger type and trigger mode are `TriggerType.SOFTWARE`
    and `TriggerMode.BULB`.

    """

    @property
    def trigger_type(self) -> microscope.TriggerType:
        return microscope.TriggerType.SOFTWARE

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return microscope.TriggerMode.BULB

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if ttype is not microscope.TriggerType.SOFTWARE:
            raise microscope.UnsupportedFeatureError(
                "the only trigger type supported is software"
            )
        if tmode is not microscope.TriggerMode.BULB:
            raise microscope.UnsupportedFeatureError(
                "the only trigger mode supported is 'bulb'"
            )

    def _do_trigger(self) -> None:
        raise microscope.IncompatibleStateError(
            "trigger does not make sense in trigger mode bulb, only enable"
        )


class SharedSerial:
    """Wraps a `Serial` instance with a lock for synchronization."""

    def __init__(self, serial: serial.Serial) -> None:
        self._serial = serial
        self._lock = threading.RLock()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def readline(self) -> bytes:
        with self._lock:
            return self._serial.readline()

    def readlines(self, hint: int = -1) -> typing.List[bytes]:
        with self._lock:
            return self._serial.readlines(hint)

    # Beware: pySerial 3.5 changed the named of its first argument
    # from terminator to expected.  See issue #233.
    def read_until(
        self, terminator: bytes = b"\n", size: typing.Optional[int] = None
    ) -> bytes:
        with self._lock:
            return self._serial.read_until(terminator, size=size)

    def write(self, data: bytes) -> int:
        with self._lock:
            return self._serial.write(data)
