#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2022-23 Ian Dobbie <ian.dobbie@jhu.edu>
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

"""ASI ms2000 controller.
"""

import contextlib
import re
import threading
import time
import typing
import logging
from typing import Callable, Any, Dict, Union

import serial

import microscope.abc
import microscope._utils
from microscope import DeviceError, InitialiseError

_logger = logging.getLogger(__name__)

# Started to develop by copying from the ludl driver.
# no support for filter, shutters, or slide loader as I dont have hardware

# Note:
# commands end in a '\r' but replies return ending in '\r\n'!

# Quick Reference – Main Operating Commands
# ------------------------------------------
# <del> or <bs> - Abort current command and flush input buffer
# Command Shortcut Description
# CDATE CD Returns Date/Time current firmware was compiled
# HALT \ Halts all serial commands being executed
# HERE H Writes a position to an axis position buffer
# HOME ! Tells stage to go to physical limit switches
# INFO I Returns a screen full of information about the axis
# MOTCTRL MC Enables/Disables motor control for axis
# MOVE M Writes a position to an axis target buffer
# MOVREL R Writes a relative position to target buffer
# RDSBYTE RB Returns a Status Information byte for an axis
# RDSTAT RS Same as RDSBYTE, in decimal ASCII format.
# RESET ~ Resets the MFC-2000 and MS-2000 controller
# SPEED S Sets the maximum velocity/speed of axis
# SPIN @ Causes axis to spin motor at given DAC rate
# STATUS / Returns B-Busy, N-Not Busy
# UNITS UN Toggles LCD units – mm or in – when DIP switch 2 is down
# WHERE W Returns current position
# ZERO Z Sets all axes to zero/set position to origin

# command set based on the Ludl control so module copied from the ludl driver

# ASI error codes
# Error Codes for MS-2000 Diagnostics
# Error codes are dumped to the screen with the last error code shown first using the ‘DU Y‘
# command. The table below lists the meanings of the error codes as of this publication.
# Error Number* Error Description
_ASI_ERRORS = {
    0: "No Error",
    1: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    2: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    3: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    4: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    5: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    6: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    7: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    8: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    9: "OVERTIME - RECOVERABLE. Error caused by competing tasks using the microprocessor.",
    10: "OVERSHOT - Move overshot the target; happens frequently, not really an error.",
    11: "OVERSHOT - Move overshot the target; happens frequently, not really an error.",
    12: "OVERSHOT - Move overshot the target; happens frequently, not really an error.",
    15: "NEGATIVE LOG - Negative number for Log conversion.",
    20: "AXIS DEAD - FATAL. No movement for 100 cycles; axis halted.",
    21: "AXIS DEAD - FATAL. No movement for 100 cycles; axis halted.",
    22: "AXIS DEAD - FATAL. No movement for 100 cycles; axis halted.",
    24: "ENCODER_ERROR",
    30: "EMERGENCY STOP - FATAL. Getting further from the target; axis halted.",
    31: "EMERGENCY STOP - FATAL. Getting further from the target; axis halted.",
    32: "EMERGENCY STOP - FATAL. Getting further from the target; axis halted.",
    34: "UPPER LIMIT - Upper Limit reached. (axis unspecific)",
    35: "LOWER LIMIT - Lower Limit reached. (axis unspecific)",
    40: "PULSE PARAMETER VALUES OUT OF RANGE - code error.",
    41: "PULSE PARAMETER VALUES OUT OF RANGE - code error.",
    42: "PULSE PARAMETER VALUES OUT OF RANGE - code error.",
    44: "FINISH SPEED CLAMP - Reached the maximum allowed move-finishing speed.",
    45: "ADC_LOCK_OOR - Out-of-range error on ADC input.",
    46: "ADC_FOLLOW_ERR - Error attempting to follow an analog ADC input.",
    50: "ENCODER ERROR OVERFLOW - FATAL. Error term so large that move intent is indiscernible; axis halted.",
    51: "ENCODER ERROR OVERFLOW - FATAL. Error term so large that move intent is indiscernible; axis halted.",
    52: "ENCODER ERROR OVERFLOW - FATAL. Error term so large that move intent is indiscernible; axis halted.",
    55: "EPROM NO LOAD - Saved-settings on EPROM not loaded, compile date mismatch.",
    60: "ADJUST-MOVE ERROR - Failed to clear ‘M’ soon enough. FATAL",
    61: "ADJUST-MOVE ERROR - Failed to clear ‘M’ soon enough. FATAL",
    62: "ADJUST-MOVE ERROR - Failed to clear ‘M’ soon enough. FATAL",
    85: "SCAN LOST PULSES - During a scan, missing pulses were detected.",
    86: "SCAN INCOMPLETE - During a scan, terminated before completing the row.",
    90: "ERROR_LARGE - RECOVERABLE. Error large. Motor set to FULL SPEED; hope to catch up.",
    91: "ERROR_LARGE - RECOVERABLE. Error large. Motor set to FULL SPEED; hope to catch up.",
    92: "ERROR_LARGE - RECOVERABLE. Error large. Motor set to FULL SPEED; hope to catch up.",
    100: "INDEX NOT FOUND",
    101: "INDEX NOT FOUND",
    102: "INDEX NOT FOUND",
    140: "PIEZO WRITE DAC - Error writing to the piezo DAC.",
    141: "PIEZO READ DAC - Error reading from piezo DAC",
    142: "PIEZO READ POS",
    143: "PIEZO WRITE POS",
    144: "PIEZO MOVE ERR",
    145: "PIEZO READ POS1",
    146: "PIEZO INIT",
    147: "PIEZO POS ERROR",
    148: "Autofocus 200um safety limit Encountered",
    149: "I2C_BAD_BUSY ERROR",
    173: "I2C_AXIS_ENABLE_ERR1",
    174: "I2C_AXIS_ENABLE_ERR2",
    175: "I2C_AXIS_MUTE1_ERR",
    176: "I2C_AXIS_MUTE2_ERR",
    203: "I2C_NACK_ERROR",
    205: "ERR_TTL_MISMATCH I2C bus error.",
    255: "10 MINUTE CLOCK - Provides time reference for error dump list.",
    300: "Autofocus Scan failed due to insufficient contrast",
    302: "Clutch Disengaged, Engage clutch to do Autofocus",
}


# Status bits for an axis

# Bit 0: 0 = No commanded move is in progress. 1 = A commanded move is in progress. This bit
# is synonymous with the STATUS command. If the bit is set, then STATUS
# returns 'B', otherwise STATUS returns 'N'.
# Bit 1: 0 = The axis is disabled. It can be renabled by one of the following: High Level command
# MC <axis>+, cycling the clutch switch for the Z-axis, Low Level StartMotor
# command (hex 47), or a system reset. This feature is available in versions 6.2c and
# later; 1 = The axis is enabled.
# Bit 2: 0 = Motor is inactive (off), 1 = Motor is active (on).
# Bit 3: 0 = Joystick/Knob disabled, 1 = Joystick/Knob enabled
# Bit 4: 0 = Motor not ramping, 1 = Motor ramping
# Bit 5: 0 = Ramping up, 1= Ramping down
# Bit 6: Upper limit switch: 0 = open, 1 = closed
# Bit 7: Lower limit switch: 0 = open, 1 = closed


def parse_info(
    info: list,
) -> dict[str, dict[str, Union[typing.Optional[str], Any]]]:
    items = []
    for line in info:
        if line in [b"", b"\n", b"\r", b"\r\n"]:
            continue
        items.append(line[:33].strip().decode())
        items.append(line[33:].strip().decode())

    pattern = r"(?P<name>.*):\s*((?P<value>\S+)(\s+)?(?P<command>[\[].*[\]])?(\s+)?(?P<units>.*)?)$"

    settings = {}
    for item in items:
        match = re.search(pattern, item)
        try:
            name = match.group("name")
        except AttributeError:
            _logger.warning(
                f"Error parsing info. No item name found on: {item}"
            )
            continue
        try:
            value = match.group("value")
        except AttributeError:
            _logger.warning(
                f"Error parsing info. No item value found on: {item}"
            )
            continue
        settings[name.strip()] = {
            "value": value,
            "command": None
            if not match.group("command")
            else match.group("command")[1:-1],
            "units": match.group("units")
            if len(match.group("units"))
            else None,
        }

    return settings


class _ASIController:
    """Connection to a ASI Controller and wrapper to its commands.

    Tested with MS2000 controller and xy stage.

    This class also implements the logic to parse and validate
    commands so it can be shared between multiple devices.

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
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        self._lock = threading.RLock()

        # We do not use the general get_description() here because
        # if this is not a ProScan device it would never reach the
        # '\rEND\r' that signals the end of the description.
        self.axis_info = {}
        self.axis_list = []
        try:
            for axis in ["X", "Y", "Z"]:
                self.command(bytes(f"INFO {axis}", "ascii"))
                answer = self.read_multiline()
                if answer == [b""]:  # no axis present
                    _logger.info(f"Axis {axis} not present")
                    continue
                _logger.info(f"Axis {axis} present")
                self.axis_info[axis] = parse_info(answer)
                self.axis_list.append(axis)
        except Exception as e:
            raise InitialiseError(
                f"Unable to read configuration. Is ASI controller connected?: {e}"
            )

        # As for this version, some MS2000 controllers have integrated control for 2 LEDs
        self.led_list = [b"X", b"Y"]

        # parse config response which tells us what devices are present
        # on this controller.

    def is_busy(self):
        pass

    def get_number_axes(self):
        return len(self.axis_list)

    def get_number_leds(self):
        return len(self.led_list)

    def command(self, command: bytes) -> None:
        """Send command to device."""
        with self._lock:
            self._serial.write(command + b"\r")

    def readline(self) -> bytes:
        """Read a line from the device connection until ``\\r\\n``."""
        with self._lock:
            # We actually read until the \\r cause multiline does not add the \\n
            line = self._serial.read_until(b"\r")
            #            _logger.warning
            return line

    def read_multiline(self):
        output = []
        line = True
        while line:
            line = self.readline()
            output.append(line.strip(b"\r"))
            if line:
                # was there any data on this line?
                if line == b"N" or line[0:2] == b":A":
                    # this means an end of command strings doesnt require an
                    # additional timeout before it returns
                    return output
                elif line[0] == b"N":
                    # this is an error string
                    error = line[2:].strip()
                    raise (
                        f"ASI controller error: {error},{_ASI_ERRORS[error]}"
                    )
        return output

    def read_until_timeout(self) -> None:
        """Read until timeout; used to clean buffer if in an unknown state."""
        with self._lock:
            self._serial.flushInput()
            while self._serial.readline():
                continue

    def wait_until_idle(self) -> None:
        """Keep sending the ``STATUS`` command until it responds ``0\\r``"""
        self._command_and_validate(b"STATUS", b"N")

    def _command_and_validate(self, command: bytes, expected: bytes) -> bytes:
        with self._lock:
            answer = self.get_command(command)
            if answer == b":A \r\n":
                # wait for move to stop
                while self.get_command(b"STATUS") != expected:
                    time.sleep(0.01)
            return answer

    def get_command(self, command: bytes) -> bytes:
        """Send get command and return the answer."""
        with self._lock:
            self.command(command)
            return self.readline()

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

    # Motion related methods #
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

    def move_by_relative_position(
        self, axis: str, delta: float, wait=True
    ) -> None:
        """Send a relative movement command to stated axis"""
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        self.move_command(bytes(f"MOVREL {axis}={str(delta)}", "ascii"))
        if wait:
            self.wait_for_motor_stop(axis)

    def move_to_absolute_position(
        self, axis: str, pos: float, wait=True
    ) -> None:
        """Send a relative movement command to stated axis"""
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        self.move_command(bytes(f"MOVE {axis}={str(pos)}", "ascii"))
        if wait:
            self.wait_for_motor_stop(axis)

    def move_to_limit(self, axis: str, speed: int):
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        self.get_command(bytes(f"SPIN {axis}={speed}", "ascii"))

    def motor_moving(self, axis: str) -> int:
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        reply = self.get_command(bytes(f"RDSTAT {axis}", "ascii"))
        flags = int(reply.strip()[3:])
        return flags & 1

    def set_speed(self, axis: str, speed: int) -> None:
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        self.get_command(bytes(f"SPEED {axis}={speed}", "ascii"))

    def find_max_speed(self, axis: str):
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        speed = 100000000
        # set the speed
        self.get_command(bytes(f"SPEED {axis}={speed}", "ascii"))
        # read off the max speed set by controller
        response = self.get_command(bytes(f"SPEED {axis}?", "ascii"))
        return float(response.strip()[5:])

    def wait_for_motor_stop(self, axis: str):
        # give axis a chance to start maybe?
        time.sleep(0.2)
        while self.motor_moving(axis):
            time.sleep(0.1)

    def reset_position(self, axis: str):
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        self.get_command(bytes(f"HERE {axis}=0", "ascii"))

    def get_absolute_position(self, axis: str) -> float:
        if axis not in self.axis_list:
            raise ValueError(
                f"Axis {axis} not present. Verify the name of the axis or your configuration files."
            )
        position = self.get_command(bytes(f"WHERE {axis}", "ascii"))
        if position[3:4] == b"N":
            print(f"Error: {position} : {_ASI_ERRORS[int(position[4:6])]}")
        else:
            return float(position.strip()[2:])

    # Light related methods #
    def is_led_on(self, channel):
        return bool(self.get_led_power(channel))

    def get_led_power(self, channel):
        answer = self.get_command(b"LED " + self.led_list[channel] + b"?")
        return int(answer[3:-4]) / 100

    def set_led_power(self, channel, power):
        power = str(int(power * 100)).encode()
        self.get_command(b"LED " + self.led_list[channel] + b"=" + power)


class _ASIStageAxis(microscope.abc.StageAxis):
    def __init__(self, dev_conn: _ASIController, axis: str) -> None:
        super().__init__()
        self._dev_conn = dev_conn
        self._axis = axis
        # not a good solution as min/max are used to build the stage map in
        # mosaic etc... Maybe we just need to know it!
        self.min_limit = 0.0
        self.max_limit = 100000.0
        # As detailed in ASI manual set speed to 67% of max
        max_speed = self._dev_conn.find_max_speed(self._axis)
        self.set_speed(max_speed * 0.67)

    def move_by(self, delta: float) -> None:
        self._dev_conn.move_by_relative_position(self._axis, int(delta))

    def move_to(self, pos: float) -> None:
        print("axis", self._axis)
        print("go to ", pos)
        self._dev_conn.move_to_absolute_position(self._axis, int(pos))
        print("got to ", self.position)

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
        self._dev_conn.wait_for_motor_stop(self._axis)

    def set_speed(self, speed: int) -> None:
        self.speed = speed
        self._dev_conn.set_speed(self._axis, speed)

    def find_limits(self, speed=100):
        # drive axis to minimum pos, zero and then drive to max position
        # spin speed is limited to +/- 128 100 chosen as fast but not maximum.
        self._dev_conn.move_to_limit(self._axis, -speed)
        # spin moves dont set the status info need to query the motor
        # status byte
        self._dev_conn.wait_for_motor_stop(self._axis)
        # reset positon to zero.
        print("axis", self._axis)
        print("min=", self.position)
        self._dev_conn.reset_position(self._axis)
        self.min_limit = self.position
        print("minpos", self.min_limit)
        self._dev_conn.homed = True
        # move to positive limit
        self._dev_conn.move_to_limit(self._axis, speed)
        self._dev_conn.wait_for_motor_stop(self._axis)
        print("max=", self.position)
        self.max_limit = self.position
        print(self.limits)
        return self.limits


class _ASIStage(microscope.abc.Stage):
    def __init__(self, conn: _ASIController, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dev_conn = conn
        self._axes = {
            a: _ASIStageAxis(self._dev_conn, a)
            for a in self._dev_conn.axis_list
        }

        self._add_settings(self._dev_conn.axis_info)

        self.homed = False

    def _get_setting(self, command, axis, dtype, value):
        if command is None:
            return value
        answer = self._dev_conn.get_command(
            bytes(f"{command} {axis}?", "ascii")
        )
        answer = answer.strip().decode()
        if answer[:2] == ":A":
            if (
                answer[-2:] == " A"
            ):  # Some setting return a non-standard pattern with two A's: ':A axis=value A'
                answer = answer[5:-1]
            elif (
                command == "MC"
            ):  # The MC command does not follow the standard return pattern. It returns ':A 1'
                answer = answer[3:]
            else:
                answer = answer[
                    5:
                ]  # What I believe is the standard pattern: ':A axis=value' (':A X=42')
        elif answer[:2] == f":{axis}":
            answer = answer[
                3:-2
            ]  # Many settings return ':axis=value A' (':X=42 A')
        elif answer[0] == "N":
            # this is an error string
            error = answer[2:]
            raise Exception(
                f"ASI controller error on command {command}: {error},{_ASI_ERRORS[error]}"
            )
        else:
            raise Exception(
                f"ASI controller error on command {command}: {answer}"
            )

        if dtype == "int":
            return int(answer)
        elif dtype == "float":
            return float(answer)
        else:
            return answer

    def _set_setting(self, value, command, axis):
        if command is None:
            return False
        else:
            self._dev_conn.set_command(
                bytes(f"{command} {axis}={value}", "ascii")
            )

    def _add_settings(self, settings) -> None:
        """INFO command returns a list of settings that is parsed into a dict. This function takes that dict and
        adds settings consequently to the stage object.
        """
        for axis, axis_settings in settings.items():
            for setting_name, setting_params in axis_settings.items():
                if setting_params["value"].replace("-", "", 1).isdigit():
                    value = int(setting_params["value"])
                    dtype = "int"
                elif (
                    setting_params["value"]
                    .replace(".", "", 1)
                    .replace("-", "", 1)
                    .isdigit()
                ):
                    value = float(setting_params["value"])
                    dtype = "float"
                else:
                    value = setting_params["value"]
                    dtype = "str"  # It might be a enum but we dont know

                if setting_params["command"] is not None:
                    read_only = False
                else:
                    read_only = True

                self.add_setting(
                    name=f"{setting_name} {axis}",
                    dtype=dtype,
                    get_func=lambda command=setting_params[
                        "command"
                    ], axis=axis, dtype=dtype, value=value: self._get_setting(
                        command, axis, dtype, value
                    ),
                    set_func=lambda value, command=setting_params[
                        "command"
                    ], axis=axis: self._set_setting(value, command, axis),
                    values=lambda: f"Units are {setting_params['units']}",
                    # readonly=read_only,
                )

    def _do_shutdown(self) -> None:
        pass

    def _do_enable(self) -> bool:
        # Before a device can move, it first needs to establish a
        # reference to the home position.  We won't be able to move
        # unless we home it first.
        if not self.homed:
            axes = self.axes
            print(axes)
            for axis in axes:
                print(axis, self.axes[axis])
                self.axes[axis].home()
                print(axis, "homed")
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
                axis_name, int(axis_delta), wait=False
            )
        self._dev_conn.wait_until_idle()

    def move_to(self, position: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance."""
        print(position)
        for axis_name, axis_position in position.items():
            self._dev_conn.move_to_absolute_position(
                axis_name, int(axis_position), wait=False
            )
        self._dev_conn.wait_until_idle()


class _ASILED(
    microscope._utils.OnlyTriggersBulbOnSoftwareMixin,
    microscope.abc.LightSource,
):
    # In principle the light source of the MS2000 and the tiger controllers support triggers, but as not yet implemented
    # we set this class as oly triggerable by software
    # TODO: Look into implementation of triggers

    def __init__(self, dev_conn: _ASIController, channel: int) -> None:
        super().__init__()
        self._dev_conn = dev_conn
        self._channel = channel
        self._do_disable()

    def get_status(self) -> typing.List[str]:
        return (
            super().get_status()
        )  # TODO: Verify what am I doing here. Just copying from the Zaber led controller

    def get_is_on(self) -> bool:
        return self._dev_conn.is_led_on(self._channel)

    def _do_get_power(self) -> float:
        return self._dev_conn.get_led_power(self._channel)

    def _do_set_power(self, power: float) -> None:
        self._dev_conn.set_led_power(self._channel, power)

    def _do_enable(self):
        self._do_set_power(self._set_point)

    def _do_disable(self):
        self._do_set_power(0.0)

    def _do_shutdown(self) -> None:
        self._do_disable()


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


class ASIMS2000(microscope.abc.Controller):
    """ASI Ms 2000 controller.

    .. note::

       The ASI MS2000 can control a stage, and other items.
       This version implements:
       stage: X, Y, Z axes
       lights: up to 2 lights are supported by some MS2000 controllers. Use the lights argument to send a list of
       one or two lights defined as strings.

    """

    def __init__(
        self, port: str, baudrate: int = 9600, timeout: float = 0.5, **kwargs
    ) -> None:
        super().__init__()
        self._conn = _ASIController(port, baudrate, timeout)
        self._devices: typing.Mapping[str, microscope.abc.Device] = {}
        self._devices["stage"] = _ASIStage(self._conn)
        for light_ch, light in enumerate(kwargs["lights"]):
            self._devices[light] = _ASILED(self._conn, light_ch)

    @property
    def devices(self) -> typing.Mapping[str, microscope.abc.Device]:
        return self._devices
