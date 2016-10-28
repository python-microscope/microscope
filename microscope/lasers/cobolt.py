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
import time
from microscope import devices
import functools


def lock_comms(func):
    """A decorator to flush the input buffer prior to issuing a command.

    Locks the comms channel so that a function must finish all its comms
    before another can run.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.comms_lock:
            return func(self, *args, **kwargs)

    return wrapper


class CoboltLaser(devices.LaserDevice):
    def __init__(self, com=None, baud=None, timeout=0.01, **kwargs):
        super(CoboltLaser, self).__init__()
        self.connection = serial.Serial(port = com,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # Start a logger.
        self._write('sn?')
        response = self._readline()
        self._logger.info("Cobolt laser serial number: [%s]" % response)
        # We need to ensure that autostart is disabled so that we can switch emission
        # on/off remotely.
        self._write('@cobas 0')
        self._logger.info("Response to @cobas 0 [%s]" % self._readline())
        self.comms_lock = threading.RLock()

    def send(self, command):
        """Send command and retrieve response."""
        self._write(str(command))
        return self._readline()

    @lock_comms
    def clearFault(self):
        self._write('cf')
        self._readline()
        return self.get_status()

    def flush_buffer(self):
        line = ' '
        while len(line) > 0:
            line = self._readline()

    @lock_comms
    def is_alive(self):
        self._write('l?')
        response = self._readline()
        return response in '01'

    @lock_comms
    def get_status(self):
        result = []
        for cmd, stat in [('l?', 'Emission on?'),
                            ('p?', 'Target power:'),
                            ('pa?', 'Measured power:'),
                            ('f?', 'Fault?'),
                            ('hrs?', 'Head operating hours:')]:
            self._write(cmd)
            result.append(stat + ' ' + self._readline())
        return result

    @lock_comms
    def _on_shutdown(self):
        # Disable laser.
        self.send('l0')
        self.send('@cob0')
        self.flush_buffer()


    ##  Initialization to do when cockpit connects.
    @lock_comms
    def initialize(self):
        self.flush_buffer()
        #We don't want 'direct control' mode.
        self.send('@cobasdr 0')
        # Force laser into autostart mode.
        self.send('@cob1')


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @lock_comms
    def enable(self):
        self._logger.info("Turning laser ON.")
        # Turn on emission.
        response = self.send('l1')
        self._logger.info("l1: [%s]" % response)

        if not self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn on. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True


    ## Turn the laser OFF.
    @lock_comms
    def disable(self):
        self._logger.info("Turning laser OFF.")
        self._write('l0')
        return self._readline()


    ## Return True if the laser is currently able to produce light.
    @lock_comms
    def get_is_on(self):
        self._write('l?')
        response = self._readline()
        return response == '1'


    @lock_comms
    def get_max_power_mw(self):
        # 'gmlp?' gets the maximum laser power in mW.
        self._write('gmlp?')
        response = self._readline()
        return float(response)


    @lock_comms
    def get_power_mw(self):
        if not self.get_is_on():
            return 0
        self._write('pa?')
        return 1000 * float(self._readline())


    @lock_comms
    def _set_power_mw(self, mW):
        mW = min(mW, self.get_max_power_mw)
        self._logger.info("Setting laser power to %.4fW."  % (mW / 1000.0, ))
        return self.send("@cobasp %.4f" % (mW / 1000.0))


    @lock_comms
    def get_set_power_mw(self):
        self._write('p?')
        return 1000 * float(self._readline())
