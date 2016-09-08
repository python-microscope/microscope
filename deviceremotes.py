import Pyro4
import multiprocessing
import threading
import time
import atexit


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
    Derived classed should implement _get_data(self).
    Derived classes may override __init__, enable and disable, but must
    ensure to call this class' implementations. This class' enable and 
    disable should be called after the rest of a derived-class'
    implementation.
    """
    def __init__(self):
        super(DataRemote, self).__init__()
        # A buffer for data.
        self._data = None
        # A thread to fetch and dispatch data.
        self._data_thread = None
        # A flag to control the _data_thread.
        self._data_thread_run = False
        # A client to which we send data.
        self._client = None


    def __del__(self):
        self.disable()


    def enable(self):
        """Enable a data capture device.

        Ensures that a data handling thread is running. 
        """
        if not self._data_thread or not self._data_thread.is_alive():
            self._data_thread = threading.Thread(target=self._data_thread_loop)
            self._data_thread.daemon = True
            self._data_thread.start()
        super(DataRemote, self).enable()


    def disable(self):
        self.enabled = False
        if self._data_thread:
            if self._data_thread.is_alive():
                self._data_thread_run = False
                self._data_thread.join()
            self.data_thread = None
        super(DataRemote, self).disable()


    def _get_data(self):
        """Poll for data, returning True if data received, False otherwise.

        If data is fetched, store it in self._data."""
        self._data = None
        return False


    def _send_data(self):
        """Dispatch data to the client."""
        if self._client and self._data:
            try:
                # Currently uses legacy receiveData. Would like to pass
                # this function name as an argument to set_client, but
                # not sure to subsequently resolve this over Pyro.
                self._client.receiveData(self._data)
            except Pyro4.errors.ConnectionClosedError:
                # Nothing is listening
                self._client = None


    def _data_thread_loop(self):
        """Poll source for data and dispatch to any client."""
        self._data_thread_run = True
        while self._data_thread_run:
            if self._get_data():
                timestamp = time.time()
                self._send_data()
            else:
                time.sleep(0.01)


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
