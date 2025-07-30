#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
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

"""Ximea cameras.

Changing settings flushes the buffer
------------------------------------

It is not possible to set some parameters during image acquisition.
In such cases, acquisition is stopped (camera is disabled) and the
restarted (camera is enabled).  However, stopping acquisition discards
any image in the camera memory that have not yet been read.

Modifying the following settings require acquisition to be stopped:

- ROIs
- binning
- trigger type (trigger source)

For more details, see the [XiAPI manual](https://www.ximea.com/support/wiki/apis/XiAPI_Manual#Flushing-the-queue).

Hardware trigger
----------------

Ximea cameras in the MQ family accept software triggers even if set
for hardware triggers (see `vendor issues
#3`<https://github.com/python-microscope/vendor-issues/issues/3>).
However, `XimeaCamera.trigger()` checks the trigger type and will
raise an exception unless the camera is set for software triggers.

Requirements
------------

Support for Ximea cameras requires Ximea's API Python (xiApiPython).
This is only available via Ximea's website and is not available on
PyPI.  See Ximea's website for `install instructions
<https://www.ximea.com/support/wiki/apis/Python>`__.

If installing under Linux be sure to follow the Linux installation tutorial
<https://www.ximea.com/support/wiki/apis/XIMEA_Linux_Software_Package>__.
"""

import contextlib
import enum
import logging
from typing import Optional, Union, Tuple

import numpy as np
from ximea import xiapi, xidefs

import microscope
import microscope.abc

_logger = logging.getLogger(__name__)


# The ximea package does not provide an enum for the error codes.
# There is ximea.xidefs.ERROR_CODES which maps the error code to an
# error message but what we need is a symbol that maps to the error
# code so we can use while handling exceptions.
_XI_TIMEOUT = 10
_XI_NOT_SUPPORTED = 12
_XI_NOT_IMPLEMENTED = 26
_XI_ACQUISITION_STOPPED = 45
_XI_UNKNOWN_PARAM = 100
_XI_UNSUPPORTED_PARAM = 106
_XI_UNSUPPORTED_INFO_PARAM = 107
_XI_READ_ONLY_PARAM = 109

# Some more "advanced" features of the Ximea cameras are not supported,
# at least for the moment. These features are implemented as settings that
# we have to "blacklist" to avoid their loading.
_UNSUPPORTED_SETTINGS = [
    # The device manifest provides XML data of the features supported by the camera
    "device_manifest",
    # Settings related to the FFS. Some ximea camera models provide access
    # to the Flash memory as a file system.
    "read_file_ffs",
    "write_file_ffs",
    "ffs_file_name",
    "ffs_file_id",
    "ffs_file_offset",
    "ffs_file_size",
    "free_ffs_size",
    "used_ffs_size",
    "ffs_access_key",
    # The context list is used to get a list of settings for off-line processing
    "xiapi_context_list",
    # The trigger source setting is not added automatically but rather through a custom function so we skip it
    "trigger_source",
]

# During acquisition, we rely on catching timeout errors which then
# get discarded.  However, with debug level set to warning (XiApi
# default log level), we get XiApi messages on stderr for each timeout
# making logging impossible.  So change this to error.
#
# Debug level is a xiapi global setting but we need a Camera instance.
xiapi.Camera().set_debug_level("XI_DL_ERROR")


@contextlib.contextmanager
def _disabled_camera(camera):
    """Context manager to temporarily disable camera."""
    if camera.enabled:
        try:
            camera.disable()
            yield camera
        finally:
            camera.enable()
    else:
        yield camera


@contextlib.contextmanager
def _enabled_camera(camera):
    """Context manager to temporarily enable camera."""
    if not camera.enabled:
        try:
            camera.enable()
            yield camera
        finally:
            camera.disable()
    else:
        yield camera


@enum.unique
class TrgSourceMap(enum.Enum):
    # The complete list is the XI_TRG_SOURCE enum (C code) or in the
    # xidefs module (Python code).

    XI_TRG_SOFTWARE = microscope.TriggerType.SOFTWARE
    XI_TRG_EDGE_RISING = microscope.TriggerType.RISING_EDGE
    XI_TRG_EDGE_FALLING = microscope.TriggerType.FALLING_EDGE

    # Not all XI_TRG_SOURCE values are defined:
    #
    # XI_TRG_OFF: Capture of next image is automatically started after
    #   previous.
    #
    # XI_TRG_LEVEL_HIGH: Specifies that the trigger is considered
    #   valid as long as the level of the source signal is high.
    #
    # XI_TRG_LEVEL_LOW: Specifies that the trigger is considered valid
    #   as long as the level of the source signal is low.


@enum.unique
class TrgSelectorMap(enum.Enum):
    # The complete list is the XI_TRG_SELECTOR enum (C code) or in the
    # xidefs module (Python code).

    # Trigger starts the capture of one frame.
    XI_TRG_SEL_FRAME_START = microscope.TriggerMode.ONCE

    # There are other modes/selector which look like they have matches
    # on TriggerMode but we never got to test them:
    #
    # XI_TRG_SEL_EXPOSURE_ACTIVE: Trigger controls the start and
    #   length of the exposure.
    #
    # XI_TRG_SEL_FRAME_BURST_START: Trigger starts the capture of the
    #   bursts of frames in an acquisition.
    #
    # XI_TRG_SEL_FRAME_BURST_ACTIVE: Trigger controls the duration of
    #   the capture of the bursts of frames in an acquisition.
    #
    # XI_TRG_SEL_MULTIPLE_EXPOSURES: Trigger which when first trigger
    #   starts exposure and consequent pulses are gating
    #   exposure(active HI)
    #
    # XI_TRG_SEL_EXPOSURE_START: Trigger controls the start of the
    #   exposure of one Frame.
    #
    # XI_TRG_SEL_MULTI_SLOPE_PHASE_CHANGE: Trigger controls the multi
    #   slope phase in one Frame (phase0 -> phase1) or (phase1 ->
    #   phase2).
    #
    # XI_TRG_SEL_ACQUISITION_START: Trigger starts acquisition of
    #   first frame.


class XimeaCamera(microscope.abc.Camera):
    """Ximea cameras

    Args:
        serial_number: the serial number of the camera to connect to.
            It can be set to `None` if there is only camera on the
            system.

    """

    def __init__(self, serial_number: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._acquiring = False
        self._handle = xiapi.Camera()
        self._img = xiapi.Image()
        self._serial_number = serial_number
        self._sensor_shape = (0, 0)
        self._roi = microscope.ROI(None, None, None, None)
        self._binning = microscope.Binning(1, 1)

        # When using the Settings system, enums are not really enums
        # and even when using lists we get indices sent back and forth
        # (works fine only when using EnumInt.  The gymnastic here
        # makes it work with the rest of enums which are there to make
        # it work with TriggerTargetMixin.
        trg_source_names = [x.name for x in TrgSourceMap]

        def _trigger_source_setter(index: int) -> None:
            trigger_mode = TrgSourceMap[trg_source_names[index]].value
            self.set_trigger(trigger_mode, self.trigger_mode)

        self.add_setting(
            "trigger source",
            "enum",
            lambda: TrgSourceMap(self.trigger_type).name,
            _trigger_source_setter,
            trg_source_names,
        )

        self.initialize()

    def _fetch_data(self) -> Optional[np.ndarray]:
        if not self._acquiring:
            return None

        try:
            self._handle.get_image(self._img, timeout=1)
        except xiapi.Xi_error as err:
            # err.status may not exist so use getattr (see
            # https://github.com/python-microscope/vendor-issues/issues/2)
            if getattr(err, "status", None) == _XI_TIMEOUT:
                return None
            elif (
                getattr(err, "status", None) == _XI_ACQUISITION_STOPPED
                and not self._acquiring
            ):
                # We can end up here during disable if self._acquiring
                # was True but is now False.
                return None
            else:
                raise

        data: np.ndarray = self._img.get_image_data_numpy()
        _logger.info(
            "Fetched imaged with dims %s and size %s.", data.shape, data.size
        )
        return data

    def abort(self):
        _logger.info("Disabling acquisition.")
        if self._acquiring:
            # We set acquiring before calling stop_acquisition because
            # the fetch loop is still running and will raise errors 45
            # otherwise.
            self._acquiring = False
            try:
                self._handle.stop_acquisition()
            except Exception:
                self._acquiring = True
                raise

    def _is_setting_readonly(self, name):
        # As far as I see, there is no other way to see if a setting is readonly apart from trying to change it
        # if a setter function is not implemented I assume it is a permanent readonly setting
        # Some cameras implement the "device_manifest" setting that returns a full description of the settings as a
        # XML file. As this is not a standard feature I prefer to stick with this "less proper" way of defining this
        if hasattr(self._handle, f"set_{name}"):
            return False
        else:
            return True

    def _get_setting_values(self, setting_name: str) -> \
            Optional[Tuple[Union[int, float, None], Union[int, float, None]]]:
        if self._is_setting_readonly(setting_name):
            return None, None
        else:
            try:
                min_val = self._handle.get_param(f"{setting_name}:min")
            except xiapi.Xi_error as err:
                if err.status == _XI_UNKNOWN_PARAM:
                    min_val = None
                else:
                    raise err
            try:
                max_val = self._handle.get_param(f"{setting_name}:max")
            except xiapi.Xi_error as err:
                if err.status == _XI_UNKNOWN_PARAM:
                    max_val = None
                else:
                    raise err

            return min_val, max_val

    def _get_int_setting(self, setting_name: str) -> int:
        return self._handle.get_param(setting_name)

    def _set_int_setting(self, setting_name: str, value: int) -> None:
        try:
            self._handle.set_param(setting_name, value)
        except xiapi.Xi_error as err:
            if err.status in [_XI_UNKNOWN_PARAM, _XI_READ_ONLY_PARAM]:
                _logger.debug(f"Failed setting {setting_name} Error {err.status}")

    def _get_float_setting(self, setting_name: str) -> float:
        return self._handle.get_param(setting_name)

    def _set_float_setting(self, setting_name: str, value: float) -> None:
        try:
            self._handle.set_param(setting_name, value)
        except xiapi.Xi_error as err:
            if err.status in [_XI_UNKNOWN_PARAM, _XI_READ_ONLY_PARAM]:
                _logger.debug(f"Failed setting {setting_name} Error {err.status}")

    def _get_str_setting(self, setting_name: str) -> str:
        return self._handle.get_param(setting_name)

    def _set_str_setting(self, setting_name: str, value: str) -> None:
        # Updating initializing all the settings sometimes tries to set a setting using an empty string.
        if len(value) == 0:
            return
        try:
            self._handle.set_param(setting_name, value)
        except xiapi.Xi_error as err:
            if err.status in [_XI_UNKNOWN_PARAM, _XI_READ_ONLY_PARAM]:
                _logger.debug(f"Failed setting {setting_name} Error {err.status}")

    def _get_enum_setting(self, setting_name: str) -> int:
        try:
            values_to_idx = {val: idx.value for val, idx in xidefs.ASSOC_ENUM[setting_name].items()}
        except KeyError as err:
            _logger.error(f"The Ximea API does not define the enum values for the setting {setting_name}")
            raise err
        return values_to_idx[self._handle.get_param(setting_name)]

    def _get_enum_values(self, setting_name: str) -> dict:
        try:
            values = {i.value: val for val, i in xidefs.ASSOC_ENUM[setting_name].items()}
        except KeyError as err:
            _logger.error(f"Failed getting values for {setting_name}")
            raise err
        return values

    def _set_enum_setting(self, setting_name: str, value: enum) -> None:
        try:
            idx_to_values = {i.value: val for val, i in xidefs.ASSOC_ENUM[setting_name].items()}
            self._handle.set_param(setting_name, idx_to_values[value])
        except KeyError as err:
            _logger.error(f"Failed setting {setting_name}. Error {err.status}")
            raise err

    def _get_bool_setting(self, setting_name: str) -> bool:
        return self._handle.get_param(setting_name)

    def _set_bool_setting(self, setting_name: str, value: bool) -> None:
        self._handle.set_param(setting_name, value)

    def initialize(self) -> None:
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        n_cameras = self._handle.get_number_devices()

        if self._serial_number is None:
            if n_cameras > 1:
                raise TypeError(
                    "more than one Ximea camera found but the"
                    " serial_number argument was not specified"
                )
            _logger.info(
                "serial_number is not specified but there is only one"
                " camera on the system"
            )
            self._handle.open_device()
        else:
            _logger.info(
                "opening camera with serial number '%s'", self._serial_number
            )
            self._handle.open_device_by_SN(self._serial_number)

        self._sensor_shape = (
            self._handle.get_width_maximum()
            + self._handle.get_offsetX_maximum(),
            self._handle.get_height_maximum()
            + self._handle.get_offsetY_maximum(),
        )
        self._roi = microscope.ROI(
            left=0,
            top=0,
            width=self._sensor_shape[0],
            height=self._sensor_shape[1],
        )
        self.set_roi(self._roi)

        self.set_trigger(
            microscope.TriggerType.SOFTWARE, microscope.TriggerMode.ONCE
        )

        # Add settings
        def _add_int_setting(name):
            self.add_setting(
                name=name,
                dtype="int",
                get_func=lambda name=name: self._get_int_setting(name),
                set_func=lambda v, name=name: self._set_int_setting(name, v),
                values=lambda name=name: self._get_setting_values(name),
                readonly=lambda name=name: self._is_setting_readonly(name)
            )

        def _add_float_setting(name):
            self.add_setting(
                name=name,
                dtype="float",
                get_func=lambda name=name: self._get_float_setting(name),
                set_func=lambda v, name=name: self._set_float_setting(name, v),
                values=lambda name=name: self._get_setting_values(name),
                readonly=lambda name=name: self._is_setting_readonly(name)
            )

        def _add_str_setting(name):
            self.add_setting(
                name=name,
                dtype="str",
                get_func=lambda name=name: self._get_str_setting(name),
                set_func=lambda v, name=name: self._set_str_setting(name, v),
                # The value of the string size is extracted from the default buffer size of xiapi.Camera.get_param
                # This is definitely not enough for many settings. The Ximea API fails to provide proper string size
                # and a reference has to be found in the C library.
                values=256,
                readonly=lambda name=name: self._is_setting_readonly(name)
            )

        def _add_enum_setting(name):
            self.add_setting(
                name=name,
                dtype="enum",
                get_func=lambda name=name: self._get_enum_setting(name),
                set_func=lambda v, name=name: self._set_enum_setting(name, v),
                values=lambda name=name: self._get_enum_values(name),
                readonly=lambda name=name: self._is_setting_readonly(name)
            )

        def _add_bool_setting(name):
            self.add_setting(
                name=name,
                dtype="bool",
                get_func=lambda name=name: self._get_bool_setting(name),
                set_func=lambda v, name=name: self._set_bool_setting(name, v),
                values=None,
                readonly=lambda name=name: self._is_setting_readonly(name)
            )

        def _add_cmd_setting(name):
            pass

        prm_type_to_add_method = {
            "xiTypeInteger": _add_int_setting,
            "xiTypeFloat": _add_float_setting,
            "xiTypeString": _add_str_setting,
            "xiTypeEnum": _add_enum_setting,
            "xiTypeBoolean": _add_bool_setting,
            "xiTypeCommand": _add_cmd_setting,
            "xiTypeInteger64": _add_int_setting,
        }

        for setting_name, setting_type in xidefs.VAL_TYPE.items():
            # TODO: Do we have to remove here the settings that are implemented in another way?
            # ROI, exposure,...
            if setting_name in _UNSUPPORTED_SETTINGS:
                continue
            try:
                self._handle.get_param(setting_name)
            except xiapi.Xi_error as err:
                # Depending on XiAPI version, camera model, and
                # selected sensor, we might get any of these errors as
                # meaning that it's not available.  See
                # https://github.com/python-microscope/vendor-issues/issues/6
                if err.status not in [
                    _XI_NOT_SUPPORTED,
                    _XI_NOT_IMPLEMENTED,
                    _XI_UNKNOWN_PARAM,
                    _XI_UNSUPPORTED_PARAM,
                    _XI_UNSUPPORTED_INFO_PARAM
                ]:
                    _logger.debug(f"The setting {setting_name} failed to be added")
                    raise err
                else:
                    continue

            prm_type_to_add_method[setting_type](setting_name)

    def _do_disable(self):
        self.abort()

    def _do_enable(self):
        _logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        # actually start camera
        self._handle.start_acquisition()
        self._acquiring = True
        _logger.info("Acquisition enabled.")
        return True

    def _get_shuttering_mode(self) -> microscope.ElectronicShutteringMode:
        shutter_type = self._handle.get_shutter_type()
        if shutter_type == "XI_SHUTTER_GLOBAL":
            return microscope.ElectronicShutteringMode.GLOBAL
        elif shutter_type == "XI_SHUTTER_ROLLING":
            return microscope.ElectronicShutteringMode.ROLLING
        # This shutter global reset release mode is de facto a rolling shutter where all pixels are activated
        # at the same time. https://www.ximea.com/support/wiki/allprod/Sensor_Shutter_Modes
        elif shutter_type == "XI_SHUTTER_GLOBAL_RESET_RELEASE":
            return microscope.ElectronicShutteringMode.ROLLING
        else:
            raise microscope.UnsupportedFeatureError(f"{shutter_type} shuttering mode is not supported.")

    def set_exposure_time(self, value: float) -> None:
        # exposure times are set in us.
        try:
            self._handle.set_exposure_direct(int(value * 1000000))
        except Exception as err:
            _logger.debug("set_exposure_time exception: %s", err)

    def get_exposure_time(self) -> float:
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        return self._handle.get_exposure() * 1.0e-6

    def get_cycle_time(self):
        return 1.0 / self._handle.get_framerate()

    def _get_sensor_shape(self) -> Tuple[int, int]:
        return self._sensor_shape

    def soft_trigger(self) -> None:
        self.trigger()

    def _do_trigger(self) -> None:
        # Value for set_trigger_software() has no meaning.  See
        # https://github.com/python-microscope/vendor-issues/issues/3
        self._handle.set_trigger_software(1)

    def _get_binning(self) -> microscope.Binning:
        return self._binning

    def _set_binning(self, binning: microscope.Binning) -> bool:
        if binning == self._binning:
            return True
        # We don't have a ximea camera that supports binning so we
        # can't write support for this (a camera without this feature
        # will raise error 100).  When writing this, careful and check
        # what XiAPI does when mixing ROI and binning.
        raise NotImplementedError()

    def _get_roi(self) -> microscope.ROI:
        assert self._roi == microscope.ROI(
            self._handle.get_offsetX(),
            self._handle.get_offsetY(),
            self._handle.get_width(),
            self._handle.get_height(),
        ), "ROI attribute is out of sync with internal camera setting"
        return self._roi

    def _set_roi(self, roi: microscope.ROI) -> bool:
        if (
            roi.width + roi.left > self._sensor_shape[0]
            or roi.height + roi.top > self._sensor_shape[1]
        ):
            raise ValueError(
                "ROI %s does not fit in sensor shape %s"
                % (roi, self._sensor_shape)
            )
        try:
            # These methods will fail if the width/height plus their
            # corresponding offsets are higher than the sensor size.
            # So we start by setting the offset to zero.  Cases to
            # think off: 1) shrinking ROI size, 2) increasing ROI
            # size, 3) resetting ROI and so can't trust self._roi as
            # the current state (see this exception handling).
            with _disabled_camera(self):
                self._handle.set_offsetX(0)
                self._handle.set_offsetY(0)
                self._handle.set_width(roi.width)
                self._handle.set_height(roi.height)
                self._handle.set_offsetX(roi.left)
                self._handle.set_offsetY(roi.top)
        except Exception:
            self._set_roi(self._roi)  # set it back to whatever was before
            raise
        self._roi = roi
        return True

    def _do_shutdown(self) -> None:
        if self._acquiring:
            self._handle.stop_acquisition()
        if self._handle.CAM_OPEN:
            # We check CAM_OPEN instead of try/catch an exception
            # because if the camera failed initialisation, XiApi fails
            # hard with error code -1009 (unknown) since the internal
            # device handler is NULL.
            self._handle.close_device()

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        trg_selector = self._handle.get_trigger_selector()
        try:
            tmode = TrgSelectorMap[trg_selector]
        except KeyError:
            raise Exception(
                "somehow set to unsupported trigger mode %s" % trg_selector
            )
        return tmode.value

    @property
    def trigger_type(self) -> microscope.TriggerType:
        trg_source = self._handle.get_trigger_source()
        try:
            ttype = TrgSourceMap[trg_source]
        except KeyError:
            raise Exception(
                "somehow set to unsupported trigger type %s" % trg_source
            )
        return ttype.value

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        if tmode is not microscope.TriggerMode.ONCE:
            raise microscope.UnsupportedFeatureError(
                "%s not supported (only TriggerMode.ONCE)" % tmode
            )

        try:
            trg_source = TrgSourceMap(ttype)
        except ValueError:
            raise microscope.UnsupportedFeatureError(
                "no support for trigger type %s" % ttype
            )

        if trg_source.name != self._handle.get_trigger_source():
            # Changing trigger source requires stopping acquisition.
            with _disabled_camera(self):
                self._handle.set_trigger_source(trg_source.name)
