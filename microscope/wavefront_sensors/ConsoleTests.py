import os
import ctypes
UserProfileFile = 'C:\Program Files (x86)\SID4\phasics\SID4-079b default profile.txt'
SDK = ctypes.CDLL('SID4_SDK')
UserProfileLocation = ctypes.c_char_p(UserProfileFile)
class SDK_Reference(ctypes.Structure):
    _fields_ = [('SDK_Reference', ctypes.c_int)]

SessionID = SDK_Reference()
SessionIDRef = ctypes.byref(SessionID)
ErrorCode = ctypes.c_long()
ErrorCodeRef = ctypes.byref(ErrorCode)

Phase = ctypes.c_float()
PhaseRef = ctypes.byref(Phase)


print('Opening SDK...')
SDK.OpenSID4(UserProfileLocation, SessionIDRef, ErrorCodeRef)

print(ErrorCode)

print('Session is:')
print(SessionID.SDK_Reference)

# print('Initializing camera...')
# SDK.CameraInit(SessionIDRef, ErrorCodeRef)
#
# print(ErrorCode)
#
# print('Starting Camera...')
# SDK.CameraStart(SessionIDRef, ErrorCodeRef)
#
# print(ErrorCode)

print('Starting Camera LifeMode...')
SDK.StartLiveMode(SessionIDRef, ErrorCodeRef)

print(ErrorCode)

#######

#######
print('Stopping Camera LifeMode...')
SDK.StopLiveMode(SessionIDRef, ErrorCodeRef)

print(ErrorCode)

print('Stopping Camera...')
SDK.CameraStop(SessionIDRef, ErrorCodeRef)

print(ErrorCode)

print('Closing Camera...')
SDK.CameraClose(SessionIDRef, ErrorCodeRef)

print(ErrorCode)

print('Closing SDK...')
SDK.CloseSID4(SessionIDRef, ErrorCodeRef)

print(ErrorCode)

