#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016-2017 Mick Phillips <mick.phillips@gmail.com>
## Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>
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

import random
import time

import Pyro4
import numpy as np

from microscope import devices
from microscope.devices import keep_acquiring
from microscope.filterwheel import FilterWheelBase

@Pyro4.expose
@Pyro4.behavior('single')
class TestCamera(devices.CameraDevice):
    def __init__(self, *args, **kwargs):
        super(TestCamera, self).__init__(**kwargs)
        # Software buffers and parameters for data conversion.
        self._a_setting = 0
        self.add_setting('a_setting', 'int',
                         lambda: self._a_setting,
                         lambda val: setattr(self, '_a_setting', val),
                         lambda: (1, 100))
        self._error_percent = 0
        self.add_setting('_error_percent', 'int',
                         lambda: self._error_percent,
                         self._set_error_percent,
                         lambda: (0, 100))
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = False

    def _set_error_percent(self, value):
        self._error_percent = value
        self._a_setting = value / 10

    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        self._logger.info("Purging buffers.")

    def _create_buffers(self):
        """Create buffers and store values needed to remove padding later."""
        self._purge_buffers()
        self._logger.info("Creating buffers.")
        #time.sleep(0.5)

    def _fetch_data(self):
        if self._acquiring and self._triggered:
            if random.randint(0, 100) < self._error_percent:
                self._logger.info('Raising exception')
                raise Exception('Exception raised in TestCamera._fetch_data')
            self._logger.info('Sending image')
            time.sleep(self._exposure_time)
            self._triggered = False
            return np.random.random_integers(255,
                                             size=(512,512)).astype(np.int16)

    def abort(self):
        self._logger.info('Disabling acquisition.')
        if self._acquiring:
            self._acquiring = False

    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        self._logger.info('Initializing.')
        time.sleep(0.5)

    def make_safe(self):
        if self._acquiring:
            self.abort()

    def _on_disable(self):
        self.abort()

    def _on_enable(self):
        self._logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        self._create_buffers()
        self._acquiring = True
        self._logger.info("Acquisition enabled.")
        return True

    def set_exposure_time(self, value):
        self._exposure_time = value

    def get_exposure_time(self):
        return self._exposure_time

    def get_cycle_time(self):
        return self._exposure_time

    def _get_sensor_shape(self):
        return (512,512)

    def get_trigger_type(self):
        return devices.TRIGGER_SOFT

    def soft_trigger(self):
        self._logger.info('Trigger received; self._acquiring is %s.'
                          % self._acquiring)
        if self._acquiring:
            self._triggered = True

    def _get_binning(self):
         return (1,1)

    @keep_acquiring
    def _set_binning(self, h, v):
        return False

    def _get_roi(self):
        return (0, 0, 512, 512)

    @keep_acquiring
    def _set_roi(self, x, y, width, height):
        return False

    def _on_shutdown(self):
        pass

class TestFilterWheel(FilterWheelBase):
    def __init__(self, filters=[], *args, **kwargs):
        super(TestFilterWheel, self).__init__(filters, *args, **kwargs)
        self._position = 0

    def _get_position(self):
        return self._position

    def _set_position(self, position):
        time.sleep(1)
        self._position = position

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass

@Pyro4.expose
class TestLaser(devices.LaserDevice):
    def __init__(self, *args, **kwargs):
        super(TestLaser, self).__init__()
        self._power = 0
        self._emission = False

    def get_status(self):
        result = [self._emission, self._power, self._set_point]
        return result

    def enable(self):
        self._emission = True
        return self._emission

    def _on_shutdown(self):
        pass

    def initialize(self):
        pass

    def disable(self):
        self._emission = False
        return self._emission

    def get_is_on(self):
        return self._emission

    def _set_power_mw(self, level):
        self._logger.info("Power set to %s." % level)
        self._power = level

    def get_max_power_mw(self):
        return 100

    def get_power_mw(self):
        return [0, self._power][self._emission]


class TestDeformableMirror(devices.DeformableMirror):
    def __init__(self, n_actuators, *args, **kwargs):
        super(TestDeformableMirror, self).__init__(*args, **kwargs)
        self._n_actuators = n_actuators

    def apply_pattern(self, pattern):
        self._validate_patterns(pattern)
        self._current_pattern = pattern
