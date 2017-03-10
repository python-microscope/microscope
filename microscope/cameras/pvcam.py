#!/usr/bin/python
# -*- coding: utf-8
#
# Copyright 2017 Mick Phillips (mick.phillips@gmail.com)
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
"""pvcam library wrapper.

This module exposes pvcam C library functions in python.
"""
import ctypes
import platform
import os
import re


_HEADER = 'pvcam.h'

# === Data types ===
# Base typedefs, from pvcam SDK master.h
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

# === Parse defines and enums from C header file. ===
fh = open(os.path.join(os.path.split(__file__)[0], _HEADER), 'r')
while True:
    line = fh.readline()
    if not line: break
    if any([re.match(pattern, line) for pattern in [
        r'^\s*\/\*.*', # /* comments
        r'^\s*#ifndef .*', # #ifndef lines
        r'^\s*#ifdef .*',  # #ifndef lines
        r'^\s*#if .*',  # #if lines
        r'^\s*#endif.*',  # #endif lines
        r'^\s*$', # blank lines
        ]]):
        continue
    # #define flag
    if re.match(r'^\s*#define\s+\w+\s?$', line):
       continue
    # #define name value
    match = re.match(r'^\s*#define\s*(\w+)\s+(\w+)\s+(\/\*)?', line)
    if match:
        name = match.groups()[0]
        value = eval(match.groups()[1])
        globals()[name] = value
        continue
    # #define name (expr)
    match = re.match(r'^\s*#define\s*(\w+)\s+(\(.*\))', line) # #define name (expr)
    if match:
        name = match.groups()[0]
        value = eval(match.groups()[1])
        globals()[name] = value
        continue
    # #typedef enum
    match = re.match(r'^\s*typedef enum\s*(\w+)?', line)
    if match:
        tag = match.groups()[0]
        globals()[tag] = {}
        line = fh.readline()
        while not re.match(r'^.*{', line):
            line = fh.readline()
        count = 0
        while not re.match(r'^.*}', line):
            match = re.match(r'^(\s*{\s*)?\s*(\w+)(\s*=\s*(\w+))?', line)
            line = fh.readline()
            if not match:
                continue
            null, name, null, value = match.groups()
            if not value:
                # No value assigned in header file.
                value = count
                count += 1
            else:
                value = eval(value)
            globals()[name] = value
            globals()[tag][value] = name
        # Get the enum name.
        match = re.match(r'^.*}\s*((\w+)?;)?', line)
        name = match.groups()[-1]
        if not name:
            line = fh.readline()
            match = re.match(r'^\s*(\w+)?;?', line)
            if not match.groups()[0]:
                raise Exception('Error parsing %s: enum name not found for tag %s.'
                                  % (_HEADER, tag))
            else:
                name = match.groups()[0]
        if name != tag:
            globals()[name] = globals()[tag]
fh.close()

# === C structures ===
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

    def __call__(self, *args, **kwargs):
        ars = []
        i = 0
        ret = []

        # pl_get_param buffer length depends on the parameter being fetched, so
        # use kwargs to pass buffer length.
        if 'buf_len' in kwargs:
            bs = kwargs['buf_len']
        elif self.name == 'pl_get_enum_param':
            # last argument is buffer length
            bs = args[-1]
        elif self.buf_len >= 0:
            bs = self.buf_len
        else:
            bs = 256
        if isinstance(bs, ctypes._SimpleCData):
            bs = bs.value


        for j in range(len(self.inp)):
            if self.inp[j]:  # an input
                if self.f.argtypes[j] is CALLBACK and not isinstance(args[i], CALLBACK):
                    ars.append(CALLBACK(args[i]))
                else:
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
    globals()[name[2:]] = f


# Class 0 functions - library
dllFunc('pl_pvcam_get_ver', [OUTPUT(uns16)], ['version'])
dllFunc('pl_pvcam_init')
dllFunc('pl_pvcam_uninit')
# Class 0 functions - camera
dllFunc('pl_cam_close', [int16], ['hcam'])
dllFunc('pl_cam_get_name',
        [int16, OUTSTRING],
        ['can_num', 'cam_name'], buf_len=CAM_NAME_LEN)
dllFunc('pl_cam_get_total', [OUTPUT(int16),], ['total_cams',])
dllFunc('pl_cam_open',
        [STRING, OUTPUT(int16), int16],
        ['cam_name', 'hcam', 'o_mode'])
dllFunc('pl_cam_register_callback',
        [int16, int32, CALLBACK],
        ['hcam', 'event', 'Callback'])
dllFunc('pl_cam_register_callback_ex',
        [int16, int32, CALLBACK, ctypes.c_void_p],
        ['hcam', 'event', 'Callback', 'Context'])
dllFunc('pl_cam_register_callback_ex2',
        [int16, int32, CALLBACK],
        ['hcam', 'event', 'Callback'])
dllFunc('pl_cam_register_callback_ex3',
        [int16, int32, CALLBACK, ctypes.c_void_p],
        ['hcam', 'event', 'Callback', 'Context'])
dllFunc('pl_cam_deregister_callback',
        [int16, ctypes.c_void_p],
        ['hcam', 'event'])
# Class 1 functions - error handling. Handled in dllFunction.
# Class 2 functions - configuration/setup.
dllFunc('pl_get_param', [int16, uns32, int16, OUTPUT(ctypes.c_void_p)],
        ['hcam', 'param_id', 'param_attrib', 'param_value'])
dllFunc('pl_set_param', [int16, uns32, ctypes.c_void_p],
        ['hcam', 'param_id', 'param_value'])
dllFunc('pl_get_enum_param',
        [int16, uns32, uns32, OUTPUT(int32), OUTSTRING, uns32],
        ['hcam', 'param_id', 'index', 'value', 'desc', 'length'])
dllFunc('pl_enum_str_length', [int16, uns32, uns32, OUTPUT(uns32)],
        ['hcam', 'param_id', 'index', 'length'])
dllFunc('pl_pp_reset', [int16,], ['hcam'])
dllFunc('pl_create_smart_stream_struct', [OUTPUT(smart_stream_type), uns16],
        ['pSmtStruct', 'entries'])
dllFunc('pl_release_smart_stream_struct', [ctypes.POINTER(smart_stream_type),],
        ['pSmtStruct',])
dllFunc('pl_create_frame_info_struct', [OUTPUT(FRAME_INFO),],
        ['pNewFrameInfo'])
dllFunc('pl_release_frame_info_struct', [ctypes.POINTER(FRAME_INFO),],
        ['pFrameInfoToDel',])

dllFunc('pl_exp_abort', [int16, int16])

_attr_map = {
    ATTR_ACCESS: uns16,
    ATTR_AVAIL: rs_bool,
    ATTR_COUNT: uns32,
    ATTR_CURRENT: None,
    ATTR_DEFAULT: None,
    ATTR_INCREMENT: None,
    ATTR_MAX: None,
    ATTR_MIN: None,
    ATTR_TYPE: uns16,
}

_typemap = {
    TYPE_INT16: int16,
    TYPE_INT32: int32,
    TYPE_FLT64: flt64,
    TYPE_UNS8: uns8,
    TYPE_UNS16: uns16,
    TYPE_UNS32: uns32,
    TYPE_UNS64: ulong64,
    TYPE_ENUM: int32, # from SDK documentation
    TYPE_BOOLEAN: rs_bool,
    TYPE_INT8: int8,
    TYPE_CHAR_PTR: ctypes.c_char_p,
    TYPE_VOID_PTR: ctypes.c_void_p,
    TYPE_VOID_PTR_PTR: ctypes.POINTER(ctypes.c_void_p),
    TYPE_INT64: long64,
    TYPE_SMART_STREAM_TYPE: smart_stream_type,
    TYPE_SMART_STREAM_TYPE_PTR: ctypes.POINTER(smart_stream_type),
    TYPE_FLT32: flt32,}


_dtypemap = {
    TYPE_INT16: 'int',
    TYPE_INT32: 'int',
    TYPE_FLT64: 'float',
    TYPE_UNS8: 'int',
    TYPE_UNS16: 'int',
    TYPE_UNS32: 'int',
    TYPE_UNS64: 'int',
    TYPE_ENUM: 'enum',
    TYPE_BOOLEAN: 'bool',
    TYPE_INT8: 'int',
    TYPE_CHAR_PTR: 'str',
    TYPE_VOID_PTR: None,
    TYPE_VOID_PTR_PTR: None,
    TYPE_INT64: 'int',
    TYPE_SMART_STREAM_TYPE: None,
    TYPE_SMART_STREAM_TYPE_PTR: None,
    TYPE_FLT32: 'float',
}
"""


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

# Mapping of param ids to maximum string lengths.
# PARAM_DD_INFO is a variable length string, and its length can be found by
# querying PARAM_DD_INFO_LEN. However, querying PARAM_DD_INFO frequently causes
# a general protection fault in the DLL, regardless of buffer length.
_length_map = {
    PARAM_DD_INFO: None,
    PARAM_CHIP_NAME: CCD_NAME_LEN,
    PARAM_SYSTEM_NAME: MAX_SYSTEM_NAME_LEN,
    PARAM_VENDOR_NAME: MAX_VENDOR_NAME_LEN,
    PARAM_PRODUCT_NAME: MAX_PRODUCT_NAME_LEN,
    PARAM_CAMERA_PART_NUMBER: MAX_CAM_PART_NUM_LEN,
    PARAM_GAIN_NAME: MAX_GAIN_NAME_LEN,
    PARAM_HEAD_SER_NUM_ALPHA: MAX_ALPHA_SER_NUM_LEN,
    PARAM_PP_FEAT_NAME: MAX_PP_NAME_LEN,
    PARAM_PP_PARAM_NAME: MAX_PP_NAME_LEN,
}

_param_to_name = {globals()[param]:param for param in globals()
                  if (param.startswith('PARAM_') and param != 'PARAM_NAME_LEN')}


def get_param_type(param_id):
    return _typemap[param_id >> 24 & 255]


def get_param_dtype(param_id):
    return _dtypemap[param_id >> 24 & 255]


def get_param(handle, param_id):
    if not _get_param(handle, param_id, ATTR_AVAIL):
        raise Exception('pvcam: parameter %s not available.' % _param_to_name[param_id])
    t = _get_param(handle, param_id, ATTR_TYPE)
    if t.value == TYPE_CHAR_PTR:
        buf_len = _length_map[param_id]
        if not buf_len:
            raise Exception('pvcan: parameter %s not supported in python.' % _param_to_name[param_id])
        c = _get_param(handle, param_id, ATTR_CURRENT, buf_len=buf_len)
    else:
        c = _get_param(handle, param_id, ATTR_CURRENT)
    if t.value == TYPE_CHAR_PTR:
        return str(buffer(c))
    else:
        return c


from microscope import devices
from microscope.devices import keep_acquiring
import Pyro4

# Trigger mode to type.
TRIGGER_MODES = {
    'internal': None,
    'external': devices.TRIGGER_BEFORE,
    'external start': None,
    'external exposure': devices.TRIGGER_DURATION,
    'software': devices.TRIGGER_SOFT,
}

@Pyro4.behavior('single')
class PVCamera(devices.CameraDevice):
    def __init__(self, *args, **kwargs):
        super(PVCamera, self).__init__(**kwargs)
        self._index = kwargs.get('index', 0)
        self._pv_name = None
        self.handle = None

    """Private methods, called here and within super classes."""
    def _fetch_data(self):
        """Fetch data, recycle any buffers and return data or None."""
        return data or None

    def _on_enable(self):
        """Enable the camera hardware and make ready to respond to triggers.

        Return True if successful, False if not."""
        return False

    def _on_disable(self):
        """Disable the hardware for a short period of inactivity."""
        self.abort()
        pass

    def _on_shutdown(self):
        """Disable the hardware for a prolonged period of inactivity."""
        self._close()


    def _get_param_access(self, param_id):
        """Fetch parameter access restrictions."""
        # Will always be an integer, so return .value.
        return _get_param(self.handle, param_id, ATTR_ACCESS).value


    def _get_param_avail(self, param_id):
        """Is param_id available?"""
        # Will always be an integer, so return .value.
        return _get_param(self.handle, param_id, ATTR_AVAIL).value


    def _get_param_count(self, param_id):
        """Fetch parameter count."""
        # Will always be an integer, so return .value.
        return _get_param(self.handle, param_id, ATTR_COUNT).value


    def _get_param_ctype(self, param_id):
        """Return the C data type for a parameter."""
        return _typemap[param_id >> 24 & 255]


    def _get_param_type_code(self, param_id):
        """Fetch the parameter type code."""
        # Will always be an integer, so return .value.
        return _get_param(self.handle, param_id, ATTR_TYPE).value


    def _get_param(self, param_id, what=ATTR_CURRENT):
        """Fetch a parameter for this device, converting from void_p."""
        t = self._get_param_type_code(param_id)
        if t == TYPE_CHAR_PTR:
            buf_len = _length_map[param_id]
            if not buf_len:
                # Parameter not supported in python.
                return None
            try:
                c = _get_param(self.handle, param_id, what, buf_len=buf_len)
            except:
                return None
        else:
            try:
                c = _get_param(self.handle, param_id, what)
            except:
                return None
        if t == TYPE_CHAR_PTR:
            return str(buffer(c))
        elif t in [TYPE_SMART_STREAM_TYPE, TYPE_SMART_STREAM_TYPE_PTR,
                         TYPE_VOID_PTR, TYPE_VOID_PTR_PTR]:
            return c
        else:
            cast_to = self._get_param_ctype(param_id)
            return ctypes.POINTER(cast_to)(c).contents.value


    def _get_param_values(self, param_id):
        """Get parameter values, range or string length."""
        dtype = get_param_dtype(param_id)
        if dtype == 'enum':
            values = []
            count = self._get_param_count(param_id)
            for i in range(count):
                length = _enum_str_length(self.handle, param_id, i)
                values.append(tuple(c.value for c in _get_enum_param(self.handle, param_id, i, length)))
        elif dtype in [str, 'str']:
            values = _length_map[param_id]
        else:
            try:
                values = (self._get_param(param_id, what=ATTR_MIN),
                          self._get_param(param_id, what=ATTR_MAX))
            except:
                raise
                values = (None, None)
        return values


    def _set_param(self, param_id, value):
        """Set a parameter with param_id to value."""
        _set_param(self.handle,
                   param_id,
                   ctypes.byref(ctypes.c_void_p(value)))


    """Private shape-related methods. These methods do not need to account
    for camera orientation or transforms due to readout mode, as that
    is handled in the parent class."""
    def _get_sensor_shape(self):
        """Return the sensor shape (width, height)."""
        return (512,512)

    def _get_binning(self):
        """Return the current binning (horizontal, vertical)."""
        return (1,1)

    @keep_acquiring
    def _set_binning(self, h, v):
        """Set binning to (h, v)."""
        return False

    def _get_roi(self):
        """Return the current ROI (left, top, width, height)."""
        return (0, 0, 512, 512)

    @keep_acquiring
    def _set_roi(self, left, top, width, height):
        """Set the ROI to (left, tip, width, height)."""
        return False


    def _close(self):
        _cam_close(self.handle)


    def _open(self):
        try:
            _cam_close(self.handle)
        except:
            pass
        self._pv_name = _cam_get_name(self._index)
        self.handle = _cam_open(self._pv_name, OPEN_EXCLUSIVE)

        self._logger.info('Initializing.')

    """Public methods, callable from client."""
    @Pyro4.expose
    def abort(self):
        """Abort acquisition.

        This should put the camera into a state in which settings can
        be modified."""
        self._acquiring = False

    @Pyro4.expose
    def initialize(self):
        """Initialise the camera.

        Open the connection and populate settings dict.
        """
        self._open()
        for (param_id, name) in _param_to_name.items():
            name = name[6:]
            dtype = get_param_dtype(param_id)
            if not dtype or not self._get_param_avail(param_id):
                continue
            writable = self._get_param_access(param_id) in [ACC_READ_WRITE, ACC_WRITE_ONLY]
            #if writeable:
            #    setfunc = lambda param_id=param_id: self._set_param(param_id, value)
            self.add_setting(name,
                            dtype,
                            lambda param_id=param_id: self._get_param(param_id),
                            lambda: None,
                            lambda param_id=param_id: self._get_param_values(param_id),
                            not writable)



    @Pyro4.expose
    def make_safe(self):
        """Put the camera into a safe state.

        Safe means (at least):
         * it won't sustain damage if light falls on the sensor."""
        if self._acquiring:
            self.abort()

    @Pyro4.expose
    def set_exposure_time(self, value):
        """Set the exposure time to value."""
        pass

    @Pyro4.expose
    def get_exposure_time(self):
        """Return the current exposure time."""
        return 0.1

    @Pyro4.expose
    def get_cycle_time(self):
        """Return the cycle time.

        Cycle time is the minimum time between exposures. This is
        typically exposure time plus readout time."""
        return 0.15

    @Pyro4.expose
    def get_trigger_type(self):
        """Return the current trigger type."""
        return camera.TRIGGER_SOFT

    @Pyro4.expose
    def soft_trigger(self):
        """Send a software trigger to the camera."""
        pass


def _test():
    try:
        _pvcam_uninit()
    except:
        pass
    _pvcam_init()
    print('Version:\t%d' % _pvcam_get_ver().value)

    n_cameras = _cam_get_total().value
    print('Found:  \t%d camera(s)' % n_cameras)
    if not n_cameras:
        _pvcam_uninit()
        return

    cameras={}
    for n in range(n_cameras):
        name = _cam_get_name(n).value
        cameras[name] = _cam_open(name, 0).value
        print ("%d\t%s" % (cameras[name], name))

    print('\n=== Callbacks ===')
    f = lambda: None
    try:
        _cam_register_callback(0, PL_CALLBACK_EOF, f)
        _cam_register_callback(0, PL_CALLBACK_EOF, CALLBACK(f))
        _cam_deregister_callback(0, PL_CALLBACK_EOF)
        print('Successfully registered EOF callback by both methods.')
    except:
        raise

    f = lambda context: None
    try:
        _cam_register_callback_ex(0, PL_CALLBACK_EOF, f, 'abc')
        _cam_register_callback_ex(0, PL_CALLBACK_EOF, CALLBACK(f), 'abc')
        _cam_deregister_callback(0, PL_CALLBACK_EOF)
        print('Successfully registered EOF callback with context by both methods.')
    except:
        raise

    f = lambda frameinfo: None
    try:
        _cam_register_callback_ex2(0, PL_CALLBACK_EOF, f)
        _cam_register_callback_ex2(0, PL_CALLBACK_EOF, CALLBACK(f))
        _cam_deregister_callback(0, PL_CALLBACK_EOF)
        print('Successfully registered EOF FRAME_INFO callback by both methods.')
    except:
        raise

    f = lambda frameinfo, context: None
    try:
        _cam_register_callback_ex3(0, PL_CALLBACK_EOF, f, 'abc')
        _cam_register_callback_ex3(0, PL_CALLBACK_EOF, CALLBACK(f), 'abc')
        _cam_deregister_callback(0, PL_CALLBACK_EOF)
        print('Successfully registered EOF FRAME_INFO callback with context by both methods.')
    except:
        raise


    print ('\n=== Querying parameter types ===')
    by_type = {}
    count = 0
    for param_id in _param_to_name:
        try:
            t = _get_param(0, param_id, ATTR_TYPE).value
            count += 1
        except:
            print("%s not available." % _param_to_name[param_id])
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(param_id)
    print("Queried %d parameters and found %d in %d types" % (len(_param_to_name), count, len(by_type)))


    print('\n=== Testing get_param ===')
    for t, param_ids in by_type.items():
        print('\n== %s parameters ==' % _typemap[t])
        passed = []
        na = []
        failed = {}
        for param_id in param_ids:
            name = _param_to_name[param_id]
            try:
                get_param(0, param_id)
                passed.append(name)
            except Exception as e:
                if e.message.endswith(name + ' not available.'):
                    na.append(name)
                else:
                    failed[name] = e.message
        #if passed:
        #    print ("= passed =")
        #    print (', '.join(passed))
        #if na:
        #    print ("= not available =")
        #    print (', '.join(na))
        if failed:
            print ("= failed =")
            for fail in failed.items(): print ("%s: \t%s" % fail)


    print('\n=== Testing get_enum_param ===')
    for param_id in by_type[TYPE_ENUM]:
        name = _param_to_name[param_id]
        sl = _enum_str_length()
        #t = _get_enum_param(0, param_id, )


    # pl_set_param
    # pl_get_enum_param
    # pl_enum_str_length
    # pl_pp_reset
    # pl_create_smart_stream_struct
    # pl_release_smart_stream_struct
    # pl_create_frame_info_struct
    # pl_release_frame_info_struct

    return cameras