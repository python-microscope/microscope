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

This class provides a wrapper for SID4's SDK interface that allows
a SID4 wavefront sensor from Phasics and all its settings to be exposed over Pyro.
"""

from cffi import FFI



header_defs = "C:\\Users\\omxt\\PycharmProjects\\microscope\\microscope\\wavefront_sensors\\SID4_SDK_defs"
header_path = "C:\\Program Files (x86)\\SID4_SDK\\DLL SDK\\Headers\\SID4_SDK.h"
cdef_from_file = ''

try:
    with open(header_defs, 'r') as header_defs:
        cdef_from_file = header_defs.read()
except FileNotFoundError:
    print('Unable to find "%s" header file.' % header_defs)
    exit(1)
except IOError:
    print('Unable to open "%s"' % header_defs)
    exit(2)
finally:
    if cdef_from_file == '' or None:
        print('File "%s" is empty' % header_defs)
        exit(3)

ffi = FFI()

ffi.cdef(cdef_from_file)

SDK = ffi.dlopen("SID4_SDK.dll")
ZernikeSDK = ffi.dlopen("Zernike_SDK.dll")

buffer_size = 1024

user_profile_file_in = ffi.new("char[]", buffer_size)
user_profile_file_in_bs = ffi.cast("long", buffer_size)
user_profile_file_in = b'C:\\Users\\omxt\\Documents\\PHASICS\\User Profiles\\SID4-079b default profile\\SID4-079b default profile.txt'

interferogram_file = ffi.new("char[]", buffer_size)
interferogram_file_bs = ffi.cast("long", buffer_size)
interferogram_file = "C:\\Program Files (x86)\\SID4_SDK\\Examples\\Labview\\Interferograms\\Interferogram.tif"

session_id = ffi.new('SDK_Reference *', 0)

nrow = ffi.new("int *", 0)
ncol = ffi.new("int *", 0)

error_code = ffi.new('long *', 0)

user_profile_name = ffi.new("char[]", buffer_size) # initialize first with a certain buffer size
user_profile_name_bs = ffi.cast("long", buffer_size)

user_profile_file_out = ffi.new("char[]", buffer_size)
user_profile_file_out_bs = ffi.cast("long", buffer_size)

user_profile_description = ffi.new("char[]", buffer_size)
user_profile_description_bs = ffi.cast("long", buffer_size)

user_profile_last_reference = ffi.new("char[]", buffer_size)
user_profile_last_reference_bs = ffi.cast("long", buffer_size)

user_profile_last_directory = ffi.new("char[]", buffer_size)
user_profile_last_directory_bs = ffi.cast("long", buffer_size)

sdk_version = ffi.new("char[]", buffer_size)
sdk_version_bs = ffi.cast("long", buffer_size)

analysis_information = ffi.new("AnalysisInfo *")

camera_information = ffi.new("CameraInfo *")

camera_sn = ffi.new("char[]", buffer_size)
camera_sn_bs = ffi.cast("long", buffer_size)

image_size = ffi.new("ArraySize *")

# tilt_information = ffi.new('TiltInfo *')
# analysis_array_size = ffi.new('ArraySize *', [64,64])

print('Opening SDK...')
SDK.OpenSID4(user_profile_file_in, session_id, error_code)
print('Session ID:')
print(session_id)
print('Error code:')
print(error_code[0])

SDK.GetUserProfile(session_id,
                   user_profile_name,
                   user_profile_name_bs,
                   user_profile_file_out,
                   user_profile_file_out_bs,
                   user_profile_description,
                   user_profile_description_bs,
                   user_profile_last_reference,
                   user_profile_last_reference_bs,
                   user_profile_last_directory,
                   user_profile_last_directory_bs,
                   sdk_version,
                   sdk_version_bs,
                   analysis_information,
                   camera_information,
                   camera_sn,
                   camera_sn_bs,
                   image_size,
                   error_code)

print('Initializing WFS...')
SDK.CameraInit(session_id, error_code)
print(error_code[0])

##print('Starting WFS...')
##SDK.CameraStart(session_id, error_code)
##print(error_code[0])
##
##print('Stoping WFS...')
##SDK.CameraStop(session_id, error_code)
##print(error_code[0])


ffi.string(user_profile_name)
int(user_profile_name_bs)

print('Grating Position', analysis_information.GratingPositionMm)
print('wavelengthNm', analysis_information.wavelengthNm)
print('RemoveBackgroundImage', analysis_information.RemoveBackgroundImage)
print('Analysis information PhaseSize_Height:')
print(int.from_bytes(ffi.buffer(analysis_information)[21:25], 'little'))
print('Analysis information PhaseSize_width:')
print(int.from_bytes(ffi.buffer(analysis_information)[17:21], 'little'))

print('FrameRate', camera_information.FrameRate)
print('TriggerMode', camera_information.TriggerMode)
print('gain', camera_information.Gain)
print('Exp Time', camera_information.ExposureTime)
print('Pixel Size', camera_information.PixelSizeM)
print('NumberOfCameraRecorded', camera_information.NumberOfCameraRecorded)

nr_of_attributes = ffi.new('long *')
SDK.Camera_GetNumberOfAttribute(session_id, nr_of_attributes, error_code)

print('nr of attributes is: ')
print(nr_of_attributes[0])

attribute_id = ffi.new('unsigned short int[]', nr_of_attributes[0])
attribute_id_bs = ffi.cast('long', nr_of_attributes[0])
attribute_name = ffi.new('char[]', buffer_size)
attribute_name_bs = ffi.cast('long', buffer_size)
attribute_min = ffi.new('long[]', nr_of_attributes[0])
attribute_min_bs = ffi.cast('long', nr_of_attributes[0] * 4)
attribute_max = ffi.new('long[]', nr_of_attributes[0])
attribute_max_bs = ffi.cast('long', nr_of_attributes[0] * 4)

print('Getting camera attributes')
SDK.Camera_GetAttributeList(session_id,
                            attribute_id,
                            attribute_id_bs,
                            attribute_name,
                            attribute_name_bs,
                            attribute_min,
                            attribute_min_bs,
                            attribute_max,
                            attribute_max_bs,
                            error_code)
print(error_code[0])

print('Attributes ids:')
print(ffi.unpack(attribute_id, nr_of_attributes[0]))
print('Names:')
print(ffi.string(attribute_name))
print('Min values:')
print(ffi.unpack(attribute_min, nr_of_attributes[0]))
print('Max values:')
print(ffi.unpack(attribute_max, nr_of_attributes[0]))

phase = ffi.new('float[]', 4096)
phase_bs = ffi.cast('long', 16384)
intensity = ffi.new('float[]', 4096)
intensity_bs = ffi.cast('long', 16384)

image = ffi.new("short int[307200]")
image_bs = ffi.cast("long", 307200)

print('Starting Live mode...')
SDK.StartLiveMode(session_id, error_code)
print(error_code[0])

print('Grabbing image...')
SDK.GrabImage(session_id, image, image_bs, camera_array_size, error_code)
print(error_code[0])

print('Part of the image')
print([x for x in image[0:20]])

print('Grabbing Live mode...')
SDK.GrabLiveMode(session_id, phase, phase_bs, intensity, intensity_bs, tilt_information, analysis_array_size, error_code)
print(error_code[0])
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
