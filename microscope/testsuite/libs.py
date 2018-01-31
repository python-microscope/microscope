#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>
##
## Microscope is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Microscope is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""Mock hardware control shared libraries and tools for patching ctypes.

Modules that make use of a shared library for hardware control require
that library to be installed in the system at import time.  import is
required for testing and building API documentation.  However, no
machines will actually have all those libraries installed.

This module provides mocks for all C functions wrapped by microscope.
In addition, the :class:`CDLL` class can be used to patch
:class:`ctypes.CDLL` to enable the importing of all microscope
modules.  Like so::

    >>> import microscope.testsuite.libs
    >>> import ctypes
    >>> ctypes.CDLL = microscope.testsuite.libs.CDLL
    >>> import microscope._wrappers.asdk # no longer fails due to missing libasdk.so
    >>> import microscope.cameras.SDK3 # also does not fail despite calling InitialiseUtilityLibrary

Most mock libraries do not have implementations of the functions.
They can be implemented like so::

    >>> import microscope._wrappers.asdk
    >>> microscope._wrappers.asdk.Init()
    Traceback (most recent call last):
    ...
    NotImplementedError: call of mock function not yet implemented
    >>> microscope._wrappers.asdk.Init._call = lambda : "initialised"
    >>> microscope._wrappers.asdk.Init()
    'initialised'

.. todo:
   Our CDLL implementation always intercepts all libraries that we
   know about.  We may want to instead replace this with a function
   that generates a class that intercepts a subset of them.
"""

import ctypes
import inspect
import sys

class MockFuncPtr(object):
  """A mock for a C function.

  To identify where it is called unintentionally, this mock will raise
  :exc:`NotImplementedError` if it is called.  To make it callable,
  replace the :meth:`__call` method like so::

    >>> func = MockFuncPtr()
    >>> func()
    Traceback (most recent call last):
    ...
    NotImplementedError: call of mock function not yet implemented
    >>> func._call = lambda : ctypes.c_int(1)
    >>> func()
    c_int(1)

  The reason to replace `__call` instead of `__call__` is that
  implicit invocations of special methods are `not guaranteed to work
  correctly when defined in an object instance
  <https://docs.python.org/3/reference/datamodel.html#special-method-lookup>`_,
  i.e., patching `instance.__call__` may not affect `instance()`.
  This is at least true in CPython.

  .. note:
     This is meant to be a mock of `_FuncPtr` which is a class created
     on the fly in ctypes from the private `_ctypes._CFuncPtr`.
  """
  def __init__(self):
    self.argtypes = None
    self.restype = ctypes.c_int
  def _call(self, *args, **kwargs):
    raise NotImplementedError("call of mock function not yet implemented")
  def __call__(self, *args, **kwargs):
    return self._call(*args, **kwargs)


class MockSharedLib(object):
  """Base class for mock shared libraries.

  Subclasses must list the name of functions from the library it mocks
  in :attr:`functions`.

  Attributes:
    libs (list): list of library names (as passed to
      :class:`ctypes.CDLL`) that this class can mock.
    functions (list): list of of function names from the library to be
      mocked.
  """
  libs = []
  functions = []
  def __init__(self):
    for fname in self.functions:
      setattr(self, fname, MockFuncPtr())


class MockLibasdk(MockSharedLib):
  """Mock Alpao's SDK for microscope._wrappers.asdk.
  """
  libs = ['libasdk.so', 'ASDK']
  functions = [
    'asdkGet',
    'asdkGetLastError',
    'asdkInit',
    'asdkRelease',
    'asdkSend',
    'asdkSendPattern',
    'asdkSet',
  ]

class MockLibatcore(MockSharedLib):
  """Mock Andor's atcore (SDK3) for microscope.cameras.SDK3.
  """
  libs = ['atcore.so', 'atcore']
  functions = [
    'AT_Close',
    'AT_Command',
    'AT_FinaliseLibrary',
    'AT_Flush',
    'AT_GetBool',
    'AT_GetEnumCount',
    'AT_GetEnumIndex',
    'AT_GetEnumStringByIndex',
    'AT_GetEnumerated',
    'AT_GetEnumeratedCount',
    'AT_GetEnumeratedString',
    'AT_GetFloat',
    'AT_GetFloatMax',
    'AT_GetFloatMin',
    'AT_GetInt',
    'AT_GetIntMax',
    'AT_GetIntMin',
    'AT_GetString',
    'AT_GetStringMaxLength',
    'AT_InitialiseLibrary',
    'AT_IsEnumIndexAvailable',
    'AT_IsEnumIndexImplemented',
    'AT_IsEnumeratedIndexAvailable',
    'AT_IsEnumeratedIndexImplemented',
    'AT_IsImplemented',
    'AT_IsReadOnly',
    'AT_IsReadable',
    'AT_IsWritable',
    'AT_Open',
    'AT_QueueBuffer',
    'AT_RegisterFeatureCallback',
    'AT_SetBool',
    'AT_SetEnumIndex',
    'AT_SetEnumString',
    'AT_SetEnumerated',
    'AT_SetEnumeratedString',
    'AT_SetFloat',
    'AT_SetInt',
    'AT_SetString',
    'AT_UnregisterFeatureCallback',
    'AT_WaitBuffer',
  ]
  def __init__(self):
    super(MockLibatcore, self).__init__()
    ## This gets called during import of microscope.cameras.SDK3Cam
    self.AT_InitialiseLibrary._call = lambda : 0 # AT_SUCCESS

class MockLibatutility(MockSharedLib):
  """Mock Andor's atutility (SDK3) for microscope.cameras.SDK3.
  """
  libs = ['atutility.so', 'atutility']
  functions = [
    'AT_ConvertBuffer',
    'AT_ConvertBufferUsingMetadata',
    'AT_FinaliseUtilityLibrary',
    'AT_InitialiseUtilityLibrary',
  ]
  def __init__(self):
    super(MockLibatutility, self).__init__()
    ## This gets called during import of microscope.cameras.SDK3
    self.AT_InitialiseUtilityLibrary._call = lambda : 0 # AT_SUCCESS

class MockLibBMC(MockSharedLib):
  """Mock BMC's SDK for microscope._wrappers.BMC.
  """
  libs = ['libBMC.so.3', 'BMC']
  functions = [
    'BMCClose',
    'BMCConfigureLog',
    'BMCErrorString',
    'BMCGetArray',
    'BMCOpen',
    'BMCSetArray',
    'BMCVersionString',
  ]

class MockLibpvcam(MockSharedLib):
  """Mock pvcam's SDK for microscope.cameras.pvcam.
  """
  libs = ['pvcam.so', 'pvcam32', 'pvcam64']
  functions = [
    'pl_cam_close',
    'pl_cam_deregister_callback',
    'pl_cam_get_name',
    'pl_cam_get_total',
    'pl_cam_open',
    'pl_cam_register_callback',
    'pl_cam_register_callback_ex',
    'pl_cam_register_callback_ex2',
    'pl_cam_register_callback_ex3',
    'pl_create_frame_info_struct',
    'pl_create_smart_stream_struct',
    'pl_enum_str_length',
    'pl_exp_abort',
    'pl_exp_abort',
    'pl_exp_check_cont_status',
    'pl_exp_check_cont_status_ex',
    'pl_exp_check_status',
    'pl_exp_finish_seq',
    'pl_exp_get_latest_frame',
    'pl_exp_get_latest_frame_ex',
    'pl_exp_get_oldest_frame',
    'pl_exp_get_oldest_frame_ex',
    'pl_exp_setup_cont',
    'pl_exp_setup_seq',
    'pl_exp_start_cont',
    'pl_exp_start_seq',
    'pl_exp_stop_cont',
    'pl_exp_unlock_oldest_frame',
    'pl_get_enum_param',
    'pl_get_param',
    'pl_pp_reset',
    'pl_pvcam_get_ver',
    'pl_pvcam_init',
    'pl_pvcam_uninit',
    'pl_release_frame_info_struct',
    'pl_release_smart_stream_struct',
    'pl_set_param',
  ]

## Create a map of library names (as they would be named when
## constructing CDLL in any supported OS), to the mock shared library.
_lib_to_mock = dict()
for _, _cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
  if issubclass(_cls, MockSharedLib):
    for _lib in _cls.libs:
      _lib_to_mock[_lib] = _cls


class CDLL(ctypes.CDLL):
  """A replacement for ctypes.CDLL that will link our mock libraries.
  """
  def __init__(self, name, *args, **kwargs):
    if _lib_to_mock.get(name) is not None:
      self._name = name
      self._handle = _lib_to_mock[name]()
    else:
      super(CDLL, self).__init__(name, *args, **kwargs)

  def __getattr__(self, name):
    if isinstance(self._handle, MockSharedLib):
      return getattr(self._handle, name)
    else:
      super(CDLL, self).__getattr__(name)
