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

"""Alpao deformable mirrors SDK.
"""

import ctypes
import os
from ctypes import c_char_p, c_double, c_int, c_size_t, c_uint32

if os.name in ("nt", "ce"):
    SDK = ctypes.WinDLL("ASDK")
else:
    # Not actually tested yet
    SDK = ctypes.CDLL("libasdk.so")


class DM(ctypes.Structure):
    pass


pDM = ctypes.POINTER(DM)

# We have this "typedefs" to ease matching with alpao's headers.
CStr = c_char_p
Scalar = c_double
Scalar_p = ctypes.POINTER(Scalar)
UInt = c_uint32
Size_T = c_size_t

COMPL_STAT = c_int  # enum for function completion status
SUCCESS = 0
FAILURE = -1


def make_prototype(name, argtypes, restype=COMPL_STAT):
    func = getattr(SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


Get = make_prototype("asdkGet", [pDM, CStr, Scalar_p])

GetLastError = make_prototype(
    "asdkGetLastError", [ctypes.POINTER(UInt), CStr, Size_T]
)

Init = make_prototype("asdkInit", [CStr], pDM)

Release = make_prototype("asdkRelease", [pDM])

Send = make_prototype("asdkSend", [pDM, Scalar_p])

SendPattern = make_prototype("asdkSendPattern", [pDM, Scalar_p, UInt, UInt])

Set = make_prototype("asdkSet", [pDM, CStr, Scalar])

Stop = make_prototype("asdkStop", [pDM])
