.. Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

Contributing
************

This documentation is for people who want to contribute code to the
project, whether fixing a small bug, adding support for a new device,
or even discussing a completely new device type.


In short
========

- Open new issues.  Do not create pull requests.
- Open a new issue even if you already have a commit made.  Even if it
  is about adding support for a new device.
- Coding style is `PEP 8 <https://www.python.org/dev/peps/pep-0008/>`_
- Development sources at
  `<https://github.com/MicronOxford/microscope>`_
- Bug tracker at `<https://github.com/MicronOxford/microscope/issues>`_


Reporting issues
================

We use the github issue tracker at
`<https://github.com/MicronOxford/microscope/issues>`_.  When
reporting an issue, please include as much information as you can
from:

- Steps to reproduce issue
    Include information so that we can try it ourselves.  Don't just
    say "camera fails when setting exposure time".  Instead, include
    the code to reproduce the issue and the error message.

- Operating system
    MacOS 10.15, Ubuntu 18.04, Windows 7, Windows 10, etc...

- Python version
    Also include the python minor version number, i.e, Python 3.7.3 or
    3.6.2.  On command line, this is the output of `python --version`.

- Device, SDK, and firmware information
    Include the device model, revision number, and serial number.
    Also include the firmware and the device SDK version number.

- PyRO version
    If the issue only happens in the network, please also include the
    version of the PyRO package.


Requesting support for new device
=================================

To request support for a new device, or even to support for a feature
of an already supported device, open a new issue on the `issue tracker
<https://github.com/MicronOxford/microscope/issues>`_.

If there's already an open issue requesting the same, please leave a
comment so that we know more people want it.


Fixing an issue
===============

To fix an issue, including adding support for a new device, please do
the following:

- Open a new issue (if not already opened)
- On the commit message, refer to the issue number
- Comment on the issue what branch or commit to pull to fix it.

Why the non-standard procedure?
-------------------------------

This procedure to fix an issue is not very standard on github
projects.  However, it prevents spreading the discussion of the issue
over multiple pages and enables one to find that discussion from the
git history.


Coding standards
================

Code style
----------

For code formatting use `PEP 8
<https://www.python.org/dev/peps/pep-0008/>`_.

Docstrings
----------

The whole API section of the documentation is generated from the
inlined docstrings.  It requires the `Google Python docstrings format
<https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_.
It looks like this::


    def func(arg1, arg2):
        """One-line summary.

        Extended description of function.

        Args:
            arg1 (int): Description of arg1.  This can be a multi-line
                description, no problem.
            arg2 (str): Description of arg2.

        Returns:
            bool: Description of return value
        """
        return True

Commit messages
---------------

The first line of the commit message have a one-line summary of the
change.  This needs to mention the class, function, or module where
relevant changes happen.  If there's an associated issue number, make
reference to it.  If it is a "fixup" commit, make reference to it.
Some examples for changes:

- limited to a method function::

    TheClassName.initialize: fix for firmware older than Y (issue #98)

- effecting multiple methods in a class::

    TheClassName: add support for very fancy feature (issue #99)

- fixing a typo or obvious mistake on a previous commit::

    AndorAtmcd: pass index to super (fixup a16bef042a41)

- documentation only::

    doc: add example for multiple cameras with hardware triggering


Test suite
----------

Most of Python Microscope is about controlling very specific hardware
and there are no realist mocks of such hardware.  Still, some parts
can be tested with::

    python setup.py test

All test units, as well as other tools for testing purposes, are part
of the :py:mod:`microscope.testsuite` package.

If your changes do not actually change a specific device, please also
include a test unit.


Copyright
=========

We do not request that copyright is assigned to us, you will remain
the copyright holder of any contribution made.  However, please ensure
that you are the copyright holder.  Depending on your contract, the
copyright holder might be your employer or university, even if you are
a student.  Ask your employer or PhD supervisor.
