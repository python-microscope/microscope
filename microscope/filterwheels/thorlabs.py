#!/usr/bin/env python3

## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
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

import io
import string
import threading
import warnings

import serial

import microscope
import microscope.abc


ELL_MODEL_TO_NR_POSITIONS = {"06": 2, "09": 4, "12": 6}


ELL_ERROR_CODES = {
    0: "OK, no error",
    1: "Communication time out",
    2: "Mechanical time out",
    3: "Command error or not supported",
    4: "Value out of range",
    5: "Module isolated",
    6: "Module out of isolation",
    7: "Initializing error",
    8: "Thermal error",
    9: "Busy",
    10: "Sensor Error (May appear during self test. If code persists there is an error)",
    11: "Motor Error (May appear during self test. If code persists there is an error)",
    12: "Out of Range (e.g. stage has been instructed to move beyond its travel range)",
    13: "Over Current error",
}


class ThorlabsFilterWheel(microscope.abc.FilterWheel):
    """Implements FilterServer wheel interface for Thorlabs FW102C.

    Note that the FW102C also has manual controls on the device, so clients
    should periodically query the current wheel position."""

    def __init__(self, com, baud=115200, timeout=2.0, **kwargs):
        """Create ThorlabsFilterWheel

        :param com: COM port
        :param baud: baud rate
        :param timeout: serial timeout
        """
        self.eol = "\r"
        rawSerial = serial.Serial(
            port=com,
            baudrate=baud,
            timeout=timeout,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            xonxoff=0,
        )
        # The Thorlabs controller serial implementation is strange.
        # Generally, it uses \r as EOL, but error messages use \n.
        # A readline after sending a 'pos?\r' command always times out,
        # but returns a string terminated by a newline.
        # We use TextIOWrapper with newline=None to perform EOL translation
        # inbound, but must explicitly append \r to outgoing commands.
        # The TextIOWrapper also deals with conversion between unicode
        # and bytes.
        self.connection = io.TextIOWrapper(
            rawSerial,
            newline=None,
            line_buffering=True,  # flush on write
            write_through=True,  # write out immediately
        )
        # A lock for the connection.  We should probably be using
        # SharedSerial (maybe change it to SharedIO, and have it
        # accept any IOBase implementation).
        self._lock = threading.RLock()
        position_count = int(self._send_command("pcount?"))
        super().__init__(positions=position_count, **kwargs)

    def _do_shutdown(self) -> None:
        pass

    def _do_set_position(self, new_position: int) -> None:
        # Thorlabs positions start at 1, hence the +1
        self._send_command("pos=%d" % (new_position + 1))

    def _do_get_position(self):
        # Thorlabs positions start at 1, hence the -1
        try:
            return int(self._send_command("pos?")) - 1
        except TypeError:
            raise microscope.DeviceError(
                "Unable to get position of %s", self.__class__.__name__
            )

    def _readline(self):
        """Custom _readline to overcome limitations of the serial implementation."""
        result = []
        with self._lock:
            while not result or result[-1] not in ("\n", ""):
                char = self.connection.read()
                # Do not allow lines to be empty.
                if result or (char not in string.whitespace):
                    result.append(char)
        return "".join(result)

    def _send_command(self, command):
        """Send a command and return any result."""
        with self._lock:
            self.connection.write(command + self.eol)
            response = "dummy"
            while command not in response and ">" not in response:
                # Read until we receive the command echo.
                response = self._readline().strip()
            if command.endswith("?"):
                # Last response was the command. Next is result.
                return self._readline().strip()
        return None


class ThorlabsFW102C(ThorlabsFilterWheel):
    """Deprecated, use ThorlabsFilterWheel.

    This class is from when ThorlabsFilterWheel did not automatically
    found its own number of positions and there was a separate class
    for each thorlabs filterwheel model.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Use ThorlabsFilterWheel instead of ThorlabsFW102C",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
        if self.n_positions != 6:
            raise microscope.InitialiseError(
                "Does not look like a FW102C, it has %d positions instead of 6"
            )


class ThorlabsFW212C(ThorlabsFilterWheel):
    """Deprecated, use ThorlabsFilterWheel.

    This class is from when ThorlabsFilterWheel did not automatically
    found its own number of positions and there was a separate class
    for each thorlabs filterwheel model.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Use ThorlabsFilterWheel instead of ThorlabsFW212C",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
        if self.n_positions != 12:
            raise microscope.InitialiseError(
                "Does not look like a FW212C, it has %d positions instead of 12"
            )


class ThorlabsELLSlider(
    microscope.abc.FilterWheel, microscope.abc.SerialDeviceMixin
):
    """Implements interface for Thorlabs ELL Multi-Position Sliders with
    Resonant Piezoelectric Motors.
    """

    def __init__(self, com, baud=9600, timeout=2.0, address=0, **kwargs):
        """Create ThorlabsELLSlider

        :param com: COM port
        :param baud: baud rate
        :param timeout: serial timeout
        :param address: the address of the device in teh daisy chain
        """
        self.address = str(address).encode()
        self.connection = serial.Serial(
            port=com,
            baudrate=baud,
            timeout=timeout,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
        )

        # Getting information about hte device
        self._write(self.address + b"in")
        info = self._readline().decode()

        self.travel = int(info[21:25], 16)
        # According to the manual you should request a movement using number of pulses but the fact is that my
        # device responds to requesting directly to engineering units (mm for linear stages) and pulses_per_unit is 0
        self.pulses_per_unit = int(info[25:33], 16)
        # We are therefore using the jog_step_size as a measure of the movement units
        self._write(self.address + b"gj")
        self.jog_step_size = int(self._readline()[3:], 16)
        self.serial_number = info[5:13]
        self.manufacturing_year = info[13:17]

        _logger.info(f"Connected to slider: {self.address.decode()}")
        _logger.info(f"s/n: {self.serial_number}")
        _logger.info(f"Manufacturing year: {self.manufacturing_year}")
        position_count = ELL_MODEL_TO_NR_POSITIONS[info[3:5]]

        # Slider has to be initialized
        self.initialize()
        super().__init__(positions=position_count, **kwargs)

    def initialize(self) -> None:
        _logger.info("Initializing slider")
        self._write(self.address + b"gs")
        reply = self._readline()
        if reply != b"0GS00":
            raise microscope.InitialiseError(
                f"Failed to initialize: {ELL_ERROR_CODES[int(reply[3:].decode())]}"
            )
        else:
            self._home_device()

    def _home_device(self) -> None:
        _logger.info("Homing slider")
        self._write(self.address + b"ho0")
        if self._readline() != (self.address + b"PO00000000"):
            raise Exception("could not home")

    def _do_shutdown(self) -> None:
        pass

    def _do_set_position(self, new_position: int) -> None:
        """
        For some reason I do not find in the documentation we have to instruct the slider to move by 1 more mm
        An example from Thorlabs console:
        Homing device ...
        Tx: 0ho0
        Rx: 0PO00000000
        Homing device ...
        Tx: 0ho0
        Rx: 0PO00000000
        Move device to 0.0 mm...
        Tx: 0ma00000000
        Rx: 0PO00000000
        Move device to 32.0 mm...
        Tx: 0ma00000020
        Rx: 0PO0000001F
        Move device to 64.0 mm...
        Tx: 0ma00000040
        Rx: 0PO0000003E
        Move device to 96.0 mm...
        Tx: 0ma00000060
        Rx: 0PO0000005D
        """
        position = new_position * (self.jog_step_size + 1)

        position = hex(position)[2:].zfill(8).encode()
        self._write(self.address + b"ma" + position)
        reply = self._readline()

        if reply[:3] != (self.address + b"PO"):
            raise Exception("Cannot set position")

    def _do_get_position(self):
        self._write(self.address + b"gp")
        position = self._readline()

        position = int(position[3:], 16)
        position = position // self.jog_step_size

        return position
