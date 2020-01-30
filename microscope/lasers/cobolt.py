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

import logging

import serial

from microscope import devices


_logger = logging.getLogger(__name__)


class CoboltLaser(devices.SerialDeviceMixIn, devices.LaserDevice):
    def __init__(self, com=None, baud=115200, timeout=0.01, **kwargs):
        super().__init__(**kwargs)
        self.connection = serial.Serial(port = com,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # Start a logger.
        response = self.send(b'sn?')
        _logger.info("Cobolt laser serial number: [%s]", response.decode())
        # We need to ensure that autostart is disabled so that we can switch emission
        # on/off remotely.
        response = self.send(b'@cobas 0')
        _logger.info("Response to @cobas 0 [%s]", response.decode())

    def send(self, command):
        """Send command and retrieve response."""
        success = False
        while not success:
            self._write(command)
            response = self._readline()
            # Catch zero-length responses to queries and retry.
            if not command.endswith(b'?'):
                success = True
            elif len(response) > 0:
                success = True
        return response

    @devices.SerialDeviceMixIn.lock_comms
    def clearFault(self):
        self.send(b'cf')
        return self.get_status()

    @devices.SerialDeviceMixIn.lock_comms
    def is_alive(self):
        response = self.send(b'l?')
        return response in b'01'

    @devices.SerialDeviceMixIn.lock_comms
    def get_status(self):
        result = []
        for cmd, stat in [(b'l?', 'Emission on?'),
                          (b'p?', 'Target power:'),
                          (b'pa?', 'Measured power:'),
                          (b'f?', 'Fault?'),
                          (b'hrs?', 'Head operating hours:')]:
            response = self.send(cmd)
            result.append(stat + " " + response.decode())
        return result

    @devices.SerialDeviceMixIn.lock_comms
    def _on_shutdown(self):
        # Disable laser.
        self.disable()
        self.send(b'@cob0')
        self.connection.flushInput()


    ##  Initialization to do when cockpit connects.
    @devices.SerialDeviceMixIn.lock_comms
    def initialize(self):
        self.connection.flushInput()
        #We don't want 'direct control' mode.
        self.send(b'@cobasdr 0')
        # Force laser into autostart mode.
        self.send(b'@cob1')


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @devices.SerialDeviceMixIn.lock_comms
    def _on_enable(self):
        _logger.info("Turning laser ON.")
        # Turn on emission.
        response = self.send(b'l1')
        _logger.info("l1: [%s]", response.decode())

        if not self.get_is_on():
            # Something went wrong.
            _logger.error("Failed to turn on. Current status:\r\n")
            _logger.error(self.get_status())
            return False
        return True


    ## Turn the laser OFF.
    @devices.SerialDeviceMixIn.lock_comms
    def disable(self):
        _logger.info("Turning laser OFF.")
        return self.send(b'l0').decode()


    ## Return True if the laser is currently able to produce light.
    @devices.SerialDeviceMixIn.lock_comms
    def get_is_on(self):
        response = self.send(b'l?')
        return response == b'1'

    def get_min_power_mw(self):
        return 0.0

    @devices.SerialDeviceMixIn.lock_comms
    def get_max_power_mw(self):
        # 'gmlp?' gets the maximum laser power in mW.
        response = self.send(b'gmlp?')
        try:
            return float(response)
        except:
            _logger.info("Bad response to gmlp?\n    %s", response.decode())


    @devices.SerialDeviceMixIn.lock_comms
    def get_power_mw(self):
        if not self.get_is_on():
            return 0.0
        success = False
        # Sometimes the controller returns b'1' rather than the power.
        while not success:
            response = self.send(b'pa?')
            if response != b'1':
                success = True
        return 1000 * float(response)


    @devices.SerialDeviceMixIn.lock_comms
    def _set_power_mw(self, mW):
        ## There is no minimum power in cobolt lasers.  Any
        ## non-negative number is accepted.
        W_str = '%.4f' % (mW / 1000.0)
        _logger.info("Setting laser power to %s W.", W_str)
        return self.send(b'@cobasp ' + W_str.encode())


    @devices.SerialDeviceMixIn.lock_comms
    def get_set_power_mw(self):
        response = self.send(b'p?')
        return 1000 * float(response)
