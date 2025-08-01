#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
## Copyright (C) 2022 Ian Dobbie <ian.dobbie@gmail.com>
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

"""Simulated devices for use during development.

This module provides a series of test devices, which mimic real
hardware behaviour.  They implement the different ABC.

"""

import logging
import math
import random
import time
from typing import Mapping, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import microscope
import microscope._utils
import microscope.abc

_logger = logging.getLogger(__name__)


## PIL 9.2 deprecated ImageFont.getsize and PIL 10.0 removed it in
## favour of ImageFont.getbbox.  When we can require PIL>=9.2, we can
## remove this (issue #282)
_IMAGEFONT_HAS_GETBBOX = hasattr(ImageFont.ImageFont, "getbbox")


def _theta_generator():
    """A generator that yields values between 0 and 2*pi"""
    TWOPI = 2 * np.pi
    th = 0
    while True:
        yield th
        th = (th + 0.01 * TWOPI) % TWOPI


class _ImageGenerator:
    """Generates test images, with methods for configuration via a Setting."""

    def __init__(self):
        self._methods = (
            self.noise,
            self.gradient,
            self.sawtooth,
            self.one_gaussian,
            self.black,
            self.white,
        )
        self._method_index = 0
        self._datatypes = (np.uint8, np.uint16, float)
        self._datatype_index = 0
        self._theta = _theta_generator()
        self.numbering = True
        # Font for rendering counter in images.
        self._font = ImageFont.load_default()

    def enable_numbering(self, enab):
        self.numbering = enab

    def get_data_types(self):
        return (t.__name__ for t in self._datatypes)

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
        # return Image.fromarray(m(width, height, dark, light).astype(d), 'L')
        data = m(width, height, dark, light).astype(d)
        if self.numbering and index is not None:
            text = "%d" % index
            if _IMAGEFONT_HAS_GETBBOX:
                size = self._font.getbbox(text)[2:]
            else:
                size = self._font.getsize(text)
            size = tuple(d + 2 for d in size)  # padding
            img = Image.new("L", size)
            ctx = ImageDraw.Draw(img)
            ctx.text((1, 1), text, fill=light)
            data[0 : size[1], 0 : size[0]] = np.asarray(img)
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
            value = 1.0
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
        return dark + light * np.exp(
            -((xx - x0) ** 2 + (yy - y0) ** 2) / (2 * sigma**2)
        )

    def sawtooth(self, w, h, dark, light):
        """A sawtooth gradient that rotates about 0,0."""
        th = next(self._theta)
        xx, yy = np.meshgrid(range(w), range(h))
        wrap = 0.1 * max(xx.max(), yy.max())
        return dark + light * ((np.sin(th) * xx + np.cos(th) * yy) % wrap) / (
            wrap
        )


class SimulatedCamera(
    microscope._utils.OnlyTriggersOnceOnSoftwareMixin, microscope.abc.Camera
):
    def __init__(self, sensor_shape: Tuple[int, int] = (512, 512), **kwargs):
        super().__init__(**kwargs)
        # Binning and ROI
        self._sensor_shape = sensor_shape
        self._roi = microscope.ROI(0, 0, *sensor_shape)
        self._binning = microscope.Binning(1, 1)
        self._shuttering_mode = microscope.ElectronicShutteringMode.GLOBAL
        # Function used to generate test image
        self._image_generator = _ImageGenerator()
        self.add_setting(
            "image pattern",
            "enum",
            self._image_generator.method,
            self._image_generator.set_method,
            self._image_generator.get_methods,
        )
        self.add_setting(
            "image data type",
            "enum",
            self._image_generator.data_type,
            self._image_generator.set_data_type,
            self._image_generator.get_data_types,
        )
        self.add_setting(
            "display image number",
            "bool",
            lambda: self._image_generator.numbering,
            self._image_generator.enable_numbering,
            None,
        )
        # Software buffers and parameters for data conversion.
        self._a_setting = 0
        self.add_setting(
            "a_setting",
            "int",
            lambda: self._a_setting,
            lambda val: setattr(self, "_a_setting", val),
            lambda: (1, 100),
        )
        self._error_percent = 0
        self.add_setting(
            "_error_percent",
            "int",
            lambda: self._error_percent,
            self._set_error_percent,
            lambda: (0, 100),
        )
        self._gain = 0
        self.add_setting(
            "gain",
            "int",
            lambda: self._gain,
            self._set_gain,
            lambda: (0, 8192),
        )
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

    def _create_buffers(self):
        """Create buffers and store values needed to remove padding later."""
        self._purge_buffers()
        _logger.info("Creating buffers.")

    def _fetch_data(self):
        if self._acquiring and self._triggered > 0:
            if random.randint(0, 100) < self._error_percent:
                _logger.info("Raising exception")
                raise microscope.DeviceError(
                    "Exception raised in SimulatedCamera._fetch_data"
                )
            _logger.info("Sending image")
            time.sleep(self._exposure_time)
            self._triggered -= 1
            # Create an image
            dark = int(32 * np.random.rand())
            light = int(255 - 128 * np.random.rand())
            width = self._roi.width // self._binning.h
            height = self._roi.height // self._binning.v
            image = self._image_generator.get_image(
                width, height, dark, light, index=self._sent
            )
            self._sent += 1
            return image

    def abort(self):
        _logger.info("Disabling acquisition; %d images sent.", self._sent)
        if self._acquiring:
            self._acquiring = False

    def _do_disable(self):
        self.abort()

    def _do_enable(self):
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
        return self._sensor_shape


    def _get_shuttering_mode(self):
        return self._shuttering_mode

    def _set_shuttering_mode(self,
                             mode: microscope.ElectronicShutteringMode):
        self._shuttering_mode = mode

    def soft_trigger(self):
        # deprecated, use self.trigger()
        self.trigger()

    def _do_trigger(self) -> None:
        _logger.info(
            "Trigger received; self._acquiring is %s.", self._acquiring
        )
        if self._acquiring:
            self._triggered += 1

    def _get_binning(self):
        return self._binning

    @microscope.abc.keep_acquiring
    def _set_binning(self, binning):
        self._binning = binning

    def _get_roi(self):
        return self._roi

    @microscope.abc.keep_acquiring
    def _set_roi(self, roi):
        self._roi = roi

    def _do_shutdown(self) -> None:
        pass


class SimulatedController(microscope.abc.Controller):
    def __init__(self, devices: Mapping[str, microscope.abc.Device]) -> None:
        self._devices = devices.copy()

    @property
    def devices(self) -> Mapping[str, microscope.abc.Device]:
        return self._devices


class SimulatedFilterWheel(microscope.abc.FilterWheel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._position = 0

    def _do_get_position(self):
        return self._position

    def _do_set_position(self, position):
        _logger.info("Setting position to %s", position)
        self._position = position

    def _do_shutdown(self) -> None:
        pass


class SimulatedLightSource(
    microscope._utils.OnlyTriggersBulbOnSoftwareMixin,
    microscope.abc.LightSource,
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._power = 0.0
        self._emission = False

    def get_status(self):
        return [str(x) for x in (self._emission, self._power, self._set_point)]

    def _do_enable(self):
        self._emission = True
        return self._emission

    def _do_shutdown(self) -> None:
        pass

    def _do_disable(self):
        self._emission = False
        return self._emission

    def get_is_on(self):
        return self._emission

    def _do_set_power(self, power: float) -> None:
        _logger.info("Power set to %s.", power)
        self._power = power

    def _do_get_power(self) -> float:
        if self._emission:
            return self._power
        else:
            return 0.0


class SimulatedDeformableMirror(
    microscope._utils.OnlyTriggersOnceOnSoftwareMixin,
    microscope.abc.DeformableMirror,
):
    def __init__(self, n_actuators, **kwargs):
        super().__init__(**kwargs)
        self._n_actuators = n_actuators

    def _do_shutdown(self) -> None:
        pass

    @property
    def n_actuators(self) -> int:
        return self._n_actuators

    def _do_apply_pattern(self, pattern):
        self._current_pattern = pattern

    def get_current_pattern(self):
        """Method for debug purposes only.

        This method is not part of the DeformableMirror ABC, it only
        exists on this test device to help during development.
        """
        return self._current_pattern


class SimulatedStageAxis(microscope.abc.StageAxis):
    def __init__(self, limits: microscope.AxisLimits) -> None:
        super().__init__()
        self._limits = limits
        # Start axis in the middle of its range.
        self._position = self._limits.lower + (
            (self._limits.upper - self._limits.lower) / 2.0
        )

    @property
    def position(self) -> float:
        return self._position

    @property
    def limits(self) -> microscope.AxisLimits:
        return self._limits

    def move_by(self, delta: float) -> None:
        self.move_to(self._position + delta)

    def move_to(self, pos: float) -> None:
        if pos < self._limits.lower:
            self._position = self._limits.lower
        elif pos > self._limits.upper:
            self._position = self._limits.upper
        else:
            self._position = pos


class SimulatedStage(microscope.abc.Stage):
    """A test stage with any number of axis.

    Args:
        limits: map of test axis to be created and their limits.

    .. code-block:: python

        # Test XY motorized stage of square shape:
        xy_stage = SimulatedStage({
            'X' : AxisLimits(0, 5000),
            'Y' : AxisLimits(0, 5000),
        })

        # XYZ stage, on rectangular shape and negative coordinates:
        xyz_stage = SimulatedStage({
            'X' : AxisLimits(-5000, 5000),
            'Y' : AxisLimits(-10000, 12000),
            'Z' : AxisLimits(0, 1000),
        })

    """

    def __init__(
        self, limits: Mapping[str, microscope.AxisLimits], **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._axes = {
            name: SimulatedStageAxis(lim) for name, lim in limits.items()
        }

    def _do_shutdown(self) -> None:
        pass

    def may_move_on_enable(self) -> bool:
        return False

    @property
    def axes(self) -> Mapping[str, microscope.abc.StageAxis]:
        return self._axes

    def move_by(self, delta: Mapping[str, float]) -> None:
        for name, rpos in delta.items():
            self.axes[name].move_by(rpos)

    def move_to(self, position: Mapping[str, float]) -> None:
        for name, pos in position.items():
            self.axes[name].move_to(pos)


class SimulatedDigitalIO(microscope.abc.DigitalIO):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = [None] * self._numLines
        self.testinput = False
        self.inputtime = time.time()

    def set_IO_state(self, line: int, state: bool) -> None:
        _logger.info("Line %d set IO state %s" % (line, str(state)))
        self._IOMap[line] = state
        if not state:
            # this is an input so needs to have a definite value,
            # default to False if not already set. If set leave alone
            if self._cache[line] == None:
                self._cache[line] = False

    def get_IO_state(self, line: int) -> bool:
        return self._IOMap[line]

    def write_line(self, line: int, state: bool):
        _logger.debug("Line %d set IO state %s" % (line, str(state)))
        self._cache[line] = state

    def read_line(self, line: int) -> bool:
        _logger.debug("Line %d returns %s" % (line, str(self._cache[line])))
        return self._cache[line]

    def _do_shutdown(self) -> None:
        pass

    # functions required as we are DataDevice returning data to the server.
    def _fetch_data(self):
        if (time.time() - self.inputtime) > 5.0:
            self.testinput = not self.testinput
            self.inputtime = time.time()
            _logger.debug("Line %d returns %s" % (3, self.testinput))
            self._cache[3] = self.testinput
            return (3, self.testinput)
        return None

    def abort(self):
        pass

    def _do_enable(self):
        return True


# DIO still to do:
# raise exception if writing to a read line and vis-versa
# raise exception if line <0 or line>num_lines
# read all lines to return True,Flase if readable and None if an output
#


class SimulatedValueLogger(microscope.abc.ValueLogger):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = [None] * self._numSensors
        self.lastDataTime = time.time()

    def initialize(self):
        # init simulated sensors
        for i in range(self._numSensors):
            self._cache[i] = 20 + i

    # functions required as we are DataDevice returning data to the server.
    def _fetch_data(self):
        if (time.time() - self.lastDataTime) > 5.0:
            self.lastDataTime = time.time()
            return self.getValues()
        return None

    def getValues(self):
        for i in range(self._numSensors):
            self._cache[i] = (
                19.5
                + i
                + 5 * math.sin(self.lastDataTime / 100)
                + random.random()
            )
            _logger.debug("Sensors %d returns %s" % (i, self._cache[i]))
        return self._cache

    def abort(self):
        pass

    def _do_enable(self):
        return True

    def _do_shutdown(self) -> None:
        pass
