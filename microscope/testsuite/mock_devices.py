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

    It has two :class:`BytesIO` buffers.  One :func:`write` into the
    the output buffer and :func:`read` from the input buffer.  After a
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
        self.status = 'laser ready' # Laser ready, status code 5
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

        ## Head hours
        elif command == b'?HH':
            answer = b'   257:34'

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
            answer = b'1' if self.light else b'0'

        ## TEC servo
        elif command == b'T=0':
            ## turning this off, also turns light servo off
            self.tec = False
            self.light = False
        elif command == b'T=1':
            self.tec = True
        elif command == b'?T':
            answer = b'1' if self.tec else b'0'

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
        elif command == b'?SP':
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
                'error' : b'6',
            }
            answer = status_codes[self.status]

        ## Fault related commands.  We don't model any faults yet.
        elif command == b'?F':
            answer = b'0'
        elif command == b'?FF':
            ## Two bytes with possible faults:
            ##    0 - external interlock fault
            ##    1 - diode temperature fault (both TEC and light
            ##        servo off)
            ##    2 - base plate temperature fault (both TEC and light
            ##        servo off)
            ##    3 - OEM controller LP temperature (both TEC and
            ##        light servo off)
            ##    4 - diode current fault
            ##    5 - analog interface fault
            ##    6 - base plate temperature fault (only light servo
            ##        turned off)
            ##    7 - diode temperature fault (only light servo turned
            ##        off)
            ##    8 - system warning/waiting for TEC servo to reach
            ##        target temperature
            ##    9 - head EEPROM fault
            ##   10 - OEM controller LP EEPROM fault
            ##   11 - EEPOT1 fault
            ##   12 - EEPOT2 fault
            ##   13 - laser ready
            ##   14 - not implemented
            ##   15 - not implemented
            if self.light:
                ## Has a bit of its own, but it's not really a fault.
                answer = b'8192' # 00100000 00000000
            else:
                answer = b'0'
        elif command == b'?FL':
            ## Show faults in text.  This is a multiline reply, one
            ## per fault, plus the header line.
            answer = b'Fault(s):\r\n\tNone'

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


class CoboltLaserMock(SerialMock):
    """Modelled after a Cobolt Jive laser 561nm.
    """
    eol = b'\r'

    baudrate = 115200
    parity = serial.PARITY_NONE
    bytesize = serial.EIGHTBITS
    stopbits = serial.STOPBITS_ONE
    rtscts = False
    dsrdtr = False

    ## Values in mW
    default_power = 50.0
    min_power = 0.0
    max_power = 600.0

    def __init__(self, *args, **kwargs):
        super(CoboltLaserMock, self).__init__(*args, **kwargs)

        self.power = CoboltLaserMock.default_power
        self.light = False

        self.interlock_open = False

        self.auto_start = False
        self.direct_control = False

        self.on_after_interlock = False

        self.fault = None

    def handle(self, command):
        ## Leading and trailing whitespace is ignored.
        command = command.strip()

        ## Acknowledgment string if command is not a query and there
        ## is no error.
        answer = b'OK'

        if command == b'sn?': # serial number
            answer = b'7863'
        elif command == b'gcn?':
            answer = b'Macro-Gen5b-SHG-0501_4W-RevA'
        elif command == b'ver?' or command == b'gfv?':
            answer = b'50070'
        elif command == b'gfvlas?':
            answer = b'This laser head does not have firmware.'
        elif command == b'hrs?': # System operating hours
            answer = b'828.98'

        ## TODO: This whole @cob0 and @cob1 need better testing on
        ## what it actually does.  Documentation says that @cob1 is
        ## "Laser ON after interlock.  Forces laser into
        ## autostart. without checking if autostart is enabled".
        ## @cob0 is undocumented.

        ## May be a bug but the commands @cob0 and @cob1 both have the
        ## effect of also turning off the laser.
        elif command == b'@cob1':
            self.on_after_interlock = True
            self.light = False
        elif command == b'@cob0':
            self.on_after_interlock = False
            self.light = False

        elif command == b'@cobas?':
            answer = b'1' if self.auto_start else b'0'
        elif command == b'@cobas 0':
            self.auto_start = False
        elif command == b'@cobas 1':
            self.auto_start = True

        ## Laser state
        elif command == b'l?':
            answer = b'1' if self.light else b'0'
        elif command == b'l1':
            if self.auto_start:
                answer = b'Syntax error: not allowed in autostart mode.'
            else:
                self.light = True
        elif command == b'l0':
            self.light = False

        ## Output power
        elif command.startswith(b'p '):
            ## The p command takes values in W so convert to mW
            new_power = float(command[2:]) * 1000.0
            if new_power > self.max_power or new_power < self.min_power:
                answer = b'Syntax error: Value is out of range.'
            else:
                self.power = new_power
        elif command == b'p?':
            answer = b'%.4f' % (self.power / 1000.0)
        elif command == b'pa?':
            if self.light:
                answer = b'%.4f' % (self.power / 1000.0)
            else:
                answer = b'0.0000'

        ## Undocumented.  Seems to be the same as 'p ...'
        elif command.startswith(b'@cobasp '):
            return self.handle(command[6:])

        ## Direct control
        elif command == b'@cobasdr?':
            answer = b'1' if self.direct_control else b'0'
        elif command == b'@cobasdr 0':
            self.direct_control = False
        elif command == b'@cobasdr 1':
            self.direct_control = False

        ## Undocumented.  Seems to returns maximum laser power in mW.
        elif command == b'gmlp?':
            answer = b'600.000000'


        ## Are you there?
        elif command == b'?':
            answer = b'OK'

        ## Get operating fault
        elif command == b'f?':
            ## The errors (which we don't model yet) are:
            ##   1 = temperature error
            ##   3 = interlock
            ##   4 = constant power fault
            answer = b'0'

        ## Interlock state
        elif command == b'ilk?':
            answer = b'1' if self.interlock_open else b'0'

        ## Autostart program state
        elif command == b'cobast?':
            ## This is completely undocumented.  Manual
            ## experimentation seems to be:
            ## 0 = laser off with @cob0
            ## 1 = laser off with @cob1
            ## 2 = waiting for temperature
            ## 3 = warming up
            ## 4 = completed (laser on)
            ## 5 = fault (such as interlock)
            ## 6 = aborted
            if self.light:
                answer = b'4'
            else:
                answer = b'1' if self.on_after_interlock else b'0'

        else:
            raise NotImplementedError("no handling for command '%s'"
                                      % command.decode('utf-8'))

        ## Sending a command is done with '\r' only.  However,
        ## responses from the hardware end with '\r\n'.
        self.in_buffer.write(answer + b'\r\n')
