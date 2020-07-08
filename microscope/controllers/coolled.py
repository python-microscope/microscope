#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
#
# Microscope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Microscope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""CoolLED illumination systems.

This was developed with a CoolLED pE-300 ultra but should work with
the whole pE-300 series.  It should also work with the pE-4000 and the
pE expansion box with the exception of loading different sources.

"""

import logging
import typing

import serial

import microscope.devices

# TODO: move this into its own module.
from microscope.controllers.lumencor import _SyncSerial


_logger = logging.getLogger(__name__)


class _CoolLEDConnection:
    """Connection to the CoolLED controller, wraps base commands."""
    def __init__(self, serial: _SyncSerial) -> None:
        self._serial = serial

        # When we connect for the first time, we will get back a
        # greeting message like 'CoolLED precisExcite, Hello, pleased
        # to meet you'.  Discard it by reading until timeout.
        self._serial.readlines()

        # Check that this behaves like a CoolLED device.
        try:
            self.get_css()
        except:
            raise RuntimeError('Not a CoolLED device, unable to get CSS')

    def get_css(self) -> bytes:
        """Get the global channel status map."""
        with self._serial.lock:
            self._serial.write(b'CSS?\n')
            answer = self._serial.readline()
        if not answer.startswith(b'CSS'):
            raise RuntimeError('answer to \'CSS?\' should start with \'CSS\''
                               ' but got \'%s\' instead' % answer.decode)
        return answer[3:-2] # remove initial b'CSS' and final b'\r\n'

    def set_css(self, css: bytes) -> None:
        """Set status for any number of channels."""
        if len(css) % 6 != 0:
            raise ValueError('css must be multiple of 6 (6 per channel)')
        with self._serial.lock:
            self._serial.write(b'CSS' + css + b'\n')
            answer = self._serial.readline()
        if not answer.startswith(b'CSS'):
            raise RuntimeError('answer to \'CSS?\' should start with \'CSS\''
                               ' but got \'%s\' instead' % answer.decode)

    def get_channels(self) -> typing.List[str]:
        """Return list of channel names (names are one character string)."""
        # answer has the form: [xsnNNN] per channel.  The letter 'x'
        # defines the channel (A to H), 's' refers to S (Selected) or
        # X (Not selected), 'n' refers to N (On) or F (Off) and 'NNN'
        # is the intensity in integer percent.
        return list(self.get_css()[::6].decode())


class _CoolLEDChannelConnection:
    """Wraps the CoolLED connection to control a single channel."""
    def __init__(self, connection: _CoolLEDConnection, name: str) -> None:
        if len(name) != 1:
            raise ValueError('name should be a one character string')
        self._conn = connection
        self._css_offset = self._conn.get_css()[::6].index(name.encode()) * 6

    def _get_css(self) -> bytes:
        global_css = self._conn.get_css()
        return global_css[self._css_offset:self._css_offset+6]

    def get_intensity(self) -> int:
        """Intensity in integer percent [0 100]"""
        return int(self._get_css()[3:])

    def set_intensity(self, intensity: int) -> None:
        """Intensity in integer percent [0 100]"""
        percent = str(intensity).zfill(3)
        self._conn.set_css(self._get_css()[0:3] + percent.encode())

    def get_switch_state(self) -> str:
        """N (On) or F (Off)"""
        return self._get_css()[2:3].decode()

    def set_switch_state(self, state: str) -> None:
        """N (On) or F (Off)"""
        if state not in ['N', 'F']:
            raise ValueError('state needs to be N (on) or F (off)')
        css = self._get_css()
        self._conn.set_css(css[0:2] + state.encode() + css[3:])

    def get_selected_state(self) -> str:
        "S (Selected) or X (Unselected)"""
        return self._get_css()[1:2].decode()


class _CoolLEDChannel(microscope.devices.LaserDevice):
    """Individual light devices that compose a CoolLED controller."""
    def __init__(self, connection: _CoolLEDConnection, name: str,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self._conn = _CoolLEDChannelConnection(connection, name)
        selected_state = self._conn.get_selected_state()
        if selected_state != 'S':
            _logger.warning('CoolLED channel \'%s\' is not "selected".  It'
                            ' will not not emit light until it is "selected"'
                            ' on the control pod.'
                            % (name))

    def initialize(self) -> None:
        pass
    def _on_shutdown(self) -> None:
        pass
    def get_status(self) -> typing.List[str]:
        return []

    def enable(self) -> None:
        self._conn.set_switch_state('N')

    def disable(self) -> None:
        self._conn.set_switch_state('F')

    def get_is_on(self) -> bool:
        switch = self._conn.get_switch_state()
        assert switch in ['N', 'F']
        if switch == 'N':
            return True
        else:
            return False

    # FIXME: we need to fix the ABC to use [0 1] values instead of mw.
    # While we don't do that, this is already set to take values in
    # that range (argument is not mw and the channels are not even
    # lasers).
    def get_min_power_mw(self) -> float:
        return 0.0
    def get_max_power_mw(self) -> float:
        return 1.0
    def get_power_mw(self) -> float:
        return self._conn.get_intensity() / 100.0
    def _set_power_mw(self, mw: float) -> None:
        self._conn.set_intensity(int(mw * 100.0))


class CoolLED(microscope.devices.ControllerDevice):
    """CoolLED controller for the individual light devices.

    Args:
        port: port name (Windows) or path to port (everything else) to
            connect to.  For example, `/dev/ttyS1`, `COM1`, or
            `/dev/cuad1`.

    The individual channels are named A to H and depend on the actual
    device.  The pE-300 have three channels named A, B, and C by
    increasing order of wavelength of their spectral region.  The
    pE-4000 have four selectable channels named A, B, C, and D with
    channels E-H for peripheral devices via a pE expansion box.

    .. code-block:: python

       # Connect to a pE-300 ultra and get the individual lights.
       controller = CoolLED('/dev/ttyACM0')
       violet = controller.devices['A']
       blue = controller.devices['B']
       red = controller.devices['C']

       # Turn on the violet channel.
       violet.enable()

    CoolLED controllers are often also used with a control pod.  The
    control pod can turn on and off individual channels but it can
    also select/unselect those channels.  If a channel is "unselected"
    a channel can only be off.  Calling `enable()` on the individual
    channels will not "select" them, the user should do it himself via
    the control pod.
    """
    def __init__(self, port: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._channels = {} # type: typing.Mapping[str, microscope.devices.LaserDevice]

        # CoolLED manual only has the baudrate, we guessed the rest.
        serial_conn = serial.Serial(port=port, baudrate=57600, timeout=1,
                                    bytesize=serial.EIGHTBITS,
                                    stopbits=serial.STOPBITS_ONE,
                                    parity=serial.PARITY_NONE, xonxoff=False,
                                    rtscts=False, dsrdtr=False)
        connection = _CoolLEDConnection(_SyncSerial(serial_conn))
        for name in connection.get_channels():
            self._channels[name] = _CoolLEDChannel(connection, name)

    @property
    def devices(self) -> typing.Mapping[str, microscope.devices.Device]:
        return self._channels
