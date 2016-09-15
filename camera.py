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
class CameraDevice(DataDevice):
    """Adds functionality to DataDevice to support cameras.

    Applies a transform to acquired data in the processing step.
    Defines the interface for cameras.
    Must implement _fetch_data as per DataDevice._fetch_data."""
    def __init__(self):
        # A tuple defining data shape.
        self.dshape = None
        # A data type.
        self.dtype = None
        # A transform to apply to data (fliplr, flipud, rot90)
        self.dtransform = (0, 0, 0)
        super(CameraDevice, self).__init__()
        self.some_setting = 0.
        #self.settings.append()


    def _process_data(self, data):
        """Apply self.dtransform to data."""
        flips = (self.transform[0], self.transform[1])
        rot = self.transform[2]

        return {(0,0): numpy.rot90(data, rot),
                (0,1): numpy.flipud(numpy.rot90(data, rot)),
                (1,0): numpy.fliplr(numpy.rot90(data, rot)),
                (1,1): numpy.fliplr(numpy.flipud(numpy.rot90(data, rot)))
                }[flips]


    @abc.abstractmethod
    @Pyro4.expose
    def get_exposure_time(self):
        pass


    def set_some_setting(self, value):
        self.some_setting = value


    def get_some_setting(self, value):
        return self.some_setting