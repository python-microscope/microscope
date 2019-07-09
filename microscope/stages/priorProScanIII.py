#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2019 Ian Dobbie (Ian.Dobbie@gmail.com)
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


#still to implement
#get position per axis
#getmovement time
#set speed and accelleration
#cleanupupafterexperiment function?



import serial
import Pyro4
import time

from microscope import devices


@Pyro4.expose
class PriorProScanIII( devices.SerialDeviceMixIn, devices.StageDevice):

    def __init__(self, hardlimits, com=None, baud=9600, timeout=0.1, *args, **kwargs):
        # default baufd rate is 9600
        # no parity or flow control
        # timeout is recomended to be over 0.5
        super(PriorProScanIII, self).__init__(*args, **kwargs)
        self.hardlimits=hardlimits
        self.connection = serial.Serial(port = com,
            baudrate = baud, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        #check axis encoder states.
        self.encoderState=self._encoder_state()
        #turn on encoders if needed and set servo mode off
        for axis in self.encoderState:
            if not self.encoderState[axis]:
                self.send(b'ENCODER,'+axis.encode()+b',1')

        #turn off servo mode by default
        self.send(b'SERVO,b,0')
        # setup individual movement axis commands
        self.move_axis_abs=[self._move_X_abs, self._move_Y_abs ]
        self.move_axis_rel=[self._move_X_rel, self._move_Y_rel ]

    def _write(self, command):
        """Send a command to the prior device.

        This is not a simple passthrough to ``serial.Serial.write``,
        it will append ``b'\\r'`` to command.  This overides the
        defualt write method
        """
        return self.connection.write(command + b'\r')

    def send(self, command):
        """Send command and retrieve response."""
        self._write(command)
        return self._readline()

#    @devices.SerialDeviceMixIn.lock_comms
#    def clearFault(self):
#        self.flush_buffer()
#        return self.get_status()

    def _flush_buffer(self):
        line = b' '
        while len(line) > 0:
            line = self._readline()

    @devices.SerialDeviceMixIn.lock_comms
    def get_status(self):
        result = self.send(b'?')
        return result.split(b'\r')

    @devices.SerialDeviceMixIn.lock_comms
    def get_position(self):
        result = self.send(b'P').split(b',')
        return ([int(result[0]),int(result[1])])

    @devices.SerialDeviceMixIn.lock_comms
    def stop(self):
        self.send(b'I')

    def move_abs(self,axis,pos):
        self.move_axis_abs[axis](pos)

    @devices.SerialDeviceMixIn.lock_comms
    def _move_X_abs(self,pos):
        position="%f"%(pos)
        self.send(b'GX,'+position.encode())
        #move returns a responce
        self._readline()

    @devices.SerialDeviceMixIn.lock_comms
    def _move_Y_abs(self,pos):
        position="%f"%(pos)
        self.send(b'GY,'+position.encode())
        #move returns a responce
        self._readline()

    def move_relative(self,axis,pos):
        self.move_axis_rel[axis](pos)

    @devices.SerialDeviceMixIn.lock_comms
    def _move_X_rel(self,pos):
        position="%f"%(pos)
        self.send(b'GR,'+position.encode()+b',0.0')
        #move returns a responce
        self._readline()

    @devices.SerialDeviceMixIn.lock_comms
    def _move_Y_rel(self,pos):
        position="%f"%(pos)
        self.send(b'GR,0.0,'+position.encode())
        #move returns a responce
        self._readline()

    @devices.SerialDeviceMixIn.lock_comms
    def get_is_moving(self):
        responce=self.send(b'$')
        responce=responce.split(b'\r')[0]
        if responce == b'0':
            return False
        else:
            return True

    @devices.SerialDeviceMixIn.lock_comms
    def get_serialnumber(self):
        return(self.send(b'SERIAL').strip(b'\r'))

    @devices.SerialDeviceMixIn.lock_comms
    def home(self):
        self.send(b'RIS')

    @devices.SerialDeviceMixIn.lock_comms
    def _encoder_state(self):
        encoderState=int(self.send(b'ENCODER'))
        responce= {'X':  True if (encoderState & 1) else False ,
                   'Y': True if (encoderState & 2) else False }
        return (responce)

    def get_hard_limits(self):
        return(self.hardlimits)
