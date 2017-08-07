Python
2.7
.13(v2
.7
.13: a06454b1afa1, Dec
17
2016, 20: 42:59) [MSC v.1500 32 bit(Intel)]
on
win32
Type
"copyright", "credits" or "license()"
for more information.
    >> > import os, ctypes
>> > os.chdir('C:\Program Files (x86)\SID4_SDK\DLL SDK\BIN')
>> > SDK = ctypes.WinDLL('SID4_SDK')
>> >
>> > SDK
< WinDLL
'SID4_SDK', handle
3110000
at
29
b58f0 >
>> > UserProfileFile = 'C:\Program Files (x86)\SID4\phasics\SID4-079b default profile.txt'
>> > SDK.OpenSID4(UserProfileFile)
0
>> > r = SDK.OpenSID4(UserProfileFile)
>> > r
0
>> > OpenSID4 = getattr(SDK, 'OpenSID4')
>> > OpenSID4
< _FuncPtr
object
at
0x02861648 >
>> > OpenSID4.restype
< class 'ctypes.c_long'>

>> > OpenSID4.argtypes
>> > r
0
>> > type(r)
< type
'int' >
>> > reference = ctypes.c_int
>> > refPointer = ctypes.POINTER(reference)
>> > refPointer
< class '__main__.LP_c_long'>

>> > p = refPointer()
>> > p
< __main__.LP_c_long
object
at
0x02886AD0 >
>> > e = refPointer()
>> > e
< __main__.LP_c_long
object
at
0x02833F30 >
>> > e
< __main__.LP_c_long
object
at
0x02833F30 >
>> > OpenSID4
< _FuncPtr
object
at
0x02861648 >
>> > OpenSID4(UserProfileFile, p, e)

Traceback(most
recent
call
last):
File
"<pyshell#24>", line
1, in < module >
OpenSID4(UserProfileFile, p, e)
ValueError: Procedure
probably
called
with too many arguments (12 bytes in excess)
>> > OpenSID4(p, e)

Traceback(most
recent
call
last):
File
"<pyshell#25>", line
1, in < module >
OpenSID4(p, e)
ValueError: Procedure
probably
called
with too many arguments (8 bytes in excess)
>> > OpenSID4()

Traceback(most
recent
call
last):
File
"<pyshell#26>", line
1, in < module >
OpenSID4()
WindowsError: exception: access
violation
writing
0x7332D7A6
>> > OpenSID4(p)
0
>> > OpenSID4(e)
0
>> > e
< __main__.LP_c_long
object
at
0x02833F30 >
>> > p
< __main__.LP_c_long
object
at
0x02886AD0 >
>> > OpenSID4.argtypes
>> > OpenSID4 = getattr(SDK, 'OpenSID4')
>> > OpenSID4
< _FuncPtr
object
at
0x02861648 >
>> >
KeyboardInterrupt
>> > class SDK_Reference(ctypes.Structure):
    _fields_ = [('SDK_Reference', c_int)]


Traceback(most
recent
call
last):
File
"<pyshell#36>", line
1, in < module >


class SDK_Reference(ctypes.Structure):


    File
"<pyshell#36>", line
2, in SDK_Reference
_fields_ = [('SDK_Reference', c_int)]
NameError: name
'c_int' is not defined
>> > class SDK_Reference(ctypes.Structure):
    _fields_ = [('SDK_Reference', ctypes.c_int)]

>> > UserProfileFile
'C:\\Program Files (x86)\\SID4\\phasics\\SID4-079b default profile.txt'
>> > UserProfileLocation = c_char_p(UserProfileFile)

Traceback(most
recent
call
last):
File
"<pyshell#40>", line
1, in < module >
UserProfileLocation = c_char_p(UserProfileFile)
NameError: name
'c_char_p' is not defined
>> > UserProfileLocation = ctypes.c_char_p(UserProfileFile)
>> > UserProfileLocation
c_char_p('C:\\Program Files (x86)\\SID4\\phasics\\SID4-079b default profile.txt')
>> > ErrorCode = ctypes.c_long()
>> > ErrorCodeRef = ctypes.byref(ErrorCode)
>> > ErrorCodeRef
< cparam
'P'(02
99
CC88) >
>> > SessionID = SDK_Reference()
>> > SessionIDRef = ctypes.byref(SessionID)
>> > OpenSID4(UserProfileLocation, SessioIDRef, ErrorCodeRef)

Traceback(most
recent
call
last):
File
"<pyshell#48>", line
1, in < module >
OpenSID4(UserProfileLocation, SessioIDRef, ErrorCodeRef)
NameError: name
'SessioIDRef' is not defined
>> > OpenSID4(UserProfileLocation, SessionIDRef, ErrorCodeRef)

Traceback(most
recent
call
last):
File
"<pyshell#49>", line
1, in < module >
OpenSID4(UserProfileLocation, SessionIDRef, ErrorCodeRef)
ValueError: Procedure
probably
called
with too many arguments (12 bytes in excess)
>> > SDK1 = ctypes.CDLL('SID4_SDK')
>> > SDK1.OpenSID4(UserProfileLocation, SessionIDRef, ErrorCodeRef)
0
>> > SessionID
< __main__.SDK_Reference
object
at
0x0299CCB0 >
>> > SessionID.value

Traceback(most
recent
call
last):
File
"<pyshell#53>", line
1, in < module >
SessionID.value
AttributeError: 'SDK_Reference'
object
has
no
attribute
'value'
>> > SessionID
< __main__.SDK_Reference
object
at
0x0299CCB0 >
>> > ErrorCode
c_long(7017)