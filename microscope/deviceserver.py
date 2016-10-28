import logging
import multiprocessing
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler
from threading import Thread

import Pyro4
from future.utils import iteritems

from microscope.devices import FloatingDeviceMixin

# Pyro configuration. Use pickle because it can serialize numpy ndarrays.
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2

# Logging formatter.
LOG_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s PID %(process)s: %(message)s')

class DeviceServer(multiprocessing.Process):
    def __init__(self, device_def, id_to_host, id_to_port, count=0, exit_event=None):
        """Initialise a device and serve at host/port according to its id.

        :param device_def:  definition of the device
        :param id_to_host: host or mapping of device identifiers to hostname
        :param id_to_port: map or mapping of device identifiers to port number
        :param count:       this is the countth process serving this class
        :param exit_event:  a shared event to signal that the process should quit.
        """
        # The device to serve.
        self._device_def = device_def
        self._device = None
        # Where to serve it.
        self._id_to_host = id_to_host
        self._id_to_port = id_to_port
        # A shared event to allow clean shutdown.
        self.exit_event = exit_event
        super(DeviceServer, self).__init__()
        self.daemon = True
        # Some SDKs need an index to access more than one device.
        self.count = count

    def run(self):
        self._device = self._device_def['cls'](index=self.count, **self._device_def)
        while True:
            try:
                self._device.initialize()
            except:
                time.sleep(5)
            else:
                break
        if isinstance(self._device, FloatingDeviceMixin):
            uid = self._device.get_id()
            if uid not in self._id_to_host or uid not in self._id_to_port:
                raise Exception("Host or port not found for device %s" % (uid,))
            host = self._id_to_host[uid]
            port = self._id_to_port[uid]
        else:
            host = self._device_def['host']
            port = self._device_def['port']
        pyro_daemon = Pyro4.Daemon(port=port, host=host)
        log_handler = RotatingFileHandler("%s_%s_%s.log" %
                                          (type(self._device).__name__, host, port))
        log_handler.setFormatter(LOG_FORMATTER)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        if __debug__:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        logger.info('Device initialized; starting daemon.')
        logger.debug('Debugging messages on.')

        # Run the Pyro daemon in a separate thread so that we can do
        # clean shutdown under Windows.
        pyro_thread = Thread(target=Pyro4.Daemon.serveSimple,
                             args=({self._device: type(self).__name__},),
                             kwargs={'daemon': pyro_daemon, 'ns': False})
        pyro_thread.daemon = True
        pyro_thread.start()
        if self.exit_event:
            # This tread waits for the termination event.
            try:
                self.exit_event.wait()
            except:
                pass
            pyro_daemon.shutdown()
            pyro_thread.join()
            # Termination condition triggered.
        else:
            # This is the main process. Sleep until interrupt.
            pyro_thread.join()
        self._device.shutdown()


def __main__():
    # An event to trigger clean termination of subprocesses. This is the
    # only way to ensure devices are shut down properly when processes
    # exit, as __del__ is not necessarily called when the interpreter exits.
    exit_event = multiprocessing.Event()

    def term_func(sig, frame):
        """Terminate subprocesses cleanly."""
        exit_event.set()
        for this_server in servers:
            this_server.join()
        sys.exit()

    signal.signal(signal.SIGTERM, term_func)
    signal.signal(signal.SIGINT, term_func)

    if len(sys.argv) == 1:
        import config
    else:
        config = __import__(os.path.splitext(sys.argv[1])[0])

    # Group devices by class.
    by_class = {}
    for r in config.DEVICES:
        by_class[r['cls']] = by_class.get(r['cls'], []) + [r]

    servers = []
    for cls, rs in iteritems(by_class):
        # Keep track of how many of these classes we have set up.
        # Some SDKs need this information to index devices.
        count = 0
        if issubclass(cls, FloatingDeviceMixin):
            # Need to provide maps of uid to host and port.
            uid_to_host = {}
            uid_to_port = {}
            for r in rs:
                uid = r['uid']
                uid_to_host[uid] = r['host']
                uid_to_port[uid] = r['port']
        else:
            uid_to_host = None
            uid_to_port = None

        for r in rs:
            servers.append(DeviceServer(r,
                                        uid_to_host, uid_to_port,
                                        exit_event=exit_event, count=count))
            servers[-1].start()
            count += 1
    for s in servers:
        s.join()


if __name__ == '__main__':
    """Serve devices via Pyro.

    Usage:  deviceserver [config]
    """

    __main__()
