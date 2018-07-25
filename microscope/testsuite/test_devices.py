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

import unittest
import unittest.mock

import numpy
import serial
import six

import microscope.testsuite.devices as dummies
import microscope.testsuite.mock_devices as mocks


class TestDeformableMirror(unittest.TestCase):
  def setUp(self):
    self.planned_n_actuators = 10
    self.pattern = numpy.zeros((self.planned_n_actuators))
    self.dm = dummies.TestDeformableMirror(self.planned_n_actuators)

  def test_number_of_actuators(self):
    self.assertEqual(self.dm.n_actuators, self.planned_n_actuators)

  def test_applying_pattern(self):
    ## This mainly checks the implementation of the dummy device.  It
    ## is not that important but it is the basis to trust the other
    ## tests wich will actually test the base class.
    self.pattern[:] = 0.2
    self.dm.apply_pattern(self.pattern)
    numpy.testing.assert_array_equal(self.dm._current_pattern, self.pattern)

  def test_out_of_range_pattern(self):
    ## While we expect values in the [0 1] range, we should not
    ## actually be checking for that.
    for v in [-1000, -1, 0, 1, 3]:
      self.pattern[:] = v
      self.dm.apply_pattern(self.pattern)
      numpy.testing.assert_array_equal(self.dm._current_pattern, self.pattern)

  def test_software_triggering(self):
    n_patterns = 5
    patterns = numpy.random.rand(n_patterns, self.planned_n_actuators)
    self.dm.queue_patterns(patterns)
    for i in range(n_patterns):
      self.dm.next_pattern()
      numpy.testing.assert_array_equal(self.dm._current_pattern, patterns[i,:])

  def test_validate_pattern(self):
    ## Pattern too long.
    patterns = numpy.zeros((self.planned_n_actuators +1))
    with six.assertRaisesRegex(self, Exception,
                               "length of second dimension"):
      self.dm.apply_pattern(patterns)

    ## Swapped dimensions.
    patterns = numpy.zeros((self.planned_n_actuators, 1))
    with six.assertRaisesRegex(self, Exception,
                               "length of second dimension"):
      self.dm.apply_pattern(patterns)

    ## One dimension too many.
    patterns = numpy.zeros((2, 1, self.planned_n_actuators))
    with six.assertRaisesRegex(self, Exception,
                               "dimensions \(must be 1 or 2\)"):
      self.dm.apply_pattern(patterns)


class TestSerialMock(unittest.TestCase):
  ## Our tests for serial devices depend on our SerialMock base class
  ## working properly so yeah, we need tests for that too.
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


class TestCoherentSapphireLaser(unittest.TestCase):
  def setUp(self):
    from microscope.lasers.sapphire import SapphireLaser
    from microscope.testsuite.mock_devices import CoherentSapphireLaserMock
    with unittest.mock.patch('microscope.lasers.sapphire.serial.Serial',
                             new=CoherentSapphireLaserMock):
      self.laser = SapphireLaser('/dev/null')

  def test_connection_defaults(self):
    self.assertEqual(self.laser.connection.baudrate, 19200)
    self.assertEqual(self.laser.connection.parity, serial.PARITY_NONE)
    self.assertEqual(self.laser.connection.bytesize, serial.EIGHTBITS)
    self.assertEqual(self.laser.connection.stopbits, serial.STOPBITS_ONE)
    self.assertEqual(self.laser.connection.rtscts, False)
    self.assertEqual(self.laser.connection.dsrdtr, False)

  def test_being(self):
     self.assertTrue(self.laser.is_alive())

  def test_turning_on_and_off(self):
     self.assertTrue(self.laser.get_is_on())
     self.laser.disable()
     self.assertFalse(self.laser.get_is_on())
     self.laser.enable()
     self.assertTrue(self.laser.get_is_on())

  def test_query_power_range(self):
    min_mw = self.laser.get_min_power_mw()
    max_mw = self.laser.get_max_power_mw()
    self.assertIsInstance(min_mw, float)
    self.assertIsInstance(max_mw, float)
    self.assertEqual(round(min_mw), 20.0)
    self.assertEqual(round(max_mw), 220.0)

  def test_setting_power(self):
    power = self.laser.get_power_mw()
    self.assertIsInstance(power, float)
    self.assertEqual(round(power), 50.0)
    self.laser.set_power_mw(100.0)
    self.assertEqual(round(self.laser.get_power_mw()), 100.0)

  def test_setting_power_outside_limit(self):
    self.laser.set_power_mw(5)
    self.assertEqual(self.laser.get_power_mw(), self.laser.get_min_power_mw(),
                     'clip setting power to the valid range')
    self.laser.set_power_mw(250)
    self.assertEqual(self.laser.get_power_mw(), self.laser.get_max_power_mw(),
                     'clip setting power to the valid range')

if __name__ == '__main__':
  unittest.main()
