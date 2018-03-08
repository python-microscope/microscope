/*
	© Copyright 2008 by PHASICS.
	All rights reserved.

	@File:	SID4_SDK_SaveMeasurement_Example.cpp
	@Description: This example shows how to save the Phase and Intensity maps.
	
	This example involves 5 SID4 SDK's functions:

	"OpenSID4" loads the configuration file specified by "userProfile_File" in memory. 
	It returns a unique reference ID "SessionID" that should be used as an input
	for all other SID4 SDK functions.

	"GetUserProfile" outputs the parameters currently used to analyse analyse interferograms
	and the camera settings.

	FileAnalysis analyses the interferogram. It ouputs a Phase and Intensity map, Tilt information
	(X and Y tilts) removed from the ouput phase.

	"SaveMeasurement" saves the Phase and Intensity maps (2D single precision real array).
	The filenames used are derived from the generic file name. The function adds a prefix "PHA"
	for the phase file and a "INT" prfix for the intensity file. The arrays are saved in TIFF format.
	The normalization information for the TIFF files are saved in a companion file, which prefix is "ACC".

	CloseSID4 closes the SID4 session. It releases memory devoted to the session.
*/


#include <stdio.h>
#include <stdlib.h>				
#include <malloc.h>				// for memory allocation
#include "SID4_SDk.h"
#include "SID4_SDk_Constants.h"

const int bufSize=1024;


void main(void)
{
	char userProfile_File[]="C:\\Program Files\\SID4_SDK\\Examples\\User Profile\\UserProfileExample.txt";
	char inteferogram_File[]="C:\\Program Files\\SID4_SDK\\Examples\\Interferograms\\Interferogram.tif";
	char GenericPath[]="C:\\Program Files\\SID4_SDK\\Examples\\Interferograms\\Result\\Interfo";	
	SDK_Reference SessionID=0;
	int nrow, ncol;
	long Error=0;
	char UserProfile_Name[bufSize]="";
	long uspName_bufSize = bufSize;
	char UserProfile_File[bufSize]="";
	long uspFile_bufSize = bufSize;
	char UserProfile_Description[bufSize]="";
	long uspDesc_bufSize = bufSize;
	char UsrP_LastReference[bufSize]="";
	long uspLastRef_bufSize = bufSize;
	char UserProfile_Directory[bufSize]="";
	long uspDir_bufSize = bufSize;
	char SDKVersion[bufSize]="";
	long version_bufSize = bufSize;
	AnalysisInfo AnalysisInformation;
	CameraInfo CameraInformation;
	char SNPhasics[bufSize]="";
	long SNPhasics_bufSize = bufSize;
	ArraySize ImageSize;

	//  Open SID4 Session
	OpenSID4(userProfile_File,&SessionID,&Error);
	if(!Error)
	{	printf ("************************ SID4 Session correctly opened **********************\n");
		printf ("SessionID=%d; Error=%d",SessionID,Error);
	}
	else{
		printf ("\nThe error %d occured in the OpenSID4 function!\n\n",Error);
		exit(1);
	}

	// Reading of parameters currently used for interferogram analysis 
	GetUserProfile(&SessionID, UserProfile_Name, uspName_bufSize, UserProfile_File, uspFile_bufSize, 
		UserProfile_Description, uspDesc_bufSize, UsrP_LastReference, uspLastRef_bufSize, 
		UserProfile_Directory, uspDir_bufSize,SDKVersion, version_bufSize, &AnalysisInformation, 
		&CameraInformation, SNPhasics, SNPhasics_bufSize, &ImageSize, &Error);
	
	// Array dimension for Phase and Intensity
	nrow = AnalysisInformation.PhaseSize_Height;    
	ncol = AnalysisInformation.PhaseSize_width;

	//// memory allocation for Phase and Intensity before calling FileAnalysis
	TiltInfo TiltInformation;
	long Intensity_bufSize = nrow*ncol;
	long Phase_bufSize = nrow*ncol;
	ArraySize AnalysisArraySize;

	AnalysisArraySize.height=nrow;
	AnalysisArraySize.width=ncol;

	float *Intensity = (float*)malloc(sizeof(float)* Intensity_bufSize);
	float *Phase = (float*)malloc(sizeof(float)* Phase_bufSize);


	// Interferogram Analysis. We get in output Phase and Intensity map, tiltInformation
	FileAnalysis(&SessionID, &AnalysisArraySize, inteferogram_File, Intensity, Intensity_bufSize, 
				 Phase, Phase_bufSize, &TiltInformation, &Error);
	if(!Error)
	{	printf ("\nXtilt=%f; Ytilt=%f\n",TiltInformation.XTilt,TiltInformation.YTilt);
	}
	else{
		printf ("\nThe error %d occured in the FileAnalysis function!\n\n",Error);
		exit(1);
	}
	
	// Save the Phase and Intensity maps. The function returns the Intensity and Phase path files.
	char PhaseFileOut[bufSize]="";
	long phaseFileOut_bufSize = bufSize;
	char IntensityFileOut[bufSize]="";
	long intensityFileOut_bufSize = bufSize;

	SaveMeasurement(&SessionID, GenericPath, &AnalysisArraySize, Phase, Phase_bufSize, Intensity, 
				Intensity_bufSize, PhaseFileOut, phaseFileOut_bufSize, 
				IntensityFileOut, intensityFileOut_bufSize, &Error);
	if(!Error)
	{	printf ("\nThe intensity map has been saved in the following file :\n");
		printf ("\n%s\n", IntensityFileOut);
		printf ("\nThe phase map has been saved in the following file :\n");
		printf ("\n%s\n", PhaseFileOut);
	}
	else{
		printf ("\nThe error %d occured in the SaveMeasurement function!\n\n",Error);
		exit(1);
	}


	// Close the SID4 session
	CloseSID4(&SessionID,&Error);

	// Memory release
	free(Intensity);
	free(Phase);

}
