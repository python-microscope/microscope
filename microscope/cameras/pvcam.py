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

.. todo::
   Support frame metadata.  The following functions are still not implemented::

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

"""

import ctypes
import numpy as np
import os
import platform
import Pyro4
from microscope import devices
from microscope.devices import keep_acquiring
from six import string_types
import time

# Readout transform mapping - {CHIP_NAME: {port: transform}}
READOUT_TRANSFORMS = {
    'Evolve-5': {0: (0,0,0),
                 1: (1,0,0)}
}

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


# defines, typedefs and enums parsed from pvcam.h .
MAX_CAM = 16
CAM_NAME_LEN = 32
PARAM_NAME_LEN = 32
ERROR_MSG_LEN = 255
CCD_NAME_LEN = 17
MAX_ALPHA_SER_NUM_LEN = 32
MAX_PP_NAME_LEN = 32
MAX_SYSTEM_NAME_LEN = 32
MAX_VENDOR_NAME_LEN = 32
MAX_PRODUCT_NAME_LEN = 32
MAX_CAM_PART_NUM_LEN = 32
MAX_GAIN_NAME_LEN = 32
OPEN_EXCLUSIVE = 0
NORMAL_COOL = 0
CRYO_COOL = 1
MPP_UNKNOWN = 0
MPP_ALWAYS_OFF = 1
MPP_ALWAYS_ON = 2
MPP_SELECTABLE = 3
SHTR_FAULT = 0
SHTR_OPENING = 1
SHTR_OPEN = 2
SHTR_CLOSING = 3
SHTR_CLOSED = 4
SHTR_UNKNOWN = 5
PMODE_NORMAL = 0
PMODE_FT = 1
PMODE_MPP = 2
PMODE_FT_MPP = 3
PMODE_ALT_NORMAL = 4
PMODE_ALT_FT = 5
PMODE_ALT_MPP = 6
PMODE_ALT_FT_MPP = 7
COLOR_NONE = 0
COLOR_RESERVED = 1
COLOR_RGGB = 2
COLOR_GRBG = 3
COLOR_GBRG = 4
COLOR_BGGR = 5
ATTR_CURRENT = 0
ATTR_COUNT = 1
ATTR_TYPE = 2
ATTR_MIN = 3
ATTR_MAX = 4
ATTR_DEFAULT = 5
ATTR_INCREMENT = 6
ATTR_ACCESS = 7
ATTR_AVAIL = 8
ACC_READ_ONLY = 1
ACC_READ_WRITE = 2
ACC_EXIST_CHECK_ONLY = 3
ACC_WRITE_ONLY = 4
IO_TYPE_TTL = 0
IO_TYPE_DAC = 1
IO_DIR_INPUT = 0
IO_DIR_OUTPUT = 1
IO_DIR_INPUT_OUTPUT = 2
READOUT_PORT_0 = 0
READOUT_PORT_1 = 1
CLEAR_NEVER = 0
CLEAR_PRE_EXPOSURE = 1
CLEAR_PRE_SEQUENCE = 2
CLEAR_POST_SEQUENCE = 3
CLEAR_PRE_POST_SEQUENCE = 4
CLEAR_PRE_EXPOSURE_POST_SEQ = 5
MAX_CLEAR_MODE = 6
OPEN_NEVER = 0
OPEN_PRE_EXPOSURE = 1
OPEN_PRE_SEQUENCE = 2
OPEN_PRE_TRIGGER = 3
OPEN_NO_CHANGE = 4
TIMED_MODE = 0
STROBED_MODE = 1
BULB_MODE = 2
TRIGGER_FIRST_MODE = 3
FLASH_MODE = 4
VARIABLE_TIMED_MODE = 5
INT_STROBE_MODE = 6
MAX_EXPOSE_MODE = 7
Extended = 8
camera = 9
The = 10
definition = 11
EXT_TRIG_INTERNAL = 12
EXT_TRIG_TRIG_FIRST = 13
EXT_TRIG_EDGE_RISING = 14
EXPOSE_OUT_FIRST_ROW = 0
EXPOSE_OUT_ALL_ROWS = 1
EXPOSE_OUT_ANY_ROW = 2
MAX_EXPOSE_OUT_MODE = 3
FAN_SPEED_HIGH = 0
FAN_SPEED_MEDIUM = 1
FAN_SPEED_LOW = 2
FAN_SPEED_OFF = 3
PL_TRIGTAB_SIGNAL_EXPOSE_OUT = 0
PP_FEATURE_RING_FUNCTION = 0
PP_FEATURE_BIAS = 1
PP_FEATURE_BERT = 2
PP_FEATURE_QUANT_VIEW = 3
PP_FEATURE_BLACK_LOCK = 4
PP_FEATURE_TOP_LOCK = 5
PP_FEATURE_VARI_BIT = 6
PP_FEATURE_RESERVED = 7
PP_FEATURE_DESPECKLE_BRIGHT_HIGH = 8
PP_FEATURE_DESPECKLE_DARK_LOW = 9
PP_FEATURE_DEFECTIVE_PIXEL_CORRECTION = 10
PP_FEATURE_DYNAMIC_DARK_FRAME_CORRECTION = 11
PP_FEATURE_HIGH_DYNAMIC_RANGE = 12
PP_FEATURE_DESPECKLE_BRIGHT_LOW = 13
PP_FEATURE_DENOISING = 14
PP_FEATURE_DESPECKLE_DARK_HIGH = 15
PP_FEATURE_ENHANCED_DYNAMIC_RANGE = 16
PP_FEATURE_MAX = 17
PP_MAX_PARAMETERS_PER_FEATURE = 10
PP_PARAMETER_RF_FUNCTION = 0
PP_FEATURE_BIAS_ENABLED = 1
PP_FEATURE_BIAS_LEVEL = 2
PP_FEATURE_BERT_ENABLED = 3
PP_FEATURE_BERT_THRESHOLD = 4
PP_FEATURE_QUANT_VIEW_ENABLED = 5
PP_FEATURE_QUANT_VIEW_E = 6
PP_FEATURE_BLACK_LOCK_ENABLED = 7
PP_FEATURE_BLACK_LOCK_BLACK_CLIP = 8
PP_FEATURE_TOP_LOCK_ENABLED = 9
PP_FEATURE_TOP_LOCK_WHITE_CLIP = 10
PP_FEATURE_VARI_BIT_ENABLED = 11
PP_FEATURE_VARI_BIT_BIT_DEPTH = 12
PP_FEATURE_DESPECKLE_BRIGHT_HIGH_ENABLED = 13
PP_FEATURE_DESPECKLE_BRIGHT_HIGH_THRESHOLD = 14
PP_FEATURE_DESPECKLE_BRIGHT_HIGH_MIN_ADU_AFFECTED = 15
PP_FEATURE_DESPECKLE_DARK_LOW_ENABLED = 16
PP_FEATURE_DESPECKLE_DARK_LOW_THRESHOLD = 17
PP_FEATURE_DESPECKLE_DARK_LOW_MAX_ADU_AFFECTED = 18
PP_FEATURE_DEFECTIVE_PIXEL_CORRECTION_ENABLED = 19
PP_FEATURE_DYNAMIC_DARK_FRAME_CORRECTION_ENABLED = 20
PP_FEATURE_HIGH_DYNAMIC_RANGE_ENABLED = 21
PP_FEATURE_DESPECKLE_BRIGHT_LOW_ENABLED = 22
PP_FEATURE_DESPECKLE_BRIGHT_LOW_THRESHOLD = 23
PP_FEATURE_DESPECKLE_BRIGHT_LOW_MAX_ADU_AFFECTED = 24
PP_FEATURE_DENOISING_ENABLED = 25
PP_FEATURE_DENOISING_NO_OF_ITERATIONS = 26
PP_FEATURE_DENOISING_GAIN = 27
PP_FEATURE_DENOISING_OFFSET = 28
PP_FEATURE_DENOISING_LAMBDA = 29
PP_FEATURE_DESPECKLE_DARK_HIGH_ENABLED = 30
PP_FEATURE_DESPECKLE_DARK_HIGH_THRESHOLD = 31
PP_FEATURE_DESPECKLE_DARK_HIGH_MIN_ADU_AFFECTED = 32
PP_FEATURE_ENHANCED_DYNAMIC_RANGE_ENABLED = 33
PP_PARAMETER_ID_MAX = 34
SMTMODE_ARBITRARY_ALL = 0
SMTMODE_MAX = 1
READOUT_NOT_ACTIVE = 0
EXPOSURE_IN_PROGRESS = 1
READOUT_IN_PROGRESS = 2
READOUT_COMPLETE = 3
FRAME_AVAILABLE = 3
READOUT_FAILED = 4
ACQUISITION_IN_PROGRESS = 5
MAX_CAMERA_STATUS = 6
CCS_NO_CHANGE = 0
CCS_HALT = 1
CCS_HALT_CLOSE_SHTR = 2
CCS_CLEAR = 3
CCS_CLEAR_CLOSE_SHTR = 4
CCS_OPEN_SHTR = 5
CCS_CLEAR_OPEN_SHTR = 6
NO_FRAME_IRQS = 0
BEGIN_FRAME_IRQS = 1
END_FRAME_IRQS = 2
BEGIN_END_FRAME_IRQS = 3
CIRC_NONE = 0
CIRC_OVERWRITE = 1
CIRC_NO_OVERWRITE = 2
EXP_RES_ONE_MILLISEC = 0
EXP_RES_ONE_MICROSEC = 1
EXP_RES_ONE_SEC = 2
SCR_PRE_OPEN_SHTR = 0
SCR_POST_OPEN_SHTR = 1
SCR_PRE_FLASH = 2
SCR_POST_FLASH = 3
SCR_PRE_INTEGRATE = 4
SCR_POST_INTEGRATE = 5
SCR_PRE_READOUT = 6
SCR_POST_READOUT = 7
SCR_PRE_CLOSE_SHTR = 8
SCR_POST_CLOSE_SHTR = 9
PL_CALLBACK_BOF = 0
PL_CALLBACK_EOF = 1
PL_CALLBACK_CHECK_CAMS = 2
PL_CALLBACK_CAM_REMOVED = 3
PL_CALLBACK_CAM_RESUMED = 4
PL_CALLBACK_MAX = 5
PL_MD_FRAME_FLAG_ROI_TS_SUPPORTED = 1
PL_MD_FRAME_FLAG_UNUSED_2 = 2
PL_MD_FRAME_FLAG_UNUSED_3 = 4
PL_MD_FRAME_FLAG_UNUSED_4 = 16
PL_MD_FRAME_FLAG_UNUSED_5 = 32
PL_MD_FRAME_FLAG_UNUSED_6 = 64
PL_MD_FRAME_FLAG_UNUSED_7 = 128
PL_MD_ROI_FLAG_INVALID = 1
PL_MD_ROI_FLAG_UNUSED_2 = 2
PL_MD_ROI_FLAG_UNUSED_3 = 4
PL_MD_ROI_FLAG_UNUSED_4 = 16
PL_MD_ROI_FLAG_UNUSED_5 = 32
PL_MD_ROI_FLAG_UNUSED_6 = 64
PL_MD_ROI_FLAG_UNUSED_7 = 128
PL_MD_FRAME_SIGNATURE = 5328208
PL_MD_EXT_TAGS_MAX_SUPPORTED = 255
PL_MD_EXT_TAG_MAX = 0
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
CLASS0 = 0
CLASS2 = 2
CLASS3 = 3
PARAM_DD_INFO_LENGTH = 16777217
PARAM_DD_VERSION = 100663298
PARAM_DD_RETRIES = 100663299
PARAM_DD_TIMEOUT = 100663300
PARAM_DD_INFO = 218103813
PARAM_ADC_OFFSET = 16908483
PARAM_CHIP_NAME = 218235009
PARAM_SYSTEM_NAME = 218235010
PARAM_VENDOR_NAME = 218235011
PARAM_PRODUCT_NAME = 218235012
PARAM_CAMERA_PART_NUMBER = 218235013
PARAM_COOLING_MODE = 151126230
PARAM_PREAMP_DELAY = 100794870
PARAM_COLOR_MODE = 151126520
PARAM_MPP_CAPABLE = 151126240
PARAM_PREAMP_OFF_CONTROL = 117572091
PARAM_PREMASK = 100794421
PARAM_PRESCAN = 100794423
PARAM_POSTMASK = 100794422
PARAM_POSTSCAN = 100794424
PARAM_PIX_PAR_DIST = 100794868
PARAM_PIX_PAR_SIZE = 100794431
PARAM_PIX_SER_DIST = 100794869
PARAM_PIX_SER_SIZE = 100794430
PARAM_SUMMING_WELL = 184680953
PARAM_FWELL_CAPACITY = 117572090
PARAM_PAR_SIZE = 100794425
PARAM_SER_SIZE = 100794426
PARAM_ACCUM_CAPABLE = 184680986
PARAM_FLASH_DWNLD_CAPABLE = 184680987
PARAM_READOUT_TIME = 67240115
PARAM_CLEAR_CYCLES = 100794465
PARAM_CLEAR_MODE = 151126539
PARAM_FRAME_CAPABLE = 184680957
PARAM_PMODE = 151126540
PARAM_TEMP = 16908813
PARAM_TEMP_SETPOINT = 16908814
PARAM_CAM_FW_VERSION = 100794900
PARAM_HEAD_SER_NUM_ALPHA = 218235413
PARAM_PCI_FW_VERSION = 100794902
PARAM_FAN_SPEED_SETPOINT = 151126726
PARAM_EXPOSURE_MODE = 151126551
PARAM_EXPOSE_OUT_MODE = 151126576
PARAM_BIT_DEPTH = 16908799
PARAM_GAIN_INDEX = 16908800
PARAM_SPDTAB_INDEX = 16908801
PARAM_GAIN_NAME = 218235394
PARAM_READOUT_PORT = 151126263
PARAM_PIX_TIME = 100794884
PARAM_SHTR_CLOSE_DELAY = 100794887
PARAM_SHTR_OPEN_DELAY = 100794888
PARAM_SHTR_OPEN_MODE = 151126537
PARAM_SHTR_STATUS = 151126538
PARAM_IO_ADDR = 100794895
PARAM_IO_TYPE = 151126544
PARAM_IO_DIRECTION = 151126545
PARAM_IO_STATE = 67240466
PARAM_IO_BITDEPTH = 100794899
PARAM_GAIN_MULT_FACTOR = 100794905
PARAM_GAIN_MULT_ENABLE = 184680989
PARAM_PP_FEAT_NAME = 218235422
PARAM_PP_INDEX = 16908831
PARAM_ACTUAL_GAIN = 100794912
PARAM_PP_PARAM_INDEX = 16908833
PARAM_PP_PARAM_NAME = 218235426
PARAM_PP_PARAM = 117572131
PARAM_READ_NOISE = 100794916
PARAM_PP_FEAT_ID = 100794917
PARAM_PP_PARAM_ID = 100794918
PARAM_SMART_STREAM_MODE_ENABLED = 184681148
PARAM_SMART_STREAM_MODE = 100795069
PARAM_SMART_STREAM_EXP_PARAMS = 235012798
PARAM_SMART_STREAM_DLY_PARAMS = 235012799
PARAM_EXP_TIME = 100859905
PARAM_EXP_RES = 151191554
PARAM_EXP_RES_INDEX = 100859908
PARAM_EXPOSURE_TIME = 134414344
PARAM_BOF_EOF_ENABLE = 151191557
PARAM_BOF_EOF_COUNT = 117637126
PARAM_BOF_EOF_CLR = 184745991
PARAM_CIRC_BUFFER = 184746283
PARAM_FRAME_BUFFER_SIZE = 134414636
PARAM_BINNING_SER = 151191717
PARAM_BINNING_PAR = 151191718
PARAM_METADATA_ENABLED = 184746152
PARAM_ROI_COUNT = 100860073
PARAM_CENTROIDS_ENABLED = 184746154
PARAM_CENTROIDS_RADIUS = 100860075
PARAM_CENTROIDS_COUNT = 100860076
PARAM_TRIGTAB_SIGNAL = 151191732
PARAM_LAST_MUXED_SIGNAL = 84082869


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
    _fields_ = [("s1", uns16),
               ("s2", uns16),
               ("sbin", uns16),
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


if os.name in ('nt', 'ce'):
    if platform.architecture()[0] == '32bit':
        _lib = ctypes.WinDLL('pvcam32')
    else:
        _lib = ctypes.WinDLL('pvcam64')
else:
    _lib = ctypes.CDLL('pvcam.so')

### Functions ###
STRING = ctypes.c_char_p

# classes so that we do some magic and automatically add byrefs etc ... can classify outputs
# (Nicked from PYME's Ixon wrapper.)
class _meta(object):
    pass


class OUTPUT(_meta):
    def __init__(self, val):
        self.type = val
        self.val = ctypes.POINTER(val)

    def get_var(self, buf_len=0):
        if self.type in [STRING, ctypes.c_void_p] and buf_len > 0:
            v = ctypes.create_string_buffer(buf_len)
            ref = ctypes.cast(ctypes.pointer(v), self.val)
        else:
            v = self.type()
            ref = ctypes.byref(v)
        return v, ref


class _OUTSTRING(OUTPUT):
    def __init__(self):
        self.val = STRING

    def get_var(self, buf_len):
        v = ctypes.create_string_buffer(buf_len)
        return v, v


OUTSTRING = _OUTSTRING()


def stripMeta(val):
    """Strip meta info from OUTPUT and OUTSTRING instances."""
    if isinstance(val, _meta):
        return val.val
    else:
        return val

# Function type for callbacks.
CALLBACK = ctypes.CFUNCTYPE(ctypes.c_void_p)


class dllFunction(object):
    """Expose a DLL function to python.

    (Again, largely nicked from PYME.)"""
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
        # May have been passed a ctype; if so, fetch its value.
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

        # print (self.name, ars)
        res = self.f(*ars)
        # print res


        if res == False:
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


def _status():
    """Fetch the PVCAM DLL status."""
    err_code = _lib.pl_error_code()
    err_msg = ctypes.create_string_buffer(ERROR_MSG_LEN)
    _lib.pl_error_message(err_code, err_msg)
    print (str(buffer(err_msg)))


def dllFunc(name, args=[], argnames=[], buf_len=0):
    """Register a function using dllFunction."""
    f = dllFunction(name, args, argnames, buf_len=buf_len)
    globals()[name[2:]] = f


"""DLL function imports."""
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
dllFunc('pl_exp_abort', [int16, int16], ['hcam', 'cam_state'])
dllFunc('pl_exp_setup_seq',
        [int16, uns16, uns16, ctypes.POINTER(rgn_type), int16, uns32, OUTPUT(uns32)],
        ['hcam', 'exp_total', 'rgn_total', 'rgn_array', 'exp_mode', 'exposure_time', 'exp_bytes'])
dllFunc('pl_exp_start_seq', [int16, ctypes.c_void_p], ['hcam', 'pixel_stream'])
dllFunc('pl_exp_setup_cont',
        [int16, uns16, ctypes.POINTER(rgn_type), int16, uns32, OUTPUT(uns32), int16],
        ['hcam', 'rgn_total', 'rgn_array', 'exp_mode', 'exposure_time', 'exp_bytes', 'buffer_mode'])
dllFunc('pl_exp_start_cont',
        [int16, ctypes.c_void_p, uns32],
        ['hcam', 'pixel_stream', 'size'])
dllFunc('pl_exp_check_status',
        [int16, OUTPUT(int16), OUTPUT(uns32)],
        ['hcam', 'status', 'bytes_arrived'])
dllFunc('pl_exp_check_cont_status',
        [int16, OUTPUT(int16), OUTPUT(uns32), OUTPUT(uns32)],
        ['hcam', 'status', 'bytes_arrived', 'buffer_cnt'])
dllFunc('pl_exp_check_cont_status_ex',
        [int16, OUTPUT(int16), OUTPUT(uns32), OUTPUT(uns32), ctypes.POINTER(FRAME_INFO)],
        ['hcam', 'status', 'byte_cnt', 'buffer_cnt', 'pFrameInfo'])
dllFunc('pl_exp_get_latest_frame', [int16, OUTPUT(ctypes.c_void_p)], ['hcam', 'frame'])
dllFunc('pl_exp_get_latest_frame_ex',
        [int16, OUTPUT(ctypes.c_void_p), ctypes.POINTER(FRAME_INFO)],
        ['hcam', 'frame', 'pFrameInfo'])
dllFunc('pl_exp_get_oldest_frame', [int16, OUTPUT(ctypes.c_void_p)], ['hcam', 'frame'])
dllFunc('pl_exp_get_oldest_frame_ex',
        [int16, OUTPUT(ctypes.c_void_p), ctypes.POINTER(FRAME_INFO)],
        ['hcam', 'frame', 'pFrameInfo'])
dllFunc('pl_exp_unlock_oldest_frame', [int16], ['hcam'])
dllFunc('pl_exp_stop_cont', [int16, int16], ['hcam', 'cam_state'])
dllFunc('pl_exp_abort', [int16, int16], ['hcam', 'cam_state'])
dllFunc('pl_exp_finish_seq', [int16, ctypes.c_void_p], ['hcam', 'pixel_stream'])


# Map ATTR_ enums to the return type for that ATTR.
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

# Map TYPE enums to their type.
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


# Map TYPE enums to the appropriate setting dtype.
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

# map PARAM enums to the parameter name
_param_to_name = {globals()[param]:param for param in globals()
                  if (param.startswith('PARAM_') and param != 'PARAM_NAME_LEN')}


def get_param_type(param_id):
    """Return parameter type code (for C/DLL) for param_id."""
    # Parameter types are encoded in the 4th MSB of the param_id.
    return _typemap[param_id >> 24 & 255]


def get_param_dtype(param_id):
    """Return parameter dtype (for microscope settings) for param_id."""
    # Parameter types are encoded in the 4th MSB of the param_id.
    return _dtypemap[param_id >> 24 & 255]


# Map status codes to strings.
STATUS_STRINGS = {READOUT_NOT_ACTIVE: 'READOUT_NOT_ACTIVE',
                  EXPOSURE_IN_PROGRESS: 'EXPOSURE_IN_PROGRESS',
                  READOUT_IN_PROGRESS: 'READOUT_IN_PROGRESS',
                  READOUT_COMPLETE: 'READOUT_COMPLETE',
                  READOUT_FAILED: 'READOUT_FAILED',
                  FRAME_AVAILABLE: 'FRAME_AVAILABLE',}


# Allowable enum values that the hardware fails to report.
_ENUM_FIXES = {
    'Evolve-5': {PARAM_PMODE: [(0, 'Normal'), (4, 'Alternate Normal')],},
}


# === Python classes ===
# Trigger modes.
class TriggerMode(object):
    """A microscope trigger mode using PVCAM PMODES."""
    def __init__(self, id, label, pv_mode, microscope_mode):
        self.id = id
        self.label = label
        self.pv_mode = pv_mode
        self.microscope_mode = microscope_mode

    def __repr__(self):
        return "<%s: '%s'>" % (type(self).__name__, self.label)


# Enumerate trigger types.
(TRIG_SOFT, TRIG_TIMED, TRIG_VARIABLE, TRIG_FIRST, TRIG_STROBED, TRIG_BULB) = range(6)

# Trigger mode definitions.
TRIGGER_MODES = {
    TRIG_SOFT: TriggerMode(TRIG_SOFT, 'software', TIMED_MODE, devices.TRIGGER_SOFT),
    TRIG_TIMED: TriggerMode(TRIG_TIMED, 'timed', TIMED_MODE, -1),
    TRIG_VARIABLE: TriggerMode(TRIG_VARIABLE, 'variable timed', VARIABLE_TIMED_MODE, -1),
    TRIG_FIRST: TriggerMode(TRIG_FIRST, 'trig. first', TRIGGER_FIRST_MODE, devices.TRIGGER_BEFORE),
    TRIG_STROBED: TriggerMode(TRIG_STROBED, 'strobed', STROBED_MODE, devices.TRIGGER_BEFORE),
    TRIG_BULB: TriggerMode(TRIG_BULB, 'bulb', BULB_MODE, devices.TRIGGER_DURATION),
}


class PVParam(object):
    """A wrapper around PVCAM parameters."""
    def __init__(self, camera, param_id):
        self.cam = camera
        self.param_id = param_id

        self.name = _param_to_name[param_id]
        self._pvtype = param_id >> 24 & 255
        self.dtype = _dtypemap[self._pvtype]
        self._ctype = _typemap[self._pvtype]
        self.__cache = {}


    def set_value(self, new_value):
        """Set a parameter value."""
        if self.dtype == 'enum':
            # We may be passed a value, a description string, or a tuple of
            # (value, string).
            values, descriptions = zip(*self.values)
            if hasattr(new_value, '__iter__'):
                desc = str(new_value[1])
            elif isinstance(new_value, string_types):
                desc = str(new_value)
            else:
                desc = None
            # If we have a description, rely on that, as this avoids any confusion
            # of index and value.
            if desc and desc in descriptions:
                new_index = descriptions.index(desc)
                new_value = values[new_index]
            elif desc:
                raise Exception("Could not find description '%s' for enum %s." % (desc, self.name))
        _set_param(self.cam.handle,
                   self.param_id,
                   # TODO: this throws errors on strings, since need to put them into
                   # a buffer before creating a pointer. Does any pvcam hardware let you
                   # write to strings, though?
                   ctypes.byref(ctypes.c_void_p(new_value)))
        # Read back the value to update cache.
        self._query(force_query=True)



    def _query(self, what=ATTR_CURRENT, force_query=False):
        """Query the DLL for an attribute for this parameter."""
        err = None
        key = (self, what) # key for cache
        if self.cam._acquiring and not force_query:
            return self.__cache.get(key, None)
        if what == ATTR_AVAIL:
            return self.available
        elif not self.available:
            raise Exception("Parameter %s is not available" % self.name)
        rtype = _attr_map[what] # return type
        if not rtype:
            rtype = _get_param(self.cam.handle, self.param_id, ATTR_TYPE)
        if rtype.value == TYPE_CHAR_PTR:
            buf_len = _length_map[self.param_id]
            if not buf_len:
                raise Exception('pvcam: parameter %s not supported in python.' % self.name)
            try:
                result = _get_param(self.cam.handle, self.param_id, what, buf_len=buf_len)
            except Exception as e:
                err = e
        else:
            try:
                result = _get_param(self.cam.handle, self.param_id, what)
            except Exception as e:
                err = e

        if err and err.message.startswith('pvcam error 49'):
            self.cam._logger.warn("Parameter %s not available due to camera state." % self.name)
            result = None
        elif err:
            raise e
        else:
            self.__cache[key] = result
        return result


    @property
    def access(self):
        """Return parameter access attribute."""
        return self._query(what=ATTR_ACCESS).value


    @property
    def available(self):
        """Return whether or not parameter is available on hardware."""
        return bool(_get_param(self.cam.handle, self.param_id, ATTR_AVAIL))


    @property
    def count(self):
        """Return count of parameter enum entries."""
        return self._query(what=ATTR_COUNT).value


    @property
    def values(self):
        """Get parameter values, range or string length."""
        if self.dtype == 'enum':
            values = []
            for i in range(self.count):
                length = _enum_str_length(self.cam.handle, self.param_id, i)
                value, desc = _get_enum_param(self.cam.handle, self.param_id, i, length)
                values.append((value.value, desc.value))
            chip = self.cam._params[PARAM_CHIP_NAME].current
            missing = _ENUM_FIXES.get(chip, {}).get(self.param_id, [])
            for m in missing:
                if m[0] not in zip(*values)[0]:
                    values.append(m)
            values.sort()
        elif self.dtype in [str, 'str']:
            values = _length_map[self.param_id] or 0
        else:
            try:
                values = (ctypes.POINTER(self._ctype)(self._query(ATTR_MIN)).contents.value,
                          ctypes.POINTER(self._ctype)(self._query(ATTR_MAX)).contents.value)
            except:
                raise
        return values


    @property
    def raw(self):
        """Return a raw parameter query result."""
        return self._query()


    @property
    def current(self):
        """Return the current (or cached) parameter value."""
        if self._pvtype == TYPE_CHAR_PTR:
                return str(memoryview(self.raw).tobytes()) or ''
        elif self._pvtype in [TYPE_SMART_STREAM_TYPE, TYPE_SMART_STREAM_TYPE_PTR,
                              TYPE_VOID_PTR, TYPE_VOID_PTR_PTR]:
            raise Exception('Value conversion not supported for parameter %s.' % self.name)
        elif self._pvtype == TYPE_ENUM:
            value = int(self.raw.value or 0) # c_void_p(0) is None, so replace with 0
            vals, descs = zip(*self.values)
            if value in vals:
                index = vals.index(value)
                description = descs[index]
            else:
                index = None
                description = '*UNDEFINED*'
            return (value, description)
        else:
            return ctypes.POINTER(self._ctype)(self.raw).contents.value


@Pyro4.behavior('single')
class PVCamera(devices.FloatingDeviceMixin, devices.CameraDevice):
    """Implements the CameraDevice interface for the pvcam library."""
    # Keep track of open cameras.
    open_cameras = []


    def __init__(self, *args, **kwargs):
        super(PVCamera, self).__init__(**kwargs)
        # Camera index in DLL.
        self._index = kwargs.get('index', 0)
        # Camera name in DLL.
        self._pv_name = None
        # Camera handle.
        self.handle = None
        # Sensor shape.
        self.shape = (None, None)
        # Region of interest.
        self.roi = (None, None, None, None)
        # Binning setting.
        self.binning = (1, 1)
        self._trigger = TRIG_STROBED
        self.exposure_time = 0.001 # in seconds
        # Cycle time
        self.cycle_time = self.exposure_time
        # Data buffer.
        self._buffer = None
        # This devices PVCAM parameters.
        self._params = {}
        # Circular buffer length.
        self._circ_buffer_length = 10

        # Add common settings.
        self.add_setting('exposure time',
                         float,
                         lambda: self.exposure_time,
                         self.set_exposure_time,
                         lambda: (1e-6, 1))
        self.add_setting('trigger mode',
                          'enum',
                          lambda: (self._trigger, TRIGGER_MODES[self._trigger].label),
                          lambda args: setattr(self, '_trigger', int(args[0])),
                          [(k, v.label) for k, v in TRIGGER_MODES.items()]
                          )
        self.add_setting('circular buffer length',
                         int,
                         lambda: self._circ_buffer_length,
                         lambda value: setattr(self, '_circ_buffer_length', value),
                         (2, 100))

    @property
    def _region(self):
        """Return a rgn_type for current roi and binning settings."""
        return rgn_type(self.roi[0], self.roi[2]-1, self.binning[0],
                        self.roi[1], self.roi[3]-1, self.binning[1])


    """Private methods, called here and within super classes."""
    def _fetch_data(self):
        """Fetch data - for use in fetch_loop."""
        # Not used: images fetched using callback.
        return None


    def _on_enable(self):
        """Enable the camera hardware and make ready to respond to triggers.

        Return True if successful, False if not."""
        # Set exposure time resolution on camera and determine t_exp, the
        # integer value used to set exposure time on the hardware later.
        if self.exposure_time < 1e-3:
            self._params[PARAM_EXP_RES].set_value(EXP_RES_ONE_MICROSEC)
            t_exp = int(self.exposure_time * 1e6)
        else:
            self._params[PARAM_EXP_RES].set_value(EXP_RES_ONE_MILLISEC)
            t_exp = value = int(self.exposure_time * 1e3)
        # Configure camera, allocate buffer, and register callback.
        if self._trigger == TRIG_SOFT:
            # Software triggering for single frames.
            # Set up callback.
            self._using_callback = True
            def cb():
                """Soft trigger mode end-of-frame callback."""
                timestamp = time.time()
                frame = self._buffer.copy()
                self._logger.debug("Fetched single frame.")
                _exp_finish_seq(self.handle, CCS_CLEAR)
                self._put(frame, timestamp)
                return
            # Need to keep a reference to the callback.
            self._eof_callback = CALLBACK(cb)
            _cam_register_callback(self.handle, PL_CALLBACK_EOF, self._eof_callback)
            nbytes = _exp_setup_seq(self.handle, 1, 1, # cam, num epxosures, num regions
                                    self._region, TRIGGER_MODES[self._trigger].pv_mode, t_exp)
            self._buffer = np.require(np.zeros(self.shape, dtype='uint16'),
                                      requirements=['C_CONTIGUOUS','ALIGNED','OWNDATA'])
        else:
            # Use a circular buffer.
            self._using_callback = True
            def cb():
                """Circular buffer mode end-of-frame callback."""
                timestamp = time.time()
                frame_p = ctypes.cast(_exp_get_latest_frame(self.handle), ctypes.POINTER(uns16))
                frame = np.ctypeslib.as_array(frame_p, (self.roi[2], self.roi[3])).copy()
                self._logger.debug("Fetched frame from circular buffer.")
                self._put(frame, timestamp)
                return
            # Need to keep a reference to the callback.
            self._eof_callback = CALLBACK(cb)
            _cam_register_callback(self.handle, PL_CALLBACK_EOF, self._eof_callback)
            buffer_shape = (self._circ_buffer_length*self.roi[2], self.roi[3])
            self._buffer = np.require(np.zeros(buffer_shape, dtype='uint16'),
                                          requirements=['C_CONTIGUOUS', 'ALIGNED', 'OWNDATA'])
            nbytes = _exp_setup_cont(self.handle, 1, self._region,
                                     TRIGGER_MODES[self._trigger].pv_mode, t_exp, CIRC_OVERWRITE).value



        # Read back exposure time.
        t_readback = self._params[PARAM_EXPOSURE_TIME].current
        t_resolution = self._params[PARAM_EXP_RES].current
        multipliers = {EXP_RES_ONE_SEC: 1.,
                       EXP_RES_ONE_MILLISEC: 1e-3,
                       EXP_RES_ONE_MICROSEC: 1e-6}
        if isinstance(t_resolution, tuple):
            self.exposure_time = t_readback * multipliers[t_resolution[0]]
        else:
            self.exposure_time = t_readback * multipliers[t_resolution]
        # Update cycle time. Exposure time in seconds; readout time in microseconds.
        self.cycle_time = self.exposure_time + 1e-6 * self._params[PARAM_READOUT_TIME].current
        # Set up exposure time for VARIABLE_TIMED_MODE, as according to documentation.
        # It doesn't seem to work.
        if self._trigger == TRIG_VARIABLE:
            self._params[PARAM_EXP_TIME].set_value(t_exp)
        # If using real triggering, start triggered acquisition.
        # (Software triggering will start acquisition in soft_trigger().)
        if self._trigger != TRIG_SOFT:
            _exp_start_cont(self.handle, self._buffer.ctypes.data_as(ctypes.c_void_p), self._buffer.nbytes)
        # Done.
        self._acquiring = True
        return self._acquiring


    def _on_disable(self):
        """Disable the hardware for a short period of inactivity."""
        self.abort()
        _cam_deregister_callback(self.handle, PL_CALLBACK_EOF)


    def _on_shutdown(self):
        """Disable the hardware for a prolonged period of inactivity."""
        self.abort()
        _cam_close(self.handle)
        PVCamera.open_cameras.remove(self.handle)
        if not PVCamera.open_cameras:
            self._logger.info("No more open cameras - calling _pvcam_uninit.")
            _pvcam_uninit()


    """Private shape-related methods. These methods do not need to account
    for camera orientation or transforms due to readout mode, as that
    is handled in the parent class."""
    def _get_sensor_shape(self):
        """Return the sensor shape (width, height)."""
        return self.shape

    def _get_binning(self):
        """Return the current binning (horizontal, vertical)."""
        return self.binning

    @keep_acquiring
    def _set_binning(self, h, v):
        """Set binning to (h, v)."""
        #  The keep_acquiring decorator will cause recreation of buffers.
        self.binning = (h, v)

    def _get_roi(self):
        """Return the current ROI (left, top, width, height)."""
        return self.roi

    @keep_acquiring
    def _set_roi(self, left, top, width, height):
        """Set the ROI to (left, tip, width, height)."""
        self.roi = (left, top, width, height)


    """Public methods, callable from client."""
    def get_id(self):
        """Get hardware's unique identifier."""
        return self._params[PARAM_HEAD_SER_NUM_ALPHA].current


    @Pyro4.expose
    def abort(self):
        """Abort acquisition.

        This should put the camera into a state in which settings can
        be modified."""
        if self._trigger == TRIG_SOFT:
            _exp_finish_seq(self.handle, CCS_CLEAR)
        else:
            _exp_stop_cont(self.handle, CCS_CLEAR)
        _exp_abort(self.handle, CCS_HALT)
        self._acquiring = False


    @Pyro4.expose
    def initialize(self):
        """Initialise the camera."""
        # Init the DLL if necessary.
        if not PVCamera.open_cameras:
            try:
                _pvcam_init()
            except:
                pass
        # If no cameras detected, need to deinit DLL so it can be reinited to update count.
        if _cam_get_total().value == 0:
            _pvcam_uninit()
            raise Exception ('No cameras detected.')
        # Connect to the camera.
        self._logger.info("DLL version: %s" % _pvcam_get_ver().value)
        self._pv_name = _cam_get_name(self._index).value
        self._logger.info('Initializing %s' % self._pv_name)
        self.handle = _cam_open(self._pv_name, OPEN_EXCLUSIVE)
        PVCamera.open_cameras.append(self.handle)
        # Set up event callbacks. Tried to use the resume callback to reinit camera
        # after power loss, but any attempt to close/reopen the camera or deinit the
        # DLL throws a Windows Error 0xE06D7363.
        def _cb(event):
            self._logger.info("Received %s event." % event)
            if event == 'removed':
                self._logger.critical("Can not re-init hardware. Exiting.")
                exit(-1)
            return
        self._cbs = {'check': CALLBACK(lambda: _cb('check')),
                     'resumed': CALLBACK(lambda: _cb('resumed')),
                     'removed': CALLBACK(lambda: _cb('removed'))}
        _cam_register_callback(self.handle, PL_CALLBACK_CHECK_CAMS, self._cbs['check'])
        _cam_register_callback(self.handle, PL_CALLBACK_CAM_REMOVED, self._cbs['removed'])
        _cam_register_callback(self.handle, PL_CALLBACK_CAM_RESUMED, self._cbs['resumed'])
        # Repopulate _params.
        self._params = {}
        # Add chip before anything else, as chip name is used to add missing enums.
        self._params[PARAM_CHIP_NAME] = PVParam(self, PARAM_CHIP_NAME)
        for (param_id, name) in _param_to_name.items():
            if param_id in self._params:
                continue
            p = PVParam(self, param_id)
            if not p.dtype or not p.available:
                continue
            self._params[param_id] = p
            name = name[6:]

            try:
                p.current
            except KeyError:
                # Raise these here, as the message is a tuple, not a str.
                raise
            except Exception as err:
                if not err.message.startswith('pvcam error 49'):
                    self._logger.warn("Skipping parameter %s: not supported in python." % (p.name), exc_info=err.message)
                    continue
            self.add_setting(p.name,
                             p.dtype,
                             lambda p=p: p.current,
                             p.set_value,
                             lambda p=p: p.values,
                             not p.access in [ACC_READ_WRITE, ACC_WRITE_ONLY])
        if PARAM_GAIN_MULT_FACTOR in self._params:
            self.add_setting('gain',
                             self._params[PARAM_GAIN_MULT_FACTOR].dtype,
                             lambda: self._params[PARAM_GAIN_MULT_FACTOR].current,
                             self._params[PARAM_GAIN_MULT_FACTOR].set_value,
                             self._params[PARAM_GAIN_MULT_FACTOR].values)

        if PARAM_PMODE in self._params:
            self.add_setting('frame transfer mode',
                             self._params[PARAM_PMODE].dtype,
                             lambda: self._params[PARAM_PMODE].current,
                             self._params[PARAM_PMODE].set_value,
                             self._params[PARAM_PMODE].values)

        self.shape = (self._params[PARAM_PAR_SIZE].current, self._params[PARAM_SER_SIZE].current)
        self.roi = (0, 0, self.shape[0], self.shape[1])

        # Populate readout modes by iterating over readout ports and speed
        # table entries.
        ro_ports = self._params[PARAM_READOUT_PORT].values
        self._readout_modes = []
        self._readout_mode_parameters = {}
        for i, port in ro_ports:
            self._params[PARAM_READOUT_PORT].set_value(i)
            ro_speeds = self._params[PARAM_SPDTAB_INDEX].values
            for j in range(ro_speeds[0], ro_speeds[1]+1):
                self._params[PARAM_SPDTAB_INDEX].set_value(j)
                bit_depth = self._params[PARAM_BIT_DEPTH].current
                freq = 1e9 / self._params[PARAM_PIX_TIME].current
                if freq > 1e6:
                    freq *= 1e-6
                    prefix = 'M'
                elif freq > 1e3:
                    freq *= 1e-3
                    prefix = 'k'
                else:
                    prefix = 'Hz'
                mode_str = "%s, %s-bit, %s %sHz" % (port, bit_depth, freq, prefix)
                self._readout_modes.append(mode_str)
                self._readout_mode_parameters[mode_str] = {'port':i, 'spdtab_index': j}
        # Set to default mode.
        self.set_readout_mode(self._readout_modes[0])
        self._params[PARAM_CLEAR_MODE].set_value(CLEAR_PRE_EXPOSURE_POST_SEQ)


    @Pyro4.expose
    @keep_acquiring
    def set_readout_mode(self, description):
        """Set the readout mode and transform."""
        params = self._readout_mode_parameters[description]
        self._params[PARAM_READOUT_PORT].set_value(params['port'])
        self._params[PARAM_SPDTAB_INDEX].set_value(params['spdtab_index'])
        self._readout_mode = description
        # Update transforms, if available.
        chip = self._params[PARAM_CHIP_NAME].current
        new_readout_transform = None
        readout_map = READOUT_TRANSFORMS.get(chip, None)
        if readout_map:
            new_readout_transform = readout_map.get(params['port'], None)
        if new_readout_transform:
            self._set_readout_transform(new_readout_transform)


    @Pyro4.expose
    def make_safe(self):
        """Put the camera into a safe state.

        Safe means (at least):
         * it won't sustain damage if light falls on the sensor."""
        if self._acquiring:
            self.abort()


    @Pyro4.expose
    @keep_acquiring
    def set_exposure_time(self, value):
        """Set the exposure time to value."""
        self.exposure_time = value


    @Pyro4.expose
    def get_exposure_time(self):
        """Return the current exposure time.

        Just return self.exposure_time, which is updated with the real
        value during _on_enable."""
        return self.exposure_time


    @Pyro4.expose
    def get_cycle_time(self):
        """Return the cycle time.

        Just return self.cycle_time, which is updated with the real
        value during _on_enable."""
        return self.cycle_time


    @Pyro4.expose
    def get_trigger_type(self):
        """Return the current trigger type."""
        return TRIGGER_MODES[self._trigger].microscope_mode


    @Pyro4.expose
    @Pyro4.oneway
    def soft_trigger(self):
        """Expose software triggering to a client.

        Trigger an exposure in TRIG_SOFT mode.
        Log some debugging stats in other trigger modes."""
        if self._trigger == TRIG_SOFT:
            self._logger.debug("Received soft trigger ...")
            _exp_start_seq(self.handle, self._buffer.ctypes.data_as(ctypes.c_void_p))
        else:
            cstatus, cbytes, cframes = _exp_check_cont_status(self.handle)
            status, bytes = _exp_check_status(self.handle)

            self._logger.debug("Status checks\ncheck_cont:   %s \t bytes: %d\tframes: %d\n"  \
                               "check_status: %s \t bytes: %d\t" \
                               % (STATUS_STRINGS[cstatus.value], cbytes.value, cframes.value,
                                  STATUS_STRINGS[status.value], bytes.value))
        return
