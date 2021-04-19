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

import logging
import multiprocessing
import os
import os.path
import signal
import tempfile
import time
import unittest
import unittest.mock

import Pyro4
import Pyro4.errors

import microscope.abc
import microscope.clients
import microscope.device_server
from microscope.testsuite.devices import (
    TestCamera,
    TestDeformableMirror,
    TestFilterWheel,
    TestFloatingDevice,
)


class ExposePIDDevice(microscope.abc.Device):
    """Test device for testing the device server keep alive."""

    def _do_shutdown(self) -> None:
        pass

    def get_pid(self) -> int:
        return os.getpid()


class DeviceServerExceptionQueue(microscope.device_server.DeviceServer):
    """`DeviceServer` that queues an exception during `run`.

    A `DeviceServer` instance runs on another process so if it fails
    we can't easily check why.  This subclass will put any exception
    that happens during `run()` into the given queue so that the
    parent process can check it.

    """

    def __init__(self, queue: multiprocessing.Queue, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._queue = queue

    def run(self):
        try:
            super().run()
        except Exception as ex:
            self._queue.put(ex)


def _patch_out_device_server_logs(func):
    """Decorator to run device server without noise from logs.

    The device server redirects the logger to stderr *and* creates
    files on the current directory.  There is no options to control
    this behaviour so this patches the loggers.
    """

    def null_logs(*args, **kwargs):
        return logging.NullHandler()

    no_file = unittest.mock.patch(
        "microscope.device_server.RotatingFileHandler", null_logs
    )
    no_stream = unittest.mock.patch(
        "microscope.device_server.StreamHandler", null_logs
    )
    return no_file(no_stream(func))


class BaseTestServeDevices(unittest.TestCase):
    """Handles start and termination of deviceserver.

    Subclasses may overload class properties defaults as needed.

    Attributes:
        DEVICES (list): list of :class:`microscope.devices` to initialise.
        TIMEOUT (number): time given for service to terminate after
            receiving signal to terminate.
        p (multiprocessing.Process): device server process.
    """

    DEVICES = []
    TIMEOUT = 5

    @_patch_out_device_server_logs
    def setUp(self):
        options = microscope.device_server.DeviceServerOptions(
            config_fpath="", logging_level=logging.INFO,
        )
        self.p = multiprocessing.Process(
            target=microscope.device_server.serve_devices,
            args=(self.DEVICES, options),
        )
        self.p.start()
        time.sleep(1)

    def tearDown(self):
        self.p.terminate()
        self.p.join(self.TIMEOUT)
        self.assertFalse(
            self.p.is_alive(), "deviceserver not dead after SIGTERM"
        )


class BaseTestDeviceServer(unittest.TestCase):
    """TestCase that starts DeviceServer on separate process.

    Subclasses should define the class attribute `args`, which is used
    to start the `DeviceServer` and implement `test_*` methods.

    """

    args = []  # args to construct DeviceServer
    TIMEOUT = 5  # time to wait after join() during tearDown

    @_patch_out_device_server_logs
    def setUp(self):
        self.queue = multiprocessing.Queue()
        self.process = DeviceServerExceptionQueue(self.queue, *self.args)
        self.process.start()
        time.sleep(1)

    def tearDown(self):
        self.process.terminate()
        self.process.join(self.TIMEOUT)
        self.assertIsNotNone(
            self.process.exitcode, "deviceserver not dead after SIGTERM"
        )


class TestStarting(BaseTestServeDevices):
    DEVICES = [
        microscope.device_server.device(
            TestCamera, "127.0.0.1", 8001, {"buffer_length": 0}
        ),
        microscope.device_server.device(
            TestFilterWheel, "127.0.0.1", 8003, {"positions": 3}
        ),
    ]

    def test_standard(self):
        """Simplest case, start and exit, given enough time to start all devices"""
        self.assertTrue(self.p.is_alive(), "service dies at start")

    def test_immediate_interrupt(self):
        """Check issues on SIGTERM before starting all devices"""
        pass


class TestInputCheck(BaseTestServeDevices):
    def test_empty_devices(self):
        """Check behaviour if there are no devices."""
        self.assertTrue(
            not self.p.is_alive(), "not dying for empty list of devices"
        )


class DeviceWithPort(microscope.abc.Device):
    def __init__(self, port, **kwargs):
        super().__init__(**kwargs)
        self._port = port

    @property
    def port(self):
        return self._port

    def _do_shutdown(self):
        pass


class TestClashingArguments(BaseTestServeDevices):
    """Device server and device constructor arguments do not clash"""

    DEVICES = [
        microscope.device_server.device(
            DeviceWithPort, "127.0.0.1", 8000, {"port": 7000}
        ),
    ]

    def test_port_conflict(self):
        client = microscope.clients.Client(
            "PYRO:DeviceWithPort@127.0.0.1:8000"
        )
        self.assertEqual(client.port, 7000)


class TestConfigLoader(unittest.TestCase):
    def _test_load_source(self, filename):
        file_contents = "DEVICES = [1,2,3]"
        with tempfile.TemporaryDirectory() as dirpath:
            filepath = os.path.join(dirpath, filename)
            with open(filepath, "w") as fh:
                fh.write(file_contents)

            module = microscope.device_server._load_source(filepath)
            self.assertEqual(module.DEVICES, [1, 2, 3])

    def test_py_file_extension(self):
        """Reading of config file module-like works"""
        self._test_load_source("foobar.py")

    def test_cfg_file_extension(self):
        """Reading of config file does not require .py file extension"""
        # Test for issue #151.  Many importlib functions assume that
        # the file has importlib.machinery.SOURCE_SUFFIXES extension
        # so we need a bit of extra work to work with none or .cfg.
        self._test_load_source("foobar.cfg")

    def test_no_file_extension(self):
        """Reading of config file does not require file extension"""
        self._test_load_source("foobar")


class TestFloatingDeviceIndexInjection(BaseTestServeDevices):
    DEVICES = [
        microscope.device_server.device(
            TestFloatingDevice, "127.0.0.1", 8001, {"uid": "foo"}, uid="foo"
        ),
        microscope.device_server.device(
            TestFloatingDevice, "127.0.0.1", 8002, {"uid": "bar"}, uid="bar"
        ),
    ]

    def test_injection_of_index_kwarg(self):
        floating_1 = Pyro4.Proxy("PYRO:TestFloatingDevice@127.0.0.1:8001")
        floating_2 = Pyro4.Proxy("PYRO:TestFloatingDevice@127.0.0.1:8002")
        self.assertEqual(floating_1.get_index(), 0)
        self.assertEqual(floating_2.get_index(), 1)


class TestServingFloatingDevicesWithWrongUID(BaseTestDeviceServer):
    # This test will create a floating device with a UID different
    # (foo) than what appears on the config (bar).  This is what
    # happens if there are two floating devices on the system (foo and
    # bar) but the config lists only one of them (bar) but the other
    # one is served instead (foo).  See issue #153.
    args = [
        microscope.device_server.device(
            TestFloatingDevice,
            "127.0.0.1",
            8001,
            # The index kwarg is typically injected by serve_devices
            # but here we're only testing DeviceServer so we need to
            # do it ourselves.
            {"uid": "foo", "index": 0},
            uid="bar",
        ),
        microscope.device_server.DeviceServerOptions(
            config_fpath="", logging_level=logging.INFO,
        ),
        {"bar": "127.0.0.1"},
        {"bar": 8001},
        multiprocessing.Event(),
    ]

    def test_fail_with_wrong_uid(self):
        """DeviceServer fails if it gets a FloatingDevice with another UID """
        self.assertFalse(
            self.process.is_alive(),
            "expected DeviceServer to have errored and be dead",
        )
        self.assertRegex(
            str(self.queue.get_nowait()),
            "Host or port not found for device foo",
        )


class TestFunctionInDeviceDefinition(BaseTestDeviceServer):
    # Test that with a function we can specify multiple devices and
    # they get the expected Pyro URI.
    args = [
        microscope.device_server.device(
            lambda **kwargs: {
                "dm1": TestDeformableMirror(10),
                "dm2": TestDeformableMirror(20),
            },
            "localhost",
            8001,
        ),
        microscope.device_server.DeviceServerOptions(
            config_fpath="", logging_level=logging.INFO,
        ),
        {},
        {},
        multiprocessing.Event(),
    ]

    def test_function_in_device_definition(self):
        """Function that constructs multiple devices in device definition"""
        self.assertTrue(self.process.is_alive())
        dm1 = Pyro4.Proxy("PYRO:dm1@127.0.0.1:8001")
        dm2 = Pyro4.Proxy("PYRO:dm2@127.0.0.1:8001")
        self.assertEqual(dm1.n_actuators, 10)
        self.assertEqual(dm2.n_actuators, 20)


class TestKeepDeviceServerAlive(BaseTestServeDevices):
    DEVICES = [
        microscope.device_server.device(
            ExposePIDDevice, "127.0.0.1", 8001, {}
        ),
    ]

    @unittest.skipUnless(
        hasattr(signal, "SIGKILL"),
        "can't test if we can't kill subprocess (windows)",
    )
    def test_keep_alive(self):
        device = Pyro4.Proxy("PYRO:ExposePIDDevice@127.0.0.1:8001")
        initial_pid = device.get_pid()

        os.kill(initial_pid, signal.SIGKILL)

        with self.assertRaises(Pyro4.errors.ConnectionClosedError):
            device.get_pid()

        # The device server checks every 5 seconds for a crashed
        # device server so give it 6 seconds.
        time.sleep(6)

        device._pyroReconnect(tries=1)
        new_pid = device.get_pid()
        self.assertNotEqual(initial_pid, new_pid)


if __name__ == "__main__":
    unittest.main()
