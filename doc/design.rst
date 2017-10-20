.. Copyright (C) 2017 David Pinto <carandraug+dev@gmail.com>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

******
Design
******

Problem
=======

Bespoke microscopes are built in research labs by physicists and
biologists that are often not interested in programming.  We found no
satisfying solution 


writing software t


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

µManager
--------

Python
------

Use cases
=========

All devices on local machine
----------------------------

The simplest typical microscope.  All devices are controlled from one
computer, the same computer where the user is, and is being controlled
by only one program.

Multiple computers controlling different devices
------------------------------------------------

The user is in one computer but the devices are actually connected to
one other computer, possible multiple computers.  Some devices may be
on the local machine.  This may be to reduce load on the machine or
because devices are only supported on specific OSes, not compatible
with each other.

Controlling single device, no microscope
----------------------------------------

There is no actual a microscope, only playing with a single device.
For example, just testing out a camera or deformable mirror.

Automated microscope control as function of analysis
----------------------------------------------------

Images are acquired and analysed.  The result of such analysis is the
control for consequent acquisition.  For example, imaging of a whole
plate and analyse images looking for specific features.  If found,
image different settings.

Multiple microscopes controlled by one central server
-----------------------------------------------------

If image acquisition is automated, a single powerful computer can
control multiple microscopes as it analyses the images.


Realities
=========

We have to deal with the reality which is less perfect and puts limits
on our implementation and design of Microscope.

State machine
-------------

Devices do not report back their state which prevents from modelling
Microscope as a state machine.  For example, users will change
objectives or move the stage.

Buggy SDK
---------

A device may be initialised only once per process.  We have this issue
with PVCAM cameras.  All processes that load or hook in any way to the
PVCAM SDK must be terminated before initialising the camera again,
even if we use the camera deactivation camera.

This prevents us from using device object creation and destruction as
device initialisation and deactivation and why we have specific enable
and disable methods instead.
