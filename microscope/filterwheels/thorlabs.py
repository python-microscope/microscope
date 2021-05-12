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
import threading
import warnings

import serial

import microscope
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
            write_through=True,  # write out immediately
        )
        # A lock for the connection.  We should probably be using
        # SharedSerial (maybe change it to SharedIO, and have it
        # accept any IOBase implementation).
        self._lock = threading.RLock()
        position_count = int(self._send_command("pcount?"))
        super().__init__(positions=position_count, **kwargs)

    def _do_shutdown(self) -> None:
        pass

    def _do_set_position(self, new_position: int) -> None:
        # Thorlabs positions start at 1, hence the +1
        self._send_command("pos=%d" % (new_position + 1))

    def _do_get_position(self):
        # Thorlabs positions start at 1, hence the -1
        return int(self._send_command("pos?")) - 1

    def _readline(self):
        """Custom _readline to overcome limitations of the serial implementation."""
        result = [None]
        with self._lock:
            while result[-1] not in ("\n", ""):
                result.append(self.connection.read())
        return "".join(result[1:])

    def _send_command(self, command):
        """Send a command and return any result."""
        result = None
        with self._lock:
            self.connection.write(command + self.eol)
            response = "dummy"
            while response not in [command, ""]:
                # Read until we receive the command echo.
                response = self._readline().strip("> \n\r")
            if command.endswith("?"):
                # Last response was the command. Next is result.
                result = self._readline().strip()
        return result


class ThorlabsFW102C(ThorlabsFilterWheel):
    """Deprecated, use ThorlabsFilterWheel.

    This class is from when ThorlabsFilterWheel did not automatically
    found its own number of positions and there was a separate class
    for each thorlabs filterwheel model.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Use ThorlabsFilterWheel instead of ThorlabsFW102C",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
        if self.n_positions != 6:
            raise microscope.InitialiseError(
                "Does not look like a FW102C, it has %d positions instead of 6"
            )


class ThorlabsFW212C(ThorlabsFilterWheel):
    """Deprecated, use ThorlabsFilterWheel.

    This class is from when ThorlabsFilterWheel did not automatically
    found its own number of positions and there was a separate class
    for each thorlabs filterwheel model.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Use ThorlabsFilterWheel instead of ThorlabsFW212C",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
        if self.n_positions != 12:
            raise microscope.InitialiseError(
                "Does not look like a FW212C, it has %d positions instead of 12"
            )
