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

import threading
import unittest

import Pyro4

import microscope.clients
import microscope.testsuite.devices as dummies


@Pyro4.expose
class PyroService:
    """Simple class to test serving via Pyro.

    We can use one of our own test devices but the idea is to have
    this tests independent from the devices.  We should be able to
    test the Client with any Python object and weird cases, even if we
    don't yet make use of them in the devices.
    """

    def __init__(self):
        self._value = 42  # not exposed

    @property
    def attr(self):  # exposed as 'proxy.attr' remote attribute
        return self._value

    @attr.setter
    def attr(self, value):  # exposed as 'proxy.attr' writable
        self._value = value


@Pyro4.expose
class ExposedDeformableMirror(dummies.TestDeformableMirror):
    """
    Microscope device server is configure to not require @expose but
    this is to test our client with Pyro4's own Daemon.  We need to
    subclass and have the passthrough because the property comes from
    the Abstract Base class, not the TestDeformableMirror class.
    """

    @property
    def n_actuators(self):
        return super().n_actuators


class TestClient(unittest.TestCase):
    def setUp(self):
        self.daemon = Pyro4.Daemon()
        self.thread = threading.Thread(target=self.daemon.requestLoop)

    def tearDown(self):
        self.daemon.shutdown()
        self.thread.join()

    def _serve_objs(self, objs):
        uris = [self.daemon.register(obj) for obj in objs]
        self.thread.start()
        clients = [microscope.clients.Client(uri) for uri in uris]
        return clients

    def test_property_access(self):
        """Test we can read properties via the Client"""
        # list of (object-to-serve, property-name-to-test)
        objs2prop = [
            (PyroService(), "attr"),
            (ExposedDeformableMirror(10), "n_actuators"),
        ]
        clients = self._serve_objs([x[0] for x in objs2prop])
        for client, obj_prop in zip(clients, objs2prop):
            obj = obj_prop[0]
            name = obj_prop[1]
            self.assertTrue(getattr(client, name), getattr(obj, name))

    def test_property_writing(self):
        """Test we can write properties via the Client"""
        obj = PyroService()
        client = (self._serve_objs([obj]))[0]
        self.assertTrue(client.attr, 42)
        client.attr = 10
        self.assertTrue(client.attr, 10)
        self.assertTrue(obj.attr, 10)


if __name__ == "__main__":
    unittest.main()
