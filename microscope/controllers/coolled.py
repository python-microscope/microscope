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

"""CoolLED illumination systems.
"""

import logging
import typing

import serial

import microscope
import microscope._utils
import microscope.abc


_logger = logging.getLogger(__name__)


class _CoolLEDConnection:
    """Connection to the CoolLED controller, wraps base commands."""

    def __init__(self, serial: microscope._utils.SharedSerial) -> None:
        self._serial = serial

        # When we connect for the first time, we will get back a
        # greeting message like 'CoolLED precisExcite, Hello, pleased
        # to meet you'.  Discard it by reading until timeout.
        self._serial.readlines()

        # Check that this behaves like a CoolLED device.
        try:
            self.get_css()
        except Exception:
            raise microscope.InitialiseError(
                "Not a CoolLED device, unable to get CSS"
            )

    def get_css(self) -> bytes:
        """Get the global channel status map."""
        with self._serial.lock:
            self._serial.write(b"CSS?\n")
            answer = self._serial.readline()
        if not answer.startswith(b"CSS"):
            raise microscope.DeviceError(
                "answer to 'CSS?' should start with 'CSS'"
                " but got '%s' instead" % answer.decode
            )
        return answer[3:-2]  # remove initial b'CSS' and final b'\r\n'

    def set_css(self, css: bytes) -> None:
        """Set status for any number of channels."""
        assert len(css) % 6 == 0, "css must be multiple of 6 (6 per channel)"
        with self._serial.lock:
            self._serial.write(b"CSS" + css + b"\n")
            answer = self._serial.readline()
        if not answer.startswith(b"CSS"):
            raise microscope.DeviceError(
                "answer to 'CSS?' should start with 'CSS'"
                " but got '%s' instead" % answer.decode
            )

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
            raise ValueError("name should be a one character string")
        self._conn = connection
        self._css_offset = self._conn.get_css()[::6].index(name.encode()) * 6

    def _get_css(self) -> bytes:
        global_css = self._conn.get_css()
        return global_css[self._css_offset : self._css_offset + 6]

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
        if state not in ["N", "F"]:
            raise ValueError("state needs to be N (on) or F (off)")
        css = self._get_css()
        self._conn.set_css(css[0:2] + state.encode() + css[3:])

    def get_selected_state(self) -> str:
        "S (Selected) or X (Unselected)" ""
        return self._get_css()[1:2].decode()

    def set_selected_state(self, state: str) -> None:
        """X (Unselected) or S (Selected)"""
        if state not in ["X", "S"]:
            raise ValueError("state must be X (Unselected) or S (Selected)")
        css = self._get_css()
        self._conn.set_css(css[0:1] + state.encode() + css[2:])


class _CoolLEDChannel(microscope.abc.LightSource):
    """Individual light devices that compose a CoolLED controller."""

    def __init__(
        self, connection: _CoolLEDConnection, name: str, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._conn = _CoolLEDChannelConnection(connection, name)
        # If a channel is disabled ("unselected"), setting the trigger
        # type to software ("on") is not recorded and reverts back to
        # high ("off").  Because of this, we keep track of what
        # trigger type we want, i.e., should be "on" or "off", and
        # apply it when the channel is enabled.
        self._should_be_on = False

        # The channel may be "selected" (enabled) and "off" (trigger
        # type HIGH).  When we set the trigger type to software,
        # that's the same as setting it "on" which will make the
        # channel emit light.  Constructing this channel should not
        # accidentally mae it emit light so disable it firt.
        self.disable()

        # Default to software trigger type.
        self.set_trigger(
            microscope.TriggerType.SOFTWARE, microscope.TriggerMode.BULB
        )

    def _do_shutdown(self) -> None:
        pass

    def get_status(self) -> typing.List[str]:
        return []

    def enable(self) -> None:
        self._conn.set_selected_state("S")
        if self._should_be_on:
            # TriggerType.SOFTWARE
            self._conn.set_switch_state("N")
        else:
            # TriggerType.HIGH
            self._conn.set_switch_state("F")

    def disable(self) -> None:
        self._conn.set_selected_state("X")

    def get_is_on(self) -> bool:
        selected = self._conn.get_selected_state()
        assert selected in ["S", "X"]
        return selected == "S"

    def _do_get_power(self) -> float:
        return self._conn.get_intensity() / 100.0

    def _do_set_power(self, power: float) -> None:
        self._conn.set_intensity(int(power * 100.0))

    @property
    def trigger_type(self) -> microscope.TriggerType:
        if self._conn.get_selected_state() == "S":
            # Channel is "selected" (enabled): get the answer from
            # switch state ("on" or "off").
            if self._conn.get_switch_state() == "N":
                return microscope.TriggerType.SOFTWARE
            else:
                return microscope.TriggerType.HIGH
        else:
            # Channel is "unselected" (disabled): trigger type will be
            # whatever we set it to when we enable it.
            if self._should_be_on:
                return microscope.TriggerType.SOFTWARE
            else:
                return microscope.TriggerType.HIGH

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return microscope.TriggerMode.BULB

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if tmode is not microscope.TriggerMode.BULB:
            raise microscope.UnsupportedFeatureError(
                "the only trigger mode supported is 'bulb'"
            )
        if ttype is microscope.TriggerType.SOFTWARE:
            self._conn.set_switch_state("N")
            self._should_be_on = True
        elif ttype is microscope.TriggerType.HIGH:
            self._conn.set_switch_state("F")
            self._should_be_on = False
        else:
            raise microscope.UnsupportedFeatureError(
                "trigger type supported must be 'SOFTWARE' or 'HIGH'"
            )

    def _do_trigger(self) -> None:
        raise microscope.IncompatibleStateError(
            "trigger does not make sense in trigger mode bulb, only enable"
        )


class CoolLED(microscope.abc.Controller):
    """CoolLED controller for the individual light devices.

    Args:
        port: port name (Windows) or path to port (everything else) to
            connect to.  For example, `/dev/ttyACM0`, `COM1`, or
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

    CoolLED controllers are often used with a control pod which can
    select/unselect and turn on/off individual channels.  The meaning
    of these two states are:

    * "selected" and "on": channel is always emitting light.  This is
      equivalent to being enabled with `SOFTWARE` trigger type.

    * "selected" and "off": channel will emit light in receipt of a
      TTL signal.  This is equivalent to being enabled with `HIGH`
      trigger type.

    * "unselected" and "off": channel nevers emit light.  This is
      equivalent to being disabled.

    * "unselected" and "on": this is not possible.  If an "unselected"
      channel is turned "on" it reverts back to "off".

    .. note::

       If a channel is set with `TriggerType.SOFTWARE` ("on") it will
       start emitting light once enabled ("selected").  Once enabled,
       even though trigger type is set to software and not hardware,
       if the channel receives a TTL signal it will switch to
       `TriggerType.HIGH` and continue to report being set to
       software.  This seems to be an issue with the CoolLED
       https://github.com/python-microscope/vendor-issues/issues/9

    This was developed with a CoolLED pE-300 ultra but should work
    with the whole pE-300 series.  It should also work with the
    pE-4000 and the pE expansion box with the exception of loading
    different sources.

    """

    def __init__(self, port: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._channels: typing.Dict[str, microscope.abc.LightSource] = {}

        # CoolLED manual only has the baudrate, we guessed the rest.
        serial_conn = serial.Serial(
            port=port,
            baudrate=57600,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        shared_serial = microscope._utils.SharedSerial(serial_conn)
        connection = _CoolLEDConnection(shared_serial)
        for name in connection.get_channels():
            self._channels[name] = _CoolLEDChannel(connection, name)

    @property
    def devices(self) -> typing.Dict[str, microscope.abc.Device]:
        return self._channels
