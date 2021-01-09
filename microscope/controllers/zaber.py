#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
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

"""Zaber devices.

Devices supported
-----------------

There is support for A-Series and X-Series devices that have firmware
version 6.06 or higher, as these are the ones who support the ASCII
protocol.

.. todo::

    Create non controller classes for the simpler case where there is
    only one Zaber device, and modelling it as controller device is
    non obvious.

.. todo::

    Consider using `__slots__` on the `_ZaberReply` for performance.

"""

import enum
import logging
import threading
import time
import typing

import serial

import microscope
import microscope._utils
import microscope.abc


_logger = logging.getLogger(__name__)

_AT_CODE = ord(b"@")
_SPACE_CODE = ord(b" ")


class _ZaberReply:
    """Wraps a Zaber reply to easily index its multiple fields. """

    def __init__(self, data: bytes) -> None:
        self._data = data
        if (
            data[0] != _AT_CODE
            or data[-2:] != b"\r\n"
            or any([data[i] != _SPACE_CODE for i in (3, 5, 8, 13, 16)])
        ):
            raise ValueError("Not a valid reply from a Zaber device")

    @property
    def address(self) -> bytes:
        """The start of reply with device address and space."""
        return self._data[1:3]

    @property
    def flag(self) -> bytes:
        """The reply flag indicates if the message was accepted or rejected.

        Can be `b"OK"` (accepted) or `b"RJ"` (rejected).  If rejected,
        the response property will be one word with the reason why.
        """
        return self._data[6:8]

    @property
    def status(self) -> bytes:
        """``b"BUSY"`` when the axis is moving and ``b"IDLE"`` otherwise.

        If the reply message applies to the whole device, the status
        is `b"BUSY"` if any axis is busy and `b"IDLE"` if all axes are
        idle.
        """
        return self._data[9:13]

    @property
    def warning(self) -> bytes:
        """The highest priority warning currently active.

        This will be `b'--'` under normal conditions.  Anything else
        is a warning.
        """
        return self._data[14:16]

    @property
    def response(self) -> bytes:
        # Assumes no checksum
        return self._data[17:-2]


class _ZaberConnection:
    """Wraps a serial connection with a reentrant lock.

    This class is just the wrap to :class:`serial.Serial`.  The class
    exposing the Zaber commands interface is
    :class:`_ZaberDeviceConnection`.

    .. todo: replace with microscope._utils.SharedSerial
    """

    def __init__(self, port: str, baudrate: int, timeout: float) -> None:
        self._serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        self._lock = threading.RLock()
        with self._lock:
            # The command / does nothing other than getting a response
            # from all devices in the chain.  This seems to be the
            # most innocent command we can use.
            self._serial.write(b"/\n")
            lines = self._serial.readlines()
        if not all([l.startswith(b"@") for l in lines]):
            raise RuntimeError(
                "'%s' does not respond like a Zaber device" % port
            )

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def write(self, data: bytes) -> int:
        with self.lock:
            return self._serial.write(data)

    def readline(self, size: int = -1) -> bytes:
        with self.lock:
            return self._serial.readline(size)


class _ZaberDeviceConnection:
    """A Zaber connection to control a single device.

    This class provides a Python interface to the Zaber commands.  It
    also does the routing of commands to the correct device in the
    chain.

    Args:
        conn: the :class:`_ZaberConnection` instance for this device.
        device_address: the device address for the specific device.
            This is the number used at the start of all Zaber
            commands.
    """

    def __init__(self, conn: _ZaberConnection, device_address: int) -> None:
        self._conn = conn
        self._address_bytes = b"%02d" % device_address

    def _validate_reply(self, reply: _ZaberReply) -> None:
        if reply.address != self._address_bytes:
            raise RuntimeError(
                "received reply from a device with different"
                " address (%s instead of %s)"
                % (reply.address.decode(), self._address_bytes.decode())
            )
        if reply.flag != b"OK":
            raise RuntimeError(
                "command rejected because '%s'" % reply.response.decode()
            )

    def command(self, command: bytes, axis: int = 0) -> _ZaberReply:
        """Send command and return reply.

        Args:
            command: a bytes array with the command and its
                parameters.
            axis: the axis number to send the command.  If zero, the
                command is executed by all axis in the device.
        """
        # We do not need to check whether axis number is valid because
        # the device will reject the command with BADAXIS if so.
        with self._conn.lock:
            self._conn.write(
                b"/%s %1d %s\n" % (self._address_bytes, axis, command)
            )
            data = self._conn.readline()
        reply = _ZaberReply(data)
        self._validate_reply(reply)
        return reply

    def is_busy(self) -> bool:
        return self.command(b"").status == b"BUSY"

    def wait_until_idle(self, timeout: float = 10.0) -> None:
        """Wait, or error, until device is idle.

        A device is busy if *any* of its axis is busy.
        """
        sleep_interval = 0.1
        for _ in range(int(timeout / sleep_interval)):
            if not self.is_busy():
                break
            time.sleep(sleep_interval)
        else:
            raise microscope.DeviceError(
                "device still busy after %f seconds" % timeout
            )

    def get_number_axes(self) -> int:
        """Reports the number of axes in the device."""
        return int(self.command(b"get system.axiscount").response)

    def been_homed(self, axis: int = 0) -> bool:
        """True if all axes, or selected axis, has been homed."""
        reply = self.command(b"get limit.home.triggered", axis)
        return all([int(x) for x in reply.response.split()])

    def home(self, axis: int = 0) -> None:
        """Move the axis to the home position."""
        self.command(b"home", axis)

    def get_rotation_length(self, axis: int) -> int:
        """Number of microsteps needed to complete one full rotation.

        This is only valid on controllers and rotary devices including
        filter wheels and filter cube turrets.
        """
        return int(self.command(b"get limit.cycle.dist", axis).response)

    def get_index_distance(self, axis: int) -> int:
        """The distance between consecutive index positions."""
        return int(self.command(b"get motion.index.dist", axis).response)

    def get_current_index(self, axis: int) -> int:
        """The current index number or zero if between index positions."""
        return int(self.command(b"get motion.index.num", axis).response)

    def move_to_index(self, axis: int, index: int) -> None:
        self.command(b"move index %d" % index, axis)

    def move_to_absolute_position(self, axis: int, position: int) -> None:
        self.command(b"move abs %d" % position, axis)

    def move_by_relative_position(self, axis: int, position: int) -> None:
        self.command(b"move rel %d" % position, axis)

    def get_absolute_position(self, axis: int) -> int:
        """Current absolute position of an axis, in microsteps."""
        return int(self.command(b"get pos", axis).response)

    def get_limit_max(self, axis: int) -> int:
        """The maximum position the device can move to, in microsteps."""
        return int(self.command(b"get limit.max", axis).response)

    def get_limit_min(self, axis: int) -> int:
        """The minimum position the device can move to, in microsteps."""
        return int(self.command(b"get limit.min", axis).response)

    def lamp_off(self, channel: int) -> None:
        self.command(b"lamp off", channel)

    def lamp_on(self, channel: int) -> None:
        self.command(b"lamp on", channel)

    def get_lamp_max_flux(self, channel: int) -> float:
        return float(self.command(b"get lamp.flux.max", channel).response)

    def get_lamp_flux(self, channel: int) -> float:
        return float(self.command(b"get lamp.flux", channel).response)

    def set_lamp_flux(self, channel: int, flux: float) -> None:
        self.command(b"set lamp.flux %.3f" % flux, channel)

    def get_lamp_is_on(self, channel: int) -> bool:
        return self.command(b"get lamp.status", channel).response == b"2"

    def get_lamp_temperature(self, channel: int) -> float:
        return float(self.command(b"get lamp.temperature", channel).response)


class _ZaberStageAxis(microscope.abc.StageAxis):
    def __init__(self, dev_conn: _ZaberDeviceConnection, axis: int) -> None:
        super().__init__()
        self._dev_conn = dev_conn
        self._axis = axis

    def move_by(self, delta: float) -> None:
        self._dev_conn.move_by_relative_position(self._axis, int(delta))
        self._dev_conn.wait_until_idle()

    def move_to(self, pos: float) -> None:
        self._dev_conn.move_to_absolute_position(self._axis, int(pos))
        self._dev_conn.wait_until_idle()

    @property
    def position(self) -> float:
        if self._dev_conn.is_busy():
            _logger.warning("querying stage axis position but device is busy")
            self._dev_conn.wait_until_idle()
        return float(self._dev_conn.get_absolute_position(self._axis))

    @property
    def limits(self) -> microscope.AxisLimits:
        min_limit = self._dev_conn.get_limit_min(self._axis)
        max_limit = self._dev_conn.get_limit_max(self._axis)
        return microscope.AxisLimits(lower=min_limit, upper=max_limit)


class _ZaberStage(microscope.abc.Stage):
    def __init__(
        self, conn: _ZaberConnection, device_address: int, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._dev_conn = _ZaberDeviceConnection(conn, device_address)
        self._axes = {
            str(i): _ZaberStageAxis(self._dev_conn, i)
            for i in range(1, self._dev_conn.get_number_axes() + 1)
        }

    def _do_shutdown(self) -> None:
        pass

    def _do_enable(self) -> bool:
        # Before a device can moved, it first needs to establish a
        # reference to the home position.  We won't be able to move
        # unless we home it first.
        if not self._dev_conn.been_homed():
            self._dev_conn.home()
        return True

    @property
    def axes(self) -> typing.Mapping[str, microscope.abc.StageAxis]:
        return self._axes

    def move_by(self, delta: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance. """
        for axis_name, axis_delta in delta.items():
            self._dev_conn.move_by_relative_position(
                int(axis_name), int(axis_delta),
            )
        self._dev_conn.wait_until_idle()

    def move_to(self, position: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance. """
        for axis_name, axis_position in position.items():
            self._dev_conn.move_to_absolute_position(
                int(axis_name), int(axis_position),
            )
        self._dev_conn.wait_until_idle()


class _ZaberFilterWheel(microscope.abc.FilterWheel):
    """Zaber filter wheels and filter cube turrets."""

    def __init__(
        self, conn: _ZaberConnection, device_address: int, **kwargs
    ) -> None:
        self._dev_conn = _ZaberDeviceConnection(conn, device_address)

        if self._dev_conn.get_number_axes() != 1:
            raise microscope.InitialiseError(
                "Device with address %d is not a filter wheel" % device_address
            )

        rotation_length = self._dev_conn.get_rotation_length(1)
        if rotation_length <= 0:
            raise microscope.InitialiseError(
                "Device with address %d is not a filter wheel" % device_address
            )
        positions = int(rotation_length / self._dev_conn.get_index_distance(1))

        super().__init__(positions, **kwargs)

        # Before a device can moved, it first needs to establish a
        # reference to the home position.  We won't be able to move
        # unless we home it first.  On a stage this happens during
        # enable because the stage movemenet can be dangerous but on a
        # filter wheel this is fine.
        if not self._dev_conn.been_homed():
            self._dev_conn.home()

    def _do_shutdown(self) -> None:
        pass

    def _do_get_position(self) -> int:
        if self._dev_conn.is_busy():
            _logger.warning("querying filterwheel position but device is busy")
            self._dev_conn.wait_until_idle()
        # Zaber positions start at one, hence -1.
        return self._dev_conn.get_current_index(axis=1) - 1

    def _do_set_position(self, position: int) -> None:
        # Zaber positions start at one, hence +1.
        self._dev_conn.move_to_index(axis=1, index=position + 1)
        self._dev_conn.wait_until_idle()


class _ZaberLED(
    microscope._utils.OnlyTriggersBulbOnSoftwareMixin,
    microscope.abc.LightSource,
):
    """A single LED from a LED controller."""

    def __init__(self, dev_conn: _ZaberDeviceConnection, channel: int) -> None:
        super().__init__()
        self._dev_conn = dev_conn
        self._channel = channel
        self._max_flux = self._dev_conn.get_lamp_max_flux(self._channel)
        self.add_setting(
            "temperature",
            "float",
            lambda: self._dev_conn.get_lamp_temperature(self._channel),
            None,
            values=tuple(),
        )

        for our_name, their_name in [
            ("wavelength peak", "lamp.wavelength.peak"),
            ("wavelength fwhm", "lamp.wavelength.fwhm"),
        ]:
            reply = self._dev_conn.command(
                b"get %s" % their_name.encode(), self._channel
            )
            value = float(reply.response)
            self.add_setting(
                our_name, "float", lambda x=value: x, None, values=tuple(),
            )

    def _do_shutdown(self) -> None:
        pass

    def get_status(self) -> typing.List[str]:
        return super().get_status()

    def _do_enable(self) -> bool:
        self._dev_conn.lamp_on(self._channel)
        return True

    def _do_disable(self) -> None:
        self._dev_conn.lamp_off(self._channel)

    def _do_get_power(self) -> float:
        return self._dev_conn.get_lamp_flux(self._channel) / self._max_flux

    def _do_set_power(self, power: float) -> None:
        self._dev_conn.set_lamp_flux(self._channel, power * self._max_flux)

    def get_is_on(self) -> bool:
        return self._dev_conn.get_lamp_is_on(self._channel)


class _ZaberLEDController(microscope.abc.Controller):
    """This effectively means a Zaber X-LCA4 LED controller.

    The X-LCA4 series is so far the only LED controller Zaber has.
    Its documentation is not included on the ASCII protocol manual,
    see the `controller specific manual online
    <https://www.zaber.com/protocol-manual?device=X-LCA4>`_

    """

    def __init__(
        self, conn: _ZaberConnection, device_address: int, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._dev_conn = _ZaberDeviceConnection(conn, device_address)
        self._leds: typing.Dict[str, _ZaberLED] = {}

        all_lamps = self._dev_conn.command(b"get lamp.status").response.split()
        # We get one status per peripheral connection.  Documentation
        # states that a value of "0" means unplugged but with X-LCA4,
        # firmware version 7.13 and build 8074, we get NA for
        # unplugged.  Also not sure how 0 (unplugged) would differ
        # from 5 (peripheral not connected).  So we count as valid
        # those with status 1 (turned off), 2 (turned on), and 3
        # (fault).
        for i, lamp_state in enumerate(all_lamps, start=1):
            if lamp_state in [b"1", b"2", b"3"]:
                # The labels on the controller are LED1, LED2, etc, so
                # use the same for key.
                self._leds["LED%d" % i] = _ZaberLED(self._dev_conn, i)
            else:
                _logger.info("no LED %d, status is %s", i, lamp_state.decode())

    @property
    def devices(self) -> typing.Dict[str, _ZaberLED]:
        return self._leds


class ZaberDeviceType(enum.Enum):
    """Enumerator for Zaber device types.

    This enum is used to specify the type of device for each address
    when constructing a :class:`ZaberDaisyChain`.
    """

    # We require the use of an enum instead of directly specifying the
    # class to keep the individual device classes private.
    STAGE = _ZaberStage
    FILTER_WHEEL = _ZaberFilterWheel
    LED_CONTROLLER = _ZaberLEDController


class ZaberDaisyChain(microscope.abc.Controller):
    """A daisy chain of Zaber devices.

    Args:
        port: the port name to connect to.  For example, `COM1`,
            `/dev/ttyUSB0`, or `/dev/cuad1`.
        address2type: a map of device addresses to the corresponding
            :class:`ZaberDeviceType`.

    Zaber devices can be daisy-chained, i.e., a set of Zaber devices
    can be connected in a sequence so that each device is only wired
    to the previous and next device in the sequence, and only the
    first device in the sequence is connected to the computer.  Even
    if there is only Zaber device, this is modelled as a one element
    daisy-chain.  If there are multiple devices, all connected
    directly to the computer, i.e., not chained, then each device is
    its own one-element daisy-chain.

    .. code-block:: python

        from microscope.controllers.zaber import ZaberDaisyChain, ZaberDeviceType
        zaber = ZaberDaisyChain("/dev/ttyUSB0",
                                {2: ZaberDeviceType.STAGE,
                                 3: ZaberDeviceType.LED_CONTROLLER,
                                 4: ZaberDeviceType.FILTER_WHEEL})

        # Device names are strings, not int.
        filterwheel = zaber.devices['4']

        # LEDs are not devices of the zaber daisy chain, they are
        # devices of the LED controller.
        led_controller = zaber.devices['3']
        led1 = led_controller.devices['LED1']

        # Stage axis names are the string of the axis number.
        xy_stage = zaber.devices['2']
        motor1 = xy_stage.axes['1']

    Each device on a chain is identified by a device address which is
    an integer between 1 and 99.  By default, the addresses start at 1
    and are sorted by distance to the computer, but this can be
    changed.

    For an LED controller device, the names of its devices are "LED1",
    "LED2", etc, the same as the labels on the LED controller itself.

    Because there is no method to correctly guess a device type, a map
    of device addresses to device types is required.

    .. note::

       Zaber devices need to be homed before they can be moved.  A
       stage will be homed during `enable` but a filter wheel will be
       homed during the object construction.

    """

    def __init__(
        self,
        port: str,
        address2type: typing.Mapping[int, ZaberDeviceType],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._conn = _ZaberConnection(port, baudrate=115200, timeout=0.5)
        self._devices: typing.Dict[str, microscope.abc.Device] = {}

        for address, device_type in address2type.items():
            if address < 1 or address > 99:
                raise ValueError("address must be an integer between 1-99")
            dev_cls = device_type.value
            self._devices[str(address)] = dev_cls(self._conn, address)

    @property
    def devices(self) -> typing.Dict[str, microscope.abc.Device]:
        return self._devices
