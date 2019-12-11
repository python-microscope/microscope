#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Prior controller.
"""

import contextlib
import threading
import typing

import serial

import microscope.devices


class _ProScanIIIConnection:
    """Connection to a Prior ProScanIII and wrapper to its commands.

    Devices that are controlled by the same controller should share
    the same connection instance to ensure correct synchronization of
    communications from different threads.  This ensures that commands
    for different devices, or replies from different devices, don't
    get entangled.

    This class also implements the logic to parse and validate
    commands so it can be shared between multiple devices.

    """
    def __init__(self, port: str, baudrate: int, timeout: float) -> None:
        # From the technical datasheet: 8 bit word 1 stop bit, no
        # parity no handshake, baudrate options of 9600, 19200, 38400,
        # 57600 and 115200.
        self._serial = serial.Serial(port=port, baudrate=baudrate,
                                     timeout=timeout, bytesize=serial.EIGHTBITS,
                                     stopbits=serial.STOPBITS_ONE,
                                     parity=serial.PARITY_NONE, xonxoff=False,
                                     rtscts=False, dsrdtr=False)
        self._lock = threading.RLock()

        with self._lock:
            # We do not use the general get_description() because if
            # this is not a ProScan device it would never reach the
            # '\rEND\r' that signals the end of the description.
            self.command(b'?')
            answer = self.readline()
            if answer != b'PROSCAN INFORMATION\r':
                self.read_until_timeout()
                raise RuntimeError("Not a ProScanIII device: '?' returned '%s'"
                                   % answer.decode())
            # A description ends with END on its own line.
            line = self._serial.read_until(b'\rEND\r')
            if not line.endswith(b'\rEND\r'):
                raise RuntimeError("Failed to clear description")


    def command(self, command: bytes) -> None:
        """Send command to device."""
        with self._lock:
            self._serial.write(command + b'\r')

    def readline(self) -> bytes:
        """Read a line from the device connection."""
        with self._lock:
            return self._serial.read_until(b'\r')

    def read_until_timeout(self) -> None:
        """Read until timeout; used to clean buffer if in an unknown state."""
        with self._lock:
            self._serial.flushInput()
            while len(self._serial.readline()) != 0:
                continue

    def _command_and_validate(self, command: bytes, expected: bytes) -> None:
        """Send command and raise exception if answer is unexpected"""
        with self._lock:
            answer = self.get_command(command)
            if answer != expected:
                self.read_until_timeout()
                raise RuntimeError("command '%s' failed (got '%s')"
                                   % (command.decode(), answer.decode()))

    def get_command(self, command: bytes) -> bytes:
        """Send get command and return the answer."""
        with self._lock:
            self.command(command)
            return self.readline()

    def move_command(self, command: bytes) -> None:
        """Send a move command and check return value."""
        # Movement commands respond with an R at the end of move.
        # Once a movement command is issued the application should
        # wait until the end of move R response is received before
        # sending any further commands.
        # TODO: this times 10 is a bit arbitrary.
        with self.changed_timeout(10 * self._serial.timeout):
            self._command_and_validate(command, b'R\r')

    def set_command(self, command: bytes) -> None:
        """Send a set command and check return value."""
        # Property type commands that set certain status respond with
        # zero.  They respond with a zero even if there are invalid
        # arguments in the command.
        self._command_and_validate(command, b'0\r')

    def get_description(self, command: bytes) -> bytes:
        """Send a get description command and return it."""
        with self._lock:
            self.command(command)
            return self._serial.read_until(b'\rEND\r')


    @contextlib.contextmanager
    def changed_timeout(self, new_timeout: float):
        previous = self._serial.timeout
        try:
            self._serial.timeout = new_timeout
            yield
        finally:
            self._serial.timeout = previous


    def assert_filterwheel_number(self, number: int) -> None:
        assert number > 0 and number < 4


    def _has_thing(self, command: bytes, expected_start: bytes) -> bool:
        # Use the commands that returns a description string to find
        # whether a specific device is connected.
        with self._lock:
            description = self.get_description(command)
            if not description.startswith(expected_start):
                self.read_until_timeout()
                raise RuntimeError("Failed to get description '%s' (got '%s')"
                                   % (command.decode(), description.decode()))
        return not description.startswith(expected_start + b'NONE\r')


    def has_filterwheel(self, number: int) -> bool:
        self.assert_filterwheel_number(number)
        # We use the 'FILTER w' command to check if there's a filter
        # wheel instead of the '?' command.  The reason is that the
        # third filter wheel, named "A AXIS" on the controller box and
        # "FOURTH" on the output of the '?' command, can be used for
        # non filter wheels.  We hope that 'FILTER 3' will fail
        # properly if what is connected to "A AXIS" is not a filter
        # wheel.
        return self._has_thing(b'FILTER %d' % number, b'FILTER_%d = ' % number)


    def get_n_filter_positions(self, number: int) -> int:
        self.assert_filterwheel_number(number)
        answer = self.get_command(b'FPW %d' % number)
        return int(answer)

    def get_filter_position(self, number: int) -> int:
        self.assert_filterwheel_number(number)
        answer = self.get_command(b'7 %d F' % number)
        return int(answer)

    def set_filter_position(self, number: int, pos: int) -> None:
        self.assert_filterwheel_number(number)
        self.move_command(b'7 %d %d' % (number, pos))


class ProScanIII(microscope.devices.ControllerDevice):
    """Prior ProScanIII controller.

    The controlled devices have the following labels:

    `filter 1`
      Filter wheel connected to connector labelled "FILTER 1".
    `filter 2`
      Filter wheel connected to connector labelled "FILTER 1".
    `filter 3`
      Filter wheel connected to connector labelled "A AXIS".

    .. note::

       The Prior ProScanIII can control up to three filter wheels.
       However, a filter position may have a different number
       dependening on which connector it is.  For example, using an 8
       position filter wheel, what is position 1 on the filter 1 and 2
       connectors, is position 4 when on the A axis (filter 3)
       connector.

    """
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0.5,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self._conn = _ProScanIIIConnection(port, baudrate, timeout)
        self._devices = {} # type: typing.Mapping[str, microscope.devices.Device]

        # Can have up to three filter wheels, numbered 1 to 3.
        for number in range(1, 4):
            if self._conn.has_filterwheel(number):
                key = 'filter %d' % number
                self._devices[key] = _ProScanIIIFilterWheel(self._conn, number)

    @property
    def devices(self) -> typing.Mapping[str, microscope.devices.Device]:
        return self._devices


class _ProScanIIIFilterWheel(microscope.devices.FilterWheelBase):
    def __init__(self, connection: _ProScanIIIConnection, number: int) -> None:
        super().__init__()
        self._conn = connection
        self._number = number
        self._positions = self._conn.get_n_filter_positions(self._number)

    def get_position(self) -> int:
        return self._conn.get_filter_position(self._number)

    def set_position(self, position: int) -> None:
        self._conn.set_filter_position(self._number, position)

    def _on_shutdown(self) -> None:
        super()._on_shutdown()

    def initialize(self) -> None:
        super().initialize()
