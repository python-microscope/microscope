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

class DeepstarLaser(devices.SerialDeviceMixIn, devices.LaserDevice):
    def __init__(self, com, baud=9600, timeout=2.0, *args, **kwargs):
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

        self._write(b'STAT0')
        model_code = self._readline()
        if not model_code.startswith(b'MC '):
            raise RuntimeError("Failed to get model code '%s'"
                               % model_code.decode())
        self._max_power = float(model_code[8:11])

        self._write(b'STAT3')
        option_codes = self._readline()
        if not option_codes.startswith(b'OC '):
            raise RuntimeError("Failed to get option codes '%s'"
                               % option_codes.decode())
        if option_codes[9:12] == b'AP1':
            self._has_apc = True
        else:
            self._logger.info('Laser is missing APC option.  Will return set'
                              ' power instead of actual power')
            self._has_apc = False

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
    def _on_enable(self):
        self._logger.info("Turning laser ON.")
        # Turn on deepstar mode with internal voltage ref
        # Enable internal peak power
        # Set MF turns off internal digital and bias modulation
        # Disable analog modulation to digital modulation
        for cmd, msg in [(b'LON', 'Enable response: [%s]'),
                         (b'L2', 'L2 response: [%s]'),
                         (b'IPO', 'Enable-internal peak power response: [%s]'),
                         (b'MF', 'MF response [%s]'),
                         (b'A2DF', 'A2DF response [%s]')]:
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
    def _on_disable(self):
        self._logger.info("Turning laser OFF.")
        self._write(b'LF')
        return self._readline().decode()


    @devices.SerialDeviceMixIn.lock_comms
    def is_alive(self):
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
        self._write(strPower.encode())
        response = self._readline()
        self._logger.info("Power response [%s]", response.decode())
        return response

    def get_min_power_mw(self):
        return 0.0

    def get_max_power_mw(self):
        return self._max_power

    @devices.SerialDeviceMixIn.lock_comms
    def _get_power_mw(self, get_actual=True):
        ## The code to get the current laser or the peak laser power
        ## is very similar so this function handles both cases.
        ##
        ## Args:
        ##     get_actual (bool): whether it should return the set
        ##         power (peak power), or the current laser power.
        if get_actual:
            query = b'P'
            scale = 0xCCC
        else:
            query = b'PP'
            scale = 0xFFF

        self._write(query + b'?')
        answer = self._readline()
        if not answer.startswith(query):
            raise RuntimeError('failed to read power ""' % answer.decode())

        level = int(answer[len(query):], 16)
        return (float(level) / float(scale)) * self._max_power

    def get_set_power_mw(self):
        return self._get_power_mw(get_actual=False)

    def get_power_mw(self):
        """Current laser power.

        Omicron LDM lasers can be bought with and without the LDM.APC
        power monitoring option (light pick-off).  If this option is
        not available, it returns the set power instead.
        """
        if not self.get_is_on():
            return 0.0
        return self._get_power_mw(get_actual=self._has_apc)

    def _set_power_mw(self, mW):
        level = float(mW) / self._max_power
        self._set_power(level)
