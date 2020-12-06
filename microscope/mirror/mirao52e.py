#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 久保俊貴 <kubo@ap.eng.osaka-u.ac.jp>
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

"""Imagine Optic Mirao 52-e deformable mirror.

The Mirao 52-e deformable mirror is not capable of receiving hardware
triggers.  It is only capable of sending hardware triggers.  That
sending of hardware triggers is not implemented on this module because
it's pointless.

The Mirao 52-e deformable mirror has a limitation on valid patterns.
From the vendor documentation (the command is the pattern to be
applied):

    [...] the sum of the absolute values defining the command must be
    lower than or equal to 24 and each value must be comprised between
    -1.0 and 1.0.

In microscope, a pattern must be specified in the [0 1] range.
However, the limit of 24, after rescaling to [-1 1] range, still
applies.

"""

import ctypes
import typing

import numpy

import microscope
import microscope._utils
import microscope.abc


try:
    import microscope._wrappers.mirao52e as mro
except Exception as e:
    raise microscope.LibraryLoadError(e) from e


class Mirao52e(
    microscope._utils.OnlyTriggersOnceOnSoftwareMixin,
    microscope.abc.DeformableMirror,
):
    """Imagine Optic Mirao 52e deformable mirror.

    The Mirao 52e deformable mirrors only support software trigger.

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Status is not the return code of the function calls.
        # Status is where we can find the error code in case a
        # function call returns false.  This _status variable will be
        # an argument in all function calls.
        self._status = ctypes.pointer(ctypes.c_int(mro.OK))
        if not mro.open(self._status):
            raise microscope.InitialiseError(
                "failed to open mirao mirror (error code %d)"
                % self._status.contents.value
            )

    @property
    def n_actuators(self) -> int:
        return mro.NB_COMMAND_VALUES

    @staticmethod
    def _normalize_patterns(patterns: numpy.ndarray) -> numpy.ndarray:
        """
        mirao52e SDK expects values in the [-1 1] range, so we normalize
        them from the [0 1] range we expect in our interface.
        """
        patterns = (patterns * 2) - 1
        return patterns

    def _do_apply_pattern(self, pattern: numpy.ndarray) -> None:
        pattern = self._normalize_patterns(pattern)
        command = pattern.ctypes.data_as(mro.Command)
        if not mro.applyCommand(command, mro.FALSE, self._status):
            self._raise_status(mro.applyCommand)

    def _raise_status(self, func: typing.Callable) -> None:
        error_code = self._status.contents.value
        raise microscope.DeviceError(
            "mro_%s() failed (error code %d)" % (func.__name__, error_code)
        )

    def _do_shutdown(self) -> None:
        if not mro.close(self._status):
            self._raise_status(mro.close)
