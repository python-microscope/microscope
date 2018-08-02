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

import numpy
import six

import microscope.testsuite.devices as dummies

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


if __name__ == '__main__':
  unittest.main()
