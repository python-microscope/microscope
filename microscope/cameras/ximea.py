#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016-2017 Mick Phillips <mick.phillips@gmail.com>
## Copyright (C) 2017 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
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

from ximea import xiapi

from microscope import devices


_logger = logging.getLogger(__name__)


class XimeaCamera(devices.CameraDevice):
    def __init__(self, dev_id=0, **kwargs):
        super().__init__(**kwargs)
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = False
        self._handle = None
        self._dev_id = dev_id
        self._roi = devices.ROI(None,None,None,None)

    def _fetch_data(self):
        if not self._acquiring:
            return

        trigger_type = self._handle.get_trigger_source()
        if trigger_type == 'XI_TRG_SOFTWARE' and not not self._triggered:
            return
        # else, we are either on 1) software trigger mode and have
        # already triggered, in which case there should be an image
        # waiting for us; or 2) any hardware trigger mode, in which
        # case we try to fetch an image and either we get one or it
        # times out if there is none.

        try:
            self._handle.get_image(self.img)
        except Exception as err:
            if getattr(err, 'status', None) == 10:
                # This is a Timeout error
                return
            else:
                raise err

        data = self.img.get_image_data_numpy()
        _logger.info("Fetched imaged with dims %s and size %s.",
                     data.shape, data.size)
        _logger.info('Sending image')
        if trigger_type == 'XI_TRG_SOFTWARE':
            self._triggered = False
        return data

    def abort(self):
        _logger.info('Disabling acquisition.')
        if self._acquiring:
            self._acquiring = False
        self._handle.stop_acquisition()

    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        try:
            self._handle = xiapi.Camera(self._dev_id)
            self._handle.open_device()
        except:
            raise Exception("Problem opening camera.")
        if self._handle is None:
            raise Exception("No camera opened.")

        _logger.info('Initializing.')
        # Try set camera into rising-edge hardware trigger mode.  If
        # that can't be done set it to software trigger mode.
        # TODO: even if the trigger source is set to edge rising, the
        # camera can still be triggered by software.  For now, this
        # lets us work with hardware and software triggers without
        # having a setting for that (but we will need to change this
        # one day). See issue #131.
        try:
            self._handle.set_trigger_source('XI_TRG_EDGE_RISING')
        except:
            self._handle.set_trigger_source('XI_TRG_SOFTWARE')
        # create img buffer to hold images.
        self.img = xiapi.Image()

    def make_safe(self):
        if self._acquiring:
            self.abort()

    def _on_disable(self):
        self.abort()

    def _on_enable(self):
        _logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        self._acquiring = True
        # actually start camera
        self._handle.start_acquisition()
        _logger.info("Acquisition enabled.")
        return True

    def set_exposure_time(self, value):
        # exposure times are set in us.
        try:
            self._handle.set_exposure(int(value * 1000000))
        except Exception as err:
            _logger.debug("set_exposure_time exception: %s", err)

    def get_exposure_time(self):
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        return (self._handle.get_exposure() * 1.0E-6)

    def get_cycle_time(self):
        return (1.0/self._handle.get_framerate())

    def _get_sensor_shape(self):
        return (self._handle.get_width(), self._handle.get_height())

    def get_trigger_source(self):
        return (self._handle.get_trigger_source())

    def get_trigger_type(self):
        trig = self._handle.get_trigger_source()
        _logger.info("called get trigger type %s", trig)
        if trig == 'XI_TRG_SOFTWARE':
            return devices.TRIGGER_SOFT
        elif trig == 'XI_TRG_EDGE_RISING':
            return devices.TRIGGER_BEFORE

    def set_trigger_source(self, trig):
        _logger.info("Set trigger source %s", trig)
        reenable = False
        if self._acquiring:
            self.abort()
            reenable = True
        result = self._handle.set_trigger_source(trig)
        _logger.info("Set trigger source result  %s", result)
        if reenable:
            self._on_enable()
        return

    def set_trigger_type(self, trig):
        _logger.info("Set trigger type %s", trig)
        self.abort()

        if trig is 0:
            self._handle.set_trigger_source('XI_TRG_SOFTWARE')
        elif trig is 1:
            self._handle.set_trigger_source('XI_TRG_EDGE_RISING')
            # define digial input mode of trigger
            self._handle.set_gpi_selector('XI_GPI_PORT1')
            self._handle.set_gpi_mode('XI_GPI_TRIGGER')
            self._handle.set_gpo_selector('XI_GPO_PORT1')
            self._handle.set_gpo_mode('XI_GPO_EXPOSURE_ACTIVE')

        self._on_enable()

        result = self._handle.get_trigger_source()
        _logger.info("Trigger type %s", result)
        _logger.info("GPI Selector %s", self._handle.get_gpi_selector())
        _logger.info("GPI Mode %s", self._handle.get_gpi_mode())

        return

    def soft_trigger(self):
        _logger.info('Soft trigger received; self._acquiring is %s.',
                     self._acquiring)
        if self._acquiring:
            self._handle.set_trigger_software(True)
            self._triggered = True

    def _get_binning(self):
        return (1, 1)

    @devices.keep_acquiring
    def _set_binning(self, h, v):
        return False

    def _get_roi(self):
        return self._roi

    @devices.keep_acquiring
    def _set_roi(self, x, y, width, height):
        self._roi = devices.ROI(x, y, width, height)

    def _on_shutdown(self):
        if self._acquiring:
            self._handle.stop_acquisition()
        self._handle.close_device()
