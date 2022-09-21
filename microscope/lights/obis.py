#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Julio Mateos Langerak <julio.mateos-langerak@igh.cnrs.fr>
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


class ObisLaser(microscope.abc.SerialDeviceMixin, microscope.abc.LightSource):
    def __init__(self, com, baud=115200, timeout=0.5, **kwargs) -> None:
        super().__init__(**kwargs)
        self.connection = serial.Serial(
            port=com,
            baudrate=baud,
            timeout=timeout,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
        )
        # Start a logger.
        self._write(b"SYSTem:INFormation:MODel?")
        response = self._readline()
        _logger.info("OBIS laser model: [%s]", response.decode())
        self._write(b"SYSTem:INFormation:SNUMber?")
        response = self._readline()
        _logger.info("OBIS laser serial number: [%s]", response.decode())
        self._write(b"SYSTem:CDRH?")
        response = self._readline()
        _logger.info("CDRH safety: [%s]", response.decode())
        self._write(b"SOURce:TEMPerature:APRobe?")
        response = self._readline()
        _logger.info("TEC temperature control: [%s]", response.decode())
        self._write(b"*TST?")
        response = self._readline()
        _logger.info("Self test procedure: [%s]", response.decode())

        # We need to ensure that autostart is disabled so that we can
        # switch emission on/off remotely.
        self._write(b"SYSTem:AUTostart?")
        response = self._readline()
        _logger.info("Response to Autostart: [%s]", response.decode())

        self._write(b"SOURce:POWer:LIMit:HIGH?")
        response = self._readline()
        _logger.info("Max intensity in watts: [%s]", response.decode())
        self._max_power_mw = float(response) * 1000.0

        self.initialize()

    def _write(self, command):
        """Send a command."""
        response = self.connection.write(command + b"\r\n")
        return response

    def _readline(self):
        """Read a line from connection without leading and trailing whitespace.
        We override from SerialDeviceMixin
        """
        response = self.connection.readline().strip()
        if self.connection.readline().strip() != b"OK":
            raise microscope.DeviceError(
                "Did not get a proper answer from the laser serial comm."
            )
        return response

    def _flush_handshake(self):
        self.connection.readline()

    @microscope.abc.SerialDeviceMixin.lock_comms
    def get_status(self):
        result = []
        for cmd, stat in [
            (b"SOURce:AM:STATe?", "Emission on?"),
            (b"SOURce:POWer:LEVel:IMMediate:AMPLitude?", "Target power:"),
            (b"SOURce:POWer:LEVel?", "Measured power:"),
            (b"SYSTem:STATus?", "Status code?"),
            (b"SYSTem:FAULt?", "Fault code?"),
            (b"SYSTem:HOURs?", "Head operating hours:"),
        ]:
            self._write(cmd)
            result.append(stat + " " + self._readline().decode())
        return result

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_enable(self):
        """Turn the laser ON. Return True if we succeeded, False otherwise."""
        _logger.info("Turning laser ON.")
        # Exiting Sleep Mode.
        self._write(b"SOURce:TEMPerature:APRobe ON")
        self._flush_handshake()
        # Turn on emission.
        self._write(b"SOURce:AM:STATe ON")
        self._flush_handshake()
        self._write(b"SOURce:AM:STATe?")
        response = self._readline()
        _logger.debug("SOURce:AM:STATe? [%s]", response.decode())

        if not self.get_is_on():
            # Something went wrong.
            _logger.error("Failed to turn ON. Current status:\r\n")
            _logger.error(self.get_status())
            return False
        return True

    def _do_shutdown(self) -> None:
        self.disable()
        # We set the power to a safe level
        self._set_power_mw(2)
        # We want it back into direct control mode.
        self._write(b"SOURce:AM:INTernal CWP")
        self._flush_handshake()

        # Going into Sleep mode
        self._write(b"SOURce:TEMPerature:APRobe OFF")
        self._flush_handshake()

    def initialize(self):
        # self.flush_buffer()
        # We ensure that handshaking is off.
        self._write(b"SYSTem:COMMunicate:HANDshaking ON")
        self._flush_handshake()
        # We don't want 'direct control' mode.
        # TODO: Change to MIXED when analogue output is available
        self._write(b"SOURce:AM:EXTernal DIGital")
        self._flush_handshake()

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_disable(self):
        """Turn the laser OFF. Return True if we succeeded, False otherwise."""
        _logger.info("Turning laser OFF.")
        # Turning LASER OFF
        self._write(b"SOURce:AM:STATe OFF")
        self._flush_handshake()

        if self.get_is_on():
            _logger.error("Failed to turn OFF. Current status:\r\n")
            _logger.error(self.get_status())
            return False
        return True

    @microscope.abc.SerialDeviceMixin.lock_comms
    def get_is_on(self):
        """Return True if the laser is currently able to produce light."""
        self._write(b"SOURce:AM:STATe?")
        response = self._readline()
        _logger.debug("Are we on? [%s]", response.decode())
        return response == b"ON"

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _get_power_mw(self):
        if not self.get_is_on():
            return 0.0
        self._write(b"SOURce:POWer:LEVel?")
        response = self._readline()
        return float(response.decode()) * 1000.0

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _set_power_mw(self, mw):
        power_w = mw / 1000.0
        _logger.debug("Setting laser power to %.7sW", power_w)
        self._write(b"SOURce:POWer:LEVel:IMMediate:AMPLitude %.5f" % power_w)
        self._flush_handshake()

    def _do_set_power(self, power: float) -> None:
        self._set_power_mw(power * self._max_power_mw)

    def _do_get_power(self) -> float:
        return self._get_power_mw() / self._max_power_mw

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
