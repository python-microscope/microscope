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
# import time
from microscope.devices import LaserDevice
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


class ObisLaser(LaserDevice):
    """A class to control OBIS lasers from Coherent"""
    def __init__(self, com=None, baud=None, timeout=0.01, **kwargs):
        super(ObisLaser, self).__init__()
        self.connection = serial.Serial(port=com,
                                        baudrate=baud,
                                        timeout=timeout,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE)
        # Start a logger.
        response = self.send('SYSTem:INFormation:MODel?')
        self._logger.info('OBIS laser model: [%s]' % response)
        response = self.send('SYSTem:INFormation:SNUMber?')
        self._logger.info('OBIS laser serial number: [%s]' % response)
        response = self.send('SYSTem:INFormation:SNUMber?')
        self._logger.info('OBIS laser serial number: [%s]' % response)
        response = self.send('SYSTem:CDRH?')
        self._logger.info('CDRH safety: [%s]' % response)
        response = self.send('SOURce:TEMPerature:APRobe?')
        self._logger.info('TEC temperature control: [%s]' % response)
        response = self.send('*TST?')
        self._logger.info('Self test procedure: [%s]' % response)

        # We need to ensure that autostart is disabled so that we can switch emission
        # on/off remotely.
        response = self.send('SYSTem:AUTostart?')
        self._logger.info('Response to Autostart: [%s]' % response)
        self.comms_lock = threading.RLock()

    def send(self, command):
        """Send command and retrieve response."""
        self._write(str(command))
        return self._readline()

    @lock_comms
    def clear_fault(self):
        self.send('SYSTem:ERRor:CLEar')
        return self.get_status()

    def flush_buffer(self):
        line = ' '
        while len(line) > 0:
            line = self._readline()

    @lock_comms
    def is_alive(self):
        response1 = self.send('SOURce:AM:STATe?')
        response2 = self.send('SOURce:TEMPerature:APRobe?')
        return response1 and response2 == 'ON'

    @lock_comms
    def get_status(self):
        result = []
        for cmd, stat in [('SOURce:AM:STATe?', 'Emission on?'),
                          ('SOURce:POWer:LEVel:IMMediate:AMPLitude?', 'Target power:'),
                          ('SOURce:POWer:LEVel?', 'Measured power:'),
                          ('SYSTem:STATus?', 'Status code?'),
                          ('SYSTem:FAULt?', 'Fault code?'),
                          ('SYSTem:HOURs?', 'Head operating hours:')]:
            result.append(stat + ' ' + self.send(cmd))
        return result

    @lock_comms
    def _on_shutdown(self):
        # Disable laser.
        self.disable()

    @lock_comms
    def initialize(self):
        """Initialization to do when cockpit connects."""
        self.flush_buffer()
        # We don't want 'direct control' mode.
        self.send('SOURce:AM:EXTernal DIGital')  # Change to MIXED when analogue output is available

    @lock_comms
    def enable(self):
        """Turn the laser ON. Return True if we succeeded, False otherwise."""
        self._logger.info('Turning laser ON.')
        # Exiting Sleep Mode.
        self.send('SOURce:TEMPerature:APRobe ON')
        # Turn on emission.
        self.send('SOURce:AM:STATe ON')
        response = self.send('SOURce:AM:STATe?')
        self._logger.info("SOURce:AM:STATe? [%s]" % response)

        if not self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn ON. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True

    @lock_comms
    def disable(self):
        """Turn the laser OFF. Return True if we succeeded, False otherwise."""
        self._logger.info('Turning laser OFF.')
        # Turning LASER OFF
        self.send('SOURce:AM:STATe OFF')
        # Going into Sleep mode
        self.send('SOURce:TEMPerature:APRobe OFF')

        if self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn OFF. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True

    @lock_comms
    def get_is_on(self):
        """Return True if the laser is currently able to produce light."""
        response = self.send('SOURce:AM:STATe?')
        return response == 'ON'

    @lock_comms
    def get_max_power_mw(self):
        """Gets the maximum laser power in mW."""
        power_w = self.send('SYSTem:INFormation:POWer?')
        return float(power_w / 1000)

    @lock_comms
    def get_power_mw(self):
        """Gets current power level in mW"""
        if not self.get_is_on():
            return 0.0
        power_w = self.send('SOURce:POWer:LEVel?')
        return 1000 * float(power_w)

    @lock_comms
    def _set_power_mw(self, mW):
        mW = min(mW, self.get_max_power_mw)
        self._logger.info("Setting laser power to %.4fW." % (mW * 1000.0))
        self.send("SOURce:POWer:LEVel:IMMediate:AMPLitude %.4f" % mW * 1000.0)

    @lock_comms
    def get_set_power_mw(self):
        power_w = self.send('SOURce:POWer:LEVel:IMMediate:AMPLitude?')
        return 1000 * float(power_w)
