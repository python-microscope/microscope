/******************************************************************************/
/* Copyright (C) Roper Scientific, Inc. All rights reserved.                  */
/******************************************************************************/

#ifndef _PVCAM_H
#define _PVCAM_H

/******************************************************************************/
/* Constants                                                                  */
/******************************************************************************/

/** Maximum number of cameras on this system. */
#define MAX_CAM                16

/******************************************************************************/
/* Name/ID sizes                                                              */
/******************************************************************************/

/** Maximum length of a camera name. */
#define CAM_NAME_LEN           32   /**< Includes space for null terminator. */
/** Maximum length of a post-processing parameter/feature name. */
/** Use MAX_PP_NAME_LEN instead. */
#define PARAM_NAME_LEN         32   /**< Includes space for null terminator. */
/** Maximum length of an error message. */
#define ERROR_MSG_LEN         255   /**< Includes space for null terminator. */
/** Maximum length of a sensor chip name. */
#define CCD_NAME_LEN           17   /**< Includes space for null terminator. */
/** Maximum length of a camera serial number string. */
#define MAX_ALPHA_SER_NUM_LEN  32   /**< Includes space for null terminator. */
/** Maximum length of a post-processing parameter/feature name. */
#define MAX_PP_NAME_LEN        32   /**< Includes space for null terminator. */
/** Maximum length of a system name. */
#define MAX_SYSTEM_NAME_LEN    32   /**< Includes space for null terminator. */
/** Maximum length of a vendor name. */
#define MAX_VENDOR_NAME_LEN    32   /**< Includes space for null terminator. */
/** Maximum length of a product name. */
#define MAX_PRODUCT_NAME_LEN   32   /**< Includes space for null terminator. */
/** Maximum length of a product name. */
#define MAX_CAM_PART_NUM_LEN   32   /**< Includes space for null terminator. */
/** Maximum length of a gain name. */
#define MAX_GAIN_NAME_LEN      32   /**< Includes space for null terminator. */

/******************************************************************************/
/* Data types                                                                 */
/******************************************************************************/

/**
GUID for #FRAME_INFO structure.
*/
typedef struct _TAG_PVCAM_FRAME_INFO_GUID
{
    uns32 f1;
    uns16 f2;
    uns16 f3;
    uns8  f4[8];
}
PVCAM_FRAME_INFO_GUID;

/**
Structure used to uniquely identify frames in the camera.
*/
typedef struct _TAG_FRAME_INFO
{
    PVCAM_FRAME_INFO_GUID FrameInfoGUID;
    int16 hCam;
    int32 FrameNr;
    long64 TimeStamp;
    int32 ReadoutTime;
    long64 TimeStampBOF;
}
FRAME_INFO;

/**
The modes under which the camera can be open.
Used with the function pl_cam_open().
Treated as int16 type.
*/
typedef enum PL_OPEN_MODES
{
    OPEN_EXCLUSIVE
}
PL_OPEN_MODES;

/**
Used with the #PARAM_COOLING_MODE parameter ID.
Treated as int32 type.
*/
typedef enum PL_COOL_MODES
{
    NORMAL_COOL,
    CRYO_COOL
}
PL_COOL_MODES;

/**
Used with the #PARAM_MPP_CAPABLE parameter ID.
Treated as int32 type.
*/
typedef enum PL_MPP_MODES
{
    MPP_UNKNOWN,
    MPP_ALWAYS_OFF,
    MPP_ALWAYS_ON,
    MPP_SELECTABLE
}
PL_MPP_MODES;

/**
Used with the #PARAM_SHTR_STATUS parameter ID.
Treated as int32 type.
*/
typedef enum PL_SHTR_MODES
{
    SHTR_FAULT,
    SHTR_OPENING,
    SHTR_OPEN,
    SHTR_CLOSING,
    SHTR_CLOSED,
    SHTR_UNKNOWN
}
PL_SHTR_MODES;

/**
Used with the #PARAM_PMODE parameter ID.
Treated as int32 type.
*/
typedef enum PL_PMODES
{
    PMODE_NORMAL,
    PMODE_FT,
    PMODE_MPP,
    PMODE_FT_MPP,
    PMODE_ALT_NORMAL,
    PMODE_ALT_FT,
    PMODE_ALT_MPP,
    PMODE_ALT_FT_MPP
}
PL_PMODES;

/**
Used with the #PARAM_COLOR_MODE parameter ID.
Treated as int32 type (but should not exceed a value of 255 due to md_frame_header.colorMask)
*/
typedef enum PL_COLOR_MODES
{
    COLOR_NONE     = 0, /**< No color mask */
    COLOR_RESERVED = 1, /**< Reserved, do not use */
    COLOR_RGGB     = 2,
    COLOR_GRBG,
    COLOR_GBRG,
    COLOR_BGGR
}
PL_COLOR_MODES;

/**
Used with the function pl_get_param().
Treated as int16 type.
*/
typedef enum PL_PARAM_ATTRIBUTES
{
    ATTR_CURRENT,
    ATTR_COUNT,
    ATTR_TYPE,
    ATTR_MIN,
    ATTR_MAX,
    ATTR_DEFAULT,
    ATTR_INCREMENT,
    ATTR_ACCESS,
    ATTR_AVAIL
}
PL_PARAM_ATTRIBUTES;

/**
Used with the function pl_get_param() and #ATTR_ACCESS.
Treated as uns16 type.
*/
typedef enum PL_PARAM_ACCESS
{
    ACC_READ_ONLY = 1,
    ACC_READ_WRITE,
    ACC_EXIST_CHECK_ONLY,
    ACC_WRITE_ONLY
}
PL_PARAM_ACCESS;

/**
Used with the #PARAM_IO_TYPE parameter ID.
Treated as int32 type.
*/
typedef enum PL_IO_TYPE
{
    IO_TYPE_TTL,
    IO_TYPE_DAC
}
PL_IO_TYPE;

/**
Used with the #PARAM_IO_DIRECTION parameter ID.
Treated as int32 type.
*/
typedef enum PL_IO_DIRECTION
{
    IO_DIR_INPUT,
    IO_DIR_OUTPUT,
    IO_DIR_INPUT_OUTPUT
}
PL_IO_DIRECTION;

/**
Used with the #PARAM_READOUT_PORT parameter ID.
Treated as int32 type.
*/
typedef enum PL_READOUT_PORTS
{
    READOUT_PORT_0 = 0,
    READOUT_PORT_1
}
PL_READOUT_PORTS;

/**
Used with the #PARAM_CLEAR_MODE parameter ID.
Treated as int32 type.
*/
typedef enum PL_CLEAR_MODES
{
    CLEAR_NEVER,
    CLEAR_PRE_EXPOSURE,
    CLEAR_PRE_SEQUENCE,
    CLEAR_POST_SEQUENCE,
    CLEAR_PRE_POST_SEQUENCE,
    CLEAR_PRE_EXPOSURE_POST_SEQ,
    MAX_CLEAR_MODE
}
PL_CLEAR_MODES;

/**
Used with the #PARAM_SHTR_OPEN_MODE parameter ID.
Treated as int32 type.
*/
typedef enum PL_SHTR_OPEN_MODES
{
    OPEN_NEVER,
    OPEN_PRE_EXPOSURE,
    OPEN_PRE_SEQUENCE,
    OPEN_PRE_TRIGGER,
    OPEN_NO_CHANGE
}
PL_SHTR_OPEN_MODES;

/**
Used with the #PARAM_EXPOSURE_MODE parameter ID.
Treated as int32 type.
Used with the functions pl_exp_setup_cont() and pl_exp_setup_seq().
Treated as int16 type.
*/
typedef enum PL_EXPOSURE_MODES
{
    /* Classic EXPOSURE modes, the MAX */
    TIMED_MODE,
    STROBED_MODE,
    BULB_MODE,
    TRIGGER_FIRST_MODE,
    FLASH_MODE,
    VARIABLE_TIMED_MODE,
    INT_STROBE_MODE,
    MAX_EXPOSE_MODE = 7,

    /*
    Extended EXPOSURE modes used with #PARAM_EXPOSURE_MODE when
    camera dynamically reports it's capabilities.
    The "7" in each of these calculations comes from previous
    definition of #MAX_EXPOSE_MODE when this file was defined.
    */
    EXT_TRIG_INTERNAL = (7 + 0) << 8,
    EXT_TRIG_TRIG_FIRST = (7 + 1) << 8,
    EXT_TRIG_EDGE_RISING  = (7 + 2) << 8
}
PL_EXPOSURE_MODES;

/**
Used with the #PARAM_EXPOSE_OUT_MODE parameter ID.
Build the values for the expose out modes that are "ORed" with the trigger
modes when setting up the script.
Treated as int32 type.
*/
typedef enum PL_EXPOSE_OUT_MODES
{
    EXPOSE_OUT_FIRST_ROW = 0, /**< Follows first row. */
    EXPOSE_OUT_ALL_ROWS,      /**< Exposure bottom row starts integrating, to when first row begins reading out. */
    EXPOSE_OUT_ANY_ROW,       /**< from first row exposing to last last row reading out. */
    MAX_EXPOSE_OUT_MODE
}
PL_EXPOSE_OUT_MODES;

/**
Used with the #PARAM_FAN_SPEED_SETPOINT parameter ID.
Treated as int32 type.
*/
typedef enum PL_FAN_SPEEDS
{
    FAN_SPEED_HIGH, /**< Maximum speed, the default state. */
    FAN_SPEED_MEDIUM,
    FAN_SPEED_LOW,
    FAN_SPEED_OFF /**< Fan is turned off. */
}
PL_FAN_SPEEDS;

/**
Used with the #PARAM_TRIGTAB_SIGNAL parameter ID.
Treated as int32 type.
*/
typedef enum PL_TRIGTAB_SIGNALS
{
    PL_TRIGTAB_SIGNAL_EXPOSE_OUT
}
PL_TRIGTAB_SIGNALS;

/**
Used with the #PARAM_PP_FEAT_ID parameter ID.
Treated as uns16 type.
*/
typedef enum PP_FEATURE_IDS
{
    PP_FEATURE_RING_FUNCTION,
    PP_FEATURE_BIAS,
    PP_FEATURE_BERT,
    PP_FEATURE_QUANT_VIEW,
    PP_FEATURE_BLACK_LOCK,
    PP_FEATURE_TOP_LOCK,
    PP_FEATURE_VARI_BIT,
    PP_FEATURE_RESERVED,            /**< Should not be used at any time moving forward. */
    PP_FEATURE_DESPECKLE_BRIGHT_HIGH,
    PP_FEATURE_DESPECKLE_DARK_LOW,
    PP_FEATURE_DEFECTIVE_PIXEL_CORRECTION,
    PP_FEATURE_DYNAMIC_DARK_FRAME_CORRECTION,
    PP_FEATURE_HIGH_DYNAMIC_RANGE,
    PP_FEATURE_DESPECKLE_BRIGHT_LOW,
    PP_FEATURE_DENOISING,
    PP_FEATURE_DESPECKLE_DARK_HIGH,
    PP_FEATURE_ENHANCED_DYNAMIC_RANGE,
    PP_FEATURE_MAX
}
PP_FEATURE_IDS;

/**
Used with the #PARAM_PP_PARAM_ID parameter ID.
*/
#define PP_MAX_PARAMETERS_PER_FEATURE   10

/**
Used with the #PARAM_PP_PARAM_ID parameter ID.
Treated as uns16 type.
*/
typedef enum PP_PARAMETER_IDS
{
    PP_PARAMETER_RF_FUNCTION                            = (PP_FEATURE_RING_FUNCTION * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_BIAS_ENABLED                             = (PP_FEATURE_BIAS * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_BIAS_LEVEL,
    PP_FEATURE_BERT_ENABLED                             = (PP_FEATURE_BERT * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_BERT_THRESHOLD,
    PP_FEATURE_QUANT_VIEW_ENABLED                       = (PP_FEATURE_QUANT_VIEW * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_QUANT_VIEW_E,
    PP_FEATURE_BLACK_LOCK_ENABLED                       = (PP_FEATURE_BLACK_LOCK * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_BLACK_LOCK_BLACK_CLIP,
    PP_FEATURE_TOP_LOCK_ENABLED                         = (PP_FEATURE_TOP_LOCK * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_TOP_LOCK_WHITE_CLIP,
    PP_FEATURE_VARI_BIT_ENABLED                         = (PP_FEATURE_VARI_BIT * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_VARI_BIT_BIT_DEPTH,
    PP_FEATURE_DESPECKLE_BRIGHT_HIGH_ENABLED            = (PP_FEATURE_DESPECKLE_BRIGHT_HIGH * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DESPECKLE_BRIGHT_HIGH_THRESHOLD,
    PP_FEATURE_DESPECKLE_BRIGHT_HIGH_MIN_ADU_AFFECTED,
    PP_FEATURE_DESPECKLE_DARK_LOW_ENABLED               = (PP_FEATURE_DESPECKLE_DARK_LOW * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DESPECKLE_DARK_LOW_THRESHOLD,
    PP_FEATURE_DESPECKLE_DARK_LOW_MAX_ADU_AFFECTED,
    PP_FEATURE_DEFECTIVE_PIXEL_CORRECTION_ENABLED       = (PP_FEATURE_DEFECTIVE_PIXEL_CORRECTION * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DYNAMIC_DARK_FRAME_CORRECTION_ENABLED    = (PP_FEATURE_DYNAMIC_DARK_FRAME_CORRECTION * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_HIGH_DYNAMIC_RANGE_ENABLED               = (PP_FEATURE_HIGH_DYNAMIC_RANGE * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DESPECKLE_BRIGHT_LOW_ENABLED             = (PP_FEATURE_DESPECKLE_BRIGHT_LOW * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DESPECKLE_BRIGHT_LOW_THRESHOLD,
    PP_FEATURE_DESPECKLE_BRIGHT_LOW_MAX_ADU_AFFECTED,
    PP_FEATURE_DENOISING_ENABLED                        = (PP_FEATURE_DENOISING * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DENOISING_NO_OF_ITERATIONS,
    PP_FEATURE_DENOISING_GAIN,
    PP_FEATURE_DENOISING_OFFSET,
    PP_FEATURE_DENOISING_LAMBDA,
    PP_FEATURE_DESPECKLE_DARK_HIGH_ENABLED              = (PP_FEATURE_DESPECKLE_DARK_HIGH * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_FEATURE_DESPECKLE_DARK_HIGH_THRESHOLD,
    PP_FEATURE_DESPECKLE_DARK_HIGH_MIN_ADU_AFFECTED,
    PP_FEATURE_ENHANCED_DYNAMIC_RANGE_ENABLED           = (PP_FEATURE_ENHANCED_DYNAMIC_RANGE * PP_MAX_PARAMETERS_PER_FEATURE),
    PP_PARAMETER_ID_MAX
}
PP_PARAMETER_IDS;

/**
Used with the #PARAM_SMART_STREAM_EXP_PARAMS and #PARAM_SMART_STREAM_DLY_PARAMS
parameter IDs and pl_create_smart_stream_struct() and
pl_release_smart_stream_struct() functions.
*/
typedef struct smart_stream_type
{
    uns16   entries;    /**< The number of entries in the array. */
    uns32*  params;     /**< The actual S.M.A.R.T. stream parameters. */
}
smart_stream_type;

/**
Used with the #PARAM_SMART_STREAM_MODE parameter ID.
Treated as uns16 type.
*/
typedef enum PL_SMT_MODES
{
    SMTMODE_ARBITRARY_ALL = 0,
    SMTMODE_MAX
}
PL_SMT_MODES;

/**
Used with the functions pl_exp_check_status(), and pl_exp_check_cont_status()
and pl_exp_check_cont_status_ex().
Treated as int16 type.
*/
/*
if NEWDATARDY or NEWDATAFIXED     READOUT_COMPLETE
else if RUNNING                   ACQUISITION_IN_PROGRESS
else if INITIALIZED or DONEDCOK   READOUT_NOT_ACTIVE
else                              READOUT_FAILED
*/
typedef enum PL_IMAGE_STATUSES
{
    READOUT_NOT_ACTIVE,
    EXPOSURE_IN_PROGRESS,
    READOUT_IN_PROGRESS,
    READOUT_COMPLETE,                   /**< Means frame available for a circular buffer acq. */
    FRAME_AVAILABLE = READOUT_COMPLETE, /**< New camera status indicating at least one frame is available. */
    READOUT_FAILED,
    ACQUISITION_IN_PROGRESS,
    MAX_CAMERA_STATUS
}
PL_IMAGE_STATUSES;

/**
Used with the function pl_exp_abort().
Treated as int16 type.
*/
typedef enum PL_CCS_ABORT_MODES
{
    CCS_NO_CHANGE = 0,
    CCS_HALT,
    CCS_HALT_CLOSE_SHTR,
    CCS_CLEAR,
    CCS_CLEAR_CLOSE_SHTR,
    CCS_OPEN_SHTR,
    CCS_CLEAR_OPEN_SHTR
}
PL_CCS_ABORT_MODES;

/**
Used with the #PARAM_BOF_EOF_ENABLE parameter ID.
Treated as int32 type.
*/
typedef enum PL_IRQ_MODES
{
    NO_FRAME_IRQS = 0,
    BEGIN_FRAME_IRQS,
    END_FRAME_IRQS,
    BEGIN_END_FRAME_IRQS
}
PL_IRQ_MODES;

/**
Used with the function pl_exp_setup_cont().
Treated as int16 type.
*/
typedef enum PL_CIRC_MODES
{
    CIRC_NONE = 0,
    CIRC_OVERWRITE,
    CIRC_NO_OVERWRITE
}
PL_CIRC_MODES;

/**
Used with the #PARAM_EXP_RES parameter ID.
Treated as int32 type.
*/
typedef enum PL_EXP_RES_MODES
{
    EXP_RES_ONE_MILLISEC = 0,
    EXP_RES_ONE_MICROSEC,
    EXP_RES_ONE_SEC
}
PL_EXP_RES_MODES;

/**
Used with the function pl_io_script_control().
Treated as uns32 type.
*/
typedef enum PL_SRC_MODES
{
    SCR_PRE_OPEN_SHTR = 0,
    SCR_POST_OPEN_SHTR,
    SCR_PRE_FLASH,
    SCR_POST_FLASH,
    SCR_PRE_INTEGRATE,
    SCR_POST_INTEGRATE,
    SCR_PRE_READOUT,
    SCR_POST_READOUT,
    SCR_PRE_CLOSE_SHTR,
    SCR_POST_CLOSE_SHTR
}
PL_SRC_MODES;

/**
Used with the functions pl_cam_register_callback*() and pl_cam_deregister_callback().
Used directly as an enum type without casting to any integral type.
*/
typedef enum PL_CALLBACK_EVENT
{
    PL_CALLBACK_BOF = 0,
    PL_CALLBACK_EOF,
    PL_CALLBACK_CHECK_CAMS,
    PL_CALLBACK_CAM_REMOVED,
    PL_CALLBACK_CAM_RESUMED,
    PL_CALLBACK_MAX
}
PL_CALLBACK_EVENT;

typedef struct rgn_type
{
    uns16 s1;   /**< First pixel in the serial register. */
    uns16 s2;   /**< Last pixel in the serial register. */
    uns16 sbin; /**< Serial binning for this region. */
    uns16 p1;   /**< First row in the parallel register. */
    uns16 p2;   /**< Last row in the parallel register. */
    uns16 pbin; /**< Parallel binning for this region. */
}
rgn_type;

typedef struct io_struct
{
    uns16 io_port;          /**< I/O port address. */
    uns32 io_type;          /**< I/O port type (TTL, DAC, etc.) */
    flt64 state;            /**< Desired output state for the port. */
    struct io_struct* next; /**< Linked list pointer.*/
}
io_entry;

typedef struct io_list
{
    io_entry pre_open;
    io_entry post_open;
    io_entry pre_flash;
    io_entry post_flash;
    io_entry pre_integrate;
    io_entry post_integrate;
    io_entry pre_readout;
    io_entry post_readout;
    io_entry pre_close;
    io_entry post_close;
}
io_list;

typedef struct active_camera_type
{
    uns16       shutter_close_delay; /**< Number of milliseconds for the shutter to close. */
    uns16       shutter_open_delay;  /**< Number of milliseconds for the shutter to open. */
    uns16       rows;                /**< Parallel size of the sensor active area. */
    uns16       cols;                /**< Serial size of the sensor active area. */
    uns16       prescan;             /**< Serial pixels before the active area. */
    uns16       postscan;            /**< Serial pixels after the active area. */
    uns16       premask;             /**< Parallel rows before the active area. */
    uns16       postmask;            /**< Parallel rows after the active area. */
    uns16       preflash;            /**< Number of milliseconds to flash the diode ring. */
    uns16       clear_count;         /**< Number of times to clear the sensor before exposure. */
    uns16       preamp_delay;        /**< Number of milliseconds for the preamp to settle. */
    rs_bool     mpp_selectable;      /**< Indicates MPP mode can be selected. */
    rs_bool     frame_selectable;    /**< Indicates frame transfer can be selected. */
    int16       do_clear;            /**< Clear: Never, Each Exposure, Each Sequence. */
    int16       open_shutter;        /**< Open: Never, Each Exposure, Each Sequence. */
    rs_bool     mpp_mode;            /**< Enable or disable MPP mode. */
    rs_bool     frame_transfer;      /**< Enable or disable frame transfer operation. */
    rs_bool     alt_mode;            /**< Enable or disable Alternate Parallel mode. */
    uns32       exp_res;             /**< Exposure resolution. */
    io_list*    io_hdr;              /**< Pointer to list of I/O script control commands. */
}
active_camera_type;

/******************************************************************************/
/* Start of Frame Metadata Types                                              */
/******************************************************************************/

/******************************************************************************/
/* Data headers and camera shared types                                       */

/**
Used in #md_frame_header structure.
Treated as uns8 type.
*/
typedef enum PL_MD_FRAME_FLAGS
{
    PL_MD_FRAME_FLAG_ROI_TS_SUPPORTED = 0x01, /**< check this bit before using the timestampBOR and timestampEOR */
    PL_MD_FRAME_FLAG_UNUSED_2         = 0x02,
    PL_MD_FRAME_FLAG_UNUSED_3         = 0x04,
    PL_MD_FRAME_FLAG_UNUSED_4         = 0x10,
    PL_MD_FRAME_FLAG_UNUSED_5         = 0x20,
    PL_MD_FRAME_FLAG_UNUSED_6         = 0x40,
    PL_MD_FRAME_FLAG_UNUSED_7         = 0x80
}
PL_MD_FRAME_FLAGS;

/**
Used in #md_frame_roi_header structure.
Treated as uns8 type.
*/
typedef enum PL_MD_ROI_FLAGS
{
    PL_MD_ROI_FLAG_INVALID   = 0x01, /**< ROI is invalid (centroid unavailable). */
    PL_MD_ROI_FLAG_UNUSED_2  = 0x02,
    PL_MD_ROI_FLAG_UNUSED_3  = 0x04,
    PL_MD_ROI_FLAG_UNUSED_4  = 0x10,
    PL_MD_ROI_FLAG_UNUSED_5  = 0x20,
    PL_MD_ROI_FLAG_UNUSED_6  = 0x40,
    PL_MD_ROI_FLAG_UNUSED_7  = 0x80
}
PL_MD_ROI_FLAGS;

/**
The signature is located in the first 4 bytes of the frame header. The signature
is checked before any metadata-related operations are executed on the buffer.
*/
#define PL_MD_FRAME_SIGNATURE 5328208

/*
The structures are shared beween platforms, thus we must ensure that no
compiler will apply different struct alignment.
*/
#pragma pack(push)
#pragma pack(1)

/**
This is a frame header that is located before each frame. The size of this
structure must remain constant. The structure is generated by the camera
and should be 16-byte aligned.
*/
typedef struct md_frame_header
{                                 /* TOTAL: 48 bytes */
    uns32       signature;        /* 4B (see the signature definition) */
    uns8        version;          /* 1B (must be 1 in the first release) */

    uns32       frameNr;          /* 4B (1-based, reset with each acquisition) */
    uns16       roiCount;         /* 2B (Number of ROIs in the frame, at least 1) */

    /* The final timestamp = timestampBOF * timestampResNs (in nano-seconds) */
    uns32       timestampBOF;     /* 4B (depends on resolution) */
    uns32       timestampEOF;     /* 4B (depends on resolution) */
    uns32       timestampResNs;   /* 4B (1=1ns, 1000=1us, 5000000=5ms, ...) */

    /* The final exposure time = exposureTime * exposureTimeResNs (nano-seconds) */
    uns32       exposureTime;     /* 4B (depends on resolution) */
    uns32       exposureTimeResNs;/* 4B (1=1ns, 1000=1us, 5000000=5ms, ...) */

    /* ROI timestamp resolution is stored here, no need to transfer with each ROI */
    uns32       roiTimestampResNs;/* 4B ROI timestamps resolution */

    uns8        bitDepth;         /* 1B (must be 10, 13, 14, 16, etc) */
    uns8        colorMask;        /* 1B (corresponds to PL_COLOR_MODES) */
    uns8        flags;            /* 1B Frame flags */
    uns16       extendedMdSize;   /* 2B (must be 0 or actual ext md data size) */
    uns8        _reserved[8];
}
md_frame_header;

/**
This is a ROI header that is located before every ROI data. The size of this
structure must remain constant. The structure is genereated by the camera
and should be 16-byte aligned.
*/
typedef struct md_frame_roi_header
{                              /* TOTAL: 32 bytes */
    uns16    roiNr;            /* 2B (1-based, reset with each frame) */

    /* The final timestamp = timestampBOR * roiTimestampResNs */
    uns32    timestampBOR;     /* 4B (depends on RoiTimestampResNs) */
    uns32    timestampEOR;     /* 4B (depends on RoiTimestampResNs) */

    rgn_type roi;              /* 12B (ROI coordinates and binning) */

    uns8     flags;            /* 1B ROI flags */
    uns16    extendedMdSize;   /* 2B (must be 0 or actual ext md data size in bytes) */
    uns8    _reserved[7];
}
md_frame_roi_header;

#pragma pack(pop)

/******************************************************************************/
/* Extended metadata related structures                                       */

/**
Maximum number of extended metadata tags supported.
*/
#define PL_MD_EXT_TAGS_MAX_SUPPORTED 255

/**
Available extended metadata tags.
Currently there are no extended metadata available.
Used in #md_ext_item_info structure.
Used directly as an enum type without casting to any integral type.
*/
typedef enum PL_MD_EXT_TAGS
{
    PL_MD_EXT_TAG_MAX = 0
}
PL_MD_EXT_TAGS;

/**
This structure describes the extended metadata TAG. This information is
retrieved from an internal table. User need this to correctly read and
display the extended metadata value.
*/
typedef struct md_ext_item_info
{
    PL_MD_EXT_TAGS tag;
    uns16          type;
    uns16          size;
    const char*    name;
}
md_ext_item_info;

/**
An extended metadata item together with its value. The user will retrieve a
collection of these items.
*/
typedef struct md_ext_item
{
    md_ext_item_info*  tagInfo;
    void*              value;
}
md_ext_item;

/**
A collection of decoded extended metadata.
*/
typedef struct md_ext_item_collection
{
    md_ext_item     list[PL_MD_EXT_TAGS_MAX_SUPPORTED];
    md_ext_item*    map[PL_MD_EXT_TAGS_MAX_SUPPORTED];
    uns16           count;
}
md_ext_item_collection;

/**
This is a helper structure that is used to decode the md_frame_roi_header. Since
the header cannot contain any pointers PVCAM will calculate all information
using offsets from frame & ROI headers.
The structure must be created using the pl_md_create_frame_struct() function.
Please note the structure keeps only pointers to data residing in the image
buffer. Once the buffer is deleted the contents of the structure become invalid.
*/
typedef struct md_frame_roi
{
    md_frame_roi_header*    header;         /**< Points directly to the header within the buffer. */
    void*                   data;           /**< Points to the ROI image data. */
    uns32                   dataSize;       /**< Size of the ROI image data in bytes. */
    void*                   extMdData;      /**< Points directly to ext/ MD data within the buffer. */
    uns16                   extMdDataSize;  /**< Size of the ext. MD buffer. */
}
md_frame_roi;

/**
This is a helper structure that is used to decode the md_frame_header. Since
the header cannot contain any pointers we need to calculate all information
using only offsets.
Please note the structure keeps only pointers to data residing in the image
buffer. Once the buffer is deleted the contents of the structure become invalid.
*/
typedef struct md_frame
{
    md_frame_header*     header;       /**< Points directly to the header withing the buffer. */
    void*                extMdData;    /**< Points directly to ext/ MD data within the buffer. */
    uns16                extMdDataSize;/**< Size of the ext. MD buffer in bytes. */
    rgn_type             impliedRoi;   /**< Implied ROI calculated during decoding. */

    md_frame_roi*        roiArray;     /**< An array of ROI descriptors. */
    uns16                roiCapacity;  /**< Number of ROIs the structure can hold. */
    uns16                roiCount;     /**< Number of ROIs found during decoding. */
}
md_frame;

/******************************************************************************/
/*End of Frame Metadata Types                                                 */
/******************************************************************************/

/******************************************************************************/
/**
@addtogroup grp_pm_deprecated_typedefs
@{
*/

typedef PVCAM_FRAME_INFO_GUID*  PPVCAM_FRAME_INFO_GUID;
typedef FRAME_INFO*             PFRAME_INFO;
typedef smart_stream_type*      smart_stream_type_ptr;
typedef rgn_type*               rgn_ptr;
typedef const rgn_type*         rgn_const_ptr;
typedef io_entry*               io_entry_ptr;
typedef io_list*                io_list_ptr;
typedef io_list**               io_list_ptr_ptr;
typedef active_camera_type*     active_camera_ptr;

/** @} */ /* grp_pm_deprecated_typedefs */

/******************************************************************************/
/**
@defgroup grp_single_byte_macros Single-byte macros

These will pull out a single uns8 from either a two-uns8 integer quantity,
or a four-uns8 integer quantity and vice versa.

They ARE NOT machine specific.

The software using them is responsible for handling the interface requirements
of the NGC camera, which expects the high uns8 first, then the lower bytes
in order.  There are several macros.

@{
*/

/** Extracts the most significant byte from a two-uns8 integer input. */
#define MS16_BYTE(two_byte_value) ( (uns8)((two_byte_value) >> 8) )
/** Extracts the least significant byte from a two-uns8 integer input. */
#define LS16_BYTE(two_byte_value) ( (uns8)((two_byte_value) >> 0) )

/** Extracts the most significant byte from a four-uns8 integer input. */
#define MS32_BYTE(four_byte_value) ( (uns8)((four_byte_value) >> 24) )
/** Extracts the middle-high significant byte from a four-uns8 integer input. */
#define MH32_BYTE(four_byte_value) ( (uns8)((four_byte_value) >> 16) )
/** Extracts the middle-low significant byte from a four-uns8 integer input. */
#define ML32_BYTE(four_byte_value) ( (uns8)((four_byte_value) >>  8) )
/** Extracts the least significant byte from a four-uns8 integer input. */
#define LS32_BYTE(four_byte_value) ( (uns8)((four_byte_value) >>  0) )

/** Produces a two-uns8 integer value from high & low uns8 input. */
#define VAL_UNS16(ms_byte,ls_byte) (\
    ((uns16)((uns8)(ms_byte)) << 8) |\
    ((uns16)((uns8)(ls_byte)) << 0) )

/** Produces a four-uns8 integer value from 4 input bytes. */
#define VAL_UNS32(ms_byte,mh_byte,ml_byte,ls_byte) (\
    ((uns32)((uns8)(ms_byte)) << 24) |\
    ((uns32)((uns8)(mh_byte)) << 16) |\
    ((uns32)((uns8)(ml_byte)) <<  8) |\
    ((uns32)((uns8)(ls_byte)) <<  0) )

/** @} */ /* grp_single_byte_macros */

/******************************************************************************/
/* Content which is needed to communicate with the PVCAM DLLs */

typedef int16 pm_script_hook (int16 hcam,
                              uns16 exp_total,
                              uns16 rgn_total,
                              const rgn_type* rgn_array,
                              int16 mode,
                              uns32 exposure_time,
                              uns32* pixels,
                              active_camera_type* active_camera);

/**
Data type used by pl_get_param() with #ATTR_TYPE.
@{
*/
#define TYPE_INT16                  1
#define TYPE_INT32                  2
#define TYPE_FLT64                  4
#define TYPE_UNS8                   5
#define TYPE_UNS16                  6
#define TYPE_UNS32                  7
#define TYPE_UNS64                  8
#define TYPE_ENUM                   9
#define TYPE_BOOLEAN               11
#define TYPE_INT8                  12
#define TYPE_CHAR_PTR              13
#define TYPE_VOID_PTR              14
#define TYPE_VOID_PTR_PTR          15
#define TYPE_INT64                 16
#define TYPE_SMART_STREAM_TYPE     17
#define TYPE_SMART_STREAM_TYPE_PTR 18
#define TYPE_FLT32                 19
/** @} */

/*
Defines for classes.
*/
#define CLASS0      0          /* Camera Communications */
#define CLASS2      2          /* Configuration/Setup */
#define CLASS3      3          /* Data Acuisition */

/******************************************************************************/
/* Start of parameter ID definitions.                                         */
/* Format: TTCCxxxx, where TT = Data type, CC = Class, xxxx = ID number       */
/******************************************************************************/

/* DEVICE DRIVER PARAMETERS */

#define PARAM_DD_INFO_LENGTH        ((CLASS0<<16) + (TYPE_INT16<<24) + 1)
#define PARAM_DD_VERSION            ((CLASS0<<16) + (TYPE_UNS16<<24) + 2)
#define PARAM_DD_RETRIES            ((CLASS0<<16) + (TYPE_UNS16<<24) + 3)
#define PARAM_DD_TIMEOUT            ((CLASS0<<16) + (TYPE_UNS16<<24) + 4)
#define PARAM_DD_INFO               ((CLASS0<<16) + (TYPE_CHAR_PTR<<24) + 5)

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
    DEPRECATED rs_bool PV_DECL pl_cam_check (int16 hcam);
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
    /**
    @addtogroup grp_pm_deprecated_functions
    Most of the functions are obsolete and their corresponding PARAM_
    parameters should be used with pl_get_param(), pl_set_param(),
    pl_get_enum_param() and pl_enum_str_length().
    @{
    */

    DEPRECATED rs_bool PV_DECL pl_exp_init_seq (void);
    DEPRECATED rs_bool PV_DECL pl_exp_uninit_seq (void);
    DEPRECATED rs_bool PV_DECL pl_dd_get_info (int16 hcam, int16 bytes, char* text);
    /* Use PARAM_DD_INFO                                              */
    DEPRECATED rs_bool PV_DECL pl_dd_get_info_length (int16 hcam, int16* bytes);
    /* Use PARAM_DD_INFO_LENGTH                                       */
    DEPRECATED rs_bool PV_DECL pl_dd_get_ver (int16 hcam, uns16* dd_version);
    /* Use PARAM_DD_VERSION                                           */
    DEPRECATED rs_bool PV_DECL pl_dd_get_retries (int16 hcam, uns16* max_retries);
    DEPRECATED rs_bool PV_DECL pl_dd_set_retries (int16 hcam, uns16 max_retries);
    /* Use PARAM_DD_RETRIES                                           */
    DEPRECATED rs_bool PV_DECL pl_dd_get_timeout (int16 hcam, uns16* m_sec);
    DEPRECATED rs_bool PV_DECL pl_dd_set_timeout (int16 hcam, uns16 m_sec);
    /* Use PARAM_DD_TIMEOUT                                           */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_adc_offset (int16 hcam, int16* offset);
    DEPRECATED rs_bool PV_DECL pl_ccd_set_adc_offset (int16 hcam, int16 offset);
    /* Use PARAM_ADC_OFFSET                                           */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_chip_name (int16 hcam, char* chip_name);
    /* Use PARAM_CHIP_NAME                                            */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_clear_cycles (int16 hcam, uns16* clear_cycles);
    DEPRECATED rs_bool PV_DECL pl_ccd_set_clear_cycles (int16 hcam, uns16 clr_cycles);
    /* Use PARAM_CLEAR_CYCLES                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_clear_mode (int16 hcam, int16* clear_mode);
    DEPRECATED rs_bool PV_DECL pl_ccd_set_clear_mode (int16 hcam, int16 ccd_clear);
    /* Use PARAM_CLEAR_MODE                                           */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_color_mode (int16 hcam, uns16* color_mode);
    /* Use PARAM_COLOR_MODE                                           */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_cooling_mode (int16 hcam, int16* cooling);
    /* Use PARAM_COOLING_MODE                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_frame_capable (int16 hcam, rs_bool* frame_capable);
    /* Use PARAM_FRAME_CAPABLE                                        */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_fwell_capacity (int16 hcam, uns32* fwell_capacity);
    /* Use PARAM_FWELL_CAPACITY                                       */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_mpp_capable (int16 hcam, int16* mpp_capable);
    /* Use PARAM_MPP_CAPABLE                                          */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_preamp_dly (int16 hcam, uns16* preamp_dly);
    /* Use PARAM_PREAMP_DELAY                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_preamp_off_control (int16 hcam,
                                                              uns32* preamp_off_control);
    DEPRECATED rs_bool PV_DECL pl_ccd_set_preamp_off_control (int16 hcam,
                                                              uns32 preamp_off_control);
    /* Use PARAM_PREAMP_OFF_CONTROL                                   */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_preflash (int16 hcam, uns16* pre_flash);
    /* Use PARAM_PREFLASH                                             */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_pmode (int16 hcam, int16* pmode);
    DEPRECATED rs_bool PV_DECL pl_ccd_set_pmode (int16 hcam, int16 pmode);
    /* Use PARAM_PMODE                                                */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_premask (int16 hcam, uns16* pre_mask);
    /* Use PARAM_PREMASK                                              */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_prescan (int16 hcam, uns16* prescan);
    /* Use PARAM_PRESCAN                                              */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_postmask (int16 hcam, uns16* post_mask);
    /* Use PARAM_POSTMASK                                             */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_postscan (int16 hcam, uns16* postscan);
    /* Use PARAM_POSTSCAN                                             */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_par_size (int16 hcam, uns16* par_size);
    /* Use PARAM_PAR_SIZE                                             */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_ser_size (int16 hcam, uns16* ser_size);
    /* Use PARAM_SER_SIZE                                             */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_serial_num (int16 hcam, uns16* serial_num);
    /* Use PARAM_SERIAL_NUM                                           */
    DEPRECATED rs_bool PV_DECL pl_ccs_get_status (int16 hcam, int16* ccs_status);
    /* Use PARAM_CCS_STATUS                                           */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_summing_well (int16 hcam, rs_bool* s_well_exists);
    /* Use PARAM_SUMMING_WELL                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_tmp (int16 hcam, int16* cur_tmp);
    DEPRECATED rs_bool PV_DECL pl_ccd_get_tmp_range (int16 hcam, int16* tmp_hi_val,
                                                     int16* tmp_lo_val);
    /* Use PARAM_TEMP                                                 */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_tmp_setpoint (int16 hcam, int16* tmp_setpoint);
    DEPRECATED rs_bool PV_DECL pl_ccd_set_tmp_setpoint (int16 hcam, int16 tmp_setpoint);
    /* Use PARAM_TEMP_SETPOINT                                        */
    DEPRECATED rs_bool PV_DECL pl_ccd_set_readout_port (int16 , int16 );
    DEPRECATED rs_bool PV_DECL pl_ccd_get_pix_par_dist (int16 hcam, uns16* pix_par_dist);
    /* Use PARAM_PIX_PAR_DIST                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_pix_par_size (int16 hcam, uns16* pix_par_size);
    /* Use PARAM_PIX_PAR_SIZE                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_pix_ser_dist (int16 hcam, uns16* pix_ser_dist);
    /* Use PARAM_PIX_SER_DIST                                         */
    DEPRECATED rs_bool PV_DECL pl_ccd_get_pix_ser_size (int16 hcam, uns16* pix_ser_size);
    /* Use PARAM_PIX_SER_SIZE                                         */
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_bits (int16 hcam, int16* spdtab_bits);
    /* Use PARAM_BIT_DEPTH                                            */
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_gain (int16 hcam, int16* spdtab_gain);
    DEPRECATED rs_bool PV_DECL pl_spdtab_set_gain (int16 hcam, int16 spdtab_gain);
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_max_gain (int16 hcam,
                                                       int16* spdtab_max_gain);
    /* Use PARAM_GAIN_INDEX                                           */
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_num (int16 hcam, int16* spdtab_num);
    DEPRECATED rs_bool PV_DECL pl_spdtab_set_num (int16 hcam, int16 spdtab_num);
    /* Use PARAM_SPDTAB_INDEX                                         */
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_entries (int16 hcam, int16* spdtab_entries);
    /* Use PARAM_SPDTAB_INDEX (ATTR_MAX)                              */
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_port (int16 hcam, int16* spdtab_port);
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_port_total (int16 hcam, int16* total_ports);
    /* Use PARAM_READOUT_PORT                                         */
    DEPRECATED rs_bool PV_DECL pl_spdtab_get_time (int16 hcam, uns16* spdtab_time);
    /* Use PARAM_PIX_TIME                                             */
    DEPRECATED rs_bool PV_DECL pl_shtr_get_close_dly (int16 hcam, uns16* shtr_close_dly);
    DEPRECATED rs_bool PV_DECL pl_shtr_set_close_dly (int16 hcam, uns16 shtr_close_dly);
    /* Use PARAM_SHTR_CLOSE_DELAY                                     */
    DEPRECATED rs_bool PV_DECL pl_shtr_get_open_dly (int16 hcam, uns16* shtr_open_dly);
    DEPRECATED rs_bool PV_DECL pl_shtr_set_open_dly (int16 hcam, uns16 shtr_open_dly);
    /* Use PARAM_SHTR_OPEN_DELAY                                      */
    DEPRECATED rs_bool PV_DECL pl_shtr_get_open_mode (int16 hcam, int16* shtr_open_mode);
    DEPRECATED rs_bool PV_DECL pl_shtr_set_open_mode (int16 hcam, int16 shtr_open_mode);
    /* Use PARAM_SHTR_OPEN_MODE                                       */
    DEPRECATED rs_bool PV_DECL pl_shtr_get_status (int16 hcam, int16* shtr_status);
    /* Use PARAM_SHTR_STATUS                                          */
    DEPRECATED rs_bool PV_DECL pl_exp_get_time_seq (int16 hcam, uns16* exp_time);
    DEPRECATED rs_bool PV_DECL pl_exp_set_time_seq (int16 hcam, uns16 exp_time);
    /* Use PARAM_EXP_TIME                                             */
    DEPRECATED rs_bool PV_DECL pl_exp_check_progress (int16 hcam, int16* status,
                                                      uns32* bytes_arrived);
    /* Use pl_exp_check_status or pl_exp_check_cont_status */

    DEPRECATED rs_bool PV_DECL pl_exp_set_cont_mode (int16 hcam, int16 mode);
    DEPRECATED rs_bool PV_DECL pl_subsys_do_diag (int16 hcam, uns8 subsys_id,
                                                  uns16* err_code);
    DEPRECATED rs_bool PV_DECL pl_subsys_get_id (int16 hcam, uns8 subsys_id,
                                                 uns16* part_num, uns8* revision);
    DEPRECATED rs_bool PV_DECL pl_subsys_get_name (int16 hcam, uns8 subsys_id,
                                                   char* subsys_name);
    DEPRECATED rs_bool PV_DECL pl_exp_get_driver_buffer (int16 hcam,
                                                         void** pixel_stream,
                                                         uns32* byte_cnt);
    DEPRECATED rs_bool PV_DECL pl_buf_init (void);
    DEPRECATED rs_bool PV_DECL pl_buf_uninit (void);

    DEPRECATED rs_bool PV_DECL pl_buf_alloc (int16* hbuf, int16 exp_total,
                                             int16 bit_depth, int16 rgn_total,
                                             const rgn_type* rgn_array);
    DEPRECATED rs_bool PV_DECL pl_buf_get_exp_date (int16 hbuf, int16 exp_num,
                                                    int16* year, uns8* month,
                                                    uns8* day, uns8* hour,
                                                    uns8* min, uns8* sec,
                                                    uns16* msec);
    DEPRECATED rs_bool PV_DECL pl_buf_set_exp_date (int16 hbuf, int16 exp_num, int16 year,
                                                    uns8 month, uns8 day, uns8 hour,
                                                    uns8 min, uns8 sec, uns16 msec);
    DEPRECATED rs_bool PV_DECL pl_buf_get_exp_time (int16 hbuf, int16 exp_num,
                                                    uns32* exp_msec);
    DEPRECATED rs_bool PV_DECL pl_buf_get_exp_total (int16 hbuf, int16* total_exps);
    DEPRECATED rs_bool PV_DECL pl_buf_get_img_bin (int16 himg, int16* ibin, int16* jbin);
    DEPRECATED rs_bool PV_DECL pl_buf_get_img_handle (int16 hbuf, int16 exp_num,
                                                      int16 img_num, int16* himg);
    DEPRECATED rs_bool PV_DECL pl_buf_get_img_ofs (int16 himg, int16* s_ofs, int16* p_ofs);
    DEPRECATED rs_bool PV_DECL pl_buf_get_img_ptr (int16 himg, void** img_addr);
    DEPRECATED rs_bool PV_DECL pl_buf_get_img_size (int16 himg, int16* x_size, int16* y_size);
    DEPRECATED rs_bool PV_DECL pl_buf_get_img_total (int16 hbuf, int16* totl_imgs);
    DEPRECATED rs_bool PV_DECL pl_buf_get_size (int16 hbuf, int32* buf_size);
    DEPRECATED rs_bool PV_DECL pl_buf_free (int16 hbuf);
    DEPRECATED rs_bool PV_DECL pl_buf_get_bits (int16 hbuf, int16* bit_depth);
    DEPRECATED rs_bool PV_DECL pl_exp_unravel (int16 hcam, uns16 exposure,
                                               void* pixel_stream, uns16 rgn_total,
                                               const rgn_type* rgn_array,
                                               uns16** array_list);
    DEPRECATED rs_bool PV_DECL pl_exp_wait_start_xfer (int16 hcam, uns32 tlimit);
    DEPRECATED rs_bool PV_DECL pl_exp_wait_end_xfer (int16 hcam, uns32 tlimit);

    DEPRECATED rs_bool PV_DECL pv_cam_get_ccs_mem (int16 hcam, uns16* size);
    DEPRECATED rs_bool PV_DECL pv_cam_send_debug (int16 hcam, char* debug_str,
                                                  uns16 reply_len, char* reply_str);
    DEPRECATED rs_bool PV_DECL pv_cam_write_read (int16 hcam, uns8 c_class, uns16 write_bytes,
                                                  uns8* write_array, uns8* read_array);
    DEPRECATED rs_bool PV_DECL pv_dd_active (int16 hcam, void* pixel_stream);
    DEPRECATED rs_bool PV_DECL pv_exp_get_bytes (int16 hcam, uns32* exp_bytes);
    DEPRECATED rs_bool PV_DECL pv_exp_get_script (int16 hcam, rs_bool* script_valid);
    DEPRECATED rs_bool PV_DECL pv_exp_get_status (int16 hcam, int16* status,
                                                  uns32* byte_cnt, uns32* frame_cnt);
    DEPRECATED rs_bool PV_DECL pv_exp_set_bytes (int16 hcam, uns32 frame_count,
                                                 uns32 seq_bytes, void* pixel_stream);
    DEPRECATED rs_bool PV_DECL pv_exp_set_script (int16 hcam, rs_bool script_valid);
    DEPRECATED rs_bool PV_DECL pv_set_error_code (int16 omode,int16 err_code);
    DEPRECATED rs_bool PV_DECL pv_cam_do_reads (int16 hcam);
    DEPRECATED rs_bool PV_DECL pv_free (void* block, int16 heap);
    DEPRECATED void*   PV_DECL pv_malloc (uns32 size, int16 heap);
    DEPRECATED void*   PV_DECL pv_realloc (void* block, uns32 size, int16 heap);
    DEPRECATED rs_bool PV_DECL pv_script_set_hook (pm_script_hook* pfn);
    DEPRECATED rs_bool PV_DECL pv_ccd_get_accum_capable (int16 hcam, rs_bool* accum_capable);
    DEPRECATED rs_bool PV_DECL pv_exp_get_frames (int16 hcam, uns32* exp_frames);
    DEPRECATED rs_bool PV_DECL pv_exp_set_frames (int16 hcam, uns32 exp_frames);
    DEPRECATED rs_bool PV_DECL pv_exp_set_no_readout_timeout (int16 hcam);
    DEPRECATED rs_bool PV_DECL pv_exp_reset_no_readout_timeout (int16 hcam);
    DEPRECATED rs_bool PV_DECL pm_cam_write_read (int16 hcam, uns8 c_class, uns16 write_bytes,
                                                  uns8* write_array, uns8* read_array);
    DEPRECATED rs_bool PV_DECL pl_ddi_get_ver (uns16* ddi_version);
    DEPRECATED rs_bool PV_DECL pl_cam_get_diags (int16 hcam);

    /** @} */ /* grp_pm_deprecated_functions */

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
