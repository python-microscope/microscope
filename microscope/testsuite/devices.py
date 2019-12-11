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

import logging
import random
import time

import numpy as np
from PIL import Image, ImageFont, ImageDraw

from microscope import devices
from microscope.devices import keep_acquiring
from microscope.devices import FilterWheelBase
from microscope.devices import ROI, Binning

from enum import IntEnum


_logger = logging.getLogger(__name__)

from functools import wraps
def must_be_initialized(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, '_initialized') and self._initialized:
            return f(self, *args, **kwargs)
        else:
            raise Exception("Device not initialized.")
    return wrapper

class CamEnum(IntEnum):
    A = 1
    B = 2
    C = 3
    D = 4

def _theta_generator():
    """A generator that yields values between 0 and 2*pi"""
    TWOPI = 2 * np.pi
    th = 0
    while True:
        yield th
        th = (th + 0.01*TWOPI) % TWOPI

class _ImageGenerator():
    """Generates test images, with methods for configuration via a Setting."""
    def __init__(self):
        self._methods = (self.noise, self.gradient, self.sawtooth,
                         self.one_gaussian, self.black, self.white)
        self._method_index = 0
        self._datatypes = (np.uint8, np.uint16, np.float)
        self._datatype_index = 0
        self._theta = _theta_generator()
        self.numbering = True
        # Font for rendering counter in images.
        self._font = ImageFont.load_default()

    def enable_numbering(self, enab):
        self.numbering = enab

    def get_data_types(self):
        return(t.__name__ for t in self._datatypes)

    def data_type(self):
        return self._datatype_index

    def set_data_type(self, index):
        self._datatype_index = index

    def get_methods(self):
        """Return the names of available image generation methods"""
        return (m.__name__ for m in self._methods)

    def method(self):
        """Return the index of the current image generation method."""
        return self._method_index

    def set_method(self, index):
        """Set the image generation method."""
        self._method_index = index

    def get_image(self, width, height, dark=0, light=255, index=None):
        """Return an image using the currently selected method."""
        m = self._methods[self._method_index]
        d = self._datatypes[self._datatype_index]
        #return Image.fromarray(m(width, height, dark, light).astype(d), 'L')
        data = m(width, height, dark, light).astype(d)
        if self.numbering and index is not None:
            text = "%d" % index
            size = tuple(d+2 for d in self._font.getsize(text))
            img = Image.new('L', size)
            ctx = ImageDraw.Draw(img)
            ctx.text((1, 1), text, fill=light)
            data[0:size[1],0:size[0]] = np.asarray(img)
        return data

    def black(self, w, h, dark, light):
        """Ignores dark and light - returns zeros"""
        return np.zeros((h, w))

    def white(self, w, h, dark, light):
        """Ignores dark and light - returns max value for current data type."""
        d = self._datatypes[self._datatype_index]
        if issubclass(d, np.integer):
            value = np.iinfo(d).max
        else:
            value = 1.
        return value * np.ones((h, w)).astype(d)

    def gradient(self, w, h, dark, light):
        """A single gradient across the whole image from top left to bottom right."""
        xx, yy = np.meshgrid(range(w), range(h))
        return dark + light * (xx + yy) / (xx.max() + yy.max())

    def noise(self, w, h, dark, light):
        """Random noise."""
        return np.random.randint(dark, light, size=(h, w))

    def one_gaussian(self, w, h, dark, light):
        "A single gaussian"
        sigma = 0.01 * max(w, h)
        x0 = np.random.randint(w)
        y0 = np.random.randint(h)
        xx, yy = np.meshgrid(range(w), range(h))
        return dark + light * np.exp(-((xx-x0)**2 + (yy-y0)**2) / (2*sigma**2))

    def sawtooth(self, w, h, dark, light):
        """A sawtooth gradient that rotates about 0,0."""
        th = next(self._theta)
        xx, yy = np.meshgrid(range(w), range(h))
        wrap = 0.1 * max(xx.max(), yy.max())
        return dark + light * ((np.sin(th)*xx + np.cos(th)*yy) % wrap) / (wrap)


class TestCamera(devices.CameraDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Binning and ROI
        self._roi = ROI(0,0,512,512)
        self._binning = Binning(1,1)
        # Function used to generate test image
        self._image_generator = _ImageGenerator()
        self.add_setting('image pattern', 'enum',
                         self._image_generator.method,
                         self._image_generator.set_method,
                         self._image_generator.get_methods)
        self.add_setting('image data type', 'enum',
                         self._image_generator.data_type,
                         self._image_generator.set_data_type,
                         self._image_generator.get_data_types)
        self.add_setting('display image number', 'bool',
                         lambda: self._image_generator.numbering,
                         self._image_generator.enable_numbering,
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
        # Enum-setting tests
        self._intEnum = CamEnum.A
        self.add_setting('intEnum', 'enum',
                         lambda: self._intEnum,
                         lambda val: setattr(self, '_intEnum', val),
                         CamEnum)
        self._dictEnum = 0
        self.add_setting('dictEnum', 'enum',
                         lambda: self._dictEnum,
                         lambda val: setattr(self, '_dictEnum', val),
                         {0:'A', 8:'B', 13:'C', 22:'D'})
        self._listEnum = 0
        self.add_setting('listEnum', 'enum',
                         lambda: self._listEnum,
                         lambda val: setattr(self, '_listEnum', val),
                         ['A', 'B', 'C', 'D'])
        self._tupleEnum = 0
        self.add_setting('tupleEnum', 'enum',
                         lambda: self._tupleEnum,
                         lambda val: setattr(self, '_tupleEnum', val),
                         ('A', 'B', 'C', 'D'))
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = 0
        # Count number of images sent since last enable.
        self._sent = 0

    def _set_error_percent(self, value):
        self._error_percent = value
        self._a_setting = value // 10

    def _set_gain(self, value):
        self._gain = value

    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        _logger.info("Purging buffers.")

    @must_be_initialized
    def _create_buffers(self):
        """Create buffers and store values needed to remove padding later."""
        self._purge_buffers()
        _logger.info("Creating buffers.")

    @must_be_initialized
    def _fetch_data(self):
        if self._acquiring and self._triggered > 0:
            if random.randint(0, 100) < self._error_percent:
                _logger.info('Raising exception')
                raise Exception('Exception raised in TestCamera._fetch_data')
            _logger.info('Sending image')
            time.sleep(self._exposure_time)
            self._triggered -= 1
            # Create an image
            dark = int(32 * np.random.rand())
            light = int(255 - 128 * np.random.rand())
            width = self._roi.width // self._binning.h
            height = self._roi.height // self._binning.v
            image = self._image_generator.get_image(width, height, dark, light, index=self._sent)
            self._sent += 1
            return image

    def abort(self):
        _logger.info("Disabling acquisition; %d images sent.", self._sent)
        if self._acquiring:
            self._acquiring = False

    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        _logger.info('Initializing.')
        time.sleep(0.5)
        self._initialized = True

    def make_safe(self):
        if self._acquiring:
            self.abort()

    def _on_disable(self):
        self.abort()

    @must_be_initialized
    def _on_enable(self):
        _logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        self._create_buffers()
        self._acquiring = True
        self._sent = 0
        _logger.info("Acquisition enabled.")
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

    @must_be_initialized
    def soft_trigger(self):
        _logger.info('Trigger received; self._acquiring is %s.',
                     self._acquiring)
        if self._acquiring:
            self._triggered += 1

    def _get_binning(self):
        return self._binning

    @keep_acquiring
    def _set_binning(self, binning):
        self._binning = binning

    def _get_roi(self):
        return self._roi

    @keep_acquiring
    def _set_roi(self, roi):
        self._roi = roi

    def _on_shutdown(self):
        pass


class TestFilterWheel(FilterWheelBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._position = 0

    def get_position(self):
        return self._position

    def set_position(self, position):
        time.sleep(1)
        _logger.info("Setting position to %s", position)
        self._position = position

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass


class TestLaser(devices.LaserDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        _logger.info("Power set to %s.", level)
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
    def __init__(self, n_actuators, **kwargs):
        super().__init__(**kwargs)
        self._n_actuators = n_actuators

    @property
    def n_actuators(self) -> int:
        return self._n_actuators

    def apply_pattern(self, pattern):
        self._validate_patterns(pattern)
        self._current_pattern = pattern

    def get_current_pattern(self):
        return self._current_pattern


class DummySLM(devices.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sim_diffraction_angle = 0.
        self.sequence_params = []
        self.sequence_index = 0

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass

    def set_sim_diffraction_angle(self, theta):
        _logger.info('set_sim_diffraction_angle %f', theta)
        self.sim_diffraction_angle = theta

    def get_sim_diffraction_angle(self):
        return self.sim_diffraction_angle

    def run(self):
        self.enabled = True
        _logger.info('run')
        return

    def stop(self):
        self.enabled = False
        _logger.info('stop')
        return

    def get_sim_sequence(self):
        return self.sequence_params

    def set_sim_sequence(self, seq):
        _logger.info('set_sim_sequence')
        self.sequence_params = seq
        return

    def get_sequence_index(self):
        return self.sequence_index


class DummyDSP(devices.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._digi = 0
        self._ana = [0,0,0,0]
        self._client = None
        self._actions = []

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass

    def Abort(self):
        _logger.info('Abort')

    def WriteDigital(self, value):
        _logger.info('WriteDigital: %s', bin(value))
        self._digi = value

    def MoveAbsolute(self, aline, pos):
        _logger.info('MoveAbsoluteADU: line %d, value %d', aline, pos)
        self._ana[aline] = pos

    def arcl(self, mask, pairs):
        _logger.info('arcl: %s, %s', mask, pairs)

    def profileSet(self, pstr, digitals, *analogs):
        _logger.info('profileSet ...')
        _logger.info('... ', pstr)
        _logger.info('... ', digitals)
        _logger.info('... ', analogs)

    def DownloadProfile(self):
        _logger.info('DownloadProfile')

    def InitProfile(self, numReps):
        _logger.info('InitProfile')

    def trigCollect(self, *args, **kwargs):
        _logger.info('trigCollect: ... ')
        _logger.info(args)
        _logger.info(kwargs)

    def ReadPosition(self, aline):
        _logger.info('ReadPosition   : line %d, value %d',
                     aline, self._ana[aline])
        return self._ana[aline]

    def ReadDigital(self):
        _logger.info('ReadDigital: %s', bin(self._digi))
        return self._digi

    def PrepareActions(self, actions, numReps=1):
        _logger.info('PrepareActions')
        self._actions = actions
        self._repeats = numReps

    def RunActions(self):
        _logger.info('RunActions ...')
        for i in range(self._repeats):
            for a in self._actions:
                _logger.info(a)
                time.sleep(a[0] / 1000.)
        if self._client:
            self._client.receiveData("DSP done")
        _logger.info('... RunActions done.')

    def receiveClient(self, *args, **kwargs):
        ## XXX: maybe this should be on its own mixin instead of on DataDevice
        return devices.DataDevice.receiveClient(self, *args, **kwargs)

    def set_client(self, *args, **kwargs):
        ## XXX: maybe this should be on its own mixin instead of on DataDevice
        return devices.DataDevice.set_client(self, *args, **kwargs)
