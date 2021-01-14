.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

.. _gui:

GUI
***

Microscope is a library for the control of microscope devices.
Provision of a graphical user interface for the control of a
microscope itself is outside the scope of the project (we recommend
the use of `Cockpit <cockpit-link_>`_ or `PYME
<https://python-microscopy.org/>`_).

Still, during development, both of the microscope and support for new
modules, a GUI can be useful.  For example, check what a camera is
acquiring, emitting light, checking if all methods are working as
expected.  For this purpose, there is the ``microscope-gui`` program
as well as a :mod:``microscope.gui`` module with Qt widgets.

The ``microscope-gui`` program provides a minimal GUI for each device
type.  It requires the device server.  For example:

.. code-block:: shell

   microscope-gui FilterWheel PYRO:SomeFilterWheel@localhost:8001

Start a program to control the filter wheel of the device being served
with Pyro at ``SomeFilterWheel@localhost:8001``.

The widgets are purposedly kept simple.  This is because the aim of
these widgets is to support development and we want to minimise issues
in the widgets code which could be interpreted as issues on the
hardware or on the device control code.

.. todo:: add screenshoots (from the paper)
