#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
## Copyright (C) 2020 Tiago Susano Pinto <tiagosusanopinto@gmail.com>
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

import microscope._utils
import microscope.abc


_logger = logging.getLogger(__name__)


class SapphireLaser(
    microscope._utils.OnlyTriggersBulbOnSoftwareMixin,
    microscope.abc.SerialDeviceMixin,
    microscope.abc.LightSource,
):
    """Coherent Sapphire laser.

    The Sapphire is a diode-pumped solid-state laser and only supports
    `TriggerMode.SOFTWARE`.

    """

    laser_status = {
        b"1": "Start up",
        b"2": "Warmup",
        b"3": "Standby",
        b"4": "Laser on",
        b"5": "Laser ready",
        b"6": "Error",
    }

    def __init__(self, com=None, baud=19200, timeout=0.5, **kwargs):
        # laser controller must run at 19200 baud, 8+1 bits,
        # no parity or flow control
        # timeout is recomended to be over 0.5
        super().__init__(**kwargs)
        self.connection = serial.Serial(
            port=com,
            baudrate=baud,
            timeout=timeout,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
        )
        # Turning off command prompt
        self.send(b">=0")

        # The sapphire laser turns on as soon as the key is switched
        # on.  So turn radiation off before we start.
        self.send(b"L=0")

        # Head ID value is a float point value,
        # but only the integer part is significant
        headID = int(float(self.send(b"?hid")))
        _logger.info("Sapphire laser serial number: [%s]", headID)

        self._max_power_mw = float(self.send(b"?maxlp"))
        self._min_power = float(self.send(b"?minlp")) / self._max_power_mw

        self.initialize()

    def _write(self, command):
        count = super()._write(command)
        # This device always writes backs something.  If echo is on,
        # it's the whole command, otherwise just an empty line.  Read
        # it and throw it away.
        self._readline()
        return count

    def send(self, command):
        """Send command and retrieve response."""
        self._write(command)
        return self._readline()

    @microscope.abc.SerialDeviceMixin.lock_comms
    def clearFault(self):
        self.flush_buffer()
        return self.get_status()

    def flush_buffer(self):
        line = b" "
        while len(line) > 0:
            line = self._readline()

    @microscope.abc.SerialDeviceMixin.lock_comms
    def get_status(self):
        result = []

        status_code = self.send(b"?sta")
        result.append(
            (
                "Laser status: "
                + self.laser_status.get(status_code, "Undefined")
            )
        )

        for cmd, stat in [
            (b"?l", "Ligh Emission on?"),
            (b"?t", "TEC Servo on?"),
            (b"?k", "Key Switch on?"),
            (b"?sp", "Target power:"),
            (b"?p", "Measured power:"),
            (b"?hh", "Head operating hours:"),
        ]:
            result.append(stat + " " + self.send(cmd).decode())

        self._write(b"?fl")
        faults = self._readline()
        response = self._readline()
        while response:
            faults += b" " + response
            response = self._readline()

        result.append(faults.decode())
        return result

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_shutdown(self) -> None:
        # Disable laser.
        self._write(b"l=0")
        self.flush_buffer()

    #  Initialization to do when cockpit connects.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def initialize(self):
        self.flush_buffer()

    # Turn the laser ON. Return True if we succeeded, False otherwise.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def _do_enable(self):
        _logger.info("Turning laser ON.")
        # Turn on emission.
        response = self.send(b"l=1")
        _logger.info("l=1: [%s]", response.decode())

        # Enabling laser might take more than 500ms (default timeout)
        prevTimeout = self.connection.timeout
        self.connection.timeout = max(1, prevTimeout)
        isON = self.get_is_on()
        self.connection.timeout = prevTimeout

        if not isON:
            # Something went wrong.
            _logger.error("Failed to turn on. Current status:\r\n")
            _logger.error(self.get_status())
        return isON

    # Turn the laser OFF.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def disable(self):
        _logger.info("Turning laser OFF.")
        return self._write(b"l=0")

    # Return True if the laser is currently able to produce light.
    @microscope.abc.SerialDeviceMixin.lock_comms
    def get_is_on(self):
        return self.send(b"?l") == b"1"

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _get_power_mw(self):
        return float(self.send(b"?p"))

    @microscope.abc.SerialDeviceMixin.lock_comms
    def _set_power_mw(self, mW):
        mW_str = "%.3f" % mW
        _logger.info("Setting laser power to %s mW.", mW_str)
        # using send instead of _write, because
        # if laser is not on, warning is returned
        return self.send(b"p=%s" % mW_str.encode())

    def _do_set_power(self, power: float) -> None:
        # power is already clipped to the [0 1] range but we need to
        # clip it again since the min power we actually can do is 0.2
        # and we get an error from the laser if we set it to lower.
        power = max(self._min_power, power)
        self._set_power_mw(power * self._max_power_mw)

    def _do_get_power(self) -> float:
        return self._get_power_mw() / self._max_power_mw
