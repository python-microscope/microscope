#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
#
# Microscope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Microscope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

import collections
import typing
import enum


# XXX: once python>=3.6 is required, subclass from typing.NamedTuple
# instead.
AxisLimits = typing.NamedTuple('AxisLimits',[('lower', float),
                                             ('upper', float)])

# A tuple containing parameters for horizontal and vertical binning.
Binning = collections.namedtuple('Binning', ['h', 'v'])


# A tuple that defines a region of interest.
ROI = collections.namedtuple('ROI', ['left', 'top', 'width', 'height'])


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
