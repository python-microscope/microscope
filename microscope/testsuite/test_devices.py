#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>
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

Using lasers as example, there is a :class:`.LaserTests` class full of
`test_*` methods, each of them a test on its own.  For each laser
device supported there is one test class, e.g.,
`TestOmicronDeepstarLaser`, and `TestCoherentSapphireLaser`.  These
subclass from both :class:`unittest.TestCase` and `LaserTests` and
need only to implement `setUp` which sets up the fake and constructs
the device instance required to run the tests.

"""

import unittest
import unittest.mock

import numpy

import microscope.testsuite.devices as dummies
import microscope.testsuite.mock_devices as mocks


class TestSerialMock(unittest.TestCase):
    ## Our tests for serial devices depend on our SerialMock base
    ## class working properly so yeah, we need tests for that too.
    class Serial(mocks.SerialMock):
        eol = b'\r\n'
        def handle(self, command):
            if command.startswith(b'echo '):
                self.in_buffer.write(command[5:] + self.eol)
            elif command in [b'foo', b'bar']:
                pass
            else:
                raise RuntimeError("unknown command '%s'" % command.decode())

    def setUp(self):
        self.serial = TestSerialMock.Serial()
        patcher = unittest.mock.patch.object(TestSerialMock.Serial, 'handle',
                                             wraps=self.serial.handle)
        self.addCleanup(patcher.stop)
        self.mock = patcher.start()

    def test_simple_commands(self):
        self.serial.write(b'foo\r\n')
        self.mock.assert_called_once_with(b'foo')

    def test_partial_commands(self):
        self.serial.write(b'fo')
        self.serial.write(b'o')
        self.serial.write(b'\r\n')
        self.serial.handle.assert_called_once_with(b'foo')

    def test_multiple_commands(self):
        self.serial.write(b'foo\r\nbar\r\n')
        calls = [unittest.mock.call(x) for x in [b'foo', b'bar']]
        self.assertEqual(self.serial.handle.mock_calls, calls)

    def test_unix_eol(self):
        self.serial.eol = b'\n'
        self.serial.write(b'foo\nbar\n')
        calls = [unittest.mock.call(x) for x in [b'foo', b'bar']]
        self.assertEqual(self.serial.handle.mock_calls, calls)

    def test_write(self):
        self.serial.write(b'echo qux\r\n')
        self.assertEqual(self.serial.readline(), b'qux\r\n')


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
        ## TODO: we need to define what happens when enable is called
        ## and device has not been initialised.  See issue #69
        self.device.initialize()
        self.device.enable()
        self.assertTrue(self.device.enabled)
        ## We don't check if it is disabled after shutdown because
        ## some devices can't be turned off.
        ## TODO: add a `has_disabled_state` to the fake so we can
        ## query whether we can check about being disabled.
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

    def test_make_safe_on_initialized(self):
        """Can make safe an initialized device"""
        self.device.initialize()
        self.device.make_safe()

    def test_make_safe_on_enabled(self):
        """Can make safe an enabled device"""
        self.device.initialize()
        self.device.enable()
        self.device.make_safe()

    def test_make_safe_on_disabled(self):
        """Can make safe a disabled device"""
        self.device.initialize()
        self.device.enable()
        self.device.make_safe()

    def test_make_safe_on_shutdown(self):
        """Can make safe a shutdown device"""
        self.device.initialize()
        self.device.enable()
        self.device.disable()
        self.device.shutdown()
        self.device.make_safe()


class SerialDeviceTests:
    def test_connection_defaults(self):
        self.assertEqual(self.device.connection.baudrate, self.fake.baudrate)
        self.assertEqual(self.device.connection.parity, self.fake.parity)
        self.assertEqual(self.device.connection.bytesize, self.fake.bytesize)
        self.assertEqual(self.device.connection.stopbits, self.fake.stopbits)
        self.assertEqual(self.device.connection.rtscts, self.fake.rtscts)
        self.assertEqual(self.device.connection.dsrdtr, self.fake.dsrdtr)


class LaserTests(DeviceTests):
    """Base class for :class:`LaserDevice` tests.

    This class implements all the general laser tests and is meant to
    be mixed with :class:`unittest.TestCase`.  Subclasses must
    implement the `setUp` method which must add two properties:

    `device`
        Instance of the :class:`LaserDevice` implementation being
        tested.

    `fake`
        Object with a multiple attributes that specify the hardware
        and control the tests, such as the device max and min power
        values.  Such attributes may as well be attributes in the
        class that fakes the hardware.

    """
    def assertEqualMW(self, first, second, msg=None):
        ## We could be smarter, but rounding the values should be
        ## enough to check the values when comparing power levels.
        self.assertEqual(round(first), round(second), msg)

    def test_being(self):
        self.assertTrue(self.device.is_alive())

    def test_get_is_on(self):
        self.assertEqual(self.device.connection.light, self.device.get_is_on())
        self.device.enable()
        self.assertEqual(self.device.connection.light, self.device.get_is_on())
        self.device.disable()
        self.assertEqual(self.device.connection.light, self.device.get_is_on())

    def test_off_after_constructor(self):
        ## Some lasers, such as our Coherent Sapphire emit laser
        ## radiation as soon as the key is switched on.  We should
        ## ensure that the laser is turned off during the
        ## construction.
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

    def test_query_power_range(self):
        min_mw = self.device.get_min_power_mw()
        max_mw = self.device.get_max_power_mw()
        self.assertIsInstance(min_mw, float)
        self.assertIsInstance(max_mw, float)
        self.assertEqualMW(min_mw, self.fake.min_power)
        self.assertEqualMW(max_mw, self.fake.max_power)

    def test_power_when_off(self):
        self.device.disable()
        power = self.device.get_power_mw()
        self.assertIsInstance(power, float)
        self.assertEqual(power, 0.0)

    def test_setting_power(self):
        self.device.enable()
        power = self.device.get_power_mw()
        self.assertIsInstance(power, float)
        self.assertEqualMW(power, self.fake.default_power)
        self.assertEqualMW(power, self.device.get_set_power_mw())

        new_power = (self.fake.min_power
                     + ((self.fake.max_power - self.fake.min_power) /2.0))
        self.device.set_power_mw(new_power)
        self.assertEqualMW(self.device.get_power_mw(), new_power)
        self.assertEqualMW(new_power, self.device.get_set_power_mw())

    def test_setting_power_outside_limit(self):
        self.device.enable()
        below_limit = self.fake.min_power - 10.0
        above_limit = self.fake.max_power + 10.0
        self.device.set_power_mw(below_limit)
        self.assertEqualMW(self.device.get_power_mw(),
                           self.device.get_min_power_mw(),
                           'clip setting power to the valid range')
        self.device.set_power_mw(above_limit)
        self.assertEqualMW(self.device.get_power_mw(),
                           self.device.get_max_power_mw(),
                           'clip setting power to the valid range')

    def test_status(self):
        status = self.device.get_status()
        self.assertIsInstance(status, list)
        for msg in status:
            self.assertIsInstance(msg, str)


class CameraTests(DeviceTests):
    pass


class FilterWheelTests(DeviceTests):
    pass


class DeformableMirrorTests(DeviceTests):
    """Collection of test cases for deformable mirrors.

    Should have the following properties defined during `setUp`:
        `planned_n_actuators` (int): number of actuators
        `device` (DeformableMirror): the microscope device instance
        `fake`: an object with the method `get_current_pattern`
    """

    def assertCurrentPattern(self, expected_pattern, msg=''):
        numpy.testing.assert_array_equal(self.fake.get_current_pattern(),
                                         expected_pattern, msg)

    def test_get_number_of_actuators(self):
        self.assertIsInstance(self.device.n_actuators, int)
        self.assertGreater(self.device.n_actuators, 0)
        self.assertEqual(self.device.n_actuators, self.planned_n_actuators)

    def test_applying_pattern(self):
        pattern = numpy.full((self.planned_n_actuators,), 0.2)
        self.device.apply_pattern(pattern)
        self.assertCurrentPattern(pattern)

    def test_out_of_range_pattern(self):
        ## While we expect values in the [0 1] range, we should not
        ## actually be checking for that.
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
        patterns = numpy.zeros((self.planned_n_actuators +1))
        with self.assertRaisesRegex(Exception, "length of second dimension"):
            self.device.apply_pattern(patterns)

    def test_validate_pattern_swapped_dimensions(self):
        patterns = numpy.zeros((self.planned_n_actuators, 1))
        with self.assertRaisesRegex(Exception, "length of second dimension"):
            self.device.apply_pattern(patterns)

    def test_validate_pattern_with_extra_dimension(self):
        patterns = numpy.zeros((2, 1, self.planned_n_actuators))
        with self.assertRaisesRegex(Exception, "dimensions \(must be 1 or 2\)"):
            self.device.apply_pattern(patterns)


class SLMTests(DeviceTests):
    pass


class DSPTests(DeviceTests):
    pass


class TestDummyLaser(unittest.TestCase, LaserTests):
    def setUp(self):
        self.device = dummies.TestLaser()

        ## TODO: we need to rethink the test so this is not needed.
        self.fake = self.device
        self.fake.default_power = self.fake._set_point
        self.fake.min_power = 0.0
        self.fake.max_power = 100.0

    def test_being(self):
        ## TODO: this test uses is_alive but that's actually a method
        ## of SerialDeviceMixIn and not specific to lasers.  It is not
        ## implemented on our dummy laser.  We need to decide what to
        ## do about it.  Is this general enough that should go to all
        ## devices?
        pass

    def test_get_is_on(self):
        ## TODO: this test assumes the connection property to be the
        ## fake.  We need to rethink how the mock lasers work.
        pass


class TestCoherentSapphireLaser(unittest.TestCase, LaserTests,
                                SerialDeviceTests):
    def setUp(self):
        from microscope.lasers.sapphire import SapphireLaser
        from microscope.testsuite.mock_devices import CoherentSapphireLaserMock
        with unittest.mock.patch('microscope.lasers.sapphire.serial.Serial',
                                 new=CoherentSapphireLaserMock):
            self.device = SapphireLaser('/dev/null')
        self.device.initialize()

        self.fake = CoherentSapphireLaserMock


class TestCoboltLaser(unittest.TestCase, LaserTests, SerialDeviceTests):
    def setUp(self):
        from microscope.lasers.cobolt import CoboltLaser
        from microscope.testsuite.mock_devices import CoboltLaserMock
        with unittest.mock.patch('microscope.lasers.cobolt.serial.Serial',
                                 new=CoboltLaserMock):
            self.device = CoboltLaser('/dev/null')
        self.device.initialize()

        self.fake = CoboltLaserMock


class TestOmicronDeepstarLaser(unittest.TestCase, LaserTests,
                               SerialDeviceTests):
    def setUp(self):
        from microscope.lasers.deepstar import DeepstarLaser
        from microscope.testsuite.mock_devices import OmicronDeepstarLaserMock
        with unittest.mock.patch('microscope.lasers.deepstar.serial.Serial',
                                 new=OmicronDeepstarLaserMock):
            self.device = DeepstarLaser('/dev/null')
        self.device.initialize()

        self.fake = OmicronDeepstarLaserMock

    def test_weird_initial_state(self):
        ## The initial state of the laser may not be ideal to actual
        ## turn it on, so test that weird settings are reset to
        ## something adequate.

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
        self.device = dummies.TestCamera()


class TestImageGenerator(unittest.TestCase):
    def test_non_square_patterns_shape(self):
        ## TODO: we should also be testing this via the camera but the
        ## TestCamera is only square.  In the mean time, we only test
        ## directly the _ImageGenerator.
        width = 16
        height = 32
        generator = dummies._ImageGenerator()
        patterns = list(generator.get_methods())
        for i, pattern in enumerate(patterns):
            with self.subTest(pattern):
                generator.set_method(i)
                array = generator.get_image(width, height, 0, 255)
                # In matplotlib, an M-wide by N-tall image has M columns
                # and N rows, so a shape of (N, M)
                self.assertEqual(array.shape, (height, width))


class TestEmptyDummyFilterWheel(unittest.TestCase, FilterWheelTests):
    def setUp(self):
        self.device = dummies.TestFilterWheel()


class TestOneFilterDummyFilterWheel(unittest.TestCase, FilterWheelTests):
    def setUp(self):
        self.device = dummies.TestFilterWheel(filters=[(0, 'DAPI', '430')])

class TestMultiFilterDummyFilterWheel(unittest.TestCase, FilterWheelTests):
    def setUp(self):
        self.device = dummies.TestFilterWheel(filters=[(0, 'DAPI', '430'),
                                                       (1, 'GFP', '580'),])

class TestEmptySixPositionFilterWheel(unittest.TestCase, FilterWheelTests):
    def setUp(self):
        self.device = dummies.TestFilterWheel(positions=6)

class TestDummyDeformableMirror(unittest.TestCase, DeformableMirrorTests):
    def setUp(self):
        self.planned_n_actuators = 86
        self.device = dummies.TestDeformableMirror(self.planned_n_actuators)
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
        it fails if there's a typo on the argument.  See issue #84.
        """
        filters = [(0, 'DAPI', '430')]
        dummies.TestFilterWheel(filters=filters)
        ## XXX: Device.__del__ calls shutdown().  However, if __init__
        ## failed the device is not complete and shutdown() fails
        ## because the logger has not been created.  See comments on
        ## issue #69.  patch __del__ to workaround this issue.
        with unittest.mock.patch('microscope.devices.Device.__del__'):
            with self.assertRaisesRegex(TypeError, "argument 'filteres'"):
                dummies.TestFilterWheel(filteres=filters)


if __name__ == '__main__':
    unittest.main()
