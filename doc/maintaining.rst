.. Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   Permission is granted to copy, distribute and/or modify this
   document under the terms of the GNU Free Documentation License,
   Version 1.3 or any later version published by the Free Software
   Foundation; with no Invariant Sections, no Front-Cover Texts, and
   no Back-Cover Texts.  A copy of the license is included in the
   section entitled "GNU Free Documentation License".

Maintaining
***********

This document includes information for those deeper in the project.


The NEWS file
=============

The file should only include user visible changes worth mentioning.
For example, adding support for a new device should be listed but
removing multiple lines to address code duplication should not.

It's easier to keep the NEWS file up to date as changes are made.
This prevents having to check all the changes since the last release
for such relevant changes.  Ideally, the same commit that makes the
relevant change should also add the entry to the NEWS file.


Steps to make a release
=======================

Because the NEWS file is supposed to always be kept up to date, there
should be no need to check it.

#. Change version number on `setup.py` and date on `NEWS`.  Commit
   these changes only.  Note that we use `release-N` for tag and not
   `v.N`.  This will enable us to one day perform snapshot releases
   with tags such as `snapshot-N`::

    VERSION=$(python setup.py --version)
    sed -i "s,(upcoming),($(date +%Y/%m/%d))," NEWS
    git commit -m "maint: release $VERSION" setup.py NEWS
    COMMIT=$(git rev-parse HEAD | cut -c1-12)
    git tag -s -u $GPGKEY \
      -m "Added tag release-$VERSION for commit $COMMIT" release-$VERSION

#. Build a source distribution from a git archive export.  Performing
   a release from a git archive will ensure that the release will not
   accidentally include modified or untracked files::

    rm -rf target/
    git archive --format=tar --prefix="target/" HEAD | tar -x
    cd target/
    python setup.py sdist --formats=gztar

   We should probably do this from a git clone and not an archive to
   ensure that we are not using a commit that has not been pushed yet.

#. Upload and sign distribution::

    twine upload -r pypi -s -i $GPGKEY target/dist/microscope-X.tar.gz

#. Add `+dev` to version string and a new entry on the NEWS file::

    sed -i "s,\(^project_version = '[^+]*\)',\1+dev'," setup.py
    # manually add new version line on NEWS file
    git commit setup.py NEWS \
      -m "maint: set version to $VERSION+dev after $VERSION release."
    git push upstream master
    git push upstream release-$VERSION


Documentation
=============

The documentation is generated automatically with `sphinx
<https://www.sphinx-doc.org/en/master/>`_.  The API section is
generated from the inline docstrings and makes use of `Sphinx's
Napoleon extension
<http://www.sphinx-doc.org/en/stable/ext/napoleon.html>`_.  It is
generated with::

    python setup.py build_sphinx

Versioning
==========

We use the style `major.minor.patch` for releases and haven't yet had
to deal with rc.

In between releases and snapshots, we use the `dev` as a local version
identifiers as per `PEP 440
<https://www.python.org/dev/peps/pep-0440/>`_ so a version string
`0.0.1+dev` is the release `0.0.1` plus development changes on top of
it (and not development release for an upcoming `0.0.1`).  With
examples:

* `0.0.1` - major version 0, minor version 0, patch version 1

* `0.0.1+dev` - not a public release.  A development build, probably
  from VCS sources, sometime *after* release `0.0.1`.  Note the use of
  `+` which marks `dev` as a local version identifier.

* `0.0.1.dev1` - we do not do this.  PEP 440 states this would be the
  first development public release *before* `0.0.1`.  We use `+dev`
  which are local version and not public releases.  This is only
  mentioned here to avoid confusion for people used to that style.
