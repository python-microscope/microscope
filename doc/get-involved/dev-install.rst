.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

Development Installation
************************

Development sources
===================

Microscope development sources are available on GitHub.  To install
the current development version of Microscope:

.. code-block:: shell

    git clone https://github.com/python-microscope/microscope.git
    pip install microscope/

Consider using editable mode if you plan to make changes to the
project:

.. code-block:: shell

    pip install --editable microscope/

Multiple Microscope versions
----------------------------

The Python package system does not, by default, handle multiple
versions of a package.  If installing from development sources beware
to not overwrite a previous installation.  A typical approach to
address this issue is with the use of `virtual environments
<https://packaging.python.org/tutorials/installing-packages/#creating-and-using-virtual-environments>`_.

Un-merged features
------------------

Some features are still in development and have not been merged in the
main branch.  To test such features you will need to know the branch
name and the repository where such feature is being developed.  For
example, to try Toshiki Kubo's implementation of the Mirao52e
deformable mirror::

  git remote add toshiki https://github.com/toshikikubo/microscope.git
  git fetch toshiki
  git checkout toshiki/mirao52e
  pip install ./
