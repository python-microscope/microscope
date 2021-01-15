.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

Getting Started
***************

To control a device with Microscope one needs to find the Python class
that supports it.  These are listed on :ref:`supported-devices`.  Each
device has its own class which typically have their own module.  Note
that many devices have the same class, for example, all Ximea cameras
use :class:`XimeaCamera <microscope.cameras.ximea.XimeaCamera>` and
all Andor CMOS cameras use :class:`AndorSDK3
<microscope.cameras.andorsdk3.AndorSDK3>`.

Connecting to the Device
========================

Once the class is known its documentation will state the arguments
required to construct the device instance and connect to it.  For
devices controlled over a serial channel the argument is typically the
port name of its address, e.g., `/dev/ttyS0` on GNU/Linux or `COM1` on
Windows.  For other devices the argument is typically the serial
number (this is typically printed on a label on the physical device).

.. code-block:: python

    from microscope.lights.sapphire import SapphireLaser
    laser = SapphireLaser(com="/dev/ttyS0")

    from microscope.mirror.alpao import AlpaoDeformableMirror
    dm = AlpaoDeformableMirror(serial_number="BIL103")

Controlling the Device
======================

The construction of the device is the only device specific code.
Beyond this :ref:`ABCs` force a defined interface on the device
classes ensuring that all devices have the same methods and
properties.  The following ABCs, one per device type, are currently
supported:

* :class:`microscope.abc.Camera`
* :class:`microscope.abc.Controller`
* :class:`microscope.abc.DeformableMirror`
* :class:`microscope.abc.FilterWheel`
* :class:`microscope.abc.LightSource`
* :class:`microscope.abc.Stage`


LightSource
-----------

A light source emits light when enabled and its power can be read and
set via the ``power`` property::

    laser.power = .7 # set power to 70%
    laser.enable() # only start emitting light now
    laser.power = laser.power /3 # set power to 1/3
    laser.disable() # stop emitting light


Filter Wheel
------------

A filter wheel changes its position by setting the ``position``
property::

    print("Number of positions is %d" % filterwheel.n_positions)
    print("Current position is %d" % filterwheel.position)
    filterwheel.position = 3 # move in filter at position 3


Stage
-----

A stage device can have any number of axes and dimensions.  For a
single ``StageDevice`` instance each axis has a name that uniquely
identifies it.  The names of the individual axes are hardware
dependent and will be part of the concrete class documentation.  They
are typically strings such as `"x"` or `"y"`.

.. code-block:: python

    stage.enable()  # may trigger a stage move

    # move operations
    stage.move_to({"x": 42.0, "y": -5.1})
    stage.move_by({"x": -5.3, "y": 14.6})

    # Individual StageAxis can be controlled directly.
    x_axis = stage.axes["x"]
    y_axis = stage.axes["y"]
    x_axis.move_to(42.0)
    y_axis.move_by(-5.3)


Camera
------

Cameras when triggered will put an image on their client which is a
queue-like object.  These queue-like objects must first be created and
set on the camera::

    buffer = queue.Queue()
    camera.set_client(buffer)
    camera.enable()
    camera.trigger()  # acquire image

    img = buffer.get()  # retrieve image


Deformable Mirror
-----------------

A deformable mirror applies a NumpPy array with the values for each of
its actuators in the range of [0 1]::

    # Set all actuators to their mid-point
    dm.apply_pattern(np.full(dm.n_actuators, 0.5))

Alternatively, a series of patterns can be first queued and applied
when a trigger is received::

    # `patterns` is a NumPy array of shape (K, N) where K is the number of
    # patterns and N is the number of actuators.
    dm.queue_patterns(patterns)
    for i in range(patterns.shape[0]):
        dm.trigger()


Controller
----------

A controller is a device that controls a series of other devices.  For
example, a multi laser engine is a controller of many light sources.
A controller instance only has as ``devices`` property which is a map
of names to instances of other device classes.

.. code-block:: python

    cyan_led = controller.devices['CYAN']
    red_laser = controller.devices['RED']

The class documentation will include details on the names of the
controller device.


Shutdown the Device
===================

When all is done, it's a good idea to disable and cleanly shutdown the
device::

    camera.disable()
    camera.shutdown()
