#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Tests for the microscope devices settings.
"""

import enum
import unittest

import microscope.devices


class EnumSetting(enum.Enum):
    A = 0
    B = 1
    C = 2


class ThingWithEnum:
    def __init__(self, enum_val):
        self._enum = enum_val

    def set_enum(self, val):
        self._enum = EnumSetting(val)

    def get_enum(self):
        return self._enum


class TestEnumSetting(unittest.TestCase):
    def setUp(self):
        self.thing = ThingWithEnum(EnumSetting(1))

    def test_get_returns_value(self):
        """For enums, get() returns the enum value not the enum instance"""
        foo = microscope.devices.Setting('foo', 'enum', self.thing.get_enum,
                                         self.thing.set_enum, EnumSetting)
        self.assertIsInstance(foo.get(), int)


    def test_get_last_written(self):
        """For enums, """
        foo = microscope.devices.Setting('foo', 'enum', None,
                                         self.thing.set_enum, EnumSetting)
        foo.set(2)
        self.assertIsInstance(foo.get(), int)
        self.assertEqual(EnumSetting(2), self.thing.get_enum())


if __name__ == '__main__':
    unittest.main()
