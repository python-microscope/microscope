.. Copyright (C) 2021 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

Support for New Device
**********************

.. note::

   Before starting the work of adding a new device, check the `issue
   tracker <https://github.com/python-microscope/microscope/issues>`__
   first.  It is likely that someone already requested it and maybe
   someone is already working on it.  Even if they are not working on
   it they might have a slightly different model and willing to test
   your implementation on it.  Sometimes there is already a
   half-working implementation that needs testing.  If there is no
   related issue on the tracker, open one.  If there is one, comment
   that you're working on it.  This ensures that there is no
   duplication of work.

Adding support for a new device is often a relatively straightforward
job.  Doing so means:

1. Identify the correct device type and the corresponding abstract
   base class in the :mod:`microscope.abc` module.  For example,
   :class:`Camera <microscope.abc.Camera>`, :class:`Controller
   <microscope.abc.Controller>`, or :class:`LightSource
   <microscope.abc.LightSource>`.

2. Read the documentation for that class which lists the abstract
   methods and properties that need to be implemented.

3. Create a concrete class that implement those abstract methods and
   properties using the documentation provided by the device vendor.

.. note::

   As one can imagine, this apparently simple 3 step process hides a
   lot of complexity, most of it in the last step.  Surprisingly, the
   difficulty is not in writing the actual code, which is often really
   simple, but in decoding the device documentation.

Besides the different device types, which define what methods need to
be implemented, devices can also be grouped by their communication
method.  When it comes to this, most devices fall under two
categories: serial connection or C library.


Serial Communication
====================

Most microscope devices will provide a RS-232 serial interface,
sometimes with USB to serial bridges.  Typical exceptions are devices
that need to transfer large amounts of data such as cameras or
deformable mirrors.  Devices with serial interface are the easiest to
control, one only needs to find the correct commands in the manual.
Here's some tips to create a new device using serial communication:

1. Create a class that wraps the serial connection and provides the
   different commands as Python methods.  The device object then "has
   a" device connection object, and the device connection object "has
   a" serial connection object.  This will greatly simplify the code
   reducing most methods to 1-2 lines of code.

2. Beware of multiple threads controlling the device and note that
   GUIs will often have multiple threads.  Consider using
   :class:`microscope._utils.SharedSerial` or roll your own
   synchronisation logic to ensure thread safety.

3. The first argument to the class initialiser should be the port
   number which identifies the device.  Beware that the assigned port
   number might change each time the computer is restarted or even
   when the device itself is restarted.  Checks your OS documentation
   to assign fixed port number/name.

4. Beware that indexing a single byte from a byte array returns an int
   and not a byte, i.e.::

       b"CMD"[0] == b"C"  # False
       b"CMD"[0] == 65  # True
       b"CMD"[0] == ord(b"C")  # True
       b"CMD"[0:1] == b"C"  # True

   However, typically the goal often is to compare the character at a
   specific position with a specific character that signals error or
   success.  Note only do we know the exact character this will be
   done pretty much every time a command is sent to the device.  So
   declare the value in the module globals and use it internally, like
   so::

       _K_CODE = ord(b"K")


C libraries / SDKs
==================

When a device is not controlled via serial it is most likely
controlled via some vendor provided SDK.  In these cases, adding
support for such device means:

1. find the C library for the SDK;
2. create a :mod:`ctypes` wrapper to it under `microscope._wrappers`;
3. use the wrapper to add support for the new device, possibly with an
   intermediary wrapper.

.. note::

   Some vendors provide Python bindings to their SDKs which may or may
   not be worth using.  Often they are undocumented thin wrappers to
   their C library and if you use them, not only will you have to deal
   with undocumented behaviour from their C library you will also have
   to deal with the undocumented idiosyncrasies of their wrapper.

Finding the C library
---------------------

The first thing to do is to identify the correct shared library file.
i.e., the C libraries.  On Windows, these are often called dll files.
Sometimes the SDK is in C++ and there will be C bindings available.
Other times, there are SDKs in many different languages and one needs
to get the "low level libraries" for those SDKs.  It may be required
to contact the vendor directly.

There may be more than one C library required for a single device.
For example, Andor's SDK3 requires the DLLs ``atcore`` and
``atutility``.

ctypes wrapper
--------------

For each library file create one Python file with the same name under
`microscope._wrappers`.  Each of those files should load the library,
declare required constants and structures, and finally declare the
function prototypes with the required argument types and return
values.  Take a look at the existing wrappers for examples but here's
some tips to write a new one:

1. Keep the wrapper as thinner as possible.  Namely, do not have
   functions automatically check the return value or convert types.
   The wrapper should provide the exact same interface provided by the
   C library but callable from Python.  That said, do specify the
   required arguments and return type by setting the ``argtypes`` and
   ``restype`` arguments.

2. Wrap only the symbols required by Python-microscope and not every
   single symbol declared in the header file.  Wrapping only the
   required functions ensures that it will work with any version of
   the library that has the required functions.  On the other hand,
   wrapping all the symbols may lead to failures with older library
   versions because they miss something that is not even required.

3. Use the exact same names as in the C header files even if they
   don't follow Python naming conventions.  However, it is very common
   for C libraries to use a prefix for all their functions, e.g. the
   ``mirao52e`` and ``BMC`` libraries prefix all their functions with
   ``mro_`` and ``BMC`` respectively.  In such case, remove that
   prefix.

4. Typedefs are often used for function arguments, e.g., ``RESULT`` is
   the return type for all functions which is a typedef for ``int`` or
   ``HANDLE`` which is a pointer for some forwarded declared struct.
   Do declare those typedefs and use them when declaring the arguments
   and return types of functions.  This eases the comparison with the
   header files and the long-term maintenance.

5. Importing the wrapper should load the library, i.e., will call
   ``ctypes.CDLL`` or similar.  This ensures that if Python fails to
   find the library this will fail as soon as possible.  However, some
   libraries need to be "manually" initialised.  Importing the wrapper
   should not initialise the library, leave it to the user of the
   library.

6. Not all Window's DLLs use ``stdcall`` so don't assume that you need
   to use ``ctypes.WinDLL`` just because you are in Windows.  Also,
   using ``WinDLL`` incorrectly instead of ``CDLL`` will not fail but
   may lead to issues later.  So check the header files and look for
   ``__cdecl`` or ``__stdcall`` declarations.

7. Different structs may have different packing alignment.  Check it,
   i.e., look for ``#pragma pack`` and ``__atribute__((packed,
   aligned(X)))``, and set it appropriately via the ``_pack_`` class
   attribute.

8. Do not do wildcard imports, i.e., no ``from ctypes import *``.

Actual device class
-------------------

Because the thin wrapper should only declare the symbols required by
the concrete device class these two should be implemented in parallel.
Details on how to implement this devices are mainly device type
specific.


Tips to implement support for a new device
==========================================

1.  Only use named arguments and keyword arguments for the class
    ``__init__``.  This is required by the device server and also
    makes things simpler when there's multiple parent classes.

2. Avoid using the :class:`FloatingDeviceMixin
   <microscope.abc.FloatingDeviceMixin>` if possible.  Some devices
   really need it, namely cameras, but these cause issues when there
   are multiple such devices available but only a subset is to be
   used.

3. While often the end goal is to use the devices via the device
   server, avoid using it during development since it adds an extra
   layer of complexity.  Do test that it works via the device server
   in the end though.

4. Make use of the :mod:`microscope.gui` module which provides simple
   widgets to quickly test the device during development.  For
   example, if one was testing the implementation of a deformable
   mirror, they could do this on a Python shell::

       from microscope.mirrors.my_new_dm import MyNewDM

       dm = MyNewDM()

       from microscope.gui import DeformableMirrorWidget, MainWindow
       from qtpy import QtWidgets

       app = QtWidgets.QApplication([])
       widget = DeformableMirrorWidget(dm)
       window = MainWindow(widget)
       window.show()
       app.exec()

5. When documenting support for the device, use the class docstring
   and not the module docstring.  Use the module docstring if there
   are multiple device classes in the module and they share
   documentation.

6. Use `type annotations <https://docs.python.org/3/library/typing.html>`__.

7. When all is done and support for a new device is merged, do not
   forget to make reference to it on the `NEWS.rst` and
   `doc/architecture/supported-devices.rst` files.

Vendor issues
-------------

More often than not a device does not really perform according to
their documentation.  The documentation rarely includes all of the
available commands, the description or arguments in the documentation
is wrong, different models behave slightly different despite using the
same SDK, and changing settings have surprising side effects.  Despite
all this defects, vendors tend to be very protective of their
documentation and can be complicated to get a copy of it --- it's
almost as if they don't want us to use it.

Anyone implementing support for a new device is bound to find issues
with the vendor interface.  In that case, please be a good citizen and
report it back to them so that they can improve.  In addition, open an
issue on Python-Microscope tracker for `vendor issues
<https://github.com/python-microscope/vendor-issues>`__.
