#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Mick Phillips (mick.phillips@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""AndorSDK3 camera device.

This class provides a wrapper for PYME's SDK3 interface that allows
a camera and all its settings to be exposed over Pyro.
"""

import logging
import queue
import time

import numpy as np

from microscope import devices
from microscope.devices import keep_acquiring
from microscope.devices import ROI

from .SDK3Cam import *


_logger = logging.getLogger(__name__)


# SDK data pointer type
DPTR_TYPE = SDK3.POINTER(SDK3.AT_U8)

# Trigger mode to type.
TRIGGER_MODES = {
    'internal': None,
    'external': devices.TRIGGER_BEFORE,
    'external start': None,
    'external exposure': devices.TRIGGER_DURATION,
    'software': devices.TRIGGER_SOFT,
}

SDK_NAMES = {
    "_accumulate_count" : "AccumulateCount",
    "_acquisition_start" : "AcquisitionStart",
    "_acquisition_stop" : "AcquisitionStop",
    "_alternating_readout_direction" : "AlternatingReadoutDirection",
    "_aoi_binning" : "AOIBinning",
    "_aoi_height" : "AOIHeight",
    "_aoi_left" : "AOILeft",
    "_aoi_top" : "AOITop",
    "_aoi_width" : "AOIWidth",
    "_aoi_stride" : "AOIStride",
    "_auxiliary_out_source" : "AuxiliaryOutSource",
    "_aux_out_source_two" : "AuxOutSourceTwo",
    "_baseline_level" : "BaselineLevel",
    "_bit_depth" : "BitDepth",
    "_buffer_overflow_event" : "BufferOverflowEvent",
    "_bytes_per_pixel" : "BytesPerPixel",
    "_camera_acquiring" : "CameraAcquiring",
    "_camera_dump" : "CameraDump",
    "_camera_model" : "CameraModel",
    "_camera_name" : "CameraName",
    "_camera_present" : "CameraPresent",
    "_controller_id" : "ControllerId",
    "_frame_count" : "FrameCount",
    "_cycle_mode" : "CycleMode",
    "_electronic_shuttering_mode" : "ElectronicShutteringMode",
    "_event_enable" : "EventEnable",
    "_events_missed_event" : "EventsMissedEvent",
    "_event_selector" : "EventSelector",
    "_exposed_pixel_height" : "ExposedPixelHeight",
    "_exposure_time" : "ExposureTime",
    "_exposure_end_event" : "ExposureEndEvent",
    "_exposure_start_event" : "ExposureStartEvent",
    "_external_trigger_delay" : "ExternalTriggerDelay",
    "_fan_speed" : "FanSpeed",
    "_firmware_version" : "FirmwareVersion",
    "_frame_rate" : "FrameRate",
    "_full_aoi_control" : "FullAOIControl",
    "_image_size_bytes" : "ImageSizeBytes",
    "_interface_type" : "InterfaceType",
    "_io_invert" : "IoInvert",
    "_io_selector" : "IoSelector",
    "_line_scan_speed" : "LineScanSpeed",
    "_lut_index" : "LutIndex",
    "_lut_value" : "LutValue",
    "_max_interface_transfer_rate" : "MaxInterfaceTransferRate",
    "_metadata_enable" : "MetadataEnable",
    "_metadata_timestamp" : "MetadataTimestamp",
    "_metadata_frame" : "MetadataFrame",
    "_overlap" : "Overlap",
    "_pixel_encoding" : "PixelEncoding",
    "_pixel_readout_rate" : "PixelReadoutRate",
    "_pre_amp_gain_control" : "PreAmpGainControl",
    "_readout_time" : "ReadoutTime",
    "_rolling_shutter_global_clear" : "RollingShutterGlobalClear",
    "_row_n_exposure_end_event" : "RowNExposureEndEvent",
    "_row_n_exposure_start_event" : "RowNExposureStartEvent",
    "_row_read_time" : "RowReadTime",
    "_scan_speed_control_enable" : "ScanSpeedControlEnable",
    "_sensor_cooling" : "SensorCooling",
    "_sensor_height" : "SensorHeight",
    "_sensor_readout_mode" : "SensorReadoutMode",
    "_sensor_temperature" : "SensorTemperature",
    "_sensor_width" : "SensorWidth",
    "_serial_number" : "SerialNumber",
    "_simple_pre_amp_gain_control" : "SimplePreAmpGainControl",
    "_software_trigger" : "SoftwareTrigger",
    "_static_blemish_correction" : "StaticBlemishCorrection",
    "_spurious_noise_filter" : "SpuriousNoiseFilter",
    "_target_sensor_temperature" : "TargetSensorTemperature",
    "_temperature_control" : "TemperatureControl",
    "_temperature_status" : "TemperatureStatus",
    "_timestamp_clock" : "TimestampClock",
    "_timestamp_clock_frequency" : "TimestampClockFrequency",
    "_timestamp_clock_reset" : "TimestampClockReset",
    "_trigger_mode" : "TriggerMode",
    "_vertically_centre_aoi" : "VerticallyCentreAOI",
}

# Wrapper to ensure feature is readable.
def readable_wrapper(func):
    def wrapper(self, *args, **kwargs):
        if SDK3.IsReadable(self.handle, self.propertyName):
            return func(self, *args, **kwargs)
        else:
            return None#Warning('%s not currently readable.' % self.propertyName)
    return wrapper

# Wrapper to ensure feature is writable.
def writable_wrapper(func):
    def wrapper(self, *args, **kwargs):
        if SDK3.IsWritable(self.handle, self.propertyName):
            return func(self, *args, **kwargs)
        else:
            return False#Warning('%s not currently writable.' % self.propertyName)
    return wrapper

# Overrides for local style and error handling.
ATInt.get_value = readable_wrapper(ATInt.getValue)
ATInt.set_value = writable_wrapper(ATInt.setValue)
ATInt.min = readable_wrapper(ATInt.min)
ATInt.max = readable_wrapper(ATInt.max)
ATBool.get_value = readable_wrapper(ATBool.getValue)
ATBool.set_value = writable_wrapper(ATBool.setValue)
ATFloat.get_value = readable_wrapper(ATFloat.getValue)
ATFloat.set_value = writable_wrapper(ATFloat.setValue)
ATString.get_value = readable_wrapper(ATString.getValue)
ATString.set_value = writable_wrapper(ATString.setValue)
ATString.max_length = readable_wrapper(ATString.maxLength)
ATEnum.get_index  = readable_wrapper(ATEnum.getIndex)
ATEnum.set_index  = writable_wrapper(ATEnum.setIndex)
ATEnum.get_string = readable_wrapper(ATEnum.getString)
ATEnum.set_string = writable_wrapper(ATEnum.setString)
ATEnum.get_available_values = readable_wrapper(ATEnum.getAvailableValueMap)
ATProperty.is_readonly = lambda self: not SDK3.IsWritable(self.handle, self.propertyName)

# Mapping of AT type to python type.
PROPERTY_TYPES = {
    ATInt: int,
    ATBool: bool,
    ATFloat: float,
    ATString: str,
    ATEnum: 'enum'
}

INVALIDATES_BUFFERS = ['_simple_pre_amp_gain_control', '_pre_amp_gain_control',
                       '_aoi_binning', '_aoi_left', '_aoi_top',
                       '_aoi_width', '_aoi_height', ]


class AndorSDK3(devices.FloatingDeviceMixin,
                devices.CameraDevice):
    SDK_INITIALIZED = False
    def __init__(self, index=0, **kwargs):
        super().__init__(index=index, **kwargs)
        if not AndorSDK3.SDK_INITIALIZED:
            SDK3.InitialiseLibrary()
        self.handle = None
        #self._sdk3cam = SDK3Camera(self._index)
        #SDK3Camera.__init__(self, self._index)
        self.add_setting('use_callback', 'bool',
                         lambda: self._using_callback,
                         self._enable_callback,
                         None)
        # Define features with local style. The SDK treats parameter names
        # without regard to case, so we just need to remove the underscores
        # when connecting properties to SDK calls. We define all possible
        # features here; they will be removed if they are not implemented
        # on the camera.
        self._accumulate_count = ATInt()
        self._acquisition_start = ATCommand()
        self._acquisition_stop = ATCommand()
        self._alternating_readout_direction = ATBool()
        self._aoi_binning = ATEnum()
        self._aoi_height = ATInt()
        self._aoi_left = ATInt()
        self._aoi_top = ATInt()
        self._aoi_width = ATInt()
        self._aoi_stride = ATInt()
        self._auxiliary_out_source = ATEnum()
        self._aux_out_source_two = ATEnum()
        self._baseline_level = ATInt()
        self._bit_depth = ATEnum()
        self._buffer_overflow_event = ATInt()
        self._bytes_per_pixel = ATFloat()
        self._camera_acquiring = ATBool()
        self._camera_dump = ATCommand()
        self._camera_model = ATString()
        self._camera_name = ATString()
        self._camera_present = ATBool()
        self._controller_id = ATString()
        self._frame_count = ATInt()
        self._cycle_mode = ATEnum()
        self._electronic_shuttering_mode = ATEnum()
        self._event_enable = ATBool()
        self._events_missed_event = ATInt()
        self._event_selector = ATEnum()
        self._exposed_pixel_height = ATInt()
        self._exposure_time = ATFloat()
        self._exposure_end_event = ATInt()
        self._exposure_start_event = ATInt()
        self._external_trigger_delay = ATFloat()
        self._fan_speed = ATEnum()
        self._firmware_version = ATString()
        self._frame_rate = ATFloat()
        self._full_aoi_control = ATBool()
        self._image_size_bytes = ATInt()
        self._interface_type = ATString()
        self._io_invert = ATBool()
        self._io_selector = ATEnum()
        self._line_scan_speed = ATFloat()
        self._lut_index = ATInt()
        self._lut_value = ATInt()
        self._max_interface_transfer_rate = ATFloat()
        self._metadata_enable = ATBool()
        self._metadata_timestamp = ATBool()
        self._metadata_frame = ATBool()
        self._overlap = ATBool()
        self._pixel_encoding = ATEnum()
        self._pixel_readout_rate = ATEnum()
        self._pre_amp_gain_control = ATEnum()
        self._readout_time = ATFloat()
        self._rolling_shutter_global_clear = ATBool()
        self._row_n_exposure_end_event = ATInt()
        self._row_n_exposure_start_event = ATInt()
        self._row_read_time = ATFloat()
        self._scan_speed_control_enable = ATBool()
        self._sensor_cooling = ATBool()
        self._sensor_height = ATInt()
        self._sensor_readout_mode = ATEnum()
        self._sensor_temperature = ATFloat()
        self._sensor_width = ATInt()
        self._serial_number = ATString()
        self._simple_pre_amp_gain_control = ATEnum()
        self._software_trigger = ATCommand()
        self._static_blemish_correction = ATBool()
        self._spurious_noise_filter = ATBool()
        self._target_sensor_temperature = ATFloat()
        self._temperature_control = ATEnum()
        self._temperature_status = ATEnum()
        self._timestamp_clock = ATInt()
        self._timestamp_clock_frequency = ATInt()
        self._timestamp_clock_reset = ATCommand()
        self._trigger_mode = ATEnum()
        self._vertically_centre_aoi = ATBool()

        # Software buffers and parameters for data conversion.
        self.num_buffers = 32
        self.add_setting('num_buffers', 'int',
                         lambda: self.num_buffers,
                         lambda val: self.set_num_buffers(val),
                         lambda: (1, 100))
        self.buffers = queue.Queue()
        self._buffer_size = None
        self._img_stride = None
        self._img_width = None
        self._img_height = None
        self._img_encoding = None
        self._buffers_valid = False
        self._exposure_callback = None

    @property
    def _acquiring(self):
        return self._camera_acquiring.get_value()

    @keep_acquiring
    def _enable_callback(self, use=False):
        self.disable()
        if use:
            SDK3.RegisterFeatureCallback(self.handle,
                                         "ExposureEndEvent",
                                         self._exposure_callback, None)
            self._event_selector.set_string("ExposureEndEvent")
            self._event_enable.set_value(True)
            self._using_callback = True
        else:
            SDK3.UnregisterFeatureCallback(self.handle,
                                           "ExposureEndEvent",
                                           self._exposure_callback, None)
            self._event_enable.set_value(False)
            self._using_callback = False
        self.enable()

    @_acquiring.setter
    def _acquiring(self, value):
        # Here to prevent an error when super.__init__ intializes
        # self._acquiring. Doesn't do anything, because the DLL keeps
        # track of acquisition state.
        pass

    def set_num_buffers(self, num):
        self.num_buffers = num
        self._buffers_valid = False

    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        _logger.debug("Purging buffers.")
        self._buffers_valid = False
        if self._acquiring:
            raise Exception ('Can not modify buffers while camera acquiring.')
        SDK3.Flush(self.handle)
        while True:
            try:
                self.buffers.get(block=False)
            except queue.Empty:
                break

    def _create_buffers(self, num=None):
        """Create buffers and store values needed to remove padding later."""
        if self._buffers_valid:
            return
        if num is None:
            num = self.num_buffers
        self._purge_buffers()
        _logger.debug("Creating %d buffers.", num)
        self._img_stride = self._aoi_stride.get_value()
        self._img_width = self._aoi_width.get_value()
        self._img_height = self._aoi_height.get_value()
        self._img_encoding = self._pixel_encoding.get_string()
        img_size = self._image_size_bytes.get_value()
        self._buffer_size = img_size
        for i in range(num):
            buf = np.require(np.empty(img_size), dtype='uint8',
                             requirements=['C_CONTIGUOUS',
                                           'ALIGNED',
                                           'OWNDATA'])
            self.buffers.put(buf)
            SDK3.QueueBuffer(self.handle,
                             buf.ctypes.data_as(DPTR_TYPE),
                             img_size)
        self._buffers_valid = True

    def invalidate_buffers(self, func):
        """Wrap functions that invalidate buffers so buffers are recreated."""
        outerself = self
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            outerself._buffers_valid = False
        return wrapper

    def _fetch_data(self, timeout=5, debug=False):
        """Fetch data and recycle buffers."""
        try:
            ptr, length = SDK3.WaitBuffer(self.handle, timeout)
        except SDK3.TimeoutError as e:
            if debug:
                _logger.debug(e)
            return None
        except Exception:
            raise
        raw = self.buffers.get()
        width = self._img_width
        height = self._img_height
        data = raw#.reshape((-1, bytes_per_row))[:, 0:width].copy()
        data = np.empty((width, height), dtype='uint16')
        SDK3.ConvertBuffer(ptr, data.ctypes.data_as(DPTR_TYPE),
                           width, height,
                           self._img_stride, self._img_encoding, 'Mono16')
        # Requeue the buffer if buffer size has not been changed elsewhere.
        if raw.size == self._buffer_size:
            self.buffers.put(raw)
            SDK3.QueueBuffer(self.handle, ptr, length)
        else:
            del raw

        return data

    def abort(self):
        """Abort acquisition."""
        _logger.debug('Disabling acquisition.')
        if self._acquiring:
            self._acquisition_stop()

    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        try:
            self.handle = SDK3.Open(self._index)
        except:
            raise Exception("Problem opening camera.")
        if self.handle == None:
            raise Exception("No camera opened.")
        for name, var in sorted(self.__dict__.items()):
            if isinstance(var, ATProperty):
                sdk_name = SDK_NAMES[name]
                if not SDK3.IsImplemented(self.handle, sdk_name):
                    delattr(self, name)
                    continue
                var.connect(self.handle, sdk_name)

                if type(var) is ATCommand:
                    continue

                is_readonly_func = var.is_readonly
                if type(var) is ATEnum:
                    set_func = var.set_index
                    get_func = var.get_index
                    vals_func = var.get_available_values
                else:
                    set_func = var.set_value
                    get_func = var.get_value
                    if type(var) is ATString:
                        vals_func = var.max_length
                    elif type(var) in (ATFloat, ATInt):
                        vals_func = lambda v=var: (v.min(), v.max())
                    else:
                        vals_func = None

                if name in INVALIDATES_BUFFERS:
                    set_func = self.invalidate_buffers(set_func)

                self.add_setting(name.lstrip('_'), PROPERTY_TYPES[type(var)],
                                 get_func, set_func, vals_func, is_readonly_func)
        # Default setup.
        self.set_cooling(True)
        if not self._camera_model.getValue().startswith('SIMCAM'):
            self._trigger_mode.set_string('Software')
            self._cycle_mode.set_string('Continuous')
        else:
            _logger.warn("No hardware found - using SIMCAM")


        def callback(*args):
            data = self._fetch_data(timeout=500)
            timestamp = time.time()
            if data is not None:
                self._put(data, timestamp)
                return 0
            else:
                return -1

        self._exposure_callback = SDK3.CALLBACKTYPE(callback)

    def set_cooling(self, value):
        try:
            self._sensor_cooling.set_value(value)
        except AttributeError:
            pass
        except Exception:
            raise

    def get_id(self):
        return self._serial_number.get_value()

    def make_safe(self):
        if self._acquiring:
            self.abort()

    def _on_shutdown(self):
        self.set_cooling(False)
        SDK3.Close(self.handle)

    def _on_disable(self):
        self.abort()
        self._buffers_valid = False

    def _on_enable(self):
        _logger.debug("Preparing for acquisition.")
        if self._acquiring:
            self._acquisition_stop()
        self._create_buffers()
        try:
            self._acquisition_start()
        except Exception as e:
            raise Exception(str(e))
        _logger.debug("Acquisition enabled: %s.", self._acquiring)
        return True

    @keep_acquiring
    def set_exposure_time(self, value):
        bounded_value = sorted((self._exposure_time.min(),
                      self._exposure_time.max(),
                      value))[1]
        self._exposure_time.set_value(bounded_value)
        self._frame_rate.set_value(self._frame_rate.max())
        _logger.debug("Set exposure time to %f, resulting framerate %f.",
                      bounded_value, self._frame_rate.get_value())

    def get_exposure_time(self):
        return self._exposure_time.get_value()

    def get_cycle_time(self):
        return 1. / self._frame_rate.get_value()

    def _get_sensor_shape(self):
        return (self._sensor_width.get_value(),
                self._sensor_height.get_value())

    def get_trigger_type(self):
        return TRIGGER_MODES[self._trigger_mode.get_string().lower()]

    def soft_trigger(self):
        return self._software_trigger()

    def _get_binning(self):
        as_text = self._aoi_binning.get_string().split('x')
        return tuple(int(t) for t in as_text)

    @keep_acquiring
    def _set_binning(self, binning):
        modes = self._aoi_binning.get_available_values()
        as_text = '%dx%d' % (binning.h, binning.v)
        if as_text in modes:
            self._aoi_binning.set_string(as_text)
            self._create_buffers()
            return True
        else:
            return False

    def _get_roi(self):
        return ROI(self._aoi_left.get_value(),
                   self._aoi_top.get_value(),
                   self._aoi_width.get_value(),
                   self._aoi_height.get_value())

    @keep_acquiring
    def _set_roi(self, roi):
        current = self.get_roi()
        if self._acquiring:
            self.abort()
        try:
            self._aoi_width.set_value(roi.width)
            self._aoi_height.set_value(roi.height)
            self._aoi_left.set_value(roi.left)
            self._aoi_top.set_value(roi.top)
        except:
            self._aoi_width.set_value(current.width)
            self._aoi_height.set_value(current.height)
            self._aoi_left.set_value(current.left)
            self._aoi_top.set_value(current.top)
            return False
        return True

    def get_gain(self):
        if hasattr(self, '_preampgain'):
            return self._preampgain.get_value()
        else:
            return None
