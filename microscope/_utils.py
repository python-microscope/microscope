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

import threading
import typing

import serial

import microscope
import microscope.abc


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

    def read_until(
        self, terminator: bytes = b"\n", size: typing.Optional[int] = None
    ) -> bytes:
        with self._lock:
            return self._serial.read_until(terminator=terminator, size=size)

    def write(self, data: bytes) -> int:
        with self._lock:
            return self._serial.write(data)
