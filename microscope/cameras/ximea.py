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

import time

import Pyro4
import numpy as np

from microscope import devices
from microscope.devices import keep_acquiring

# import ximea python module.
from ximea import xiapi

trigger_type_to_value = {
    0: 'XI_TRG_SOFTWARE',
    1: 'XI_TRG_EDGE_RISING',
}


@Pyro4.expose
@Pyro4.behavior('single')
class XimeaCamera(devices.CameraDevice):
    def __init__(self, *args, **kwargs):
        super(XimeaCamera, self).__init__(**kwargs)
        # example parameter to allow setting.
        #        self.add_setting('_error_percent', 'int',
        #                         lambda: self._error_percent,
        #                         self._set_error_percent,
        #                         lambda: (0, 100))
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = False

    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        self._logger.info("Purging buffers.")

    def _create_buffers(self):
        """Create buffers and store values needed to remove padding later."""
        self._purge_buffers()
        self._logger.info("Creating buffers.")
        # time.sleep(0.5)

    def _fetch_data(self):
        trigger_type = self.handle.get_trigger_source()
        if trigger_type == 'XI_TRG_SOFTWARE':
            if self._acquiring and self._triggered:
                try:
                    self.handle.get_image(self.img)
                    data = self.img.get_image_data_numpy()
                    self._logger.info("Fetched imaged with dims %s and size %s." % (data.shape, data.size))
                    self._logger.info('Sending image')
                    self._triggered = False
                    return self.img.get_image_data_numpy()
                except Exception as err:
                    self._logger.info('Get image error %s' % err)
                    raise
        elif trigger_type == 'XI_TRG_EDGE_RISING':
            if self._acquiring:
                try:
                    self.handle.get_image(self.img)
                    data = self.img.get_image_data_numpy()
                    self._logger.info("Fetched imaged with dims %s and size %s." % (data.shape, data.size))
                    self._logger.info('Sending image')
                    return self.img.get_image_data_numpy()
                except Exception as err:
                    if err.args is xiapi.Xi_error(10).args:
                        return None
                    else:
                        self._logger.info('Get image error %s' % err)

    def abort(self):
        self._logger.info('Disabling acquisition.')
        if self._acquiring:
            self._acquiring = False
        self.handle.stop_acquisition()

    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """

        try:
            self.handle = xiapi.Camera()
            self.handle.open_device()
        except:
            raise Exception("Problem opening camera.")
        if self.handle == None:
            raise Exception("No camera opened.")

        #        for name, var in sorted(self.__dict__.items()):
        self._logger.info('Initializing.')
        # Try set camera into rising-edge hardware trigger mode. If that can't be done
        # set it to software trigger mode
        try:
            self.handle.set_trigger_source('XI_TRG_EDGE_RISING')
        except:
            self.handle.set_trigger_source('XI_TRG_SOFTWARE')
        # create img buffer to hold images.

        self.img = xiapi.Image()

    def get_current_image(self):
        self._logger.info('In get_current_image')
        try:
            if self._acquiring and self._triggered:
                self.handle.get_image(self.img)
                data = self.img.get_image_data_numpy()
                self._logger.info("Fetched imaged with dims %s and size %s." % (data.shape, data.size))
                self._logger.info('Sending image')
                self._triggered = False
                return data
        except Exception as e:
            self._logger.info("Error in ximeaCam: %s" % (e))
            raise Exception(str(xiapi.Xi_error(e.status)))

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
        # actually start camera
        self.handle.start_acquisition()
        self._logger.info("Acquisition enabled.")
        return True

    #    def enable(self):
    #        self._on_enable()

    def set_exposure_time(self, value):
        # exposure times are set in us.
        try:
            self.handle.set_exposure(int(value * 1000000))
        except Exception as err:
            self._logger.debug("set_exposure_time exception: %s" % err)

    def get_exposure_time(self):
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        return (self.handle.get_exposure() * 1.0E-6)

    def get_cycle_time(self):
        return (self.handle.get_exposure() * 1.0E-6)

    def _get_sensor_shape(self):
        return (self.handle.get_width(), self.handle.get_height())

    def get_trigger_source(self):
        return (self.handle.get_trigger_source())

    def get_trigger_type(self):
        trig = self.handle.get_trigger_source()
        self._logger.info("called get trigger type %s" % trig)
        if trig == 'XI_TRG_SOFTWARE':
            return devices.TRIGGER_SOFT
        elif trig == 'XI_TRG_EDGE_RISING':
            return devices.TRIGGER_BEFORE

    def set_trigger_source(self, trig):
        self._logger.info("Set trigger source %s" % (trig))
        reenable = False
        if self._acquiring:
            self.abort()
            reenable = True
        result = self.handle.set_trigger_source(trig)
        self._logger.info("Set trigger source result  %s" % (result))
        if reenable:
            self._on_enable()
        return

    def set_trigger_type(self, trig):
        self._logger.info("Set trigger type %s" % (trig))
        self.abort()

        if trig is 0:
            self.handle.set_trigger_source('XI_TRG_SOFTWARE')
        elif trig is 1:
            self.handle.set_trigger_source('XI_TRG_EDGE_RISING')
            # define digial input mode of trigger
            self.handle.set_gpi_selector('XI_GPI_PORT1')
            self.handle.set_gpi_mode('XI_GPI_TRIGGER')
            self.handle.set_gpo_selector('XI_GPO_PORT1')
            self.handle.set_gpo_mode('XI_GPO_EXPOSURE_ACTIVE')

        self._on_enable()

        result = self.handle.get_trigger_source()
        self._logger.info("Trigger type %s" % result)
        self._logger.info("GPI Selector %s" % self.handle.get_gpi_selector())
        self._logger.info("GPI Mode %s" % self.handle.get_gpi_mode())

        return
        # return(self.handle.set_trigger_source(TRIGGER_MODES[trig]))

    def soft_trigger(self):
        self._logger.info('Soft trigger received; self._acquiring is %s.'
                          % self._acquiring)
        if self._acquiring:
            self.handle.set_trigger_software(True)
            self._triggered = True

    def _get_binning(self):
        return (1, 1)

    @keep_acquiring
    def _set_binning(self, h, v):
        return False

    def _get_roi(self):
        size = self._get_sensor_shape()
        return (0, 0, size[0], size[1])

    @keep_acquiring
    def _set_roi(self, x, y, width, height):
        return False

    def _on_shutdown(self):
        if self._acquiring:
            self.handle.stop_acquisition()
        self.handle.close_device()