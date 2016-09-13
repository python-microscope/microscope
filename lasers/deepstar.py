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
import functools
import laser

CONFIG_NAME = 'deepstar'
CLASS_NAME = 'DeepstarLaser'

def flushBuffer(func):
    """A decorator to flush the input buffer prior to issuing a command.

    There have been problems with the DeepStar lasers returning junk characters
    after the expected response, so it is advisable to flush the input buffer
    prior to running a command and subsequent readline. It also locks the comms
    channel so that a function must finish all its comms before another can run.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.commsLock:
            self.connection.flushInput()
            return func(self, *args, **kwargs)

    return wrapper


class DeepstarLaser(laser.LaserRemote):
    def __init__(self, serialPort, baudRate, timeout):
        super(DeepstarLaser, self).__init__()
        self.connection = serial.Serial(port = serialPort,
            baudrate = baudRate, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # If the laser is currently on, then we need to use 7-byte mode; otherwise we need to
        # use 16-byte mode.
        self.write('S?')
        response = self.readline()
        self.logger.info("Current laser state: [%s]" % response)
        self.commsLock = threading.RLock()
        

    ## Simple passthrough.
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command.
    def write(self, command):
        # We'll need to pad the command out to 16 bytes. There's also a 7-byte mode but
        # we never need to use it.
        commandLength = 16
        # CR/LF count towards the byte limit, hence the -2.
        command = command + (' ' * (commandLength - 2 - len(command)))
        response = self.connection.write(command + '\r\n')
        return response


    ## Get the status of the laser, by sending the
    # STAT0, STAT1, STAT2, and STAT3 commands.
    @flushBuffer
    def getStatus(self):
        result = []
        for i in xrange(4):
            self.write('STAT%d' % i)
            result.append(self.readline())
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @flushBuffer
    def enable(self):
        self.logger.info("Turning laser ON.")
        self.write('LON')
        response = self.readline()
        #Turn on deepstar mode with internal voltage ref
        self.logger.info("Enable response: [%s]" % response)
        self.write('L2')
        response = self.readline()
        self.logger.info("L2 response: [%s]" % response)
        #Enable internal peak power
        self.write('IPO')
        response = self.readline()
        self.logger.info("Enable-internal peak power response: [%s]" % response)
        #Set MF turns off internal digital and bias modulation
        self.write('MF')
        response = self.readline()
        self.logger.info("MF response [%s]" % response)

        if not self.getIsOn():
            # Something went wrong.
            self.write('S?')
            response = self.readline()
            self.logger.error("Failed to turn on. Current status: %s" % response)
            return False
        return True


    ## Turn the laser OFF.
    @flushBuffer
    def disable(self):
        self.logger.info("Turning laser OFF.")
        self.write('LF')
        return self.readline()


    @flushBuffer
    def isAlive(self):
        self.write('S?')
        response = self.readline()
        return response.startswith('S')


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @flushBuffer
    def getIsOn(self):
        self.write('S?')
        response = self.readline()
        self.logger.info("Are we on? [%s]" % response)
        return response == 'S2'


    @flushBuffer
    def setPower(self, level):
        if (level > 1.0) :
            return
        self.logger.info("level=%d" % level)
        power=int (level*0xFFF)
        self.logger.info("power=%d" % power)
        strPower = "PP%03X" % power
        self.logger.info("power level=%s" %strPower)
        self.write(strPower)
        response = self.readline()
        self.logger.info("Power response [%s]" % response)
        return response


    @flushBuffer
    def getMaxPower_mW(self):
        # Max power in mW is third token of STAT0.
        self.write('STAT0')
        response = self.readline()
        return int(response.split()[2])


    @flushBuffer
    def getPower(self):
        if not self.getIsOn():
            # Laser is not on.
            return 0
        self.write('PP?')
        response = self.readline()
        return int('0x' + response.strip('PP'), 16)


    def getPower_mW(self):
        maxPower = self.getMaxPower_mW()
        power = self.getPower()
        return maxPower * float(power) / float(0xFFF)


    def setPower_mW(self, mW):
        maxPower = self.getMaxPower_mW()
        level = float(mW) / maxPower
        self.setPower(level)