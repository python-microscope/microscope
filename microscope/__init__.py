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

import enum
import typing


class AxisLimits(typing.NamedTuple):
    lower: float
    upper: float


class Binning(typing.NamedTuple):
    """A tuple containing parameters for horizontal and vertical binning. """

    h: int
    v: int


class ROI(typing.NamedTuple):
    """A tuple that defines a region of interest."""

    left: int
    top: int
    width: int
    height: int


class TriggerType(enum.Enum):
    SOFTWARE = 0
    RISING_EDGE = 1
    FALLING_EDGE = 2
    PULSE = 3


class TriggerMode(enum.Enum):
    ONCE = 1
    BULB = 2
    STROBE = 3
    START = 4
