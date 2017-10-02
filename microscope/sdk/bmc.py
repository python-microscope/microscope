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

"""Wrapper to Boston MicroMachines Corporation (BMC) SDK.
"""

from ctypes import *
import sys

if sys.platform == "win32":
  ## Not actually tested yet
  SDK = windll.BMC
else:
  SDK = cdll.LoadLibrary("libBMC.so.3")

## Definitions from BMCDefs.h
BMC_MAX_PATH = 260
BMC_SERIAL_NUMBER_LEN = 11
MAX_DM_SIZE = 4096

class DM_PRIV(Structure):
  pass

class DM_DRIVER(Structure):
  _fields_ = [
      ("channel_count", c_uint),
      ("serial_number", c_char * (BMC_SERIAL_NUMBER_LEN+1)),
      ("reserved", c_uint * 7)
  ]

class DM(Structure):
  _fields_ = [
      ("Driver_Type", c_uint),
      ("DevId", c_uint),
      ("HVA_Type", c_uint),
      ("use_fiber", c_uint),
      ("use_CL", c_uint),
      ("burst_mode", c_uint),
      ("fiber_mode", c_uint),
      ("ActCount", c_uint),
      ("MaxVoltage", c_uint),
      ("VoltageLimit", c_uint),
      ("mapping", c_char * BMC_MAX_PATH),
      ("inactive", c_uint * MAX_DM_SIZE_),
      ("profiles_path", c_char * BMC_MAX_PATH),
      ("maps_path", c_char * BMC_MAX_PATH),
      ("cals_path", c_char * BMC_MAX_PATH),
      ("cal", c_char * BMC_MAX_PATH),
      ("serial_number", c_char * (BMC_SERIALl_NUMBER_LEN+1)),
      ("driver", DM_DRIVER),
      ("priv", POINTER(DM_PRIV)),
  ]

DMHANDLE = POINTER(DM)
BMCRC = c_int # an enum for the error codes
BMCLOGLEVEL = c_int # enum for log-levels

def make_prototype(name, argtypes, restype=BMCRC):
  func = getattr(SDK, name)
  func.argtypes = argtypes
  func.restype = restype
  return func

BMCOpen = make_prototype("BMCOpen", [DMHANDLE, c_char_p])

BMCSetSingle = make_prototype("BMCSetSingle", [DMHANDLE, c_uint32, c_double])

BMCSetArray = make_prototype("BMCSetArray",
                             [DMHANDLE, POINTER(c_double), POINTER(c_uint32)])

BMCGetArray = make_prototype("BMCGetArray",
                             [DMHANDLE, POINTER(c_double),c_uint32])

BMCClearArray = make_prototype ("BMCClearArray", [DMHANDLE])

BMCClose = make_prototype("BMCClose", [DMHANDLE])

BMCErrorString = make_prototype("BMCErrorString", [BMCRC], c_char_p)

BMCConfigureLog = make_prototype("BMCConfigureLog", [c_char_p, BMCLOGLEVEL])

BMCVersionString = make_prototype("BMCVersionString", [], c_char_p)
