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

"""Boston MicroMachines Corporation deformable mirrors.
"""

import ctypes
import os
import warnings

import numpy

import microscope
import microscope._utils
import microscope.abc


try:
    import microscope._wrappers.BMC as BMC
except Exception as e:
    raise microscope.LibraryLoadError(e) from e


class BMCDeformableMirror(
    microscope._utils.OnlyTriggersOnceOnSoftwareMixin,
    microscope.abc.DeformableMirror,
):
    """Boston MicroMachines (BMC) deformable mirror.

    BMC deformable mirrors only support software trigger.
    """

    def __init__(self, serial_number: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dm = BMC.DM()

        if __debug__:
            BMC.ConfigureLog(os.devnull.encode(), BMC.LOG_ALL)
        else:
            BMC.ConfigureLog(os.devnull.encode(), BMC.LOG_OFF)

        status = BMC.Open(self._dm, serial_number.encode())
        if status:
            raise microscope.InitialiseError(BMC.ErrorString(status))

    @property
    def n_actuators(self) -> int:
        return self._dm.ActCount

    def _do_apply_pattern(self, pattern: numpy.ndarray) -> None:
        data_pointer = pattern.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        status = BMC.SetArray(self._dm, data_pointer, None)
        if status:
            raise microscope.DeviceError(BMC.ErrorString(status))

    def _do_shutdown(self) -> None:
        status = BMC.Close(self._dm)
        if status:
            warnings.warn(BMC.ErrorString(status), RuntimeWarning)
