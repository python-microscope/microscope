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
import devicebase
import Pyro4

# Triggering types.
(TRIGGER_AFTER, TRIGGER_BEFORE, TRIGGER_DURATION) = range(3)

class CameraDevice(devicebase.DataDevice):
    """Adds functionality to DataDevice to support cameras.

    Defines the interface for cameras.
    Applies a transform to acquired data in the processing step.
    """
    def __init__(self, *args, **kwargs):
        # A tuple defining data shape.
        self.dshape = None
        # A data type.
        self.dtype = None
        # A transform to apply to data (fliplr, flipud, rot90)
        self.dtransform = (0, 0, 0)
        super(CameraDevice, self).__init__(**kwargs)
        self.some_setting = 0.
        #self.settings.append()


    def _process_data(self, data):
        """Apply self.dtransform to data."""
        flips = (self.transform[0], self.transform[1])
        rot = self.transform[2]

        # Choose appropriate transform based on (flips, rot).
        return {(0,0): numpy.rot90(data, rot),
                (0,1): numpy.flipud(numpy.rot90(data, rot)),
                (1,0): numpy.fliplr(numpy.rot90(data, rot)),
                (1,1): numpy.fliplr(numpy.flipud(numpy.rot90(data, rot)))
                }[flips]


    @abc.abstractmethod
    @Pyro4.expose
    def set_exposure_time(self, value):
        pass


    def get_exposure_time(self):
        pass


    def get_cycle_time(self):
        pass


    def get_sensor_shape(self):
        """Return a tuple of (width, height)."""
        pass


    def get_binning(self):
        """Return a tuple of (horizontal, vertical)."""
        pass


    def set_binning(self, h_bin, v_bin):
        """Set binning along both axes."""
        pass


    def get_sensor_temperature(self):
        """Return the sensor temperature."""
        pass


    def get_roi(self):
        """Return ROI as a rectangle (x0, y0, width, height).

        Chosen this rectangle format as it completely defines the ROI without
        reference to the sensor geometry."""
        pass


    def set_roi(self, x, y, width, height):
        """Set the ROI according to the provided rectangle.

        Return True if ROI set correctly, False otherwise."""
        pass


    def get_gain(self):
        """Get the current amplifier gain."""
        pass


    def set_gain(self):
        """Set the amplifier gain."""
        pass


    def get_trigger_type(self):
        """Return the current trigger mode.

        One of
            TRIGGER_AFTER,
            TRIGGER_BEFORE or
            TRIGGER_DURATION (bulb exposure.)
        """

    def get_meta_data(self):
        """Return metadata."""
        pass