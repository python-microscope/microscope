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
import time

from microscope.devices import FilterWheelBase


class ThorlabsFilterWheel(FilterWheelBase):
    """Implements FilterServer wheel interface for Thorlabs FW102C.

    Note that the FW102C also has manual controls on the device, so clients
    should periodically query the current wheel position."""
    def __init__(self, com, baud, timeout, **kwargs):
        """Create ThorlabsFilterWheel

        :param com: COM port
        :param baud: baud rate
        :param timeout: serial timeout
        :keyword filters: optional list of filters
        """
        super().__init__(com, baud, timeout, **kwargs)
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

    def initialize(self, *args, **kwargs):
        pass

    def _on_shutdown(self):
        pass

    def set_position(self, n):
        """Public method to move to position n."""
        command = 'pos=%d' % n
        self.connection.write(command + self.eol)
        # The serial connection will timeout until new position is reached.
        # Count timeouts to detect failure to return to responsive state.
        count = 0
        maxCount = 10
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
                time.sleep(0.1)

    def get_position(self):
        """Public method to query the current position"""
        return int(self._send_command('pos?'))

    def _send_command(self, command):
        """Send a command and return any result."""
        result = None
        self.connection.write(command + self.eol)
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


class ThorlabsFW102C(ThorlabsFilterWheel):
    # Thorlabs 6-position filterwheel.
    _positions = 6


class ThorlabsFW212C(ThorlabsFilterWheel):
    # Thorlabs 12-position filterwheel.
    _positions = 12
