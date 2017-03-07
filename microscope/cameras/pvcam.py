import ctypes
import platform

# base typedefs
#typedef unsigned short rs_bool;
rs_bool = ctypes.c_ushort
#typedef signed char    int8;
int8 = ctypes.c_byte
#typedef unsigned char  uns8;
uns8 = ctypes.c_ubyte
#typedef short          int16;
int16 = ctypes.c_short
#typedef unsigned short uns16;
uns16 = ctypes.c_ushort
#typedef int            int32;
int32 = ctypes.c_int32
#typedef unsigned int   uns32;
uns32 = ctypes.c_uint32
#typedef float          flt32;
flt32 = ctypes.c_float
#typedef double         flt64;
flt64 = ctypes.c_double
#typedef unsigned long long ulong64;
ulong64 = ctypes.c_ulonglong
#typedef signed long long long64;
long64 = ctypes.c_longlong
# enums
enumtype = ctypes.c_int32

# Maximum length of a camera name.
CAM_NAME_LEN = 32
# Maximum length of a post-processing parameter/feature name.
# Use MAX_PP_NAME_LEN instead.
PARAM_NAME_LEN = 32
# Maximum length of an error message.
ERROR_MSG_LEN = 255
# Maximum length of a sensor chip name.
CCD_NAME_LEN = 17
# Maximum length of a camera serial number string.
MAX_ALPHA_SER_NUM_LEN = 32
# Maximum length of a post-processing parameter/feature name.
MAX_PP_NAME_LEN = 32
# Maximum length of a system name.
MAX_SYSTEM_NAME_LEN = 32
# Maximum length of a vendor name.
MAX_VENDOR_NAME_LEN = 32
# Maximum length of a product name.
MAX_PRODUCT_NAME_LEN = 32
# Maximum length of a product name.
MAX_CAM_PART_NUM_LEN = 32
# Maximum length of a gain name.
MAX_GAIN_NAME_LEN = 32

# Data types

# GUID for #FRAME_INFO structure.
class PVCAM_FRAME_INFO_GUID(ctypes.Structure):
    _fields_ = [("f1", uns32),
                ("f2", uns16),
                ("f3", uns16),
                ("f4", uns8 * 8),]

# Structure used to uniquely identify frames in the camera.
class FRAME_INFO(ctypes.Structure):
    _fields_ = [("FrameInfoGUID", PVCAM_FRAME_INFO_GUID),
                ("hCam", int16),
                ("FrameNr", int32),
                ("TimeStamp", long64),
                ("ReadoutTime", int32),
                ("TimeStampBOF", long64),]


class smart_stream_type(ctypes.Structure):
    _fields_ = [("entries", uns16),
                ("params", uns32),]


class rgn_type(ctypes.Structure):
    _fields = [("s1", uns16),
               ("s2", uns16),
               ("sb", uns16),
               ("p1", uns16),
               ("p2", uns16),
               ("pbin", uns16),]


class io_struct(ctypes.Structure):
    pass

io_struct._fields_ = [("io_port", uns16),
                     ("io_type", uns32),
                     ("state", flt64),
                     ("next", ctypes.POINTER(io_struct))]


class io_list(ctypes.Structure):
    _fields_ = [
        ("pre_open", ctypes.POINTER(io_struct)),
        ("post_open", ctypes.POINTER(io_struct)),
        ("pre_flash", ctypes.POINTER(io_struct)),
        ("post_flash", ctypes.POINTER(io_struct)),
        ("pre_integrate", ctypes.POINTER(io_struct)),
        ("post_integrate", ctypes.POINTER(io_struct)),
        ("pre_readout", ctypes.POINTER(io_struct)),
        ("post_readout", ctypes.POINTER(io_struct)),
        ("pre_close", ctypes.POINTER(io_struct)),
        ("post_close", ctypes.POINTER(io_struct)),
    ]

class active_camera_type(ctypes.Structure):
    _fields_ = [
        ("shutter_close_delay", uns16),
        ("shutter_open_delay", uns16),
        ("rows", uns16),
        ("cols", uns16),
        ("prescan", uns16),
        ("postscan", uns16),
        ("premask", uns16),
        ("postmask", uns16),
        ("preflash", uns16),
        ("clear_count", uns16),
        ("preamp_delay", uns16),
        ("mpp_selectable", rs_bool),
        ("frame_selectable", rs_bool),
        ("do_clear", uns16),
        ("open_shutter", uns16),
        ("mpp_mode", rs_bool),
        ("frame_transfer", rs_bool),
        ("alt_mode", rs_bool),
        ("exp_res", uns32),
        ("io_hdr", ctypes.POINTER(io_list)),
    ]


class md_frame_header(ctypes.Structure):
    _fields_ = [
        ("signature", uns32),
        ("version", uns8 ),
        ("frameNr", uns32),
        ("roiCount", uns16),
        ("timestampBOF", uns32),
        ("timestampEOF", uns32),
        ("timestampResNs", uns32),
        ("exposureTime", uns32),
        ("exposureTimeResN", uns32),
        ("roiTimestampResN", uns32),
        ("bitDepth", uns8),
        ("colorMask", uns8),
        ("flags", uns8),
        ("extendedMdSize", uns16),
        ("_reserved", uns8*8),]


class md_frame_roi_header(ctypes.Structure):
    _fields_ = [
        ("roiNr", uns16),
        ("timestampBOR", uns32),
        ("timestampEOR", uns32),
        ("roi", rgn_type),
        ("flags", uns8),
        ("extendedMdSize", uns16),
        ("_reserved", uns8*7),
    ]


PL_MD_EXT_TAGS_MAX_SUPPORTED = 255

class md_ext_item_info(ctypes.Structure):
    _fields_ = [
        ("tag", uns16),
        ("size", uns16),
        ("name", ctypes.c_char_p),
    ]

class md_ext_item(ctypes.Structure):
    _fields_ = [
        ("tagInfo", ctypes.POINTER(md_ext_item_info)), #
        ("value", ctypes.c_void_p)
    ]


class md_ext_item_collection(ctypes.Structure):
    _fields_ = [
        ("list", md_ext_item*PL_MD_EXT_TAGS_MAX_SUPPORTED),
        ("map", ctypes.POINTER(md_ext_item)*PL_MD_EXT_TAGS_MAX_SUPPORTED),
        ("count", uns16),
    ]

class md_frame_roi(ctypes.Structure):
    _fields_ = [
        ("header", ctypes.POINTER(md_frame_roi_header)),
        ("data", ctypes.c_void_p),
        ("dataSize", uns32),
        ("extMdData", ctypes.c_void_p),
        ("extMdDataSize", uns16),
    ]

class md_frame(ctypes.Structure):
    _fields_ = [
        ("header", ctypes.POINTER(md_frame_header)),
        ("extMdData", ctypes.c_void_p),
        ("extMdDataSize", uns16),
        ("impliedRoi", rgn_type),
        ("roiArray", ctypes.POINTER(md_frame_roi)),
        ("roiCapacity", uns16),
        ("roiCount", uns16),
    ]

arch, plat = platform.architecture()

if plat.startswith('Windows'):
    if arch == '32bit':
        _lib = ctypes.WinDLL('pvcam32')
    else:
        _lib = ctypes.WinDLL('pvcam64')
else:
    _lib = ctypes.CDLL('pvcam.so')



# Data type definitions
TYPE_INT16 = 1
TYPE_INT32 = 2
TYPE_FLT64 = 4
TYPE_UNS8 = 5
TYPE_UNS16 = 6
TYPE_UNS32 = 7
TYPE_UNS64 = 8
TYPE_ENUM = 9
TYPE_BOOLEAN = 11
TYPE_INT8 = 12
TYPE_CHAR_PTR = 13
TYPE_VOID_PTR = 14
TYPE_VOID_PTR_PTR = 15
TYPE_INT64 = 16
TYPE_SMART_STREAM_TYPE = 17
TYPE_SMART_STREAM_TYPE_PTR = 18
TYPE_FLT32 = 19

CLASS0 = 0 # Camera Communications
CLASS2 = 2 # Configuration/Setup
CLASS3 = 3 # Data Acuisition

### Functions ###
STRING = ctypes.c_char_p

# classes so that we do some magic and automatically add byrefs etc ... can classify outputs
class _meta(object):
    pass


class OUTPUT(_meta):
    def __init__(self, val):
        self.type = val
        self.val = ctypes.POINTER(val)

    def get_var(self, buf_len=0):
        v = self.type()
        return v, ctypes.byref(v)


class _OUTSTRING(OUTPUT):
    def __init__(self):
        self.val = STRING

    def get_var(self, buf_len):
        v = ctypes.create_string_buffer(buf_len)
        return v, v


OUTSTRING = _OUTSTRING()


def stripMeta(val):
    if isinstance(val, _meta):
        return val.val
    else:
        return val


CALLBACK = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)


class dllFunction(object):
    def __init__(self, name, args=[], argnames=[], buf_len=-1, lib=_lib):
        self.f = getattr(lib, name)
        self.f.restype = rs_bool
        self.f.argtypes = [stripMeta(a) for a in args]

        self.fargs = args
        self.fargnames = argnames
        self.name = name

        self.inp = [not isinstance(a, OUTPUT) for a in args]
        self.in_args = [a for a in args if not isinstance(a, OUTPUT)]
        self.out_args = [a for a in args if isinstance(a, OUTPUT)]

        self.buf_len = buf_len

        docstring = name + '\n\nArguments:\n===========\n'
        for i in range(len(args)):
            an = ''
            if i < len(argnames):
                an = argnames[i]
            docstring += '\t%s\t%s\n' % (args[i], an)

        self.f.__doc__ = docstring

    def __call__(self, *args):
        ars = []
        i = 0
        ret = []

        if self.buf_len >= 0:
            bs = self.buf_len
        else:
            bs = 255

        for j in range(len(self.inp)):
            if self.inp[j]:  # an input
                ars.append(args[i])
                i += 1
            else:  # an output
                r, ar = self.fargs[j].get_var(bs)
                ars.append(ar)
                ret.append(r)
                # print r, r._type_

        # print ars
        res = self.f(*ars)
        # print res

        if not res:
            err_code = _lib.pl_error_code()
            err_msg = ctypes.create_string_buffer(ERROR_MSG_LEN)
            _lib.pl_error_message(err_code, err_msg)

            raise Exception('pvcam error %d: %s' % (err_code, err_msg.value))

        if len(ret) == 0:
            return None
        if len(ret) == 1:
            return ret[0]
        else:
            return ret


def dllFunc(name, args=[], argnames=[], buf_len=0):
    f = dllFunction(name, args, argnames, buf_len=buf_len)
    globals()[name[3:]] = f



# Class 0 functions - library
dllFunc('pl_pvcam_get_ver', [OUTPUT(uns16)])
dllFunc('pl_pvcam_init')
dllFunc('pl_pvcam_uninit')
# Class 0 functions - camera
dllFunc('pl_cam_close', [int16,])
dllFunc('pl_cam_get_name', [int16, OUTSTRING], buf_len=CAM_NAME_LEN)
dllFunc('pl_cam_get_total', [OUTPUT(int16),])
dllFunc('pl_cam_open', [STRING, OUTPUT(int16), int16])
dllFunc('pl_cam_register_callback', [int16, enumtype, ctypes.c_void_p])

dllFunc('pl_error_code')

"""
pl_cam_register_callback_ex(int16
hcam, int32
callback_event,
void * callback, void * context);

pl_cam_register_callback_ex2(int16
hcam, int32
callback_event,
void * callback);

pl_cam_register_callback_ex3(int16
hcam, int32
callback_event,
void * callback, void * context);

pl_cam_deregister_callback(int16
hcam, int32
callback_event);
"""

# DEVICE DRIVER PARAMETERS
#define PARAM_DD_INFO_LENGTH        ((CLASS0<<16) + (TYPE_INT16<<24) + 1)
#define PARAM_DD_VERSION            ((CLASS0<<16) + (TYPE_UNS16<<24) + 2)
#define PARAM_DD_RETRIES            ((CLASS0<<16) + (TYPE_UNS16<<24) + 3)
#define PARAM_DD_TIMEOUT            ((CLASS0<<16) + (TYPE_UNS16<<24) + 4)
#define PARAM_DD_INFO               ((CLASS0<<16) + (TYPE_CHAR_PTR<<24) + 5)
"""
/* CONFIGURATION AND SETUP PARAMETERS */

/* Sensor skip parameters */

/** ADC offset setting. */
#define PARAM_ADC_OFFSET            ((CLASS2<<16) + (TYPE_INT16<<24)     + 195)
/** Sensor chip name. */
#define PARAM_CHIP_NAME             ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 129)
/** Camera system name. */
#define PARAM_SYSTEM_NAME           ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 130)
/** Camera vendor name. */
#define PARAM_VENDOR_NAME           ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 131)
/** Camera product name. */
#define PARAM_PRODUCT_NAME          ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 132)
/** Camera part number. */
#define PARAM_CAMERA_PART_NUMBER    ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 133)

#define PARAM_COOLING_MODE          ((CLASS2<<16) + (TYPE_ENUM<<24)      + 214)
#define PARAM_PREAMP_DELAY          ((CLASS2<<16) + (TYPE_UNS16<<24)     + 502)
#define PARAM_COLOR_MODE            ((CLASS2<<16) + (TYPE_ENUM<<24)      + 504)
#define PARAM_MPP_CAPABLE           ((CLASS2<<16) + (TYPE_ENUM<<24)      + 224)
#define PARAM_PREAMP_OFF_CONTROL    ((CLASS2<<16) + (TYPE_UNS32<<24)     + 507)
#pragma message("PARAM_SERIAL_NUM has been removed because it is not supported.  Compilation will fail with apps that use this parameter, but execution will continue to work until the next release (at that point, execution will start to throw an error).  Please contact support with any concerns.")

/* Sensor dimensions and physical characteristics */

/* Pre and post dummies of sensor. */
#define PARAM_PREMASK               ((CLASS2<<16) + (TYPE_UNS16<<24)     +  53)
#define PARAM_PRESCAN               ((CLASS2<<16) + (TYPE_UNS16<<24)     +  55)
#define PARAM_POSTMASK              ((CLASS2<<16) + (TYPE_UNS16<<24)     +  54)
#define PARAM_POSTSCAN              ((CLASS2<<16) + (TYPE_UNS16<<24)     +  56)
#define PARAM_PIX_PAR_DIST          ((CLASS2<<16) + (TYPE_UNS16<<24)     + 500)
#define PARAM_PIX_PAR_SIZE          ((CLASS2<<16) + (TYPE_UNS16<<24)     +  63)
#define PARAM_PIX_SER_DIST          ((CLASS2<<16) + (TYPE_UNS16<<24)     + 501)
#define PARAM_PIX_SER_SIZE          ((CLASS2<<16) + (TYPE_UNS16<<24)     +  62)
#define PARAM_SUMMING_WELL          ((CLASS2<<16) + (TYPE_BOOLEAN<<24)   + 505)
#define PARAM_FWELL_CAPACITY        ((CLASS2<<16) + (TYPE_UNS32<<24)     + 506)
/** Y dimension of active area of sensor chip. */
#define PARAM_PAR_SIZE              ((CLASS2<<16) + (TYPE_UNS16<<24)     +  57)
/** X dimension of active area of sensor chip. */
#define PARAM_SER_SIZE              ((CLASS2<<16) + (TYPE_UNS16<<24)     +  58)
#define PARAM_ACCUM_CAPABLE         ((CLASS2<<16) + (TYPE_BOOLEAN<<24)   + 538)
#define PARAM_FLASH_DWNLD_CAPABLE   ((CLASS2<<16) + (TYPE_BOOLEAN<<24)   + 539)

/* General parameters */

/** Readout time of current ROI in milliseconds. */
#define PARAM_READOUT_TIME          ((CLASS2<<16) + (TYPE_FLT64<<24)     + 179)

/* CAMERA PARAMETERS */
#define PARAM_CLEAR_CYCLES          ((CLASS2<<16) + (TYPE_UNS16<<24)     +  97)
#define PARAM_CLEAR_MODE            ((CLASS2<<16) + (TYPE_ENUM<<24)      + 523)
#define PARAM_FRAME_CAPABLE         ((CLASS2<<16) + (TYPE_BOOLEAN<<24)   + 509)
#define PARAM_PMODE                 ((CLASS2<<16) + (TYPE_ENUM <<24)     + 524)
#pragma message("PARAM_CCS_STATUS has been removed because it is not supported.  Compilation will fail with apps that use this parameter, but execution will continue to work until the next release (at that point, execution will start to throw an error).  Please contact support with any concerns.")

/* These are the temperature parameters for the detector. */
#define PARAM_TEMP                  ((CLASS2<<16) + (TYPE_INT16<<24)     + 525)
#define PARAM_TEMP_SETPOINT         ((CLASS2<<16) + (TYPE_INT16<<24)     + 526)

/* These are the parameters used for firmware version retrieval. */
#define PARAM_CAM_FW_VERSION        ((CLASS2<<16) + (TYPE_UNS16<<24)     + 532)
#define PARAM_HEAD_SER_NUM_ALPHA    ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 533)
#define PARAM_PCI_FW_VERSION        ((CLASS2<<16) + (TYPE_UNS16<<24)     + 534)
#pragma message("PARAM_CAM_FW_FULL_VERSION has been removed because it is not supported.  Compilation will fail with apps that use this parameter, but execution will continue to work until the next release (at that point, execution will start to throw an error).  Please contact support with any concerns.")
#define PARAM_FAN_SPEED_SETPOINT    ((CLASS2<<16) + (TYPE_ENUM<<24)      + 710)

/* Exposure mode, timed strobed etc, etc. */
#define PARAM_EXPOSURE_MODE         ((CLASS2<<16) + (TYPE_ENUM<<24)      + 535)
#define PARAM_EXPOSE_OUT_MODE       ((CLASS2<<16) + (TYPE_ENUM<<24)      + 560)

/* SPEED TABLE PARAMETERS */
#define PARAM_BIT_DEPTH             ((CLASS2<<16) + (TYPE_INT16<<24)     + 511)
#define PARAM_GAIN_INDEX            ((CLASS2<<16) + (TYPE_INT16<<24)     + 512)
#define PARAM_SPDTAB_INDEX          ((CLASS2<<16) + (TYPE_INT16<<24)     + 513)
#define PARAM_GAIN_NAME             ((CLASS2<<16) + (TYPE_CHAR_PTR<<24)  + 514)
#define PARAM_READOUT_PORT          ((CLASS2<<16) + (TYPE_ENUM<<24)      + 247)
#define PARAM_PIX_TIME              ((CLASS2<<16) + (TYPE_UNS16<<24)     + 516)

/* SHUTTER PARAMETERS */
#define PARAM_SHTR_CLOSE_DELAY      ((CLASS2<<16) + (TYPE_UNS16<<24)     + 519)
#define PARAM_SHTR_OPEN_DELAY       ((CLASS2<<16) + (TYPE_UNS16<<24)     + 520)
#define PARAM_SHTR_OPEN_MODE        ((CLASS2<<16) + (TYPE_ENUM <<24)     + 521)
#define PARAM_SHTR_STATUS           ((CLASS2<<16) + (TYPE_ENUM <<24)     + 522)

/* I/O PARAMETERS */
#define PARAM_IO_ADDR               ((CLASS2<<16) + (TYPE_UNS16<<24)     + 527)
#define PARAM_IO_TYPE               ((CLASS2<<16) + (TYPE_ENUM<<24)      + 528)
#define PARAM_IO_DIRECTION          ((CLASS2<<16) + (TYPE_ENUM<<24)      + 529)
#define PARAM_IO_STATE              ((CLASS2<<16) + (TYPE_FLT64<<24)     + 530)
#define PARAM_IO_BITDEPTH           ((CLASS2<<16) + (TYPE_UNS16<<24)     + 531)

/* GAIN MULTIPLIER PARAMETERS */
#define PARAM_GAIN_MULT_FACTOR      ((CLASS2<<16) + (TYPE_UNS16<<24)     + 537)
#define PARAM_GAIN_MULT_ENABLE      ((CLASS2<<16) + (TYPE_BOOLEAN<<24)   + 541)

/* POST PROCESSING PARAMETERS */
#define PARAM_PP_FEAT_NAME          ((CLASS2<<16) + (TYPE_CHAR_PTR<<24) +  542)
#define PARAM_PP_INDEX              ((CLASS2<<16) + (TYPE_INT16<<24)    +  543)
#define PARAM_ACTUAL_GAIN           ((CLASS2<<16) + (TYPE_UNS16<<24)     + 544)
#define PARAM_PP_PARAM_INDEX        ((CLASS2<<16) + (TYPE_INT16<<24)    +  545)
#define PARAM_PP_PARAM_NAME         ((CLASS2<<16) + (TYPE_CHAR_PTR<<24) +  546)
#define PARAM_PP_PARAM              ((CLASS2<<16) + (TYPE_UNS32<<24)    +  547)
#define PARAM_READ_NOISE            ((CLASS2<<16) + (TYPE_UNS16<<24)     + 548)
#define PARAM_PP_FEAT_ID            ((CLASS2<<16) + (TYPE_UNS16<<24)    +  549)
#define PARAM_PP_PARAM_ID           ((CLASS2<<16) + (TYPE_UNS16<<24)    +  550)

/* S.M.A.R.T. STREAMING PARAMETERS */
#define PARAM_SMART_STREAM_MODE_ENABLED     ((CLASS2<<16) + (TYPE_BOOLEAN<<24)  +  700)
#define PARAM_SMART_STREAM_MODE             ((CLASS2<<16) + (TYPE_UNS16<<24)    +  701)
#define PARAM_SMART_STREAM_EXP_PARAMS       ((CLASS2<<16) + (TYPE_VOID_PTR<<24) +  702)
#define PARAM_SMART_STREAM_DLY_PARAMS       ((CLASS2<<16) + (TYPE_VOID_PTR<<24) +  703)

/* DATA AQUISITION PARAMETERS */

/* ACQUISITION PARAMETERS */
#define PARAM_EXP_TIME              ((CLASS3<<16) + (TYPE_UNS16<<24)     +   1)
#define PARAM_EXP_RES               ((CLASS3<<16) + (TYPE_ENUM<<24)      +   2)
#pragma message("PARAM_EXP_MIN_TIME has been removed because it is not supported.  Compilation will fail with apps that use this parameter, but execution will continue to work until the next release (at that point, execution will start to throw an error).  Please contact support with any concerns.")
#define PARAM_EXP_RES_INDEX         ((CLASS3<<16) + (TYPE_UNS16<<24)     +   4)
#define PARAM_EXPOSURE_TIME         ((CLASS3<<16) + (TYPE_UNS64<<24)     +   8)

/* PARAMETERS FOR  BEGIN and END of FRAME Interrupts */
#define PARAM_BOF_EOF_ENABLE        ((CLASS3<<16) + (TYPE_ENUM<<24)      +   5)
#define PARAM_BOF_EOF_COUNT         ((CLASS3<<16) + (TYPE_UNS32<<24)     +   6)
#define PARAM_BOF_EOF_CLR           ((CLASS3<<16) + (TYPE_BOOLEAN<<24)   +   7)

/* Test to see if hardware/software can perform circular buffer */
#define PARAM_CIRC_BUFFER           ((CLASS3<<16) + (TYPE_BOOLEAN<<24)   + 299)
#define PARAM_FRAME_BUFFER_SIZE     ((CLASS3<<16) + (TYPE_UNS64<<24)     + 300)

/* Supported binning reported by camera */
#define PARAM_BINNING_SER           ((CLASS3<<16) + (TYPE_ENUM<<24)      + 165)
#define PARAM_BINNING_PAR           ((CLASS3<<16) + (TYPE_ENUM<<24)      + 166)

#pragma message("PARAM_CURRENT_PVTIME has been removed because it is not supported.  Compilation will fail with apps that use this parameter, but execution will continue to work until the next release (at that point, execution will start to throw an error).  Please contact support with any concerns.")

/* Parameters related to multiple ROIs and Centroids */
#define PARAM_METADATA_ENABLED      ((CLASS3<<16) + (TYPE_BOOLEAN<<24)   + 168)
#define PARAM_ROI_COUNT             ((CLASS3<<16) + (TYPE_UNS16  <<24)   + 169)
#define PARAM_CENTROIDS_ENABLED     ((CLASS3<<16) + (TYPE_BOOLEAN<<24)   + 170)
#define PARAM_CENTROIDS_RADIUS      ((CLASS3<<16) + (TYPE_UNS16  <<24)   + 171)
#define PARAM_CENTROIDS_COUNT       ((CLASS3<<16) + (TYPE_UNS16  <<24)   + 172)

/* Parameters related to triggering table */
#define PARAM_TRIGTAB_SIGNAL        ((CLASS3<<16) + (TYPE_ENUM<<24)      + 180)
#define PARAM_LAST_MUXED_SIGNAL     ((CLASS3<<16) + (TYPE_UNS8<<24)      + 181)

/******************************************************************************/
/* End of parameter ID definitions.                                           */
/******************************************************************************/

/******************************************************************************/
/* Start of function prototypes.                                              */
/******************************************************************************/

#ifndef PV_EMBEDDED

#ifdef PV_C_PLUS_PLUS
extern "C"
{
#endif

    /*****************************************************************************/
    /*****************************************************************************/
    /*                                                                           */
    /*                 Camera Communications Function Prototypes                 */
    /*                                                                           */
    /*****************************************************************************/
    /*****************************************************************************/

    /*****************************************************************************/
    /* rs_bool (RETURN)  All functions that return a rs_bool return TRUE for     */
    /*                   success and FALSE for failure.  If a failure occurs     */
    /*                   pl_error_code() and pl_error_message() can be used to   */
    /*                   determine the cause.                                    */
    /*****************************************************************************/

    /*****************************************************************************/
    /* pvcam_version     Version number of the PVCAM library                     */
    /*                     16 bits = MMMMMMMMrrrrTTTT where MMMMMMMM = Major #,  */
    /*                     rrrr = Minor #, and TTTT = Trivial #                  */
    /*****************************************************************************/

    rs_bool PV_DECL pl_pvcam_get_ver (uns16* pvcam_version);
    rs_bool PV_DECL pl_pvcam_init (void);
    rs_bool PV_DECL pl_pvcam_uninit (void);

    /*****************************************************************************/
    /* hcam              Camera handle returned from pl_cam_open()               */
    /* cam_num           Camera number Range: 0 through (totl_cams-1)            */
    /* camera_name       Text name assigned to a camera (with RSConfig)          */
    /* totl_cams         Total number of cameras in the system                   */
    /* o_mode            Mode to open the camera in (must be OPEN_EXCLUSIVE)     */
    /*****************************************************************************/

    /**
    @addtogroup grp_pm_deprecated_functions
    @{
    */

    /** @} */
    rs_bool PV_DECL pl_cam_close (int16 hcam);
    rs_bool PV_DECL pl_cam_get_name (int16 cam_num, char* camera_name);
    rs_bool PV_DECL pl_cam_get_total (int16* totl_cams);
    rs_bool PV_DECL pl_cam_open (char* camera_name, int16* hcam, int16 o_mode);

    /*****************************************************************************/
    /* callback_event    Callback event to register for (see PL_CALLBACK_EVENT)  */
    /* callback          Callback function pointer                               */
    /* contex            Pointer to custom user contex                           */
    /*****************************************************************************/

    rs_bool PV_DECL pl_cam_register_callback (int16 hcam, int32 callback_event,
                                              void* callback);
    rs_bool PV_DECL pl_cam_register_callback_ex (int16 hcam, int32 callback_event,
                                                 void* callback, void* context);
    rs_bool PV_DECL pl_cam_register_callback_ex2 (int16 hcam, int32 callback_event,
                                                 void* callback);
    rs_bool PV_DECL pl_cam_register_callback_ex3 (int16 hcam, int32 callback_event,
                                                 void* callback, void* context);
    rs_bool PV_DECL pl_cam_deregister_callback (int16 hcam, int32 callback_event);

    /*****************************************************************************/
    /*****************************************************************************/
    /*                                                                           */
    /*                     Error Reporting Function Prototypes                   */
    /*                                                                           */
    /*****************************************************************************/
    /*****************************************************************************/

    /*****************************************************************************/
    /* int16 (RETURN)    pl_error_code(void) returns the error code of the last  */
    /*                   pl_ function call.                                      */
    /* err_code          Unique ID of the error: returned from pl_error_code()   */
    /* msg               Text description of err_code.                           */
    /*****************************************************************************/

    int16   PV_DECL pl_error_code (void);
    rs_bool PV_DECL pl_error_message (int16 err_code, char* msg);


    /*****************************************************************************/
    /*****************************************************************************/
    /*                                                                           */
    /*                   Configuration/Setup Function Prototypes                 */
    /*                                                                           */
    /*****************************************************************************/
    /*****************************************************************************/

    /*****************************************************************************/
    /* param_id          ID of the parameter to get or set (PARAM_...)           */
    /* param_attribute   Attribute of the parameter to get (ATTR_...)            */
    /* param_value       Value to get or set                                     */
    /* index             Index of enumeration Range: 0 through N-1 ... where N   */
    /*                     is retrieved with get_param(...,ATTR_COUNT,...)       */
    /* value             Numerical value of enumeration                          */
    /* desc              Text description of enumeration                         */
    /* length            Length of text description of enumeration               */
    /*****************************************************************************/

    rs_bool PV_DECL pl_get_param (int16 hcam, uns32 param_id,
                                  int16 param_attribute, void* param_value);
    rs_bool PV_DECL pl_set_param (int16 hcam, uns32 param_id,
                                  void* param_value);
    rs_bool PV_DECL pl_get_enum_param (int16 hcam, uns32 param_id, uns32 index,
                                       int32* value, char* desc,
                                       uns32 length);
    rs_bool PV_DECL pl_enum_str_length (int16 hcam, uns32 param_id, uns32 index,
                                        uns32* length);
    rs_bool PV_DECL pl_pp_reset (int16 hcam);

    rs_bool PV_DECL pl_create_smart_stream_struct(smart_stream_type** array,
                                                  uns16 entries);

    rs_bool PV_DECL pl_release_smart_stream_struct(smart_stream_type** array);

    rs_bool PV_DECL pl_create_frame_info_struct(FRAME_INFO** new_frame);

    rs_bool PV_DECL pl_release_frame_info_struct(FRAME_INFO* frame_to_delete);

    /*****************************************************************************/
    /*****************************************************************************/
    /*                                                                           */
    /*                   Data Acquisition Function Prototypes                    */
    /*                                                                           */
    /*****************************************************************************/
    /*****************************************************************************/

    /*****************************************************************************/
    /* pixel_stream      Buffer to hold image(s)                                 */
    /* byte_cnt          Size of bufer to hold images (in bytes)                 */
    /* exp_total         Total number of exposures to take                       */
    /* rgn_total         Total number of regions defined for each image          */
    /* rgn_array         Array of regions (must be rgn_total in size)            */
    /*                     s1    starting pixel in the serial register           */
    /*                     s2    ending pixel in the serial register             */
    /*                     sbin  serial binning for this region                  */
    /*                     p1    starting pixel in the parallel register         */
    /*                     p2    ending pixel in the parallel register           */
    /*                     pbin  parallel binning for this region                */
    /* exp_mode          Mode for capture (TIMED_MODE, STROBED_MODE, ...)        */
    /* exposure_time     Time to expose in selected exposure resolution          */
    /*                     Default is milliseconds (see PARAM_EXP_RES)           */
    /* exp_bytes         Value returned from PVCAM specifying the required       */
    /*                     number of bytes to allocate for the capture           */
    /* buffer_mode       Circular buffer mode (CIRC_OVERWRITE,...)               */
    /* size              Size of continuous capture pixel_stream                 */
    /*                     (must be a multiple of byte_cnt)                      */
    /* status            Status of the current capture (EXPOSURE_IN_PROGRESS,...)*/
    /* bytes_arrived     Number of bytes that have arrived.  For continuous      */
    /*                     mode this is the number of bytes that have arrived    */
    /*                     this time through the buffer.                         */
    /* buffer_cnt        Number of times through the buffer (continuous mode)    */
    /* frame             Pointer to the requested image                          */
    /* cam_state         State to set the camera in (CCS_NO_CHANGE,...)          */
    /* hbuf              Standard image buffer                                   */
    /* exposure          Exposure # to unravel, 65535 for All, else exposure #   */
    /* array_list        Array of Pointers that will get the unraveled images    */
    /*                     in the same order as the regions.                     */
    /* tlimit            Time in milliseconds to wait for a transfer             */
    /*****************************************************************************/

    rs_bool PV_DECL pl_exp_setup_seq (int16 hcam, uns16 exp_total,
                                      uns16 rgn_total, const rgn_type* rgn_array,
                                      int16 exp_mode, uns32 exposure_time,
                                      uns32* exp_bytes);
    rs_bool PV_DECL pl_exp_start_seq (int16 hcam, void* pixel_stream);
    rs_bool PV_DECL pl_exp_setup_cont (int16 hcam, uns16 rgn_total,
                                       const rgn_type* rgn_array, int16 exp_mode,
                                       uns32 exposure_time, uns32* exp_bytes,
                                       int16 buffer_mode);
    rs_bool PV_DECL pl_exp_start_cont (int16 hcam, void* pixel_stream, uns32 size);
    rs_bool PV_DECL pl_exp_check_status (int16 hcam, int16* status, uns32* bytes_arrived);
    rs_bool PV_DECL pl_exp_check_cont_status (int16 hcam, int16* status,
                                              uns32* bytes_arrived, uns32* buffer_cnt);
    rs_bool PV_DECL pl_exp_check_cont_status_ex (int16 hcam, int16* status,
                                                 uns32* byte_cnt, uns32* buffer_cnt,
                                                 FRAME_INFO* pFrameInfo);
    rs_bool PV_DECL pl_exp_get_latest_frame (int16 hcam, void** frame);
    rs_bool PV_DECL pl_exp_get_latest_frame_ex (int16 hcam, void** frame,
                                                FRAME_INFO* pFrameInfo);
    rs_bool PV_DECL pl_exp_get_oldest_frame (int16 hcam, void** frame);
    rs_bool PV_DECL pl_exp_get_oldest_frame_ex (int16 hcam, void** frame,
                                                FRAME_INFO* pFrameInfo);
    rs_bool PV_DECL pl_exp_unlock_oldest_frame (int16 hcam);
    rs_bool PV_DECL pl_exp_stop_cont (int16 hcam, int16 cam_state);
    rs_bool PV_DECL pl_exp_abort (int16 hcam, int16 cam_state);
    rs_bool PV_DECL pl_exp_finish_seq (int16 hcam, void* pixel_stream, int16 hbuf);

    /*****************************************************************************/
    /* addr              Specifies which I/O address to control                  */
    /* state             Specifies the value to write to the register            */
    /* location          Specifies when to control the I/O (SCR_PRE_FLASH,...)   */
    /*****************************************************************************/
    rs_bool PV_DECL pl_io_script_control (int16 hcam, uns16 addr, flt64 state,
                                          uns32 location);
    rs_bool PV_DECL pl_io_clear_script_control (int16 hcam);

    /*****************************************************************************/
    /*****************************************************************************/
    /*                                                                           */
    /*                         Frame metadata functions                          */
    /*                                                                           */
    /*****************************************************************************/
    /*****************************************************************************/

    /**
    Decodes all the raw frame buffer metadata into a friendly structure.
    @param pDstFrame A pre-allocated helper structure that will be filled with
                     information from the given raw buffer.
    @param pSrcBuf A raw frame buffer as retrieved from PVCAM
    @param srcBufSize The size of the raw frame buffer
    @return #PV_FAIL in case of failure.
    */
    rs_bool PV_DECL pl_md_frame_decode (md_frame* pDstFrame, void* pSrcBuf, uns32 srcBufSize);

    /**
    Optional function that recomposes a multi-ROI frame into a displayable image buffer.
    Every ROI will be copied into its appropriate location in the provided buffer.
    Please note that the function will subtract the Implied ROI position from each ROI
    position which essentially moves the entire Implied ROI to a [0, 0] position.
    Use the Offset arguments to shift all ROIs back to desired positions if needed.
    If you use the Implied ROI position for offset arguments the frame will be recomposed
    as it appears on the full frame.
    The caller is responsible for black-filling the input buffer. Usually this function
    is called during live/preview mode where the destination buffer is re-used. If the
    ROIs do move during acquisition it is essential to black-fill the destination buffer
    before calling this function. This is not needed if the ROIs do not move.
    If the ROIs move during live mode it is also recommended to use the offset arguments
    and recompose the ROI to a full frame - with moving ROIs the implied ROI may change
    with each frame and this may cause undesired ROI "twitching" in the displayable image.

    @param pDstBuf An output buffer, the buffer must be at least the size of the implied
                   ROI that is calculated during the frame decoding process. The buffer
                   must be of type uns16. If offset is set the buffer must be large
                   enough to allow the entire implied ROI to be shifted.
    @param offX    Offset in the destination buffer, in pixels. If 0 the Implied
                   ROI will be shifted to position 0 in the target buffer.
                   Use (ImpliedRoi.s1 / ImplierRoi.sbin) as offset value to
                   disable the shift and keep the ROIs in their absolute positions.
    @param offY    Offset in the destination buffer, in pixels. If 0 the Implied
                   ROI will be shifted to position 0 in the target buffer.
                   Use (ImpliedRoi.p1 / ImplierRoi.pbin) as offset value to
                   disable the shift and keep the ROIs in their absolute positions.
    @param dstWidth  Width, in pixels of the destination image buffer. The buffer
                     must be large enough to hold the entire Implied ROI, including
                     the offsets (if used).
    @param dstHeight Height, in pixels of the destination image buffer.
    @param pSrcFrame A helper structure, previously decoded using the frame
                     decoding function.
    @return #PV_FAIL in case of failure.
    */
    rs_bool PV_DECL pl_md_frame_recompose (void* pDstBuf, uns16 offX, uns16 offY,
                                           uns16 dstWidth, uns16 dstHeight,
                                           md_frame* pSrcFrame);

    /**
    This method creates an empty md_frame structure for known number of ROIs.
    Use this method to prepare and pre-allocate one structure before starting
    continous acquisition. Once callback arrives fill the structure with
    pl_md_frame_decode() and display the metadata.
    Release the structure when not needed.
    @param pFrame a pointer to frame helper structure address where the structure
                  will be allocated.
    @param roiCount Number of ROIs the structure should be prepared for.
    @return #PV_FAIL in case of failure.
    */
    rs_bool PV_DECL pl_md_create_frame_struct_cont (md_frame** pFrame, uns16 roiCount);

    /**
    This method creates an empty md_frame structure from an existing buffer.
    Use this method when loading buffers from disk or when performance is not
    critical. Do not forget to release the structure when not needed.
    For continous acquisition where the number or ROIs is known it is recommended
    to use the other provided method to avoid frequent memory allocation.
    @param pFrame A pointer address where the newly created structure will be stored.
    @param pSrcBuf A raw frame data pointer as returned from the camera
    @param srcBufSize Size of the raw frame data buffer
    @return #PV_FAIL in case of failure
    */
    rs_bool PV_DECL pl_md_create_frame_struct (md_frame** pFrame, void* pSrcBuf,
                                               uns32 srcBufSize);

    /**
    Releases the md_frame struct
    @param pFrame a pointer to the previously allocated structure
    */
    rs_bool PV_DECL pl_md_release_frame_struct (md_frame* pFrame);

    /**
    Reads all the extended metadata from the given ext. metadata buffer.
    @param pOutput A pre-allocated structure that will be filled with metadata
    @param pExtMdPtr A pointer to the ext. MD buffer, this can be obtained from
                    the md_frame and md_frame_roi structures.
    @param extMdSize Size of the ext. MD buffer, also retrievable from the helper
                     structures.
    @return #PV_FAIL in case the metadata cannot be decoded.
    */
    rs_bool PV_DECL pl_md_read_extended (md_ext_item_collection* pOutput, void* pExtMdPtr,
                                         uns32 extMdSize);

#ifdef PV_C_PLUS_PLUS
};
#endif

#endif /* PV_EMBEDDED */

/******************************************************************************/
/* End of function prototypes.                                                */
/******************************************************************************/

#endif /* _PVCAM_H */
"""