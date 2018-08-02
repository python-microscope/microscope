#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
# Copyright 2018 David Pinto <david.pinto@bioch.ox.ac.uk>
# Copyright 2018 Julio Mateos Langerak <julio.mateos-langerak@igh.cnrs.fr>
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
class ObisLaser(devices.SerialDeviceMixIn, devices.LaserDevice):
    def __init__(self, com, baud, timeout, *args, **kwargs):
        super(ObisLaser, self).__init__(*args, **kwargs)
        self.connection = serial.Serial(port=com,
                                        baudrate=baud,
                                        timeout=timeout,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE)
        # Start a logger.
        self._write(b'SYSTem:INFormation:MODel?')
        response = self._readline()
        self._logger.info('OBIS laser model: [%s]' % response.decode())
        self._write(b'SYSTem:INFormation:SNUMber?')
        response = self._readline()
        self._logger.info('OBIS laser serial number: [%s]' % response.decode())
        self._write(b'SYSTem:CDRH?')
        response = self._readline()
        self._logger.info('CDRH safety: [%s]' % response.decode())
        self._write(b'SOURce:TEMPerature:APRobe?')
        response = self._readline()
        self._logger.info('TEC temperature control: [%s]' % response.decode())
        self._write(b'*TST?')
        response = self._readline()
        self._logger.info('Self test procedure: [%s]' % response.decode())

        # We need to ensure that autostart is disabled so that we can switch emission
        # on/off remotely.
        self._write(b'SYSTem:AUTostart?')
        response = self._readline()
        self._logger.info('Response to Autostart: [%s]' % response.decode())

    def _write(self, command):
        """Send a command."""
        response = self.connection.write(command + b'\r\n')
        return response

    def _readline(self):
        """Read a line from connection without leading and trailing whitespace.
        We override from serialDeviceMixIn
        """
        response = self.connection.readline().strip()
        if self.connection.readline().strip() != b'OK':
            raise Exception('Did not get a proper answer from the laser serial comm.')
        return response

    def _flush_handshake(self):
        self.connection.readline()

    @devices.SerialDeviceMixIn.lock_comms
    def get_status(self):
        result = []
        for cmd, stat in [(b'SOURce:AM:STATe?', 'Emission on?'),
                          (b'SOURce:POWer:LEVel:IMMediate:AMPLitude?', 'Target power:'),
                          (b'SOURce:POWer:LEVel?', 'Measured power:'),
                          (b'SYSTem:STATus?', 'Status code?'),
                          (b'SYSTem:FAULt?', 'Fault code?'),
                          (b'SYSTem:HOURs?', 'Head operating hours:')]:
            self._write(cmd)
            result.append(stat + ' ' + self._readline().decode())
        return result

    @devices.SerialDeviceMixIn.lock_comms
    def enable(self):
        """Turn the laser ON. Return True if we succeeded, False otherwise."""
        self._logger.info('Turning laser ON.')
        # Exiting Sleep Mode.
        self._write(b'SOURce:TEMPerature:APRobe ON')
        self._flush_handshake()
        # Turn on emission.
        self._write(b'SOURce:AM:STATe ON')
        self._flush_handshake()
        self._write(b'SOURce:AM:STATe?')
        response = self._readline()
        self._logger.info("SOURce:AM:STATe? [%s]" % response.decode())

        if not self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn ON. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True

    def _on_shutdown(self):
        self.disable()
        # We set the power to a safe level
        self._set_power_mw(2)
        # We want it back into direct control mode.
        self._write(b'SOURce:AM:INTernal CWP')
        self._flush_handshake()

        # Going into Sleep mode
        self._write(b'SOURce:TEMPerature:APRobe OFF')
        self._flush_handshake()


    def initialize(self):
        """Initialization to do when cockpit connects."""
        # self.flush_buffer()
        # We ensure that handshaking is off.
        self._write(b'SYSTem:COMMunicate:HANDshaking ON')
        self._flush_handshake()
        # We don't want 'direct control' mode.
        # TODO: Change to MIXED when analogue output is available
        self._write(b'SOURce:AM:EXTernal DIGital')
        self._flush_handshake()

    @devices.SerialDeviceMixIn.lock_comms
    def disable(self):
        """Turn the laser OFF. Return True if we succeeded, False otherwise."""
        self._logger.info('Turning laser OFF.')
        # Turning LASER OFF
        self._write(b'SOURce:AM:STATe OFF')
        self._flush_handshake()

        if self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn OFF. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True

    @devices.SerialDeviceMixIn.lock_comms
    def isAlive(self):
        return self.get_is_on

    @devices.SerialDeviceMixIn.lock_comms
    def get_is_on(self):
        """Return True if the laser is currently able to produce light."""
        self._write(b'SOURce:AM:STATe?')
        response = self._readline()
        self._logger.info("Are we on? [%s]", response.decode())
        return response == b'ON'

    @devices.SerialDeviceMixIn.lock_comms
    def _set_power(self, power_w):
        """Sets the power level in Watts"""
        if power_w > (self.get_max_power_mw() / 1000):
            return
        self._logger.info("Setting laser power to %.7sW", power_w)
        self._write(b'SOURce:POWer:LEVel:IMMediate:AMPLitude %.5f' % power_w)
        self._flush_handshake()
        curr_power = self._get_power()
        self._logger.info("Power response [%s]", curr_power)
        return curr_power

    @devices.SerialDeviceMixIn.lock_comms
    def get_max_power_mw(self):
        """Gets the maximum laser power in mW."""
        self._write(b'SYSTem:INFormation:POWer?')
        power_w = self._readline()
        return int(float(power_w.decode()) * 1000)

    @devices.SerialDeviceMixIn.lock_comms
    def _get_power(self):
        if not self.get_is_on():
            # Laser is not on.
            return 0
        self._write(b'SOURce:POWer:LEVel?')
        response = self._readline()
        return float(response.decode())

    def get_power_mw(self):
        return 1000 * self._get_power()

    def _set_power_mw(self, mw):
        mw = min(mw, self.get_max_power_mw())
        return self._set_power(mw / 1000)
