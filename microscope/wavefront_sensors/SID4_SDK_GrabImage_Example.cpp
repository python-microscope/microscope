/*
	© Copyright 2008 by PHASICS.
	All rights reserved.

	@File:	SID4_SDK_GrabImage_Example.cpp
	@Description: This example shows how to grab an interferogram from the current camera.
	
	4 functions are involved:

	OpenSID4 loads the configuration file specified by "userProfile_File" in memory. 
	It returns a unique reference ID "SessionID" that should be used as an input
	for all other SID4 SDK functions.

	GetUserProfile outputs the current camera settings.

	GrabImage grabs an interferogram from the camera. It initializes the camera according the
	current camera settings, grabs an image (2D int16 Array) and stops the acquisition.

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
	ArraySize ImageCameraSize;

	//  Open SID4 Session
	OpenSID4(userProfile_File,&SessionID,&Error);
	if(!Error)
	{	printf ("************************ SID4 Session correctly opened **********************\n");
		printf ("SessionID=%d; Error=%d\n",SessionID,Error);
	}
	else{
		printf ("\nThe error %d occured in the OpenSID4 function!\n\n",Error);
		exit(1);
	}

	// Reading of the current camera settings stored in the user profile
	GetUserProfile(&SessionID, UserProfile_Name, uspName_bufSize, UserProfile_File, uspFile_bufSize, 
		UserProfile_Description, uspDesc_bufSize, UsrP_LastReference, uspLastRef_bufSize, 
		UserProfile_Directory, uspDir_bufSize,SDKVersion, version_bufSize, &AnalysisInformation, 
		&CameraInformation, SNPhasics, SNPhasics_bufSize, &ImageCameraSize, &Error);

	if(!Error)
	{	
		printf("\n**Camera settings** \n");
		printf ("PhasicsS/N=%s\n",SNPhasics);
		printf ("FrameRate=%d\n",CameraInformation.FrameRate);
		printf ("Gain=%d\n",CameraInformation.Gain);
		printf ("ExposureTime=%d\n",CameraInformation.ExposureTime);
		printf ("TriggerMode=%d\n",CameraInformation.TriggerMode);
	}


	nrow = ImageCameraSize.height;    // 480
	ncol = ImageCameraSize.width;		// 640

	// Memory allocation of Image before calling GrabImage function
	long Image_bufSize = nrow*ncol;
	short int *Image = (short int*)malloc(sizeof(short int)* Image_bufSize);

	// Grab an image from camera
	GrabImage(&SessionID, Image, Image_bufSize, &ImageCameraSize, &Error);
		
	if(!Error)
	{	printf("\n**Image content**\n");
		printf ("Image[0,0]=%d ",Image[0]);
	}

	// Close the SID4 session
	CloseSID4(&SessionID,&Error);

	// Release memory
	free(Image);
}
