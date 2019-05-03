.. Copyright (C) 2017 Mick Phillips <mick.phillips@gmail.com>
   Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

Examples
********

Run servers with `python -m microscope.deviceserver SERVERS` and then
run the example with `python example.py`


Experiments
===========

.. code:: python

  from microscope import clients

  camera = clients.DataClient('PYRO:TestCamera@127.0.0.1:8005')
  laser =  clients.Client('PYRO:TestLaser@127.0.0.1:8006')

  laser.enable()
  laser.set_power_mw(30)

  camera.enable()
  camera.set_exposure_time(0.15)

  data = []

  for i in range(10):
      data.append(camera.trigger_and_wait())
      print("Frame %d captured." % i)

  print(data)

  laser.disable()
  camera.disable()


Configurations
==============

.. code:: python

  """Config file for devicebase.

  Import device classes, then define entries in DEVICES as:
     devices(CLASS, HOST, PORT, other_args)
  """
  ## Function to create record for each device.
  from microscope.devices import device
  ## Import device modules/classes here.
  from microscope.testsuite.devices import TestCamera
  from microscope.testsuite.devices import TestLaser
  from microscope.testsuite.devices import TestFilterWheel

  DEVICES = [
      device(TestCamera, '127.0.0.1', 8005, otherargs=1,),
      device(TestLaser, '127.0.0.1', 8006),
      device(TestFilterWheel, '127.0.0.1', 8007,
             filters=[(0, 'GFP', 525), (1, 'RFP'), (2, 'Cy5')]),
  ]
