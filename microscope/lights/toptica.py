#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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
import re
import typing

import serial

import microscope
import microscope._utils
import microscope.abc


_logger = logging.getLogger(__name__)


def _get_table_value(table: bytes, key: bytes) -> bytes:
    """Get the value for a key in a table/multiline output.

    Some commands return something like a table of key/values.  There
    may be even empty lines on this table.  This searches for the
    first line with a specific key (hopefully there's only one line
    with such key) and returns the associated value.
    """
    # Key might be the first line, hence '(?:^|\r\n)'
    match = re.search(b"(?:^|\r\n) *" + key + b": (.*)\r\n", table)
    if match is None:
        raise microscope.DeviceError(
            "failed to find key %s on table: %s" % (key, table)
        )
    return match.group(1)


class _iBeamConnection:
    """Connection to a specific Toptica iBeam smart laser.

    This class wraps the serial connection to the device, and provides
    access to some of its commands performing most of the parsing and
    validation.

    Args:
        port: port name (Windows) or path to port (everything else) to
            connect to.  For example, `/dev/ttyS1`, `COM1`, or
            `/dev/cuad1`.

    """

    def __init__(self, port: str):
        # From the Toptica iBeam SMART manual:
        # Direct connection via COMx with 115200,8,N,1 and serial
        # interface handshake "none". That means that no hardware
        # handshake (DTR, RTS) and no software handshake (XON,XOFF) of
        # the underlying operating system is supported.
        serial_conn = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=1.0,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        self._serial = microscope._utils.SharedSerial(serial_conn)

        # We don't know what is the current verbosity state and so we
        # don't know yet what we should be reading back.  So blindly
        # set to the level we want, flush all output, and then check
        # if indeed this is a Toptica iBeam device.
        with self._serial.lock:
            self._serial.write(b"echo off\r\n")
            self._serial.write(b"prompt off\r\n")
            # The talk level we want is 'usual'.  In theory we should
            # be able to use 'quiet' which only answers queries but in
            # practice 'quiet' does not answer some queries like 'show
            # serial'.
            self._serial.write(b"talk usual\r\n")
            self._serial.readlines()  # discard all pending lines

        # Empty command does nothing and returns nothing extra so we
        # use it to ensure this at least behaves like a Toptica iBeam.
        try:
            self.command(b"")
        except microscope.DeviceError as e:
            raise microscope.InitialiseError(
                "Failed to confirm Toptica iBeam on %s" % (port)
            ) from e

        answer = self.command(b"show serial")
        if not answer.startswith(b"SN: "):
            raise microscope.DeviceError(
                "Failed to parse serial from %s" % answer
            )
        _logger.info("got connection to Toptica iBeam %s", answer.decode())

    def command(self, command: bytes) -> bytes:
        """Run command and return answer after minimal validation.

        The output of a command has the format::

            \r\nANSWER\r\n[OK]\r\n

        The returned bytes only include `ANSWER` without its own final
        `\r\n`.  This means that the return value might be an empty
        array of bytes.
        """
        # We expect to be on 'talk usual' mode without prompt so each
        # command will end with [OK] on its own line.
        with self._serial.lock:
            self._serial.write(command + b"\r\n")
            # An answer always starts with \r\n so there will be one
            # before [OK] even if this command is not a query.
            answer = self._serial.read_until(b"\r\n[OK]\r\n")

        if not answer.startswith(b"\r\n"):
            raise microscope.DeviceError(
                "answer to command %s does not start with CRLF."
                " This may be leftovers from a previous command:"
                " %s" % (command, answer)
            )
        if not answer.endswith(b"\r\n[OK]\r\n"):
            raise microscope.DeviceError(
                "Command %s failed or failed to read answer: %s"
                % (command, answer)
            )

        # If an error occurred, the answer still ends in [OK].  We
        # need to check if the second line (first line is \r\n) is an
        # error code with the format "%SYS-L-XXX, error description"
        # where L is the error level (I for Information, W for
        # Warning, E for Error, and F for Fatal), and XXX is the error
        # code number.
        if answer[2:7] == b"%SYS-" and answer[7] != ord(b"I"):
            # Errors of level I (information) should not raise an
            # exception since they can be replies to normal commands.
            raise microscope.DeviceError(
                "Command %s failed: %s" % (command, answer)
            )

        # Exclude the first \r\n, the \r\n from a possible answer, and
        # the final [OK]\r\n
        return answer[2:-8]

    def laser_on(self) -> None:
        """Activate LD driver."""
        self.command(b"laser on")

    def laser_off(self) -> None:
        """Deactivate LD driver."""
        self.command(b"laser off")

    def set_normal_channel_power(self, power: float) -> None:
        """Set power in mW for channel 2 (normal operating level channel).

        We don't have channel number as an argument because we only
        want to be setting the power via channel 2 (channel 1 is the
        bias and we haven't seen a laser with a channel 3 yet).
        """
        self.command(b"channel 2 power %f" % power)

    def show_power_uW(self) -> float:
        """Returns actual laser power in µW."""
        answer = self.command(b"show power")
        if not answer.startswith(b"PIC  = ") and not answer.endswith(b" uW  "):
            raise microscope.DeviceError(
                "failed to parse power from answer: %s" % answer
            )
        return float(answer[7:-5])

    def status_laser(self) -> bytes:
        """Returns actual status of the LD driver (ON or OFF)."""
        return self.command(b"status laser")

    def show_max_power(self) -> float:
        # There should be a cleaner way to get these, right?  We can
        # query the current limits (mA) but how do we go from there to
        # the power limits (mW)?
        table = self.command(b"show satellite")
        value = _get_table_value(table, key=b"Pmax")
        if not value.endswith(b" mW"):
            raise microscope.DeviceError(
                "failed to parse power from %s" % value
            )
        return float(value[:-3])


class TopticaiBeam(
    microscope._utils.OnlyTriggersBulbOnSoftwareMixin,
    microscope.abc.LightSource,
):
    """Toptica iBeam smart laser.

    Control of laser power is performed by setting the power level on
    the normal channel (#2) only.  The bias channel (#1) is left
    unmodified and so defines the lowest level power.
    """

    def __init__(self, port: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._conn = _iBeamConnection(port)
        # The Toptica iBeam has up to five operation modes, named
        # "channels" on the documentation.  Only the first three
        # channels have any sort of documentation:
        #
        #   Ch 1: bias level channel
        #   Ch 2: normal operating level channel
        #   Ch 3: only used at high-power models
        #
        # We haven't come across a laser with a channel 3 so we are
        # ignoring it until then.  So we just leave the bias channel
        # (1) alone and control power via the normal channel (2).
        self._max_power = self._conn.show_max_power()

    def _do_shutdown(self) -> None:
        pass

    def get_status(self) -> typing.List[str]:
        status: typing.List[str] = []
        return status

    def enable(self) -> None:
        self._conn.laser_on()

    def disable(self) -> None:
        self._conn.laser_off()

    def get_is_on(self) -> bool:
        state = self._conn.status_laser()
        if state == b"ON":
            return True
        elif state == b"OFF":
            return False
        else:
            raise microscope.DeviceError(
                "Unexpected laser status: %s" % state.decode()
            )

    def _get_max_power_mw(self) -> float:
        return self._max_power

    def _get_power_mw(self) -> float:
        return self._conn.show_power_uW() * (10 ** -3)

    def _set_power_mw(self, mw: float) -> None:
        self._conn.set_normal_channel_power(mw)

    def _do_set_power(self, power: float) -> None:
        self._set_power_mw(power * self._get_max_power_mw())

    def _do_get_power(self) -> float:
        return self._get_power_mw() / self._get_max_power_mw()
