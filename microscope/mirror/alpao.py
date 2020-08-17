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
import warnings

import numpy

import microscope
import microscope.abc

try:
    import microscope._wrappers.asdk as asdk
except Exception as e:
    raise microscope.LibraryLoadError(e) from e


class AlpaoDeformableMirror(microscope.abc.DeformableMirror):
    """Alpao deformable mirror.

    The Alpao mirrors support hardware triggers modes
    `TriggerMode.ONCE` and `TriggerMode.START`.  By default, they will
    be set for software triggering, and trigger once.
    """

    _TriggerType_to_asdkTriggerIn = {
        microscope.TriggerType.SOFTWARE: 0,
        microscope.TriggerType.RISING_EDGE: 1,
        microscope.TriggerType.FALLING_EDGE: 2,
    }

    _supported_TriggerModes = [
        microscope.TriggerMode.ONCE,
        microscope.TriggerMode.START,
    ]

    @staticmethod
    def _normalize_patterns(patterns: numpy.ndarray) -> numpy.ndarray:
        """
        Alpao SDK expects values in the [-1 1] range, so we normalize
        them from the [0 1] range we expect in our interface.
        """
        patterns = (patterns * 2) - 1
        return patterns

    def _find_error_str(self) -> str:
        """Get an error string from the Alpao SDK error stack.

        Returns
        -------
        A string.  Will be empty if there was no error on the stack.
        """
        err_msg_buffer_len = 64
        err_msg_buffer = ctypes.create_string_buffer(err_msg_buffer_len)

        err = ctypes.pointer(asdk.UInt(0))
        status = asdk.GetLastError(err, err_msg_buffer, err_msg_buffer_len)
        if status == asdk.SUCCESS:
            msg = err_msg_buffer.value
            if len(msg) > err_msg_buffer_len:
                msg = msg + b"..."
            msg += b" (error code %i)" % (err.contents.value)
            return msg.decode()
        else:
            return ""

    def _raise_if_error(
        self, status: int, exception_cls=microscope.DeviceError
    ) -> None:
        if status != asdk.SUCCESS:
            msg = self._find_error_str()
            if msg:
                raise exception_cls(msg)

    def __init__(self, serial_number: str, **kwargs) -> None:
        """
        Parameters
        ----------
        serial_number: string
        The serial number of the deformable mirror, something like "BIL103".
        """
        super().__init__(**kwargs)
        self._dm = asdk.Init(serial_number.encode())
        if not self._dm:
            raise microscope.InitialiseError(
                "Failed to initialise connection: don't know why"
            )
        # In theory, asdkInit should return a NULL pointer in case of
        # failure and that should be enough to check.  However, at least
        # in the case of a missing configuration file it still returns a
        # DM pointer so we still need to check for errors on the stack.
        self._raise_if_error(asdk.FAILURE)

        value = asdk.Scalar_p(asdk.Scalar())
        status = asdk.Get(self._dm, b"NbOfActuator", value)
        self._raise_if_error(status)
        self._n_actuators = int(value.contents.value)
        self._trigger_type = microscope.TriggerType.SOFTWARE
        self._trigger_mode = microscope.TriggerMode.ONCE

    @property
    def n_actuators(self) -> int:
        return self._n_actuators

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return self._trigger_mode

    @property
    def trigger_type(self) -> microscope.TriggerType:
        return self._trigger_type

    def _do_apply_pattern(self, pattern: numpy.ndarray) -> None:
        pattern = self._normalize_patterns(pattern)
        data_pointer = pattern.ctypes.data_as(asdk.Scalar_p)
        status = asdk.Send(self._dm, data_pointer)
        self._raise_if_error(status)

    def set_trigger(self, ttype, tmode):
        if tmode not in self._supported_TriggerModes:
            raise microscope.UnsupportedFeatureError(
                "unsupported trigger of mode '%s' for Alpao Mirrors"
                % tmode.name
            )
        elif (
            ttype == microscope.TriggerType.SOFTWARE
            and tmode != microscope.TriggerMode.ONCE
        ):
            raise microscope.UnsupportedFeatureError(
                "trigger mode '%s' only supports trigger type ONCE" % tmode.name
            )
        self._trigger_mode = tmode

        try:
            value = self._TriggerType_to_asdkTriggerIn[ttype]
        except KeyError:
            raise microscope.UnsupportedFeatureError(
                "unsupported trigger of type '%s' for Alpao Mirrors"
                % ttype.name
            )
        status = asdk.Set(self._dm, b"TriggerIn", value)
        self._raise_if_error(status)
        self._trigger_type = ttype

    def queue_patterns(self, patterns: numpy.ndarray) -> None:
        if self._trigger_type == microscope.TriggerType.SOFTWARE:
            super().queue_patterns(patterns)
            return

        self._validate_patterns(patterns)
        patterns = self._normalize_patterns(patterns)
        patterns = numpy.atleast_2d(patterns)
        n_patterns: int = patterns.shape[0]

        # The Alpao SDK seems to only support the trigger mode start.  It
        # still has option called nRepeats that we can't really figure
        # what is meant to do.  When set to 1, the mode is start.  What
        # we want it is to have trigger mode once which was not
        # supported.  We have received a modified version where if
        # nRepeats is set to same number of patterns, does trigger mode
        # once (not documented on Alpao SDK).
        if self._trigger_mode == microscope.TriggerMode.ONCE:
            n_repeats = n_patterns
        elif self._trigger_mode == microscope.TriggerMode.START:
            n_repeats = 1
        else:
            # We should not get here in the first place since
            # set_trigger filters unsupported modes.
            raise microscope.UnsupportedFeatureError(
                "trigger type '%s' and trigger mode '%s' is not supported"
                % (self._trigger_type.name, self._trigger_mode.name)
            )

        data_pointer = patterns.ctypes.data_as(asdk.Scalar_p)

        # We don't know if the previous queue of pattern ran until the
        # end, so we need to clear it before sending (see issue #50)
        status = asdk.Stop(self._dm)
        self._raise_if_error(status)

        status = asdk.SendPattern(self._dm, data_pointer, n_patterns, n_repeats)
        self._raise_if_error(status)

    def __del__(self):
        status = asdk.Release(self._dm)
        if status != asdk.SUCCESS:
            msg = self._find_error_str()
            warnings.warn(msg)
        super().__del__()
