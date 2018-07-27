#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2018 David Pinto <david.pinto@bioch.ox.ac.uk>
##
## This file is part of Microscope.
##
## Microscope is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Microscope is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""Mock devices to be used in test cases.

These classes mock the different hardware as much as needed for our
testing needs.  Their behaviour is based first on the specifications
we have, and second on what we actually experience.  Our experience is
that most hardware does not actually follow the specs.

To fake a specific device type for interactive usage, use the dummy
device classes instead.  There's a concrete class for each device
interface.
"""

import functools
import io

import serial.serialutil


class SerialMock(serial.serialutil.SerialBase):
    """Base class to mock devices controlled via serial.

    It has two :class:`io.BytesIO` buffers.  One `write()`s into the
    the output buffer and `read()`s from the input buffer.  After a
    write, the output buffer is analysed for a command.  If there is a
    command, stuff gets done.  This usually means adding to the input
    buffer and changing state of the device.
    """
    def __init__(self, *args, **kwargs):
        super(SerialMock, self).__init__(*args, **kwargs)
        self.in_buffer = io.BytesIO()
        self.out_buffer = io.BytesIO()

        ## Number of bytes in out buffer pending 'interpretation'.  A
        ## command is only interpreted and handled when EOL is seen.
        self.out_pending_bytes = 0
        self.out_parsed_bytes = 0

        ## Number of bytes in the input buffer that have been read
        self.in_read_bytes = 0

    def open(self):
        pass

    def close(self):
        self.in_buffer.close()
        self.out_buffer.close()

    def handle(self, command):
        raise NotImplementedError('sub classes need to implement handle()')

    def write(self, data):
        self.out_buffer.write(data)
        self.out_pending_bytes += len(data)

        if self.out_pending_bytes > len(data):
            ## we need to retrieve data from a previous write
            self.out_buffer.seek(-self.out_pending_bytes, 2)
            data = self.out_buffer.read(self.out_pending_bytes)

        for msg in data.split(self.eol)[:-1]:
            self.handle(msg)
            self.out_pending_bytes -= len(msg) + len(self.eol)
        return len(data)

    def _readx_wrapper(self, reader, *args, **kwargs):
        """Place pointer of input buffer before and after read methods"""
        self.in_buffer.seek(self.in_read_bytes)
        msg = reader(*args, **kwargs)
        self.in_read_bytes += len(msg)
        return msg

    def read(self, size=1):
        return self._readx_wrapper(self.in_buffer.read, size)

    def readline(self, size=-1):
        return self._readx_wrapper(self.in_buffer.readline, size)

    def reset_input_buffer(self):
        self.in_read_bytes = self.in_buffer.getbuffer().nbytes
        self.in_buffer.seek(0, 2)

    def reset_output_buffer(self):
        pass


class CoherentSapphireLaserMock(SerialMock):
    """Modelled after a Coherent Sapphire LP 561nm laser.

    This mocked device is constructed into the ready state.  That is,
    after the laser has been turned on enough time to warmup (~ 30
    seconds), and then the key has been turned on for enough time to
    actual get the laser ready (~10 seconds).

    We don't mock the turning of the key, that's much trickier and we
    don't need it yet.  We'll do it if it ever becomes an issue, and
    probably use a state machine library for that.

    """
    eol = b'\r\n'

    ## Communication parameters
    baudrate = 19200
    parity = serial.PARITY_NONE
    bytesize = serial.EIGHTBITS
    stopbits = serial.STOPBITS_ONE
    rtscts = False
    dsrdtr = False

    ## Laser is 200mW, range is 10 to 110%
    default_power = 50.0
    min_power = 20.0
    max_power = 220.0

    def __init__(self, *args, **kwargs):
        super(CoherentSapphireLaserMock, self).__init__(*args, **kwargs)

        self.key = 'on'
        self.status = 'ready' # Laser ready, status code 5
        self.light = True # Light Servo
        self.tec = True # TEC (Thermo-Electric Cooler) Servo
        self.echo = True
        self.prompt = True
        self.power = CoherentSapphireLaserMock.default_power

    def write(self, data):
        ## Echo as soon as we get data, do not wait for an EOL.  Also,
        ## echo before handling the command because if will echo even
        ## if the command is to turn the echo off.
        if self.echo:
            self.in_buffer.write(data)
        else:
            ## If echo is off, we still echo EOLs
            self.in_buffer.write(self.eol * data.count(self.eol))
        return super(CoherentSapphireLaserMock, self).write(data)

    def handle(self, command):
        ## Operator's manual mentions all commands in uppercase.
        ## Experimentation shows that they are case insensitive.
        command = command.upper()

        answer = None

        ## Prompt
        if command == b'>=0':
            self.prompt = False
        elif command == b'>=1':
            self.prompt = True

        ## Echo
        elif command == b'E=0':
            self.echo = False
        elif command == b'E=1':
            self.echo = True

        ## Head ID
        elif command == b'?HID':
            answer = b'505925.000'

        ## Key switch
        elif command == b'?K':
            if self.key == 'standby':
                answer = b'0'
            elif self.key == 'on':
                answer = b'1'
            else:
                raise RuntimeError("unknown key state '%s'" % self.key)

        ## Light servo
        elif command == b'L=0':
            self.light = False
        elif command == b'L=1':
            if self.tec:
                if self.key == 'on':
                    self.light = True
                ## if key switch is not on, keep light off
            else:
                answer = b'TEC must be ON (T=1) to enable Light Output!'
        elif command == b'?L':
            if self.light:
                answer = b'1'
            else:
                answer = b'0'

        ## TEC servo
        elif command == b'T=0':
            ## turning this off, also turns light servo off
            self.tec = False
            self.light = False
        elif command == b'T=1':
            self.tec = True
        elif command == b'?T':
            if self.tec:
                answer = b'1'
            else:
                answer = b'0'

        ## Laser power
        elif command == b'?MINLP':
            answer = b'20.000'
        elif command == b'?MAXLP':
            answer = b'220.000'
        elif command == b'?P':
            if not self.light:
                answer = b'0.000'
            else:
                answer = b'%.3f' % (self.power)
        elif command.startswith(b'P='):
            new_power = float(command[2:])
            if new_power < 19.999999 or new_power > 220.00001:
                answer = b'value must be between 20.000 and 220.000'
            else:
                if not self.light:
                    answer = b'Note: Laser_Output is OFF (L=0)'
                self.power = new_power

        ## Nominal output power
        elif command == b'NOMP':
            answer = b'200'

        ## Laser type and nominal power
        elif command == b'LT':
            answer = b'Sapphire 200mW'

        ## Laser head status
        elif command == b'?STA':
            status_codes = {
                'start up' : b'1',
                'warmup' : b'2',
                'standby' : b'3',
                'laser on' : b'4',
                'laser ready' : b'5',
            }
            answer = status_codes[self.status]

        ## Software version
        elif command in [b'sv', b'svps']:
            answer = b'8.005'

        ## Nominal laser wavelength
        elif command == b'?WAVE':
            answer = b'561'

        else:
            raise NotImplementedError("no handling for command '%s'"
                                      % command.decode('utf-8'))

        if answer is not None:
            self.in_buffer.write(answer + self.eol)

        if self.prompt:
            self.in_buffer.write(b'Sapphire:0-> ')
        return
