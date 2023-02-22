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

"""Hamamatsu cameras.

Hamamatsu cameras are supported through `DCAM-API
<https://dcam-api.com/>`_, Hamamatsu's library for all of its digital
cameras.  DCAM-API needs to be installed.  It can be downloaded from
its website.  There is a Linux version mentioned on their website but
is not listed for download, you will need to request it from the
vendor.

Helper commands
===============

This module has the ``list-devices`` and ``list-properties`` commands
to help in debugging.  ``list-devices`` lists all Hamamatsu devices
and their device ID as required to construct :class:`.HamamatsuCamera`
while ``list-properties`` lists all the properties and their values
for a given camera.

Run ``python -m microscope.cameras.hamamatsu -h`` for details.

"""

import argparse
import ctypes
import logging
import math
import sys
import threading
import typing

import numpy as np

import microscope
import microscope.abc


try:
    import microscope._wrappers.dcamapi4 as dcam
except Exception as e:
    raise microscope.LibraryLoadError(e) from e


_logger = logging.getLogger(__name__)


_DCAM_BINNING_TO_MICROSCOPE = {
    dcam.PROPMODEVALUE.BINNING__1: microscope.Binning(1, 1),
    dcam.PROPMODEVALUE.BINNING__2: microscope.Binning(2, 2),
    dcam.PROPMODEVALUE.BINNING__4: microscope.Binning(4, 4),
    dcam.PROPMODEVALUE.BINNING__8: microscope.Binning(8, 8),
    dcam.PROPMODEVALUE.BINNING__16: microscope.Binning(16, 16),
    dcam.PROPMODEVALUE.BINNING__1_2: microscope.Binning(1, 2),
    dcam.PROPMODEVALUE.BINNING__2_4: microscope.Binning(2, 4),
}


_MICROSCOPE_BINNING_TO_DCAM = {
    v: k for (k, v) in _DCAM_BINNING_TO_MICROSCOPE.items()
}


# Maps (TriggerType, TriggerMode) combinations to DCAM's
# (TRIGGERACTIVE, TRIGGERPOLARITY) *when* TRIGGERSOURCE is EXTERNAL.
_MICROSCOPE_TRIGGER_TO_DCAM_EXTERNAL = {
    (microscope.TriggerType.RISING_EDGE, microscope.TriggerMode.ONCE): (
        dcam.PROPMODEVALUE.TRIGGERACTIVE__EDGE,
        dcam.PROPMODEVALUE.TRIGGERPOLARITY__POSITIVE,
    ),
    (microscope.TriggerType.HIGH, microscope.TriggerMode.BULB): (
        dcam.PROPMODEVALUE.TRIGGERACTIVE__LEVEL,
        dcam.PROPMODEVALUE.TRIGGERPOLARITY__POSITIVE,
    ),
    (microscope.TriggerType.FALLING_EDGE, microscope.TriggerMode.ONCE): (
        dcam.PROPMODEVALUE.TRIGGERACTIVE__EDGE,
        dcam.PROPMODEVALUE.TRIGGERPOLARITY__NEGATIVE,
    ),
    (microscope.TriggerType.LOW, microscope.TriggerMode.BULB): (
        dcam.PROPMODEVALUE.TRIGGERACTIVE__LEVEL,
        dcam.PROPMODEVALUE.TRIGGERPOLARITY__NEGATIVE,
    ),
}


_DCAM_EXTERNAL_TRIGGER_TO_MICROSCOPE = {
    v: k for (k, v) in _MICROSCOPE_TRIGGER_TO_DCAM_EXTERNAL.items()
}


def _status_to_error(status: int) -> str:
    """Converts a DCAMAPI4 status code into a string with name and code.

    The string returned refers to the name and the error code in
    hexadecimal notation, e.g,::

      >>> status = -2147483130  # return code from some DCAM API function
      >>> _status_to_error(status)
      'NOCAMERA[0x80000206]'

    The name is more human readable but we don't list all the error
    status in the header file, only the most common, and even if we
    did list them all, there are some that not listed.

    The status code in hexadecimal notation with uint32 overflow
    behaviour is the same used in the dcamapi4 header file.  This
    makes debugging easier because we can just search for that code
    there to find additional information.

    """
    try:
        err = dcam.ERR(status)
    except ValueError:
        name = ""
    else:
        name = err.name
    return "{}[{:#010x}]".format(name, status & 0x8FFFFFFF)


def _call(f: typing.Callable[..., int], *args) -> None:
    """Call a C function from dcamapi4.

    This is an helper function for the most typical case of checking
    the return value for failure and raising an exception if so.  For
    special handling of certain codes, do it yourself.

    """
    status = f(*args)
    if dcam.failed(status):
        raise microscope.DeviceError(
            "%s failed: %s" % (f.__name__, _status_to_error(status))
        )


def _create_struct_with_size(
    stype: typing.Type[ctypes.Structure],
) -> ctypes.Structure:
    s = stype()
    s.size = ctypes.sizeof(stype)
    return s


def _create_struct_with_cbSize(
    stype: typing.Type[ctypes.Structure],
) -> ctypes.Structure:
    s = stype()
    s.cbSize = ctypes.sizeof(stype)
    return s


def _create_devstring_with_length(
    nbytes: int,
) -> typing.Tuple[dcam.DEV_STRING, ctypes.c_char]:
    # FIXME: the type annotation is not quite right, we actually
    #        return a ctypes array of c_char as the second value.
    devstr = _create_struct_with_size(dcam.DEV_STRING)
    devstr.textbytes = nbytes
    strbuf = ctypes.create_string_buffer(nbytes)
    devstr.text = ctypes.cast(ctypes.pointer(strbuf), ctypes.c_char_p)
    # We need to return the strbuf because otherwise it is destroyed
    # and the pointer in devstr will be wrong (this is what should
    # happen.  In practice, it seems that Python does not clean up
    # string buffers after they have been destructed.  Still, one day
    # this might change so better do it properly).
    return devstr, strbuf


def _create_WAIT_OPEN(hdcam: dcam.HDCAM) -> dcam.WAIT_OPEN:
    wait_open = _create_struct_with_size(dcam.WAIT_OPEN)
    wait_open.hdcam = hdcam
    return wait_open


def _get_device_string(
    dev: dcam.HDCAM, devstr: dcam.DEV_STRING, idstr: dcam.IDSTR
) -> str:
    devstr.iString = idstr
    _call(dcam.dev_getstring, dev, devstr)
    return devstr.text.decode()


def _get_mode_prop_text(
    hdcam: dcam.HDCAM,
    property_id: dcam.int32,
    property_value: ctypes.c_double,
) -> str:
    strbuf = ctypes.create_string_buffer(64)
    vtxt = _create_struct_with_cbSize(dcam.PROP_VALUETEXT)
    vtxt.iProp = property_id
    vtxt.value = property_value
    vtxt.text = ctypes.cast(ctypes.pointer(strbuf), ctypes.c_char_p)
    vtxt.textbytes = ctypes.sizeof(strbuf)
    _call(dcam.prop_getvaluetext, hdcam, ctypes.byref(vtxt))
    return strbuf.value.decode()


class _DCAM_API:
    """Kind of a singleton.

    Initializes DCAM-API the first time it's needed, and closes it
    when no longer needed.

    """

    _api = _create_struct_with_size(dcam.API_INIT)
    _counter = 0
    _lock = threading.Lock()

    def __init__(self):
        with _DCAM_API._lock:
            if _DCAM_API._counter == 0:
                _logger.info("DCAM-API counter at zero: initialising")
                status = dcam.api_init(ctypes.byref(_DCAM_API._api))
                if status == dcam.ERR.NOCAMERA.value:
                    _logger.error("DCAM-API failed to init: DCAMERR_NOCAMERA")
                    raise microscope.LibraryLoadError(
                        "DCAM-API failed to initialise because it"
                        " found no devices"
                    )
                elif dcam.failed(status):
                    _logger.error("DCAM-API failed to init")
                    raise microscope.DeviceError(
                        "dcamapi_init failed: %s" % _status_to_error(status)
                    )
                _logger.info("DCAM-API: found %d device(s)" % self.n_devices)
            _DCAM_API._counter += 1

    def __del__(self):
        with _DCAM_API._lock:
            _DCAM_API._counter -= 1
            if _DCAM_API._counter == 0:
                _logger.info("DCAM-API counter at zero: uninitialising")
                status = dcam.api_uninit()
                if dcam.failed(status):
                    _logger.warning(
                        "Failed to uninitialise the DCAMAPI: %s",
                        _status_to_error(status),
                    )

    @property
    def n_devices(self) -> int:
        return _DCAM_API._api.iDeviceCount


class HamamatsuCamera(microscope.abc.Camera):
    """Hamamatsu Camera.

    Args:
        camera_id: This is the ``DCAM_IDSTR_CAMERAID`` value, all of
            the characters including ``S/N:`` or similar if it is
            present.  This value will be the serial number if it can
            be retrieved from the device.  If not, it will be a bus
            specific string, e.g. ``"COM1"``.

            The expected value can be obtained for all available
            devices running ``python -m microscope.cameras.hamamatsu
            list-devices``.

    """

    def __init__(self, camera_id: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hdcam = dcam.HDCAM()  # NULL pointer
        self._api = _DCAM_API()
        self._frame = _create_struct_with_size(dcam.BUF_FRAME)
        self._buffer = np.empty((0, 0), dtype=np.uint8)

        devstr, devstrbuf = _create_devstring_with_length(64)
        for idx in range(self._api.n_devices):
            hdcam = ctypes.cast(ctypes.cast(idx, ctypes.c_void_p), dcam.HDCAM)
            this_cid = _get_device_string(hdcam, devstr, dcam.IDSTR.CAMERAID)
            _logger.debug("Found device with CAMERAID '%s'", this_cid)
            if this_cid == camera_id:
                sopen = _create_struct_with_size(dcam.DEV_OPEN)
                sopen.index = idx
                try:
                    _call(dcam.dev_open, ctypes.byref(sopen))
                except microscope.DeviceError as err:
                    raise microscope.InitialiseError() from err

                self._hdcam = sopen.hdcam
                break
        else:
            raise microscope.InitialiseError(
                "Failed to find an Hamamatsu device with camera id: %s"
                % camera_id
            )

        self._wait_open = _create_WAIT_OPEN(self._hdcam)

        self._wait_start = _create_struct_with_size(dcam.WAIT_START)
        self._wait_start.eventmask = dcam.WAIT_EVENT.FRAMEREADY
        # We will wait for one second and not forever because when
        # disable() is called, it joins the fetch thread (where this
        # timeout is used) before aborting the waiting (which is done
        # in _do_disable).  Maybe that should be changed.
        self._wait_start.timeout = 1000  # milliseconds

        self._init_method_check_wait_for_frameready_support()

        prop_attr = _create_struct_with_cbSize(dcam.PROP_ATTR)
        prop_value = ctypes.c_double(0.0)

        def supports_property(prop_id: dcam.IDPROP) -> bool:
            prop_attr.iProp = prop_id
            status = dcam.prop_getattr(self._hdcam, ctypes.byref(prop_attr))
            return not dcam.failed(status)

        self._supports_independent_binning = supports_property(
            dcam.IDPROP.BINNING_INDEPENDENT
        )

        # We can't query the sensor size, we can only get the image
        # size which will be affected by binning and subarray (ROI).
        # So we get it now before we start messing around.
        self._sensor_shape = (
            self._get_long_property(dcam.IDPROP.IMAGE_WIDTH),
            self._get_long_property(dcam.IDPROP.IMAGE_HEIGHT),
        )

        self._init_method_add_all_properties()
        self._init_method_set_default_trigger_configuration()

    def _init_method_check_wait_for_frameready_support(self) -> None:
        # Check if this camera supports FRAMEREADY events which we
        # need to handle image acquisition.  Not sure if there is any
        # camera that does not support it but doesn't hurt to check.
        self._wait_open = _create_WAIT_OPEN(self._hdcam)
        _call(dcam.wait_open, ctypes.byref(self._wait_open))
        if not self._wait_open.supportevent & dcam.WAIT_EVENT.FRAMEREADY:
            microscope.MicroscopeError(
                "this device is not supported because it has no"
                " support for FRAMEREADY events"
            )
        _call(dcam.wait_close, self._wait_open.hwait)

    def _init_method_set_default_trigger_configuration(self) -> None:
        # We only use DCAM's trigger mode normal.  If this device does
        # not support it, then we don't know what to do.
        self._set_long_property(
            dcam.IDPROP.TRIGGER_MODE, dcam.PROPMODEVALUE.TRIGGER_MODE__NORMAL
        )
        self.set_trigger(
            microscope.TriggerType.SOFTWARE, microscope.TriggerMode.ONCE
        )

    def _init_method_add_all_properties(self) -> None:
        """Add all properties as settings during __init__."""
        prop_id = dcam.int32(0)  # start at zero, stop when it errors
        prop_name = ctypes.create_string_buffer(64)
        prop_attr = _create_struct_with_cbSize(dcam.PROP_ATTR)
        prop_value = ctypes.c_double(0.0)
        while True:
            status = dcam.prop_getnextid(
                self._hdcam,
                ctypes.byref(prop_id),
                dcam.PROP_OPTION.SUPPORT,
            )
            if dcam.ERR(status) == dcam.ERR.NOPROPERTY:
                break
            elif dcam.failed(status):
                raise microscope.DeviceError(
                    "dcamprop_getnextif failed: %s"
                    % (_status_to_error(status))
                )

            _call(
                dcam.prop_getname,
                self._hdcam,
                prop_id,
                prop_name,
                ctypes.sizeof(prop_name),
            )
            name = prop_name.value.decode()

            if name in self._settings:
                raise microscope.MicroscopeError(
                    "duplicated property '%s'" % name
                )

            prop_attr.iProp = prop_id
            _call(dcam.prop_getattr, self._hdcam, ctypes.byref(prop_attr))

            # TODO: no support for array properties yet.  Shouldn't be
            # too hard though.
            if prop_attr.attribute2 & dcam.PROPATTRIBUTE2.ATTR2_ARRAYBASE:
                _logger.info(
                    "ignoring ARRAY type property named '%s' (id %d)",
                    name,
                    prop_id.value,
                )
                continue

            prop_type = prop_attr.attribute & dcam.PROPATTRIBUTE.TYPE_MASK
            if prop_type == dcam.PROPATTRIBUTE.TYPE_MODE:
                dtype = "enum"
            elif prop_type == dcam.PROPATTRIBUTE.TYPE_LONG:
                dtype = "int"
            elif prop_type == dcam.PROPATTRIBUTE.TYPE_REAL:
                dtype = "float"
            else:
                raise microscope.MicroscopeError(
                    "property x id is of unknown type '%d'" % prop_type
                )

            get_func = None
            if prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_READABLE:
                pid = prop_id.value
                if dtype == "float":
                    get_func = lambda pid=pid: self._get_real_property(pid)
                elif dtype == "int":
                    get_func = lambda pid=pid: self._get_long_property(pid)
                elif dtype == "enum":
                    get_func = lambda pid=pid: self._get_mode_property(pid)
                else:
                    raise RuntimeError("reached imposible state")

            set_func = None
            if prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_WRITABLE:
                pid = prop_id.value
                if dtype == "float":
                    set_func = lambda v, pid=pid: self._set_real_property(
                        pid, v
                    )
                elif dtype == "int":
                    set_func = lambda v, pid=pid: self._set_long_property(
                        pid, v
                    )
                elif dtype == "enum":
                    set_func = lambda v, pid=pid: self._set_long_property(
                        pid, v
                    )
                else:
                    raise RuntimeError("reached imposible state")

            if get_func is None and set_func is None:
                raise microscope.MicroscopeError(
                    "property '%s' (id %d) is neither readable nor writable"
                    % (name, prop_id.value)
                )

            values = tuple()
            if dtype == "float":
                values = (prop_attr.valuemin, prop_attr.valuemax)
            elif dtype == "int":
                values = (int(prop_attr.valuemin), int(prop_attr.valuemax))
            elif dtype == "enum":
                values = self._init_method_get_prop_values(prop_attr)
            else:
                raise RuntimeError("reached imposible state")

            # Cameras can be in BUSY, READY, STABLE, or UNSTABLE
            # state.  All writable properties are writable during
            # STABLE and UNSTABLE.  Some are also writable during
            # READY or BUSY state.
            readonly = None
            if set_func is not None:
                if (
                    prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_ACCESSREADY
                    and prop_attr.attribute
                    & dcam.PROPATTRIBUTE.ATTR_ACCESSBUSY
                ):
                    readonly = None
                elif prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_ACCESSBUSY:
                    readonly = lambda: self._is_capturing_status_ready()
                elif prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_ACCESSREADY:
                    readonly = lambda: self._is_capturing_status_busy()
                else:
                    readonly = (
                        lambda: self._is_capturing_status_busy_or_ready()
                    )

            self.add_setting(
                name,
                dtype,
                get_func,
                set_func,
                values,
                readonly,
            )

    def _init_method_get_prop_values(
        self, prop_attr: dcam.PROP_ATTR
    ) -> typing.Dict[int, str]:
        strbuf = ctypes.create_string_buffer(64)
        vtxt = _create_struct_with_cbSize(dcam.PROP_VALUETEXT)
        vtxt.iProp = prop_attr.iProp
        vtxt.text = ctypes.cast(ctypes.pointer(strbuf), ctypes.c_char_p)
        vtxt.textbytes = ctypes.sizeof(strbuf)

        val2txt: typing.Dict[int, str] = {}
        next_value = ctypes.c_double(prop_attr.valuemin)
        while next_value.value <= prop_attr.valuemax:
            vtxt.value = next_value.value
            _call(dcam.prop_getvaluetext, self._hdcam, ctypes.byref(vtxt))
            val2txt[int(vtxt.value)] = strbuf.value.decode()
            status = dcam.prop_queryvalue(
                self._hdcam,
                vtxt.iProp,
                ctypes.byref(next_value),
                dcam.PROP_OPTION.NEXT,
            )
            if status == dcam.ERR.OUTOFRANGE.value:
                break  # this was the last valid property value
            elif dcam.failed(status):
                raise microscope.DeviceError(
                    "dcamprop_queryvalue failed: %s" % _status_to_error(status)
                )
        return val2txt

    def _do_shutdown(self) -> None:
        if self._hdcam:
            _logger.debug("Closing device")
            status = dcam.dev_close(self._hdcam)
            if dcam.failed(status):
                _logger.warning("Failed to close device during shutdown")
            self._hdcam = dcam.HDCAM()  # NULL pointer
        else:
            _logger.warning(
                "Not closing device (again?) because HDCAM is NULL pointer"
            )

    def _get_real_property(self, pid: int) -> float:
        val = ctypes.c_double()
        _call(dcam.prop_getvalue, self._hdcam, pid, ctypes.byref(val))
        return val.value

    def _get_long_property(self, pid: int) -> int:
        return int(self._get_real_property(pid))

    def _get_mode_property(self, pid: int) -> str:
        pvalue = self._get_real_property(pid)
        return _get_mode_prop_text(self._hdcam, pid, pvalue)

    def _set_real_property(self, pid: int, value: float) -> None:
        _call(dcam.prop_setvalue, self._hdcam, pid, value)

    def _set_long_property(self, pid: int, value: int) -> None:
        self._set_real_property(pid, float(value))

    def _is_doing_independent_binning(self) -> bool:
        if not self._supports_independent_binning:
            return False

        mode = self._get_long_property(dcam.IDPROP.BINNING_INDEPENDENT)
        if mode == dcam.PROPMODEVALUE.MODE__ON:
            return True
        elif mode == dcam.PROPMODEVALUE.MODE__OFF:
            return False
        else:
            raise microscope.DeviceError(
                "Unable to find if doing independent axis binning."
                "  It is set to %d which is neither ON (%d) nor OFF (%d)"
                % (
                    mode,
                    dcam.PROPMODEVALUE.MODE__ON,
                    dcam.PROPMODEVALUE.MODE__OFF,
                )
            )

    def initialize(self) -> None:
        pass

    def _get_capturing_status(self) -> dcam.CAP_STATUS:
        cap_status = dcam.int32()
        _call(dcam.cap_status, self._hdcam, ctypes.byref(cap_status))
        return dcam.CAP_STATUS(cap_status.value)

    def _is_capturing_status_busy(self) -> bool:
        return self._get_capturing_status() == dcam.CAP_STATUS.BUSY

    def _is_capturing_status_ready(self) -> bool:
        return self._get_capturing_status() == dcam.CAP_STATUS.READY

    def _is_capturing_status_busy_or_ready(self) -> bool:
        status = self._get_capturing_status()
        return (
            status == dcam.CAP_STATUS.BUSY or status == dcam.CAP_STATUS.READY
        )

    def _do_enable(self) -> None:
        if self._is_capturing_status_busy():
            _logger.warning(
                "ignoring call to enable() because camera is already"
                " capturing (CAP_STATUS is BUSY)"
            )
            return True

        # We create the buffer during enable (it will only be used in
        # fetch_data) with the sizes and pixeltype of this moment.
        # This is OK, because we can't change binning, subarray, and
        # data type while enabled anyway.  Changing those will disable
        # and re-enable at which point we will create a new adjusted
        # buffer.
        self._do_enable_method_setup_image_buffer()

        # DCAMWAIT_OPEN and its HDCAMWAIT are invalid after being
        # used/closed, we need to create a new one.  If we don't,
        # wait_open will succeed but wait_start will fail later.
        self._wait_open = _create_struct_with_size(dcam.WAIT_OPEN)
        self._wait_open.hdcam = self._hdcam

        _logger.debug("Acquiring wait handle")
        _call(dcam.wait_open, ctypes.byref(self._wait_open))

        nframes = 10  # FIXME: no hardcoded 10
        _logger.debug("Allocating buffer for %d frames", nframes)
        _call(dcam.buf_alloc, self._hdcam, nframes)

        _logger.debug("Starting capture of images")
        _call(dcam.cap_start, self._hdcam, dcam.CAP_START.SEQUENCE)

        # FIXME: needed to make enable continue but we shouldn't need
        # to return anything and enable() should rely on exceptions to
        # signal things failed.
        return True

    def _do_enable_method_setup_image_buffer(self) -> None:
        pixeltype = self._get_long_property(dcam.IDPROP.IMAGE_PIXELTYPE)
        if pixeltype == dcam.PIXELTYPE.MONO8:
            dtype = np.uint8
        elif pixeltype == dcam.PIXELTYPE.MONO16:
            dtype = np.uint16
        else:
            raise microscope.UnsupportedFeature()

        width = self._get_long_property(dcam.IDPROP.IMAGE_WIDTH)
        height = self._get_long_property(dcam.IDPROP.IMAGE_HEIGHT)
        _logger.debug(
            "Creating image buffer: %d x %d (%s)", height, width, dtype
        )
        self._buffer = np.empty((height, width), dtype=dtype)
        self._frame.iFrame = -1
        self._frame.buf = self._buffer.ctypes.data_as(ctypes.c_void_p)
        self._frame.rowbytes = width * self._buffer.itemsize
        self._frame.width = width
        self._frame.height = height

    def _do_disable(self) -> None:
        if not self._is_capturing_status_busy():
            _logger.warning(
                "ignoring call to disable() because camera is already"
                " not capturing (CAP_STATUS is not BUSY)"
            )
            return

        _logger.debug("Stopping capture of images")
        _call(dcam.cap_stop, self._hdcam)
        _logger.debug("Aborting the wait for an event")
        _call(dcam.wait_abort, self._wait_open.hwait)
        _call(dcam.wait_close, self._wait_open.hwait)
        _logger.debug("Releasing capturing buffer")
        _call(dcam.buf_release, self._hdcam, dcam.BUF_ATTACHKIND.FRAME)

    def abort(self) -> None:
        self.disable()

    def get_exposure_time(self) -> float:
        return self._get_real_property(dcam.IDPROP.EXPOSURETIME)

    def set_exposure_time(self, seconds: float) -> None:
        self._set_real_property(dcam.IDPROP.EXPOSURETIME, seconds)

    def get_cycle_time(self) -> float:
        return self._get_real_property(dcam.IDPROP.TIMING_MINTRIGGERINTERVAL)

    def _get_sensor_shape(self) -> typing.Tuple[int, int]:
        return self._sensor_shape

    def _get_binning(self) -> microscope.Binning:
        if self._is_doing_independent_binning():
            h = self._get_long_property(dcam.IDPROP.BINNING_HORZ)
            v = self._get_long_property(dcam.IDPROP.BINNING_VERT)
            return microscope.Binning(h, v)
        else:
            mode = self._get_long_property(dcam.IDPROP.BINNING)
            return _DCAM_BINNING_TO_MICROSCOPE[mode]

    def _set_binning(self, binning: microscope.Binning) -> None:
        # Changing the binning settings may change the exposure time,
        # so save it and revert it later.
        original_exposure_time = self.get_exposure_time()
        success = False
        do_reset_exposure_time = True
        if self._is_doing_independent_binning():
            # We may be able to set it on one axis and then fail to
            # set on the other (maybe it's not supported).  So save
            # the original binning setting and revert it if it fails.
            original_binning = self._get_binning()
            try:
                self._set_long_property(dcam.IDPROP.BINNING_HORZ)
                self._set_long_property(dcam.IDPROP.BINNING_VERT)
            except microscope.DeviceError:
                self._set_binning(original_binning)
            else:
                success = True
        elif binning in _MICROSCOPE_BINNING_TO_DCAM:
            mode = _MICROSCOPE_BINNING_TO_DCAM[binning]
            try:
                self._set_long_property(dcam.IDPROP.BINNING, mode)
            except microscope.DeviceError:
                pass
            else:
                success = True
        else:
            # Binning combination not supported.
            do_reset_exposure_time = False

        if do_reset_exposure_time:
            self.set_exposure_time(original_exposure_time)
        return success

    def _get_roi(self) -> microscope.ROI:
        pass

    def _set_roi(self, roi: microscope.ROI) -> None:
        pass

    def _fetch_data(self) -> typing.Optional[np.ndarray]:
        _logger.debug("Start waiting for FRAMEREADY")
        status = dcam.wait_start(
            self._wait_open.hwait, ctypes.byref(self._wait_start)
        )
        if status == dcam.ERR.TIMEOUT.value:
            _logger.debug("Timeout waiting for FRAMEREADY")
            return None
        elif dcam.failed(status):
            _logger.warning(
                "dcamwait_start failed: %d", _status_to_error(status)
            )
            return None

        # We don't bother checking for what event happened because we
        # are only waiting for FRAMEREADY anyway.
        _logger.debug(
            "Copying frame %d (w=%d,h=%d,type=%d) from capturing buffer.",
            self._frame.iFrame,
            self._frame.width,
            self._frame.height,
            self._frame.type,
        )
        status = dcam.buf_copyframe(self._hdcam, ctypes.byref(self._frame))
        if dcam.failed(status):
            raise microscope.DeviceError(status)
        return self._buffer.copy()

    def _do_trigger(self) -> None:
        _call(dcam.cap_firetrigger, self._hdcam, 0)

    def _get_trigger_combo(
        self,
    ) -> typing.Tuple[microscope.TriggerType, microscope.TriggerMode]:
        source = self._get_long_property(dcam.IDPROP.TRIGGERSOURCE)
        if source == dcam.PROPMODEVALUE.TRIGGERSOURCE__SOFTWARE:
            return (
                microscope.TriggerType.SOFTWARE,
                microscope.TriggerMode.ONCE,
            )
        elif source == dcam.PROPMODEVALUE.TRIGGERSOURCE__INTERNAL:
            return (
                microscope.TriggerType.SOFTWARE,
                microscope.TriggerMode.STROBE,
            )
        elif source == dcam.PROPMODEVALUE.TRIGGERSOURCE__EXTERNAL:
            active = self._get_long_property(dcam.IDPROP.TRIGGERACTIVE)
            polarity = self._get_long_property(dcam.IDPROP.TRIGGERPOLARITY)
            return _DCAM_EXTERNAL_TRIGGER_TO_MICROSCOPE[(active, polarity)]
        else:
            raise microscope.DeviceError(
                "DCAM_IDPROP_TRIGGERSOURCE is set to '%d' which is"
                " not handled in Python-Microscope (maybe it was set"
                " manually via the settings dict?)" % (source)
            )

    @property
    def trigger_type(self) -> microscope.TriggerType:
        return self._get_trigger_combo()[0]

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        return self._get_trigger_combo()[1]

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if ttype == microscope.TriggerType.SOFTWARE:
            if tmode == microscope.TriggerMode.ONCE:
                self._set_long_property(
                    dcam.IDPROP.TRIGGERSOURCE,
                    dcam.PROPMODEVALUE.TRIGGERSOURCE__SOFTWARE,
                )
            elif tmode == microscope.TriggerMode.STROBE:
                self._set_long_property(
                    dcam.IDPROP.TRIGGERSOURCE,
                    dcam.PROPMODEVALUE.TRIGGERSOURCE__INTERNAL,
                )
            else:
                raise microscope.UnsupportedFeatureError(
                    "%s with %s is not supported" % (ttype, tmode)
                )

        elif (ttype, tmode) in _MICROSCOPE_TRIGGER_TO_DCAM_EXTERNAL:
            active, polarity = _MICROSCOPE_TRIGGER_TO_DCAM_EXTERNAL[
                (ttype, tmode)
            ]

            # Save the previous values in case we need to revert them
            prev_source = self._get_long_property(dcam.IDPROP.TRIGGERSOURCE)
            prev_active = self._get_long_property(dcam.IDPROP.TRIGGERACTIVE)
            prev_polarity = self._get_long_property(
                dcam.IDPROP.TRIGGERPOLARITY
            )
            try:
                self._set_long_property(
                    dcam.IDPROP.TRIGGERSOURCE,
                    dcam.PROPMODEVALUE.TRIGGERSOURCE__EXTERNAL,
                )
                self._set_long_property(dcam.IDPROP.TRIGGERACTIVE, active)
                self._set_long_property(dcam.IDPROP.TRIGGERPOLARITY, polarity)
            except microscope.DeviceError as exc:
                self._set_long_property(dcam.IDPROP.TRIGGERSOURCE, prev_source)
                self._set_long_property(dcam.IDPROP.TRIGGERACTIVE, prev_active)
                self._set_long_property(
                    dcam.IDPROP.TRIGGERPOLARITY, prev_polarity
                )
                raise microscope.UnsupportedFeatureError(
                    "%s with %s is not supported" % (ttype, tmode)
                ) from exc

        else:
            raise microscope.UnsupportedFeatureError(
                "%s with %s is not supported" % (ttype, tmode)
            )

    # This method is deprecated but Cockpit still uses it.
    def soft_trigger(self):
        return self.trigger()


def _list_devices() -> None:
    """Print all available Hamamatsu devices and some of their info."""
    api = _DCAM_API()

    models: typing.List[str] = []
    cids: typing.List[str] = []

    devstr, devstrbuf = _create_devstring_with_length(64)
    for i in range(api.n_devices):
        # First arg to dcamdev_getstring is a HDCAM (a pointer) but
        # that would require first dcamdev_open().  So the function
        # accepts the camera index (an int) which in C would be cast
        # like so:
        #
        #     (HDCAM)(intptr_t)device_idx
        hdcam = ctypes.cast(ctypes.cast(i, ctypes.c_void_p), dcam.HDCAM)

        models.append(_get_device_string(hdcam, devstr, dcam.IDSTR.MODEL))
        cids.append(_get_device_string(hdcam, devstr, dcam.IDSTR.CAMERAID))

    idx_width = max(len("INDEX"), len(str(api.n_devices - 1))) + 2
    model_width = max(len("MODEL"), max([len(s) for s in models])) + 2
    cid_width = max(len("CAMERA ID"), max([len(s) for s in cids])) + 2
    fmt = "%s  %s  %s"
    print(
        fmt
        % (
            "INDEX".center(idx_width),
            "MODEL".center(model_width),
            "CAMERA ID".center(cid_width),
        )
    )
    print(fmt % ("-" * idx_width, "-" * model_width, "-" * cid_width))
    for i, model, cid in zip(range(api.n_devices), models, cids):
        print(
            fmt
            % (
                str(i).rjust(idx_width),
                model.rjust(model_width),
                cid.rjust(cid_width),
            )
        )


def _list_properties(index: int) -> None:
    api = _DCAM_API()
    sopen = _create_struct_with_size(dcam.DEV_OPEN)
    sopen.index = index
    _call(dcam.dev_open, ctypes.byref(sopen))
    hdcam = sopen.hdcam

    # Collect all the strings to pretty print later.
    ids: typing.List[str] = []
    names: typing.List[str] = []
    rws: typing.List[str] = []
    values: typing.List[str] = []

    # There is no property with ID zero, it is reserved, so we start
    # at ID zero and loop to the next until there is no next property.
    prop_id = dcam.int32(0)
    prop_name = ctypes.create_string_buffer(64)
    prop_attr = _create_struct_with_cbSize(dcam.PROP_ATTR)
    prop_value = ctypes.c_double(0.0)
    while True:
        status = dcam.prop_getnextid(
            hdcam,
            ctypes.byref(prop_id),
            dcam.PROP_OPTION.SUPPORT,
        )
        if dcam.ERR(status) == dcam.ERR.NOPROPERTY:
            break
        elif dcam.failed(status):
            raise RuntimeError("getnextid failed: %s")

        _call(
            dcam.prop_getname,
            hdcam,
            prop_id,
            prop_name,
            ctypes.sizeof(prop_name),
        )

        prop_attr.iProp = prop_id
        _call(dcam.prop_getattr, hdcam, ctypes.byref(prop_attr))
        is_readable = prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_READABLE
        is_writable = prop_attr.attribute & dcam.PROPATTRIBUTE.ATTR_WRITABLE
        if is_readable and is_writable:
            rw = "R/W"
        elif is_readable:
            rw = "R/O"
        elif is_writable:
            rw = "W/O"
        else:
            # Not readable and not writable? We've fucked up.
            raise RuntimeError("failed")

        if not is_readable:
            value = ""
        else:
            # The value is always a double but dependending on the
            # type (mode, long, or real) we can convert to something
            # more sensible (text, int, or double).
            _call(dcam.prop_getvalue, hdcam, prop_id, ctypes.byref(prop_value))

            attr_type = prop_attr.attribute & dcam.PROPATTRIBUTE.TYPE_MASK
            if attr_type == dcam.PROPATTRIBUTE.TYPE_MODE:
                value = _get_mode_prop_text(hdcam, prop_id, prop_value)
            elif attr_type == dcam.PROPATTRIBUTE.TYPE_LONG:
                value = str(int(prop_value.value))
            elif attr_type == dcam.PROPATTRIBUTE.TYPE_REAL:
                value = str(prop_value.value)
            else:
                raise RuntimeError("unknown attribute type '%d'" % attr_type)

        ids.append(_status_to_error(prop_id.value))
        names.append(prop_name.value.decode())
        rws.append(rw)
        values.append(value)

    id_width = max(len("ID"), max([len(s) for s in ids])) + 2
    name_width = max(len("NAME"), max([len(s) for s in names])) + 2
    rw_width = max(len("R/W"), max([len(s) for s in rws])) + 2
    value_width = max(len("VALUE"), max([len(s) for s in values])) + 2
    fmt = "%s  %s  %s  %s"
    print(
        fmt
        % (
            "ID".center(id_width),
            "NAME".center(name_width),
            "R/W".center(rw_width),
            "VALUE".center(value_width),
        )
    )
    print(
        fmt
        % ("-" * id_width, "-" * name_width, "-" * rw_width, "-" * value_width)
    )
    for pid, name, rw, value in zip(ids, names, rws, values):
        print(
            fmt
            % (
                pid.rjust(id_width),
                name.ljust(name_width),
                rw.rjust(rw_width),
                value.rjust(value_width),
            )
        )

    status = dcam.dev_close(hdcam)
    if dcam.failed(status):
        _logger.warning("failed to close device during shutdown")


def _main(argv: typing.List[str]) -> int:
    prog_name = "microscope.cameras.hamamatsu"
    parser = argparse.ArgumentParser(prog=prog_name)
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    ls_devices_parser = subparsers.add_parser(
        "list-devices",
        help="List available Hamamatsu devices.",
    )

    ls_prop_parser = subparsers.add_parser(
        "list-properties",
        help="List all properties for a Hamamatsu device.",
    )
    ls_prop_parser.add_argument(
        "index",
        type=int,
        help="Camera index to have properties listed.",
    )

    args = parser.parse_args(argv[1:])
    if args.command == "list-devices":
        _list_devices()
    elif args.command == "list-properties":
        _list_properties(args.index)
    else:
        # We shouldn't have got here because argparse should have
        # caught it... unless we forget to handle the command.
        print(
            "%s: unhandled command '%'" % (prog_name, args.command),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
