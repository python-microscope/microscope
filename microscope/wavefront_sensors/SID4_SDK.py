#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2016 Julio Mateos Langerak (julio.mateos-langerak@igh.cnrs.fr)
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
"""SID4_SDK wavefront sensor device.

This module provides a wrapper for SID4's SDK interface that allows
a SID4 wavefront sensor from Phasics and all its settings to be exposed over Pyro.

The interface with the SID4 SDK has been implemented using cffi API 'in line'
"""
from microscope import devices
from microscope.devices import WavefrontSensorDevice, keep_acquiring
from cffi import FFI
import Pyro4
import numpy as np
import time
# Python 2.7 to 3
try:
    import queue
except:
    import Queue as queue

# Trigger mode to type.
TRIGGER_MODES = {
    0: devices.TRIGGER_SOFT,  # 0:'continuous mode' TODO: check all this
    1: devices.TRIGGER_SOFT,  # 1:'mode0'
    2: devices.TRIGGER_BEFORE  # 2:'mode1'
}
FRAME_RATES = {
    0: '3.75hz',
    1: '7.5hz',
    2: '15hz',
    3: '30hz',
    4: '60hz'
}
EXPOSURE_TIMES = {  # Asa string and in msec
    0: ('1/60s', 16.6667),
    1: ('1/200s', 5.0),
    2: ('1/500s', 2.0),
    3: ('1/1000s', 1.0),
    4: ('1/2000s', 0.5),
    5: ('1/4000s', 0.25),
    6: ('1/8000s', 0.125),
    7: ('1/20000s', 0.05)
}
REFERENCE_SOURCES = {
    0: 'SDK_WORKSHOP',  # Workshop reference
    1: 'SDK_CAMERA',  # Reference from a grabbed camera image
    2: 'SDK_FILE'  # Reference from an interferogram file, which path is given by ReferencePath
}
ZERNIKE_BASES = {0: 'Zernike', 1: 'Legendre'}
CAMERA_ATTRIBUTES = {
    'Exposure': (0, 0, 7),
    'Gain': (1, 40, 210),
    'GainOffset': (2, -1, -1),
    'Trigger': (3, 0, 2),
    'FrameRate': (4, 1, 5),
    'ImageWidth': (5, -1, -1),
    'ImageHeight': (6, -1, -1),
    'TimeOut': (7, 1, 10000),
    'AE_On/Off': (8, -1, -1)
}

INVALIDATES_BUFFERS = ['_simple_pre_amp_gain_control', '_pre_amp_gain_control',
                       '_aoi_binning', '_aoi_left', '_aoi_top',
                       '_aoi_width', '_aoi_height', ]

# We setup some necessary configuration parameters
# TODO: Move this into the config file

# This is the default profile path of the camera
WFS_PROFILE_PATH = b'C:\\Users\\omxt\\Documents\\PHASICS\\User Profiles\\SID4-079b default profile\\SID4-079b default profile.txt'

# We import the headers definitions used by cffi from a file in order to avoid copyright issues
HEADER_DEFINITIONS = "C:\\Users\\omxt\\PycharmProjects\\microscope\\microscope\\wavefront_sensors\\SID4_SDK_defs"
SID4_SDK_DLL_PATH = "SID4_SDK.dll"
ZERNIKE_SDK_DLL_PATH = "Zernike_SDK.dll"


@Pyro4.expose
# @Pyro4.behavior('single')
class SID4Device(WavefrontSensorDevice):
    """
    This class represents the SID4 wavefront sensors
    Important note: The header defs is a text file containing the headers from 
    the SID4_SDK.h file with some modifications. Namely all #include and #ifdef have been  
    removed. Also, the typedef of LVBoolean has been changed for 'unsigned char'
    
    :param header_defs: Absolute path to the header definitions from the SDK.
    :param dll_path: name of, or absolute path to the SID4_SDK.dll file
    :param wfs_profile_path: Absolute path to the profile file that has to be loaded at startup.
    Must be a byte encoded string.
    """
    def __init__(self,
                 header_definitions=HEADER_DEFINITIONS,
                 sid4_sdk_dll_path=SID4_SDK_DLL_PATH,
                 zernike_sdk_dll_path=ZERNIKE_SDK_DLL_PATH,
                 wfs_profile_path=WFS_PROFILE_PATH,
                 camera_attributes=CAMERA_ATTRIBUTES,
                 **kwargs):
        self.header_definitions = header_definitions
        try:
            with open(self.header_definitions, 'r') as self.header_definitions:
                self.cdef_from_file = self.header_definitions.read()
        except FileNotFoundError:
            print('Unable to find "%s" header file.' % self.header_definitions)
            exit(1)
        except IOError:
            print('Unable to open "%s"' % self.header_definitions)
            exit(2)
        finally:
            if self.cdef_from_file == '' or None:
                print('File "%s" is empty' % self.header_definitions)
                exit(3)
                
        # Create here the interface to the SDK
        self.ffi = FFI()
        self.ffi.cdef(self.cdef_from_file, override=True)
        self.SID4_SDK = self.ffi.dlopen(sid4_sdk_dll_path)
        self.zernike_SDK = self.ffi.dlopen(zernike_sdk_dll_path)
        
        # Allocate all necessary instances to control the SID4
        self.buffer_size = 1024  # buffer size to be used to initialize some variables

        # Create main instances
        self.session_id = self.ffi.new('SDK_Reference *')
        self.error_code = self.ffi.new('long *', 0)

        # Create metadata instances
        self.user_profile_name = self.ffi.new("char[]", self.buffer_size)
        self.user_profile_name_bs = self.ffi.cast("long", self.buffer_size)

        self.user_profile_file = self.ffi.new("char[]", self.buffer_size)
        self.user_profile_file_bs = self.ffi.cast("long", self.buffer_size)
        self.user_profile_file = wfs_profile_path

        self.user_profile_description = self.ffi.new("char[]", self.buffer_size)
        self.user_profile_description_bs = self.ffi.cast("long", self.buffer_size)

        self.user_profile_last_reference = self.ffi.new("char[]", self.buffer_size)
        self.user_profile_last_reference_bs = self.ffi.cast("long", self.buffer_size)

        self.user_profile_directory = self.ffi.new("char[]", self.buffer_size)
        self.user_profile_directory_bs = self.ffi.cast("long", self.buffer_size)

        self.sdk_version = self.ffi.new("char[]", self.buffer_size)
        self.sdk_version_bs = self.ffi.cast("long", self.buffer_size)

        self.analysis_information = self.ffi.new("AnalysisInfo *")
        self.camera_information = self.ffi.new("CameraInfo *")

        self.reference_source = self.ffi.cast("unsigned short int", 0)
        self.reference_path = self.ffi.new("char[]", self.buffer_size)
        self.reference_changed = self.ffi.cast("unsigned char", 0)

        self.camera_sn = self.ffi.new("char[]", self.buffer_size)
        self.camera_sn_bs = self.ffi.cast("long", self.buffer_size)

        self.camera_array_size = self.ffi.new('ArraySize *')
        self.analysis_array_size = self.ffi.new('ArraySize *')

        # Create zernike-related parameters
        self.zernike_information = self.ffi.new("ZernikeInformation *")
        self.zernike_parameters = self.ffi.new("ZernikeParam *")

        self.zernike_version = self.ffi.new("char[]", self.buffer_size)
        self.zernike_version_bs = self.ffi.cast("long", self.buffer_size)

        self.polynomials_list = self.ffi.new("char[]", self.buffer_size)
        self.polynomials_list_bs = self.ffi.cast("long", self.buffer_size)

        # Call super __init__.
        super(SID4Device, self).__init__(**kwargs)

        # Create camera attributes. TODO: this should be created programmatically
        self.camera_attributes = camera_attributes

        # Add profile settings
        self.add_setting('user_profile_name', 'str',
                         lambda: self.ffi.string(self.user_profile_name),
                         None,
                         self.buffer_size,
                         readonly=True)
        self.add_setting('user_profile_file', 'str',
                         lambda: self.ffi.string(self.user_profile_file),  # TODO: this lambda will probably not work
                         self._set_user_profile_file,
                         self.buffer_size)
        self.add_setting('user_profile_description', 'str',
                         lambda: self.ffi.string(self.user_profile_description),
                         None,
                         self.buffer_size,
                         readonly=True)
        self.add_setting('user_profile_last_reference', 'str',
                         lambda: self.ffi.string(self.user_profile_last_reference),
                         None,
                         self.buffer_size,
                         readonly=True)
        self.add_setting('user_profile_last_directory', 'str',
                         lambda: self.ffi.string(self.user_profile_directory),
                         None,
                         self.buffer_size,
                         readonly=True)
        self.add_setting('sdk_version', 'str',
                         lambda: self.ffi.string(self.sdk_version),
                         None,
                         self.buffer_size,
                         readonly=True)

        # Add camera settings
        self.add_setting('frame_rate', 'enum',
                         lambda: FRAME_RATES[self.camera_information.FrameRate],
                         self._set_frame_rate,
                         lambda: FRAME_RATES.keys())
        self.add_setting('trigger_mode', 'enum',
                         lambda: TRIGGER_MODES[self.camera_information.TriggerMode],
                         self._set_trigger_mode,
                         lambda: TRIGGER_MODES.keys())
        self.add_setting('gain', 'int',
                         lambda: self.camera_information.Gain,
                         self._set_gain,
                         lambda: (40, 210))
        self.add_setting('exposure_time', 'enum',
                         lambda: self.camera_information.ExposureTime,
                         self._set_exposure_time,
                         lambda: EXPOSURE_TIMES.keys())
        self.add_setting('exposure_time_ms', 'float',
                         lambda: EXPOSURE_TIMES[self.camera_information.ExposureTime][1],
                         None,  # The SID4 does not support an arbitrary exposure time.
                         lambda: (0.05, 17.0),
                         readonly=True)
        self.add_setting('camera_pixel_size_m', 'float',
                         lambda: self.camera_information.PixelSizeM,
                         None,
                         lambda: (0.0, 0.1),
                         readonly=True)
        self.add_setting('camera_number_rows', 'int',
                         lambda: self.camera_array_size.nRow,
                         None,
                         lambda: (0, 480),
                         readonly=True)
        self.add_setting('camera_number_cols', 'int',
                         lambda: self.camera_array_size.nCol,
                         None,
                         lambda: (0, 640),
                         readonly=True)
        self.add_setting('number_of_camera_recorded', 'int',
                         lambda: self.camera_information.NumberOfCameraRecorded,
                         None,
                         lambda: (0, 255),
                         readonly=True)

        # Add analysis settings
        self.add_setting('reference_source', 'enum',
                         lambda: int(self.reference_source),
                         self._set_reference_source,
                         lambda: REFERENCE_SOURCES.keys())
        self.add_setting('reference_path', 'str',
                         lambda: int(self.reference_path),
                         self._set_reference_path,
                         self.buffer_size)
        self.add_setting('grating_position_mm', 'float',
                         lambda: self.analysis_information.GratingPositionMm,
                         None,
                         (0.0, 300.0),  # TODO: Verify these values
                         readonly=True)
        self.add_setting('wavelength_nm', 'float',
                         self._get_wavelength_nm,
                         self._set_wavelength_nm,
                         (400.0, 1100.0))
        self.add_setting('remove_background_image', 'bool',
                         lambda: self.analysis_information.RemoveBackgroundImage,
                         self._set_remove_background_image,
                         None)
        self.add_setting('phase_size_width', 'int',
                         lambda: self.analysis_information.PhaseSize_width,
                         None,
                         (0, 160),
                         readonly=True)
        self.add_setting('phase_size_height', 'int',
                         lambda: self.analysis_information.PhaseSize_Height,
                         None,
                         (0, 120),
                         readonly=True)
        self.add_setting('zernike_base', 'enum',
                         self._get_zernike_base,
                         self._set_zernike_base,
                         lambda: ZERNIKE_BASES.values())
        self.add_setting('zernike_polynomials', 'int',
                         self._get_zernike_polynomials,
                         self._set_zernike_polynomials,
                         (0, 254))
        self.add_setting('image_row_size', 'int',
                         lambda: self.zernike_parameters.ImageRowSize,
                         None,
                         (0, 480),
                         readonly=True)
        self.add_setting('image_col_size', 'int',
                         lambda: self.zernike_parameters.ImageColSize,
                         None,
                         (0, 640),
                         readonly=True)
        self.add_setting('mask_row_size', 'int',
                         lambda: self.zernike_parameters.MaskRowSize,
                         None,
                         (0, 480),
                         readonly=True)
        self.add_setting('mask_col_size', 'int',
                         lambda: self.zernike_parameters.MaskColSize,
                         None,
                         (0, 640),
                         readonly=True)
        self.add_setting('zernike_version', 'str',
                         lambda: self.zernike_version,
                         None,
                         self.buffer_size,
                         readonly=True)

        # Software buffers and parameters for data conversion.
        self.num_buffers = 32
        self.add_setting('num_buffers', 'int',
                         lambda: self.num_buffers,
                         lambda val: self.set_num_buffers(val),
                         (1, 100))
        self.buffers = queue.Queue()
        self.filled_buffers = queue.Queue()
        self._buffer_size = None
        self._buffers_valid = False
        self._exposure_callback = None

    # @property
    # def _acquiring(self):
    #     return self._camera_acquiring.get_value()
    #
    # @keep_acquiring
    # def _enable_callback(self, use=False):
    #     pass # TODO: Verify if we need this
    #
    # @_acquiring.setter
    # def _acquiring(self, value):
    #     pass # TODO: Verify if we need this

    def set_num_buffers(self, num):
        self.num_buffers = num
        self._buffers_valid = False

    def _purge_buffers(self):
        """Purge buffers on both camera and PC."""
        self._logger.debug("Purging buffers.")
        self._buffers_valid = False
        if self._acquiring:
            raise Exception('Can not modify buffers while camera acquiring.')
        # TODO: implement the flush
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
        self._logger.debug("Creating %d buffers." % num)
        intensity_map_size = self._intensity_map_size.get_value()
        phase_map_size = self._phase_map_size.get_value()
        zernike_indexes_size = self._zernike_indexes_size.get_value()
        for i in range(num):
            intensity_buf = np.require(np.empty(intensity_map_size),
                                       dtype='uint32',
                                       requirements=['C_CONTIGUOUS',
                                                     'ALIGNED',
                                                     'OWNDATA'])
            phase_buf = np.require(np.empty(phase_map_size),
                                   dtype='float32',
                                   requirements=['C_CONTIGUOUS',
                                                 'ALIGNED',
                                                 'OWNDATA'])
            # Create data instances in either way
            self.tilt_information = self.ffi.new('TiltInfo *')
            self.projection_coefficients_in = self.ffi.new("double[]", zernike_indexes_size)

            tilts_buf = np.require(np.empty(2),
                                   dtype='float32',
                                   requirements=['C_CONTIGUOUS',
                                                 'ALIGNED',
                                                 'OWNDATA'])
            rms_buf = np.require(np.empty(1),
                                 dtype='float32',
                                 requirements=['C_CONTIGUOUS',
                                               'ALIGNED',
                                               'OWNDATA'])
            ptv_buf = np.require(np.empty(1),
                                 dtype='int32',
                                 requirements=['C_CONTIGUOUS',
                                               'ALIGNED',
                                               'OWNDATA'])
            zernike_buf = np.require(np.empty(zernike_indexes_size),
                                     dtype='float64',
                                     requirements=['C_CONTIGUOUS',
                                                   'ALIGNED',
                                                   'OWNDATA'])

            self.buffers.put([intensity_buf,
                              phase_buf,
                              tilts_buf,
                              rms_buf,
                              ptv_buf,
                              zernike_buf])
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
            raw = self.filled_buffers.get(timeout=timeout)
        except:
            raise Exception('There is no data in the buffer')
        data = [np.copy(x) for x in raw]

        # Requeue the buffer. TODO: we should check if buffer size has not been changed elsewhere.
        self.buffers.put(raw)

        return data

    def abort(self):
        """Abort acquisition."""
        self._logger.debug('Aborting acquisition.')
        if self._acquiring:
            self._acquisition_stop()

    def initialize(self):
        """Initialize the SID4

        Opens the connection to the SDK, initializes the SID4 and populates the settings
        from the input profile"""
        self._logger.debug('Opening SDK...')
        try:
            self._set_user_profile_file(self.user_profile_file)
        except:
            raise Exception('SDK could not open.')

        # get the camera attributes and populate them
        # self._get_camera_attribute_list()

        # Default setup
        # self.trigger_mode.set_string('Software')z
        # self._cycle_mode.set_string('Continuous')

        # def callback(*args):
        #     data = self._fetch_data(timeout=500)
        #     timestamp = time.time()
        #     if data is not None:
        #         self._dispatch_buffer.put((data, timestamp))
        #         return 0
        #     else:
        #         return -1
        #
        # self._exposure_callback = SDK3.CALLBACKTYPE(callback)

    # def _get_camera_attribute_list(self):
    #     """This method updates the camera attributes stored in the camera_attributes dict
    #
    #     To call at camera initialization"""
    #     self.nr_of_attributes = self.ffi.new('long *')
    #     print(self.nr_of_attributes[0])
    #     # try:
    #     #     self.SID4_SDK.Camera_GetNumberOfAttribute(self.session_id, self.nr_of_attributes, self.error_code)
    #     # except:
    #     #     raise Exception('Could not get nr_of_attributes.')
    #     print(self.error_code[0])
    #     print(self.nr_of_attributes[0])
    #
    #     self.attribute_id = self.ffi.new('unsigned short int[]', self.nr_of_attributes[0])
    #     self.attribute_id_bs = self.ffi.cast('long', self.nr_of_attributes[0])
    #     self.attributes = self.ffi.new('char[]', self.buffer_size)
    #     self.attributes_bs = self.ffi.cast('long', self.buffer_size)
    #     self.attribute_min = self.ffi.new('long[]', self.nr_of_attributes[0])
    #     self.attribute_min_bs = self.ffi.cast('long', self.nr_of_attributes[0] * 4)
    #     self.attribute_max = self.ffi.new('long[]', self.nr_of_attributes[0])
    #     self.attribute_max_bs = self.ffi.cast('long', self.nr_of_attributes[0] * 4)
    #     # self.attribute_id = self.ffi.new('unsigned short int[]', 9)
    #     # self.attribute_id_bs = self.ffi.cast('long', 36)
    #     # self.attributes = self.ffi.new('char[]', 1024)
    #     # self.attributes_bs = self.ffi.cast('long', 1024)
    #     # self.attribute_min = self.ffi.new('long[]', 9)
    #     # self.attribute_min_bs = self.ffi.cast('long', 36)
    #     # self.attribute_max = self.ffi.new('long[]', 9)
    #     # self.attribute_max_bs = self.ffi.cast('long', 36)
    #
    #     self.SID4_SDK.Camera_GetAttributeList(self.session_id,
    #                                           self.attribute_id,
    #                                           self.attribute_id_bs,
    #                                           self.attributes,
    #                                           self.attributes_bs,
    #                                           self.attribute_min,
    #                                           self.attribute_min_bs,
    #                                           self.attribute_max,
    #                                           self.attribute_max_bs,
    #                                           self.error_code)
    #
    #     print(self.error_code[0])
    #
    #     self.attributes_list = self.ffi.string(self.attributes)  # [:-2].split(sep = b'\t')
    #
    #     for i in range(self.nr_of_attributes[0]):
    #         self.camera_attributes[self.attributes_list[i]] = (self.attribute_id[i],
    #                                                            self.attribute_min[i],
    #                                                            self.attribute_max[i])

    def _on_enable(self):
        self._logger.debug('Enabling SID4.')
        if self._acquiring:
            self._acquisition_stop()
        self._create_buffers()

        self._logger.debug('Initializing SID4...')
        try:
            self.SID4_SDK.CameraInit(self.session_id, self.error_code)
        except:
            raise Exception('SID4 could not Init. Error code: ', self.error_code[0])

    def _acquisition_start(self):
        try:
            self.SID4_SDK.CameraStart(self.session_id, self.error_code)
            if not self.error_code[0]:
                self._acquiring = True
        except:
            raise Exception('Unable to enable SID4. Error code: ', str(self.error_code[0]))

    def _acquisition_stop(self):
        try:
            self.SID4_SDK.CameraStop(self.session_id, self.error_code)
            if not self.error_code[0]:
                self._acquiring = False
        except:
            raise Exception('Unable to stop acquisiiton. Error code: ', str(self.error_code[0]))

    def _on_disable(self):
        self.abort()
        self._buffers_valid = False
        try:
            self.SID4_SDK.CameraClose(self.session_id, self.error_code)
        except:
            raise Exception('Unable to close camera. Error code: ', str(self.error_code[0]))

    def _on_shutdown(self):
        self.abort()
        self.disable()
        try:
            self.SID4_SDK.CloseSID4(self.session_id, self.error_code)
        except:
            raise Exception('Unable to close SDK. Error code: ', str(self.error_code[0]))

            # phase = ffi.new('float[]', 4096)
        # phase_bs = ffi.cast('long', 16384)
        # intensity = ffi.new('float[]', 4096)
        # intensity_bs = ffi.cast('long', 16384)
        #
        # image = ffi.new("short int[307200]")
        # image_bs = ffi.cast("long", 307200)
        #
        #
        #
        # ffi.string(self.user_profile_name)
        # int(user_profile_name_bs)
        
        # print(analysis_information.GratingPositionMm)
        # print(analysis_information.wavelengthNm)
        # print(analysis_information.RemoveBackgroundImage)
        # print(analysis_information.PhaseSize_width)
        # print(analysis_information.PhaseSize_Height)
        #
        # print(camera_information.FrameRate)
        # print(camera_information.TriggerMode)
        # print(camera_information.Gain)
        # print(camera_information.ExposureTime)
        # print(camera_information.PixelSizeM)
        # print(camera_information.NumberOfCameraRecorded)
        #
        #
        # print('Starting Live mode...')
        # SDK.StartLiveMode(self.session_id, self.error_code)
        # print(self.error_code[0])
        #
        # print('Grabbing image...')
        # SDK.GrabImage(self.session_id, image, image_bs, camera_array_size, self.error_code)
        # print(self.error_code[0])
        #
        # print('Part of the image')
        # print([x for x in image[0:20]])
        #
        # print('Grabbing Live mode...')
        # SDK.GrabLiveMode(self.session_id, phase, phase_bs, intensity, intensity_bs, self.tilt_information, self.analysis_array_size, self.error_code)
        # print(self.error_code[0])
        ##
        ##print('Part of the phase')
        ##print([x for x in phase[0:20]])
        ##
        ##print('Part of the intensity')
        ##print([x for x in intensity[0:20]])
        ##
        ##print('Stopping Live mode...')
        ##SDK.StopLiveMode(session_id, error_code)
        ##print(error_code[0])
        ##
        ##print('Closing camera...')
        ##SDK.CameraClose(session_id, error_code)
        ##print(error_code[0])
        ##
        ##print('Closing SDK...')
        ##SDK.CloseSID4(session_id, error_code)
        ##print(error_code[0])
        ##
        ### keep phase alive
        ##a = phase

    @keep_acquiring
    def _set_user_profile_file(self, path=None):
        """Sets the user profile file but also reloads the SDK with OpenSID4 and
        repopulates the settings with GetUserProfile"""
        self.user_profile_file = path
        try:
            self.SID4_SDK.OpenSID4(self.user_profile_file, self.session_id, self.error_code)
            self.SID4_SDK.GetUserProfile(self.session_id,
                                         self.user_profile_name,
                                         self.user_profile_name_bs,
                                         self.user_profile_file,
                                         self.user_profile_file_bs,
                                         self.user_profile_description,
                                         self.user_profile_description_bs,
                                         self.user_profile_last_reference,
                                         self.user_profile_last_reference_bs,
                                         self.user_profile_directory,
                                         self.user_profile_directory_bs,
                                         self.sdk_version,
                                         self.sdk_version_bs,
                                         self.analysis_information,
                                         self.camera_information,
                                         self.camera_sn,
                                         self.camera_sn_bs,
                                         self.analysis_array_size,
                                         self.error_code)
        except:
            raise Exception('SDK could not open. Error code: ', self.error_code[0])

        print(self.session_id[0])
        print(self.ffi.string(self.user_profile_name))
        print(int(self.user_profile_name_bs))
        print(self.user_profile_file)
        print(int(self.user_profile_file_bs))
        print(self.ffi.string(self.user_profile_description))
        print(int(self.user_profile_description_bs))
        print(self.ffi.string(self.user_profile_last_reference))
        print(int(self.user_profile_last_reference_bs))
        print(self.ffi.string(self.user_profile_directory))
        print(int(self.user_profile_directory_bs))
        print(self.ffi.string(self.sdk_version))
        print(int(self.sdk_version_bs))
        print(self.analysis_information.GratingPositionMm)
        print(self.analysis_information.wavelengthNm)
        print(self.analysis_information.RemoveBackgroundImage)
        print(self.analysis_information.PhaseSize_width)
        print(self.analysis_information.PhaseSize_Height)
        print(self.camera_information.FrameRate)
        print(self.camera_information.TriggerMode)
        print(self.camera_information.Gain)
        print(self.camera_information.ExposureTime)
        print(self.camera_information.PixelSizeM)
        print(self.camera_information.NumberOfCameraRecorded)
        print(self.ffi.string(self.camera_sn))
        print(int(self.camera_sn_bs))
        print(self.analysis_array_size.nRow)
        print(self.analysis_array_size.nCol)
        print(self.error_code[0])

    @keep_acquiring
    def _set_camera_attribute(self, attribute, value):
        attribute_id = self.ffi.cast('unsigned short int', self.camera_attributes[attribute][0])
        new_value = self.ffi.cast('double', value)
        try:
            self.SID4_SDK.Camera_SetAttribute(self.session_id,
                                              attribute_id,
                                              new_value,
                                              self.error_code)
        except:
            raise Exception('Could not change camera attribute: %s', attribute)

    def _modify_user_profile(self, save=False):

        try:
            self.SID4_SDK.ModifyUserProfile(self.session_id,
                                            self.analysis_information,
                                            self.reference_source,
                                            self.reference_path,
                                            self.user_profile_description,
                                            self.reference_changed,
                                            self.error_code)
        except:
            Exception('Could not modify user profile')

        if save:
            self._save_user_profile()

    def _save_user_profile(self):
        try:
            self.SID4_SDK.SaveCurrentUserProfile(self.session_id, self.error_code)
        except:
            Exception('Could not save user profile')

    def _set_frame_rate(self, rate):
        self._set_camera_attribute('FrameRate', rate)
        if self.error_code[0]:
            self.camera_information.FrameRate = rate

    def _set_trigger_mode(self, mode):
        self._set_camera_attribute('Trigger', mode)
        if self.error_code[0]:
            self.camera_information.TriggerMode = mode

    def _set_gain(self, gain):
        self._set_camera_attribute('Gain', gain)
        if self.error_code[0]:
            self.camera_information.Gain = gain

    def _set_exposure_time(self, index):
        self._set_camera_attribute('Exposure', index)
        if self.error_code[0]:
            self.camera_information.ExposureTime = index

    def _set_reference_source(self, source, save=False):
        self.reference_source = source
        self._modify_user_profile(save=save)

    def _set_reference_path(self, path, save=False):
        self.reference_path = path
        self._modify_user_profile(save=save)

    def _get_wavelength_nm(self):
        return self.analysis_information.wavelengthNm

    def _set_wavelength_nm(self, wavelength, save=False):
        self.analysis_information.wavelengthNm = wavelength
        self._modify_user_profile(save=save)

    def _set_remove_background_image(self, remove, save=False):
        if remove:
            self.analysis_information.RemoveBackgroundImage = 1
        else:
            self.analysis_information.RemoveBackgroundImage = 0

        self._modify_user_profile(save=save)

    def _set_phase_size_width(self, width, save=False):
        self.analysis_information.PhaseSize_width = width
        self._modify_user_profile(save=save)

    def _set_phase_size_height(self, height, save=False):
        self.analysis_information.PhaseSize_Height = height
        self._modify_user_profile(save=save)

    def _get_intensity_size_width(self):
        pass

    def _set_intensity_size_width(self):
        pass

    def _get_intensity_size_height(self):
        pass

    def _set_intensity_size_height(self):
        pass

    def _get_zernike_base(self):
        pass

    def _set_zernike_base(self):
        pass

    def _get_zernike_polynomials(self):
        pass

    def _set_zernike_polynomials(self):
        pass


if __name__ == '__main__':

    wfs = SID4Device()
    wfs.initialize()
