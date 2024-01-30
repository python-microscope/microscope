.. Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

Maintainer's guide
******************

This document includes information for those deeper in the project.


The NEWS file
=============

The file should only include user visible changes worth mentioning.
For example, adding support for a new device should be listed but
removing multiple lines to address code duplication should not.

It's easier to keep the ``NEWS`` file up to date as changes are made.
This prevents having to check all the changes since the last release
for such relevant changes.  Ideally, the same commit that makes the
relevant change should also add the entry to the NEWS file.


Steps to make a release
=======================

#. Check the ``NEWS`` is up to date for the next release.  Because the
   ``NEWS`` file is supposed to be kept up to date with each commit
   that introduces changes worth mentioning, there should be no need
   to add entries now.  But if so, then::

    git commit -m "maint: update NEWS for upcoming release" NEWS.rst

#. Manually add date and version for next release on ``NEWS.rst``.
   Then change the version on ``pyproject.toml``, commit it, and tag
   it::

       NEW_VERSION="X.Y.Z"  # replace this with new version number
       OLD_VERSION=`grep '^version ' pyproject.toml | sed 's,^version = "\([0-9.]*+dev\)"$,\1,'`
       python3 -c "from packaging.version import parse; assert parse('$NEW_VERSION') > parse('$OLD_VERSION');"

       sed -i 's,^version = "'$OLD_VERSION'"$,version = "'$NEW_VERSION'",' pyproject.toml
       git commit -m "maint: release $NEW_VERSION" pyproject.toml NEWS.rst
       COMMIT=$(git rev-parse HEAD | cut -c1-12)
       git tag -a -m "Added tag release-$NEW_VERSION for commit $COMMIT" release-$NEW_VERSION

   Note that we use ``release-N`` for tag and not ``v.N``.  This will
   enable us to one day perform snapshot releases with tags such as
   ``snapshot-N``.

#. Build a source and wheel distribution from a git archive export::

       rm -rf target
       git archive --format=tar --prefix="target/" release-$NEW_VERSION | tar -x
       (cd target/ ; python3 -m build)

   Performing a release from a git archive ensures that the release
   does not accidentally include modified or untracked files.  The
   wheel distribution is not for actual distribution, we only build it
   to ensure that a binary distribution can be built from the source
   distribution.

   We should probably do this from a git clone and not an archive to
   ensure that we are not using a commit that has not been pushed yet.

#. Upload source distribution to PyPI::

    twine upload -r pypi target/dist/microscope-$NEW_VERSION.tar.gz

#. Add ``+dev`` to version string and manually add a new entry on the
   ``NEWS`` file for the upcoming version::

       sed -i 's,^version = "'$NEW_VERSION'"$,version = "'$NEW_VERSION'+dev",' pyproject.toml
       # manually add new version line on NEWS.rst file
       git commit -m "maint: set version to $NEW_VERSION+dev after $NEW_VERSION release." pyproject.toml NEWS.rst
       git push upstream master
       git push upstream release-$NEW_VERSION


Documentation
=============

The documentation is generated with `Sphinx
<https://www.sphinx-doc.org/>`__, like so::

    sphinx-build -b html doc/ dist/sphinx/html
    sphinx-build -M pdflatex doc/ dist/sphinx/pdf

The API section is generated from the inline docstrings and makes use
of Sphinx's `Napoleon
<http://www.sphinx-doc.org/en/stable/ext/napoleon.html>`__ and `apidoc
<https://github.com/sphinx-contrib/apidoc>`__ extensions.


Versioning
==========

We use the style ``major.minor.patch`` for releases and haven't yet
had to deal with rc.

In between releases and snapshots, we use the ``dev`` as a local
version identifiers as per `PEP 440
<https://www.python.org/dev/peps/pep-0440/>`_ so a version string
``0.0.1+dev`` is the release ``0.0.1`` plus development changes on top
of it (and not development release for an upcoming ``0.0.1``).  With
examples:

* ``0.0.1`` - major version 0, minor version 0, patch version 1

* ``0.0.1+dev`` - not a public release.  A development build, probably
  from VCS sources, sometime *after* release ``0.0.1``.  Note the use
  of ``+`` which marks ``dev`` as a local version identifier.

* ``0.0.1.dev1`` - we do not do this.  PEP 440 states this would be
  the first development public release *before* ``0.0.1``.  We use
  ``+dev`` which are local version and not public releases.  This is
  only mentioned here to avoid confusion for people used to that
  style.


Website
=======

The sources for the https://python-microscope.org is on the repository
https://github.com/python-microscope/python-microscope.org
