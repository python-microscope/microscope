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
from PIL import Image, ImageFont, ImageDraw

from microscope import devices
from microscope.devices import keep_acquiring
from microscope.devices import FilterWheelBase

@Pyro4.behavior('single')
class TestCamera(devices.CameraDevice):
    def __init__(self, *args, **kwargs):
        super(TestCamera, self).__init__(**kwargs)
        # Binning and ROI
        self._roi = (0,0,511,511)
        self._binning = (1,1)
        self.add_setting('binning', 'tuple',
                         lambda: self._binning,
                         lambda val: setattr(self, '_binning', val),
                         None)
        self.add_setting('roi', 'tuple',
                         lambda: self._roi,
                         lambda val: setattr(self, '_roi', val),
                         None)
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
        self._gain = 0
        self.add_setting('gain', 'int',
                         lambda: self._gain,
                         self._set_gain,
                         lambda: (0, 8192))
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = 0
        # Count number of images sent since last enable.
        self._sent = 0
        # Font for rendering counter in images.
        self._font = ImageFont.load_default()

    def _set_error_percent(self, value):
        self._error_percent = value
        self._a_setting = value / 10

    def _set_gain(self, value):
        self._gain = value

    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        self._logger.info("Purging buffers.")

    def _create_buffers(self):
        """Create buffers and store values needed to remove padding later."""
        self._purge_buffers()
        self._logger.info("Creating buffers.")

    def _fetch_data(self):
        if self._acquiring and self._triggered > 0:
            if random.randint(0, 100) < self._error_percent:
                self._logger.info('Raising exception')
                raise Exception('Exception raised in TestCamera._fetch_data')
            self._logger.info('Sending image')
            time.sleep(self._exposure_time)
            self._triggered -= 1
            # Create an image
            dark = int(32 * np.random.rand())
            light = int(255 - 128 * np.random.rand())
            width = (self._roi[2] - self._roi[0]) // self._binning[0]
            height = (self._roi[3] - self._roi[1]) // self._binning[1]
            size = (width, height)
            image = Image.fromarray(
                np.random.randint(dark, light, size=size).astype(np.uint8), 'L')
            # Render text
            text = "%d" % self._sent
            tsize = self._font.getsize(text)
            ctx = ImageDraw.Draw(image)
            ctx.rectangle([size[0]-tsize[0]-8, 0, size[0], tsize[1]+8], fill=dark)
            ctx.text((size[0]-tsize[0]-4, 4), text, fill=light)

            self._sent += 1
            return np.asarray(image).T

    def abort(self):
        self._logger.info("Disabling acquisition; %d images sent." % self._sent)
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
        self._sent = 0
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
            self._triggered += 1

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


class TestLaser(devices.LaserDevice):
    def __init__(self, *args, **kwargs):
        super(TestLaser, self).__init__()
        self._set_point = 0.0
        self._power = 0.0
        self._emission = False

    def get_status(self):
        return [str(x) for x in (self._emission, self._power, self._set_point)]

    def _on_enable(self):
        self._emission = True
        return self._emission

    def _on_shutdown(self):
        pass

    def initialize(self):
        pass

    def _on_disable(self):
        self._emission = False
        return self._emission

    def get_is_on(self):
        return self._emission

    def _set_power_mw(self, level):
        self._logger.info("Power set to %s." % level)
        self._power = level

    def get_max_power_mw(self):
        return 100.0

    def get_min_power_mw(self):
        return 0.0

    def get_power_mw(self):
        if self._emission:
            return self._power
        else:
            return 0.0


class TestDeformableMirror(devices.DeformableMirror):
    def __init__(self, n_actuators, *args, **kwargs):
        super(TestDeformableMirror, self).__init__(*args, **kwargs)
        self._n_actuators = n_actuators

    def apply_pattern(self, pattern):
        self._validate_patterns(pattern)
        self._current_pattern = pattern

    def get_current_pattern(self):
        return self._current_pattern


@Pyro4.behavior('single')
class DummySLM(devices.Device):
    def __init__(self, *args, **kwargs):
        devices.Device.__init__(self, args, kwargs)
        self.sim_diffraction_angle = 0.
        self.sequence_params = []
        self.sequence_index = 0

    def initialize(self, *args, **kwargs):
        pass

    def _on_shutdown(self):
        pass

    def set_sim_diffraction_angle(self, theta):
        self._logger.info('set_sim_diffraction_angle %f' % theta)
        self.sim_diffraction_angle = theta

    def get_sim_diffraction_angle(self):
        return self.sim_diffraction_angle

    def run(self):
        self.enabled = True
        self._logger.info('run')
        return

    def stop(self):
        self.enabled = False
        self._logger.info('stop')
        return

    def get_sim_sequence(self):
        return self.sequence_params

    def set_sim_sequence(self, seq):
        self._logger.info('set_sim_sequence')
        self.sequence_params = seq
        return

    def get_sequence_index(self):
        return self.sequence_index


@Pyro4.behavior('single')
class DummyDSP(devices.Device):
    def __init__(self, *args, **kwargs):
        devices.Device.__init__(self, args, kwargs)
        self._digi = 0
        self._ana = [0,0,0,0]
        self._client = None
        self._actions = []

    def initialize(self, *args, **kwargs):
        pass

    def _on_shutdown(self):
        pass

    def Abort(self):
        self._logger.info('Abort')

    def WriteDigital(self, value):
        self._logger.info('WriteDigital: %s' % "{0:b}".format(value))
        self._digi = value

    def MoveAbsolute(self, aline, pos):
        self._logger.info('MoveAbsoluteADU: line %d, value %d' % (aline, pos))
        self._ana[aline] = pos

    def arcl(self, mask, pairs):
        self._logger.info('arcl: %s, %s' % (mask, pairs))

    def profileSet(self, pstr, digitals, *analogs):
        self._logger.info('profileSet ...')
        self._logger.info('... ', pstr)
        self._logger.info('... ', digitals)
        self._logger.info('... ', analogs)

    def DownloadProfile(self):
        self._logger.info('DownloadProfile')

    def InitProfile(self, numReps):
        self._logger.info('InitProfile')

    def trigCollect(self, *args, **kwargs):
        self._logger.info('trigCollect: ... ')
        self._logger.info(args)
        self._logger.info(kwargs)

    def ReadPosition(self, aline):
        self._logger.info('ReadPosition   : line %d, value %d' % (aline, self._ana[aline]))
        return self._ana[aline]

    def ReadDigital(self):
        self._logger.info('ReadDigital: %s' % "{0:b}".format(self._digi))
        return self._digi

    def PrepareActions(self, actions, numReps=1):
        self._logger.info('PrepareActions')
        self._actions = actions
        self._repeats = numReps

    def RunActions(self):
        self._logger.info('RunActions ...')
        for i in range(self._repeats):
            for a in self._actions:
                self._logger.info(a)
                time.sleep(a[0] / 1000.)
        if self._client:
            self._client.receiveData("DSP done")
        self._logger.info('... RunActions done.')

    def receiveClient(self, *args, **kwargs):
        ## XXX: maybe this should be on its own mixin instead of on DataDevice
        return devices.DataDevice.receiveClient(self, *args, **kwargs)

    def set_client(self, *args, **kwargs):
        ## XXX: maybe this should be on its own mixin instead of on DataDevice
        return devices.DataDevice.set_client(self, *args, **kwargs)
