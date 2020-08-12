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

import io

import serial

import microscope.abc


class ThorlabsFilterWheel(microscope.abc.FilterWheel):
    """Implements FilterServer wheel interface for Thorlabs FW102C.

    Note that the FW102C also has manual controls on the device, so clients
    should periodically query the current wheel position."""

    def __init__(self, com, baud=115200, timeout=2.0, **kwargs):
        """Create ThorlabsFilterWheel

        :param com: COM port
        :param baud: baud rate
        :param timeout: serial timeout
        """
        super().__init__(**kwargs)
        self.eol = "\r"
        rawSerial = serial.Serial(
            port=com,
            baudrate=baud,
            timeout=timeout,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            xonxoff=0,
        )
        # The Thorlabs controller serial implementation is strange.
        # Generally, it uses \r as EOL, but error messages use \n.
        # A readline after sending a 'pos?\r' command always times out,
        # but returns a string terminated by a newline.
        # We use TextIOWrapper with newline=None to perform EOL translation
        # inbound, but must explicitly append \r to outgoing commands.
        # The TextIOWrapper also deals with conversion between unicode
        # and bytes.
        self.connection = io.TextIOWrapper(
            rawSerial,
            newline=None,
            line_buffering=True,  # flush on write
            write_through=True,
        )  # write out immediately

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass

    def _do_set_position(self, new_position: int) -> None:
        self._send_command("pos=%d" % new_position)

    def _do_get_position(self):
        return int(self._send_command("pos?"))

    def _readline(self):
        """A custom _readline to overcome limitations of the serial implementation."""
        result = [None]
        while result[-1] not in ("\n", ""):
            result.append(self.connection.read())
        return "".join(result[1:])

    def _send_command(self, command):
        """Send a command and return any result."""
        result = None
        self.connection.write(command + self.eol)
        response = "dummy"
        while response not in [command, ""]:
            # Read until we receive the command echo.
            response = self._readline().strip("> \n\r")
        if command.endswith("?"):
            # Last response was the command. Next is result.
            result = self._readline().strip()
        return result


# TODO: we should be able to read the model and number of positions
# from the device itself, we shouldn't need a separate class for each
# model.
class ThorlabsFW102C(ThorlabsFilterWheel):
    # Thorlabs 6-position filterwheel.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, positions=6, **kwargs)


class ThorlabsFW212C(ThorlabsFilterWheel):
    # Thorlabs 12-position filterwheel.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, positions=12, **kwargs)
