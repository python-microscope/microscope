#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016 David Miguel Susano Pinto <carandraug@gmail.com>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import distutils.cmd

import setuptools
import setuptools.command.sdist


project_name = "microscope"
project_version = "0.7.0"


# setup.py is used for both maintainers actions (build documentation,
# run testuite, etc), and users actions (mainly install).  We need to
# be careful to not require maintainer tools (such as sphinx) for
# users actions.  See issue #47.

has_sphinx = True
try:
    import sphinx.setup_command
except ImportError:
    has_sphinx = False


# Shadow the sphinx provided command, in order to run sphinx-apidoc
# before sphinx-build.  This builds the rst files with the actual
# package inline documentation.
if has_sphinx:
    try:  # In sphinx 1.7, apidoc was moved to the ext subpackage
        import sphinx.ext.apidoc as apidoc

        # In addition of changing the subpackage, the signature for main()
        # also changed https://github.com/sphinx-doc/sphinx/issues/5088 If
        # we are building in older versions, the program name needs to be
        # included in the args passed to apidoc.main()
        apidoc_ini_args = []
    except ImportError:
        import sphinx.apidoc as apidoc

        apidoc_ini_args = ["sphinx-apidoc"]

    class BuildDoc(sphinx.setup_command.BuildDoc):
        def run(self):
            apidoc.main(
                apidoc_ini_args
                + [
                    "--separate",  # each module on its own page
                    "--private",  # include private modules
                    "--module-first",
                    "--tocfile",
                    "index",
                    "--output-dir",
                    "doc/api",
                    "microscope",
                    # exclude the testsuite
                    "microscope/testsuite/",
                    # exclude the wrappers to shared libraries
                    "microscope/_wrappers/",
                    # exclude the deprecated devices and deviceserver that
                    # are kept for backwards compatibility only.
                    "microscope/devices.py",
                    "microscope/deviceserver.py",
                    "microscope/lasers/",
                    "microscope/cameras/_SDK3.py",
                    "microscope/cameras/_SDK3Cam.py",
                ]
            )
            super().run()

else:

    class BuildDoc(distutils.cmd.Command):
        user_options = []

        def __init__(self, *args, **kwargs):
            raise RuntimeError("sphinx is required to build the documentation")


# Modify the sdist command class to include extra files in the source
# distribution.  Seems a bit ridiculous that we have to do this but
# the only alternative is to have a MANIFEST file and we don't want
# to have yet another configuration file.
#
# The package_data (from setuptools) and data_files (from distutils)
# options are for files that will be installed and we don't want to
# install this files, we just want them on the source distribution
# for user information.
manifest_files = [
    "COPYING",
    "NEWS.rst",
    "README.rst",
    "INSTALL.rst",
]


class sdist(setuptools.command.sdist.sdist):
    def make_distribution(self):
        self.filelist.extend(manifest_files)
        setuptools.command.sdist.sdist.make_distribution(self)


setuptools.setup(
    name=project_name,
    version=project_version,
    description="An interface for control of microscope devices.",
    long_description=open("README.rst", "r").read(),
    long_description_content_type="text/x-rst",
    license="GPL-3.0+",
    # We need an author and an author_email value or PyPI rejects us.
    # For email address, when there are multiple authors, they tell us
    # to get a mailing list :/
    author="See homepage for a complete list of contributors",
    author_email=" ",
    url="https://www.python-microscope.org",
    download_url="https://pypi.org/project/microscope/",
    project_urls={
        "Documentation": "https://www.python-microscope.org/doc/",
        "Source": "https://github.com/python-microscope/microscope",
        "Release notes": "https://www.python-microscope.org/doc/news.html",
        "Tracker": "https://github.com/python-microscope/microscope",
    },
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "Pillow",
        "Pyro4",
        "hidapi",
        "numpy",
        "pyserial",
        "scipy",
    ],
    extras_require={"GUI": ["PySide2"]},
    entry_points={
        "console_scripts": [
            "device-server = microscope.device_server:_setuptools_entry_point",
            "deviceserver = microscope.device_server:_setuptools_entry_point",
            "microscope-gui = microscope.gui:_setuptools_entry_point [GUI]",
        ]
    },
    # https://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    test_suite="microscope.testsuite",
    command_options={
        "build_sphinx": {
            # The dict for command_options must be of the form
            # '(option, (source, value))' where source is the
            # filename where that information came from.
            "project": ("setup.py", project_name),
            "version": ("setup.py", project_version),
            "release": ("setup.py", project_version),
            "source_dir": ("setup.py", "doc"),
        },
    },
    cmdclass={
        "build_sphinx": BuildDoc,
        "sdist": sdist,
    },
)
