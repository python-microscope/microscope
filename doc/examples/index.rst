.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

.. _examples:

Examples
********

Example scripts of the things that can be done, typically when
interacting with multiple devices.

.. For now, we just "insert" the example code but later we might have
   one per file and a discussion of what is happening.

Experiments
===========

Simple experiments can be ran with Python only.  For a simple time
series experiment:

.. code:: python

    import queue
    import time

    from microscope.lights.cobolt import CoboltLaser
    from microscope.cameras.atmcd import AndorAtmcd

    laser = CoboltLaser(com='/dev/ttyS0')
    laser.power = 0.3

    camera = AndorAtmcd(uid='9146')
    camera.set_exposure_time(0.15)

    buffer = queue.Queue()

    camera.set_client(buffer)
    laser.enable()
    camera.enable()

    for i in range(10):
        camera.trigger()  # images go to buffer
        time.sleep(1)

    laser.disable()
    camera.disable()


Remote devices
==============

Microscope was designed around the idea that the multiple devices are
distributed over the network.  To accomplish this, the device objects
can be replaced with ``Client`` and ``DataClient`` instances.  For
example, to run the previous experiment with remote devices:

.. code:: python

    import microscope.clients

    camera_uri = 'PYRO:SomeCamera@127.0.0.1:8005'
    laser_uri = 'PYRO:SomeLaser@127.0.0.1:8006'

    camera = microscope.clients.DataClient(camera_uri)
    laser =  microscope.clients.Client(laser_uri)


Device server
=============

The device server requires a configuration file defining the different
devices to be initialised.  It can be started with:

.. code-block:: shell

    python -m microscope.device_server PATH-TO-CONFIG-FILE

The device server configuration file is a Python script that defines a
``DEVICES`` list.  Each element in the list corresponds to one
device.  For example::

    """Configuration file for deviceserver.
    """
    # The 'device' function creates device definitions.
    from microscope.device_server import device

    # Import required device classes
    from microscope.lights.cobolt import CoboltLaser
    from microscope.cameras.atmcd import AndorAtmcd

    # host is the IP address (or hostname) from where the device will be
    # accessible.  If everything is on the same computer, then host will
    # be '127.0.0.1'.  If devices are to be available on the network,
    # then it will be the IP address on that network.
    host = '127.0.0.1'

    # Each element in the DEVICES list identifies a device that will be
    # served on the network.  Each device is defined like so:
    #
    # device(cls, host, port, conf)
    #     cls: class of the device that will be served
    #     host: ip or hostname where the device will be accessible.
    #         This will be the same value for all devices.
    #     port: port number where the device will be accessible.
    #         Each device must have its own port.
    #     conf: a dict with the arguments to construct the device
    #         instance.  See the individual class documentation.
    #
    # This list, initialises two cobolt lasers and one Andor camera.
    DEVICES = [
        device(CoboltLaser, host, 7701,
               {"com": "/dev/ttyS0"}),
        device(CoboltLaser, host, 7702,
               {"com": "/dev/ttyS1"}),
        device(AndorAtmcd, host, 7703,
               {"uid": "9146"}),
    ]


Test devices
------------

Microscope includes multiple simulated devices.  These are meant to
support development by providing a fake device for testing purposes.

.. code:: python

    from microscope.device_server import device

    from microscope.simulators import (
        SimulatedCamera,
        SimulatedFilterWheel,
        SimulatedLightSource,
    )

    DEVICES = [
      device(SimulatedCamera, '127.0.0.1', 8005),
      device(SimulatedLightSource, '127.0.0.1', 8006),
      device(SimulatedFilterWheel, '127.0.0.1', 8007,
             {"positions": 6}),
    ]
