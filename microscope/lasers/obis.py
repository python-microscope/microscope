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
from microscope import devices


class ObisLaser(devices.SerialDeviceMixIn, devices.LaserDevice):
    def __init__(self, com, baud=115200, timeout=.5, **kwargs):
        super(ObisLaser, self).__init__(**kwargs)
        self.connection = serial.Serial(port=com,
                                        baudrate=baud,
                                        timeout=timeout,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE)
        # Ensure handshakes are on
        self._write(b'SYSTem:COMMunicate:HANDshaking ON')
        response = self._readline()
        self._logger.info('Enabling handshaking: [%s]' % response.decode())
        # Get general status
        self._write(b'SOURce:AM:STATe?')
        response = self._readline()
        self._logger.info('Current laser state: [%s]' % response.decode())
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
        self._write(b'SYSTem:AUTostart ON')
        response = self._readline()
        self._logger.info('Switching Autostart on. Response to Autostart: [%s]'
                          % response.decode())

        # Get LASER powers
        self._write(b'SYSTem:INFormation:POWer?')
        power_w = self._readline()
        self._max_power = float(power_w.decode()) * 1000
        self._write(b'SOURce:POWer:LIMit:LOW?')
        power_w = self._readline()
        self._min_power = float(power_w.decode()) * 1000

    # def _write(self, command):
    #     msg_length = self.connection.write(command + b'\r\n')
    #     response = self._readline()
    #     if response == b'OK':  # We receive an OK handshake
    #         response = self._readline()
    #     elif response
    #
    #     return response
    #
    def _readline(self):
        """Read a line from connection without leading and trailing whitespace.
        We override from serialDeviceMixIn
        """
        response = self.connection.readline().strip()
        if response == b'OK':  # The response is a simple handshake
            return response
        elif response[:3] == b'ERR':  #There was an error
            self._logger.error('There was a handshake error: [%s]', response)
            return response
        else:  # There is a real response and we want to deal with the handshake
            try:  # We try as handshake might be turned off
                handshake = self.connection.readline().strip()
            except:
                self._logger.error('Handshake seems to be inactive')
                return response
            if handshake[:3] == b'ERR':  # There was an error
                self._logger.error('There was a handshake error: [%s]', handshake)
            return response

    @devices.SerialDeviceMixIn.lock_comms
    def get_status(self):
        result = []
        for cmd, msg in [(b'SOURce:AM:STATe?', 'Emission on?'),
                         (b'SOURce:POWer:LEVel:IMMediate:AMPLitude?', 'Target power:'),
                         (b'SOURce:POWer:LEVel?', 'Measured power:'),
                         (b'SYSTem:STATus?', 'Status code?'),
                         (b'SYSTem:FAULt?', 'Fault code?'),
                         (b'SYSTem:HOURs?', 'Head operating hours:')]:
            self._write(cmd)
            result.append(msg + ' ' + self._readline().decode())
        return result

    @devices.SerialDeviceMixIn.lock_comms
    def _on_enable(self):
        """Turn the laser ON. Return True if we succeeded, False otherwise."""
        self._logger.info('Turning laser ON.')
        # Exiting Sleep Mode.
        for cmd, msg in [(b'SOURce:TEMPerature:APRobe ON', 'Temperature control response: [%s]'),
                         (b'SOURce:AM:STATe ON', 'Emission response: [%s]'),
                         (b'SOURce:AM:EXTernal DIGital', 'Enabling Digital modulation response: [%s]')
                         ]:
            self._write(cmd)
            response = self._readline()
            self._logger.info(msg, response.decode())

        if not self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn ON. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True

    def _on_shutdown(self):
        self.disable()
        # Going into Sleep mode
        self._write(b'SOURce:TEMPerature:APRobe OFF')
        response = self._readline()
        self._logger.info('Disabling temperature control response: [%s]', response.decode())

    def initialize(self):
        pass

    @devices.SerialDeviceMixIn.lock_comms
    def _on_disable(self):
        """Turn the laser OFF. Return True if we succeeded, False otherwise."""
        self._logger.info('Turning laser OFF.')
        # Turning LASER OFF
        self._write(b'SOURce:AM:STATe OFF')
        self._readline()

        if self.get_is_on():
            # Something went wrong.
            self._logger.error("Failed to turn OFF. Current status:\r\n")
            self._logger.error(self.get_status())
            return False
        return True

    @devices.SerialDeviceMixIn.lock_comms
    def is_alive(self):
        return self.get_is_on()

    @devices.SerialDeviceMixIn.lock_comms
    def get_is_on(self):
        self._write(b'SOURce:AM:STATe?')
        response = self._readline()
        self._logger.info("Are we on? [%s]", response.decode())
        return response == b'ON'

    def _set_power(self, level):
        if level > 1.0:
            return
        self._logger.info("level=%d", level)
        power_mw = level * self._max_power
        self._set_power_mw(power_mw)

    def get_min_power_mw(self):
        return self._min_power

    def get_max_power_mw(self):
        return self._max_power

    @devices.SerialDeviceMixIn.lock_comms
    def _get_power_mw(self, get_actual=True):
        if get_actual:
            self._write(b'SOURce:POWer:LEVel?')
            response = self._readline()
            return float(response.decode()) * 1000
        else:
            self._write(b'SOURce:POWer:LEVel:IMMediate:AMPLitude?')
            response = self._readline()
            return float(response.decode()) * 1000

    def get_set_power_mw(self):
        return self._get_power_mw(get_actual=False)

    def get_power_mw(self):
        if not self.get_is_on():
            return 0.0
        return self._get_power_mw()

    @devices.SerialDeviceMixIn.lock_comms
    def _set_power_mw(self, mW):
        if mW > self._max_power:
            return
        self._logger.info("power level in mW=%.5f", mW)
        power_w = mW / 1000.0
        self._write(b'SOURce:POWer:LEVel:IMMediate:AMPLitude %.5f' % power_w)
        response = self._readline()
        self._logger.info("Power response [%s]", response.decode())
        return response
