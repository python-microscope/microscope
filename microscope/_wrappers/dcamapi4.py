#!/usr/bin/env python3

## Copyright (C) 2022 David Miguel Susano Pinto <carandraug@gmail.com>
##
## This file is part of Microscope.
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

"""Hamamatsu DCAM-API.

.. note::

    The names of the enums, structs, and functions here are similar to
    those declared in `dcamapi4.h` and `dcamprop.h`.  The only change
    is the removal of the dcam prefix.  While the library and header
    is dcamapi, the names are actually dcamapi*, dcamdev*, dcamprop*,
    etc.  To avoid the possibility of future clash of names, we only
    dropped the dcam part from their names.

"""

import ctypes
import enum
import os

import microscope._utils


if os.name == "nt":
    _LIB = microscope._utils.library_loader("dcamapi", ctypes.WinDLL)
else:
    _LIB = microscope._utils.library_loader("libdcamapi.so", ctypes.CDLL)


if os.name == "nt":
    int32 = ctypes.c_long
    _ui32 = ctypes.c_ulong
else:
    int32 = ctypes.c_int
    _ui32 = ctypes.c_uint

int32_p = ctypes.POINTER(int32)


def _int32_overflow(x: int) -> int:
    """Convert int to signed int, with overflow if required."""
    return (x & (0x80000000 - 1)) - (x & 0x80000000)


class ERR(int, enum.Enum):
    """Enum type with signed int overflow behaviour.

    Return values from DCAM-API are an enum (signed int).  Error codes
    are negative numbers but they are declared in hex notation as
    positive numbers and rely on overflow of signed integers.  For
    example, `DCAMERR_NOCAMERA` is declared as `0x80000206` which in
    decimal is `2147484166` but because of signed integer overflow is
    actually `-2147483130`.

    We want to declare them here with the same notation used in the
    header files but Python would automatically convert to long to
    accommodate the large number.  This simulates the signed integer
    overflow behaviour that enables us to use the same notation which
    makes it easier to maintain.

    The comparison and initialisation with int may look a bit odd
    (expects a signed int that has overflown for initialisation and a
    long from Python for comparison).  This is to make it simpler its
    use.  Initialisation is done to lookup the error name using the
    return value from a C function.  Comparison, if not done against
    another enum, can use the same hexadecimal notation in C:

    >>> status_long = 0x80000206  # Python will not overflow this
    >>> status_long
    2147484166
    >>> status_int = -2147483130  # 0x80000206 if cast to signed int
    >>> ERR(status_int)
    <ERR.NOCAMERA: -2147483130>
    >>> ERR.NOCAMERA == status_int
    False
    >>> ERR.NOCAMERA == ERR.NOCAMERA
    True
    >>> ERR.NOCAMERA == 0x80000206
    True
    >>> ERR.NOCAMERA.value == status_int
    True

    While the header declares all error values in this enum, it does
    not declare all success.  Many functions return 1 (SUCCESS) but
    others return positive values whose values mean the result of
    processing, so the values are unstable and not defined by DCAMERR.
    You can use `failed()` function to check whether the function is
    success or not.

    """

    def __new__(cls, value):
        overflown = (value & (0x80000000 - 1)) - (value & 0x80000000)
        obj = int.__new__(cls, value)
        obj._value_ = overflown
        return obj

    SUCCESS = 1

    BUSY = 0x80000101
    NOTREADY = 0x80000103
    NOTSTABLE = 0x80000104
    UNSTABLE = 0x80000105
    NOTBUSY = 0x80000107
    COOLINGTROUBLE = 0x80000302
    NOTRIGGER = 0x80000303
    TEMPERATURE_TROUBLE = 0x80000304
    TOOFREQUENTTRIGGER = 0x80000305
    ABORT = 0x80000102
    TIMEOUT = 0x80000106
    LOSTFRAME = 0x80000301
    MISSINGFRAME_TROUBLE = 0x80000F06
    INVALIDIMAGE = 0x80000321
    NOMEMORY = 0x80000203
    NOMODULE = 0x80000204
    NODRIVER = 0x80000205
    NOCAMERA = 0x80000206
    NOGRABBER = 0x80000207
    INVALIDCAMERA = 0x80000806
    INVALIDHANDLE = 0x80000807
    INVALIDPARAM = 0x80000808
    INVALIDVALUE = 0x80000821
    OUTOFRANGE = 0x80000822
    NOTWRITABLE = 0x80000823
    NOTREADABLE = 0x80000824
    INVALIDPROPERTYID = 0x80000825
    NOPROPERTY = 0x80000828
    ACCESSDENY = 0x8000082C
    WRONGPROPERTYVALUE = 0x8000082E
    INVALIDFRAMEINDEX = 0x80000833
    NODEVICEBUFFER = 0x8000083B
    REQUIREDSNAP = 0x8000083C
    LESSSYSTEMMEMORY = 0x8000083F
    NOTSUPPORT = 0x80000F03
    FAILREADCAMERA = 0x83001002
    INVALIDWAITHANDLE = 0x84002001
    NEWRUNTIMEREQUIRED = 0x84002002
    NOCONNECTION = 0x80000F07
    NOTIMPLEMENT = 0x80000F02
    DEVICEINITIALIZING = 0xB0000001
    MISSPROP_TRIGGERSOURCE = 0xE0100110


class PIXELTYPE(enum.IntEnum):
    MONO8 = 0x00000001
    MONO16 = 0x00000002


class BUF_ATTACHKIND(enum.IntEnum):
    FRAME = 0


class CAP_TRANSFERKIND(enum.IntEnum):
    FRAME = 0


class CAP_STATUS(enum.IntEnum):
    ERROR = 0x0000
    BUSY = 0x0001
    READY = 0x0002
    STABLE = 0x0003
    UNSTABLE = 0x0004


class WAIT_EVENT(enum.IntEnum):
    FRAMEREADY = 0x0002


class CAP_START(enum.IntEnum):
    SEQUENCE = -1
    SNAP = 0


class IDSTR(enum.IntEnum):
    BUS = 0x04000101
    CAMERAID = 0x04000102
    VENDOR = 0x04000103
    MODEL = 0x04000104
    CAMERAVERSION = 0x04000105
    DRIVERVERSION = 0x04000106
    MODULEVERSION = 0x04000107
    DCAMAPIVERSION = 0x0400010


class WAIT_TIMEOUT(enum.IntEnum):
    INFINITE = ctypes.c_int(0x80000000).value


class PROP_OPTION(enum.IntEnum):
    PRIOR = 0xFF000000
    NEXT = 0x01000000
    NEAREST = 0x80000000
    SUPPORT = 0x00000000
    UPDATED = 0x00000001
    VOLATILE = 0x00000002
    ARRAYELEMENT = 0x00000004
    NONE = 0x00000000


class tag_dcam(ctypes.Structure):
    pass


HDCAM = ctypes.POINTER(tag_dcam)


class DCAMWAIT(ctypes.Structure):
    pass


HDCAMWAIT = ctypes.POINTER(DCAMWAIT)


class GUID(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("Data1", _ui32),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class API_INIT(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("iDeviceCount", int32),
        ("reserved", int32),
        ("initoptionbytes", int32),
        ("initoption", int32_p),
        ("guid", GUID),
    ]


class DEV_OPEN(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("index", int32),
        ("hdcam", HDCAM),
    ]


class DEV_STRING(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("iString", int32),
        ("text", ctypes.c_char_p),
        ("textbytes", int32),
    ]


class PROP_ATTR(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("cbSize", int32),
        ("iProp", int32),
        ("option", int32),
        ("iReserved1", int32),
        ("attribute", int32),
        ("iGroup", int32),
        ("iUnit", int32),
        ("attribute2", int32),
        ("valuemin", ctypes.c_double),
        ("valuemax", ctypes.c_double),
        ("valuestep", ctypes.c_double),
        ("valuedefault", ctypes.c_double),
        ("nMaxChannel", int32),
        ("iReserved3", int32),
        ("nMaxView", int32),
        ("iProp_NumberOfElement", int32),
        ("iProp_ArrayBase", int32),
        ("iPropStep_Element", int32),
    ]


class PROP_VALUETEXT(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("cbSize", int32),
        ("iProp", int32),
        ("value", ctypes.c_double),
        ("text", ctypes.c_char_p),
        ("textbytes", int32),
    ]


class TIMESTAMP(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("sec", _ui32),
        ("microsec", int32),
    ]


class CAP_TRANSFERINFO(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("iKind", int32),
        ("nNewestFrameIndex", int32),
        ("nFrameCount", int32),
    ]


class BUF_FRAME(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("iKind", int32),
        ("option", int32),
        ("iFrame", int32),
        ("buf", ctypes.c_void_p),
        ("rowbytes", int32),
        ("type", ctypes.c_int),  # actually, PIXELTYPE which is an enum
        ("width", int32),
        ("height", int32),
        ("left", int32),
        ("top", int32),
        ("timestamp", TIMESTAMP),
        ("framestamp", int32),
        ("camerastamp", int32),
    ]


class WAIT_OPEN(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("supportevent", int32),
        ("hwait", HDCAMWAIT),
        ("hdcam", HDCAM),
    ]


class WAIT_START(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ("size", int32),
        ("eventhappened", int32),
        ("eventmask", int32),
        ("timeout", int32),
    ]


class PROPATTRIBUTE(enum.IntEnum):
    ATTR_HASVALUETEXT = 0x10000000
    ATTR_WRITABLE = 0x00020000
    ATTR_READABLE = 0x00010000
    ATTR_ACCESSREADY = 0x00002000
    ATTR_ACCESSBUSY = 0x00001000
    TYPE_MODE = 0x00000001
    TYPE_LONG = 0x00000002
    TYPE_REAL = 0x00000003
    TYPE_MASK = 0x0000000F


class PROPATTRIBUTE2(enum.IntEnum):
    ATTR2_ARRAYBASE = 0x08000000
    ATTR2_ARRAYELEMENT = 0x04000000


class PROPMODEVALUE(enum.IntEnum):
    TRIGGERSOURCE__INTERNAL = 1
    TRIGGERSOURCE__EXTERNAL = 2
    TRIGGERSOURCE__SOFTWARE = 3

    TRIGGERACTIVE__EDGE = 1
    TRIGGERACTIVE__LEVEL = 2

    TRIGGER_MODE__NORMAL = 1

    TRIGGERPOLARITY__NEGATIVE = 1
    TRIGGERPOLARITY__POSITIVE = 2

    BINNING__1 = 1
    BINNING__2 = 2
    BINNING__4 = 4
    BINNING__8 = 8
    BINNING__16 = 16
    BINNING__1_2 = 102
    BINNING__2_4 = 204

    MODE__OFF = 1
    MODE__ON = 2


class IDPROP(enum.IntEnum):
    TRIGGERSOURCE = 0x00100110
    TRIGGERACTIVE = 0x00100120
    TRIGGER_MODE = 0x00100210
    TRIGGERPOLARITY = 0x00100220
    TRIGGER_CONNECTOR = 0x00100230
    EXPOSURETIME = 0x001F0110
    TIMING_MINTRIGGERINTERVAL = 0x00403050
    BINNING = 0x00401110
    BINNING_INDEPENDENT = 0x00401120
    BINNING_HORZ = 0x00401130
    BINNING_VERT = 0x00401140
    IMAGE_WIDTH = 0x00420210
    IMAGE_HEIGHT = 0x00420220
    IMAGE_PIXELTYPE = 0x00420270


def _add_prototype(name, argtypes, restype=ctypes.c_int):
    prototype = getattr(_LIB, name)
    prototype.argtypes = argtypes
    prototype.restype = restype
    return prototype


api_init = _add_prototype("dcamapi_init", [ctypes.POINTER(API_INIT)])
api_uninit = _add_prototype("dcamapi_uninit", [])

dev_open = _add_prototype("dcamdev_open", [ctypes.POINTER(DEV_OPEN)])
dev_close = _add_prototype("dcamdev_close", [HDCAM])

cap_start = _add_prototype("dcamcap_start", [HDCAM, int32])
cap_stop = _add_prototype("dcamcap_stop", [HDCAM])
cap_status = _add_prototype("dcamcap_status", [HDCAM, int32_p])

dev_getstring = _add_prototype(
    "dcamdev_getstring", [HDCAM, ctypes.POINTER(DEV_STRING)]
)

prop_getattr = _add_prototype(
    "dcamprop_getattr", [HDCAM, ctypes.POINTER(PROP_ATTR)]
)
prop_getvalue = _add_prototype(
    "dcamprop_getvalue", [HDCAM, int32, ctypes.POINTER(ctypes.c_double)]
)
prop_setvalue = _add_prototype(
    "dcamprop_setvalue", [HDCAM, int32, ctypes.c_double]
)
prop_queryvalue = _add_prototype(
    "dcamprop_queryvalue",
    [HDCAM, int32, ctypes.POINTER(ctypes.c_double), int32],
)
prop_getnextid = _add_prototype("dcamprop_getnextid", [HDCAM, int32_p, int32])
prop_getname = _add_prototype(
    "dcamprop_getname",
    [HDCAM, int32, ctypes.c_char_p, int32],
)
prop_getvaluetext = _add_prototype(
    "dcamprop_getvaluetext", [HDCAM, ctypes.POINTER(PROP_VALUETEXT)]
)

buf_alloc = _add_prototype("dcambuf_alloc", [HDCAM, int32])
buf_release = _add_prototype("dcambuf_release", [HDCAM, int32])
buf_copyframe = _add_prototype(
    "dcambuf_copyframe", [HDCAM, ctypes.POINTER(BUF_FRAME)]
)

cap_start = _add_prototype("dcamcap_start", [HDCAM, int32])
cap_stop = _add_prototype("dcamcap_stop", [HDCAM])
cap_firetrigger = _add_prototype("dcamcap_firetrigger", [HDCAM, int32])

cap_status = _add_prototype("dcamcap_status", [HDCAM, int32_p])
cap_transferinfo = _add_prototype(
    "dcamcap_transferinfo", [HDCAM, ctypes.POINTER(CAP_TRANSFERINFO)]
)

wait_open = _add_prototype("dcamwait_open", [ctypes.POINTER(WAIT_OPEN)])
wait_close = _add_prototype("dcamwait_close", [HDCAMWAIT])
wait_start = _add_prototype(
    "dcamwait_start", [HDCAMWAIT, ctypes.POINTER(WAIT_START)]
)
wait_abort = _add_prototype("dcamwait_abort", [HDCAMWAIT])


def failed(status: int) -> bool:
    """Utility function declared in dcamapi4.h"""
    return status < 0
