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

import serial

from microscope.devices import FilterWheelBase


class ThorlabsFilterWheel(FilterWheelBase):
    """Implements FilterServer wheel interface for Thorlabs FW102C.

    Note that the FW102C also has manual controls on the device, so clients
    should periodically query the current wheel position."""
    def __init__(self, com, baud=115200, timeout=2.0, **kwargs):
        """Create ThorlabsFilterWheel

        :param com: COM port
        :param baud: baud rate
        :param timeout: serial timeout
        :keyword filters: optional list of filters
        """
        super().__init__(**kwargs)
        self.eol = '\r'
        rawSerial = serial.Serial(port=com,
                baudrate=baud, timeout=timeout,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                xonxoff=0)
        # The Thorlabs controller serial implementation is strange.
        # Generally, it uses \r as EOL, but error messages use \n.
        # A readline after sending a 'pos?\r' command always times out,
        # but returns a string terminated by a newline.
        # We use TextIOWrapper with newline=None to perform EOL translation
        # inbound, but must explicitly append \r to outgoing commands.
        # The TextIOWrapper also deals with conversion between unicode
        # and bytes.
        self.connection = io.TextIOWrapper(rawSerial, newline=None,
                                           line_buffering=True, # flush on write
                                           write_through=True) # write out immediately

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass

    def set_position(self, n):
        """Public method to move to position n."""
        command = 'pos=%d' % n
        self._send_command(command)

    def get_position(self):
        """Public method to query the current position"""
        return int(self._send_command('pos?'))

    def _readline(self):
        """A custom _readline to overcome limitations of the serial implementation."""
        result = [None]
        while result[-1] not in ('\n', ''):
            result.append(self.connection.read())
        return ''.join(result[1:])

    def _send_command(self, command):
        """Send a command and return any result."""
        result = None
        self.connection.write(command + self.eol)
        response = 'dummy'
        while response not in [command, '']:
            # Read until we receive the command echo.
            response = self._readline().strip('> \n\r')
        if command.endswith('?'):
            # Last response was the command. Next is result.
            result = self._readline().strip()
        return result


class ThorlabsFW102C(ThorlabsFilterWheel):
    # Thorlabs 6-position filterwheel.
    _positions = 6


class ThorlabsFW212C(ThorlabsFilterWheel):
    # Thorlabs 12-position filterwheel.
    _positions = 12
