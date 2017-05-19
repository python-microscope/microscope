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

"""Class for Alpao deformable mirror.

Exceptions:
  May throw an OSError during import if the alpao SDK is not available.
"""
import ctypes
import sys

#import microscope.devices

if sys.platform == "win32":
  _SDK = ctypes.windll.ASDK # throws OSError if missing
else:
  raise NotImplementedError("alpao module not yet tested for non windows")

_COMPL_STAT = ctypes.c_int # an enum type
_CStr = ctypes.c_char_p
_Scalar = ctypes.c_double
_UInt = ctypes.c_uint32
_Size_T = ctypes.c_size_t

class _asdkDM(ctypes.Structure):
  pass

## Values for COMPL_STAT enum hardcoded because enum values are not
## exported by ctypes.
_SUCCESS = 0
_FAILURE = -1

_SDK.asdkInit.restype = ctypes.POINTER(_asdkDM)
_SDK.asdkInit.argtypes = [_CStr]

_SDK.asdkRelease.restype = _COMPL_STAT
_SDK.asdkRelease.argtypes = [ctypes.POINTER(_asdkDM)]

_SDK.asdkGet.restype = _COMPL_STAT
_SDK.asdkGet.argtypes = [ctypes.POINTER(_asdkDM), _CStr,
                         ctypes.POINTER(_Scalar)]

_SDK.asdkGetLastError.restype = _COMPL_STAT
_SDK.asdkGetLastError.argtypes = [ctypes.POINTER(_UInt),
                                  ctypes.POINTER(_CStr), _Size_T]


class _DM(object):
  """Wraps the Alpao C interface into a class.

  This is pretty much a Python implementation of the C++ acs::DM class
  from Alpao's SDK.

  Maybe this class is pointless and we could make the calls to the C
  functions directly on the DeformableMirror class.
  """

  def __init__(self, serial_number):
    self._dm = _SDK.asdkInit(serial_number.encode("utf-8"))
    if not self._dm:
      raise Exception("Failed to initialise connection: don't know why")
    ## In theory, asdkInit should return a NULL pointer in case of
    ## failure.  However, at least in the case of a missing
    ## configuration file it still returns a DM pointer so we check if
    ## there's any error on the stack.  But maybe there are
    ## initialisation errors that do make it return a NULL pointer so
    ## we check both.
    err = ctypes.pointer(_UInt(0))
    msg_len = 64 # should be enough
    msg = ctypes.create_string_buffer(msg_len) ## FIXME (msg is wrong)
    status = _SDK.asdkGetLastError(err, msg, msg_len)
    if status == _SUCCESS:
      msg = msg.value
      if len(msg) > msg_len:
        msg = msg + "..."
      raise Exception("Failed to initialise connection: %s (error %i)"
                      % (msg, err.value))

  # def send(self, values, n_repeats=1):
  #   """Send values
  #   """
  #   status = _SDK.asdkSend(self._dm, const Scalar * value)
  #   if status != SUCCESS:
  #     raise Exception()

  # def reset(self):
  #   status = _SDK.asdkReset(self._dm)
  #   if status != SUCCESS:
  #     raise Exception()

  # def stop(self):
  #   """Stops all current transfer.
  #   """
  #   status = _SDK.asdkReset(self._dm)
  #   if status != SUCCESS:
  #     raise Exception()

  def get_number_of_actuators(self):
    value = ctypes.pointer(_Scalar())
    status = _SDK.asdkGet(self._dm, "NbOfActuator".encode("utf-8"), value)
    if status != _SUCCESS:
      raise Exception()
    return int(value.contents.value)

  def __del__(self):
    ## Don't bother checking if release was successful.  It's not like
    ## we have an alternative plan.
    _SDK.asdkRelease(self._dm)

class AlpaoDeformableMirror(microscope.devices.DeformableMirror):
  def __init__(self, serial_number, *args, **kwargs):
    microscope.devices.DeformableMirror.__init__(self, *args, **kwargs)
    self.serial_number = serial_number
