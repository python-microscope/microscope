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

"""Interactive tests for hardware.
"""

import time

import numpy

def test_mirror_actuators(dm, time_interval=0.5):
    """Iterate over all actuators of a deformable mirror.

    Parameters
    ----------
        dm : microscope.device.DeformableMirror
            The mirror to test
        time_interval : number
            Number of seconds between trying each actuator.
    """
    base_value = 0.5
    data = numpy.full((dm.n_actuators), base_value)
    dm.apply_pattern(data)

    time.sleep(time_interval)
    for new_value in [1.0, 0.0]:
        for i in range(dm.n_actuators):
            data[i] = new_value
            dm.apply_pattern(data)
            time.sleep(time_interval)
            data[i] = base_value

    dm.apply_pattern(data)
