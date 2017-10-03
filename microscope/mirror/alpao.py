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
import time

import numpy

import microscope.devices
import microscope.wrappers.alpao as ASDK


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
  ## The length of the buffer given to Alpao SDK to write error
  ## messages.
  _err_msg_len = 64

  trigger_type_to_value = {
    microscope.devices.TRIGGER_SOFT : 0,
    microscope.devices.TRIGGER_AFTER : 1,
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

    err = ctypes.pointer(ASDK.UInt(0))
    status = ASDK.GetLastError(err, self._err_msg, self._err_msg_len)
    if status == ASDK.SUCCESS:
      msg = self._err_msg.value
      if len(msg) > self._err_msg_len:
        msg = msg + "..."
      raise Exception("Failed to initialise connection: %s (error %i)"
                      % (msg, err.contents.value))

  def __init__(self, serial_number, *args, **kwargs):
    """
    Parameters
    ----------
    serial_number: string
      The serial number of the deformable mirror, something like "BIL103".
    """
    super(AlpaoDeformableMirror, self).__init__(*args, **kwargs)

    ## We need to constantly check for errors and need a buffer to
    ## have the message written to.  To avoid creating a new buffer
    ## each time, have a buffer per instance.
    self._err_msg = ctypes.create_string_buffer(self._err_msg_len)

    self._dm = ASDK.Init(serial_number.encode("utf-8"))
    if not self._dm:
      raise Exception("Failed to initialise connection: don't know why")

    ## In theory, asdkInit should return a NULL pointer in case of
    ## failure.  However, at least in the case of a missing
    ## configuration file it still returns a DM pointer so we check if
    ## there's any error on the stack.  But maybe there are
    ## initialisation errors that do make it return a NULL pointer so
    ## we check both.
    self._check_error()

    value = ASDK.Scalar_p(ASDK.Scalar())
    status = ASDK.Get(self._dm, "NbOfActuator".encode("utf-8"), value)
    if status != ASDK.SUCCESS:
      self._check_error()
    self.n_actuators = int(value.contents.value)

  def get_n_actuators(self):
    return self.n_actuators

  def send(self, values):
    if values.size != self.n_actuators:
      raise Exception(("Number of values '%d' differ from number of"
                       " actuators '%d'") % (values.size, self.n_actuators))

    status = ASDK.Send(self._dm, values.ctypes.data_as(ASDK.Scalar_p))
    if status != ASDK.SUCCESS:
      self._check_error()

  def send_patterns(self, patterns):
    """Send multiple patterns to the mirror.

    Args:
      patterns - numpy array with 2 dimensions, with one row per
        pattern.  Even if sending only one pattern, the number of rows
        must be 1, i.e., size (1, N) and not just N.
    """
    if patterns.ndim != 2:
      raise Exception("patterns have %d dimensions instead of 2"
                      % patterns.ndim)
    elif (patterns.shape[1] != self.get_n_actuators()):
      raise Exception(("PATTERNS length of second dimension '%d' must equal"
                       " to the number of actuators '%d'"
                       % (patterns.shape[1], self.n_actuators)))

    n_patterns = patterns.shape[0]
    ## There is an issue with Alpao SDK in that they don't really
    ## support hardware trigger.  Instead, an hardware trigger will
    ## signal the mirror to apply all the patterns as quickly as
    ## possible.  We received a modified version from Alpao that does
    ## what we want --- each trigger applies the next pattern --- but
    ## that requires nPatt and nRepeat to have the same value, hence
    ## the last two arguments here being 'n_patterns, n_patterns'.
    status = ASDK.SendPattern(self._dm, patterns.ctypes.data_as(ASDK.Scalar_p),
                              n_patterns, n_patterns)
    if status != ASDK.SUCCESS:
      self._check_error()

  def set_trigger(self, mode):
    try:
      value = self.trigger_type_to_value[mode]
    except KeyError:
      raise Exception("invalid trigger type '%d' for Alpao Mirrors." %trigger_type)

    status = ASDK.Set(self._dm, "TriggerIn".encode( "utf-8"), value)
    if status != ASDK.SUCCESS:
      raise Exception("failed to set trigger mode '%d'" %  value)

  def reset(self):
    status = ASDK.Reset(self._dm)
    if status != ASDK.SUCCESS:
      self._check_error()

  def _on_shutdown(self):
    pass
  def initialize(self):
    pass

  def __del__(self):
    ## Will throw an OSError if it's already been releaed.
    ASDK.Release(self._dm)
