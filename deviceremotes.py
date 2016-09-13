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
import abc
import multiprocessing
import numpy as np
from collections import OrderedDict
import Pyro4
import Queue
from threading import Thread
import time


class Remote(object):
    #__metaclass__ = abc.ABCMeta
    def __init__(self):
        print "__init__"
        self.enabled = None
        # A list of settings. (Can't serialize OrderedDict, so use {}.)
        self.settings = OrderedDict()


    def __del__(self):
        print "__del__"
        self.shutdown()


    def add_setting(self, name, dtype, get_func, set_func, values, adv=False):
        """Add a setting definition.

        :param name: the setting's name
        :param dtype: a data type from ('int', 'float', 'bool', 'enum', 'str')
        :param get_func: a function to get the current value
        :param set_func: a function to set the value
        :param values: a description of allowed values dependent on dtype
        :param adv: is this an advanced setting?
        """

        # Mapping of dtype to type(values)
        DTYPES = {'int':tuple,
                  'float':tuple,
                  'bool':type(None),
                  'enum':list,
                  'str':int}
        if dtype not in DTYPES:
            raise Exception('Unsupported dtype.')
        elif not isinstance(values, DTYPES[dtype]):
            raise Exception('Invalid values type for %s: expected %s' %
                            (dtype, DTYPES[dtype]))
        else:
            self.settings.update({name:{'type':dtype,
                                        'get':get_func,
                                        'set':set_func,
                                        'values':values,
                                        'current':None,
                                        'advanced':adv}})


    @Pyro4.expose
    def get_some_dict(self):
        return {'a':1, 'b':2}


    @abc.abstractmethod
    @Pyro4.expose
    def disable(self):
        """Disable the device for a short period for inactivity."""
        self.enabled = False


    @abc.abstractmethod
    @Pyro4.expose
    def enable(self):
        """Enable the device."""
        self.enabled = True

    @abc.abstractmethod
    @Pyro4.expose
    def get_id(self):
        """Return a unique hardware identifier, such as a serial number."""
        pass


    @Pyro4.expose
    def get_settings(self):
        """Return the dict of settings as list of tuples."""
        return [s for s in self.settings.iteritems()]


    @abc.abstractmethod
    @Pyro4.expose
    def initialize(self, *args, **kwargs):
        """Initialize the device."""
        print "initialize"
        self.add_setting('thing', 'int', None, None, (0, 100))


    @abc.abstractmethod
    @Pyro4.expose
    def make_safe(self):
        """Put the device into a safe state."""
        pass


    @abc.abstractmethod
    @Pyro4.expose
    def shutdown(self):
        """Shutdown the device for a prolonged period of inactivity."""
        print "shutdown"
        self.enabled = False

    @Pyro4.expose
    def update_settings(self, settings, init=False):
        """Update settings based on dict of settings and values."""
        if init:
            # Assume nothing about state: set everything.
            my_keys = set(self.settings.keys())
            their_keys = set(settings.keys())
            update_keys = my_keys | their_keys
        else:
            # Only update changed values.
            my_keys = set(self.settings.keys())
            their_keys = set(settings.keys())
            update_keys = set(key for key in my_keys & their_keys
                              if self.settings[key]['current'] != settings[key]['current'])
        results = {}
        # Update values.
        for key in update_keys:
            if key not in my_keys or not self.settings[key]['set']:
                # Setting not recognised or no set function implemented
                result[key] = NotImplemented
                update_keys.remove(key)
                continue
            self.settings[key]['set'](settings[key])
        # Read back values in second loop.
        for key in update_keys:
            results[key] = settings[key]['get']()
        return results


class DataRemote(Remote):
    """A data capture device.

    This class handles a thread to fetch data from a device and dispatch
    it to a client.  The client is set using set_client(uri) or (legacy)
    receiveClient(uri).
    Derived classed should implement:
        abort(self)                ---  required
        start_acquisition(self)    ---  required
        _fetch_data(self)          ---  required
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
        # A flag to indicate if device is ready to acquire.
        self._acquiring = False


    def __del__(self):
        self.disable()


    @abc.abstractmethod
    @Pyro4.expose
    def abort(self):
        """Stop acquisition as soon as possible."""
        self._acquiring = False


    @abc.abstractmethod
    @Pyro4.expose
    def start_aquisition(self):
        """Start acquisition."""
        self._acquiring = True


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


    @abc.abstractmethod
    def _fetch_data(self):
        """Poll for data

        If data is fetched, store it in self._data and return True; otherwise
        return False."""
        pass


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
            if self._fetch_data():
                timestamp = time.time()
                self._buffer.put((timestamp, self._data.copy()))
            else:
                time.sleep(0.001)


    @Pyro4.expose
    def set_client(self, client_uri):
        """Set up a connection to our client."""
        self._client = Pyro4.Proxy(client_uri)


    def update_settings(self, settings, init=False):
        """Update settings, toggling acquisition if necessary."""
        was_acquiring = self.acquiring
        if was_acquiring:
            self.abort()
        super(DataRemote, self).update_settings(settings, init)
        if was_acquiring:
            self.start_aquisition()


    @Pyro4.expose
    def receiveClient(self, client_uri):
        """A passthrough for compatibility."""
        self.set_client(client_uri)


class CameraRemote(DataRemote):
    """Adds functionality to DataRemote to support cameras.

    Applies a transform to acquired data in the processing step.
    Defines the interface for cameras.
    Must implement _fetch_data as per DataRemote._fetch_data."""
    def __init__(self):
        # A tuple defining data shape.
        self.dshape = None
        # A data type.
        self.dtype = None
        # A transform to apply to data (fliplr, flipud, rot90)
        self.dtransform = (0, 0, 0)
        super(CameraRemote, self).__init__()
        self.some_setting = 0.
        #self.settings.append()


    def _process_data(self, data):
        """Apply self.dtransform to data."""
        flips = (self.transform[0], self.transform[1])
        rot = self.transform[2]

        return {(0,0): numpy.rot90(data, rot),
                (0,1): numpy.flipud(numpy.rot90(data, rot)),
                (1,0): numpy.fliplr(numpy.rot90(data, rot)),
                (1,1): numpy.fliplr(numpy.flipud(numpy.rot90(data, rot)))
                }[flips]


    @abc.abstractmethod
    @Pyro4.expose
    def get_exposure_time(self):
        pass


    def set_some_setting(self, value):
        self.some_setting = value


    def get_some_setting(self, value):
        return self.some_setting


class RemoteServer(multiprocessing.Process):
    def __init__(self, term_event, remote_class, id_to_host, id_to_port, index=0):
        """Initialise a remote and serve at host/port according to its id.

        :param remoteClass: class to serve
        :param id_to_host:  mapping of device identifiers to hostname
        :param id_to_port:  mapping of device identifiers to port number
        :param index:  device index if serving multiple devices of same type."""
        self._index = index
        self._id_to_host = id_to_host
        self._id_to_port = id_to_port
        # The device to serve.
        self._remote = None
        self._remote_class = remote_class
        # A shared event to allow clean shutdown.
        self.term_event = term_event
        super(RemoteServer, self).__init__()
        self.daemon = True


    def run(self):
        self._remote = self._remote_class()
        while True:
            try:
                self._remote.initialize(self._index)
            except:
                time.sleep(5)
            else:
                break
        uid = (self._remote_class, self._remote.get_id())
        if uid not in self._id_to_host or uid not in self._id_to_port:
            raise Exception("Host or port not found for device "
                            "with id %s." % uid)
        host = self._id_to_host[uid]
        port = self._id_to_port[uid]
        pyro_daemon = Pyro4.Daemon(port=port, host=host)
        # Run the Pyro daemon in a separate thread so that we can do
        # clean shutdown under Windows.
        pyro_thread = Thread(target=Pyro4.Daemon.serveSimple,
                                   args=({self._remote: 'REMOTE'},),
                                   kwargs={'daemon':pyro_daemon, 'ns':False})
        pyro_thread.daemon = True
        pyro_thread.start()
        # This tread waits for the termination event.
        try:
            self.term_event.wait()
        except:
            pass
        # Termination condition triggered.
        pyro_daemon.shutdown()
        pyro_thread.join()
        self._remote.shutdown()


if __name__ == '__main__':
    """Serve devices via pyro.

    Usage:  deviceremotes [config]
    """
    import signal, sys
    import os
    # An event to trigger clean termination of subprocesses.
    term_event = multiprocessing.Event()
    def term_func(sig, frame):
        """Terminate subprocesses cleanly."""
        term_event.set()
        for s in servers:
            s.join()
        sys.exit()

    signal.signal(signal.SIGTERM, term_func)
    signal.signal(signal.SIGINT, term_func)

    if len(sys.argv) == 1:
        import config
    else:
        config = __import__(os.path.splitext(sys.argv[1])[0])
    config.REMOTES.sort()
    uid_to_host = {}
    uid_to_port = {}
    for (cls, clsid, host, port) in config.REMOTES:
        uid = (cls, clsid)
        uid_to_host[uid] = host
        uid_to_port[uid] = int(port)
    for cls, clsid, host, port in config.REMOTES:
        servers = []
        servers.append(RemoteServer(term_event, cls, uid_to_host, uid_to_port))
        servers[-1].start()
    while True:
        pass