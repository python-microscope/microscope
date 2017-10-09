#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016 David Pinto <david.pinto@bioch.ox.ac.uk>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import setuptools
import sys

extra_requires = []

## The enum34 package will cause conflicts with the builtin enum
## package so don't require it.  See
## https://bitbucket.org/stoneleaf/enum34/issues/19/enum34-isnt-compatible-with-python-36#comment-36515102
if sys.version_info >= (3, 4):
  extra_requires += ["enum34"]

setuptools.setup(
  name = "microscope",
  version = "0.1.0+dev",
  description = "An extensible microscope hardware interface.",
  license = "GPL-3.0+",

  ## Do not use author_email because that won't play nice once there
  ## are multiple authors.
  author = "Mick Phillips <mick.phillips@bioch.ox.ac.uk>",

  url = "https://github.com/MicronOxford/microscope",

  packages = [
    "microscope",
    "microscope.cameras",
    "microscope.lasers",
    "microscope.testsuite",
    "microscope._wrappers",
  ],

  install_requires = [
    "numpy",
    "Pyro4",
    "pyserial",
    ## We use six instead of anything else because we are already
    ## indirectly dependent on it due to serpent which is a Pyro4
    ## dependency.
    "six",
  ] + extra_requires,

  entry_points = {
    'console_scripts' : [
      'deviceserver = microscope.deviceserver:__main__',
    ]
  },

  ## https://pypi.python.org/pypi?:action=list_classifiers
  classifiers = [
    "Intended Audience :: Science/Research",
    "Topic :: Scientific/Engineering",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
  ],
  test_suite="microscope.testsuite",
)
