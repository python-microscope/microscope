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

"""Classes for remote control of microscope components."""
import Pyro4
import multiprocessing
import numpy as np
import Queue
from threading import Thread
import time


class Remote(object):
    def __init__(self):
        self.enabled = None


    def enable(self):
        self.enabled = True


    def disable(self):
        self.enabled = False


    def shutdown(self):
        self.enabled = False


    def abort(self):
        pass


    def make_safe(self):
        pass


    def get_settings(self):
        pass


    def update_settings(self, settings):
        pass


class DataRemote(Remote):
    """A data capture device.

    This class handles a thread to fetch data from a device and dispatch
    it to a client.  The client is set using set_client(uri) or (legacy)
    receiveClient(uri).
    Derived classed should implement:
        _get_data(self)            ---  required
        _process_data(self, data)  ---  optional
    Derived classes may override __init__, enable and disable, but must
    ensure to call this class's implementations as indicated in the docstrings.
    """
    def __init__(self, buffer_length=0):
        """Derived.__init__ must call this at some point."""
        super(DataRemote, self).__init__()
        # A length-1 buffer for fetching data.
        self._data = None
        # A thread to fetch and dispatch data.
        self._fetch_thread = None
        # A flag to control the _fetch_thread.
        self._fetch_thread_run = False
        # A client to which we send data.
        self._client = None
        # A thread to dispatch data.
        self._dispatch_thread = None
        # A buffer for data dispatch.
        self._buffer = Queue.Queue(maxsize = buffer_length)


    def __del__(self):
        self.disable()


    def enable(self):
        """Enable the data capture device.

        Ensures that a data handling threads are running.
        Derived.enable must set up a self._data array to receive data,
        then call this after any other processing."""
        if not self._fetch_thread or not self._fetch_thread.is_alive():
            self._fetch_thread = Thread(target=self._fetch_loop)
            self._fetch_thread.daemon = True
            self._fetch_thread.start()
        if not self._dispatch_thread or not self._dispatch_thread.is_alive():
            self._dispatch_thread = Thread(target=self._dispatch_loop)
            self._dispatch_thread.daemon = True
            self._dispatch_thread.start()
        super(DataRemote, self).enable()


    def disable(self):
        """Disable the data capture device.

        Derived.disable must call this at some point."""
        self.enabled = False
        if self._fetch_thread:
            if self._fetch_thread.is_alive():
                self._fetch_thread_run = False
                self._fetch_thread.join()
        super(DataRemote, self).disable()


    def _get_data(self):
        """Poll for data

        If data is fetched, store it in self._data and return True; otherwise
        return False."""
        raise NotImplementedError
        self._data = None
        return False


    def _process_data(self, data):
        """Do any data processing prior to sending to client and return data."""
        return data


    def _send_data(self, data, timestamp):
        """Dispatch data to the client."""
        if self._client:
            try:
                # Currently uses legacy receiveData. Would like to pass
                # this function name as an argument to set_client, but
                # not sure to subsequently resolve this over Pyro.
                self._client.receiveData(data, timestamp)
            except Pyro4.errors.ConnectionClosedError:
                # Nothing is listening
                self._client = None
            except:
                raise


    def _dispatch_loop(self):
        while True:
            if self._buffer.empty():
                time.sleep(0.01)
                continue
            timestamp, data = self._buffer.get()
            self._send_data(self._process_data(data), timestamp)
            self._buffer.task_done()


    def _fetch_loop(self):
        """Poll source for data and put into buffer."""
        self._fetch_thread_run = True
        while self._fetch_thread_run:
            if self._get_data():
                timestamp = time.time()
                self._buffer.put((timestamp, self._data.copy()))
            else:
                time.sleep(0.001)


    def set_client(self, client_uri):
        """Set up a connection to our client."""
        self._client = Pyro4.Proxy(client_uri)


    def receiveClient(self, client_uri):
        """A passthrough for compatibility."""
        self.set_client(client_uri)


class CameraRemote(DataRemote):
    def __init__(self):
        # A tuple defining data shape.
        self.dshape = None
        # A data type.
        self.dtype = None
        self.dtransform = None
        super(CameraRemote, self).__init__()


    def get_exposure_time(self):
        pass