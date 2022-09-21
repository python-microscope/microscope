.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

.. _ABCs:

ABCs
****

At the core of Microscope are the Abstract Base Classes (ABC) for the
different device types.  ABCs are a way to enforce a defined interface
by requiring those subclassing from them, the concrete classes, to
implement the declared abstract methods.  For example,
:class:`TopticaiBeam <microscope.lights.toptica.TopticaiBeam>` is a
concrete implementation of the :class:`LightSource
<microscope.abc.LightSource>` ABC and so is forced to implement a
series of methods, marked as abstract on the ABC, thus "promising"
that it works like all other devices that implement the
``LightSource`` ABC.

Microscope has the following ABCs that map to a specific device type:

* :class:`microscope.abc.Camera`
* :class:`microscope.abc.Controller`
* :class:`microscope.abc.DeformableMirror`
* :class:`microscope.abc.FilterWheel`
* :class:`microscope.abc.LightSource`
* :class:`microscope.abc.Stage`

In addition, they all subclass from :class:`microscope.abc.Device`
which defines a base interface to all devices such as the
:meth:`shutdown <microscope.abc.Device.shutdown>` method.

The actual concrete classes, those which provide actual control over
the devices, are listed on the section :ref:`supported-devices`.

In addition to the different device ABC, there is
:class:`microscope.abc.StageAxis` which is not a device on its own but
are device specific and returned by ``Stage`` instances to control the
individual axis.

Finally, :class:`microscope.abc.TriggerTargetMixin` is an ABC that is
mixed in other classes to add support for hardware triggers.

.. once we write the section on hardware triggers we should link it
   here.

Settings
========

Many microscope devices have specialised features which, when not
unique, are very specific to the hardware.  For example, some cameras
have the option of applying noise filters during acquisition or
provide control over amplifiers in the different stages of the
readout.  Being so specialised, such features do not fit in the ABC of
their device type.  To supported these features, Microscope has the
concept of "Settings".

Settings map a name, such as `"TemperatureSetPoint"` or
`"PREAMP_DELAY"`, to their setters and getters which act at the lowest
level available.  Those getter/setter are not exposed and only
available via the ``get_setting`` and ``set_setting`` methods, like
so:

.. code-block:: python

    camera.get_setting("TemperatureSetPoint")
    # Some settings are readonly, so check first
    if not camera.describe_setting("TemperatureSetPoint")["readonly"]:
        camera.set_setting("TemperatureSetPoint", -5)

Settings often overlap with the defined interface.  For example,
``PVCamera`` instances have the ``binning`` property as defined on the
``Camera`` ABC, but if supported by the hardware they will also have
the `"BINNING_PAR"` and `"BINNING_SER"` settings which effectively do
the same.

The use of settings is a powerful feature that provides a more direct
access to the device but this comes at the cost of reduced
interoperability, i.e., code written using settings becomes tied to
that specific hardware which makes it hard to later replace the device
with a different one.  In addition, settings also bypass the rest of
the device code and it is possible for settings to lead a device into
an unknown state.  Once settings are used, there is no more promise on
the behaviour of the device interface.  If possible, avoid use of
settings and prefer methods defined by the ABC.

An alternative to the current settings scheme would be to declare a
method for each setting on the concrete device classes.  There are a
few reasons not to.  First, many classes support a wide range of
models, for example, ``AndorSDK3`` supports all of Andor CMOS cameras,
and different models have different settings which would lead to
multiple classes with different sets of methods.  Second, some of
those settings would clash with the ABC, for example, `"AndorAtmcd"`
devices might have a `"Binning"` setting which could clash with the
``binning`` property.  Finally, using ``get_setting`` and
``set_setting`` clearly declares the use of methods that are not part
of the interface and reminds the implications that come with it.
