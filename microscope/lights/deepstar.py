#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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

import logging

import serial

import microscope
import microscope.abc


_logger = logging.getLogger(__name__)


class DeepstarLaser(
    microscope.abc.SerialDeviceMixin, microscope.abc.LightSource
):
    """Omicron DeepStar laser.

    Omicron LDM lasers can be bought with and without the LDM.APC
    power monitoring option (light pick-off).  If this option is not
    available, the `power` attribute will return the set power value
    instead of the actual power value.

    """

    def __init__(self, com, baud=9600, timeout=2.0, **kwargs):
        super().__init__(**kwargs)
        self.connection = serial.Serial(
            port=com,
            baudrate=baud,
            timeout=timeout,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
        )
        # If the laser is currently on, then we need to use 7-byte mode; otherwise we need to
        # use 16-byte mode.
        self._write(b"S?")
        response = self._readline()
        _logger.info("Current laser state: [%s]", response.decode())

        self._write(b"STAT3")
        option_codes = self._readline()
        if not option_codes.startswith(b"OC "):
            raise microscope.DeviceError(
                "Failed to get option codes '%s'" % option_codes.decode()
            )
        if option_codes[9:12] == b"AP1":
            self._has_apc = True
        else:
            _logger.warning(
                "Laser is missing APC option.  Will return set"
                " power instead of actual power"
            )
            self._has_apc = False

    def _write(self, command):
        """Send a command."""
        # We'll need to pad the command out to 16 bytes. There's also
        # a 7-byte mode but we never need to use it.  CR/LF counts
        # towards the byte limit, hence 14 (16-2)
        command = command.ljust(14) + b"\r\n"
        response = self.connection.write(command)
        return response

    # Get the status of the laser, by sending the
    # STAT0, STAT1, STAT2, and STAT3 commands.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def get_status(self):
        result = []
        for i in range(4):
            self._write(("STAT%d" % i).encode())
            result.append(self._readline().decode())
        return result

    # Turn the laser ON. Return True if we succeeded, False otherwise.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_enable(self):
        _logger.info("Turning laser ON.")
        # Turn on deepstar mode with internal voltage ref
        # Enable internal peak power
        # Set MF turns off internal digital and bias modulation
        # Disable analog modulation to digital modulation
        for cmd, msg in [
            (b"LON", "Enable response: [%s]"),
            (b"L2", "L2 response: [%s]"),
            (b"IPO", "Enable-internal peak power response: [%s]"),
            (b"MF", "MF response [%s]"),
            (b"A2DF", "A2DF response [%s]"),
        ]:
            self._write(cmd)
            response = self._readline()
            _logger.debug(msg, response.decode())

        if not self.get_is_on():
            # Something went wrong.
            self._write(b"S?")
            response = self._readline()
            _logger.error(
                "Failed to turn on. Current status: [%s]", response.decode()
            )
            return False
        return True

    def _do_shutdown(self) -> None:
        self.disable()

    # Turn the laser OFF.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_disable(self):
        _logger.info("Turning laser OFF.")
        self._write(b"LF")
        return self._readline().decode()

    # Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def get_is_on(self):
        self._write(b"S?")
        response = self._readline()
        _logger.debug("Are we on? [%s]", response.decode())
        return response == b"S2"

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_set_power(self, power: float) -> None:
        _logger.debug("level=%d", power)
        power_int = int(power * 0xFFF)
        _logger.debug("power=%d", power_int)
        strPower = "PP%03X" % power_int
        _logger.debug("power level=%s", strPower)
        self._write(strPower.encode())
        response = self._readline()
        _logger.debug("Power response [%s]", response.decode())

    def _do_get_power(self) -> float:
        if not self.get_is_on():
            return 0.0
        if self._has_apc:
            query = b"P"
            scale = 0xCCC
        else:
            query = b"PP"
            scale = 0xFFF

        self._write(query + b"?")
        answer = self._readline()
        if not answer.startswith(query):
            raise microscope.DeviceError(
                "failed to read power from '%s'" % answer.decode()
            )

        level = int(answer[len(query) :], 16)
        return float(level) / float(scale)

    @property
    def trigger_type(self) -> microscope.TriggerType:
        return microscope.TriggerType.HIGH

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return microscope.TriggerMode.BULB

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if ttype is not microscope.TriggerType.HIGH:
            raise microscope.UnsupportedFeatureError(
                "the only trigger type supported is 'high'"
            )
        if tmode is not microscope.TriggerMode.BULB:
            raise microscope.UnsupportedFeatureError(
                "the only trigger mode supported is 'bulb'"
            )

    def _do_trigger(self) -> None:
        raise microscope.IncompatibleStateError(
            "trigger does not make sense in trigger mode bulb, only enable"
        )
