#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
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
import threading
import functools

from microscope import devices

def _flush_buffer(func):
    """A decorator to flush the input buffer prior to issuing a command.

    There have been problems with the DeepStar lasers returning junk characters
    after the expected response, so it is advisable to flush the input buffer
    prior to running a command and subsequent readline. It also locks the comms
    channel so that a function must finish all its comms before another can run.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.comms_lock:
            self.connection.flushInput()
            return func(self, *args, **kwargs)

    return wrapper


class DeepstarLaser(devices.LaserDevice):
    def __init__(self, port, baud, timeout, **kwargs):
        super(DeepstarLaser, self).__init__()
        self.connection = serial.Serial(port = port,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # If the laser is currently on, then we need to use 7-byte mode; otherwise we need to
        # use 16-byte mode.
        self._write('S?')
        response = self._readline()
        self._logger.info("Current laser state: [%s]" % response)
        self.comms_lock = threading.RLock()
        

    def _write(self, command):
        """Send a command."""
        # We'll need to pad the command out to 16 bytes. There's also a 7-byte mode but
        # we never need to use it.
        commandLength = 16
        # CR/LF count towards the byte limit, hence the -2.
        command = command + (' ' * (commandLength - 2 - len(command)))
        response = self.connection.write(command + '\r\n')
        return response


    ## Get the status of the laser, by sending the
    # STAT0, STAT1, STAT2, and STAT3 commands.
    @_flush_buffer
    def get_status(self):
        result = []
        for i in xrange(4):
            self._write('STAT%d' % i)
            result.append(self._readline())
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @_flush_buffer
    def enable(self):
        self._logger.info("Turning laser ON.")
        self._write('LON')
        response = self._readline()
        #Turn on deepstar mode with internal voltage ref
        self._logger.info("Enable response: [%s]" % response)
        self._write('L2')
        response = self._readline()
        self._logger.info("L2 response: [%s]" % response)
        #Enable internal peak power
        self._write('IPO')
        response = self._readline()
        self._logger.info("Enable-internal peak power response: [%s]" % response)
        #Set MF turns off internal digital and bias modulation
        self._write('MF')
        response = self._readline()
        self._logger.info("MF response [%s]" % response)

        if not self.get_is_on():
            # Something went wrong.
            self._write('S?')
            response = self._readline()
            self._logger.error("Failed to turn on. Current status: %s" % response)
            return False
        return True

    def _on_shutdown(self):
        self.disable()

    def initialize(self):
        pass

    ## Turn the laser OFF.
    @_flush_buffer
    def disable(self):
        self._logger.info("Turning laser OFF.")
        self._write('LF')
        return self._readline()


    @_flush_buffer
    def isAlive(self):
        self._write('S?')
        response = self._readline()
        return response.startswith('S')


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @_flush_buffer
    def get_is_on(self):
        self._write('S?')
        response = self._readline()
        self._logger.info("Are we on? [%s]" % response)
        return response == 'S2'


    @_flush_buffer
    def _set_power(self, level):
        if (level > 1.0) :
            return
        self._logger.info("level=%d" % level)
        power=int (level*0xFFF)
        self._logger.info("power=%d" % power)
        strPower = "PP%03X" % power
        self._logger.info("power level=%s" %strPower)
        self._write(strPower)
        response = self._readline()
        self._logger.info("Power response [%s]" % response)
        return response


    @_flush_buffer
    def get_max_power_mw(self):
        # Max power in mW is third token of STAT0.
        self._write('STAT0')
        response = self._readline()
        return int(response.split()[2])


    @_flush_buffer
    def _get_power(self):
        if not self.get_is_on():
            # Laser is not on.
            return 0
        self._write('PP?')
        response = self._readline()
        return int('0x' + response.strip('PP'), 16)


    def get_power_mw(self):
        maxPower = self.get_max_power_mw()
        power = self._get_power()
        return maxPower * float(power) / float(0xFFF)


    def _set_power_mw(self, mW):
        maxPower = self.get_max_power_mw()
        level = float(mW) / maxPower
        self._set_power(level)