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

"""This module is deprecated and only kept for backwards compatibility.
"""

from microscope import ROI, AxisLimits, Binning, TriggerMode, TriggerType
from microscope.abc import (
    TRIGGER_AFTER,
    TRIGGER_BEFORE,
    TRIGGER_DURATION,
    TRIGGER_SOFT,
    Camera as CameraDevice,
    Controller as ControllerDevice,
    DataDevice,
    DeformableMirror,
    Device,
    FilterWheel as FilterWheelBase,
    FloatingDeviceMixin,
    LightSource as LaserDevice,
    SerialDeviceMixin as SerialDeviceMixIn,
    Stage as StageDevice,
    StageAxis,
    TriggerTargetMixin as TriggerTargetMixIn,
    keep_acquiring,
)
from microscope.device_server import device
