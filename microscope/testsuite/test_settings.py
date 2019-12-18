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


class ThingWithSomething:
    """Very simple container with setter and getter methods"""
    def __init__(self, val):
        self.val = val

    def set_val(self, val):
        self.val = val

    def get_val(self):
        return self.val


def create_enum_setting(default, with_getter=True, with_setter=True):
    thing = ThingWithSomething(EnumSetting(default))
    getter = thing.get_val if with_getter else None
    setter = thing.set_val if with_setter else None
    setting = microscope.devices._Setting('foobar', 'enum', get_func=getter,
                                          set_func=setter, values=EnumSetting)
    return setting, thing


class TestEnumSetting(unittest.TestCase):

    def test_get_returns_enum_value(self):
        """For enums, get() returns the enum value not the enum instance"""
        setting, thing = create_enum_setting(1)
        self.assertIsInstance(setting.get(), int)

    def test_set_creates_enum(self):
        """For enums, set() sets an enum instance, not the enum value"""
        setting, thing = create_enum_setting(1)
        setting.set(2)
        self.assertIsInstance(thing.val, EnumSetting)
        self.assertEqual(thing.val, EnumSetting(2))

    def test_set_and_get_write_only(self):
        """get() works for write-only enum settings"""
        setting, thing = create_enum_setting(1, with_getter=False)
        self.assertEqual(EnumSetting(1), thing.val)
        setting.set(2)
        self.assertEqual(setting.get(), 2)
        self.assertEqual(EnumSetting(2), thing.val)


if __name__ == '__main__':
    unittest.main()
