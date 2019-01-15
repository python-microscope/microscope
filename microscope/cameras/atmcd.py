#
#   andorsdk - a ctypes interface to Andor's SDK DLL.
#   Copyright (C) 2015-2019 Mick Phillips
#   mick.phillips@gmail.com
#   Re-wrapped using David Baddeley's approach for SDK3.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""atmcd

   This module wraps Andor's SDK for (EM)CCD cameras.
"""
import re, sys, functools, os, platform
import ctypes
from ctypes import Structure, POINTER
from ctypes import c_int, c_uint, c_long, c_ulong, c_longlong, c_ulonglong
from ctypes import c_ubyte, c_short, c_float, c_double, c_char, c_char_p
from ctypes import c_void_p
from numpy.ctypeslib import ndpointer

# Andor docs use Windows datatypes in call signatures. These may not be available on
# other platforms.
try:
    from ctypes.wintypes import BYTE, WORD, DWORD, HANDLE
except:
    # Docs give no clues. These need testing against a non-Windows library.
    BYTE = ctypes.c_byte
    WORD = ctypes.c_ushort
    DWORD = ctypes.c_ulong
    HANDLE = ctypes.c_void_p

_stdcall_libraries = {}
arch, plat = platform.architecture()
if arch == '32bit':
    _dllName = 'atmcd32d'
else:
    _dllName = 'atmcd64d'
if os.name in ('nt', 'ce'):
    _dll = ctypes.WinDLL(_dllName)
else:
    _dll = ctypes.CDLL(_dllName + '.so')

# Andor's types
at_32 = c_long
at_u32 = c_ulong
at_64 = c_longlong
at_u64 =  c_ulonglong

"""Version Information Definitions"""
# Version information enumeration
class AT_VersionInfoId(c_int): pass
AT_SDKVersion = AT_VersionInfoId(0x40000000)
AT_DeviceDriverVersion = AT_VersionInfoId(0x40000001)
# No. of elements in version info.
AT_NoOfVersionInfoIds = 2
# Minimum recommended length of the Version Info buffer parameter
AT_VERSION_INFO_LEN = 80
# Minimum recommended length of the Controller Card Model buffer parameter
AT_CONTROLLER_CARD_MODEL_LEN = 80

"""DDG Lite Definitions"""
## Channel enumeration
class AT_DDGLiteChannelId(c_int): pass
AT_DDGLite_ChannelA = AT_DDGLiteChannelId(0x40000000)
AT_DDGLite_ChannelB = AT_DDGLiteChannelId(0x40000001)
AT_DDGLite_ChannelC = AT_DDGLiteChannelId(0x40000002)
## Control byte flags
AT_DDGLite_ControlBit_GlobalEnable   = 0x01
AT_DDGLite_ControlBit_ChannelEnable  = 0x01
AT_DDGLite_ControlBit_FreeRun        = 0x02
AT_DDGLite_ControlBit_DisableOnFrame = 0x04
AT_DDGLite_ControlBit_RestartOnFire  = 0x08
AT_DDGLite_ControlBit_Invert         = 0x10
AT_DDGLite_ControlBit_EnableOnFire   = 0x20

"""USB iStar Definitions"""
# Electrical
AT_DDG_POLARITY_POSITIVE  = 0
AT_DDG_POLARITY_NEGATIVE  = 1
AT_DDG_TERMINATION_50OHMS = 0
AT_DDG_TERMINATION_HIGHZ  = 1
# Stepmode
AT_STEPMODE_CONSTANT      = 0
AT_STEPMODE_EXPONENTIAL   = 1
AT_STEPMODE_LOGARITHMIC   = 2
AT_STEPMODE_LINEAR        = 3
AT_STEPMODE_OFF           = 100
# Gatemode
AT_GATEMODE_FIRE_AND_GATE = 0
AT_GATEMODE_FIRE_ONLY     = 1
AT_GATEMODE_GATE_ONLY     = 2
AT_GATEMODE_CW_ON         = 3
AT_GATEMODE_CW_OFF        = 4
AT_GATEMODE_DDG           = 5


"""typedef structs"""
class ANDORCAPS(Structure):
    _fields_ = [
                ("ulSize", c_ulong),
                ("ulAcqModes", c_ulong),
                ("ulReadModes", c_ulong),
                ("ulTriggerModes", c_ulong),
                ("ulCameraType", c_ulong),
                ("ulPixelMode", c_ulong),
                ("ulSetFunctions", c_ulong),
                ("ulGetFunctions", c_ulong),
                ("ulFeatures", c_ulong),
                ("ulPCICard", c_ulong),
                ("ulEMGainCapability", c_ulong),
                ("ulFTReadModes", c_ulong),
                ]

    def __init__(self):
        # The function that uses this strcut requires that ulSize contains
        # the size of the structure.
        self.ulSize = sys.getsizeof(self)

AndorCapabilities = ANDORCAPS


class COLORDEMOSAICINFO(Structure):
    _fields_ = [
        ('iX', c_int),
        ('iY', c_int),
        ('iAlgorithm', c_int),
        ('iXPhase', c_int),
        ('iYPhase', c_int),
        ('iBackground', c_int),
        ]

ColorDemosaicInfo = COLORDEMOSAICINFO


class SYSTEMTIME(Structure):
    _fields_ = [
        ('wYear', WORD),
        ('wMonth', WORD),
        ('wDayOfWeek', WORD),
        ('wDay', WORD),
        ('wHour', WORD),
        ('wMinute', WORD),
        ('wSecond', WORD),
        ('wMilliseconds', WORD),
        ]


class WHITEBALANCEINFO(Structure):
    _fields_ = [
        ('iSize', c_int),
        ('iX', c_int),
        ('iY', c_int),
        ('iAlgorithm', c_int),
        ('iROI_left', c_int),
        ('iROI_right', c_int),
        ('iROI_top', c_int),
        ('iROI_bottom', c_int),
        ('iOperation', c_int),
        ]

WhiteBalanceInfo = WHITEBALANCEINFO


"""Enums"""
# Status codes
DRV_ERROR_CODES = 20001
DRV_SUCCESS = 20002
DRV_VXDNOTINSTALLED = 20003
DRV_ERROR_SCAN = 20004
DRV_ERROR_CHECK_SUM = 20005
DRV_ERROR_FILELOAD = 20006
DRV_UNKNOWN_FUNCTION = 20007
DRV_ERROR_VXD_INIT = 20008
DRV_ERROR_ADDRESS = 20009
DRV_ERROR_PAGELOCK = 20010
DRV_ERROR_PAGEUNLOCK = 20011
DRV_ERROR_BOARDTEST = 20012
DRV_ERROR_ACK = 20013
DRV_ERROR_UP_FIFO = 20014
DRV_ERROR_PATTERN = 20015
DRV_ACQUISITION_ERRORS = 20017
DRV_ACQ_BUFFER = 20018
DRV_ACQ_DOWNFIFO_FULL = 20019
DRV_PROC_UNKONWN_INSTRUCTION = 20020
DRV_ILLEGAL_OP_CODE = 20021
DRV_KINETIC_TIME_NOT_MET = 20022
DRV_ACCUM_TIME_NOT_MET = 20023
DRV_NO_NEW_DATA = 20024
DRV_PCI_DMA_FAIL = 20025
DRV_SPOOLERROR = 20026
DRV_SPOOLSETUPERROR = 20027
DRV_FILESIZELIMITERROR = 20028
DRV_ERROR_FILESAVE = 20029
DRV_TEMPERATURE_CODES = 20033
DRV_TEMPERATURE_OFF = 20034
DRV_TEMPERATURE_NOT_STABILIZED = 20035
DRV_TEMPERATURE_STABILIZED = 20036
DRV_TEMPERATURE_NOT_REACHED = 20037
DRV_TEMPERATURE_OUT_RANGE = 20038
DRV_TEMPERATURE_NOT_SUPPORTED = 20039
DRV_TEMPERATURE_DRIFT = 20040
DRV_TEMP_CODES = 20033
DRV_TEMP_OFF = 20034
DRV_TEMP_NOT_STABILIZED = 20035
DRV_TEMP_STABILIZED = 20036
DRV_TEMP_NOT_REACHED = 20037
DRV_TEMP_OUT_RANGE = 20038
DRV_TEMP_NOT_SUPPORTED = 20039
DRV_TEMP_DRIFT = 20040
DRV_GENERAL_ERRORS = 20049
DRV_INVALID_AUX = 20050
DRV_COF_NOTLOADED = 20051
DRV_FPGAPROG = 20052
DRV_FLEXERROR = 20053
DRV_GPIBERROR = 20054
DRV_EEPROMVERSIONERROR = 20055
DRV_DATATYPE = 20064
DRV_DRIVER_ERRORS = 20065
DRV_P1INVALID = 20066
DRV_P2INVALID = 20067
DRV_P3INVALID = 20068
DRV_P4INVALID = 20069
DRV_INIERROR = 20070
DRV_COFERROR = 20071
DRV_ACQUIRING = 20072
DRV_IDLE = 20073
DRV_TEMPCYCLE = 20074
DRV_NOT_INITIALIZED = 20075
DRV_P5INVALID = 20076
DRV_P6INVALID = 20077
DRV_INVALID_MODE = 20078
DRV_INVALID_FILTER = 20079
DRV_I2CERRORS = 20080
DRV_I2CDEVNOTFOUND = 20081
DRV_I2CTIMEOUT = 20082
DRV_P7INVALID = 20083
DRV_P8INVALID = 20084
DRV_P9INVALID = 20085
DRV_P10INVALID = 20086
DRV_P11INVALID = 20087
DRV_USBERROR = 20089
DRV_IOCERROR = 20090
DRV_VRMVERSIONERROR = 20091
DRV_GATESTEPERROR = 20092
DRV_USB_INTERRUPT_ENDPOINT_ERROR = 20093
DRV_RANDOM_TRACK_ERROR = 20094
DRV_INVALID_TRIGGER_MODE = 20095
DRV_LOAD_FIRMWARE_ERROR = 20096
DRV_DIVIDE_BY_ZERO_ERROR = 20097
DRV_INVALID_RINGEXPOSURES = 20098
DRV_BINNING_ERROR = 20099
DRV_INVALID_AMPLIFIER = 20100
DRV_INVALID_COUNTCONVERT_MODE = 20101
DRV_ERROR_NOCAMERA = 20990
DRV_NOT_SUPPORTED = 20991
DRV_NOT_AVAILABLE = 20992
DRV_ERROR_MAP = 20115
DRV_ERROR_UNMAP = 20116
DRV_ERROR_MDL = 20117
DRV_ERROR_UNMDL = 20118
DRV_ERROR_BUFFSIZE = 20119
DRV_ERROR_NOHANDLE = 20121
DRV_GATING_NOT_AVAILABLE = 20130
DRV_FPGA_VOLTAGE_ERROR = 20131
DRV_OW_CMD_FAIL = 20150
DRV_OWMEMORY_BAD_ADDR = 20151
DRV_OWCMD_NOT_AVAILABLE = 20152
DRV_OW_NO_SLAVES = 20153
DRV_OW_NOT_INITIALIZED = 20154
DRV_OW_ERROR_SLAVE_NUM = 20155
DRV_MSTIMINGS_ERROR = 20156
DRV_OA_NULL_ERROR = 20173
DRV_OA_PARSE_DTD_ERROR = 20174
DRV_OA_DTD_VALIDATE_ERROR = 20175
DRV_OA_FILE_ACCESS_ERROR = 20176
DRV_OA_FILE_DOES_NOT_EXIST = 20177
DRV_OA_XML_INVALID_OR_NOT_FOUND_ERROR = 20178
DRV_OA_PRESET_FILE_NOT_LOADED = 20179
DRV_OA_USER_FILE_NOT_LOADED = 20180
DRV_OA_PRESET_AND_USER_FILE_NOT_LOADED = 20181
DRV_OA_INVALID_FILE = 20182
DRV_OA_FILE_HAS_BEEN_MODIFIED = 20183
DRV_OA_BUFFER_FULL = 20184
DRV_OA_INVALID_STRING_LENGTH = 20185
DRV_OA_INVALID_CHARS_IN_NAME = 20186
DRV_OA_INVALID_NAMING = 20187
DRV_OA_GET_CAMERA_ERROR = 20188
DRV_OA_MODE_ALREADY_EXISTS = 20189
DRV_OA_STRINGS_NOT_EQUAL = 20190
DRV_OA_NO_USER_DATA = 20191
DRV_OA_VALUE_NOT_SUPPORTED = 20192
DRV_OA_MODE_DOES_NOT_EXIST = 20193
DRV_OA_CAMERA_NOT_SUPPORTED = 20194
DRV_OA_FAILED_TO_GET_MODE = 20195
DRV_PROCESSING_FAILED = 20211
# Acquisition modes
AC_ACQMODE_SINGLE = 1
AC_ACQMODE_VIDEO = 2
AC_ACQMODE_ACCUMULATE = 4
AC_ACQMODE_KINETIC = 8
AC_ACQMODE_FRAMETRANSFER = 16
AC_ACQMODE_FASTKINETICS = 32
AC_ACQMODE_OVERLAP = 64
AC_READMODE_FULLIMAGE = 1
AC_READMODE_SUBIMAGE = 2
AC_READMODE_SINGLETRACK = 4
AC_READMODE_FVB = 8
AC_READMODE_MULTITRACK = 16
AC_READMODE_RANDOMTRACK = 32
AC_READMODE_MULTITRACKSCAN = 64
AC_TRIGGERMODE_INTERNAL = 1
AC_TRIGGERMODE_EXTERNAL = 2
AC_TRIGGERMODE_EXTERNAL_FVB_EM = 4
AC_TRIGGERMODE_CONTINUOUS = 8
AC_TRIGGERMODE_EXTERNALSTART = 16
AC_TRIGGERMODE_EXTERNALEXPOSURE = 32
AC_TRIGGERMODE_INVERTED = 64
AC_TRIGGERMODE_EXTERNAL_CHARGESHIFTING = 128
AC_TRIGGERMODE_BULB = 32
AC_CAMERATYPE_PDA = 0
AC_CAMERATYPE_IXON = 1
AC_CAMERATYPE_ICCD = 2
AC_CAMERATYPE_EMCCD = 3
AC_CAMERATYPE_CCD = 4
AC_CAMERATYPE_ISTAR = 5
AC_CAMERATYPE_VIDEO = 6
AC_CAMERATYPE_IDUS = 7
AC_CAMERATYPE_NEWTON = 8
AC_CAMERATYPE_SURCAM = 9
AC_CAMERATYPE_USBICCD = 10
AC_CAMERATYPE_LUCA = 11
AC_CAMERATYPE_RESERVED = 12
AC_CAMERATYPE_IKON = 13
AC_CAMERATYPE_INGAAS = 14
AC_CAMERATYPE_IVAC = 15
AC_CAMERATYPE_UNPROGRAMMED = 16
AC_CAMERATYPE_CLARA = 17
AC_CAMERATYPE_USBISTAR = 18
AC_CAMERATYPE_SIMCAM = 19
AC_CAMERATYPE_NEO = 20
AC_CAMERATYPE_IXONULTRA = 21
AC_CAMERATYPE_VOLMOS = 22
AC_PIXELMODE_8BIT = 1
AC_PIXELMODE_14BIT = 2
AC_PIXELMODE_16BIT = 4
AC_PIXELMODE_32BIT = 8
AC_PIXELMODE_MONO = 0x000000
AC_PIXELMODE_RGB  = 0x010000
AC_PIXELMODE_CMY  = 0x020000
# Set functions
AC_SETFUNCTION_VREADOUT = 0x01
AC_SETFUNCTION_HREADOUT = 0x02
AC_SETFUNCTION_TEMPERATURE = 0x04
AC_SETFUNCTION_MCPGAIN = 0x08
AC_SETFUNCTION_EMCCDGAIN = 0x10
AC_SETFUNCTION_BASELINECLAMP = 0x20
AC_SETFUNCTION_VSAMPLITUDE = 0x40
AC_SETFUNCTION_HIGHCAPACITY = 0x80
AC_SETFUNCTION_BASELINEOFFSET = 0x0100
AC_SETFUNCTION_PREAMPGAIN = 0x0200
AC_SETFUNCTION_CROPMODE = 0x0400
AC_SETFUNCTION_DMAPARAMETERS = 0x0800
AC_SETFUNCTION_HORIZONTALBIN = 0x1000
AC_SETFUNCTION_MULTITRACKHRANGE = 0x2000
AC_SETFUNCTION_RANDOMTRACKNOGAPS = 0x4000
AC_SETFUNCTION_EMADVANCED = 0x8000
AC_SETFUNCTION_GATEMODE = 0x010000
AC_SETFUNCTION_DDGTIMES = 0x020000
AC_SETFUNCTION_IOC = 0x040000
AC_SETFUNCTION_INTELLIGATE = 0x080000
AC_SETFUNCTION_INSERTION_DELAY = 0x100000
AC_SETFUNCTION_GATESTEP = 0x200000
AC_SETFUNCTION_TRIGGERTERMINATION = 0x400000
AC_SETFUNCTION_EXTENDEDNIR = 0x800000
AC_SETFUNCTION_SPOOLTHREADCOUNT = 0x1000000
# AC_SETFUNCTION_MCPGAIN deprecated
AC_SETFUNCTION_GAIN = 8
AC_SETFUNCTION_ICCDGAIN = 8
# Get functions
AC_GETFUNCTION_TEMPERATURE = 0x01
AC_GETFUNCTION_TARGETTEMPERATURE = 0x02
AC_GETFUNCTION_TEMPERATURERANGE = 0x04
AC_GETFUNCTION_DETECTORSIZE = 0x08
AC_GETFUNCTION_MCPGAIN = 0x10
AC_GETFUNCTION_EMCCDGAIN = 0x20
AC_GETFUNCTION_HVFLAG = 0x40
AC_GETFUNCTION_GATEMODE = 0x80
AC_GETFUNCTION_DDGTIMES = 0x0100
AC_GETFUNCTION_IOC = 0x0200
AC_GETFUNCTION_INTELLIGATE = 0x0400
AC_GETFUNCTION_INSERTION_DELAY = 0x0800
AC_GETFUNCTION_GATESTEP = 0x1000
AC_GETFUNCTION_PHOSPHORSTATUS = 0x2000
AC_GETFUNCTION_MCPGAINTABLE = 0x4000
AC_GETFUNCTION_BASELINECLAMP = 0x8000
# AC_GETFUNCTION_MCPGAIN deprecated
AC_GETFUNCTION_GAIN = 0x10
AC_GETFUNCTION_ICCDGAIN = 0x10
# Features
AC_FEATURES_POLLING = 1
AC_FEATURES_EVENTS = 2
AC_FEATURES_SPOOLING = 4
AC_FEATURES_SHUTTER = 8
AC_FEATURES_SHUTTEREX = 16
AC_FEATURES_EXTERNAL_I2C = 32
AC_FEATURES_SATURATIONEVENT = 64
AC_FEATURES_FANCONTROL = 128
AC_FEATURES_MIDFANCONTROL = 256
AC_FEATURES_TEMPERATUREDURINGACQUISITION = 512
AC_FEATURES_KEEPCLEANCONTROL = 1024
AC_FEATURES_DDGLITE = 0x0800
AC_FEATURES_FTEXTERNALEXPOSURE = 0x1000
AC_FEATURES_KINETICEXTERNALEXPOSURE = 0x2000
AC_FEATURES_DACCONTROL = 0x4000
AC_FEATURES_METADATA = 0x8000
AC_FEATURES_IOCONTROL = 0x10000
AC_FEATURES_PHOTONCOUNTING = 0x20000
AC_FEATURES_COUNTCONVERT = 0x40000
AC_FEATURES_DUALMODE = 0x80000
AC_FEATURES_OPTACQUIRE = 0x100000
AC_FEATURES_REALTIMESPURIOUSNOISEFILTER = 0x200000
AC_FEATURES_POSTPROCESSSPURIOUSNOISEFILTER = 0x400000
AC_FEATURES_DUALPREAMPGAIN = 0x800000
AC_FEATURES_DEFECT_CORRECTION = 0x1000000
AC_FEATURES_STARTOFEXPOSURE_EVENT = 0x2000000
AC_FEATURES_ENDOFEXPOSURE_EVENT = 0x4000000
AC_FEATURES_CAMERALINK = 0x80000007108864
# Gain types
AC_EMGAIN_8BIT = 1
AC_EMGAIN_12BIT = 2
AC_EMGAIN_LINEAR12 = 4
AC_EMGAIN_REAL12 = 8

## We need a mapping to enable lookup of status codes to meaning.
status_codes = {}
for attrib_name in dir(sys.modules[__name__]):
    if attrib_name.startswith('DRV_'):
        status_codes.update({eval(attrib_name): attrib_name})

## The lookup function.
def lookup_status(code):
    key = code[0] if type(code) is list else code
    if key in status_codes:
        return status_codes[key]
    else:
        return "Unknown status code %s." % key


## The following classes and functions are lifted from David Baddeley's
# SDK3 wrapper, with some modifications and additions.

# Classes used to handle outputs and parameters that need buffers.
class _meta(object):
    pass

STRING = c_char_p

class ARRAY(_meta):
    def __init__(self, val):
        self.type = val
        self.val = ndpointer(val, flags="C_CONTIGUOUS")


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

    def getVar(self, bufLen):
        v = ctypes.create_string_buffer(bufLen)
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
    def __init__(self, name, args=[], argnames=[], lib=_dll):
        self.f = getattr(lib, name)
        self.f.restype = c_uint
        self.f.argtypes = [stripMeta(a) for a in args]
        self.fargs = args
        self.fargnames = argnames
        self.name = name
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
        c_args = []
        i = 0
        ret = []

        if self.buf_size_arg_pos >= 0:
            try:
                bs = args[self.buf_size_arg_pos]
            except:
                bs = 255
        else:
            bs = 255

        i = 0
        for farg in self.fargs:
            if isinstance(farg, OUTPUT):
                r, c_arg = farg.getVar(bs)
                c_args.append(c_arg)
                ret.append(r)
            elif isinstance(farg, _OUTSTRLEN):
                c_args.append(bs)
            else:
                c_args.append(args[i])
                i += 1

        # Make the library call.
        status = self.f(*c_args)
        if not status == DRV_SUCCESS:
            raise Exception("%s: %s" % (self.name, status_codes[status]))
        if len(ret) == 0:
            return None
        if len(ret) == 1:
            return ret[0]
        else:
            return ret

def dllFunc(name, args=[], argnames=[], lib=_dll):
    try:
        f = dllFunction(name, args, argnames, lib)
    except Exception as e:
        raise Exception("Error wrapping dll function '%s':\n\t%s" % (name, e))
    globals()[name] = f

dllFunc('AbortAcquisition', [], [])
dllFunc('CancelWait', [], [])
dllFunc('CoolerOFF', [], [])
dllFunc('CoolerON', [], [])
dllFunc('DemosaicImage', [POINTER(WORD), POINTER(WORD), POINTER(WORD),
                          POINTER(WORD), POINTER(ColorDemosaicInfo)],
                         ['grey', 'red', 'green', 'blue', 'info'])
dllFunc('EnableKeepCleans', [c_int], ['iMode'])
dllFunc('FreeInternalMemory', [], [])
dllFunc('GetAcquiredData', [ARRAY(at_32), c_ulong], ['arr', 'size'])
dllFunc('GetAcquiredData16', [ARRAY(WORD), c_ulong], ['arr', 'size'])
# GetAcquiredFloatData(float * arr, unsigned long size)
dllFunc('GetAcquisitionProgress', [OUTPUT(c_long), OUTPUT(c_long)],
                                  ['acc', 'series'])
dllFunc('GetAcquisitionTimings', [OUTPUT(c_float), OUTPUT(c_float), OUTPUT(c_float)],
                                 ['exposure', 'accumulate', 'kinetic'])
dllFunc('GetAdjustedRingExposureTimes', [c_int, POINTER(c_float)],
                                        ['iNumTimes', 'fptimes'])
# GetAllDMAData(at_32 * arr, unsigned long size)
dllFunc('GetAmpDesc', [c_int, OUTSTRING, OUTSTRLEN],
                      ['index', 'name', 'length'])
dllFunc('GetAmpMaxSpeed', [c_int, OUTPUT(c_float)], ['index', 'speed'])
dllFunc('GetAvailableCameras', [OUTPUT(c_long)], ['totalCameras'])
# # GetBackground(at_32 * arr, unsigned long size)
dllFunc('GetBaselineClamp', [OUTPUT(c_int)], ['state'])
dllFunc('GetBitDepth', [c_int, OUTPUT(c_int)], ['channel', 'depth'])
dllFunc('GetCameraEventStatus', [OUTPUT(DWORD)], ['camStatus'])
dllFunc('GetCameraHandle', [c_long, OUTPUT(c_long)],
                           ['cameraIndex', 'cameraHandle'])
dllFunc('GetCameraInformation', [c_int, OUTPUT(c_long)],
                                ['index', 'information'])
dllFunc('GetCameraSerialNumber', [OUTPUT(c_int)], ['number'])
dllFunc('GetCapabilities', [OUTPUT(AndorCapabilities)], ['caps'])
dllFunc('GetControllerCardModel', [OUTSTRING], ['controllerCardModel'])
dllFunc('GetCountConvertWavelengthRange', [OUTPUT(c_float), OUTPUT(c_float)],
                                          ['minVal', 'maxVal'])
dllFunc('GetCurrentCamera', [OUTPUT(c_long)], ['cameraHandle'])
# # GetCYMGShift(int * iXshift, int * iYShift)
# GetDDGExternalOutputEnabled(at_u32 uiIndex, at_u32 * puiEnabled)
# GetDDGExternalOutputPolarity(at_u32 uiIndex, at_u32 * puiPolarity)
# GetDDGExternalOutputStepEnabled(at_u32 uiIndex, at_u32 * puiEnabled)
# GetDDGExternalOutputTime(at_u32 uiIndex, at_u64 * puiDelay, at_u64 * puiWidth)
# GetDDGTTLGateWidth(at_u64 opticalWidth, at_u64 * ttlWidth)
# GetDDGGateTime(at_u64 * puiDelay, at_u64 * puiWidth)
# GetDDGInsertionDelay(int * piState)
# GetDDGIntelligate(int * piState)
# GetDDGIOC(int * state)
# GetDDGIOCFrequency(double * frequency)
# GetDDGIOCNumber(unsigned long * numberPulses)
# GetDDGIOCNumberRequested(at_u32 * pulses)
# GetDDGIOCPeriod(at_u64 * period)
# GetDDGIOCPulses(int * pulses)
# GetDDGIOCTrigger(at_u32 * trigger)
# GetDDGOpticalWidthEnabled(at_u32 * puiEnabled)
# # GetDDGLiteGlobalControlByte(unsigned char * control)
# # GetDDGLiteControlByte(AT_DDGLiteChannelId channel, unsigned char * control)
# # GetDDGLiteInitialDelay(AT_DDGLiteChannelId channel, float * fDelay)
# # GetDDGLitePulseWidth(AT_DDGLiteChannelId channel, float * fWidth)
# # GetDDGLiteInterPulseDelay(AT_DDGLiteChannelId channel, float * fDelay)
# # GetDDGLitePulsesPerExposure(AT_DDGLiteChannelId channel, at_u32 * ui32Pulses)
# GetDDGPulse(double wid, double resolution, double * Delay, double * Width)
# GetDDGStepCoefficients(at_u32 mode, double * p1, double * p2)
# GetDDGStepMode(at_u32 * mode)
dllFunc('GetDetector', [OUTPUT(c_int), OUTPUT(c_int)], ['xpixels', 'ypixels'])
# # GetDICameraInfo(void * info)
dllFunc('GetEMAdvanced', [OUTPUT(c_int)], ['state'])
dllFunc('GetEMCCDGain', [OUTPUT(c_int)], [' gain'])
dllFunc('GetEMGainRange', [OUTPUT(c_int), OUTPUT(c_int)], ['low', 'high'])
dllFunc('GetExternalTriggerTermination', [OUTPUT(at_u32)], ['puiTermination'])
dllFunc('GetFastestRecommendedVSSpeed', [OUTPUT(c_int), OUTPUT(c_float)],
                                        ['index', 'speed'])
# # GetFIFOUsage(int * FIFOusage)
dllFunc('GetFilterMode', [OUTPUT(c_int)], ['mode'])
dllFunc('GetFKExposureTime', [OUTPUT(c_float)], ['time'])
# # GetFKVShiftSpeed(int index, int * speed)
dllFunc('GetFKVShiftSpeedF', [c_int, OUTPUT(c_float)], ['index', 'speed'])
dllFunc('GetFrontEndStatus', [OUTPUT(c_int)], ['piFlag'])
dllFunc('GetGateMode', [OUTPUT(c_int)], ['piGatemode'])
dllFunc('GetHardwareVersion', [OUTPUT(c_uint) for i in range(6)],
                              ['PCB', 'Decode', 'dummy1', 'dummy2',
                               'CameraFirmwareVersion', 'CameraFirmwareBuild'])
dllFunc('GetHeadModel', [OUTSTRING], ['name'])
# # GetHorizontalSpeed(int index, int * speed)
dllFunc('GetHSSpeed', [c_int, c_int, c_int, OUTPUT(c_float)],
                      ['channel', 'typ', 'index', 'speed'])
dllFunc('GetHVflag', [OUTPUT(c_int)], ['bFlag'])
# # GetID(int devNum, int * id)
dllFunc('GetImageFlip', [OUTPUT(c_int), OUTPUT(c_int)],
                        ['iHFlip', 'iVFlip'])
dllFunc('GetImageRotate', [OUTPUT(c_int)], ['Rotate'])
dllFunc('GetImages', [c_long, c_long, ARRAY(at_32), c_ulong, OUTPUT(c_long), OUTPUT(c_long)],
                     ['first','last', 'arr', 'size', 'validfirst', 'validlast'])
dllFunc('GetImages16', [c_long, c_long, ARRAY(WORD), c_ulong, OUTPUT(c_long), OUTPUT(c_long)],
                       ['first','last', 'arr', 'size', 'validfirst', 'validlast'])
dllFunc('GetImagesPerDMA', [OUTPUT(c_ulong)], ['images'])
# # GetIRQ(int * IRQ)
dllFunc('GetKeepCleanTime', [OUTPUT(c_float)], ['KeepCleanTime'])
dllFunc('GetMaximumBinning', [c_int, c_int, OUTPUT(c_int)],
                             ['ReadMode', 'HorzVert', 'MaxBinning'])
dllFunc('GetMaximumExposure', [OUTPUT(c_float)], ['MaxExp'])
dllFunc('GetMCPGain', [OUTPUT(c_int)], ['piGain'])
dllFunc('GetMCPGainRange', [OUTPUT(c_int), OUTPUT(c_int)], ['iLow', 'iHigh'])
# # GetMCPGainTable(int iNum, int * piGain, float * pfPhotoepc)
dllFunc('GetMCPVoltage', [OUTPUT(c_int)], ['iVoltage'])
dllFunc('GetMinimumImageLength', [OUTPUT(c_int)], ['MinImageLength'])
# # GetMinimumNumberInSeries(int * number)
dllFunc('GetMostRecentColorImage16', [c_ulong, c_int, ARRAY(WORD), ARRAY(WORD), ARRAY(WORD)],
                                     ['size', 'algorithm', 'red', 'green', 'blue'])
dllFunc('GetMostRecentImage', [ARRAY(at_32), c_ulong], ['arr', 'size'])
dllFunc('GetMostRecentImage16', [ARRAY(WORD), c_ulong], ['arr', 'size'])
# # GetMSTimingsData(SYSTEMTIME * TimeOfStart, float * pfDifferences, int inoOfImages)
dllFunc('GetMetaDataInfo', [OUTPUT(SYSTEMTIME), OUTPUT(c_float), c_uint],
                           ['TimeOfStart', 'TimeFromStart', 'index'])
# # GetMSTimingsEnabled(void)
# # GetNewData(at_32 * arr, unsigned long size)
# # GetNewData16(WORD * arr, unsigned long size)
# # GetNewData8(unsigned char * arr, unsigned long size)
# # GetNewFloatData(float * arr, unsigned long size)
dllFunc('GetNumberADChannels', [OUTPUT(c_int)], ['channels'])
dllFunc('GetNumberAmp', [OUTPUT(c_int)], ['amp'])
dllFunc('GetNumberAvailableImages', [OUTPUT(at_32), OUTPUT(at_32)],
                                    ['first', 'last'])
dllFunc('GetNumberDDGExternalOutputs', [OUTPUT(at_u32)], ['puiCount'])
# # GetNumberDevices(int * numDevs)
dllFunc('GetNumberFKVShiftSpeeds', [OUTPUT(c_int)], ['number'])
# # GetNumberHorizontalSpeeds(int * number)
dllFunc('GetNumberHSSpeeds', [c_int, c_int, OUTPUT(c_int)],
                             ['channel', 'typ', 'speeds'])
dllFunc('GetNumberNewImages', [OUTPUT(c_long), OUTPUT(c_long)], ['first', 'last'])
dllFunc('GetNumberPhotonCountingDivisions', [OUTPUT(at_u32)], ['noOfDivisions'])
dllFunc('GetNumberPreAmpGains', [OUTPUT(c_int)], ['noGains'])
dllFunc('GetNumberRingExposureTimes', [OUTPUT(c_int)], ['ipnumTimes'])
dllFunc('GetNumberIO', [OUTPUT(c_int)], ['iNumber'])
# # GetNumberVerticalSpeeds(int * number)
dllFunc('GetNumberVSAmplitudes', [c_int], ['number'])
dllFunc('GetNumberVSSpeeds', [c_int], ['speeds'])
dllFunc('GetOldestImage', [ARRAY(at_32), c_ulong], ['arr', 'size'])
dllFunc('GetOldestImage16', [ARRAY(WORD), c_ulong], ['arr', 'size'])
dllFunc('GetPhosphorStatus', [OUTPUT(c_int)], ['piFlag'])
# # GetPhysicalDMAAddress(unsigned long * Address1, unsigned long * Address2)
dllFunc('GetPixelSize', [OUTPUT(c_float), OUTPUT(c_float)], ['xSize', 'ySize'])
dllFunc('GetPreAmpGain', [c_int, OUTPUT(c_float)], ['index', 'gain'])
dllFunc('GetPreAmpGainText', [c_int , OUTSTRING, OUTSTRLEN],
                             ['index', 'name', 'length'])
dllFunc('GetDualExposureTimes', [OUTPUT(c_float), OUTPUT(c_float)],
                                ['exposure1', 'exposure2'])
dllFunc('GetQE', [STRING, c_float, c_uint, OUTPUT(c_float)],
                 ['sensor', 'wavelength', 'mode', 'QE'])
dllFunc('GetReadOutTime', [OUTPUT(c_float)], ['ReadOutTime'])
# # GetRegisterDump(int * mode)
dllFunc('GetRingExposureRange', [OUTPUT(c_float), OUTPUT(c_float)],
                                ['Min', 'Max'])
# # GetSDK3Handle(int * Handle)
dllFunc('GetSensitivity', [c_int, c_int, c_int, c_int, OUTPUT(c_float)],
                          ['channel', 'horzShift', 'amplifier', 'pa', 'sensitivity'])
dllFunc('GetShutterMinTimes', [OUTPUT(c_int), OUTPUT(c_int)],
                              ['minclosingtime', 'minopeningtime'])
dllFunc('GetSizeOfCircularBuffer', [OUTPUT(c_long)], ['index'])
# # GetSlotBusDeviceFunction(DWORD * dwslot, DWORD * dwBus, DWORD * dwDevice, DWORD * dwFunction)
dllFunc('GetSoftwareVersion', [OUTPUT(c_uint) for i in range(6)],
                              ['eprom', 'coffile', 'vxdrev', 'vxdver', 'dllrev', 'dllver'])
# # GetSpoolProgress(long * index)
# # GetStartUpTime(float * time)
dllFunc('GetStatus', [OUTPUT(c_int)], ['status'])
dllFunc('GetTECStatus', [OUTPUT(c_int)], ['piFlag'])
dllFunc('GetTemperature', [OUTPUT(c_int)], ['temperature'])
dllFunc('GetTemperatureF', [OUTPUT(c_float)], ['temperature'])
dllFunc('GetTemperatureRange', [OUTPUT(c_int), OUTPUT(c_int)],
                               ['mintemp', 'maxtemp'])
# # GetTemperatureStatus(float * SensorTemp, float * TargetTemp, float * AmbientTemp, float * CoolerVolts)
dllFunc('GetTotalNumberImagesAcquired', [OUTPUT(c_long)], ['index'])
dllFunc('GetIODirection', [c_int, OUTPUT(c_int)], ['index', 'iDirection'])
dllFunc('GetIOLevel', [c_int, OUTPUT(c_int)], ['index', 'iLevel'])
dllFunc('GetVersionInfo', [AT_VersionInfoId, OUTSTRING, OUTSTRLEN],
                          ['arr', 'szVersionInfo', 'ui32BufferLen'])
# # GetVerticalSpeed(int index, int * speed)
# # GetVirtualDMAAddress(void ** Address1, void ** Address2)
dllFunc('GetVSAmplitudeString', [c_int, OUTSTRING], ['index', 'text'])
dllFunc('GetVSAmplitudeFromString', [STRING, OUTPUT(c_int)], ['text', 'index'])
dllFunc('GetVSAmplitudeValue', [c_int, OUTPUT(c_int)], ['index', 'value'])
dllFunc('GetVSSpeed', [c_int, OUTPUT(c_float)], ['index', 'speed'])
# GPIBReceive(int id, short address, char * text, int size)
# GPIBSend(int id, short address, char * text)
# I2CBurstRead(BYTE i2cAddress, long nBytes, BYTE * data)
# I2CBurstWrite(BYTE i2cAddress, long nBytes, BYTE * data)
# I2CRead(BYTE deviceID, BYTE intAddress, BYTE * pdata)
# I2CReset(void)
# I2CWrite(BYTE deviceID, BYTE intAddress, BYTE data)
# #'IdAndorDll(void)
# InAuxPort(int port, int * state)
dllFunc('Initialize', [STRING], ['dir'])
# #'InitializeDevice(char * dir)
dllFunc('IsAmplifierAvailable', [c_int], ['iamp'])
dllFunc('IsCoolerOn', [OUTPUT(c_int)], ['iCoolerStatus'])
dllFunc('IsCountConvertModeAvailable', [c_int], ['mode'])
dllFunc('IsInternalMechanicalShutter', [OUTPUT(c_int)], ['InternalShutter'])
dllFunc('IsPreAmpGainAvailable', [c_int, c_int, c_int, c_int, OUTPUT(c_int)],
                                 ['channel', 'amplifier', 'index', 'pa', 'status'])
dllFunc('IsTriggerModeAvailable', [c_int], ['iTriggerMode'])
# #'Merge(const at_32 * arr, long nOrder, long nPoint, long nPixel, float * coeff, long fit, long hbin, at_32 * output, float * start, float * step_Renamed)
# OutAuxPort(int port, int state)
dllFunc('PrepareAcquisition', [], [])
# SaveAsBmp(char * path, char * palette, long ymin, long ymax)
# SaveAsCommentedSif(char * path, char * comment)
# SaveAsEDF(char * szPath, int iMode)
# SaveAsFITS(char * szFileTitle, int typ)
# SaveAsRaw(char * szFileTitle, int typ)
# SaveAsSif(char * path)
# SaveAsSPC(char * path)
# SaveAsTiff(char * path, char * palette, int position, int typ)
# SaveAsTiffEx(char * path, char * palette, int position, int typ, int mode)
# #'SaveEEPROMToFile(char * cFileName)
# #'SaveToClipBoard(char * palette)
# #'SelectDevice(int devNum)
dllFunc('SendSoftwareTrigger', [], [])
dllFunc('SetAccumulationCycleTime', [c_float], ['time'])
# SetAcqStatusEvent(HANDLE statusEvent)
dllFunc('SetAcquisitionMode', [c_int], ['mode'])
# #'SetAcquisitionType(int typ)
dllFunc('SetADChannel', [c_int], ['channel'])
dllFunc('SetAdvancedTriggerModeState', [c_int], ['iState'])
# #'SetBackground(at_32 * arr, unsigned long size)
dllFunc('SetBaselineClamp', [c_int], ['state'])
dllFunc('SetBaselineOffset', [c_int], ['offset'])
dllFunc('SetCameraLinkMode', [c_int], ['mode'])
dllFunc('SetCameraStatusEnable', [DWORD], ['Enable'])
dllFunc('SetChargeShifting', [c_uint, c_uint], ['NumberRows', 'NumberRepeats'])
dllFunc('SetComplexImage', [c_uint, POINTER(c_int)], ['numAreas', 'areas'])
dllFunc('SetCoolerMode', [c_int], ['mode'])
dllFunc('SetCountConvertMode', [c_int], ['Mode'])
dllFunc('SetCountConvertWavelength', [c_float], ['wavelength'])
dllFunc('SetCropMode', [c_int, c_int, c_int], ['active', 'cropHeight', 'reserved'])
dllFunc('SetCurrentCamera', [c_long], ['cameraHandle'])
dllFunc('SetCustomTrackHBin', [c_int], ['bin'])
# #'SetDataType(int typ)
dllFunc('SetDACOutput', [c_int, c_int, c_int], ['iOption', 'iResolution', 'iValue'])
dllFunc('SetDACOutputScale', [c_int], ['iScale'])
# #'SetDDGAddress(BYTE t0, BYTE t1, BYTE t2, BYTE t3, BYTE address)
# SetDDGExternalOutputEnabled(at_u32 uiIndex, at_u32 uiEnabled)
# SetDDGExternalOutputPolarity(at_u32 uiIndex, at_u32 uiPolarity)
# SetDDGExternalOutputStepEnabled(at_u32 uiIndex, at_u32 uiEnabled)
# SetDDGExternalOutputTime(at_u32 uiIndex, at_u64 uiDelay, at_u64 uiWidth)
# #'SetDDGGain(int gain)
# SetDDGGateStep(double step_Renamed)
# SetDDGGateTime(at_u64 uiDelay, at_u64 uiWidth)
# SetDDGInsertionDelay(int state)
# SetDDGIntelligate(int state)
# SetDDGIOC(int state)
# SetDDGIOCFrequency(double frequency)
# SetDDGIOCNumber(unsigned long numberPulses)
# SetDDGIOCPeriod(at_u64 period)
# SetDDGIOCTrigger(at_u32 trigger)
# SetDDGOpticalWidthEnabled(at_u32 uiEnabled)
# #'SetDDGLiteGlobalControlByte(unsigned char control)
# #'SetDDGLiteControlByte(AT_DDGLiteChannelId channel, unsigned char control)
# #'SetDDGLiteInitialDelay(AT_DDGLiteChannelId channel, float fDelay)
# #'SetDDGLitePulseWidth(AT_DDGLiteChannelId channel, float fWidth)
# #'SetDDGLiteInterPulseDelay(AT_DDGLiteChannelId channel, float fDelay)
# #'SetDDGLitePulsesPerExposure(AT_DDGLiteChannelId channel, at_u32 ui32Pulses)
# SetDDGStepCoefficients(at_u32 mode, double p1, double p2)
# SetDDGStepMode(at_u32 mode)
# SetDDGTimes(double t0, double t1, double t2)
# SetDDGTriggerMode(int mode)
# SetDDGVariableGateStep(int mode, double p1, double p2)
# SetDelayGenerator(int board, short address, int typ)
# SetDMAParameters(int MaxImagesPerDMA, float SecondsPerDMA)
# SetDriverEvent(HANDLE driverEvent)
dllFunc('SetEMAdvanced', [c_int], ['state'])
dllFunc('SetEMCCDGain', [c_int], ['gain'])
# #'SetEMClockCompensation(int EMClockCompensationFlag)
dllFunc('SetEMGainMode', [c_int], ['mode'])
dllFunc('SetExposureTime', [c_float], ['time'])
dllFunc('SetExternalTriggerTermination', [at_u32], ['uiTermination'])
dllFunc('SetFanMode', [c_int], ['mode'])
dllFunc('SetFastExtTrigger', [c_int], ['mode'])
dllFunc('SetFastKinetics', [c_int, c_int, c_float, c_int, c_int, c_int],
                           ['exposedRows', 'seriesLength', 'time', 'mode',
                            'hbin', 'vbin'])
dllFunc('SetFastKineticsEx', [c_int, c_int, c_float, c_int, c_int, c_int, c_int],
                             ['exposedRows', 'seriesLength', 'time', 'mode',
                              'hbin', 'vbin', 'offset'])
dllFunc('SetFilterMode', [c_int], ['mode'])
# #'SetFilterParameters(int width, float sensitivity, int range, float accept, int smooth, int noise)
dllFunc('SetFKVShiftSpeed', [c_int], ['index'])
# #'SetFPDP(int state)
dllFunc('SetFrameTransferMode', [c_int], ['mode'])
# SetFrontEndEvent(HANDLE driverEvent)
# #'SetFullImage(int hbin, int vbin)
dllFunc('SetFVBHBin', [c_int], ['bin'])
# #'SetGain(int gain)
dllFunc('SetGate', [c_float, c_float, c_float],
                   ['delay', 'width', 'stepRenamed'])
dllFunc('SetGateMode',[c_int], ['gatemode'])
dllFunc('SetHighCapacity', [c_int], ['state'])
# #'SetHorizontalSpeed(int index)
dllFunc('SetHSSpeed', [c_int, c_int], ['typ', 'index'])
dllFunc('SetImage', [c_int, c_int, c_int, c_int, c_int, c_int],
                    ['bnin', 'vbin', 'hstar', 'hend', 'vstart', 'vend'])
dllFunc('SetImageFlip', [c_int, c_int],['iHFlip', 'iVFlip'])
dllFunc('SetImageRotate', [c_int], ['iRotate'])
# SetIsolatedCropMode(int active, int cropheight, int cropwidth, int vbin, int hbin)
# SetKineticCycleTime(float time)
# SetMCPGain(int gain)
# SetMCPGating(int gating)
# #'SetMessageWindow(HWND wnd)' # reser)
# SetMetaData(int state)
# SetMultiTrack(int number, int height, int offset, int * bottom, int * gap)
# SetMultiTrackHBin(int bin)
# SetMultiTrackHRange(int iStart, int iEnd)
# #'SetMultiTrackScan(int trackHeight, int numberTracks, int iSIHStart, int iSIHEnd, int trackHBinning, int trackVBinning, int trackGap, int trackOffset, int trackSkip, int numberSubFrames)
# #'SetNextAddress(at_32 * data, long lowAdd, long highAdd, long length, long physical)
# #'SetNextAddress16(at_32 * data, long lowAdd, long highAdd, long length, long physical)
# SetNumberAccumulations(int number)
# SetNumberKinetics(int number)
# SetNumberPrescans(int iNumber)
# SetOutputAmplifier(int typ)
# SetOverlapMode(int mode)
# SetPCIMode(int mode, int value)
# SetPhotonCounting(int state)
# SetPhotonCountingThreshold(long min, long max)
# SetPhosphorEvent(HANDLE driverEvent)
# SetPhotonCountingDivisions(at_u32 noOfDivisions, at_32 * divisions)
# #'SetPixelMode(int bitdepth, int colormode)
# SetPreAmpGain(int index)
# SetDualExposureTimes(float expTime1, float expTime2)
# SetDualExposureMode(int mode)
# SetRandomTracks(int numTracks, int * areas)
# SetReadMode(int mode)
# #'SetRegisterDump(int mode)
# SetRingExposureTimes(int numTimes, float * times)
# SetSaturationEvent(HANDLE saturationEvent)
# SetShutter(int typ, int mode, int closingtime, int openingtime)
# SetShutterEx(int typ, int mode, int closingtime, int openingtime, int extmode)
# #'SetShutters(int typ, int mode, int closingtime, int openingtime, int exttype, int extmode, int dummy1, int dummy2)
# SetSifComment(char * comment)
# SetSingleTrack(int centre, int height)
# SetSingleTrackHBin(int bin)
# SetSpool(int active, int method, char * path, int framebuffersize)
# SetSpoolThreadCount(int count)
# #'SetStorageMode(long mode)
# SetTECEvent(HANDLE driverEvent)
# SetTemperature(int temperature)
# #'SetTemperatureEvent(HANDLE temperatureEvent)
# SetTriggerMode(int mode)
# SetTriggerInvert(int mode)
# GetTriggerLevelRange(float * minimum, float * maximum)
# SetTriggerLevel(float f_level)
# SetIODirection(int index, int iDirection)
# SetIOLevel(int index, int iLevel)
# #'SetUserEvent(HANDLE userEvent)
# #'SetUSGenomics(long width, long height)
# #'SetVerticalRowBuffer(int rows)
# #'SetVerticalSpeed(int index)
# #'SetVirtualChip(int state)
# SetVSAmplitude(int index)
# SetVSSpeed(int index)
# ShutDown(void)
# StartAcquisition(void)
# #'UnMapPhysicalAddress(void)
# WaitForAcquisition(void)
# WaitForAcquisitionByHandle(long cameraHandle)
# WaitForAcquisitionByHandleTimeOut(long cameraHandle, int iTimeOutMs)
# WaitForAcquisitionTimeOut(int iTimeOutMs)
# WhiteBalance(WORD * wRed, WORD * wGreen, WORD * wBlue, float * fRelR, float * fRelB, WhiteBalanceInfo * info)
# OA_Initialize(const char * const pcFilename, unsigned int uiFileNameLen)
# OA_EnableMode(const char * const pcModeName)
# OA_GetModeAcqParams(const char * const pcModeName, char * const pcListOfParams)
# OA_GetUserModeNames(char * pcListOfModes)
# OA_GetPreSetModeNames(char * pcListOfModes)
# OA_GetNumberOfUserModes(unsigned int * const puiNumberOfModes)
# OA_GetNumberOfPreSetModes(unsigned int * const puiNumberOfModes)
# OA_GetNumberOfAcqParams(const char * const pcModeName, unsigned int * const puiNumberOfParams)
# OA_AddMode(char * pcModeName, unsigned int uiModeNameLen, char * pcModeDescription, unsigned int uiModeDescriptionLen)
# OA_WriteToFile(const char * const pcFileName, unsigned int uiFileNameLen)
# OA_DeleteMode(const char * const pcModeName, unsigned int uiModeNameLen)
# OA_SetInt(const char * const pcModeName, const char * pcModeParam, const int iIntValue)
# OA_SetFloat(const char * const pcModeName, const char * pcModeParam, const float fFloatValue)
# OA_SetString(const char * const pcModeName, const char * pcModeParam, char * pcStringValue, const unsigned int uiStringLen)
# OA_GetInt(const char * const pcModeName, const char * const pcModeParam, int * iIntValue)
# OA_GetFloat(const char * const pcModeName, const char * const pcModeParam, float * fFloatValue)
# OA_GetString(const char * const pcModeName, const char * const pcModeParam, char * pcStringValue, const unsigned int uiStringLen)
# Filter_SetMode(unsigned int mode)
# Filter_GetMode(unsigned int * mode)
# Filter_SetThreshold(float threshold)
# Filter_GetThreshold(float * threshold)
# Filter_SetDataAveragingMode(int mode)
# Filter_GetDataAveragingMode(int * mode)
# Filter_SetAveragingFrameCount(int frames)
# Filter_GetAveragingFrameCount(int * frames)
# Filter_SetAveragingFactor(int averagingFactor)
# Filter_GetAveragingFactor(int * averagingFactor)
# PostProcessNoiseFilter(at_32 * pInputImage, at_32 * pOutputImage, int iOutputBufferSize, int iBaseline, int iMode, float fThreshold, int iHeight, int iWidth)
# PostProcessCountConvert(at_32 * pInputImage, at_32 * pOutputImage, int iOutputBufferSize, int iNumImages, int iBaseline, int iMode, int iEmGain, float fQE, float fSensitivity, int iHeight, int iWidth)
# PostProcessPhotonCounting(at_32 * pInputImage, at_32 * pOutputImage, int iOutputBufferSize, int iNumImages, int iNumframes, int iNumberOfThresholds, float * pfThreshold, int iHeight, int iWidth)
# #'PostProcessDataAveraging(at_32 * pInputImage, at_32 * pOutputImage, int iOutputBufferSize, int iNumImages, int iAveragingFilterMode, int iHeight, int iWidth, int iFrameCount, int iAveragingFactor)