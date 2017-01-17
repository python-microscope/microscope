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
import abc
from microscope import devices
import Pyro4
import time

class FilterWheelBase(devices.Device):
    __metaclass__ = abc.ABCMeta

    def __init__(self, filters, *args, **kwargs):
        super(FilterWheelBase, self).__init__(*args, **kwargs)
        self._utype = devices.UFILTER
        self._filters = dict(map(lambda f: (f[0], f[1:]), filters))
        self._inv_filters = {val: key for key, val in self._filters.items()}
        # The position as an integer.
        self.add_setting('position',
                         'int',
                         self._get_position,
                         self._set_position,
                         (0, 5))
        # The selected filter.
        self.add_setting('filter',
                         'enum',
                         lambda: self._filters[self._get_position()],
                         lambda val: self._set_position(self._inv_filters[val]),
                         self._filters.values)

    @abc.abstractmethod
    def _get_position(self):
        return self._position

    @abc.abstractmethod
    def _set_position(self, position):
        self._position = position

    @Pyro4.expose
    def get_filters(self):
        return self._filters.items()


class TestFilterwheel(FilterWheelBase):
    def __init__(self, filters=[], *args, **kwargs):
        super(TestFilterwheel, self).__init__(filters, *args, **kwargs)
        self._position = 0

    def _get_position(self):
        return self._position

    def _set_position(self, position):
        time.sleep(1)
        self._position = position

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass
