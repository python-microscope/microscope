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
import abc
import devicebase

class LaserDevice(devicebase.Device):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        super(LaserDevice, self).__init__(*args, **kwargs)
        ## Should connect to the physical device here and set self.connection
        # to a type with read, readline and write methods (e.g. serial.Serial).
        self.connection = None
        self.powerSetPoint_mW = None
        # Wrap derived-classes setPower_mW to store power set point.
        # The __get__(self, Laser) binds the wrapped function to an instance.
        self.setPower_mW = _storeSetPoint(self.setPower_mW).__get__(self, Laser)


    ## Simple passthrough.
    @abc.abstractmethod
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    @abc.abstractmethod
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command.
    @abc.abstractmethod
    def write(self, command):
        # Override if a specific format is required.
        response = self.connection.write(command + '\r\n')
        return response

    
    ## Query and return the laser status.
    @abc.abstractmethod
    def getStatus(self):
        result = []
        # ...
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @abc.abstractmethod
    def enable(self):
        pass


    ## Turn the laser OFF.
    @abc.abstractmethod
    def disable(self):
        pass


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @abc.abstractmethod
    def getIsOn(self):
        pass


    ## Return the max. power in mW.
    @abc.abstractmethod
    def getMaxPower_mW(self):
        pass


    ## Return the current power in mW.
    @abc.abstractmethod
    def getPower_mW(self):
        pass


    ## Return the power set point.
    def getSetPower_mW(self):
        return self.powerSetPoint_mW


    ## Set the power from an argument in mW.
    @abc.abstractmethod
    def setPower_mW(self, mW):
        pass