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

"""A dummy filter wheel class. """
from microscope import devices
from future.utils import iteritems
import Pyro4
import time

class TestFilterwheel(devices.Device):
    def __init__(self, filters=[], *args, **kwargs):
        super(TestFilterwheel, self).__init__()
        self._utype = devices.UFILTER
        self.__position = 0
        self._filters = dict(map(lambda f: (f[0], f[1:]), filters))
        self._inv_filters = {val:key for key, val in iteritems(self._filters)}
        # The position as an integer.
        self.add_setting('position',
                         'int',
                         lambda: self._position,
                         lambda val: setattr(self, '_position', val),
                         (0,5))
        # The selected filter.
        self.add_setting('filter',
                         'enum',
                         lambda: self._filters[self._position],
                         lambda val: setattr(self, '_position', self._inv_filters[val]),
                         self._filters.values)

    @property
    def _position(self):
        return self.__position

    @_position.setter
    def _position(self, value):
        time.sleep(1)
        self.__position = value


    @Pyro4.expose
    def get_filters(self):
        return [(index, filt) for index, filt in iteritems(self._filters)]

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass