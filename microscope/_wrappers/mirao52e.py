#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Wrapper to the Imagine Optic Mirao 52-e API.
"""

import ctypes


# Vendor only supports Windows
SDK = ctypes.WinDLL('mirao52e')


TRUE = 1 # TRUE MroBoolean value
FALSE = 0 # FALSE MroBoolean value

# Number of values of a mirao 52-e command (the number of actuators
# is a define on the library header)
NB_COMMAND_VALUES = 52

# Error code defines
OK = 0


Boolean = ctypes.c_char
Command = ctypes.POINTER(ctypes.c_double)


def prototype(name, argtypes, restype=Boolean):
    func = getattr(SDK, name)
    # All functions have 'int *' as the last argument for status.
    func.argtypes = argtypes + [ctypes.POINTER(ctypes.c_int)]
    func.restype = restype
    return func


open = prototype('mro_open', [])
close = prototype('mro_close', [])

applyCommand = prototype('mro_applyCommand', [Command, Boolean])
