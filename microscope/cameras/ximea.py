#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016-2017 Mick Phillips <mick.phillips@gmail.com>
## Copyright (C) 2017 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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
import typing

import numpy as np
from ximea import xiapi

from microscope import devices


_logger = logging.getLogger(__name__)


class XimeaCamera(devices.CameraDevice):
    """Ximea cameras

    Args:
        serial_number (str): the serial number of the camera to
            connect to.  It can be set to `None` if there is only
            camera on the system.
    """
    def __init__(self, serial_number: typing.Optional[str] = None,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self._acquiring = False
        self._exposure_time = 0.1
        self._handle = xiapi.Camera()
        self._serial_number = serial_number
        self._roi = devices.ROI(None,None,None,None)

    def _fetch_data(self) -> typing.Optional[np.ndarray]:
        if not self._acquiring:
            return None

        try:
            self._handle.get_image(self.img, timeout=1)
        except Exception as err:
            # err.status may not exist so use getattr (see
            # https://github.com/python-microscope/vendor-issues/issues/2)
            if getattr(err, 'status', None) == 10: # Timeout
                return None
            else:
                raise err

        data = self.img.get_image_data_numpy() # type: np.ndarray
        _logger.info("Fetched imaged with dims %s and size %s.",
                     data.shape, data.size)
        return data

    def abort(self):
        _logger.info('Disabling acquisition.')
        if self._acquiring:
            self._handle.stop_acquisition()
            self._acquiring = False

    def initialize(self) -> None:
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        n_cameras = self._handle.get_number_devices()

        if self._serial_number is None:
            if n_cameras > 1:
                raise Exception('more than one Ximea camera found but the'
                                ' serial_number argument was not specified')
            _logger.info('serial_number is not specified but there is only one'
                         ' camera on the system')
            self._handle.open_device()
        else:
            _logger.info('opening camera with serial number \'%s\'',
                         self._serial_number)
            self._handle.open_device_by_SN(self._serial_number)
            # Camera.dev_id defaults to zero.  However, after opening
            # the device by serial number is is not updated (see
            # https://github.com/python-microscope/vendor-issues/issues/1).
            # So we manually iterate over each possible device ID and
            # modify dev_id until it behaves as it should.  If we
            # don't fix this and there are multiple cameras connected,
            # some of the handle methods will return info from another
            # camera.
            for dev_id in range(n_cameras):
                self._handle.dev_id = dev_id
                if (self._serial_number.encode()
                    == self._handle.get_device_info_string('device_sn')):
                    break
            else:
                raise Exception('failed to get DevId for device with SN %s'
                                % self._serial_number)

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

    def _on_shutdown(self) -> None:
        if self._acquiring:
            self._handle.stop_acquisition()
        if self._handle.CAM_OPEN:
            # We check CAM_OPEN instead of try/catch an exception
            # because if the camera failed initialisation, XiApi fails
            # hard with error code -1009 (unknown) since the internal
            # device handler is NULL.
            self._handle.close_device()
        else:
            _logger.warning('shutdown() called but camera was already closed')
