#!/usr/bin/env python3

## Copyright (C) 2022 Julio Mateos Langerak <julio.mateos-langerak@igh.cnrs.fr>
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

import logging

import serial

import microscope.abc

_logger = logging.getLogger(__name__)

MODEL_TO_NR_POSITIONS = {"06": 2,
                         "09": 4,
                         "12": 6}
ERROR_CODES = {0: "OK, no error",
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
               13: "Over Current error"
               }


class ThorlabsELLSlider(microscope.abc.FilterWheel, microscope.abc.SerialDeviceMixin):
    """Implements interface for Thorlabs ELL Multi-Position Sliders with Resonant Piezoelectric Motors.
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
            parity=serial.PARITY_NONE
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
        position_count = MODEL_TO_NR_POSITIONS[info[3:5]]

        # Slider has to be initialized
        self.initialize()
        super().__init__(positions=position_count, **kwargs)

    def initialize(self) -> None:
        _logger.info("Initializing slider")
        self._write(self.address + b"gs")
        reply = self._readline()
        if reply != b"0GS00":
            raise microscope.InitialiseError(
                f"Failed to initialize: {ERROR_CODES[int(reply[3:].decode())]}"
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

