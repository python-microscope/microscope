#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
# and 2017 Ian Dobbie (Ian.Dobbie@gmail.com)
# and 2018 Tiago Susano Pinto (tiagosusanopinto@gmail.com)
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


class SapphireLaser(devices.LaserDevice):
    def __init__(self, com=None, baud=19200, timeout=0.5, **kwargs):
        # laser controller must run at 19200 baud, 8+1 bits,
        # no parity or flow control
        # timeout is recomended to be over 0.5
        super(SapphireLaser, self).__init__()
        self.connection = serial.Serial(port = com,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # Turning off command prompt
        self.send('>=0')
        # Head ID value is a float point value,
        # but only the integer part is significant
        headID = int(float(self.send('?hid')))
        self._logger.info("Sapphire laser serial number: [%s]" % headID)

        self.comms_lock = threading.RLock()

    def _read(self, num_chars):
        """Simple passthrough to read numChars from connection."""
        return self.connection.read(num_chars).decode()

    def _readline(self):
        """Simple passthrough to read one line from connection."""
        return self.connection.readline().strip().decode()

    def _write(self, command):
        """Send a command to the device."""
        # Overrided with a specific format.
        commandEncoded = (command + '\r\n').encode()
        self.connection.write(commandEncoded)
        return self._readline()

    def send(self, command):
        """Send command and retrieve response."""
        self._write(command)
        return self._readline()

    @lock_comms
    def clearFault(self):
        self.flush_buffer()
        return self.get_status()

    def flush_buffer(self):
        line = ' '
        while len(line) > 0:
            line = self._readline()

    @lock_comms
    def is_alive(self):
        return self.send('?l') in '01'

    def parseLaserStatus(status):
        if status == '1':
            return 'Start up'
        elif status == '2':
            return 'Warmup'
        elif status == '3':
            return 'Standby'
        elif status == '4':
            return 'Laser on'
        elif status == '5':
            return 'Laser ready'
        elif status == '6':
            return 'Error'
        else:
            return 'Undefined'

    @lock_comms
    def get_status(self):
        result = []

        result.append('Laser status: ' +
            SapphireLaser.parseLaserStatus(self.send('?sta')))

        for cmd, stat in [('?l', 'Ligh Emission on?'),
                            ('?t', 'TEC Servo on?'),
                            ('?k', 'Key Switch on?'),
                            ('?sp', 'Target power:'),
                            ('?p', 'Measured power:'),
                            ('?hh', 'Head operating hours:')]:
            result.append(stat + ' ' + self.send(cmd))

        self._write('?fl')
        faults = self._readline()
        response = self._readline()
        while response:
            faults += ' ' + response
            response = self._readline()

        result.append(faults)
        return result

    @lock_comms
    def _on_shutdown(self):
        # Disable laser.
        self._write('l=0')
        self.flush_buffer()


    ##  Initialization to do when cockpit connects.
    @lock_comms
    def initialize(self):
        self.flush_buffer()


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @lock_comms
    def enable(self):
        self._logger.info("Turning laser ON.")
        # Turn on emission.
        response = self._write('l=1')
        self._logger.info("l=1: [%s]" % response)

        # Enabling laser might take more than 500ms (default timeout)
        prevTimeout = self.connection.timeout
        self.connection.timeout = max(1, prevTimeout)
        isON = self.get_is_on()
        self.connection.timeout = prevTimeout

        if not isON:
            # Something went wrong.
            self._logger.error("Failed to turn on. Current status:\r\n")
            self._logger.error(self.get_status())
        return isON


    ## Turn the laser OFF.
    @lock_comms
    def disable(self):
        self._logger.info("Turning laser OFF.")
        return self._write('l=0')


    ## Return True if the laser is currently able to produce light.
    @lock_comms
    def get_is_on(self):
        return self.send('?l') == '1'


    @lock_comms
    def get_max_power_mw(self):
        # '?maxlp' gets the maximum laser power in mW.
        return float(self.send('?maxlp'))

    @lock_comms
    def get_min_power_mw(self):
        # '?minlp' gets the minimum laser power in mW.
        return float(self.send('?minlp'))

    @lock_comms
    def get_power_mw(self):
        return float(self.send('?p'))


    @lock_comms
    def _set_power_mw(self, mW):
        mW = max(min(mW, self.get_max_power_mw()), self.get_min_power_mw())
        self._logger.info("Setting laser power to %.3fmW." % mW)
        # using send instead of _write, because
        # if laser is not on, warning is returned
        return self.send('p=%.3f' % mW)


    @lock_comms
    def get_set_power_mw(self):
        return float(self.send('?sp'))
