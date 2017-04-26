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
from microscope import devices
import Pyro4

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
        self._power = level

    def get_max_power_mw(self):
        return 100

    def get_power_mw(self):
        return self._power

