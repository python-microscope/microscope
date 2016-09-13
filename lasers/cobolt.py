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
import laser
import functools


def lockComms(func):
    """A decorator to flush the input buffer prior to issuing a command.

    Locks the comms channel so that a function must finish all its comms
    before another can run.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.commsLock:
            return func(self, *args, **kwargs)

    return wrapper


class CoboltLaser(laser.LaserRemote):
    def __init__(self, com=None, baud=None, timeout=0.01, **kwargs):
        super(CoboltLaser, self).__init__()
        self.connection = serial.Serial(port = com,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # Start a logger.
        self.write('sn?')
        response = self.readline()
        self.logger.info("Cobolt laser serial number: [%s]" % response)
        # We need to ensure that autostart is disabled so that we can switch emission
        # on/off remotely.
        self.write('@cobas 0')
        self.logger.info("Response to @cobas 0 [%s]" % self.readline())
        self.commsLock = threading.RLock()


    ## Simple passthrough.
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command. 
    def write(self, command):
        response = self.connection.write(command + '\r\n')
        return response


    ## Send command and retrieve response.
    def send(self, command):
        self.write(str(command))
        return self.readline()


    @lockComms
    def clearFault(self):
        self.write('cf')
        self.readline()
        return self.getStatus()


    def flushBuffer(self):
        line = ' '
        while len(line) > 0:
            line = self.readline()

    @lockComms
    def isAlive(self):
        self.write('l?')
        response = self.readline()
        return response in '01'


    @lockComms
    def getStatus(self):
        result = []
        for cmd, stat in [('l?', 'Emission on?'),
                            ('p?', 'Target power:'),
                            ('pa?', 'Measured power:'),
                            ('f?', 'Fault?'),
                            ('hrs?', 'Head operating hours:')]:
            self.write(cmd)
            result.append(stat + ' ' + self.readline())
        return result


    ## Things that should be done when cockpit exits.
    @lockComms
    def onExit(self):
        # Disable laser.
        self.send('l0')
        self.send('@cob0')
        self.flushBuffer()


    ##  Initialization to do when cockpit connects.
    @lockComms
    def onCockpitInitialize(self):
        self.flushBuffer()
        #We don't want 'direct control' mode.
        self.send('@cobasdr 0')
        # Force laser into autostart mode.
        self.send('@cob1')


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @lockComms
    def enable(self):
        self.logger.info("Turning laser ON at %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
        # Turn on emission.
        response = self.send('l1')
        self.logger.info("l1: [%s]" % response)

        if not self.getIsOn():
            # Something went wrong.
            self.logger.error("Failed to turn on. Current status:\r\n")
            self.logger.error(self.getStatus())
            return False
        return True


    ## Turn the laser OFF.
    @lockComms
    def disable(self):
        self.logger.info("Turning laser OFF at %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
        self.write('l0')
        return self.readline()


    ## Return True if the laser is currently able to produce light.
    @lockComms
    def getIsOn(self):
        self.write('l?')
        response = self.readline()
        return response == '1'


    @lockComms
    def getMaxPower_mW(self):
        # 'gmlp?' gets the maximum laser power in mW.
        self.write('gmlp?')
        response = self.readline()
        return float(response)


    @lockComms
    def getPower_mW(self):
        if not self.getIsOn():
            return 0
        self.write('pa?')
        return 1000 * float(self.readline())


    @lockComms
    def setPower_mW(self, mW):
        mW = min(mW, self.getMaxPower_mW)
        self.logger.info("Setting laser power to %.4fW at %s"  % (mW / 1000.0, time.strftime('%Y-%m-%d %H:%M:%S')))
        return self.send("@cobasp %.4f" % (mW / 1000.0))


    @lockComms
    def getSetPower_mW(self):
        self.write('p?')
        return 1000 * float(self.readline())
