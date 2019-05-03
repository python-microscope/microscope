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

import io

import Pyro4
import serial

import microscope.devices


class ThorlabsFilterWheel(microscope.devices.FilterWheelBase):
    """Implements FilterServer wheel interface for Thorlabs FW102C."""
    def __init__(self, com, baud, timeout, **kwargs):
        super(self.__class__, self).__init__(com, baud, timeout, **kwargs)
        self.eol = '\r'
        # The EOL character means the serial connection must be wrapped in a
        # TextIOWrapper.
        rawSerial = serial.Serial(port=com,
                baudrate=baud, timeout=timeout,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                xonxoff=0)
        # Use a buffer size of 1 in the BufferedRWPair. Without this,
        # either 8192 chars need to be read before data is passed upwards,
        # or he buffer needs to be flushed, incurring a serial timeout.
        self.connection = io.TextIOWrapper(io.BufferedRWPair(rawSerial, rawSerial, 1))
        # Last received wheel position.
        self.lastPosition = None
        # Last requested position.
        self.requestedPosition = None


    def initialize(self, *args, **kwargs):
        pass

    def _on_shutdown(self):
        pass

    def _set_position(self, n):
        """Private function to move to position n."""
        command = 'pos=%d' % n
        self.connection.write(unicode(command + self.eol))
        # The serial connection will timeout until new position is reached.
        # Count timeouts to detect failure to return to responsive state.
        count = 0
        maxCount = 1000
        response = None
        while True:
            response = self.connection.readline().strip()
            if response == command:
                # Command echo received - reset counter.
                count = 0
            elif response == '>':
                # Command input caret received - connection is responsive again.
                break
            else:
                # Increment counter and test against maxCount.
                count += 1
                if count > maxCount:
                    self.connection.flush()
                    raise Exception('fw102c: Communication error.')
                time.sleep(0.01)

    def _get_position(self):
        """Private function to read current position."""
        try:
            currentPosition = int(self._send_command('pos?'))
        except:
            return self.lastPosition
        else:
            self.lastPosition = currentPosition
            return self.lastPosition

    def getPosition(self):
        """Public function to fetch current position."""
        return self.lastPosition

    def _send_command(self, command):
        """Send a command and return any result."""
        result = None
        self.connection.write(unicode(command + self.eol))
        response = 'dummy'
        while response not in [command, '']:
            # Read until we receive the command echo.
            response = self.connection.readline().strip()
        if command.endswith('?'):
            # Last response was the command. Next is result.
            result = self.connection.readline().strip()
        while response not in ['>', '']:
            # Read until we receive the input caret.
            response = self.connection.readline().strip()
        return result
