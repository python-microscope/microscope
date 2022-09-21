.. Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

Design
******

Problem
=======

Research laboratories are constantly developing new microscopes that
are are complex systems that rely on the tight integration between
many components.  Instead of focusing on the microscopy, these teams
spend substantial time and effort in software development to control
their new microscopes.  Such software is limited to the specific
microscope setup and components and becomes unshareable, difficult to
maintain, or incur ongoing licensing costs.  A huge amount of time,
effort, and resources is wasted as scientists in different labs, and
even in the same lab, repeatably implement solutions to the same
problems.


Project aims
============

* Community targeted.  We want to use this ourselves but we could
  write something simpler if it was only for use by ourselves.  We
  want other people building or using microscopes to be able to use it
  and contribute back.  This means we should consider use cases other
  than our own on design choices.

* Free (libre) software.  Even though we consider other use cases when
  designing it we will still be resources limited on what we can
  implement.  The users should be able to help themselves and
  contribute the fixes back to everyone else.

* Ease of use.  Microscopes are built by physicists and biologists.
  They are the main target for Microscope, not software engineers.
  They should be able to use and install it without much trouble.


Choices
=======

Why not using µManager
----------------------

`µManager <https://micro-manager.org/>`_ is an existing open source
software for the control of microscopes.  It is written in Java and
based on top of ImageJ, an open source image analysis program.
However, µManager design has issues when controlling more complex
microscopes where devices are spread over multiple computers, with
multiple cameras, and devices are synchronised with TTL signals.  In
addition, while Java makes it easier to access ImageJ it makes more
difficult to use the whole of numpy and scipy.

Python
------

Python has multiple features:

#. it is widely used in the scientific community.  This increases the
   odds that users of Microscope will be capable to participate in its
   development.

#. unlike other widespread languages in the scientific community, it
   is a general purpose programming language and not mainly for
   numerical or symbolic computation.

#. while Python is not firstly a language for numerical computations,
   numpy and scipy are the basis for this.  Most algorithms for image
   analysis are available in Python.


Use cases
=========

Microscope GUI
--------------

This provides the device and experiment interface that a GUI
microscope interface would need to be viable.

Devices on local machine
------------------------

The simplest typical microscope.  All devices are controlled from a
single computer, the same computer where the user is.  The
synchronisation between devices is all done in software.

Devices over multiple computers in local network
------------------------------------------------

The user is in one computer but the devices are actually connected to
multiple other computers.  This may be for performance but also
because different microscope devices may require different
incompatible OS.

Synchronisation of devices during an experiment will likely be
performed by a separate device with high time precision based on a
table of events.

Controlling an independent device
---------------------------------

There is no actual a microscope, only experiment with a single device.
For example, just testing of a camera or deformable mirror.  This
device may be in a local or a remote machine.

Programmed image acquisition based on image analysis
----------------------------------------------------

Automated image analysis can make decisions during image acquisition.
For example, scanning slides for specific features; tracking of moving
particles; and automatically changing imaging parameters over time.

Multiple microscopes controlled by one central server
-----------------------------------------------------

If image acquisition is automated, a single system can automatically
control multiple microscopes without user interaction.


Realities
=========

We have to deal with the reality which is less perfect and puts limits
on our implementation and design of Microscope.

State machine
-------------

Devices do not report back their state which prevents from modelling
Microscope as a state machine.  For example, users will change
objectives or move the stage.

History
=======

Development of Python Microscope started at `Oxford Micron Bioimaging
Unit <https://www.micron.ox.ac.uk>`_ to provide remote control of
microscope devices independent of hardware specifics.  Locally,
development was guided to support development of a new version of
`cockpit <https://www.micron.ox.ac.uk/software/cockpit/>`_, a
graphical user interface for the control of microscopes.
