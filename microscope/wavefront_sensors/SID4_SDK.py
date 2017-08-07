#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2017 Julio Mateos (julio.mateos-langerak@igh.cnrs.fr)
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
"""Phasics SID4 SDK python interface

This module provides a python interface to Phasics SDK to control
SID4 waveform sensors.
"""

import ctypes
from ctypes import POINTER, Structure, c_int, c_uint8, c_ushort, c_long, c_ulong, c_float, c_char, c_ubyte, c_uint, c_double, c_void_p

# Type definitions
LVBoolean = c_uint8 # 8-bit integer. 0 if False, 1 if True
SDK_Reference = c_int # 32-bit integer used to define a unique reference ID
SDK_WC = ctypes.c_wchar
SDK_CHAR = c_char
SDK_INT = c_int
SDK_LONG = c_long
SDK_DOUBLE = c_double
SDK_ULONG = c_ulong
SDK_FLOAT = c_float
SDK_UCHAR = c_ubyte
SDK_USHORT = c_ushort

class SDK_Reference(Structure):
    _fields_ = [('SDK_Reference', SDK_INT)]

class ArraySize(Structure):
    """This structure contains information about 2D array size:
    it gives the size of each dimension.
    Note: this structure is used to initialize the size of all the array
    containing the phase map information.
    So this structure is often used in the SDK SID4 and particularly in the
    Interferogram Analysis Function.

    :parameter nRow: Long integer that specifies the size of the first dimension,
    in other words it gives the rows number
    :parameter nCol: Long integer that specifies the size of the second dimension,
    in other words it gives the columns number
    """
    _fields_ = [('nRow', SDK_LONG),
                ('nCol', SDK_LONG)]

class AnalysisInfo(Structure):
    """This structure type contains information on the user profile
    currently in memory, such as its location on the hard drive,
    the current reference file, grating position (in mm)
    and the wavelength (in nm) used  as the unit for the phase values.
    The PhaseSize variable is very important since it allows sizing
    the phase and intensity maps used as inputs for the interferogram
    analysis functions.

    This structure is filled by the GetUserProfile function

    :parameter GratingPositionMm: Double precision float giving
    the grating position in millimeters.
    This distance corresponds to the one between the diffraction grating and the CCD sensor of the SID4
    :parameter wavelengthNm: Double precision float that gives the wevelength currently used in nanometer
    :parameter RemoveBackgroundImage: Boolean specifying if the background image is removed or not:
    - false (value 0): the image background is not removed
    - true (value 1): the image background is removed
    :parameter PhaseSize_width: Long integer specifying the first dimension size of the phase map.
    In other words it gives the number of lines
    :parameter PhaseSize_Height: Long integer specifying the second dimension size of the phase map.
    In other words it gives the number of columns
    """
    _fields_ = [('GratingPositionMm', SDK_DOUBLE),
                ('wavelengthNm', SDK_DOUBLE),
                ('RemoveBackgroundImage', LVBoolean),
                ('PhaseSize_width', SDK_LONG),
                ('PhaseSize_Height', SDK_LONG)]

class CameraInfo(Structure):
    """This structure type contains information on the camera settings
    associated with the user profile currently in memory.

    The camera parameters like the frame rate are indicates
    in order to remain the SDK compatible with older Teli cameras.
    If your camera are not a Teli one the frame rate, trigger mode,
    gain, exposure time parameter should not be taken into account.
    On the other side the parameters pixel size and number of camera
    recorded are always correct.

    Regardless of the type of camera you use, the parameters
    of this one can be recovered through function Camera_GetAttribute.

    This structure is filled by the GetUserProfile function
    :parameter FrameRate: The following values are to be taken into account only if your camera is a TELI:
    Camera frame rate: 0 = "3.75hz",  1 = "7.5hz", 2 = "15hz", 3 = "30hz", 4 = "60hz"
    :parameter TriggerMode: The following values are to be taken into account only if your camera is a TELI:
    Camera trigger mode: 0 = continous mode; 1 = trigger mode0; 2 = trigger mode1.
    :parameter Gain: The following values are to be taken into account only if your camera is a TELI:
    Camera gain. The range is [40;208]
    :parameter ExposureTime: The following values are to be taken into account only if your camera is a TELI:
    Camera exposure time: 0 = "1/60s", 1 = "1/200s", 2 = "1/500s", 3 = "1/1000s", 4 = "1/2000s", 5 = "1/4000s",
    6 = "1/8000s", 7 = "1/20000s".
    :parameter PixelSizeM: Size of the camera pixel (µm)
    :parameter NumberOfCameraRecorded: Number of recorded camera in the SID4 SDK software
    """
    _fields_ = [('FrameRate', SDK_LONG),
                ('TriggerMode', SDK_ULONG),
                ('Gain', SDK_LONG),
                ('ExposureTime', SDK_ULONG),
                ('PixelSizeM', SDK_FLOAT),
                ('NumberOfCameraRecorded', SDK_UCHAR)]

class ZernikeInformation(Structure):
    """This structure type contains information on the projection base
    and the number of polynomials.

    The base can be either Zernike or Legendre.
    The number of polynomials depends on the value of the highest polynomial order

    :parameter Base: Unsigned short int that specifies the polynomials base (Zernike=0 and Legendre=1)
    :parameter Polynomials: Long integer that specifies the number of polynomials
    """
    _fields_ = [('Base', SDK_USHORT),
                ('Polynomials', SDK_LONG)]

class ZernikeParam(Structure):
    """This structure type contains information useful for Zernike calculation.
    It defines the size of the intensity map and the size of the mask
    the program will use to compute the Zernike coefficients.
    It also defines the projection base (Zernike or Legendre).

    :parameter ImageRowSize: Unsigned long integer that specifies the number of rows of the intensity map
    :parameter ImageColSize: Unsigned long integer that specifies the number of columns of the intensity map
    :parameter MaskRowSize: Unsigned long integer that specifies the number of rows of the mask map
    :parameter MaskColSize: Unsigned long integer that specifies the number of columns of the mask map
    :parameter Base: Unsigned short int that specifies the polynomials base (Zernike=0 and Legendre=1)
    """
    _fields_ = [('ImageRowSize', SDK_ULONG),
                ('ImageColSize', SDK_ULONG),
                ('MaskRowSize', SDK_ULONG),
                ('MaskColSize', SDK_ULONG),
                ('Base', SDK_USHORT)]

class TiltInfo(Structure):
    """This structure type contains Tilt information (X and Y tilts)
    removed from the output phase

    :parameter XTilt: X tilt removed from output phase given in milliradian
    :parameter YTilt: Y tilt removed from output phase given in milliradian
    """
    _fields_ = [('XTilt', SDK_FLOAT),
                ('YTilt', SDK_FLOAT)]

# Import the dll's

_stdcall_libraries = {}
_stdcall_libraries['SID4_SDK'] = ctypes.WinDLL('SID4_SDK')

# Get error codes

NO_ERROR = 0
# TODO: Get error codes from SID4_SDK_Constants.h through a subclass of Exception

class DeviceError(Exception):
    pass

### Functions ###
STRING = POINTER(SDK_WC)

# classes so that we do some magic and automatically add byrefs etc ... can classify outputs
class _meta(object):
    pass

class OUTPUT(_meta):
    def __init__(self, val):
        self.type = val
        self.val = POINTER(val)

    def getVar(self, bufLen=0):
        v = self.type()
        return v, ctypes.byref(v)


class _OUTSTRING(OUTPUT):
    def __init__(self):
        self.val = STRING

    def getVar(self, bufLen=0):
        v = ctypes.create_unicode_buffer(bufLen)
        return v, v

OUTSTRING = _OUTSTRING()

class _OUTSTRLEN(_meta):
    def __init__(self):
        self.val = c_int

OUTSTRLEN = _OUTSTRLEN()

def stripMeta(val):
    if isinstance(val, _meta):
        return val.val
    else:
        return val

class dllFunction(object):
    def __init__(self, name, args=[], argnames=[], lib='SID4_SDK'):
        self.f = getattr(_stdcall_libraries[lib], name)
        self.f.restype = c_int
        self.f.argtypes = [stripMeta(a) for a in args]

        self.fargs = args
        self.fargnames = argnames
        self.name = name

        self.inp = [not isinstance(a, OUTPUT) for a in args]
        self.in_args = [a for a in args if not isinstance(a, OUTPUT)]
        self.out_args = [a for a in args if isinstance(a, OUTPUT)]

        self.buf_size_arg_pos = -1
        for i in range(len(self.in_args)):
            if isinstance(self.in_args[i], _OUTSTRLEN):
                self.buf_size_arg_pos = i

        ds = name + '\n\nArguments:\n===========\n'
        for i in range(len(args)):
            an = ''
            if i < len(argnames):
                an = argnames[i]
            ds += '\t%s\t%s\n' % (args[i], an)

        self.f.__doc__ = ds

    def __call__(self, *args):
        ars = []
        i = 0
        ret = []

        if self.buf_size_arg_pos >= 0:
            bs = args[self.buf_size_arg_pos]
        else:
            bs = 255

        for j in range(len(self.inp)):
            if self.inp[j]:  # an input
                ars.append(args[i])
                i += 1
            else:  # an output
                r, ar = self.fargs[j].getVar(bs)
                ars.append(ar)
                ret.append(r)
                # print r, r._type_

        # print ars
        res = self.f(*ars)
        # print res

        if not res == NO_ERROR:
            raise DeviceError(self.name, res)

        if len(ret) == 0:
            return None
        if len(ret) == 1:
            return ret[0]
        else:
            return ret

def dllFunc(name, args=[], argnames=[], lib='SID4_SDK'):
    f = dllFunction(name, args, argnames, lib)
    globals()[name] = f

# Configuration Functions

dllFunc('OpenSID4',
        [SDK_CHAR, OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['UserProfileLocation[]', '*SessionID', '*ErrorCode'])
dllFunc('CloseSID4',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SessionID', '*ErrorCode'])
dllFunc('GetUserProfile',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_LONG, SDK_CHAR, SDK_LONG,
         SDK_CHAR, SDK_LONG, SDK_CHAR, SDK_LONG,
         SDK_CHAR, SDK_LONG, SDK_CHAR, SDK_LONG, OUTPUT(AnalysisInfo),
         OUTPUT(CameraInfo), SDK_CHAR, SDK_LONG, OUTPUT(ArraySize), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'UserProfile_Name[]', 'uspName_bufSize', 'UserProfile_File[]', 'uspFile_bufSize',
         'UserProfile_Description[]', 'uspDesc_bufSize', 'UsrP_LatestReference[]', 'uspLastRef_bufSize',
         'UserProfileDirectory[]', 'uspDir_bufSize', 'SDKVersion[]', 'version_bufSize', '*AnalysisInformation',
         '*CameraInformation', 'SNPhasics[]', 'SNPhasics_bufSize', '*AnalysisArraySize', '*ErrorCode'])
dllFunc('ChangeReference',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_USHORT, SDK_CHAR, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'ReferencePath[]', 'ReferenceSource', 'ArchivedPath[]', 'ArchivedPath_bufSize', '*ErrorCode'])
dllFunc('ChangeMask',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_LONG, SDK_LONG, OUTPUT(SDK_USHORT), SDK_ULONG, SDK_LONG, SDK_LONG, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'MaskFile[]', 'ROI_GlobalRectangle[]', 'globalRect_bufSize', '*ROI_NbOfContours',
         'ROI_Contours_info[]', 'contoursInfo_bufSize', 'ROI_Contours_coordinates[]', 'contoursCoord_bufSize',
         '*ErrorCode'])
dllFunc('SetBackground',
        [OUTPUT(SDK_Reference), SDK_USHORT, SDK_CHAR, SDK_CHAR, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'Source', 'BackgroundFile[]', 'UpdatedBackgroundImageFile[]', 'updatedImageFile_bufSize',
         '*ErrorCode'])
dllFunc('LoadMaskDescriptorInfo',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_LONG, SDK_LONG, OUTPUT(SDK_USHORT), SDK_ULONG, SDK_LONG, SDK_LONG, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'MaskFile[]', 'ROI_GlobalRectangle[]', 'globalRect_bufSize', '*ROI_NbOfContours',
         'ROI_Contours_info[]', 'contoursInfo_bufSize', 'ROI_contours_coordinates[]', 'contoursCoord_bufSize',
         '*ErrorCode'])
dllFunc('LoadMaskDescriptor',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_LONG, SDK_LONG, OUTPUT(SDK_USHORT), SDK_ULONG, SDK_LONG, SDK_LONG, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'MaskFile[]', 'ROI_GlobalRectangle[]', 'globalRect_bufSize', '*ROI_NbOfContours',
         'ROI_Contours_info[]', 'contoursInfo_bufSize', 'ROI_contours_coordinates[]', 'contoursCoord_bufSize',
         '*ErrorCode'])
dllFunc('ModifyUserProfile',
        [OUTPUT(SDK_Reference), OUTPUT(AnalysisInfo), SDK_USHORT, SDK_CHAR, SDK_CHAR, OUTPUT(LVBoolean), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*AnalysisInformation', 'ReferenceSource', 'ReferencePath[]', 'UserProfile_Decription[]',
         '*ReferenceChanged', '*ErrorCode'])
dllFunc('NewUserProfile',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_CHAR, SDK_CHAR, SDK_CHAR, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'CameraSNPhasics[]', 'ProfileName[]', 'UserProfileDirectory[]', 'ProfilePathFileOut[]',
         'pathFileOut_bufSize', '*ErrorCode'])
dllFunc('SaveMaskDescriptor',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_LONG, SDK_LONG, SDK_USHORT, SDK_ULONG, SDK_LONG, SDK_LONG, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'MaskFile[]', 'ROI_GlobalRectangle[]', 'globalRect_bufSize', 'ROI_NbOfContours',
         'ROI_Contours_info[]', 'contoursInfo_bufSize', 'ROI_contours_coordinates[]', 'contoursCoord_bufSize',
         '*ErrorCode'])
dllFunc('SaveCurrentUserProfile',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])

# Camera Control Functions

dllFunc('CameraList',
        [OUTPUT(SDK_Reference), SDK_CHAR, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'CameraList_SNPhasics[]', 'camList_bufSize', '*ErrorCode'])
# Obsolete
# dllFunc('CameraSetup',
#         [OUTPUT(SDK_Reference), SDK_USHORT, SDK_USHORT, OUTPUT(SDK_LONG)],
#         ['*SDKSessionID', 'CameraParameter', 'Value', '*ErrorCode'])
dllFunc('CameraInit',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])
dllFunc('CameraStart',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])
dllFunc('CameraStop',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])
dllFunc('CameraClose',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])
dllFunc('StartLiveMode',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])
dllFunc('StopLiveMode',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*ErrorCode'])
dllFunc('Camera_GetAttribute',
        [OUTPUT(SDK_Reference), SDK_USHORT, OUTPUT(SDK_DOUBLE), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'AttributeID', '*AttributeValueOut', '*ErrorCode'])
dllFunc('Camera_GetAttributeList',
        [OUTPUT(SDK_Reference), SDK_USHORT, SDK_LONG, SDK_CHAR, SDK_LONG,
         SDK_LONG, SDK_LONG, SDK_LONG, SDK_LONG, OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'AttributeID[]', 'attribID_bufSize', 'AttributeName_SeparatedByTab[]', 'attribName_bufSize',
         'AttributeGmin[]', 'attribGmin_bufSize', 'AttributeGmax[]', 'attribGmax_bufSize', '*ErrorCode'])
dllFunc('Camera_SetAttribute',
        [OUTPUT(SDK_Reference), SDK_USHORT, OUTPUT(SDK_DOUBLE), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'AttributeID', '*AttributeValue', '*ErrorCode'])
dllFunc('Camera_GetNumberOfAttribute',
        [OUTPUT(SDK_Reference), OUTPUT(SDK_LONG), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', '*NumberOfAttribute', '*ErrorCode'])
dllFunc('Camera_ConvertExposureMs',
        [OUTPUT(SDK_Reference), SDK_DOUBLE, OUTPUT(SDK_DOUBLE), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'ExposureRawValueIn', '*ExposureValueMsOut', '*ErrorCode'])

# Inteferogram Analysis functions

dllFunc('ArrayAnalysis',
        [OUTPUT(SDK_Reference), SDK_INT, SDK_LONG, SDK_FLOAT, SDK_LONG,
         SDK_FLOAT, SDK_LONG, OUTPUT(TiltInfo), OUTPUT(ArraySize), OUTPUT(ArraySize), OUTPUT(SDK_LONG)],
        ['*SDKSessionID', 'InterferogramInArrayI16[]', 'Interfero_bufSize', 'Intensity[]', 'Intensity_bufSize',
         'Phase[]', 'Phase_bufSize', '*TiltInformation', '*AnalysisArraySize', '*ImageCameraSize', '*ErrorCode'])