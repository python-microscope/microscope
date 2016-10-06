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
from ast import literal_eval
import devicebase
import numpy
import itertools
import Pyro4

# Triggering types.
(TRIGGER_AFTER, TRIGGER_BEFORE, TRIGGER_DURATION, TRIGGER_SOFT) = range(4)

ALLOWED_TRANSFORMS = [p for p in itertools.product(*3*[range(2)])]

class CameraDevice(devicebase.DataDevice):
    """Adds functionality to DataDevice to support cameras.

    Defines the interface for cameras.
    Applies a transform to acquired data in the processing step.
    """
    def __init__(self, *args, **kwargs):
        super(CameraDevice, self).__init__(**kwargs)
        # Transforms to apply to data (fliplr, flipud, rot90)
        # Transform to correct for readout order.
        self._readout_transform = (0, 0, 0)
        # Transform supplied by client to correct for system geometry.
        self._transform = (0, 0, 0)
        # A transform provided by the client.
        self.add_setting('transform', 'enum',
                         self.get_transform,
                         self.set_transform,
                         lambda: ALLOWED_TRANSFORMS)


    def _process_data(self, data):
        """Apply self._transform to data."""
        flips = (self._transform[0], self._transform[1])
        rot = self._transform[2]

        # Choose appropriate transform based on (flips, rot).
        return {(0,0): numpy.rot90(data, rot),
                (0,1): numpy.flipud(numpy.rot90(data, rot)),
                (1,0): numpy.fliplr(numpy.rot90(data, rot)),
                (1,1): numpy.fliplr(numpy.flipud(numpy.rot90(data, rot)))
                }[flips]

    @Pyro4.expose
    def get_transform(self):
        """Return the current transform without readout transform."""
        return tuple(self._readout_transform[i] ^ self._transform[i]
                                for i in range(3))

    @Pyro4.expose
    def set_transform(self, transform):
        """Combine provided transform with readout transform."""
        if isinstance(transform, (str, unicode)):
            transform = literal_eval(transform)
        self._transform = tuple(self._readout_transform[i] ^ transform[i]
                                for i in range(3))


    @abc.abstractmethod
    @Pyro4.expose
    def set_exposure_time(self, value):
        pass

    @Pyro4.expose
    def get_exposure_time(self):
        pass

    @Pyro4.expose
    def get_cycle_time(self):
        pass

    @Pyro4.expose
    def get_sensor_shape(self):
        """Return a tuple of (width, height)."""
        pass

    @Pyro4.expose
    def get_binning(self):
        """Return a tuple of (horizontal, vertical)."""
        pass

    @Pyro4.expose
    def set_binning(self, h_bin, v_bin):
        """Set binning along both axes."""
        pass

    @Pyro4.expose
    def get_sensor_temperature(self):
        """Return the sensor temperature."""
        pass

    @Pyro4.expose
    def get_roi(self):
        """Return ROI as a rectangle (x0, y0, width, height).

        Chosen this rectangle format as it completely defines the ROI without
        reference to the sensor geometry."""
        pass

    @Pyro4.expose
    def set_roi(self, x, y, width, height):
        """Set the ROI according to the provided rectangle.

        Return True if ROI set correctly, False otherwise."""
        pass

    @Pyro4.expose
    def get_gain(self):
        """Get the current amplifier gain."""
        pass

    @Pyro4.expose
    def set_gain(self):
        """Set the amplifier gain."""
        pass

    @Pyro4.expose
    def get_trigger_type(self):
        """Return the current trigger mode.

        One of
            TRIGGER_AFTER,
            TRIGGER_BEFORE or
            TRIGGER_DURATION (bulb exposure.)
        """

    @Pyro4.expose
    def get_meta_data(self):
        """Return metadata."""
        pass

    @Pyro4.expose
    def soft_trigger(self):
        """Optional software trigger - implement if available."""
        pass