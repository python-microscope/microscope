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
# TODO: implement timeout setting
# TODO: Better error handling
# TODO: write UniTests

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
    0: devices.TRIGGER_SOFT,  # 0:'continuous mode'
    1: devices.TRIGGER_BEFORE,  # 1:'mode0'
    2: devices.TRIGGER_DURATION  # 2:'mode1'
}
FRAME_RATES = {
    1: '3.75hz',
    2: '7.5hz',
    3: '15hz',
    4: '30hz',
    5: '60hz'
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

INVALIDATES_SETTINGS = ['_simple_pre_amp_gain_control', '_pre_amp_gain_control',
                       '_aoi_binning', '_aoi_left', '_aoi_top',
                       '_aoi_width', '_aoi_height', ]

# We setup some necessary configuration parameters. TODO: Move this into the config file
# This is the default profile path of the camera
WFS_PROFILE_PATH = b'C:\\Users\\omxt\\Documents\\PHASICS\\User Profiles\\SID4-079b default profile\\SID4-079b default profile.txt'
WFS_MASK_PATH = b'C:\\Users\\omxt\\Documents\\PHASICS\\User Profiles\\SID4-079b default profile\\Imasque.msk'

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
    
    :param header_definitions: Absolute path to the header definitions from the SDK.
    :param sid4_sdk_dll_path: name of, or absolute path to, the SID4_SDK.dll file
    :param zernike_sdk_dll_path: name of, or absolute path to, the Zernike_SDK.dll file
    :param wfs_profile_path: Absolute path to the profile file that has to be loaded at startup.
    Must be a byte encoded string.
    :param camera_attributes: This is a dictionary containing a reference to the camera attributes
    returned by the SDK's 'Camera_GetAttributeList'. The dictionary has as keys the attribute name
    and as values a tuple containing (attribute_id, min_value, max_value).
    """
    def __init__(self,
                 header_definitions=HEADER_DEFINITIONS,
                 sid4_sdk_dll_path=SID4_SDK_DLL_PATH,
                 zernike_sdk_dll_path=ZERNIKE_SDK_DLL_PATH,
                 wfs_profile_path=WFS_PROFILE_PATH,
                 wfs_mask_path=WFS_MASK_PATH,
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

        # self.camera_array_size = self.ffi.new("ArraySize *")
        self.interferogram_array_size = self.ffi.new("ArraySize *")
        self.analysis_array_size = self.ffi.new("ArraySize *")

        # Create ROI and pupil (mask) related parameters
        self.user_mask_file = self.ffi.new("char[]", self.buffer_size)
        self.user_mask_file_bs = self.ffi.cast("long", self.buffer_size)
        self.user_mask_file = wfs_mask_path

        self.roi_global_rectangle = self.ffi.new("long []", 4)
        self.roi_global_rectangle_bs = self.ffi.cast("long", 4)

        self.roi_nb_contours = self.ffi.new("unsigned short int *", 1)

        self.roi_contours_info = self.ffi.new("unsigned long []", 3)
        self.roi_contours_info_bs = self.ffi.cast("long", 3)

        self.roi_contours_coordinates = self.ffi.new("long []", 4)
        self.roi_contours_coordinates_bs = self.ffi.cast("long", 4)

        # Create zernike-related parameters
        self.zernike_information = self.ffi.new("ZernikeInformation *")
        self.zernike_parameters = self.ffi.new("ZernikeParam *")

        self.zernike_version = self.ffi.new("char[]", self.buffer_size)
        self.zernike_version_bs = self.ffi.cast("long", self.buffer_size)

        self.polynomials_list = self.ffi.new("char[]", self.buffer_size)
        self.polynomials_list_bs = self.ffi.cast("long", self.buffer_size)

        self.zernike_array_size = self.ffi.new("ArraySize *")
        self.zernike_orders = self.ffi.cast("unsigned char", 0)

        self.acquisition_buffer = {}

        # Call super __init__.
        super(SID4Device, self).__init__(**kwargs)

        # Create camera attributes. TODO: this should be created programmatically
        self.camera_attributes = camera_attributes

        # We compute a dict with exposure_times (in seconds) to Index.
        self.exposure_time_s_to_index = {}
        for key, exposure in EXPOSURE_TIMES.items():
            self.exposure_time_s_to_index[exposure[1]] = key

        # TODO: Soft_trigger
        self._is_software_trigger = True
        # HACK: as fetching the data from the camera is triggering we use this
        # variable to control that not the same data is acquired twice. Note the camera
        # uses no buffers
        self._valid_data = False

        # Add profile settings
        self.add_setting('user_profile_name', 'str',
                         lambda: self.ffi.string(self.user_profile_name),
                         None,
                         self.buffer_size,
                         readonly=True)
        self.add_setting('user_profile_file', 'str',
                         lambda: self.ffi.string(self.user_profile_file),
                         None,
                         self.buffer_size,
                         readonly=True)
        self.add_setting('user_profile_description', 'str',
                         lambda: self.ffi.string(self.user_profile_description),  # TODO: Fix here
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
        self.add_setting('camera_sn', 'str',
                         lambda: self.ffi.string(self.camera_sn),
                         None,
                         self.buffer_size,
                         readonly=True)

        # Add camera settings
        self.add_setting('frame_rate', 'enum',
                         self._get_frame_rate,
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
                         lambda: self._get_camera_attribute('ImageHeight'),
                         None,
                         lambda: (0, 480),
                         readonly=True)
        self.add_setting('camera_number_cols', 'int',
                         lambda: self._get_camera_attribute('ImageWidth'),
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
                         lambda: int(self.reference_source),  # TODO: verify returns 0
                         self._set_reference_source,
                         lambda: REFERENCE_SOURCES.keys())
        self.add_setting('reference_path', 'str',
                         lambda: self.ffi.string(self.reference_path),  # TODO: verify
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
                         self._get_phase_size_width,
                         None,
                         (0, 160),
                         readonly=True)
        self.add_setting('phase_size_height', 'int',
                         self._get_phase_size_height,
                         None,
                         (0, 120),
                         readonly=True)
        self.add_setting('zernike_base', 'enum',
                         lambda: self.zernike_information.Base,
                         self._set_zernike_base,  # TODO: not working
                         lambda: ZERNIKE_BASES.values())
        self.add_setting('nr_zernike_orders', 'int',
                         self._get_nr_zernike_orders,
                         self._set_nr_zernike_orders,
                         (0, 254))
        self.add_setting('nr_zernike_polynomials', 'int',
                         self._get_nr_zernike_polynomials,
                         None,
                         (0, 36000),
                         readonly=True)
        self.add_setting('zernike_mask_col_size', 'int',
                         lambda: self.zernike_parameters.MaskColSize,
                         None,
                         (0, 160),
                         readonly=True)
        self.add_setting('zernike_mask_row_size', 'int',
                         lambda: self.zernike_parameters.MaskRowSize,
                         None,
                         (0, 120),
                         readonly=True)
        self.add_setting('zernike_version', 'str',
                         lambda: self.ffi.string(self.zernike_version),  # TODO: error
                         None,
                         self.buffer_size,
                         readonly=True)

    def get_id(self):
        self.get_setting('camera_sn')

    def get_error(self):
        return self.error_code[0]

    def get_camera_session(self):
        return self.session_id[0]

    def invalidate_settings(self, func):
        """Wrap functions that invalidate settings so settings are reloaded."""
        outerself = self

        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            outerself._settings_valid = False
        return wrapper

    def _create_buffers(self):
        """Creates a buffer to store the data. It also reloads all necessary parameters"""
        self._refresh_zernike_attributes()

        self.analysis_array_size.nCol = self.get_setting('phase_size_width')
        self.analysis_array_size.nRow = self.get_setting('phase_size_height')

        # TODO: split phase and intensity map sizes. They are not necessarily the same
        phase_map_width = intensity_map_width = self.get_setting('phase_size_width')
        phase_map_height = intensity_map_height = self.get_setting('phase_size_height')
        nr_zernike_polynomials = self.get_setting('nr_zernike_polynomials')
        phase_map_size = intensity_map_size = phase_map_width * phase_map_height

        phase_map = self.ffi.new("float[]", phase_map_size)
        phase_map_bs = self.ffi.cast("long", phase_map_size)
        np_phase_map = np.frombuffer(buffer=self.ffi.buffer(phase_map),
                                     dtype='float32')
        np_phase_map.shape = (phase_map_width, phase_map_height)

        intensity_map = self.ffi.new("float[]", intensity_map_size)
        intensity_map_bs = self.ffi.cast("long", intensity_map_size)
        np_intensity_map = np.frombuffer(buffer=self.ffi.buffer(intensity_map),
                                         dtype='float32')
        np_intensity_map.shape = (intensity_map_width, intensity_map_height)

        tilt = self.ffi.new('TiltInfo *')
        np_tilt = np.frombuffer(buffer=self.ffi.buffer(tilt),
                                dtype='float32')

        projection_coefficients = self.ffi.new("double[]", nr_zernike_polynomials)
        projection_coefficients_bs = self.ffi.cast("long", nr_zernike_polynomials)
        np_projection_coefficients = np.frombuffer(buffer=self.ffi.buffer(projection_coefficients),
                                                   dtype='float64')

        self.acquisition_buffer.update({'phase_map': phase_map,
                                        'phase_map_bs': phase_map_bs,
                                        'np_phase_map': np_phase_map,
                                        'intensity_map': intensity_map,
                                        'intensity_map_bs': intensity_map_bs,
                                        'np_intensity_map': np_intensity_map,
                                        'tilts': tilt,
                                        'np_tilts': np_tilt,
                                        'zernike_polynomials': projection_coefficients,
                                        'zernike_polynomials_bs': projection_coefficients_bs,
                                        'np_zernike_polynomials': np_projection_coefficients})

    def _grab_live(self):
        """Uses the SDK's GrabLiveMode to get the phase and intensity maps and
        calls the Zernike functions to calculate the projection of the polynomials"""
        try:
            self.SID4_SDK.GrabLiveMode(self.session_id,
                                       self.acquisition_buffer['phase_map'],
                                       self.acquisition_buffer['phase_map_bs'],
                                       self.acquisition_buffer['intensity_map'],
                                       self.acquisition_buffer['intensity_map_bs'],
                                       self.acquisition_buffer['tilts'],
                                       self.analysis_array_size,
                                       self.error_code)
        except:
            self._logger.debug('Could not use GrabLiveMode. Error: ', self.error_code[0])
            Exception('Could not GrabLiveMode')
        try:
            self.zernike_SDK.Zernike_PhaseProjection(self.acquisition_buffer['phase_map'],
                                                     self.acquisition_buffer['phase_map_bs'],
                                                     self.zernike_array_size,
                                                     self.acquisition_buffer['zernike_polynomials'],
                                                     self.acquisition_buffer['zernike_polynomials_bs'],
                                                     self.error_code)
        except:
            self._logger.debug('Could not use PhaseProjection. Error: ', self.error_code[0])
            Exception('Could not get PhaseProjection')

    @Pyro4.expose()
    def soft_trigger(self):
        if self._acquiring and self._is_software_trigger:
            self._grab_live()
            self._valid_data = True
        else:
            raise Exception('cannot trigger if camera is not acquiring or is not in software trigger mode.')

    def _fetch_data(self, timeout=5, debug=False):
        if not self._is_software_trigger:  # Camera is not using software trigger
            self._grab_live()
        else:  # Camera is using software trigger:
            if not self._valid_data:
                return None

        self._valid_data = False

        return {'phase_map': np.copy(self.acquisition_buffer['np_phase_map']),
                'intensity_map': np.copy(self.acquisition_buffer['np_intensity_map']),
                'tilts': np.copy(self.acquisition_buffer['np_tilts']),
                'zernike_polynomials': np.copy(self.acquisition_buffer['np_zernike_polynomials'])}

    def _process_data(self, data):
        """Apply necessary transformations to data to be served to the client.

        Return as a dictionary:
        - intensity_map: a 2D array containing the intensity
        - linearity: some measure of the linearity of the data.
            Simple saturation at the intensity map might not be enough to indicate
            if we are exposing correctly to get a accurate measure of the phase.
        - phase_map: a 2D array containing the phase
        - tilts: a tuple containing X and Y tilts
        - RMS: the root mean square measurement
        - PtoV: peak to valley measurement
        - zernike_polynomials: a list with the relevant Zernike polynomials
        """
        trimmed_phase_map = self._trim_zeros(data['phase_map'])
        processed_data = {'intensity_map': self._apply_transform(data['intensity_map']),
                          'phase_map': self._apply_transform(data['phase_map']),
                          'tilts': data['tilts'],
                          'zernike_polynomials': data['zernike_polynomials'],
                          'RMS': trimmed_phase_map.std(),
                          'PtoV': trimmed_phase_map.ptp()}

        return processed_data

    def _apply_transform(self, array):
        """Apply self._transform to a numpy array"""
        flips = (self._transform[0], self._transform[1])
        rot = self._transform[2]

        # Choose appropriate transform based on (flips, rot).
        return {(0, 0): np.rot90(array, rot),
                (0, 1): np.flipud(np.rot90(array, rot)),
                (1, 0): np.fliplr(np.rot90(array, rot)),
                (1, 1): np.fliplr(np.flipud(np.rot90(array, rot)))
                }[flips]

    def _trim_zeros(self, data):
        """Returns a linear numpy array where the zeros outside the pupil have been trimmed"""
        trimmed_data = np.array([])
        for row in data:
            trimmed_data = np.append(trimmed_data, np.trim_zeros(row))
        return trimmed_data

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
            self.SID4_SDK.OpenSID4(self.user_profile_file, self.session_id, self.error_code)
            self._refresh_user_profile_params()
        except:
            raise Exception('SDK could not open.')

        # update the settings that are not implemented through the user profile or the camera attributes
        self.update_settings(settings={'nr_zernike_orders': 5})

        # Load zernike analysis settings
        self._refresh_zernike_attributes()
        self._logger.debug('Loading zernike analysis settings...')

        # Load mask descriptor file
        self._load_pupil_descriptor()
        self._logger.debug('Loading pupil settings...')

        self._logger.debug('Initializing SID4...')
        try:
            self.SID4_SDK.CameraInit(self.session_id, self.error_code)
        except:
            raise Exception('SID4 could not Init. Error code: ', self.error_code[0])
        self._logger.debug('...SID4 Initialized')

    def _on_enable(self):
        self._logger.debug('Enabling SID4.')
        if self._acquiring:
            self._acquisition_stop()
        self._logger.debug('Starting SID4 acquisition...')

        self._create_buffers()

        self._acquisition_start()
        self._logger.debug('Acquisition enabled: %s' % self._acquiring)
        return True

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

    def _on_shutdown(self):
        self.disable()
        try:
            self.SID4_SDK.CameraClose(self.session_id, self.error_code)
        except:
            raise Exception('Unable to close camera. Error code: ', str(self.error_code[0]))

        try:
            self.SID4_SDK.CloseSID4(self.session_id, self.error_code)
        except:
            raise Exception('Unable to close SDK. Error code: ', str(self.error_code[0]))

    @keep_acquiring
    def _refresh_user_profile_params(self):
        """Sets the user profile file but also reloads the SDK with OpenSID4 and
        repopulates the settings with GetUserProfile"""
        try:
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
                                         self.interferogram_array_size,
                                         self.error_code)

        except:
            raise Exception('SDK could not open. Error code: ', self.error_code[0])

    def _refresh_zernike_attributes(self):
        """Applies changes to the zernike parameters.
        :returns True if sucessful and False otherwise"""
        self.zernike_parameters.ImageRowSize = self.zernike_array_size.nCol = self.get_setting('phase_size_width')
        self.zernike_parameters.ImageColSize = self.zernike_array_size.nRow = self.get_setting('phase_size_height')
        # TODO: the two following are not necessarily true
        self.zernike_parameters.MaskRowSize = self.get_setting('phase_size_width')
        self.zernike_parameters.MaskColSize = self.get_setting('phase_size_height')

        try:
            self.zernike_SDK.Zernike_UpdateProjection_fromParameter(self.zernike_parameters,
                                                                    self.zernike_orders,
                                                                    self.error_code)
        except:
            Exception('Could not update zernike parameters')
            return False
        try:
            self.zernike_SDK.Zernike_GetZernikeInfo(self.zernike_information,
                                                    self.zernike_array_size,
                                                    self.zernike_version,
                                                    self.zernike_version_bs)
        except:
            Exception('Could not get zernike info')
            return False

        return True

    def _get_camera_attribute(self, attribute):
        attribute_id = self.ffi.cast('unsigned short int', self.camera_attributes[attribute][0])
        value = self.ffi.new('double *')
        try:
            self.SID4_SDK.Camera_GetAttribute(self.session_id,
                                              attribute_id,
                                              value,
                                              self.error_code)
        except:
            raise Exception('Could not get camera attribute: %s', attribute)

        return value[0]

    @keep_acquiring
    def _set_camera_attribute(self, attribute, value):
        attribute_id = self.ffi.cast('unsigned short int', self.camera_attributes[attribute][0])
        new_value = self.ffi.new('double *', value)
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

    def _get_frame_rate(self):
        return self._get_camera_attribute(attribute='FrameRate')

    def _set_frame_rate(self, rate):
        self._set_camera_attribute('FrameRate', rate)
        if not self.error_code[0]:
            self.camera_information.FrameRate = rate

    def _set_trigger_mode(self, mode):  # TODO: SoftTrigger
        self._set_camera_attribute('Trigger', mode)
        if not self.error_code[0]:
            self.camera_information.TriggerMode = mode
        if mode == 0:
            self._is_software_trigger = True
            self._valid_data = False
        else:
            self._is_software_trigger = False
            self._valid_data = False

    def _set_gain(self, gain):
        self._set_camera_attribute('Gain', gain)
        if not self.error_code[0]:
            self.camera_information.Gain = gain

    def get_exposure_time(self):
        return 1000 * self.get_setting('exposure_time_ms')

    def set_exposure_time(self, value):
        """The SID4 does not accept arbitrary exposure times but a limited
        number of values that are expressed in EXPOSURE_TIMES.
        We here take the closest value and apply that exposure time"""
        index = min(self.exposure_time_s_to_index, key=lambda x: abs(x - value))
        self._set_exposure_time(index=index)

    def _set_exposure_time(self, index):
        if type(index) == str:
            index = self.exposure_time_s_to_index['index']
        self._set_camera_attribute('Exposure', index)
        if not self.error_code[0]:
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

    def _get_sensor_shape(self):
        return (self.get_setting('camera_number_cols'),
                self.get_setting('camera_number_rows'))

    def _get_binning(self):
        # TODO: Check if it is not better to put here the 'natural' binning that we get after interferogram analysis
        return 1, 1

    def _set_binning(self, h_bin, v_bin):
        """binning is not implemented"""
        return False

    def _get_roi(self):
        roi = (self.roi_global_rectangle[0],
               self.roi_global_rectangle[1],
               self.roi_global_rectangle[2] - self.roi_global_rectangle[0],
               self.roi_global_rectangle[3] - self.roi_global_rectangle[1])
        return roi

    def _set_roi(self, left, top, width, height):
        right = left + width
        bottom = top + height
        self.roi_global_rectangle = [left, top, right, bottom]
        return self.set_pupil()

    def _get_pupil(self):
        return self._pupil_shape, self._pupil_edge

    def _set_pupil(self, shape, edge):
        """Implementation of a simple version to set the pupil to a circle or rectangle
        (shape) embedded into the main ROI with a certain margin (edge). It is possible
        to generate more complex pupils but I don't currently see the need."""
        self.roi_nb_contours[0] = 1  # number of sub-ROIs defining the pupil
        # sub-ROI characteristics, there are three value for each sub-ROI
        self.roi_contours_info[0] = 1  # contour is the external (0) or internal edge (1) of an sub-ROI
        self.roi_contours_info[1] = 4  # shape of the contour: 3 = Rectangle, 4 = Oval or Circle
        self.roi_contours_info[2] = 4  # Nb of coordinates defining the contour. The minimum value is 4 in the case of a simple form (rectangle, circle, ellipse) and can be higher in the case of a polygon
        self.roi_contours_info_bs = 3 * self.roi_nb_contours[0]
        # Coordinates of the Rectangle of each sub-ROI the ones behind the others.
        # They are not referred to the global ROI so we have to calculate them according to it
        # Note that the global rectangle must be defined before setting the pupil
        self.roi_contours_coordinates[0] = self.roi_global_rectangle[0] + edge
        self.roi_contours_coordinates[1] = self.roi_global_rectangle[1] + edge
        self.roi_contours_coordinates[2] = self.roi_global_rectangle[2] - edge
        self.roi_contours_coordinates[3] = self.roi_global_rectangle[3] - edge
        self.roi_contours_coordinates_bs = 4 * self.roi_nb_contours[0]

        return self._change_mask()

    @keep_acquiring
    def _change_mask(self):
        """Calls SDK ChangeMask using the current parameters. Checks for coherence
        Return False if not successful"""
        # TODO check coherence
        mask_file = self.ffi.new("char[]", self.buffer_size)
        mask_file = b''
        try:
            self.SID4_SDK.ChangeMask(self.session_id,
                                     mask_file,
                                     self.roi_global_rectangle,
                                     self.roi_global_rectangle_bs,
                                     self.roi_nb_contours,
                                     self.roi_contours_info,
                                     self.roi_contours_info_bs,
                                     self.roi_contours_coordinates,
                                     self.roi_contours_coordinates_bs,
                                     self.error_code)
        except:
            Exception('Could not change mask')
            return False

        return True

    def _load_pupil_descriptor(self, mask_descriptor_path=None):
        """Loads the mask parameters from a file"""
        if mask_descriptor_path is None:
            mask_descriptor_path = self.user_mask_file

        self.error_code[0] = 0
        self.SID4_SDK.LoadMaskDescriptor(self.session_id,
                                         mask_descriptor_path,
                                         self.roi_global_rectangle,
                                         self.roi_global_rectangle_bs,
                                         self.roi_nb_contours,
                                         self.roi_contours_info,
                                         self.roi_contours_info_bs,
                                         self.roi_contours_coordinates,
                                         self.roi_contours_coordinates_bs,
                                         self.error_code)
        # catch if the allocated arrays were not enough to contain all subROIs.
        if self.error_code[0] == 7005:
            self.roi_contours_info = self.ffi.new("unsigned long []", 3 * self.roi_nb_contours[0])
            self.roi_contours_info_bs = self.ffi.cast("long", 3 * self.roi_nb_contours[0])

            self.roi_contours_coordinates = self.ffi.new("long []", 4 * self.roi_nb_contours[0])
            self.roi_contours_coordinates_bs = self.ffi.cast("long", 4 * self.roi_nb_contours[0])
            self._load_pupil_descriptor(mask_descriptor_path=mask_descriptor_path)

    def _get_phase_size_width(self):
        # HACK: This is actually not the right way to collect this info but cffi is
        # otherwise getting different bytes from memory
        return int.from_bytes(self.ffi.buffer(self.analysis_information)[17:21], 'little')

    def _get_phase_size_height(self):
        # HACK: This is actually not the right way to collect this info but cffi is
        # otherwise getting different bytes from memory
        return int.from_bytes(self.ffi.buffer(self.analysis_information)[21:25], 'little')

    def _set_zernike_base(self, base):
        current_base = self.zernike_parameters.Base
        self.zernike_parameters.Base = base
        if self._refresh_zernike_attributes():
            return
        else:
            self.zernike_parameters.Base = current_base

    def _get_nr_zernike_orders(self):
        return self.zernike_orders

    def _set_nr_zernike_orders(self, orders):
        current_orders = self.zernike_orders
        self.zernike_orders = orders
        if self._refresh_zernike_attributes():
            return
        else:
            self.zernike_orders = current_orders

    def _get_nr_zernike_polynomials(self):
        return int.from_bytes(self.ffi.buffer(self.zernike_information)[2:6], 'little')

    def _set_zernike_mask_row_size(self, row_size):
        pass

    def _set_zernike_mask_col_size(self, col_size):
        pass

if __name__ == '__main__':

    wfs = SID4Device()
    wfs.initialize()
    wfs.enable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.disable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.enable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.disable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.shutdown()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.initialize()
    wfs.enable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.disable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.shutdown()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))
    wfs.enable()
    print('Enabled: ' + str(wfs.get_is_enabled()))
    print('Acquiring: ' + str(wfs._acquiring))

    for i in range(3):
        wfs.soft_trigger()



    print('Current exposure_time: ', wfs.get_setting('exposure_time'))
    print('Changing exposure_time')
    wfs.set_setting('exposure_time', 2)
    print('Current exposure_time: ', wfs.get_setting('exposure_time'))
    wfs.soft_trigger()

    print(wfs._fetch_data()['intensity_map'][15, 15])
    print('Changing exposure_time')
    wfs.set_setting('exposure_time', 2)
    print('Current exposure_time: ', wfs.get_setting('exposure_time'))
    print('Changing exposure_time')
    wfs.set_setting('exposure_time', 3)
    print('Current exposure_time: ', wfs.get_setting('exposure_time'))
    print('Changing exposure_time')
    wfs.set_setting('exposure_time', 6)
    print('Current exposure_time: ', wfs.get_setting('exposure_time'))
    print('Changing exposure_time')
    wfs.set_setting('exposure_time', 8)
    print('Current exposure_time: ', wfs.get_setting('exposure_time'))
    for i in range(10):
        wfs.soft_trigger()
        print(wfs._fetch_data()['intensity_map'][15, 15])
    exposure_time = wfs.get_setting('exposure_time')
    print(exposure_time)
    wfs.set_setting('exposure_time', 5)
    # wfs.set_setting('exposure_time', '1/200s')
    print('Changing Exposure time')
    exposure_time = wfs.get_setting('exposure_time')
    print(exposure_time)
    frame_rate = wfs.get_setting('frame_rate')
    print('FrameRate: ', frame_rate)
    wfs.set_setting('frame_rate', 1)
    frame_rate = wfs.get_setting('frame_rate')
    print('FrameRate: ', frame_rate)
    for i in range(10):
        wfs.soft_trigger()
        print(wfs._fetch_data()['intensity_map'][15,15])
    wfs.set_setting('frame_rate', 5)
    frame_rate = wfs.get_setting('frame_rate')
    print('FrameRate: ', frame_rate)
    print('Changing mask to 80')
    wfs.set_roi(100, 100, 80, 80)
    for i in range(10):
        wfs.soft_trigger()
        print(wfs._fetch_data()['intensity_map'][15,15])

    wfs.shutdown()