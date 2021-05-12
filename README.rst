Python-Microscope
*****************

.. image:: https://github.com/python-microscope/python-microscope.org/raw/master/_static/microscope-logo-96-dpi.png
   :align: center
   :alt: Python-Microscope logo

Python's ``microscope`` package is a free and open source library for:

* control of local and remote microscope devices;
* aggregation of microscope devices into complex microscopes;
* automate microscope experiments with hardware triggers.

It is aimed at those that are building their own microscopes or want
programmatic control for microscope experiments.  More details can be
found in the paper `Python-Microscope: High performance control of
arbitrarily complex and scalable bespoke microscopes
<https://www.biorxiv.org/content/10.1101/2021.01.18.427171v1>`__ and
in the `online documentation <https://python-microscope.org/>`__.

Python Microscope source distribution are available in `PyPI
<https://pypi.python.org/pypi/microscope>`__ and can be easily
installed with ``pip``::

    pip install microscope

Alternatively, the development sources are available on `github
<https://github.com/python-microscope/microscope.git>`__.

This package does *not* provide a graphical user interface that a
typical microscope user would expect.  Instead, it provides the
foundation over which such interfaces can be built.  For a microscope
graphical user interface in Python consider using `Microscope-Cockpit
<https://www.micron.ox.ac.uk/software/cockpit/>`__.
