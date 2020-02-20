#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Lumencor Spectra Light Engine.

The implementation here is limited to the Lumencor Spectra III but
should be trivial to make it work for other Lumencor light engines.
We only need access to other such devices.

.. note::

   The engine is expected to be on the standard mode communications
   (not legacy).  This can be changed via the device web interface.
"""

import threading
import typing

import serial

import microscope.devices


class _SyncSerial:
    """Wraps a `Serial` instance with a lock for synchronization."""
    def __init__(self, serial: serial.Serial) -> None:
        self._serial = serial
        self._lock = threading.RLock()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def readline(self) -> bytes:
        with self._lock:
            return self._serial.readline()

    def readlines(self, hint: int = -1) -> typing.List[bytes]:
        with self._lock:
            return self._serial.readlines(hint)

    def write(self, data: bytes) -> int:
        with self._lock:
            return self._serial.write(data)


class _SpectraIIIConnection:
    """Connection to a Spectra III Light Engine.

    This module makes checks for Spectra III light engine and it was
    only tested for it.  But it should work with other lumencor light
    engines with little work though, if only we got access to them.
    """
    def __init__(self, serial: _SyncSerial) -> None:
        self._serial = serial
        # We use command() and readline() instead of get_command() in
        # case this is not a Lumencor and won't even give a standard
        # answer and raises an exception during the answer validation.
        self._serial.write(b'GET MODEL\n')
        answer = self._serial.readline()
        if not answer.startswith(b'A MODEL Spectra III'):
            raise RuntimeError("Not a Lumencor Spectra III Light Engine")

    def command_and_answer(self, *TX_tokens: bytes) -> bytes:
        # Command contains two or more tokens.  The first token for a
        # TX (transmitted) command string is one of the two keywords
        # GET, SET (to query or to set).  The second token is the
        # command name.
        assert len(TX_tokens) >= 2, 'invalid command with less than two tokens'
        assert TX_tokens[0] in (b'GET', b'SET'), 'invalid command (not SET/GET)'

        TX_command = b' '.join(TX_tokens) + b'\n'
        with self._serial.lock:
            self._serial.write(TX_command)
            answer = self._serial.readline()
        RX_tokens = answer.split(maxsplit=2)
        # A received answer has at least two tokens.  The first token
        # is A or E (for success or failure).  The second token is the
        # command name (second token of the transmitted command).
        if (len(RX_tokens) < 2 or RX_tokens[0] != b'A'
            or RX_tokens[1] != TX_tokens[1]):
            raise RuntimeError('command %s failed: %s' % (TX_command, answer))
        return answer

    def get_command(self, command: bytes, *args: bytes) -> bytes:
        answer = self.command_and_answer(b'GET', command, *args)
        # The three bytes we remove at the start are the 'A ' before
        # the command, and the space after the command.  The last two
        # bytes are '\r\n'.
        return answer[3+len(command):-2]

    def set_command(self, command: bytes, *args: bytes) -> None:
        self.command_and_answer(b'SET', command, *args)

    def get_channel_map(self) -> typing.List[typing.Tuple[int, str]]:
        answer = self.get_command(b'CHMAP')
        return list(enumerate(answer.decode().split()))


class _LightChannelConnection:
    """Commands for a channel in a Lumencor light engine."""
    def __init__(self, connection: _SpectraIIIConnection, index: int) -> None:
        self._conn = connection
        self._index_bytes = b'%d' % index

    def get_light_state(self) -> bool:
        """On (True) or off (False) state"""
        # We use CHACT (actual light state) instead of CH (light
        # state) because CH checks both the TTL inputs and channel
        # state switches.
        state = self._conn.get_command(b'CHACT', self._index_bytes)
        if state == b'1':
            return True
        elif state == b'0':
            return False
        else:
            raise RuntimeError('unexpected answer')

    def set_light_state(self, state: bool) -> None:
        """Turn light on (True) or off (False)."""
        state_arg = b'1' if state else b'0'
        self._conn.set_command(b'CH', self._index_bytes, state_arg)

    def get_max_intensity(self) -> int:
        """Maximum valid intensity that can be applied to a light channel."""
        return int(self._conn.get_command(b'MAXINT', self._index_bytes))

    def get_power_output(self) -> float:
        """Estimated power output for a given channel (in mW).

        Power estimation is based on the power output calibration
        factor, power sensor reading, power sensor exposure, power
        sensor gain and crosstalk level.  Estimation model assumes
        linear dependency.
        """
        return float(self._conn.get_command(b'CHPWRWATTS', self._index_bytes))

    def get_power_reference(self) -> float:
        """Light power reference (in mW).

        This gives an indication of the power output when the channel
        is set to its maximum intensity.  However, its dependent on
        being manually set and kept adjusted over time.

        A value of -1 is returned if the power reference hasn't been
        defined yet.
        """
        return float(self._conn.get_command(b'PWRREF', self._index_bytes))

    def set_intensity(self, intensity: int) -> None:
        """Set light intensity between 0 and maximum intensity."""
        self._conn.set_command(b'CHINT', self._index_bytes, b'%d' % intensity)


class SpectraIIILightEngine(microscope.devices.ControllerDevice):
    """Spectra III Light Engine.

    Args:
        port (str): port name (Windows) or path to port (everything
            else) to connect to.  For example, `/dev/ttyS1`, `COM1`,
            or `/dev/cuad1`.

    The names used on the devices dict are the ones provided by the
    Spectra engine.  These are the colour names in capitals such as
    `'BLUE'`, `'NIR'`, or `'VIOLET'`.

    Not all sources may be turned on simultaneously. To prevent
    exceeding the capacity of the DC power supply, power consumption
    is tracked by the Spectra onboard computer. If a set limit is
    exceeded, either by increasing intensity settings for sources that
    are already on, or by turning on additional sources, commands will
    be rejected. To clear the error condition, reduce intensities of
    sources that are on or turn off additional sources.

    .. note::

       This relies on having power reference values set for each
       channel.  The Spectra light engines do not provide a method to
       obtain the maximum power output or to set the power ouput.  As
       such, this relies on the internal power reference value.  This
       should be set manually on the device to obtain reasonable
       results when setting the power output.

    """
    def __init__(self, port: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lights = {} # type: typing.Mapping[str, microscope.devices.Device]

        # We use standard (not legacy) mode communication so 115200,8,N,1
        serial_conn = serial.Serial(port=port, baudrate=115200, timeout=1,
                                    bytesize=serial.EIGHTBITS,
                                    stopbits=serial.STOPBITS_ONE,
                                    parity=serial.PARITY_NONE, xonxoff=False,
                                    rtscts=False, dsrdtr=False)
        connection = _SpectraIIIConnection(_SyncSerial(serial_conn))

        for index, name in connection.get_channel_map():
            if name in self._lights:
                raise RuntimeError('multiple lights with name \'%s\'' % name)
            self._lights[name] = _SpectraIIILightChannel(connection, index)

    @property
    def devices(self) -> typing.Mapping[str, microscope.devices.Device]:
        return self._lights


class _SpectraIIILightChannel(microscope.devices.LaserDevice):
    """A single light channel from a light engine.

    A channel is not necessarily a lasers although it subclasses from
    `LaserDevice`.  Constituent light sources may include LEDs,
    luminescent light pipes, or lasers.
    """
    def __init__(self, connection: _SpectraIIIConnection, index: int) -> None:
        super().__init__()
        self._conn = _LightChannelConnection(connection, index)
        # The lumencor only allows to set the power via intensity
        # levels (values between 0 and MAXINT) .  There is no method
        # to query the maximum power output, that information is on
        # the device certificate of conformance and may changes over
        # time.
        #
        # Power Reference is close to the max possible power (mw).  It
        # seems to do nothing other than providing a estimate of what
        # power will be emitted when the intensity is at its maximum.
        # It needs to be set manually and kept up to date.
        self._power_ref = self._conn.get_power_reference() # type: float
        if self._power_ref == -1:
            raise RuntimeError('Power reference value is not set')
        self._max_intensity = self._conn.get_max_intensity() # type: int

    def initialize(self) -> None:
        pass

    def _on_shutdown(self) -> None:
        # There is a shutdown command but this actually powers off the
        # device which is not what LaserDevice.shutdown() is meant to
        # do.  So do nothing.
        pass

    def get_status(self) -> typing.List[str]:
        status = [] # type: typing.List[str]
        return status

    def enable(self) -> None:
        self._conn.set_light_state(True)

    def disable(self) -> None:
        self._conn.set_light_state(False)

    def get_is_on(self) -> bool:
        return self._conn.get_light_state()

    def get_min_power_mw(self) -> float:
        return 0.0

    def get_max_power_mw(self) -> float:
        return self._power_ref

    def get_power_mw(self) -> float:
        return self._conn.get_power_output()

    def _set_power_mw(self, mw: float) -> None:
        # The mw argument should have already been clipped by
        # `LaserDevice.set_power_mw()` so no need to do so again.
        intensity = int((mw / self._power_ref) * self._max_intensity)
        self._conn.set_intensity(intensity)
