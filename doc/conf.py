#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import sys

sys.path.insert(0, '../microscope')


## This should ve read from setup.py.  Maybe we should use
## pkg_resources to avoid duplication?
author = 'Micron Oxford'
project = 'Microscope'
copyright = '2017, Micron Oxford'


master_doc = 'index'


extensions = [
  'sphinx.ext.autodoc',
  'sphinx.ext.napoleon',
  'sphinx.ext.todo',
  'sphinx.ext.viewcode',
]

## Configuration for sphinx.ext.todo
todo_include_todos = True


##
## Options for HTML output
##

html_theme = 'alabaster'
html_static_path = ['_static']

html_theme_options = {
  'show_powered_by' : False,
}

## This is required for the alabaster theme
## http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
  '**': [
    'about.html',
    'navigation.html',
    'searchbox.html',
  ]
}
