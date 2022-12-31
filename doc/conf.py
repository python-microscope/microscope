#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import ctypes
import datetime
import sys
import unittest.mock


sys.path.insert(0, "../microscope")


# autodoc imports the modules to be documented.  Modules that wrap the
# device C libraries will load that library.  This would require all
# device libraries to be available to build the documentation.
# autodoc can mocks different modules (see `autodoc_mock_imports`) but
# that's not enough for all of our cases.


def patch_cdll():
    real_c_dll = ctypes.CDLL

    mocked_c_libs = [
        # Andor's SDK for (EM)CCD cameras.  Loading of this libary
        # should be in a separate microcope._wrappers.atmcd module and
        # then autodoc could just mock it.
        "atmcd32d",
        "atmcd32d.so",
        "atmcd64d",
        "atmcd64d.so",
        # pvcam's SDK.  Loading of this shared library should be in a
        # separate microcope._wrappers.pvcam module and then autodoc
        # could just mock it.
        "pvcam.so",
        "pvcam32",
        "pvcam64",
    ]

    def cdll_diversion(name, *args, **kwargs):
        if name in mocked_c_libs:
            return unittest.mock.MagicMock()
        else:
            return real_c_dll(name, *args, **kwargs)

    ctypes.WinDLL = cdll_diversion
    ctypes.CDLL = cdll_diversion


patch_cdll()


def patch_sizeof():
    # autodoc is mocking microscope._wrappers.dcamapi4 but we create
    # one of these structs for a singleton.
    real_sizeof = ctypes.sizeof

    def sizeof_diversion(struct):
        if (
            hasattr(struct, "___sphinx_mock__")
            and str(struct) == "microscope._wrappers.dcamapi4.API_INIT"
        ):
            return 40  # doesn't really matter
        else:
            return real_sizeof(struct)

    ctypes.sizeof = sizeof_diversion


patch_sizeof()


# This should ve read from setup.py.  Maybe we should use
# pkg_resources to avoid duplication?
author = ""
project = "Microscope"

copyright = "%s, %s" % (datetime.datetime.now().year, author)

master_doc = "index"
# nitpicky = True


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]

# Configuration for sphinx.ext.autodoc
autodoc_mock_imports = [
    "microscope._wrappers",
    "microscope.cameras._SDK3",  # should go into microscope._wrappers
    "picamera",
    "picamera.array",
    "RPi",
    "servicemanager",
    "win32service",
    "win32serviceutil",
]

# Configuration for sphinx.ext.intersphinx
intersphinx_mapping = {
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pyro4": ("https://pyro4.readthedocs.io/en/stable/", None),
    "pyserial": ("https://pyserial.readthedocs.io/en/latest/", None),
    "python": ("https://docs.python.org/3", None),
}

# Configuration for sphinx.ext.napoleon
napoleon_google_docstring = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = False

# Configuration for sphinx.ext.todo
todo_include_todos = True


#
# Options for HTML output
#

# html_theme = "agogo"
html_static_path = ["_static"]
html_title = "Python Microscope documentation"
html_short_title = "import microscope"
html_show_copyright = False
html_show_sphinx = False
html_copy_source = False
html_show_sourcelink = False

rst_prolog = """
.. _repo-browse: https://github.com/python-microscope/microscope
.. _repo-vcs: https://github.com/python-microscope/microscope.git
.. _gpl-licence: https://www.gnu.org/licenses/gpl-3.0.html
.. _cockpit-link: https://github.com/MicronOxford/cockpit/
"""
