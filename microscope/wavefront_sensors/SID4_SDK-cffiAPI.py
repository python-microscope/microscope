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


# We import the headers from a file in order to avoid copyright issues
header_path = 'C:\Program Files (x86)\SID4_SDK\DLL SDK\Headers\SID4_SDK.h'
dll_path = 'C:\Program Files (x86)\SID4_SDK\DLL SDK\BIN\SID4_SDK.dll'
cdef_from_file = ''

try:
    with open(header_path, 'r') as SDK_header:
        cdef_from_file = SDK_header.read()
except FileNotFoundError:
    print('Unable to find "%s" header file.' % header_path)
    exit(1)
except IOError:
    print('Unable to open "%s"' % header_path)
    exit(2)
finally:
    if cdef_from_file == '' or None:
        print('File "%s" is empty' % header_path)
        exit(3)

ffibuilder = FFI()

print(cdef_from_file[0:100])

ffibuilder.set_source("_SDK_SID4",
                      r""" // passed to the real C compiler
                           #include "C:\Program Files (x86)\SID4_SDK\DLL SDK\Headers\SID4_SDK.h"
                       """,
                      libraries=[])  # or a list of libraries to link with
# libraries=[dll_path])

# '''
# Open VS prompt
# cd C:\Users\omxt\PycharmProjects\microscope\microscope\wavefront_sensors
# cl.exe /c /nologo /Ox /W3 /GL /DNDEBUG /MD^
#  -Ic:\Users\omxt\Applications\WinPython-32bit-3.6.1.0Qt5\python-3.6.1\include^
#  -Ic:\Users\omxt\Applications\WinPython-32bit-3.6.1.0Qt5\python-3.6.1\include^
#  "-IC:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC\14.11.25503\ATLMFC\include"^
#  "-IC:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC\14.11.25503\include"^
#  "-IC:\Program Files (x86)\Windows Kits\NETFXSDK\4.6.1\include\um"^
#  "-IC:\Program Files (x86)\Windows Kits\10\include\10.0.15063.0\ucrt"^
#  "-IC:\Program Files (x86)\Windows Kits\10\include\10.0.15063.0\shared"^
#  "-IC:\Program Files (x86)\Windows Kits\10\include\10.0.15063.0\um"^
#  "-IC:\Program Files (x86)\Windows Kits\10\include\10.0.15063.0\winrt"^
#  "-IC:\Program Files (x86)\SID4_SDK\DLL SDK\Headers"^
#  /Tc_SDK_SID4.c /Fo.\Release\_SDK_SID4.obj
#  '''


# ffibuilder.cdef(cdef_from_file)
ffibuilder.cdef('''
#pragma pack(push)
#pragma pack(1)

typedef unsigned char LVBoolean;

typedef int SDK_Reference;

//****************************************************************//
// Definitions of structures used in the SID4_SDK functions       //
//****************************************************************//

// Tilt Information
typedef struct {
	float XTilt;
	float YTilt;
	} TiltInfo;

// Size Information on the 2D arrays given as input parameters
typedef struct {
	long nRow;
	long nCol;
	} ArraySize;


// Analysis Information, to be used with GetUserProfile
typedef struct {
	double GratingPositionMm;
	double wavelengthNm;
	LVBoolean RemoveBackgroundImage;
	long PhaseSize_width;
	long PhaseSize_Height;
	} AnalysisInfo;

// Camera Information, to be used with GetUserProfile
typedef struct {
	long FrameRate;
	unsigned long TriggerMode;
	long Gain;
	unsigned long ExposureTime;
	float PixelSizeM;
	unsigned char NumberOfCameraRecorded;
	} CameraInfo;

//**************************************************************//
// SID4_SDK Basic functions                                        //
//**************************************************************//

// Configuration functions
void __cdecl OpenSID4(char UserProfileLocation[], SDK_Reference *SessionID,
	long *ErrorCode);

void __cdecl CloseSID4(SDK_Reference *SessionID, long *ErrorCode);

void __cdecl GetUserProfile(SDK_Reference *SDKSessionID, char UserProfile_Name[],
	long uspName_bufSize, char UserProfile_File[], long uspFile_bufSize,
	char UserProfile_Description[], long uspDesc_bufSize,
	char UsrP_LatestReference[], long uspLastRef_bufSize,
	char UserProfile_Directory[], long uspDir_bufSize, char SDKVersion[],
	long version_bufSize, AnalysisInfo *AnalysisInformation, CameraInfo *CameraInformation,
	char SNPhasics[], long SNPhasics_bufSize, ArraySize *AnalysisArraySize,
	long *ErrorCode);

void __cdecl ChangeReference(SDK_Reference *SDKSessionID, char ReferencePath[],
	unsigned short int ReferenceSource, char ArchivedPath[], long ArchivedPath_bufSize,
	long *ErrorCode);

	void __cdecl SetBackground(SDK_Reference *SDKSessionID, unsigned short int Source,
	char BackgroundFile[], char UpdatedBackgoundImageFile[],
	long updatedImageFile_bufSize, long *ErrorCode);

void __cdecl ChangeMask(SDK_Reference *SDKSessionID, char MaskFile[],
	long ROI_GlobalRectangle[], long globalRect_bufSize,
	unsigned short int *ROI_NbOfContours, unsigned long ROI_Contours_info[],
	long contoursInfo_bufSize, long ROI_Contours_coordinates[],
	long contoursCoord_bufSize, long *ErrorCode);

void __cdecl LoadMaskDescriptorInfo(SDK_Reference *SDKSessionID, char MaskFile[],
	long ROI_GlobalRectangle[], long globalRect_bufSize,
	unsigned short int *ROI_NbOfContours, unsigned long ROI_Contours_info[],
	long contoursInfo_bufSize, long ROI_Contours_coordinates[],
	long contoursCoord_bufSize, long *ErrorCode);

void __cdecl LoadMaskDescriptor(SDK_Reference *SDKSessionID, char MaskFile[],
	long ROI_GlobalRectangle[], long globalRect_bufSize,
	unsigned short int *ROI_NbOfContours, unsigned long ROI_Contours_info[],
	long contoursInfo_bufSize, long ROI_Contours_coordinates[],
	long contoursCoord_bufSize, long *ErrorCode);

void __cdecl ModifyUserProfile(SDK_Reference *SDKSessionID,
	AnalysisInfo *AnalysisInformation, unsigned short int ReferenceSource, char ReferencePath[],
	char UserProfile_Description[], LVBoolean *ReferenceChanged,
	long *ErrorCode);

void __cdecl NewUserProfile(SDK_Reference *SDKSessionID, char CameraSNPhasics[],
	char ProfileName[], char UserProfileDirectory[], char ProfilePathFileOut[],
	long pathFileOut_bufSize, long *ErrorCode);

void __cdecl SaveCurrentUserProfile(SDK_Reference *SDKSessionID,
	long *ErrorCode);

void __cdecl SaveMaskDescriptor(SDK_Reference *SDKSessionID, char MaskFile[],
	long ROI_GlobalRectangle[], long globalRect_bufSize,
	unsigned short int ROI_NbOfContours, unsigned long ROI_Contours_info[],
	long contoursInfo_bufSize, long ROI_Contours_coordinates[],
	long contoursCoord_bufSize, long *ErrorCode);

// Camera control functions
void __cdecl StartLiveMode(SDK_Reference *SDKSessionID, long *ErrorCode);

void __cdecl StopLiveMode(SDK_Reference *SDKSessionID, long *ErrorCodeID);

void __cdecl CameraInit(SDK_Reference *SDKSessionID, long *ErrorCode);

void __cdecl CameraStart(SDK_Reference *SDKSessionID, long *ErrorCode);

void __cdecl CameraStop(SDK_Reference *SDKSessionID, long *ErrorCode);

void __cdecl CameraClose(SDK_Reference *SDKSessionID, long *ErrorCode);

void __cdecl CameraList(SDK_Reference *SDKSessionID, char CameraList_SNPhasics[],
	long camList_bufSize, long *ErrorCode);

void __cdecl CameraSetup(SDK_Reference *SDKSessionID, unsigned short int CameraParameter,
	unsigned long Value, long *ErrorCode);

void __cdecl Camera_ConvertExposureMs(SDK_Reference *SDKSessionID,
	double ExposureRawValueIn, double *ExposureValueMsOut, long *ErrorCode);
void __cdecl Camera_GetNumberOfAttribute(SDK_Reference *SDKSessionID,
	long *NumberOfAttribute, long *ErrorCode);

void __cdecl Camera_GetAttribute(SDK_Reference *SDKSessionID,
	unsigned short int AttributeID, double *AttributeValueOut, long *ErrorCode);
void __cdecl Camera_SetAttribute(SDK_Reference *SDKSessionID,
	unsigned short int AttributeID, double *AttributeValue, long *ErrorCode);

void __cdecl Camera_GetAttributeList(SDK_Reference *SDKSessionID,
	unsigned short int AttributeID[], long attribID_bufSize,
	char AttributeName_SeparatedByTab[], long attribName_bufSize,
	long AttributeGmin[], long attribGmin_bufSize, long AttributeGmax[],
	long attribGmax_bufSize, long *ErrorCode);

// Interferogram analysis functions
void __cdecl ArrayAnalysis(SDK_Reference *SDKSessionID,
	short int InterferogramInArrayI16[], long Interfero_bufSize,
	float Intensity[], long Intensity_bufSize, float Phase[],
	long Phase_bufSize, TiltInfo *TiltInformation, ArraySize *AnalysisArraySize,
	ArraySize *ImageCameraSize, long *ErrorCode);

void __cdecl FileAnalysis(SDK_Reference *SDKSessionID, ArraySize *AnalysisArraySize,
	char InterferogramFile[], float Intensity[], long Intensity_bufSize,
	float Phase[], long Phase_bufSize, TiltInfo *TiltInformation,
	long *ErrorCode);

void __cdecl GrabLiveMode(SDK_Reference *SDKSessionID, float Phase[],
	long Phase_bufSize, float Intensity[], long Intensity_bufSize,
	TiltInfo *TiltInformation, ArraySize *AnalysisArraySize, long *ErrorCode);

void __cdecl GrabImage(SDK_Reference *SDKSessionID, short int Image[],
	long Image_bufSize, ArraySize *ImageCameraSize, long *ErrorCode);

void __cdecl Snap(SDK_Reference *SDKSessionID, float Phase[],
	long Phase_bufSize, float Intensity[], long Intensity_bufSize,
	TiltInfo *TiltInformation, long *ErrorCode);

void __cdecl GrabToFile(SDK_Reference *SDKSessionID, unsigned long PaletteNumber,
	char InterferogramFile[], LVBoolean *CheckOverWrite, long *ErrorCode);

void __cdecl GetPhaseGradients(SDK_Reference *SDKSessionID,
	ArraySize *AnalysisArraySize, float GradientX[], long GradX_bufSize,
	float GradientY[], long GradY_bufSize, long *ErrorCode);

void __cdecl SetIntegrationParam(SDK_Reference *SDKSessionID,
	unsigned char Adv_Activation, unsigned short int Adv_Niter, float Adv_MSE_Threshold,
	long *ErrorCode);

void __cdecl GetQualityMap(SDK_Reference *SDKSessionID, ArraySize *AnalysisArraySize,
	float QualityMap[], long qualityMap_bufSize, long *ErrorCode);

void __cdecl GetIntegrationParam(SDK_Reference *SDKSessionID,
	unsigned char *Adv_Activation, unsigned short int *Adv_Niter, float *Adv_MSE_Threshold,
	long *ErrorCode);

void __cdecl SetUnwrapParam(SDK_Reference *SDKSessionID,
	unsigned short int UnwrappingAlgorithm, unsigned char UnwrappingOptions[],
	long unwrapOptions_bufSize, long *ErrorCode);

void __cdecl GetUnwrapParam(SDK_Reference *SDKSessionID,
	unsigned short int *UnwrappingAlgoritm, unsigned char UnwrappingOptions[],
	long unwrapOptions_bufSize, long *ErrorCode);

void __cdecl getIntegrationParamOut(SDK_Reference *SDKSessionID,
	LVBoolean *Adv_Activation, unsigned short int *Adv_Niter, float *Adv_MSE_Threshold,
	long *ErrorCode);

void __cdecl ADVTR_GetAnalysisArraySize(SDK_Reference *SDKSessionID,
	double TR_AnalyseIn, ArraySize *AnalysisArraySize, long *ErrorCode);

void __cdecl ADVTR_ComputeAnalysisTr(SDK_Reference *SDKSessionID, ArraySize *ImageSize,
	short int InterferogramI16[], long interfero_bufSize, double *TR_AnalyseOut,
	long *ErrorCode);

void __cdecl ADVTR_ArrayAnalysisTr(SDK_Reference *SDKSessionID, ArraySize *ImageSize,
	short int InterferogramI16[], long interfero_bufSize, double TR_AnalyseIn,
	ArraySize *AnalysisArraySize, float Phase[], long phase_bufSize,
	float Intensity[], long intensity_bufSize, TiltInfo *TiltInformation,
	long *ErrorCode);

void __cdecl GetImageInfo(SDK_Reference *SDKSessionID, char InterferogramFile[],
	ArraySize *ImageSize, long *ErrorCode);


// Input-Output functions
void __cdecl LoadInterferogram(SDK_Reference *SDKSessionID,
	char InterferogramFile[], ArraySize *ImageSize, short int InterferogramI16[],
	long interfero_bufSize, long *ErrorCode);

void __cdecl LoadMeasurementInfo(SDK_Reference *SDKSessionID, char PhaseFile[],
	ArraySize *AnalysisArraySize, long *ErrorCode);

void __cdecl LoadMeasurement(SDK_Reference *SDKSessionID, char PhaseFile[],
	ArraySize *AnalysisArraySize, float Phase[], long Phase_bufSize,
	float Intensity[], long Intensity_bufSize, long *ErrorCode);

void __cdecl SaveLastMeasurement(SDK_Reference *SDKSessionID, char GenericPath[],
	unsigned short int MeasurementList[], long measurementList_bufSize,
	char MeasurementFilesOut[], long filesOut_bufSize, long *ErrorCode);

void __cdecl SaveMeasurement(SDK_Reference *SDKSessionID, char GenericPath[],
	ArraySize *AnalysisArraySize, float Phase[], long Phase_bufSize,
	float Intensity[], long Intensity_bufSize, char PhaseFileOut[],
	long phaseFileOut_bufSize, char IntensityFileOut[],
	long intensityFileOut_bufSize, long *ErrorCode);



long __cdecl LVDLLStatus(char *errStr, int errStrLen, void *module);

#pragma pack(pop)
''')

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)