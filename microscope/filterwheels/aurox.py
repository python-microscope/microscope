#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2019 Mick Phillips (mick.phillips@gmail.com)
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

"""Adds support for Aurox devices

Requires package hidapi."""

import hid
import microscope.devices
from enum import Enum

## Clarity constants. These may differ across products, so mangle names.
# USB IDs
_Clarity__VENDORID = 0x1F0A
_Clarity__PRODUCTID = 0x0088
# Base status
_Clarity__SLEEP = 0x7f
_Clarity__RUN = 0x0f
# Door status
_Clarity__DOOROPEN = 0x01
_Clarity__DOORCLOSED = 0x02
# Disk position/status
_Clarity__SLDPOS0 = 0x00 #disk out of beam path, wide field
_Clarity__SLDPOS1 = 0x01 #disk pos 1, low sectioning
_Clarity__SLDPOS2 = 0x02 #disk pos 2, mid sectioning
_Clarity__SLDPOS3 = 0x03 #disk pos 3, high sectioning
_Clarity__SLDERR = 0xff #An error has occurred in setting slide position (end stops not detected)
_Clarity__SLDMID = 0x10 #slide in mid position (was =0x03 for SD62)
# Filter position/status
_Clarity__FLTPOS1 = 0x01 #Filter in position 1
_Clarity__FLTPOS2 = 0x02 #Filter in position 2
_Clarity__FLTPOS3 = 0x03 #Filter in position 3
_Clarity__FLTPOS4 = 0x04 #Filter in position 4
_Clarity__FLTERR = 0xff #An error has been detected in the filter drive (eg filters not present)
_Clarity__FLTMID = 0x10 #Filter in mid position
# Calibration LED state
_Clarity__CALON = 0x01 #CALibration led power on
_Clarity__CALOFF = 0x02 #CALibration led power off
# Error status
_Clarity__CMDERROR = 0xff #Reply to a command that was not understood
# Commands
_Clarity__GETVERSION = 0x00 #Return 3-byte version number byte1.byte2.byte3
# State commands: single command byte immediately followed by any data.
_Clarity__GETONOFF = 0x12 #No data out, returns 1 byte on/off status
_Clarity__GETDOOR = 0x13 #No data out, returns 1 byte shutter status, or SLEEP if device sleeping
_Clarity__GETSLIDE = 0x14 #No data out, returns 1 byte disk-slide status, or SLEEP if device sleeping
_Clarity__GETFILT = 0x15 #No data out, returns 1 byte filter position, or SLEEP if device sleeping
_Clarity__GETCAL = 0x16 #No data out, returns 1 byte CAL led status, or SLEEP if device sleeping
_Clarity__GETSERIAL = 0x19 #No data out, returns 4 byte BCD serial number (little endian)
_Clarity__FULLSTAT = 0x1f #No data, Returns 10 bytes VERSION[3],ONOFF,SHUTTER,SLIDE,FILT,CAL,??,??
# Run state action commands
_Clarity__SETONOFF = 0x21 #1 byte out on/off status, echoes command or SLEEP
_Clarity__SETSLIDE = 0x23 #1 byte out disk position, echoes command or SLEEP
_Clarity__SETFILT = 0x24 #1 byte out filter position, echoes command or SLEEP
_Clarity__SETCAL = 0x25 #1 byte out CAL led status, echoes command or SLEEP
# Service mode commands. Stops disk spinning for alignment.
_Clarity__SETSVCMODE1 = 0xe0 #1 byte for service mode. SLEEP activates service mode. RUN returns to normal mode.


class Clarity(microscope.devices.FilterWheelBase):
    _slide_to_sectioning = {__SLDPOS0: 'bypass',
                            __SLDPOS1: 'low',
                            __SLDPOS2: 'mid',
                            __SLDPOS3: 'high',
                            __SLDMID: 'mid',}
    _positions = 4

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        from threading import Lock
        self._lock = Lock()
        self._hid = None
        self.add_setting("sectioning", "enum",
                         self.get_slide_position,
                         lambda val: self.set_slide_position(val),
                         self._slide_to_sectioning)

    def _send_command(self, command, param=0, max_length=16, timeout_ms=100):
        if not self._hid:
            raise Exception("Not connected to device.")
        with self._lock:
            buffer = [0x00] * max_length
            buffer[0] = command
            buffer[1] = param
            result = self._hid.write(buffer)
            response = self._hid.read(max_length, timeout_ms)
            if response[0] != command:
                return None
            else:
                return response[1:]

    @property
    def is_connected(self):
        return self._hid is not None

    def open(self):
        try:
            h = hid.device()
            h.open(vendor_id=__VENDORID, product_id=__PRODUCTID)
            h.set_nonblocking(False)
        except:
            raise
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
        result = self._slide_to_sectioning.get(self._send_command(__GETSLIDE), None)
        if result is None:
            raise Exception("Slide position error.")
        return result

    def set_slide_position(self, position):
        """Set the slide position"""
        result = self._send_command(__SETSLIDE, position)
        if result is None:
            raise Exception("Slide position error.")
        return result

    def get_slides(self):
        return (self._slide_to_sectioning)

    def get_status(self):
        # Fetch 10 bytes VERSION[3],ONOFF,SHUTTER,SLIDE,FILT,CAL,??,??
        result = self._send_command(__FULLSTAT)
        status = {}
        status['on'] = result[3] == __RUN
        slide = result[4]
        status['slide'] = (slide, self._slide_to_sectioning.get(slide, None))
        status['filter'] = (result[6], self._filters.get(result[6], None))
        status['calibration'] == result[7] == __CALON
        return status

    # Implemented by FilterWheelBase
    #def get_filters(self):
    #    pass

    def get_position(self):
        """Return the current filter position"""
        result = self._send_command(__GETFILT)
        if result ==  __FLTERR:
            raise Exception("Filter position error.")
        return result

    def set_position(self, pos):
        """Set the filter position"""
        result = self._send_command(__SETFILT, pos)
        if result is None:
            raise Exception("Filter position error.")
        return result
