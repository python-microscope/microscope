#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""TODO: complete this docstring
"""
import inspect
import itertools
import queue
import socket
import threading

import Pyro4

# Pyro configuration. Use pickle because it can serialize numpy ndarrays.
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'

LISTENERS = {}


class Client:
    """Base Client object that makes methods on proxy available locally."""
    def __init__(self, url):
        self._url = url
        self._proxy = None
        self._connect()

    def _connect(self):
        """Connect to a proxy and set up self passthrough to proxy methods."""
        self._proxy = Pyro4.Proxy(self._url)
        self._proxy._pyroGetMetadata()

        # Derived classes may over-ride some methods. Leave these alone.
        my_methods = [m[0] for m in inspect.getmembers(self, predicate=inspect.ismethod)]
        methods = set(self._proxy._pyroMethods).difference(my_methods)
        # But in the case of propertyes, we need to inspect the class.
        my_properties = [m[0] for m in inspect.getmembers(self.__class__, predicate=inspect.isdatadescriptor)]
        properties = set(self._proxy._pyroAttrs).difference(my_properties)

        for attr in itertools.chain(methods, properties):
            setattr(self, attr, getattr(self._proxy, attr))


class DataClient(Client):
    """A client that can receive and buffer data."""
    def __init__(self, url):
        super().__init__(url)
        self._buffer = queue.Queue()
        # Register self with a listener.
        if self._url.split('@')[1].split(':')[0] in ['127.0.0.1', 'localhost']:
            iface = '127.0.0.1'
        else:
            # TODO: support multiple interfaces. Could use ifaddr.get_adapters() to
            # query ip addresses then pick first interface on the same subnet.
            iface = socket.gethostbyname(socket.gethostname())
        if iface not in LISTENERS:
            LISTENERS[iface] = Pyro4.Daemon(host=iface)
            lthread = threading.Thread(target=LISTENERS[iface].requestLoop)
            lthread.daemon = True
            lthread.start()
        self._client_uri = LISTENERS[iface].register(self)

    def enable(self):
        """Set the client on the remote and enable it."""
        self.set_client(self._client_uri)
        self._proxy.enable()


    @Pyro4.expose
    @Pyro4.oneway
    # noinspection PyPep8Naming
    # Legacy naming convention.
    def receiveData(self, data, timestamp, *args):
        self._buffer.put((data, timestamp))


    def trigger_and_wait(self):
        if not hasattr(self, 'soft_trigger'):
            raise Exception("Device has no soft_trigger method.")
        self.soft_trigger()
        return self._buffer.get(block=True)
