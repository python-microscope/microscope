#!/usr/bin/env python3

## Copyright (C) 2016-2017 Mick Phillips <mick.phillips@gmail.com>
## Copyright (C) 2019 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
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
import logging
import queue
import time
from io import BytesIO

import numpy as np
import picamera
import picamera.array
import RPi.GPIO as GPIO

import microscope.abc
from microscope import ROI, Binning, TriggerMode, TriggerType
from microscope.abc import keep_acquiring


GPIO_Trigger = 21
GPIO_CAMLED = 5

_logger = logging.getLogger(__name__)


# Trigger types.
@enum.unique
class TrgSourceMap(enum.Enum):
    SOFTWARE = TriggerType.SOFTWARE
    EDGE_RISING = TriggerType.RISING_EDGE


class PiCamera(microscope.abc.Camera):
    def __init__(self, *args, **kwargs):
        super(PiCamera, self).__init__(**kwargs)
        # example parameter to allow setting.
        #        self.add_setting('_error_percent', 'int',
        #                         lambda: self._error_percent,
        #                         self._set_error_percent,
        #                         lambda: (0, 100))
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = False
        self.camera = None
        # Region of interest.
        self.roi = ROI(None, None, None, None)
        # Cycle time
        self.exposure_time = 0.001  # in seconds
        self.cycle_time = self.exposure_time
        # initialise in soft trigger mode
        self._trigger_type = TriggerType.SOFTWARE
        # setup hardware triggerline
        GPIO.setmode(GPIO.BCM)
        # GPIO trigger line is an input
        GPIO.setup(GPIO_Trigger, GPIO.IN)
        # GPIO control over camera LED is an output
        GPIO.setup(GPIO_CAMLED, GPIO.OUT)
        # add trigger to settings
        trg_source_names = [x.name for x in TrgSourceMap]
        # set up queue to store images as they are acquired
        self._queue = queue.Queue()
        self._awb_modes = picamera.PiCamera.AWB_MODES
        self._iso_modes = [0, 100, 200, 320, 400, 500, 640, 800]

        def _trigger_source_setter(index: int) -> None:
            trigger_type = TrgSourceMap[trg_source_names[index]].value
            self.set_trigger(trigger_type, self.trigger_mode)

        self.add_setting(
            "trig source",
            "enum",
            lambda: TrgSourceMap(self._trigger_type).name,
            _trigger_source_setter,
            trg_source_names,
        )
        self.add_setting(
            "AWB",
            "enum",
            lambda: self._awb_modes[self.get_awb_mode()],
            lambda awb: self.set_awb_mode(awb),
            values=(list(self._awb_modes.keys())),
        )

        self.add_setting(
            "ISO",
            "enum",
            lambda: self._iso_modes.index(self.camera.iso),
            lambda iso: self.set_iso_mode(iso),
            values=(self._iso_modes),
        )

        # self.add_setting(
        #     "pixel size",
        #     "float",
        #     lambda: self._pixel_size,
        #     lambda pxsz: setattr(self, "_pixel_size", pxsz),
        #     # technically should be: (nextafter(0.0, inf), nextafter(inf, 0.0))
        #     values=(0.0, float("inf")),
        # )
        self.initialize()

    def get_awb_mode(self):
        return self.camera.awb_mode

    def set_awb_mode(self, val):
        for key, value in self._awb_modes.items():
            if value == val:
                self.camera.awb_mode = key

    def set_iso_mode(self, val):
        self.camera.iso = self._iso_modes[val]

    def HW_trigger(self, channel):
        """Function called by GPIO interupt, needs to trigger image capture"""
        with picamera.array.PiYUVArray(self.camera) as output:
            self.camera.capture(output, format="yuv", use_video_port=False)
            self._queue.put(
                output.array[
                    self.roi.top : self.roi.top + self.roi.height,
                    self.roi.left : self.roi.left + self.roi.width,
                    0,
                ]
            )

    def _fetch_data(self):
        try:
            data = self._queue.get_nowait()
        except queue.Empty:
            return None
        _logger.info("Sending image")
        return data

    def initialize(self):
        """Initialise the Pi Camera camera.
        Open the connection, connect properties and populate settings dict.
        """
        if not self.camera:
            try:
                # initialise camera in still image mode.
                self.camera = picamera.PiCamera(sensor_mode=2)
            except:
                raise Exception("Problem opening camera.")
        _logger.info("Initializing camera.")
        self.camversion = self.camera.revision
        _logger.info("cam version " + self.camversion)

        # create img buffer to hold images.
        # disable camera LED by default
        self.setLED(False)
        self.set_awb_mode(0)  # set auto white balance to off
        self._get_sensor_shape()
        # default to full image at init.
        self._set_roi(
            ROI(
                0,
                0,
                self.camera.resolution.width,
                self.camera.resolution.height,
            )
        )

    def make_safe(self):
        if self._acquiring:
            self.abort()

    def _do_disable(self):
        self.abort()

    def _do_shutdown(self):
        self._do_disable()
        self.camera.close()

    def _do_enable(self):
        _logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        # actually start camera
        if not self.camera:
            self.initialize()
        self._acquiring = True
        _logger.info("Acquisition enabled.")
        return True

    def abort(self):
        _logger.info("Disabling acquisition.")
        if self._acquiring:
            self._acquiring = False

    def set_trigger(self, ttype: TriggerType, tmode: TriggerMode) -> None:
        if ttype == self._trigger_type:
            return
        elif ttype == TriggerType.SOFTWARE:
            GPIO.remove_event_detect(GPIO_Trigger)
            self._trigger_type = TriggerType.SOFTWARE
        elif ttype == TriggerType.RISING_EDGE:
            GPIO.add_event_detect(
                GPIO_Trigger,
                GPIO.RISING,
                callback=self.HW_trigger,
                bouncetime=10,
            )
            self._trigger_type = TriggerType.RISING_EDGE

    @property
    def trigger_mode(self) -> TriggerMode:
        #        if self._trigger_type==devices.TRIGGER_BEFORE:
        return TriggerMode.ONCE

    #        else:
    #            return TriggerMode.ONCE

    @property
    def trigger_type(self) -> TriggerType:
        return self._trigger_type

    def _get_roi(self):
        """Return the current ROI (left, top, width, height)."""
        return self.roi

    def _set_binning(self, h_bin, v_bin):
        return True

    def _get_binning(self):
        return Binning(1, 1)

    @keep_acquiring
    def _set_roi(self, region):
        """Set the ROI to the name tuple ROI(left, top, width, height)."""
        self.roi = region

    # set camera LED status, off is best for microscopy.
    def setLED(self, state=False):
        GPIO.output(GPIO_CAMLED, state)

    def set_exposure_time(self, value):
        # frame rate has to be adjusted as well as max exposure time is
        # 1/framerate.
        # picam v1.3 I have has limit 1/6 to 90 fps
        # exposure time can be shorter than frame rate bound but not longer
        value = min(value, 6.0)
        fr = max(value, 1.0 / 90.0)
        self.set_framerate(1.0 / fr)
        # exposure times are set in us.
        self.camera.shutter_speed = int(value * 1.0e6)

    def get_exposure_time(self):
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        return self.camera.exposure_speed * 1.0e-6

    def get_cycle_time(self):
        # fudge to make it work initially
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        # pi 4 camera module v 1.3 minimum reliable time to capture and
        # download a frame appears to be .7 s.
        return self.camera.exposure_speed * 1.0e-6 + 0.7

    def get_framerate(self):
        return float(self.camera.framerate)

    def set_framerate(self, rate):
        #       rate= max (rate, self.camera.framerate_range.low)
        #       rate= min (rate, self.camera.framerate_range.high)
        self.camera.framerate = rate
        return float(self.camera.framerate)

    def _get_sensor_shape(self):
        if self.camversion == "ov5647":  # picam version 1
            self.camera.resolution = (2592, 1944)
        # faqll back to defualt if not set above.
        res = self.camera.resolution
        return (res.width, res.height)

    def zoom(self, roi):
        # picamera zoom parameter returns an roi but defined as floats and not
        # in pixels
        x = roi[0] / self.camera.resolution.width
        width = (roi[2]) / self.camera.resolution.width
        y = roi[1] / self.camera.resolution.height
        height = (roi[3]) / self.camera.resolution.height
        print("using roi to set zoom", roi, (x, y, width, height))
        self.camera.zoom = (x, y, width, height)

    def _do_trigger(self):
        self.soft_trigger()

    def soft_trigger(self):
        _logger.info(
            "Trigger received; self._acquiring is %s." % self._acquiring
        )
        if self._acquiring:
            with picamera.array.PiYUVArray(self.camera) as output:
                self.camera.capture(output, format="yuv", use_video_port=False)
                self._queue.put(
                    output.array[
                        self.roi.top : self.roi.top + self.roi.height,
                        self.roi.left : self.roi.left + self.roi.width,
                        0,
                    ]
                )


# ongoing implemetation notes

# should be able to use rotation and hflip to set specific output image
# rotations

# roi's can be set with the zoom function, default is (0,0,1,1)
# meaning all the data. However this is no help as the grab is still
# just as slow

# Need to setup a buffer for harware triggered data aquisition so we can
# call the acquisition and then download the data at our leasure
