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

"""Test all the concrete device classes.

We have the same tests for all devices of the same type.  To do this,
there is a :class:`unittest.TestCase` class for each device that
subclasses from that device type class of tests.  Each such class only
needs to implement the `setUp` method.  It may also add device
specific tests.

Using lasers as example, there is a :class:`.LightSourceTests` class
full of `test_*` methods, each of them a test on its own.  For each
light source device supported there is one test class, e.g.,
`TestOmicronDeepstarLaser`, and `TestCoherentSapphireLaser`.  These
subclass from both :class:`unittest.TestCase` and `LightSourceTests`
and need only to implement `setUp` which sets up the fake and
constructs the device instance required to run the tests.

"""

import unittest
import unittest.mock

import numpy

import microscope.testsuite.devices as dummies
import microscope.testsuite.mock_devices as mocks
from microscope import simulators


class TestSerialMock(unittest.TestCase):
    # Our tests for serial devices depend on our SerialMock base
    # class working properly so yeah, we need tests for that too.
    class Serial(mocks.SerialMock):
        eol = b"\r\n"

        def handle(self, command):
            if command.startswith(b"echo "):
                self.in_buffer.write(command[5:] + self.eol)
            elif command in [b"foo", b"bar"]:
                pass
            else:
                raise RuntimeError("unknown command '%s'" % command.decode())

    def setUp(self):
        self.serial = TestSerialMock.Serial()
        patcher = unittest.mock.patch.object(
            TestSerialMock.Serial, "handle", wraps=self.serial.handle
        )
        self.addCleanup(patcher.stop)
        self.mock = patcher.start()

    def test_simple_commands(self):
        self.serial.write(b"foo\r\n")
        self.mock.assert_called_once_with(b"foo")

    def test_partial_commands(self):
        self.serial.write(b"fo")
        self.serial.write(b"o")
        self.serial.write(b"\r\n")
        self.serial.handle.assert_called_once_with(b"foo")

    def test_multiple_commands(self):
        self.serial.write(b"foo\r\nbar\r\n")
        calls = [unittest.mock.call(x) for x in [b"foo", b"bar"]]
        self.assertEqual(self.serial.handle.mock_calls, calls)

    def test_unix_eol(self):
        self.serial.eol = b"\n"
        self.serial.write(b"foo\nbar\n")
        calls = [unittest.mock.call(x) for x in [b"foo", b"bar"]]
        self.assertEqual(self.serial.handle.mock_calls, calls)

    def test_write(self):
        self.serial.write(b"echo qux\r\n")
        self.assertEqual(self.serial.readline(), b"qux\r\n")


class DeviceTests:
    """Tests cases for all devices.

    This collection of tests cover the very basic behaviour of
    devices,stuff like initialising and enabling the device.  Classes
    of tests specific to each device type should subclass from it.

    Subclasses must define a `device` property during `setUp`, an
    instance of :class:`Device`.

    """

    def test_on_and_off(self):
        """Device can be turned on and off"""
        self.device.initialize()
        self.device.shutdown()

    def test_enable_and_disable(self):
        # TODO: we need to define what happens when enable is called
        # and device has not been initialised.  See issue #69
        self.device.initialize()
        self.device.enable()
        self.assertTrue(self.device.enabled)
        # We don't check if it is disabled after shutdown because
        # some devices can't be turned off.
        # TODO: add a `has_disabled_state` to the fake so we can
        # query whether we can check about being disabled.
        self.device.disable()
        self.device.shutdown()

    def test_enable_enabled(self):
        """Handles enabling of an already enabled device"""
        self.device.initialize()
        self.device.enable()
        self.assertTrue(self.device.enabled)
        self.device.enable()
        self.assertTrue(self.device.enabled)

    def test_disable_disabled(self):
        """Handles disabling of an already disabled device.

        Test disabling twice, both before and after enabling it for
        the first time.
        """
        self.device.initialize()
        self.device.disable()
        self.device.disable()
        self.device.enable()
        self.assertTrue(self.device.enabled)
        self.device.disable()
        self.device.disable()


class SerialDeviceTests:
    def test_connection_defaults(self):
        self.assertEqual(self.device.connection.baudrate, self.fake.baudrate)
        self.assertEqual(self.device.connection.parity, self.fake.parity)
        self.assertEqual(self.device.connection.bytesize, self.fake.bytesize)
        self.assertEqual(self.device.connection.stopbits, self.fake.stopbits)
        self.assertEqual(self.device.connection.rtscts, self.fake.rtscts)
        self.assertEqual(self.device.connection.dsrdtr, self.fake.dsrdtr)


class LightSourceTests(DeviceTests):
    """Base class for :class:`LightSource` tests.

    This class implements all the general laser tests and is meant to
    be mixed with :class:`unittest.TestCase`.  Subclasses must
    implement the `setUp` method which must add two properties:

    `device`
        Instance of the :class:`LightSource` implementation being
        tested.

    `fake`
        Object with a multiple attributes that specify the hardware
        and control the tests, such as the device max and min power
        values.  Such attributes may as well be attributes in the
        class that fakes the hardware.

    """

    def assertEqualMW(self, first, second, msg=None):
        # We could be smarter, but rounding the values should be
        # enough to check the values when comparing power levels.
        self.assertEqual(round(first), round(second), msg)

    def test_get_is_on(self):
        self.assertEqual(self.device.connection.light, self.device.get_is_on())
        self.device.enable()
        self.assertEqual(self.device.connection.light, self.device.get_is_on())
        self.device.disable()
        self.assertEqual(self.device.connection.light, self.device.get_is_on())

    def test_off_after_constructor(self):
        # Some lasers, such as our Coherent Sapphire emit laser
        # radiation as soon as the key is switched on.  We should
        # ensure that the laser is turned off during the
        # construction.
        self.assertFalse(self.device.get_is_on())

    def test_turning_on_and_off(self):
        self.device.enable()
        self.assertTrue(self.device.get_is_on())
        self.device.disable()
        self.assertFalse(self.device.get_is_on())

    def test_shutdown(self):
        self.device.enable()
        self.device.disable()
        self.device.shutdown()

    def test_power_when_off(self):
        self.device.disable()
        self.assertIsInstance(self.device.power, float)
        self.assertEqual(self.device.power, 0.0)

    def test_setting_power(self):
        self.device.enable()
        self.assertIsInstance(self.device.power, float)
        power_mw = self.device.power * self.fake.max_power
        self.assertEqualMW(power_mw, self.fake.default_power)
        self.assertEqualMW(self.device.power, self.device.get_set_power())

        new_power = 0.5
        new_power_mw = new_power * self.fake.max_power
        self.device.power = new_power
        self.assertEqualMW(
            self.device.power * self.fake.max_power, new_power_mw
        )
        self.assertEqualMW(new_power, self.device.get_set_power())

    def test_setting_power_outside_limit(self):
        self.device.enable()
        self.device.power = -0.1
        self.assertEqual(
            self.device.power,
            self.fake.min_power / self.fake.max_power,
            "clip setting power below 0",
        )
        self.device.power = 1.1
        self.assertEqual(self.device.power, 1.0, "clip setting power above 1")

    def test_status(self):
        status = self.device.get_status()
        self.assertIsInstance(status, list)
        for msg in status:
            self.assertIsInstance(msg, str)


class CameraTests(DeviceTests):
    pass


class ControllerTests(DeviceTests):
    pass


class FilterWheelTests(DeviceTests):
    def test_get_and_set_position(self):
        self.assertEqual(self.device.position, 0)
        max_pos = self.device.n_positions - 1
        self.device.position = max_pos
        self.assertEqual(self.device.position, max_pos)

    def test_set_position_to_negative(self):
        with self.assertRaisesRegex(Exception, "can't move to position"):
            self.device.position = -1

    def test_set_position_above_limit(self):
        with self.assertRaisesRegex(Exception, "can't move to position"):
            self.device.position = self.device.n_positions


class DeformableMirrorTests(DeviceTests):
    """Collection of test cases for deformable mirrors.

    Should have the following properties defined during `setUp`:
        `planned_n_actuators` (int): number of actuators
        `device` (DeformableMirror): the microscope device instance
        `fake`: an object with the method `get_current_pattern`
    """

    def assertCurrentPattern(self, expected_pattern, msg=""):
        numpy.testing.assert_array_equal(
            self.fake.get_current_pattern(), expected_pattern, msg
        )

    def test_get_number_of_actuators(self):
        self.assertIsInstance(self.device.n_actuators, int)
        self.assertGreater(self.device.n_actuators, 0)
        self.assertEqual(self.device.n_actuators, self.planned_n_actuators)

    def test_applying_pattern(self):
        pattern = numpy.full((self.planned_n_actuators,), 0.2)
        self.device.apply_pattern(pattern)
        self.assertCurrentPattern(pattern)

    def test_out_of_range_pattern(self):
        # While we expect values in the [0 1] range, we should not
        # actually be checking for that.
        pattern = numpy.zeros((self.planned_n_actuators,))
        for v in [-1000, -1, 0, 1, 3]:
            pattern[:] = v
            self.device.apply_pattern(pattern)
            self.assertCurrentPattern(pattern)

    def test_software_triggering(self):
        n_patterns = 5
        patterns = numpy.random.rand(n_patterns, self.planned_n_actuators)
        self.device.queue_patterns(patterns)
        for i in range(n_patterns):
            self.device.next_pattern()
            self.assertCurrentPattern(patterns[i])

    def test_validate_pattern_too_long(self):
        patterns = numpy.zeros((self.planned_n_actuators + 1))
        with self.assertRaisesRegex(Exception, "length of second dimension"):
            self.device.apply_pattern(patterns)

    def test_validate_pattern_swapped_dimensions(self):
        patterns = numpy.zeros((self.planned_n_actuators, 1))
        with self.assertRaisesRegex(Exception, "length of second dimension"):
            self.device.apply_pattern(patterns)

    def test_validate_pattern_with_extra_dimension(self):
        patterns = numpy.zeros((2, 1, self.planned_n_actuators))
        with self.assertRaisesRegex(
            Exception, "dimensions \\(must be 1 or 2\\)"
        ):
            self.device.apply_pattern(patterns)


class SLMTests(DeviceTests):
    pass


class DSPTests(DeviceTests):
    pass


class TestDummyLightSource(unittest.TestCase, LightSourceTests):
    def setUp(self):
        self.device = simulators.SimulatedLightSource()

        # TODO: we need to rethink the test so this is not needed.
        self.fake = self.device
        self.fake.default_power = self.fake._set_point
        self.fake.min_power = 0.0
        self.fake.max_power = 100.0

    def test_get_is_on(self):
        # TODO: this test assumes the connection property to be the
        # fake.  We need to rethink how the mock lasers work.
        pass


class TestCoherentSapphireLaser(
    unittest.TestCase, LightSourceTests, SerialDeviceTests
):
    def setUp(self):
        from microscope.lights.sapphire import SapphireLaser
        from microscope.testsuite.mock_devices import CoherentSapphireLaserMock

        with unittest.mock.patch(
            "microscope.lights.sapphire.serial.Serial",
            new=CoherentSapphireLaserMock,
        ):
            self.device = SapphireLaser("/dev/null")
        self.device.initialize()

        self.fake = CoherentSapphireLaserMock


class TestCoboltLaser(unittest.TestCase, LightSourceTests, SerialDeviceTests):
    def setUp(self):
        from microscope.lights.cobolt import CoboltLaser
        from microscope.testsuite.mock_devices import CoboltLaserMock

        with unittest.mock.patch(
            "microscope.lights.cobolt.serial.Serial", new=CoboltLaserMock
        ):
            self.device = CoboltLaser("/dev/null")
        self.device.initialize()

        self.fake = CoboltLaserMock


class TestOmicronDeepstarLaser(
    unittest.TestCase, LightSourceTests, SerialDeviceTests
):
    def setUp(self):
        from microscope.lights.deepstar import DeepstarLaser
        from microscope.testsuite.mock_devices import OmicronDeepstarLaserMock

        with unittest.mock.patch(
            "microscope.lights.deepstar.serial.Serial",
            new=OmicronDeepstarLaserMock,
        ):
            self.device = DeepstarLaser("/dev/null")
        self.device.initialize()

        self.fake = OmicronDeepstarLaserMock

    def test_weird_initial_state(self):
        # The initial state of the laser may not be ideal to actual
        # turn it on, so test that weird settings are reset to
        # something adequate.

        self.device.connection.internal_peak_power = False
        self.device.connection.bias_modulation = True
        self.device.connection.digital_modulation = True
        self.device.connection.analog2digital = True

        self.device.enable()
        self.assertTrue(self.device.get_is_on())

        self.assertTrue(self.device.connection.internal_peak_power)
        self.assertFalse(self.device.connection.bias_modulation)
        self.assertFalse(self.device.connection.digital_modulation)
        self.assertFalse(self.device.connection.analog2digital)


class TestDummyCamera(unittest.TestCase, CameraTests):
    def setUp(self):
        self.device = simulators.SimulatedCamera()


class TestImageGenerator(unittest.TestCase):
    def test_non_square_patterns_shape(self):
        # TODO: we should also be testing this via the camera but the
        # TestCamera is only square.  In the mean time, we only test
        # directly the _ImageGenerator.
        width = 16
        height = 32
        generator = simulators._ImageGenerator()
        patterns = list(generator.get_methods())
        for i, pattern in enumerate(patterns):
            with self.subTest(pattern):
                generator.set_method(i)
                array = generator.get_image(width, height, 0, 255)
                # In matplotlib, an M-wide by N-tall image has M columns
                # and N rows, so a shape of (N, M)
                self.assertEqual(array.shape, (height, width))


class TestDummyController(unittest.TestCase, ControllerTests):
    def setUp(self):
        self.laser = simulators.SimulatedLightSource()
        self.filterwheel = simulators.SimulatedFilterWheel(positions=6)
        self.device = simulators.SimulatedController(
            {"laser": self.laser, "filterwheel": self.filterwheel}
        )

    def test_device_names(self):
        self.assertSetEqual(
            {"laser", "filterwheel"}, set(self.device.devices.keys())
        )

    def test_control_filterwheel(self):
        self.assertEqual(self.device.devices["filterwheel"].position, 0)
        self.device.devices["filterwheel"].position = 2
        self.assertEqual(self.device.devices["filterwheel"].position, 2)

    def test_control_laser(self):
        self.assertEqual(self.device.devices["laser"].power, 0.0)
        self.device.devices["laser"].enable()
        self.device.devices["laser"].power = 0.8
        self.assertEqual(self.device.devices["laser"].power, 0.8)


class TestEmptyDummyFilterWheel(unittest.TestCase):
    def test_zero_positions(self):
        with self.assertRaisesRegex(
            ValueError, "positions must be a positive number"
        ):
            simulators.SimulatedFilterWheel(positions=0)


class TestOnePositionFilterWheel(unittest.TestCase, FilterWheelTests):
    def setUp(self):
        self.device = simulators.SimulatedFilterWheel(positions=1)


class TestSixPositionFilterWheel(unittest.TestCase, FilterWheelTests):
    def setUp(self):
        self.device = simulators.SimulatedFilterWheel(positions=6)


class TestDummyDeformableMirror(unittest.TestCase, DeformableMirrorTests):
    def setUp(self):
        self.planned_n_actuators = 86
        self.device = simulators.SimulatedDeformableMirror(
            self.planned_n_actuators
        )
        self.fake = self.device


class TestDummySLM(unittest.TestCase, SLMTests):
    def setUp(self):
        self.device = dummies.DummySLM()


class TestDummyDSP(unittest.TestCase, DSPTests):
    def setUp(self):
        self.device = dummies.DummyDSP()


class TestBaseDevice(unittest.TestCase):
    def test_unexpected_kwargs_raise_exception(self):
        """Unexpected kwargs on constructor raise exception.

        Test first that we can construct the device.  Then test that
        it fails if there are unused kwargs.  This is an issue when
        there are default arguments, there's a typo on the argument
        name, and the class uses the default instead of an error.  See
        issue #84.
        """
        simulators.SimulatedLightSource()
        # XXX: Device.__del__ calls shutdown().  However, if __init__
        # failed the device is not complete and shutdown() fails
        # because the logger has not been created.  See comments on
        # issue #69.  patch __del__ to workaround this issue.
        with unittest.mock.patch("microscope.devices.Device.__del__"):
            with self.assertRaisesRegex(TypeError, "argument 'power'"):
                simulators.SimulatedLightSource(power=2)


if __name__ == "__main__":
    unittest.main()
