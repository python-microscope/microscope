#!/usr/bin/env python3

## Copyright (C) YYYY Name of Copyright Holder <email of copyright holder>
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

"""Test camera device.
"""

import microscope
import microscope.abc

# Trigger mode to type.
TRIGGER_MODES = {
    "internal": None,
    "external": microscope.abc.TRIGGER_BEFORE,
    "external start": None,
    "external exposure": microscope.abc.TRIGGER_DURATION,
    "software": microscope.abc.TRIGGER_SOFT,
}


class TemplateCamera(microscope.abc.Camera):
    def __init__(self, *args, **kwargs):
        super(TestCamera, self).__init__(**kwargs)
        # Software buffers and parameters for data conversion.
        self._a_setting = 0
        self.add_setting(
            "a_setting",
            "int",
            lambda: self._a_setting,
            lambda val: setattr(self, "_a_setting", val),
            lambda: (1, 100),
        )

    """Private methods, called here and within super classes."""

    def _fetch_data(self):
        """Fetch data, recycle any buffers and return data or None."""
        return data or None

    def _on_enable(self):
        """Enable the camera hardware and make ready to respond to triggers.

        Return True if successful, False if not."""
        return False

    def _on_disable(self):
        """Disable the hardware for a short period of inactivity."""
        self.abort()
        pass

    def _on_shutdown(self):
        """Disable the hardware for a prolonged period of inactivity."""
        pass

    """Private shape-related methods. These methods do not need to account
    for camera orientation or transforms due to readout mode, as that
    is handled in the parent class."""

    def _get_sensor_shape(self):
        """Return the sensor shape (width, height)."""
        return (512, 512)

    def _get_binning(self):
        """Return the current binning (horizontal, vertical)."""
        return microscope.Binning(1, 1)

    @microscope.abc.keep_acquiring
    def _set_binning(self, binning):
        """Set binning to (h, v)."""
        return False

    def _get_roi(self):
        """Return the current ROI (left, top, width, height)."""
        return microscope.ROI(0, 0, 512, 512)

    @microscope.abc.keep_acquiring
    def _set_roi(self, roi):
        """Set the ROI to (left, tip, width, height)."""
        return False

    """Public methods, callable from client."""

    def abort(self):
        """Abort acquisition.

        This should put the camera into a state in which settings can
        be modified."""
        self._acquiring = False

    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        self._logger.info("Initializing.")

    def make_safe(self):
        """Put the camera into a safe state.

        Safe means (at least):
         * it won't sustain damage if light falls on the sensor."""
        if self._acquiring:
            self.abort()

    def set_exposure_time(self, value):
        """Set the exposure time to value."""
        pass

    def get_exposure_time(self):
        """Return the current exposure time."""
        return 0.1

    def get_cycle_time(self):
        """Return the cycle time.

        Cycle time is the minimum time between exposures. This is
        typically exposure time plus readout time."""
        return 0.15

    def get_trigger_type(self):
        """Return the current trigger type."""
        return camera.TRIGGER_SOFT

    def soft_trigger(self):
        """Send a software trigger to the camera."""
        pass
