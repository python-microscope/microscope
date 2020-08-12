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

"""Boston Micromachines deformable mirrors SDK.
"""

import ctypes
import os
from ctypes import c_char, c_char_p, c_double, c_int, c_uint, c_uint32

if os.name in ("nt", "ce"):
    # Not actually tested yet
    SDK = ctypes.WinDLL("BMC2")
else:
    SDK = ctypes.CDLL("libBMC.so.3")


# Definitions from BMCDefs.h
MAX_PATH = 260
SERIAL_NUMBER_LEN = 11
MAX_DM_SIZE = 4096


class DM_PRIV(ctypes.Structure):
    pass


class DM_DRIVER(ctypes.Structure):
    _fields_ = [
        ("channel_count", c_uint),
        ("serial_number", c_char * (SERIAL_NUMBER_LEN + 1)),
        ("reserved", c_uint * 7),
    ]


class DM(ctypes.Structure):
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
        ("mapping", c_char * MAX_PATH),
        ("inactive", c_uint * MAX_DM_SIZE),
        ("profiles_path", c_char * MAX_PATH),
        ("maps_path", c_char * MAX_PATH),
        ("cals_path", c_char * MAX_PATH),
        ("cal", c_char * MAX_PATH),
        ("serial_number", c_char * (SERIAL_NUMBER_LEN + 1)),
        ("driver", DM_DRIVER),
        ("priv", ctypes.POINTER(DM_PRIV)),
    ]


DMHANDLE = ctypes.POINTER(DM)

RC = c_int  # enum for error codes

LOGLEVEL = c_int  # enum for log-levels
LOG_ALL = 0
LOG_TRACE = LOG_ALL
LOG_DEBUG = 1
LOG_INFO = 2
LOG_WARN = 3
LOG_ERROR = 4
LOG_FATAL = 5
LOG_OFF = 6


def make_prototype(name, argtypes, restype=RC):
    func = getattr(SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


Open = make_prototype("BMCOpen", [DMHANDLE, c_char_p])

SetArray = make_prototype(
    "BMCSetArray",
    [DMHANDLE, ctypes.POINTER(c_double), ctypes.POINTER(c_uint32)],
)

GetArray = make_prototype(
    "BMCGetArray", [DMHANDLE, ctypes.POINTER(c_double), c_uint32]
)

Close = make_prototype("BMCClose", [DMHANDLE])

ErrorString = make_prototype("BMCErrorString", [RC], c_char_p)

ConfigureLog = make_prototype("BMCConfigureLog", [c_char_p, LOGLEVEL])

VersionString = make_prototype("BMCVersionString", [], c_char_p)
