#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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

import enum
import io

import serial.serialutil


class SerialMock(serial.serialutil.SerialBase):
    """Base class to mock devices controlled via serial.

    It has two :class:`io.BytesIO` buffers.  One :func:`write`s the
    output buffer and the other :func:`read`s the input buffer.  After
    a write, the output buffer is analysed for a command.  If there is
    a command, stuff gets done.  This usually means adding to the
    input buffer and changing state of the device.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_buffer = io.BytesIO()
        self.out_buffer = io.BytesIO()

        # Number of bytes in out buffer pending 'interpretation'.  A
        # command is only interpreted and handled when EOL is seen.
        self.out_pending_bytes = 0
        self.out_parsed_bytes = 0

        # Number of bytes in the input buffer that have been read
        self.in_read_bytes = 0

    def open(self):
        pass

    def close(self):
        self.in_buffer.close()
        self.out_buffer.close()

    def handle(self, command):
        raise NotImplementedError("sub classes need to implement handle()")

    def write(self, data):
        self.out_buffer.write(data)
        self.out_pending_bytes += len(data)

        if self.out_pending_bytes > len(data):
            # we need to retrieve data from a previous write
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

    eol = b"\r\n"

    # Communication parameters
    baudrate = 19200
    parity = serial.PARITY_NONE
    bytesize = serial.EIGHTBITS
    stopbits = serial.STOPBITS_ONE
    rtscts = False
    dsrdtr = False

    # Laser is 200mW, range is 10 to 110%
    default_power = 50.0
    min_power = 20.0
    max_power = 220.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.key = "on"
        self.status = "laser ready"  # Laser ready, status code 5
        self.light = True  # Light Servo
        self.tec = True  # TEC (Thermo-Electric Cooler) Servo
        self.echo = True
        self.prompt = True
        self.power = CoherentSapphireLaserMock.default_power

    def write(self, data):
        # Echo as soon as we get data, do not wait for an EOL.  Also,
        # echo before handling the command because if will echo even
        # if the command is to turn the echo off.
        if self.echo:
            self.in_buffer.write(data)
        else:
            # If echo is off, we still echo EOLs
            self.in_buffer.write(self.eol * data.count(self.eol))
        return super().write(data)

    def handle(self, command):
        # Operator's manual mentions all commands in uppercase.
        # Experimentation shows that they are case insensitive.
        command = command.upper()

        answer = None

        # Prompt
        if command == b">=0":
            self.prompt = False
        elif command == b">=1":
            self.prompt = True

        # Echo
        elif command == b"E=0":
            self.echo = False
        elif command == b"E=1":
            self.echo = True

        # Head ID
        elif command == b"?HID":
            answer = b"505925.000"

        # Head hours
        elif command == b"?HH":
            answer = b"   257:34"

        # Key switch
        elif command == b"?K":
            if self.key == "standby":
                answer = b"0"
            elif self.key == "on":
                answer = b"1"
            else:
                raise RuntimeError("unknown key state '%s'" % self.key)

        # Light servo
        elif command == b"L=0":
            self.light = False
        elif command == b"L=1":
            if self.tec:
                if self.key == "on":
                    self.light = True
                # if key switch is not on, keep light off
            else:
                answer = b"TEC must be ON (T=1) to enable Light Output!"
        elif command == b"?L":
            answer = b"1" if self.light else b"0"

        # TEC servo
        elif command == b"T=0":
            # turning this off, also turns light servo off
            self.tec = False
            self.light = False
        elif command == b"T=1":
            self.tec = True
        elif command == b"?T":
            answer = b"1" if self.tec else b"0"

        # Laser power
        elif command == b"?MINLP":
            answer = b"20.000"
        elif command == b"?MAXLP":
            answer = b"220.000"
        elif command == b"?P":
            if not self.light:
                answer = b"0.000"
            else:
                answer = b"%.3f" % (self.power)
        elif command == b"?SP":
            answer = b"%.3f" % (self.power)
        elif command.startswith(b"P="):
            new_power = float(command[2:])
            if new_power < 19.999999 or new_power > 220.00001:
                answer = b"value must be between 20.000 and 220.000"
            else:
                if not self.light:
                    answer = b"Note: Laser_Output is OFF (L=0)"
                self.power = new_power

        # Nominal output power
        elif command == b"NOMP":
            answer = b"200"

        # Laser type and nominal power
        elif command == b"LT":
            answer = b"Sapphire 200mW"

        # Laser head status
        elif command == b"?STA":
            status_codes = {
                "start up": b"1",
                "warmup": b"2",
                "standby": b"3",
                "laser on": b"4",
                "laser ready": b"5",
                "error": b"6",
            }
            answer = status_codes[self.status]

        # Fault related commands.  We don't model any faults yet.
        elif command == b"?F":
            answer = b"0"
        elif command == b"?FF":
            # Two bytes with possible faults:
            #    0 - external interlock fault
            #    1 - diode temperature fault (both TEC and light
            #        servo off)
            #    2 - base plate temperature fault (both TEC and light
            #        servo off)
            #    3 - OEM controller LP temperature (both TEC and
            #        light servo off)
            #    4 - diode current fault
            #    5 - analog interface fault
            #    6 - base plate temperature fault (only light servo
            #        turned off)
            #    7 - diode temperature fault (only light servo turned
            #        off)
            #    8 - system warning/waiting for TEC servo to reach
            #        target temperature
            #    9 - head EEPROM fault
            #   10 - OEM controller LP EEPROM fault
            #   11 - EEPOT1 fault
            #   12 - EEPOT2 fault
            #   13 - laser ready
            #   14 - not implemented
            #   15 - not implemented
            if self.light:
                # Has a bit of its own, but it's not really a fault.
                answer = b"8192"  # 00100000 00000000
            else:
                answer = b"0"
        elif command == b"?FL":
            # Show faults in text.  This is a multiline reply, one
            # per fault, plus the header line.
            answer = b"Fault(s):\r\n\tNone"

        # Software version
        elif command in [b"sv", b"svps"]:
            answer = b"8.005"

        # Nominal laser wavelength
        elif command == b"?WAVE":
            answer = b"561"

        else:
            raise NotImplementedError(
                "no handling for command '%s'" % command.decode("utf-8")
            )

        if answer is not None:
            self.in_buffer.write(answer + self.eol)

        if self.prompt:
            self.in_buffer.write(b"Sapphire:0-> ")
        return


class CoboltLaserMock(SerialMock):
    """Modelled after a Cobolt Jive laser 561nm.
    """

    eol = b"\r"

    baudrate = 115200
    parity = serial.PARITY_NONE
    bytesize = serial.EIGHTBITS
    stopbits = serial.STOPBITS_ONE
    rtscts = False
    dsrdtr = False

    # Values in mW
    default_power = 50.0
    min_power = 0.0
    max_power = 600.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.power = CoboltLaserMock.default_power
        self.light = False

        self.interlock_open = False

        self.auto_start = False
        self.direct_control = False

        self.on_after_interlock = False

        self.fault = None

    def handle(self, command):
        # Leading and trailing whitespace is ignored.
        command = command.strip()

        # Acknowledgment string if command is not a query and there
        # is no error.
        answer = b"OK"

        if command == b"sn?":  # serial number
            answer = b"7863"
        elif command == b"gcn?":
            answer = b"Macro-Gen5b-SHG-0501_4W-RevA"
        elif command == b"ver?" or command == b"gfv?":
            answer = b"50070"
        elif command == b"gfvlas?":
            answer = b"This laser head does not have firmware."
        elif command == b"hrs?":  # System operating hours
            answer = b"828.98"

        # TODO: This whole @cob0 and @cob1 need better testing on
        # what it actually does.  Documentation says that @cob1 is
        # "Laser ON after interlock.  Forces laser into
        # autostart. without checking if autostart is enabled".
        # @cob0 is undocumented.

        # May be a bug but the commands @cob0 and @cob1 both have the
        # effect of also turning off the laser.
        elif command == b"@cob1":
            self.on_after_interlock = True
            self.light = False
        elif command == b"@cob0":
            self.on_after_interlock = False
            self.light = False

        elif command == b"@cobas?":
            answer = b"1" if self.auto_start else b"0"
        elif command == b"@cobas 0":
            self.auto_start = False
        elif command == b"@cobas 1":
            self.auto_start = True

        # Laser state
        elif command == b"l?":
            answer = b"1" if self.light else b"0"
        elif command == b"l1":
            if self.auto_start:
                answer = b"Syntax error: not allowed in autostart mode."
            else:
                self.light = True
        elif command == b"l0":
            self.light = False

        # Output power
        elif command.startswith(b"p "):
            # The p command takes values in W so convert to mW
            new_power = float(command[2:]) * 1000.0
            if new_power > self.max_power or new_power < self.min_power:
                answer = b"Syntax error: Value is out of range."
            else:
                self.power = new_power
        elif command == b"p?":
            answer = b"%.4f" % (self.power / 1000.0)
        elif command == b"pa?":
            if self.light:
                answer = b"%.4f" % (self.power / 1000.0)
            else:
                answer = b"0.0000"

        # Undocumented.  Seems to be the same as 'p ...'
        elif command.startswith(b"@cobasp "):
            return self.handle(command[6:])

        # Direct control
        elif command == b"@cobasdr?":
            answer = b"1" if self.direct_control else b"0"
        elif command == b"@cobasdr 0":
            self.direct_control = False
        elif command == b"@cobasdr 1":
            self.direct_control = False

        # Undocumented.  Seems to returns maximum laser power in mW.
        elif command == b"gmlp?":
            answer = b"600.000000"

        # Are you there?
        elif command == b"?":
            answer = b"OK"

        # Get operating fault
        elif command == b"f?":
            # The errors (which we don't model yet) are:
            #   1 = temperature error
            #   3 = interlock
            #   4 = constant power fault
            answer = b"0"

        # Interlock state
        elif command == b"ilk?":
            answer = b"1" if self.interlock_open else b"0"

        # Autostart program state
        elif command == b"cobast?":
            # This is completely undocumented.  Manual
            # experimentation seems to be:
            # 0 = laser off with @cob0
            # 1 = laser off with @cob1
            # 2 = waiting for temperature
            # 3 = warming up
            # 4 = completed (laser on)
            # 5 = fault (such as interlock)
            # 6 = aborted
            if self.light:
                answer = b"4"
            else:
                answer = b"1" if self.on_after_interlock else b"0"

        else:
            raise NotImplementedError(
                "no handling for command '%s'" % command.decode("utf-8")
            )

        # Sending a command is done with '\r' only.  However,
        # responses from the hardware end with '\r\n'.
        self.in_buffer.write(answer + b"\r\n")


class OmicronDeepstarLaserMock(SerialMock):
    """Modelled after a TA Deepstar 488nm.
    """

    eol = b"\r\n"

    baudrate = 9600
    parity = serial.PARITY_NONE
    bytesize = serial.EIGHTBITS
    stopbits = serial.STOPBITS_ONE
    rtscts = False
    dsrdtr = False

    # Values in mW
    default_power = 50.0
    min_power = 0.0
    max_power = 200.0

    class State(enum.Enum):
        S0 = 0  # Global error state or interlocked state
        S1 = 1  # Standby state or Laser OFF state
        S2 = 2  # Laser ON state

    class Mode(enum.Enum):
        blackout = 1
        bias = 2
        modulated = 3
        deepstar = 4

    command2mode = {
        b"L0": Mode.blackout,
        b"BLK": Mode.blackout,
        b"LB": Mode.bias,
        b"L1": Mode.modulated,
        b"L2": Mode.deepstar,
    }
    mode2answer = {
        Mode.blackout: b"L0",  # always L0, even if BLK was used
        Mode.bias: b"LB",
        Mode.modulated: b"L1",
        Mode.deepstar: b"L2",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.power = self.default_power

        self.state = self.State.S1  # default dependent on 'ASx' command
        self.mode = self.Mode.blackout

        self.internal_peak_power = False
        self.analog2digital = False
        self.bias_modulation = False
        self.digital_modulation = False

    @property
    def light(self):
        if (
            self.state != self.State.S2
            or self.mode == self.mode.blackout
            or not self.internal_peak_power
            or (self.analog2digital and not self.digital_modulation)
        ):
            return False
        return True

    def write(self, data):
        # This connection does not wait for an eol to parse the
        # command.  It only looks at 16 or 7 bit (depending on
        # state).  Sending a message one character at a time will not
        # work so just send the whole data to be handled.
        self.handle(data)
        return len(data)

    def handle(self, command):
        if len(command) != 16 and (
            len(command) != 7 and self.state != self.State.S2
        ):
            # Such a thing will make the laser go into S0 state which
            # will also turns it off..  We don't model this because
            # we don't know well how the reset (RST command) works.
            raise RuntimeError("invalid Omicron Deepstar command")
        elif command[-2:] != b"\r\n":
            # Even if a command is correct, the last two characters
            # need to be \r\n.
            raise RuntimeError("command does not end in '\\r\\n'")

        command = command[:-2].rstrip(b" ")
        answer = None

        if command == b"S?":
            answer = self.state.name.encode()
        elif command == b"STAT0":
            # Model-code of the connected lasersystem:
            answer = (
                b"MC"
                + b" 488"  # wavelength
                + b" "  # empty for single diode system (D for double)
                + b" %3d" % (self.max_power)  # in mw
                + b" TA   "
            )  # controller version / operating mode
        elif command == b"STAT1":
            answer = (
                b"SL"
                + b" 6AB"  # actual bias (hexadecimal)
                + b" 600"  # modulated bias-level (hexadecimal)
                + b" 868"  # mod-level internal set for drive max. current
                + b" T249"  # diode temperature (in celcius * 10)
                + b" V117"
            )  # control voltage (in volts * 10)
        elif command == b"STAT2":
            answer = (
                b"R111"  # firmware release
                + b" N02"  # No used laserpen
                + b" SNP131056"  # S/No of laserhead
                + b" SNC131056"  # S/No of controller
                + b" WH 04667"  # working hours
                + b" SLS B9C 500"
            )  # start values for the diode parameters
        elif command == b"STAT3":
            # Stored option code flags.
            answer = (
                b"OC "
                + b"AS1"  # autostart option
                + b"TH0"  # TTL-logic-high
                + b"AP0"  # auto power correction
                + b"FK0"  # fiber coupling single mode
                + b"AC0"  # analog modulation for CW-lasers
                + b"AM0"  # analog modulation for modulated lasers
                + b"SU0"  # subtractive analog modulation for modulated lasers
                + b"CO0"  # collimator optic
                + b"FO0"  # focusing optic
                + b"MO0"  # highspeed monitoring
                + b"US0"  # USB interface
                + b"LA1"  # RS232 interface
                + b"FA0"
            )  # fiber coupling single mode

        # Changing mode
        elif command in self.command2mode.keys():
            if self.state == self.State.S2:
                self.mode = self.command2mode[command]
                answer = b">"
            else:
                answer = b"UK"

        # Current mode (undocumented)
        elif command == b"L?":
            if self.state == self.State.S2:
                answer = self.mode2answer[self.mode]
            else:
                answer = b"UK"

        # Laser on
        elif command == b"LON":
            if self.state == self.State.S1:
                self.state = self.State.S2
                answer = b"LONOK"
            elif self.mode == self.Mode.S2:
                answer = b"UK"
            else:  # in S0 state
                # This is undocumented and it's probably a bug on
                # their firmware.  Should probably be returning UK.
                answer = b"INT"

        # Laser off
        elif command == b"LF":
            if self.state == self.State.S2:
                self.state = self.State.S1
                answer = b"LOFFOK"
            else:
                answer = b"UK"

        # Peak Power
        elif command.startswith(b"PP"):
            # peak power values are a 3 byte char hexadecimal number,
            # scale to the range of possible power:
            #     000[hex] =    0[dec] =   0% =   0 mW
            #     FFF[hex] = 4095[dec] = 100% = 200 mW
            if command == b"PP?":
                level = self.power / self.max_power
                answer = b"PP%03X" % round(float(0xFFF) * level)
            elif len(command) == 5:
                level = int(command[2:], 16) / float(0xFFF)
                self.power = level * self.max_power
                answer = command
            else:
                raise RuntimeError("invalid command '%'" % command)

        # Power level
        elif command == b"P?":
            # TODO: get a laser that supports this command to test.
            # This is only based on the documentation.
            #
            # Actual laser power is a 4 byte char heaxadecimal
            # number.  Range for actual laser power is:
            #     0x0000 =    0 [dec] =   0% =   0 mW
            #     0x0CCC = 3276 [dec] = 100% = 200 mW
            #     0x0FFF = 4095 [dec] = 120% = 240 mW
            level = self.power / self.max_power
            answer = b"P%04X" % round(float(0xCCC) * level)

        # Internal peak power
        elif command == b"IPO":
            self.internal_peak_power = True
            answer = command
        elif command == b"IPF":
            self.internal_peak_power = False
            answer = command
        elif command == b"IP?":
            answer = b"IPO" if self.internal_peak_power else b"IPF"

        # Analogue modulation path or signal linked to the digital
        # modulation path.
        elif command == b"A2DO":
            self.analog2digital = True
            answer = b"A2D ON"
        elif command == b"A2DF":
            self.analog2digital = False
            answer = b"A2D OFF"
        elif command == b"A2D?":
            answer = b"A2D ON" if self.analog2digital else b"A2D OFF"

        # Bias and Digital modulation
        elif command == b"MF":
            self.bias_modulation = False
            self.digital_modulation = False
            answer = command
        elif command == b"MO1":
            self.bias_modulation = True
            self.digital_modulation = False
            answer = command
        elif command == b"MO2":
            self.bias_modulation = False
            self.digital_modulation = True
            answer = command
        elif command == b"MO3":
            self.bias_modulation = True
            self.digital_modulation = True
            answer = command

        else:
            raise NotImplementedError(
                "no handling for command '%s'" % command.decode("utf-8")
            )

        self.in_buffer.write(answer + self.eol)
