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

Limitations:
The Zyla can not read out the full chip in 16-bit mode.
"""
import abc
import camera
import ctypes
import devicebase
import numpy as np
import Queue
import threading
from PYME.Acquire.Hardware.AndorNeo.SDK3Cam import *

# Number of buffers to allocate.
NUM_BUFFERS = 50

# SDK data pointer type
DPTR_TYPE = SDK3.POINTER(SDK3.AT_U8)

# Trigger mode to type.
TRIGGER_MODES = {
    'internal': None,
    'external': camera.TRIGGER_BEFORE,
    'external start': None,
    'external exposure': camera.TRIGGER_DURATION,
    'software': camera.TRIGGER_SOFT,
}


# Wrapper to preserve acquiring state.
def keep_aquiring(func):
    def wrapper(self, *args, **kwargs):
        if self._camera_acquiring.get_value():
            self.abort()
            result = func(self, *args, **kwargs)
            self.start_acquisition()
        else:
            result = func(self, *args, **kwargs)
        return result
    return wrapper


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
ATEnum.get_available_values = readable_wrapper(ATEnum.getAvailableValues)

# Mapping of AT type to python type.
PROPERTY_TYPES = {
    ATInt: int,
    ATBool: bool,
    ATFloat: float,
    ATString: str,
    ATEnum: 'enum'
}


class AndorSDK3(camera.CameraDevice,
                devicebase.FloatingDeviceMixin,
                SDK3Camera):
    SDK_INITIALIZED = False
    def __init__(self, *args, **kwargs):
        super(AndorSDK3, self).__init__(**kwargs)
        if not AndorSDK3.SDK_INITIALIZED:
            SDK3.InitialiseLibrary()
        self._index = kwargs.get('index', 0)
        self.handle = None
        SDK3Camera.__init__(self, self._index)

        # Define features with local style. The SDK treats parameter names
        # without regard to case, so we just need to remove the underscores
        # when connecting properties to SDK calls. We define all possible
        # features here; they will be removed if they are not implemented
        # on the camera.
        self._accumulate_count = ATInt()
        self._acquisition_start = ATCommand()
        self._acquisition_stop = ATCommand()
        self._aoi_binning = ATEnum()
        self._aoi_height = ATInt()
        self._aoi_left = ATInt()
        self._aoi_top = ATInt()
        self._aoi_width = ATInt()
        self._aoi_stride = ATInt()
        self._auxiliary_out_source = ATEnum()
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
        self._exposure_time = ATFloat()
        self._exposure_end_event = ATInt()
        self._exposure_start_event = ATInt()
        self._fan_speed = ATEnum()
        self._firmware_version = ATString()
        self._frame_rate = ATFloat()
        self._full_aoi_control = ATBool()
        self._image_size_bytes = ATInt()
        self._interface_type = ATString()
        self._io_invert = ATBool()
        self._io_selector = ATEnum()
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
        self._sensor_cooling = ATBool()
        self._sensor_height = ATInt()
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
        self.buffers = Queue.Queue()
        self._buffer_size = None
        self._img_stride = None
        self._img_width = None
        self._img_height = None
        self._img_encoding = None


    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        if self._camera_acquiring.get_value():
            raise Exception ('Can not modify buffers while camera acquiring.')
        SDK3.Flush(self.handle)
        while True:
            try:
                self.buffers.get(block=False)
            except Queue.Empty:
                break


    def _create_buffers(self, num=NUM_BUFFERS):
        """Create buffers and store values needed to remove padding later."""
        self._purge_buffers()
        self._img_stride = self._aoi_stride.get_value()
        self._img_width = self._aoi_width.get_value()
        self._img_height = self._aoi_height.get_value()
        self._img_encoding = self._pixel_encoding.get_string()
        img_size = self._image_size_bytes.get_value()
        self._buffer_size = img_size
        for i in xrange(num):
            buf = np.require(np.empty(img_size), dtype='uint8',
                             requirements=['C_CONTIGUOUS',
                                           'ALIGNED',
                                           'OWNDATA'])
            self.buffers.put(buf)
            SDK3.QueueBuffer(self.handle,
                             buf.ctypes.data_as(DPTR_TYPE),
                             img_size)


    def _fetch_data(self, timeout=10, debug=False):
        try:
            ptr, length = SDK3.WaitBuffer(self.handle, timeout)
        except SDK3.TimeoutError as e:
            if debug:
                print e
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
        if self._camera_acquiring.get_value():
            self._acquisition_stop()


    def initialize(self):
        """Initialise the camera.

        Open the connection, connect properties and populate settings dict.
        """
        self.handle = SDK3.Open(self._index)
        for name, var in self.__dict__.items():
            sdk_name = name.replace('_', '')
            if isinstance(var, ATProperty):
                if not SDK3.IsImplemented(self.handle, sdk_name):
                    delattr(self, name)
                    continue
                var.connect(self.handle, sdk_name)

                if type(var) is ATCommand:
                    continue
                elif type(var) is ATEnum:
                    set_func = var.set_index
                    get_func = lambda v=var: (v.get_index(), v.get_string())
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
                self.add_setting(name.lstrip('_'), PROPERTY_TYPES[type(var)],
                                 get_func, set_func, vals_func)
        self.set_cooling(True)


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
        if self._camera_acquiring.get_value():
            self.abort()


    def shutdown(self):
        self.set_cooling(False)
        SDK3.Close(self.handle)


    def start_acquisition(self):
        if self._camera_acquiring.get_value():
            self._acquisition_stop()
        self._acquisition_start()


    def set_exposure_time(self, value):
        self._exposure_time.set_value(value)
        self._frame_rate.set_value(self._frame_rate.max())


    def get_exposure_time(self):
        return self._exposure_time.get_value()


    def get_cycle_time(self):
        return 1. / self._frame_rate.get_value()


    def get_sensor_shape(self):
        return (self._sensor_width.get_value(),
                self._sensor_height.get_value())


    def get_trigger_type(self):
        return TRIGGER_MODES[self._trigger_mode.get_string().lower()]



    def get_binning(self):
         as_text = self._aoi_binning.get_string().split('x')
         return tuple(int(t) for t in as_text)


    @keep_aquiring
    def set_binning(self, h, v):
        modes = self._aoi_binning.get_available_values()
        as_text = '%dx%d' % (h,v)
        if as_text in modes:
            self._aoi_binning.set_string(as_text)
            self._create_buffers()
            return True
        else:
            return False


    def get_roi(self):
        return (self._aoi_left.get_value(),
                self._aoi_top.get_value(),
                self._aoi_width.get_value(),
                self._aoi_height.get_value())


    @keep_aquiring
    def set_roi(self, x, y, width, height):
        current = self.get_roi()
        if self._camera_acquiring.get_value():
            self.abort()
        try:
            self._aoi_width.set_value(width)
            self._aoi_height.set_value(height)
            self._aoi_left.set_value(x)
            self._aoi_top.set_value(y)
        except:
            self._aoi_width.set_value(current[2])
            self._aoi_height.set_value(current[3])
            self._aoi_left.set_value(current[0])
            self._aoi_top.set_value(current[1])
            return False
        return True


    def get_gain(self):
        if hasattr(self, '_preampgain'):
            return self._preampgain.get_value()
        else:
            return None