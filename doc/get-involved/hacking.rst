.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

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
- Coding style is `Black <https://black.readthedocs.io/>`_
- Development sources are on `Github <repo-browse_>`_
- Bug tracker is also on `Github
  <https://github.com/python-microscope/microscope/issues>`_


Reporting issues
================

We use the github issue tracker at
`<https://github.com/python-microscope/microscope/issues>`_.  When
reporting an issue please include as much information as you can
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

- Pyro version
    If the issue only happens in the network, please also include the
    version of the Pyro package.


Requesting support for new device
=================================

To request support for a new device, or even to support for a feature
of an already supported device, open a new issue on the `issue tracker
<https://github.com/python-microscope/microscope/issues>`_.

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

Code format style
-----------------

Let us not discuss over code formatting style.  Code formatting is
handled by `Black <https://black.readthedocs.io/>`_.  Simply run
`black` at the root of the project after making changes and before
making a commit:

.. code-block:: shell

   black ./


Docstrings
----------

The API section of the documentation is generated from the inlined
docstrings.  It requires the `Google Python docstrings format
<https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
minus the type description on the list of arguments since those are
defined in the type annotations.  It looks like this::


    def func(arg1: str, arg2: int) -> bool:
        """One-line summary.

        Extended description of function.

        Args:
            arg1: Description of arg1.  This can be a multi-line
                description, no problem.
            arg2: Description of arg2.

        Returns:
            Description of return value
        """
        return True


Commit messages
---------------

The first line of the commit message have a one-line summary of the
change.  This needs to mention the class, function, or module where
relevant changes happen.  If there's an associated issue number, make
reference to it.  If it is a "fixup" commit, make reference to it.
Some examples for changes:

- limited to a method function:

    `TheClassName.enable: fix for firmware older than Y (#98)`

- effecting multiple methods in a class:

    `TheClassName: add support for very fancy feature (#99)`

- fixing a typo or obvious mistake on a previous commit:

    `AndorAtmcd: pass index to super (fixup a16bef042a41)`

- documentation only:

    `doc: add example for multiple cameras with hardware triggering`


Test suite
----------

Most of Python Microscope is about controlling very specific hardware
and there are no realist mocks of such hardware.  Still, there are
some tests written.  They can be run with `tox
<https://tox.readthedocs.io/>`_.  The repository has the required
configuration, so simply run ``tox`` at the root of the repository.

All test units, as well as other tools for testing purposes, are part
of the :mod:`microscope.testsuite` package.

If your changes do not actually change a specific device, please
include a test unit.


Copyright
=========

We do not request that copyright is assigned to us, you can remain the
copyright holder of any contribution made.  However, please ensure
that you are the copyright holder.  Depending on your contract, and
even if you are a student, the copyright holder is likely to be your
employer or university.  Ask your employer or PhD supervisor first.
