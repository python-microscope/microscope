#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016 David Pinto <david.pinto@bioch.ox.ac.uk>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import sys

import setuptools
import sphinx.setup_command

try:
  import sphinx.ext.apidoc as apidoc
except ImportError:
  import sphinx.apidoc as apidoc

project_name = 'microscope'
project_version = '0.1.0+dev'

extra_requires = []

## The enum34 package will cause conflicts with the builtin enum
## package so don't require it.  See
## https://bitbucket.org/stoneleaf/enum34/issues/19/enum34-isnt-compatible-with-python-36#comment-36515102
if sys.version_info >= (3, 4):
  extra_requires += ["enum34"]


## Shadow the sphinx provided command, in order to run sphinx-apidoc
## before sphinx-build.  This builds the rst files with the actual
## package inline documentation.
class BuildDoc(sphinx.setup_command.BuildDoc):
  def run(self):
    apidoc.main(["sphinx-apidoc", "--output-dir", "doc", "microscope",
                 ## TODO: a list of modules to exclude because they
                 ##       can't be imported, which will be required by
                 ##       autodoc.  They can't be imported because of
                 ##       the shared libraries are not on the system
                 ##       building the docs.  Remove this when we
                 ##       figure out mock libraries for all of them.
                 "microscope/cameras/*",
                 "microscope/mirror/*"])
    sphinx.setup_command.BuildDoc.run(self)


setuptools.setup(
  name = project_name,
  version = project_version,
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

  command_options = {
    'build_sphinx' : {
      ## This is a bit silly but the dict for command_options must be
      ## of the form '(option, (source, value))' where source is the
      ## filename where that information came from.
      'project': ('setup.py', project_name),
      'version': ('setup.py', project_version),
      'release': ('setup.py', project_version),
      'source_dir' : ('setup.py', 'doc'),
    },
  },

  cmdclass = {
    'build_sphinx' : BuildDoc,
  },
)
