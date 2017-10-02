#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>
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

import microscope.devices
import microscope.sdk.bmc as BMC

class BMCDeformableMirror(microscope.devices.DeformableMirror):
  def __init__(self, serial_number, *args, **kwargs):
    super(BMCDeformableMirror, self).__init__()
    self._dm = BMC.DM()
    BMC.ConfigureLog(os.devnull, BMC.LOG_OFF)
    status = BMC.Open(self._dm, serial_number.encode("utf-8"))
    if status:
      msg = BMC.ErrorString(status)
      raise Exception(msg)

  def initialize(self):
    pass
  def _on_shutdown(self):
    pass

  def get_n_actuators(self):
    return self._dm.ActCount

  def send(self, values):
    if values.size != self.get_n_actuators():
      raise Exception("not right size")
    data_pointer = values.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    status = BMC.SetArray(self._dm, data_pointer, None)
    if status:
      msg = BMC.ErrorString(status)
      raise Exception(msg)

  def reset(self):
    BMC.ClearArray(self._dm)
    return

  def __del__(self):
    BMC.Close(self._dm)
    super(BMCDeformableMirror, self).__del__()
