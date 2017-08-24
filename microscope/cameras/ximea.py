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
from microscope.filterwheel import FilterWheelBase

#import ximea python module.
from ximea import xiapi


# Trigger mode to type.
TRIGGER_MODES = {
    'internal': None,
    'external': devices.TRIGGER_BEFORE,
    'external start': None,
    'external exposure': devices.TRIGGER_DURATION,
    'software': devices.TRIGGER_SOFT,
}

    #trig types from define file....
    # #structure containing information about trigger source
# XI_TRG_SOURCE = { 
#     "XI_TRG_OFF": c_uint(0),    #Camera works in free run mode.
#     "XI_TRG_EDGE_RISING": c_uint(1),    #External trigger (rising edge).
#     "XI_TRG_EDGE_FALLING": c_uint(2),    #External trigger (falling edge).
#     "XI_TRG_SOFTWARE": c_uint(3),    #Software(manual) trigger.
#     "XI_TRG_LEVEL_HIGH": c_uint(4),    #Specifies that the trigger is considered valid as long as the level of the source signal is high.
#     "XI_TRG_LEVEL_LOW": c_uint(5),    #Specifies that the trigger is considered valid as long as the level of the source signal is low.
#    }




@Pyro4.expose
@Pyro4.behavior('single')
class XimaeCamera(devices.CameraDevice):
    def __init__(self, *args, **kwargs):
        super(XimaeCamera, self).__init__(**kwargs)
#example parameter to allow setting.
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
        #time.sleep(0.5)

    def _fetch_data(self):
        if self._acquiring and self._triggered:
            self.handle.get_image(self.img)
            self._logger.info('Sending image')
            self._triggered = False
            return self.img.get_image_data_raw()

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
        #create img buffer to hold images.
        self.img=xiapi.Image()

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
        #actually start camera
        self.handle.start_acquisition()
        self._logger.info("Acquisition enabled.")
        return True

    def set_exposure_time(self, value):
        #exposure times are set in us.
        self.handle.set_exposure(value*1.0E6)

    def get_exposure_time(self):
        #exposure times are in us, so multiple by 1E-6 to get seconds.
        return (self.handle.get_exposure()*1.0E-6) 

    def get_cycle_time(self):
        return (self.handle.get_exposure()*1.0E-6)

    def _get_sensor_shape(self):
        return (self.img.width,self.image.height)

    #trig types from define file....
    # #structure containing information about trigger source
# XI_TRG_SOURCE = { 
#     "XI_TRG_OFF": c_uint(0),    #Camera works in free run mode.
#     "XI_TRG_EDGE_RISING": c_uint(1),    #External trigger (rising edge).
#     "XI_TRG_EDGE_FALLING": c_uint(2),    #External trigger (falling edge).
#     "XI_TRG_SOFTWARE": c_uint(3),    #Software(manual) trigger.
#     "XI_TRG_LEVEL_HIGH": c_uint(4),    #Specifies that the trigger is considered valid as long as the level of the source signal is high.
#     "XI_TRG_LEVEL_LOW": c_uint(5),    #Specifies that the trigger is considered valid as long as the level of the source signal is low.
#    }

    def get_trigger_type(self):
        trig=self.handle.get_trigger_source()
        return devices.TRIGGER_SOFT

    def set_trigger_type(self, trigger):
        if (trigger == devices.TRIGGER_SOFT):
            self.handle.set_triger_source(XI_TG_SOURCE['Xi_TRG_SOFTWARE'])
        elif (trigger == devices.TRIGGER_BEFORE):
            self.handle.set_triger_source(XI_TG_SOURCE['Xi_TRG_EDGE_RISING'])
            #define digial input mode of trigger
            self.handle.set_gpi_selector(1)
            self.handle.set_gpi_mode(XI_GPI_TRIGGER)

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
        if self_.acquiring:
            self.handle.stop_acquisition()
        self.handle.close_device()

