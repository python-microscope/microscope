.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

.. _device-server:

Device Server
*************

Microscope has been designed from the start to support remote devices
where each device is on its own separate server.  These separate
servers may be in different computers or they can be different daemons
(or services) in the same computer.  In this architecture, a program
that wants to control the device becomes a client and connects to the
device server.  A program that controls multiple devices, such as
`Cockpit <cockpit-link_>`_, connects to multiple servers one per
device.  This client-server architecture to control a microscope has a
series of advantages:

- having each device on its own separate daemon means that each runs
  on its own Python process and so are not blocked by `Python GIL
  <https://wiki.python.org/moin/GlobalInterpreterLock>`_

- enables distribution of devices with hard requirements over multiple
  computers.  This is typically done when there are too many cameras
  acquiring images at high speed and IO becomes a bottleneck.

- possible to have devices with incompatible requirements, e.g., a
  camera that only works in Linux with a deformable mirror that only
  works in Windows.

.. todo::

   add figures to explain device server (figure from the paper).

The `device-server` program
===========================

The `device-server` program is part of the Microscope installation.
It can started from the command line with a configuration file
defining the devices to be served, like so:

.. code-block:: bash

    device-server PATH-TO-CONFIGURATION-FILE
    # alternatively, if scripts were not installed:
    python -m microscope.device_server PATH-TO-CONFIGURATION-FILE

where the configuration file is a Python script that declares the
devices to be constructed and served on its ``DEVICES`` attribute via
device definitions.  A device definition is created with the
:func:`microscope.device_server.device` function.  For example:

.. code-block:: python

    # Serve two test cameras, each on their own process.
    from microscope.device_server import device
    from microscope.simulators import SimulatedCamera

    DEVICES = [
        device(SimulatedCamera, host="127.0.0.1", port=8000),
        device(SimulatedCamera, host="127.0.0.1", port=8001)
    ]

The example above creates two device servers, each on their own python
process and listening on different ports.  If the class requires
arguments to construct the device, these must be passed as separate
keyword arguments, like so:

.. code-block:: python

    from microscope.device_server import device
    from microscope.simulators import SimulatedFilterWheel

    DEVICES = [
        # The device will be constructed with `SimulatedFilterWheel(**conf)`
        # i.e., `SimulatedFilterWheel(positions=6)`
        device(
            SimulatedFilterWheel,
            host="127.0.0.1",
            port=8001,
            conf={"positions": 6},
        ),
    ]

Instead of a device type, a function can be passed to the device
definition.  Reasons to do so are: configure the device before serving
it; specify their URI; force a group of devices in the same process
(see :ref:`composite-devices`); and readability of the configuration
when `conf` gets too complex.  For example:

.. code-block:: python

    # Serve a cameras and a filter wheel
    from microscope.device_server import device
    from microscope.simulators import SimulatedCamera

    def construct_camera() -> typing.Dict[str, Device]:
        camera = SimulatedCamera()
        camera.set_setting("display image number", False)
        return {"DummyCamera": camera}

    # Will serve PYRO:DummyCamera@127.0.0.1:8000
    DEVICES = [
        device(construct_camera, host="127.0.0.1", port=8000),
    ]


Connect to remote devices
=========================

The Microscope device server makes use of `Pyro4
<https://pyro4.readthedocs.io/en/stable/>`_, a Python package for
remote method invocation of Python objects.  One can use the Pyro
proxy, the remote object, as if it was a local instance of the device
itself and Pyro takes care of locating the right object on the right
computer and execute the method.  Creating the proxy is simply a
matter of knowing the device server URI:

.. code-block:: python

    import Pyro4

    proxy = Pyro4.Proxy('PYRO:SomeLaser@127.0.0.1:8000')
    # use proxy as if it was an instance of the SomeLaser class
    proxy._pyroRelease()

The device server will take care of anything special.  If the remote
device is a :class:`Controller<microscope.abc.Controller>`, the device
server will use automatically create proxies for the individual
devices it controls.

Pyro configuration
------------------

Pyro4 configuration is the singleton :obj:`Pyro4.config`.  If there's
any special configuration wanted, this can be done on the
`device-server` configuration file:

.. code-block:: python

    import Pyro4
    import microscope.device_server
    # ...

    # Pyro4.config is a singleton, these changes to config will be
    # used for all the device servers.  This needs to be done after
    # importing microscope.device_server
    Pyro4.config.COMPRESSION = True
    Pyro4.config.PICKLE_PROTOCOL_VERSION = 2

    DEVICES = [
        #...
    ]

Importing the `microscope.device_server` will already change the Pyro
configuration, namely it sets the `SERIALIZER` to use the pickle
protocol.  Despite the security implications associated with it,
pickle is the fastest of the protocols and one of the few capable of
serialise numpy arrays which are camera images.


Floating Devices
================

A :class:`floating device<microscope.abc.FloatingDeviceMixin>` is a
device that can't be specified during object construction, and only
after initialisation can it be identified.  This happens in some
cameras and is an issue when more than one such device is present.
For example, if there are two Andor CMOS cameras present, it is not
possible to specify which one to use when constructing the `AndorSDK3`
instance.  Only after the device has been initialised can we query its
ID, typically the device serial number, and check if we obtained the
one we want.  Like so:

.. code-block:: python

    wanted = "20200910" # serial number of the wanted camera
    camera = AndorSDK3()
    camera.initialize()
    if camera.get_id() != wanted:
        # We got the other camera, so try again
        next_camera = AndorSDK3()
        # Only shutdown the first camera after getting the next or we
        # might get the same wrong camera again.
        camera.shutdown()
        camera = next_camera

In the interest of keeping each camera on their own separate process,
the above can't be used.  To address this, the device definition must
specify the `uid` if the device class is a floating device.  Like so::

    DEVICES = [
        device(AndorSDK3, "127.0.0.1", 8000, uid="20200910"),
        device(AndorSDK3, "127.0.0.1", 8001, uid="20130802"),
    ]

The device server will then construct each device on its own process,
and then serve them on the named port.  Two implication come out of
this.  The first is that the `uid` *must* be specified, even if there
is only such device present on the system.  The second is that all
devices of that class *must* be present.

.. _composite-devices:

Composite Devices
=================

A composite device is a device that internally makes use of another
device to function.  These are typically not real hardware, they are
an abstraction that merges multiple devices to provide something
augmented.  For example, `ClarityCamera` is a camera that returns a
processed image based on the settings of `AuroxClarity`.  Another
example is the `StageAwareCamera` which is a dummy camera that returns
a subsection of an image file based on the stage coordinates in order
to mimic navigating a real sample.

If the multiple devices are on the same computer, it might be worth
have them share the same process to avoid the inter process
communication.  This is achieved by returning multiple devices on the
function that constructs.  Like so:

.. code-block:: python

    def construct_composite_device(
        device1 = SomeDevice()
        composite_device = DeviceThatNeedsOther(device1)
        return {
            "Device1" : device1,
            "CompositeDevice": composite_device,
        }

    # Will serve both:
    #   PYRO:Device1@127.0.0.1:8000
    #   PYRO:CompositeDevice@127.0.0.1:8000
    DEVICES = [
        device(construct_composite_device, "127.0.0.1", 8000)
    ]
