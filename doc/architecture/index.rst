.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

Architecture
************

.. toctree::
   :hidden:

   abc
   supported-devices
   device-server
   triggers
   gui

At its core, Microscope is a Python library that provides a defined
interface to microscope devices.  Technically, Microscope aims to be:

* Easy to use
* Flexible
* Fast

..
   The main reason for Microscope is to enable faster development of new
   microscope.  The people doing this systems are not computer
   scientists, and code is what they use to get the system and not their
   aim.  Also, biologists who do new experiments, we want them to be able
   to script.  As such, Microscope needs to be easy to use.

..
   We don't know what will be be the microscopes of the future.  The
   devices are independent of each other, we want to keep supporting
   that.

   Microscopes require the interaction of multiple devices with tight
   timing constraints, specially when imaging at high speeds.

   Python is a great choice for that aim, and since most researchers
   During development, a series of
   choices have been made with these aims in mind, namely the choice of
   Python as the programming language

Python has become the *de facto* language for scientific computing.
If most researchers are already familiar with it, it makes it easier
to adopt since they don't need to learn a new language.  Python is
also well know for being easy to learn.

In addition, Python has a terrific ecosystem for scientific computing,
e.g., NumPy, SciPy and SciKits, or TensorFlow.  One of the
flexibility, is the ability to expand the control of individual to
merge with the analysis.  Having the whole Python scientific stack is
great, makes it more flexible.

Flexibility also means ability to distribute devices.  For this,
Microscope was developed to support :ref:`remote devices
<device-server>`.  This enables distribution of devices over multiple
computers, an arbitrary number of devices, to provide any flexibility
required.

Finally, despite common ideas that performance requires a compiled
language such as C++, Python has been shown to be fast enough.
Anyway, when push comes to shove, new microscopes have tight timing
requirements, synchronization between multiple devices that can only
be satisfied by real time software.  Most devices have a mode of
operation where they act on receive of a hardware trigger and many
devices can act as source of triggers.
