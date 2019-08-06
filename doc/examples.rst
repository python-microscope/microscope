.. Copyright (C) 2017 Mick Phillips <mick.phillips@gmail.com>
   Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

.. _examples:

Examples
********

Experiments
===========

Simple experiments can be ran with Python only.  For a simple time
series experiment:

.. code:: python

  from microscope.lasers.cobolt import CoboltLaser
  from microscope.cameras.atmcd import AndorAtmcd

  laser = CoboltLaser(com='/dev/ttyS0')
  laser.enable()
  laser.set_power_mw(30)

  camera = AndorAtmcd(uid='9146')
  camera.enable()
  camera.set_exposure_time(0.15)

  data = []
  for i in range(10):
      data.append(camera.trigger_and_wait())
      print("Frame %d captured." % i)
  print(data)

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

  camera_uri = 'PYRO:TestCamera@127.0.0.1:8005'
  laser_uri = 'PYRO:TestLaser@127.0.0.1:8006'

  camera = microscope.clients.DataClient(camera_uri)
  laser =  microscope.clients.Client(laser_uri)
  ...


Device server
=============

The device server requires a configuration file defining the different
devices to be initialised.  It can be started with::

  python -m microscope.deviceserver PATH-TO-CONFIG-FILE

The device server configuration file is a Python script that defines a
``DEVICES`` list.  Each element in the list corresponds to one
device.  For example:

.. code:: python

  """Configuration file for deviceserver.
  """
  # The 'device' function creates device definitions.
  from microscope.devices import device

  # Import required device classes
  from microscope.lasers.cobolt import CoboltLaser
  from microscope.cameras.atmcd import AndorAtmcd

  # host is the IP address (or hostname) from where the device will be
  # accessible.  If everything is on the same computer, then host will
  # be '127.0.0.1'.  If devices are to be available on the network,
  # then it will be the IP address on that network.
  host = '192.168.1.2'

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
             {'com' : '/dev/ttyS0'}),
      device(CoboltLaser, host, 7702,
             {'com' : '/dev/ttyS1'}),
      device(AndorAtmcd, host, 7703,
             {'uid' : '9146'}),
  ]


Test devices
------------

Microscope includes multiple test devices.  These are meant to support
development by providing a fake device for testing purposes.

.. code:: python

  from microscope.devices import device

  from microscope.testsuite.devices import TestCamera
  from microscope.testsuite.devices import TestLaser
  from microscope.testsuite.devices import TestFilterWheel

  DEVICES = [
      device(TestCamera, '127.0.0.1', 8005),
      device(TestLaser, '127.0.0.1', 8006),
      device(TestFilterWheel, '127.0.0.1', 8007,
             {'filters' : [(0, 'GFP', 525),
                           (1, 'RFP'), (2, 'Cy5')]}),
  ]
