.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

.. _install:

Installation
************

Microscope is available on the Python Package Index (PyPI) and can be
`installed like any other Python package
<https://packaging.python.org/tutorials/installing-packages/>`_.  The
short version of it is "use pip"::

    pip install microscope

You need to have Python and pip already installed on your system.


Requirements
============

Microscope can run in any operating system with Python installed but
individual devices and the intended usage may add specific
requirements:

- **hardware performance**: control of devices at high speed, namely
  image acquisition at very high rates, may require a fast connection
  to the camera, high amount of memory, or a disk with fast write
  speeds.

- **external libraries**: control of many devices is performed via
  vendor provided external libraries which are often limited to
  specific operating systems.  For example, Alpao does not provide a
  library for Linux systems so control of Alpao deformable mirrors is
  limited to Windows.  See the :ref:`Dependencies
  <install-dependencies>` sections below.

If there are multiple devices with high resources or incompatible
requirements they can be distributed over multiple computers.  For
example, two cameras acquiring images at a high frame rate or a camera
that requires Windows paired with a deformable mirror that requires
Linux.  See the :ref:`device-server` section for details.


.. _install-dependencies:

Dependencies
============

Microscope has very few dependencies.  All are Python packages
available on PyPI and will be automatically resolved if Microscope is
installed with pip.  However, the interface to many devices is done
via an external library (or SDK, or driver) that is only provided by
the device vendor.

To identify if an external library is required check the device module
documentation.  If an external library is required, contact the device
vendor for install instructions.  Cameras and deformable mirrors all
require an external library.  Filter wheels, lasers, and stages
typically do not but there are exceptions.
