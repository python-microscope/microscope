.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

Microscope Documentation
************************

.. toctree::
   :hidden:

   getting-started
   install
   examples/index
   architecture/index
   api/index
   news
   get-involved/index
   authors

Microscope is fundamentally a Python package for the control of
microscope devices.  It provides an easy to use interface for
different device types.  For example:

.. code-block:: python

    # Connect to a Coherent Sapphire laser, set its power while
    # emitting light.
    from microscope.lights.sapphire import SapphireLaser
    laser = SapphireLaser(com="/dev/ttyS1")
    laser.initialize()
    laser.power = .7  # initial laser power at 70%
    laser.enable()  # start emitting light
    laser.power = laser.power / .3 # set laser power to 1/3


    # Connect to a Thorlabs filterwheel, query filter position, then
    # change filter.
    from microscope.filterwheels.thorlabs import ThorlabsFW102C
    filterwheel = ThorlabsFW102C(com="/dev/ttyS0")
    filterwheel.initialize()
    print("Number of positions is %d" % filterwheel.n_positions)
    print("Current position is %d" % filterwheel.position)
    filterwheel.position = 3  # move in filter at position 3


At the core of Microscope is the idea that all devices of the same
type should have the same interface (see :ref:`ABCs`).
