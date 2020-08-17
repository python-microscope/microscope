#!/usr/bin/env python3

## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
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

"""Adds support for Aurox devices

Requires package hidapi."""

import time
from threading import Lock

import hid

import microscope
import microscope.devices

# Clarity constants. These may differ across products, so mangle names.
# USB IDs
_Clarity__VENDORID = 0x1F0A
_Clarity__PRODUCTID = 0x0088
# Base status
_Clarity__SLEEP = 0x7F
_Clarity__RUN = 0x0F
# Door status
_Clarity__DOOROPEN = 0x01
_Clarity__DOORCLOSED = 0x02
# Disk position/status
_Clarity__SLDPOS0 = 0x00  # disk out of beam path, wide field
_Clarity__SLDPOS1 = 0x01  # disk pos 1, low sectioning
_Clarity__SLDPOS2 = 0x02  # disk pos 2, mid sectioning
_Clarity__SLDPOS3 = 0x03  # disk pos 3, high sectioning
_Clarity__SLDERR = 0xFF  # An error has occurred in setting slide position (end stops not detected)
_Clarity__SLDMID = 0x10  # slide between positions (was =0x03 for SD62)
# Filter position/status
_Clarity__FLTPOS1 = 0x01  # Filter in position 1
_Clarity__FLTPOS2 = 0x02  # Filter in position 2
_Clarity__FLTPOS3 = 0x03  # Filter in position 3
_Clarity__FLTPOS4 = 0x04  # Filter in position 4
_Clarity__FLTERR = 0xFF  # An error has been detected in the filter drive (eg filters not present)
_Clarity__FLTMID = 0x10  # Filter between positions
# Calibration LED state
_Clarity__CALON = 0x01  # CALibration led power on
_Clarity__CALOFF = 0x02  # CALibration led power off
# Error status
_Clarity__CMDERROR = 0xFF  # Reply to a command that was not understood
# Commands
_Clarity__GETVERSION = 0x00  # Return 3-byte version number byte1.byte2.byte3
# State commands: single command byte immediately followed by any data.
_Clarity__GETONOFF = 0x12  # No data out, returns 1 byte on/off status
_Clarity__GETDOOR = 0x13  # No data out, returns 1 byte shutter status, or SLEEP if device sleeping
_Clarity__GETSLIDE = 0x14  # No data out, returns 1 byte disk-slide status, or SLEEP if device sleeping
_Clarity__GETFILT = 0x15  # No data out, returns 1 byte filter position, or SLEEP if device sleeping
_Clarity__GETCAL = 0x16  # No data out, returns 1 byte CAL led status, or SLEEP if device sleeping
_Clarity__GETSERIAL = (
    0x19  # No data out, returns 4 byte BCD serial number (little endian)
)
_Clarity__FULLSTAT = 0x1F  # No data, Returns 10 bytes VERSION[3],ONOFF,SHUTTER,SLIDE,FILT,CAL,??,??
# Run state action commands
_Clarity__SETONOFF = 0x21  # 1 byte out on/off status, echoes command or SLEEP
_Clarity__SETSLIDE = 0x23  # 1 byte out disk position, echoes command or SLEEP
_Clarity__SETFILT = 0x24  # 1 byte out filter position, echoes command or SLEEP
_Clarity__SETCAL = 0x25  # 1 byte out CAL led status, echoes command or SLEEP
# Service mode commands. Stops disk spinning for alignment.
_Clarity__SETSVCMODE1 = 0xE0  # 1 byte for service mode. SLEEP activates service mode. RUN returns to normal mode.


class Clarity(microscope.devices.FilterWheelBase):
    _slide_to_sectioning = {
        __SLDPOS0: "bypass",
        __SLDPOS1: "low",
        __SLDPOS2: "mid",
        __SLDPOS3: "high",
    }
    _positions = 4
    _resultlen = {
        __GETONOFF: 1,
        __GETDOOR: 1,
        __GETSLIDE: 1,
        __GETFILT: 1,
        __GETCAL: 1,
        __GETSERIAL: 4,
        __FULLSTAT: 10,
    }

    def __init__(self, **kwargs):
        super().__init__(positions=Clarity._positions, **kwargs)
        self._lock = Lock()
        self._hid = None
        self.add_setting(
            "sectioning",
            "enum",
            self.get_slide_position,
            lambda val: self.set_slide_position(val),
            self._slide_to_sectioning,
        )

    def _send_command(self, command, param=0, max_length=16, timeout_ms=100):
        """Send a command to the Clarity and return its response"""
        if not self._hid:
            self.open()
        with self._lock:
            # The device expects a list of 16 integers
            buffer = [0x00] * max_length  # The 0th element must be 0.
            buffer[1] = command  # The 1st element is the command
            buffer[2] = param  # The 2nd element is any command argument.
            result = self._hid.write(buffer)
            if result == -1:
                # Nothing to read back. Check hid error state.
                err = self._hid.error()
                if err != "":
                    self.close()
                    raise microscope.DeviceError(err)
                else:
                    return None
            while True:
                # Read responses until we see the response to our command.
                # (We should get the correct response on the first read.)
                response = self._hid.read(result - 1, timeout_ms)
                if not response:
                    # No response
                    return None
                elif response[0] == command:
                    break
            bytes = self._resultlen.get(command, None)
            if bytes is None:
                return response[1:]
            elif bytes == 1:
                return response[1]
            else:
                return response[1:]

    @property
    def is_connected(self):
        return self._hid is not None

    def open(self):
        h = hid.device()
        h.open(vendor_id=__VENDORID, product_id=__PRODUCTID)
        h.set_nonblocking(False)
        self._hid = h

    def close(self):
        if self.is_connected:
            self._hid.close()
            self._hid = None

    def get_id(self):
        return self._send_command(__GETSERIAL)

    def _on_enable(self):
        if not self.is_connected:
            self.open()
        self._send_command(__SETONOFF, __RUN)
        return self._send_command(__GETONOFF) == __RUN

    def _on_disable(self):
        self._send_command(__SETONOFF, __SLEEP)

    def set_calibration(self, state):
        if state:
            result = self._send_command(__SETCAL, __CALON)
        else:
            result = self._send_command(__SETCAL, __CALOFF)
        return result

    def get_slide_position(self):
        """Get the current slide position"""
        result = self._send_command(__GETSLIDE)
        if result is None:
            raise microscope.DeviceError("Slide position error.")
        return result

    def set_slide_position(self, position, blocking=True):
        """Set the slide position"""
        result = self._send_command(__SETSLIDE, position)
        if result is None:
            raise microscope.DeviceError("Slide position error.")
        while blocking and self.moving():
            pass
        return result

    def get_slides(self):
        return self._slide_to_sectioning

    def get_status(self):
        # Fetch 10 bytes VERSION[3],ONOFF,SHUTTER,SLIDE,FILT,CAL,??,??
        result = self._send_command(__FULLSTAT)
        if result is None:
            return
        # A status dict to populate and return
        status = {}
        # A list to track states, any one of which mean the device is busy.
        busy = []
        # Disk running
        status["on"] = result[3] == __RUN
        # Door open
        # Note - it appears that the __DOOROPEN and __DOORCLOSED status states
        # are switched, or that the DOOR is in fact an internal shutter. I'll
        # interpret 'door' as the external door here, as that is what the user
        # can see. When the external door is open, result[4] == __DOORCLOSED
        door = result[4] == __DOORCLOSED
        status["door open"] = door
        busy.append(door)
        # Slide position
        slide = result[5]
        if slide == __SLDMID:
            # Slide is moving
            status["slide"] = (None, "moving")
            busy.append(True)
        else:
            status["slide"] = (
                slide,
                self._slide_to_sectioning.get(slide, None),
            )
        # Filter position
        filter = result[6]
        if filter == __FLTMID:
            # Filter is moving
            status["filter"] = (None, "moving")
            busy.append(True)
        else:
            status["filter"] = result[6]
        # Calibration LED on
        status["calibration"] = result[7] == __CALON
        # Slide or filter moving
        status["busy"] = any(busy)
        return status

    # Implemented by FilterWheelBase
    # def get_filters(self):
    #    pass

    def moving(self):
        """Report whether or not the device is between positions."""
        # Wait a short time to avoid false negatives when called
        # immediately after initiating a move. Trial and error
        # indicates a delay of 50ms is required.
        time.sleep(0.05)
        # Can return false negatives on long moves, so OR 5 readings.
        moving = False
        for i in range(5):
            moving = moving or any(
                (
                    self.get_slide_position() == __SLDMID,
                    self.get_position() == __FLTMID,
                )
            )
            time.sleep(0.01)
        return moving

    def _do_get_position(self):
        """Return the current filter position"""
        result = self._send_command(__GETFILT)
        if result == __FLTERR:
            raise microscope.DeviceError("Filter position error.")
        return result

    def _do_set_position(self, pos, blocking=True):
        """Set the filter position"""
        result = self._send_command(__SETFILT, pos)
        if result is None:
            raise microscope.DeviceError("Filter position error.")
        while blocking and self.moving():
            pass
        return result

    def _on_shutdown(self):
        pass

    def initialize(self):
        pass
