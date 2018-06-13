#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016 David Pinto <david.pinto@bioch.ox.ac.uk>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import setuptools
import setuptools.command.sdist
import sys

import sphinx.setup_command

try: # In sphinx 1.7, apidoc was moved to the ext subpackage
  import sphinx.ext.apidoc as apidoc
  ## In addition of changing the subpackage, the signature for main()
  ## also changed https://github.com/sphinx-doc/sphinx/issues/5088 If
  ## we are building in older versions, the program name needs to be
  ## included in the args passed to apidoc.main()
  apidoc_ini_args = []
except ImportError:
  import sphinx.apidoc as apidoc
  apidoc_ini_args = ['sphinx-apidoc']

try: # In Python 3.3, mock was merged into unittest package
  import unittest.mock as mock
except ImportError:
  import mock

import microscope.testsuite.libs

project_name = 'microscope'
project_version = '0.2.0'

extra_requires = []

## The enum34 package will cause conflicts with the builtin enum
## package so don't require it.  See
## https://bitbucket.org/stoneleaf/enum34/issues/19/enum34-isnt-compatible-with-python-36#comment-36515102
if sys.version_info < (3, 4):
  extra_requires += ["enum34"]


## Shadow the sphinx provided command, in order to run sphinx-apidoc
## before sphinx-build.  This builds the rst files with the actual
## package inline documentation.
class BuildDoc(sphinx.setup_command.BuildDoc):
  @mock.patch('ctypes.CDLL', new=microscope.testsuite.libs.CDLL)
  def run(self):
    apidoc.main(apidoc_ini_args + [
                 "--separate", # each module on its own page
                 "--module-first",
                 "--output-dir", "doc/api",
                 "microscope"])
    sphinx.setup_command.BuildDoc.run(self)

## Modify the sdist command class to include extra files in the source
## distribution.  Seems a bit ridiculous that we have to do this but
## the only alternative is to have a MANIFEST file and we don't want
## to have yet another configuration file.
##
## The package_data (from setuptools) and data_files (from distutils)
## options are for files that will be installed and we don't want to
## install this files, we just want them on the source distribution
## for user information.
manifest_files = [
  "COPYING",
  "NEWS",
  "README",
]
class sdist(setuptools.command.sdist.sdist):
  def make_distribution(self):
    self.filelist.extend(manifest_files)
    setuptools.command.sdist.sdist.make_distribution(self)


setuptools.setup(
  name = project_name,
  version = project_version,
  description = "An extensible microscope hardware interface.",
  long_description = open('README', 'r').read(),
  license = "GPL-3.0+",

  ## We need an author and an author_email value or PyPI rejects us.
  ## For multiple authors, they tell us to get a mailing list :/
  author = "See homepage for a complete list of contributors",
  author_email = " ",

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
      ## This seems a bit silly but the dict for command_options must
      ## be of the form '(option, (source, value))' where source is
      ## the filename where that information came from.
      'project': ('setup.py', project_name),
      'version': ('setup.py', project_version),
      'release': ('setup.py', project_version),
      'source_dir' : ('setup.py', 'doc'),
    },
  },

  cmdclass = {
    'build_sphinx' : BuildDoc,
    'sdist' : sdist,
  },
)
