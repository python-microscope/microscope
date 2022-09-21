#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import datetime
import sys


sys.path.insert(0, "../microscope")


# This should ve read from setup.py.  Maybe we should use
# pkg_resources to avoid duplication?
author = "Micron Oxford"
project = "Microscope"

copyright = "%s, %s" % (datetime.datetime.now().year, author)

master_doc = "index"
nitpicky = True


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]

# autodoc_mock_imports = ["microscope._wrappers"]

# Configuration for sphinx.ext.todo
todo_include_todos = True

# Configuration for sphinx.ext.napoleon
napoleon_google_docstring = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True


#
# Options for HTML output
#

html_theme = "agogo"
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
