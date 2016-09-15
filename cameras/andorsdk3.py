#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import abc
import camera
import devicebase
from PYME.Acquire.Hardware.AndorNeo.SDK3Cam import *


class AndorSDK3(camera.CameraDevice,
                devicebase.FloatingDeviceMixin):
    SDK_INITIALIZED = False
    def __init__(self, *args, **kwargs):
        super(AndorSDK3, self).__init__(**kwargs)
        if not AndorSDK3.SDK_INITIALIZED:
            SDK3.InitialiseLibrary()


    def _fetch_data(self):
        pass


    def abort(self):
        pass


    def enable(self):
        pass


    def disable(self):
        pass


    def initialize(self):
        pass


    def get_id(self):
        pass


    def make_safe(self):
        pass


    def shutdown(self):
        SDK3.FinaliseLibrary()
        pass


    def start_acquisition(self):
        pass


    def get_exposure_time(self):
        return 1.0      