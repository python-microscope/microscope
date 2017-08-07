/*
	© Copyright 2008 by PHASICS.
	All rights reserved.

	@File:	SID4_SDK_OpenSID4_Example.cpp
	@Description: This example shows how to use OpenSID4() and CloseSID4() functions.

	OpenSID4 loads the configuration file specified by "userProfile_File" in memory. 
	It returns a unique reference ID "SessionID" that should be used as an input
	for all other SID4 SDK functions.

	CloseSID4 closes the SID4 session. It releases memory devoted to the session.
*/

#include <stdio.h>
#include "SID4_SDk.h"
#include "SID4_SDk_Constants.h"

void main(void)
{
	char userProfile_File[]="C:\\Program Files\\SID4_SDK\\Examples\\User Profile\\UserProfileExample.txt";
	SDK_Reference SessionID=0;
	long Error=0;

	OpenSID4(userProfile_File,&SessionID,&Error);
	printf ("This example shows how to use OpenSID4() and CloseSID4() functions\n");
	printf ("SessionID=%d; Error=%d",SessionID,Error);
	CloseSID4(&SessionID,&Error);
	//getchar();
	printf("ok");
}
