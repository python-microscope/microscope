#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2022 Ian Dobbie <ian.dobbie@jhu.edu>
##
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

"""Ludl controller.
"""

import contextlib
import re
import threading
import time
import typing

import serial

import microscope.abc


# so far very basic support for stages
# no support for filter, shutters, or slide loader as I dont have hardware

# Note:
# commands end in a '\r' but replies return ending in '\n'!

# errors
# -1 Unknown command
# -2 Illegal point type or axis, or module not installed
# -3 Not enough parameters (e.g. move r=)
# -4 Parameter out of range
# -21 Process aborted by HALT command

# Slide Loader:
# -4 (parameter out of range) used for cassette or slot range errors
# -10 No slides selected
# -11 End of list reached
# -12 Slide error
# -16 Motor move error (move not completed successfully due to stall,
# end limit, etc….)
# -17 Initialization erro

# On startup the stage move to extremes to find limits and then sets
# the -ve limit on each axis to 0.

LUDL_ERRORS = {
    -1: "Unknown command",
    -2: "Illegal point type or axis, or module not installed",
    -3: "Not enough parameters (e.g. move r=)",
    -4: "Parameter out of range",
    -21: "Process aborted by HALT command",
    # Slide Loader:
    # -4:, (parameter out of range) used for cassette or slot range errors
    -10: "No slides selected",
    -11: "End of list reached",
    -12: "Slide error",
    -16: "Motor move error (move not completed successfully due to stall, end limit, etc.",
    -17: "Initialization error",
}

AXIS_MAPPER = {
    1: "X",
    2: "Y",
    3: "Z",
}


class _LudlController:
    """Connection to a Ludl Controller and wrapper to its commands.

    Tested with MC2000 controller and xy stage.

    This class also implements the logic to parse and validate
    commands so it can be shared between multiple devices.

    This class has only been tested on a MAC2000 controller from the
    1990's however newer controllers should be compatible.

    """

    def __init__(self, port: str, baudrate: int, timeout: float) -> None:
        # From the technical datasheet: 8 bit word 1 stop bit, no
        # parity no handshake, baudrate options of 9600, 19200, 38400,
        # 57600 and 115200.
        self._serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_TWO,
            parity=serial.PARITY_NONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        self._lock = threading.RLock()

        with self._lock:
            # We do not use the general get_description() here because
            # if this is not a ProScan device it would never reach the
            # '\rEND\r' that signals the end of the description.
            try:
                self.command(b"RCONFIG")
                answer = self.read_multiline()
            except:
                print("Unable to read configuration. Is Ludl connected?")
                return
            # parse config responce which tells us what devices are present
            # on this controller.

            self._devlist = {}

            for line in answer[4:-1]:
                # loop through lines 4 to second last one which are devices
                # present on this controller
                devinfo = re.split(r"\s{2,}", line.decode("ascii"))
                # dev address,label,id,description, type
                self._devlist[devinfo[0]] = devinfo[1:]

    #            print(answer)

    def is_busy(self):
        pass

    def get_number_axes(self):
        return 2

    def command(self, command: bytes) -> None:
        """Send command to device."""
        with self._lock:
            self._serial.write(command + b"\r")

    def readline(self) -> bytes:
        """Read a line from the device connection until ``\\n``."""
        with self._lock:
            return self._serial.read_until(b"\n")

    def read_multiline(self):
        output = []
        line = True
        while line:
            line = self.readline()
            output.append(line.strip())
            if line == b"N" or line[0:2] == b":A":
                # thins means an end of command strings doesn require an
                # additional timeout before it returns
                return output
            elif line[0] == b"N":
                # this is an error string
                error = line[2:].strip()
                raise (
                    "Ludl controller error: %s,%s"
                    % (error, LUDL_ERRORS[error])
                )
        return output

    def read_until_timeout(self) -> None:
        """Read until timeout; used to clean buffer if in an unknown state."""
        with self._lock:
            self._serial.flushInput()
            while self._serial.readline():
                continue

    def wait_until_idle(self) -> None:
        """Keep sending the ``STATUS`` comand until it responds ``0\\r``"""
        self._command_and_validate(b"STATUS", b"N")

    def _command_and_validate(self, command: bytes, expected: bytes) -> None:
        with self._lock:
            answer = self.get_command(command)
            if answer == b":A \n":
                # wait for move to stop
                while self.get_command(b"STATUS") != expected:
                    time.sleep(0.01)
            return answer

    def get_command(self, command: bytes) -> bytes:
        """Send get command and return the answer."""
        with self._lock:
            self.command(command)
            return self.readline()

    def move_command(self, command: bytes) -> None:
        """Send a move command and check return value."""
        # Movement commands respond with ":A \n" but the move is then
        # being performed.  The move is only finihsed once the
        # "STATUS" command returns "N" rather than "B"
        self._command_and_validate(command, b"N")
        #
        # No Following is not true as Cockpit expects moves to happen
        # before the return.
        # actully beter to just issue the move command and rely on
        # other process to check position
        # self.get_command(command)

    def move_by_relative_position(self, axis: bytes, delta: float) -> None:
        """Send a relative movement command to stated axis"""
        axisname = AXIS_MAPPER[axis]
        self.move_command(
            bytes("MOVREL {0}={1}".format(axisname, str(delta)), "ascii")
        )

    def move_to_absolute_position(self, axis: bytes, pos: float) -> None:
        """Send a relative movement command to stated axis"""
        axisname = AXIS_MAPPER[axis]
        self.move_command(
            bytes("MOVE {0}={1}".format(axisname, str(pos)), "ascii")
        )

    def move_to_limit(self, axis: bytes, speed: int):
        axisname = AXIS_MAPPER[axis]
        self.get_command(
            bytes("SPIN {0}={1}".format(axisname, speed), "ascii")
        )

    def motor_moving(self, axis: bytes) -> int:
        axisname = AXIS_MAPPER[axis]
        reply = self.get_command(bytes("RDSTAT {0}".format(axisname), "ascii"))
        flags = int(reply.strip()[3:])
        return flags & 1

    def set_speed(self, axis: bytes, speed: int) -> None:
        axisname = AXIS_MAPPER[axis]
        self.get_command(
            bytes("SPEED {0}={1}".format(axisname, speed), "ascii")
        )

    def wait_for_motor_stop(self, axis: bytes):
        while self.motor_moving(axis):
            time.sleep(0.1)

    def reset_position(self, axis: bytes):
        axisname = AXIS_MAPPER[axis]
        self.get_command(bytes("HERE {0}=0".format(axisname), "ascii"))

    def get_absolute_position(self, axis: bytes) -> float:
        axisname = AXIS_MAPPER[axis]
        position = self.get_command(
            bytes("WHERE {0}".format(axisname), "ascii")
        )
        if position[3:4] == b"N":
            print(
                "Error: {0} : {1}".format(
                    position, LUDL_ERRORS[int(position[4:6])]
                )
            )
        else:
            return float(position.strip()[2:])

    def set_command(self, command: bytes) -> None:
        """Send a set command and check return value."""
        # Property type commands that set certain status respond with
        # zero.  They respond with a zero even if there are invalid
        # arguments in the command.
        self._command_and_validate(command, b"0\r")

    def get_description(self, command: bytes) -> bytes:
        """Send a get description command and return it."""
        with self._lock:
            self.command(command)
            return self._serial.read_until(b"\rEND\r")

    @contextlib.contextmanager
    def changed_timeout(self, new_timeout: float):
        previous = self._serial.timeout
        try:
            self._serial.timeout = new_timeout
            yield
        finally:
            self._serial.timeout = previous


class _LudlStageAxis(microscope.abc.StageAxis):
    def __init__(self, dev_conn: _LudlController, axis: str) -> None:
        super().__init__()
        self._dev_conn = dev_conn
        self._axis = axis
        # not a good solution as min/max are used to build the stage map in
        # mosaic etc... Maybe we just need to know it!
        self.min_limit = 0.0
        self.max_limit = 100000.0
        self.set_speed(100000)

    def move_by(self, delta: float) -> None:
        self._dev_conn.move_by_relative_position(self._axis, int(delta))

    def move_to(self, pos: float) -> None:
        self._dev_conn.move_to_absolute_position(self._axis, int(pos))

    @property
    def position(self) -> float:
        if self._dev_conn.is_busy():
            _logger.warning("querying stage axis position but device is busy")
            self._dev_conn.wait_until_idle()
        return float(self._dev_conn.get_absolute_position(self._axis))

    @property
    def limits(self) -> microscope.AxisLimits:
        return microscope.AxisLimits(
            lower=self.min_limit, upper=self.max_limit
        )

    #   def speed(self) -> int:
    #       return self.speed

    def home(self) -> None:
        self.find_limits()
        self.move_to(self.max_limit / 2)

    def set_speed(self, speed: int) -> None:
        self.speed = speed
        self._dev_conn.set_speed(self._axis, speed)

    def find_limits(self, speed=100000):
        # drive axis to minimum pos, zero and then drive to max position
        self._dev_conn.move_to_limit(self._axis, -speed)
        # spin moves dont set the status info need to query the motor
        # status byte
        self._dev_conn.wait_for_motor_stop(self._axis)
        # reset positon to zero.
        print(self.position)
        self._dev_conn.reset_position(self._axis)
        self.min_limit = 0.0
        self._dev_conn.homed = True
        # move to positive limit
        self._dev_conn.move_to_limit(self._axis, speed)
        self._dev_conn.wait_for_motor_stop(self._axis)
        self.max_limit = self.position
        return self.limits


class _LudlStage(microscope.abc.Stage):
    def __init__(self, conn: _LudlController, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dev_conn = conn
        self._axes = {
            str(i): _LudlStageAxis(self._dev_conn, i)
            for i in range(1, 3)  # self._dev_conn.get_number_axes() + 1)
        }
        self.homed = False

    def _do_shutdown(self) -> None:
        pass

    def _do_enable(self) -> bool:
        # Before a device can moved, it first needs to establish a
        # reference to the home position.  We won't be able to move
        # unless we home it first.
        if not self.homed:
            axes = self.axes
            for axis in axes:
                self.axes[axis].home()
            self.homed = True
        return True

    def may_move_on_enable(self) -> bool:
        return not self.homed

    @property
    def axes(self) -> typing.Mapping[str, microscope.abc.StageAxis]:
        return self._axes

    def move_by(self, delta: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance."""
        for axis_name, axis_delta in delta.items():
            self._dev_conn.move_by_relative_position(
                int(axis_name),
                int(axis_delta),
            )
        self._dev_conn.wait_until_idle()

    def move_to(self, position: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance."""
        print(position)
        for axis_name, axis_position in position.items():
            self._dev_conn.move_to_absolute_position(
                int(axis_name),
                int(axis_position),
            )
        self._dev_conn.wait_until_idle()


#    def assert_filterwheel_number(self, number: int) -> None:
#        assert number > 0 and number < 4

#    def _has_thing(self, command: bytes, expected_start: bytes) -> bool:
#        # Use the commands that returns a description string to find
#        # whether a specific device is connected.
#        with self._lock:
#            description = self.get_description(command)
#            if not description.startswith(expected_start):
#                self.read_until_timeout()
#                raise RuntimeError(
#                    "Failed to get description '%s' (got '%s')"
#                    % (command.decode(), description.decode())
#                )
#        return not description.startswith(expected_start + b"NONE\r")

# def has_filterwheel(self, number: int) -> bool:
#     self.assert_filterwheel_number(number)
#     # We use the 'FILTER w' command to check if there's a filter
#     # wheel instead of the '?' command.  The reason is that the
#     # third filter wheel, named "A AXIS" on the controller box and
#     # "FOURTH" on the output of the '?' command, can be used for
#     # non filter wheels.  We hope that 'FILTER 3' will fail
#     # properly if what is connected to "A AXIS" is not a filter
#     # wheel.
#     return self._has_thing(b"FILTER %d" % number, b"FILTER_%d = " % number)

# def get_n_filter_positions(self, number: int) -> int:
#     self.assert_filterwheel_number(number)
#     answer = self.get_command(b"FPW %d" % number)
#     return int(answer)

# def get_filter_position(self, number: int) -> int:
#     self.assert_filterwheel_number(number)
#     answer = self.get_command(b"7 %d F" % number)
#     return int(answer)

# def set_filter_position(self, number: int, pos: int) -> None:
#     self.assert_filterwheel_number(number)
#     self.move_command(b"7 %d %d" % (number, pos))


# IMD 20220408
# Not yet implemented filterwheel or shutters as I dont have any on my system


class LudlMC2000(microscope.abc.Controller):
    """Ludl MC 2000 controller.

    .. note::

       The Ludl MC2000 can control a stage, filter wheels, and
       shutters but only the stage is currently implemented.

    """

    def __init__(
        self, port: str, baudrate: int = 9600, timeout: float = 0.5, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._conn = _LudlController(port, baudrate, timeout)
        self._devices: typing.Mapping[str, microscope.abc.Device] = {}
        self._devices["stage"] = _LudlStage(self._conn)

    #        # Can have up to three filter wheels, numbered 1 to 3.
    #        for number in range(1, 4):
    #            if self._conn.has_filterwheel(number):
    #                key = "filter %d" % number
    #                self._devices[key] = _ludlFilterWheel(self._conn, number)

    @property
    def devices(self) -> typing.Mapping[str, microscope.abc.Device]:
        return self._devices


# ludl controller can do filter wheels so leave this code for future adoption
#
# class _ludlFilterWheel(microscope.abc.FilterWheel):
#     def __init__(self, connection: _ludlConnection, number: int) -> None:
#         super().__init__(positions=connection.get_n_filter_positions(number))
#         self._conn = connection
#         self._number = number

#     def _do_get_position(self) -> int:
#         return self._conn.get_filter_position(self._number)

#     def _do_set_position(self, position: int) -> None:
#         self._conn.set_filter_position(self._number, position)

#     def _do_shutdown(self) -> None:
#         pass
