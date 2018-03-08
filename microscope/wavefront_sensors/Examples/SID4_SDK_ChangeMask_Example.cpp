/*
	© Copyright 2008 by PHASICS.
	All rights reserved.

	@File:	SID4_SDK_ChangeMask_Example.cpp
	@Description: This example shows how to define the pupil analysis applied to 
	the interferogram by loading a mask file (.msk).
	
	This example involves 6 SID4 SDK's functions:

	"OpenSID4" loads the configuration file specified by "userProfile_File" in memory. 
	It returns a unique reference ID "SessionID" that should be used as an input
	for all other SID4 SDK functions.

	"GetUserProfile" outputs the parameters currently used to analyse analyse interferograms
	and the camera settings.

	"LoadMaskDescriptorInfo" returns the mask descriptor information from a "*.msk" file:
		"Globalrectangle" gives the left, top, right and bottom position of the ROI global rectangle
		"ROI_NbOfContours" indicates the number of sub-ROI defined in the chosen mask (main ROI).
		"ROIinfo_Contours_info": array containing the sub-ROI characteristics, 
								there are three value for each one: 
								ID: this value refers to whether the contour is the external (0) or internal edge (1) 
								TypeValue: refers to the shape type of the contour: 3 = Rectangle, 4 = Oval or Circle
								NumberOfCorrdinates: the number of points that defines the contour.
		"ROIinfo_Contours_coordinates": array containing successively the coordinates of all sub-ROIs

	"ChangeMask" changes the current mask applied to the interferograms before any analysis. This
	defines the analysis pupil. It can be changed by giving the path to a previously saved mask file
	(.msk files saves with the phase and intensity files) or by giving manually the definition
	of a Region of Interedt (ROI) which indicates the position and shape of the desired pupil.

	"FileAnalysis" analyses the interferogram. It ouputs a Phase and Intensity map, Tilt information
	(X and Y tilts) removed from the ouput phase.

	"CloseSID4" closes the SID4 session. It releases memory devoted to the session.
*/


#include <stdio.h>
#include <malloc.h>				// for memory allocation
#include "SID4_SDk.h"
#include "SID4_SDk_Constants.h"

const int bufSize=1024;


void main(void)
{
	char MaskFile1[]="C:\\Program Files\\SID4_SDK\\Examples\\Mask files\\Mask2.msk";	
	char MaskFile2[]="C:\\Program Files\\SID4_SDK\\Examples\\Mask files\\Mask3.msk";	
	char userProfile_File[]="C:\\Program Files\\SID4_SDK\\Examples\\User Profile\\UserProfileExample.txt";
	char inteferogram_File[]="C:\\Program Files\\SID4_SDK\\Examples\\Interferograms\\Interferogram.tif";
	SDK_Reference SessionID=0;
	int i,nrow, ncol;
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
		printf ("SessionID=%d; Error=%d\n",SessionID,Error);
	}

	// Reading of parameters currently used for interferogram analysis 
	GetUserProfile(&SessionID, UserProfile_Name, uspName_bufSize, UserProfile_File, uspFile_bufSize, 
		UserProfile_Description, uspDesc_bufSize, UsrP_LastReference, uspLastRef_bufSize, 
		UserProfile_Directory, uspDir_bufSize,SDKVersion, version_bufSize, &AnalysisInformation, 
		&CameraInformation, SNPhasics, SNPhasics_bufSize, &ImageSize, &Error);
	
	// Array dimension for Phase and Intensity
	nrow = AnalysisInformation.PhaseSize_Height;    
	ncol = AnalysisInformation.PhaseSize_width;

	// memory allocation for Phase and Intensity before calling the FileAnalysis function
	TiltInfo TiltInformation;
	long Intensity_bufSize = nrow*ncol;
	long Phase_bufSize = nrow*ncol;
	ArraySize AnalysisArraySize;

	AnalysisArraySize.height=nrow;
	AnalysisArraySize.width=ncol;

	float *Intensity = (float*)malloc(sizeof(float)* Intensity_bufSize);
	float *Phase = (float*)malloc(sizeof(float)* Phase_bufSize);
	
	TiltInformation.XTilt=0;
	TiltInformation.YTilt=0;

	
	// Definition of the ROI Descriptor (Mask) which will be applied to the interferogram 
	// before any analysis

	//ROI Descriptor defintion 
	long ROI_GlobalRectangle[4];						//poition left, top, right and bottom side of the ROI global rectangle
	long globalRect_bufSize = 4;						// size of the ROI_GlobalRectangle array
	unsigned short int ROI_NbOfContours;				// gives the number of sub-ROI defined in the chosen mask (main ROI).
	unsigned long ROIinfo_Contours_info[bufSize];		//array containing the sub-ROI characteristics, there are three value for each one: ID,TypeValue, NumberOfCorrdinates
	long contoursInfo_bufSize = bufSize;
	long ROIinfo_Contours_coordinates[bufSize];		    //array containing successively the coordinates of all sub-ROIs
	long contoursCoord_bufSize = bufSize;

	// we want to use the mask defined in the "Mask2.msk" file as the analysis pupil.
	// Before to use the "ChangeMask" function to set the analysis pupil, it is necessary 
	// to get first the ROI descriptor information using the "LoadMaskDescriptorInfo" function
	// in order to initialize the input parameters of the "ChangeMask" function.

	LoadMaskDescriptorInfo(&SessionID, MaskFile1, ROI_GlobalRectangle, globalRect_bufSize, 
			&ROI_NbOfContours, ROIinfo_Contours_info, contoursInfo_bufSize, ROIinfo_Contours_coordinates, 
			contoursCoord_bufSize, &Error);

	unsigned long *ROI_1_Contours_info =(unsigned long*)calloc(3*ROI_NbOfContours,sizeof(unsigned long));   

	int j=0;
	int TotalNumberOfCoord = 0;
	for(i=0;i<ROI_NbOfContours;i++)
	{	
		j=3*i;
		*(ROI_1_Contours_info+j) = ROIinfo_Contours_info[j+0];		//ID of each sub-ROI
		*(ROI_1_Contours_info+j+1) = ROIinfo_Contours_info[j+1];	//Type of each sub-ROI
		*(ROI_1_Contours_info+j+2) = ROIinfo_Contours_info[j+2];	// NumberOfCoordinates of each sub-ROI
		TotalNumberOfCoord += *(ROI_1_Contours_info+j+2);
	}
	long *ROI_1_Contours_coordinates =(long*)calloc(TotalNumberOfCoord,sizeof(long));   

	// Set the mask defined in the Mask2.msk file as the current analysis pupil
	ChangeMask(&SessionID, MaskFile1, ROI_GlobalRectangle, globalRect_bufSize, 
			&ROI_NbOfContours, ROI_1_Contours_info, 3*ROI_NbOfContours, 
			ROI_1_Contours_coordinates, TotalNumberOfCoord, &Error);

	// Interferogram analysis with the mask defined in the "Mask2.msk" file
	FileAnalysis(&SessionID, &AnalysisArraySize, inteferogram_File, Intensity, Intensity_bufSize, 
				 Phase, Phase_bufSize, &TiltInformation, &Error);
	if(!Error)
	{	printf ("\nInterferogram Analysis with the mask defined in the Mask2.msk file");
		printf ("\nXtilt=%f; Ytilt=%f\n",TiltInformation.XTilt,TiltInformation.YTilt);
	}

	// We want now perform a new interferogram analysis with a new anylis pupil
	// We get first the mask descriptor information from the Mask3.msk file in order
	// to correctly initialize the "ChangeMask" function
	LoadMaskDescriptorInfo(&SessionID, MaskFile2, ROI_GlobalRectangle, globalRect_bufSize, 
			&ROI_NbOfContours, ROIinfo_Contours_info, contoursInfo_bufSize, ROIinfo_Contours_coordinates, 
			contoursCoord_bufSize, &Error);

	unsigned long *ROI_2_Contours_info =(unsigned long*)calloc(3*ROI_NbOfContours,sizeof(unsigned long));   
	j=0;
	TotalNumberOfCoord = 0;
	for(i=0;i<ROI_NbOfContours;i++)
	{	
		j=3*i;
		*(ROI_2_Contours_info+j) = ROIinfo_Contours_info[j+0];		//ID of each sub-ROI
		*(ROI_2_Contours_info+j+1) = ROIinfo_Contours_info[j+1];	//Type of each sub-ROI
		*(ROI_2_Contours_info+j+2) = ROIinfo_Contours_info[j+2];	// NumberOfCoordinates of each sub-ROI
		TotalNumberOfCoord += *(ROI_2_Contours_info+j+2);
	}
	long *ROI_2_Contours_coordinates =(long*)calloc(TotalNumberOfCoord,sizeof(long));   

	// Set the mask defined in the Mask3.msk file as the new current analysis pupil
	ChangeMask(&SessionID, MaskFile2, ROI_GlobalRectangle, globalRect_bufSize, 
			&ROI_NbOfContours, ROI_2_Contours_info, 3*ROI_NbOfContours, 
			ROI_2_Contours_coordinates, TotalNumberOfCoord, &Error);


	// Interferogram analysis with the new analysis pupil
	FileAnalysis(&SessionID, &AnalysisArraySize, inteferogram_File, Intensity, Intensity_bufSize, 
				 Phase, Phase_bufSize, &TiltInformation, &Error);
	if(!Error)
	{	printf ("\nInterferogram Analysis with the mask defined in the Mask3.msk file");
		printf ("\nXtilt=%f; Ytilt=%f\n\n",TiltInformation.XTilt,TiltInformation.YTilt);
	}



	// Close the SID4 session
	CloseSID4(&SessionID,&Error);

	// Memory release
	free(Intensity);
	free(Phase);
	free(ROI_1_Contours_info);
	free(ROI_1_Contours_coordinates);
	free(ROI_2_Contours_info);
	free(ROI_2_Contours_coordinates);

}
