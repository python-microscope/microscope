#!/usr/bin/env python3

## Copyright (C) 2021 David Miguel Susano Pinto <carandraug@gmail.com>
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

import logging
import typing

import serial

import microscope
import microscope._utils
import microscope.abc


_LOGGER = logging.getLogger(__name__)

_QUOTATION_CODE = ord(b'"')


def _parse_string(answer: bytes) -> str:
    assert answer[0] == _QUOTATION_CODE and answer[-1] == _QUOTATION_CODE
    return answer[1:-1].decode()


def _parse_bool(answer: bytes) -> bool:
    assert answer in [b"#f", b"#t"]
    return answer == b"#t"


class _iChromeConnection:
    """Connection to the iChrome MLE.

    This is a simple wrapper to the iChrome MLE interface.  It only
    supports the parameter commands which reply with a single line
    which is all we need to support this on Python-Microscope.

    """

    def __init__(self, shared_serial: microscope._utils.SharedSerial) -> None:
        self._serial = shared_serial

        self._serial.readlines()  # discard anything that may be on the line

        if self.get_system_type() != "iChrome-MLE":
            raise microscope.DeviceError("not an iChrome MLE device")

    def _param_command(self, command: bytes) -> bytes:
        """Run command and return raw answer (minus prompt and echo)."""
        command = command + b"\r\n"
        with self._serial.lock:
            self._serial.write(command)
            answer = self._serial.read_until(b"\r\n> ")

        # When we read, we are reading the whole command console
        # including the prompt and even the command is echoed back.
        assert answer[: len(command)] == command and answer[-4:] == b"\r\n> "

        # Errors are indicated by the string "Error: " at the
        # beginning of a new line.
        if answer[len(command) : len(command) + 7] == b"Error: ":
            base_command = command[:-2]
            error_msg = answer[len(command) + 8 : -4]
            raise microscope.DeviceError(
                "error on command '%s': %s"
                % (base_command.decode(), error_msg.decode())
            )

        # Return the answer minus the "echoed" command and the prompt
        # for the next command.
        return answer[len(command) : -4]

    def param_ref(self, name: bytes) -> bytes:
        """Get parameter value (`param-ref` operator)."""
        return self._param_command(b"(param-ref '%s)" % name)

    def param_set(self, name: bytes, value: bytes) -> None:
        """Change parameter (`param-set!` operator)."""
        answer = self._param_command(b"(param-set! '%s %s)" % (name, value))
        status = int(answer)
        if status < 0:
            raise microscope.DeviceError(
                "Failed to set parameter %s (return value %d)"
                % (name.decode(), status)
            )

    def get_serial_number(self) -> str:
        return _parse_string(self.param_ref(b"serial-number"))

    def get_system_type(self) -> str:
        return _parse_string(self.param_ref(b"system-type"))


class _iChromeLaserConnection:
    def __init__(self, conn: _iChromeConnection, laser_number: int) -> None:
        self._conn = conn
        self._param_prefix = b"laser%d:" % laser_number

        # We Need to confirm that indeed there is a laser at this
        # position.  There is no command to check this, we just try to
        # read a parameter and check if it works.
        try:
            self.get_label()
        except microscope.DeviceError as ex:
            raise microscope.DeviceError(
                "failed to get label, probably no laser %d" % laser_number
            ) from ex

    def _param_ref(self, name: bytes) -> bytes:
        return self._conn.param_ref(self._param_prefix + name)

    def _param_set(self, name: bytes, value: bytes) -> None:
        self._conn.param_set(self._param_prefix + name, value)

    def get_label(self) -> str:
        return _parse_string(self._param_ref(b"label"))

    def get_type(self) -> str:
        return _parse_string(self._param_ref(b"type"))

    def get_delay(self) -> int:
        return int(self._param_ref(b"delay"))

    def get_enable(self) -> bool:
        return _parse_bool(self._param_ref(b"enable"))

    def set_enable(self, state: bool) -> None:
        value = b"#t" if state else b"#f"
        self._param_set(b"enable", value)

    def get_cw(self) -> bool:
        return _parse_bool(self._param_ref(b"cw"))

    def set_cw(self, state: bool) -> None:
        value = b"#t" if state else b"#f"
        self._param_set(b"cw", value)

    def get_use_ttl(self) -> bool:
        return _parse_bool(self._param_ref(b"use-ttl"))

    def set_use_ttl(self, state: bool) -> None:
        value = b"#t" if state else b"#f"
        self._param_set(b"use-ttl", value)

    def get_level(self) -> float:
        return float(self._param_ref(b"level"))

    def set_level(self, level: float) -> None:
        value = b"%.1f" % level
        self._param_set(b"level", value)

    def get_status_txt(self) -> str:
        return _parse_string(self._param_ref(b"status-txt"))


class _iChromeLaser(microscope.abc.LightSource):
    def __init__(self, conn: _iChromeConnection, laser_number: int) -> None:
        super().__init__()
        self._conn = _iChromeLaserConnection(conn, laser_number)

        # FIXME: set values to '0' because we need to pass an int as
        # values for settings of type str.  Probably a bug on
        # Device.set_setting.
        self.add_setting("label", "str", self._conn.get_label, None, values=0)
        self.add_setting("type", "str", self._conn.get_type, None, values=0)

        self.add_setting(
            "delay", "int", self._conn.get_delay, None, values=tuple()
        )

    def get_status(self) -> typing.List[str]:
        return self._conn.get_status_txt().split()

    def get_is_on(self) -> bool:
        if self._conn.get_enable():
            if self._conn.get_cw():
                return True
            else:
                # There doesn't seem to be command to check whether
                # the TTL line is currently high, so just return True
                # if set that way.
                return self._conn.get_use_ttl()
        else:
            return False

    def _do_get_power(self) -> float:
        return self._conn.get_level() / 100.0

    def _do_set_power(self, power: float) -> None:
        self._conn.set_level(power * 100.0)

    def _do_enable(self) -> None:
        self._conn.set_enable(True)

    def _do_disable(self) -> None:
        self._conn.set_enable(False)

    def _do_shutdown(self) -> None:
        pass  # Nothing to do

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return microscope.TriggerMode.BULB

    @property
    def trigger_type(self) -> microscope.TriggerType:
        if self._conn.get_use_ttl():
            return microscope.TriggerType.HIGH
        else:
            return microscope.TriggerType.SOFTWARE

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if tmode is not microscope.TriggerMode.BULB:
            raise microscope.UnsupportedFeatureError(
                "only TriggerMode.BULB mode is supported"
            )

        # From the manual it seems that cw and ttl parameters are
        # mutually exclusive but also still need to be set separately.
        if ttype is microscope.TriggerType.HIGH:
            self._conn.set_cw(False)
            self._conn.set_use_ttl(True)
        elif ttype is microscope.TriggerType.SOFTWARE:
            self._conn.set_use_ttl(False)
            self._conn.set_cw(True)
        else:
            raise microscope.UnsupportedFeatureError(
                "only trigger type HIGH and SOFTWARE are supported"
            )

    def _do_trigger(self) -> None:
        raise microscope.IncompatibleStateError(
            "trigger does not make sense in trigger mode bulb, only enable"
        )


class iChromeMLE(microscope.abc.Controller):
    """Toptica iChrome MLE (multi-laser engine).

    The names of the light devices are `laser1`, `laser2`, `laser3`,
    ...

    """

    def __init__(self, port: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lasers: typing.Dict[str, _iChromeLaser] = {}

        # Setting specified on the manual (M-051 version 03)
        serial_conn = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        shared_serial = microscope._utils.SharedSerial(serial_conn)
        ichrome_connection = _iChromeConnection(shared_serial)

        _LOGGER.info("Connected to %s", ichrome_connection.get_serial_number())

        # According to the manual the iChrome can have between 3 and 5
        # lasers.  There doesn't seem to be a simple command to check
        # what's installed, we'd have to parse the whole summary
        # table.  So we try/except to each laser line.
        for i in range(1, 6):
            name = "laser%d" % i
            try:
                laser = _iChromeLaser(ichrome_connection, i)
            except microscope.DeviceError:
                _LOGGER.info("no %s available", name)
                continue
            else:
                _LOGGER.info("found %s on iChrome MLE", name)
                self._lasers[name] = laser

    @property
    def devices(self) -> typing.Dict[str, _iChromeLaser]:
        return self._lasers
