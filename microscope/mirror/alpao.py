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
import time

import numpy

import microscope.devices

if sys.platform == "win32":
  _SDK = ctypes.windll.ASDK # throws OSError if missing
else:
  raise NotImplementedError("alpao module not yet tested for non windows")


## These type names are the same names used in Alpao SDK documentation
## and header files.

class _asdkDM(ctypes.Structure):
  pass

_asdkDM_p = ctypes.POINTER(_asdkDM)
_COMPL_STAT = ctypes.c_int # an enum type
_CStr = ctypes.c_char_p
_Scalar = ctypes.c_double
_Scalar_p = ctypes.POINTER(_Scalar)
_UInt = ctypes.c_uint32
_Size_T = ctypes.c_size_t

## COMPL_STAT values hardcoded because enum definitions are not
## exported.
_SUCCESS = 0
_FAILURE = -1


_SDK.asdkGet.argtypes = [_asdkDM_p, _CStr, _Scalar_p]
_SDK.asdkGet.restype = _COMPL_STAT

_SDK.asdkGetLastError.argtypes = [ctypes.POINTER(_UInt), _CStr, _Size_T]
_SDK.asdkGetLastError.restype = _COMPL_STAT

_SDK.asdkInit.argtypes = [_CStr]
_SDK.asdkInit.restype = _asdkDM_p

_SDK.asdkPrintLastError.argtypes = []
_SDK.asdkPrintLastError.restype = None

_SDK.asdkRelease.argtypes = [_asdkDM_p]
_SDK.asdkRelease.restype = _COMPL_STAT

_SDK.asdkReset.argtypes = [_asdkDM_p]
_SDK.asdkReset.restype = _COMPL_STAT

_SDK.asdkSend.argtypes = [_asdkDM_p, _Scalar_p]
_SDK.asdkSend.restype = _COMPL_STAT

_SDK.asdkSendPattern.argtypes = [_asdkDM_p, _Scalar_p, _UInt, _UInt]
_SDK.asdkSendPattern.restype = _COMPL_STAT

_SDK.asdkSet.argtypes = [_asdkDM_p, _CStr, _Scalar]
_SDK.asdkSet.restype = _COMPL_STAT

_SDK.asdkSetString.argtypes = [_asdkDM_p, _CStr, _CStr]
_SDK.asdkSetString.restype = _COMPL_STAT

_SDK.asdkStop.argtypes = [_asdkDM_p]
_SDK.asdkStop.restype = _COMPL_STAT

class _DM(object):
  """Wraps the Alpao C interface into a class.

  This is pretty much a Python implementation of the C++ acs::DM class
  from Alpao's SDK.

  Maybe this class is pointless and we could make the calls to the C
  functions directly on the AlpaoDeformableMirror class.
  """

  ## The length of the buffer given to Alpao SDK to write error
  ## messages.
  _err_msg_len = 64

  ## TODO: Confirm this values, the SDK manual does not say
  trigger_type_to_value = {
    microscope.devices.TRIGGER_SOFT : 0,
    microscope.devices.TRIGGER_BEFORE: 2,
  }

  def _check_error(self):
    """Check for errors in the Alpao SDK.

    Checks if there is an error in the Alpao SDK stack and raise an
    exception if so.
    """
    ## asdkGetLastError should write a null-terminated string but
    ## doesn't seem like it (at least CannotOpenCfg does not ends in
    ## null) so we empty the buffer ourselves before using it.  Note
    ## that even when there are no errors, we need to empty the buffer
    ## because the buffer has the message 'No error in stack'.
    ##
    ## TODO: report this upstream to Alpao and clean our code.
    self._err_msg[0:self._err_msg_len] = b'\x00' * self._err_msg_len

    err = ctypes.pointer(_UInt(0))
    status = _SDK.asdkGetLastError(err, self._err_msg, self._err_msg_len)
    if status == _SUCCESS:
      msg = self._err_msg.value
      if len(msg) > self._err_msg_len:
        msg = msg + "..."
      raise Exception("Failed to initialise connection: %s (error %i)"
                      % (msg, err.value))

  def __init__(self, serial_number):
    """
    Parameters
    ----------
    serial_number: string
      The serial number of the deformable mirror, something like "BIL103".
    """
    ## We need to constantly check for errors and need a buffer to
    ## have the message written to.  To avoid creating a new buffer
    ## each time, have a buffer per instance.
    self._err_msg = ctypes.create_string_buffer(self._err_msg_len)

    self._dm = _SDK.asdkInit(bytes(serial_number, "utf-8"))
    if not self._dm:
      raise Exception("Failed to initialise connection: don't know why")

    ## In theory, asdkInit should return a NULL pointer in case of
    ## failure.  However, at least in the case of a missing
    ## configuration file it still returns a DM pointer so we check if
    ## there's any error on the stack.  But maybe there are
    ## initialisation errors that do make it return a NULL pointer so
    ## we check both.
    ##
    ## TODO: report this upstream to Alpao and clean our code.
    self._check_error()

    value = _Scalar_p(_Scalar())
    status = _SDK.asdkGet(self._dm, bytes("NbOfActuator", "utf-8"), value)
    if status != _SUCCESS:
      self._check_error()
    self.n_actuators = int(value.contents.value)

  def send(self, values, n_repeats=1):
    """Send values to the mirror.

    Parameters
    ----------
    values: numpy array
      An N elements array of values in the range [-1 1], where N
      equals the number of actuators.
    """
    if n_repeats != 1:
      NotImplementedError()
    elif values.size != self.n_actuators:
      raise Exception(("Number of values '%d' differ from number of"
                       " actuators '%d'") % (values.size, self.n_actuators))

    status = _SDK.asdkSend(self._dm, values.ctypes.data_as(_Scalar_p))
    if status != _SUCCESS:
      raise Exception()

  def send_patterns(self, patterns):
    """Send multiple patterns to the mirror.

    Args:
      patterns - numpy array with 2 dimensions, with one row per
        pattern.  Even if sending only one pattern, the number of rows
        must be 1, i.e., size (1, N) and not just N.
    """
    ## TODO: add option to repeat the pattern on the device
    status = _SDK.asdkSendPattern(self._dm, patterns.ctypes.data_as(_Scalar_p),
                                  patterns.shape[0], 1)
    if status != _SUCCESS:
      raise Exception()

  def reset(self):
    """Reset mirror values.
    """
    status = _SDK.asdkReset(self._dm)
    if status != _SUCCESS:
      self._check_error()

  def set_trigger_type(self, trigger_type):
    try:
      value = self.trigger_type_to_value[trigger_type]
    except KeyError:
      raise Exception("invalid trigger type '%d' for Alpao Mirrors"
                      % trigger_type)

    status = _SDK.asdkSet(self._dm, bytes("TriggerMode", "utf-8"), value)
    if status != _SUCCESS:
      raise Exception("failed to set trigger mode '%d'" %  value)

  def __del__(self):
    ## Will throw an OSError if it's already been releaed.
    _SDK.asdkRelease(self._dm)


def _test_all_actuators(dm, time_interval=1):
  """TODO: maybe move this to testsuite namespace?
  """
  data = numpy.full((dm.n_actuators), -1.0, dtype=_Scalar)
  for i in range(dm.n_actuators):
    data[i] = 1.0
    dm.send(data)
    time.sleep(time_interval)
    data[i] = -1.0
  dm.reset()


class AlpaoDeformableMirror(microscope.devices.DeformableMirror):
  def __init__(self, serial_number, *args, **kwargs):
    microscope.devices.DeformableMirror.__init__(self, *args, **kwargs)
    self._dm = _DM(serial_number)

  def get_n_actuators(self):
    return self._dm.n_actuators

  def send(self, values):
    self._dm.send(values)

  def send_patterns(self, patterns):
    if patterns.ndim != 2:
      raise Exception("patterns have %d dimensions instead of 2"
                      % patterns.ndim)
    elif patterns.shape[1] == self.get_n_actuators():
      raise Exception(("PATTERNS number of columns '%d' must equal number of"
                       " actuators '%d'"
                       % (patterns.shape[1], self.get_n_actuators())))
    self._dm.send_patterns(patterns)

  def set_trigger(self, mode):
    self._dm.set_trigger_type(mode)

  def reset(self):
    self._dm.reset()

  ## Do not set _on_shutdown.  To shutdown device, destroy object.
