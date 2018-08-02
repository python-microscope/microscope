#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
# Copyright 2018 David Pinto <david.pinto@bioch.ox.ac.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import serial

import Pyro4

from microscope import devices


@Pyro4.expose
class DeepstarLaser(devices.SerialDeviceMixIn, devices.LaserDevice):
    def __init__(self, com, baud, timeout, *args, **kwargs):
        super(DeepstarLaser, self).__init__(*args, **kwargs)
        self.connection = serial.Serial(port = com,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # If the laser is currently on, then we need to use 7-byte mode; otherwise we need to
        # use 16-byte mode.
        self._write(b'S?')
        response = self._readline()
        self._logger.info("Current laser state: [%s]", response.decode())

    def _write(self, command):
        """Send a command."""
        # We'll need to pad the command out to 16 bytes. There's also
        # a 7-byte mode but we never need to use it.  CR/LF counts
        # towards the byte limit, hence 14 (16-2)
        command = command.ljust(14) + b'\r\n'
        response = self.connection.write(command)
        return response


    ## Get the status of the laser, by sending the
    # STAT0, STAT1, STAT2, and STAT3 commands.
    @devices.SerialDeviceMixIn.lock_comms
    def get_status(self):
        result = []
        for i in range(4):
            self._write(('STAT%d' % i).encode())
            result.append(self._readline().decode())
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @devices.SerialDeviceMixIn.lock_comms
    def enable(self):
        self._logger.info("Turning laser ON.")
        # Turn on deepstar mode with internal voltage ref
        # Enable internal peak power
        # Set MF turns off internal digital and bias modulation
        for cmd, msg in [(b'LON', 'Enable response: [%s]'),
                         (b'L2', 'L2 response: [%s]'),
                         (b'IPO', 'Enable-internal peak power response: [%s]'),
                         (b'MF', 'MF response [%s]')]:
            self._write(cmd)
            response = self._readline()
            self._logger.info(msg, response.decode())

        if not self.get_is_on():
            # Something went wrong.
            self._write(b'S?')
            response = self._readline()
            self._logger.error("Failed to turn on. Current status: [%s]",
                               response.decode())
            return False
        return True

    def _on_shutdown(self):
        self.disable()

    def initialize(self):
        pass

    ## Turn the laser OFF.
    @devices.SerialDeviceMixIn.lock_comms
    def disable(self):
        self._logger.info("Turning laser OFF.")
        self._write(b'LF')
        return self._readline().decode()


    @devices.SerialDeviceMixIn.lock_comms
    def isAlive(self):
        self._write(b'S?')
        response = self._readline()
        return response.startswith(b'S')


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @devices.SerialDeviceMixIn.lock_comms
    def get_is_on(self):
        self._write(b'S?')
        response = self._readline()
        self._logger.info("Are we on? [%s]", response.decode())
        return response == b'S2'


    @devices.SerialDeviceMixIn.lock_comms
    def _set_power(self, level):
        if (level > 1.0) :
            return
        self._logger.info("level=%d", level)
        power=int (level*0xFFF)
        self._logger.info("power=%d", power)
        strPower = "PP%03X" % power
        self._logger.info("power level=%s", strPower)
        self._write(six.b(strPower))
        response = self._readline()
        self._logger.info("Power response [%s]", response.decode())
        return response


    @devices.SerialDeviceMixIn.lock_comms
    def get_max_power_mw(self):
        # Max power in mW is third token of STAT0.
        self._write(b'STAT0')
        response = self._readline()
        return int(response.split()[2])


    @devices.SerialDeviceMixIn.lock_comms
    def _get_power(self):
        if not self.get_is_on():
            # Laser is not on.
            return 0
        self._write(b'PP?')
        response = self._readline()
        return int(b'0x' + response.strip(b'P'), 16)


    def get_power_mw(self):
        maxPower = self.get_max_power_mw()
        power = self._get_power()
        return maxPower * float(power) / float(0xFFF)


    def _set_power_mw(self, mW):
        maxPower = self.get_max_power_mw()
        level = float(mW) / maxPower
        self._set_power(level)
