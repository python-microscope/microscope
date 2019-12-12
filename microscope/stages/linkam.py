#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 Mick Phillips <mick.phillips@gmail.com>
##
## Microscope is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Microscope is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""A microscope interface to Linkam stages.

This module requires the LinkamSDK library and a license file, available
from Linkam Scientific Instruments.

Currently, this module supports on the the correlative microscopy stage,
but should be readily extensible to support other Linkam stages.

NOTE: this module does not run correctly with python optimisations in
use. When invoked with python -O, there seem to be issues with accessing
ctypes objects.
  * get_status() throws AttributeError "c_ulonglong has no attribute 'flags'";
  * get_id returns an empty string, not the device serial number."""

import ctypes
from ctypes import addressof, byref, POINTER
from enum import Enum, IntEnum
from microscope import devices
from microscope.devices import Setting
import datetime, time

_max_version_length = 20

# Typedefs from C headers
_int8_t = ctypes.c_int8
_uint8_t = ctypes.c_uint8
_int16_t = ctypes.c_int16
_uint16_t = ctypes.c_uint16
_int32_t = ctypes.c_int32
_uint32_t = ctypes.c_uint32
_int64_t = ctypes.c_int64
_uint64_t = ctypes.c_uint64
_float64_t = ctypes.c_double
_float32_t = ctypes.c_float
_float64_t = ctypes.c_double
_float32_t = ctypes.c_float
_CommsHandle = ctypes.c_uint64

class _CommsInfo(ctypes.Structure):
    """CommsInfo struct from C headers"""
    _fields_ = [("type", ctypes.c_uint),
                ("info", ctypes.c_char * 124)]

    @property
    def view_of_info(self):
        """Provide a view of the info field so that its subfields can be accessed"""
        if self.type == 0:
            ptype = None
        elif self.type == 1:
            ptype = POINTER(_SerialCommsInfo)
        elif self.type == 2:
            ptype = POINTER(_USBCommsInfo)

        if ptype is None:
            return self.info
        else:
            offset = getattr(_CommsInfo, 'info').offset
            return _USBCommsInfo.from_buffer(self, getattr(_CommsInfo, 'info').offset)


class _SerialCommsInfo(ctypes.Structure):
    """SerialCommsInfo struct from C headers"""
    _fields_ = [("port", ctypes.c_char * 64),
                ("baudrate", ctypes.c_uint32),
                ("bytesize", ctypes.c_uint),
                ("parity", ctypes.c_uint),
                ("stopbits", ctypes.c_uint),
                ("flowcontrol", ctypes.c_uint),
                ("timeout", ctypes.c_uint32),
                ("padding", ctypes.c_uint8 * 36)]


class _USBCommsInfo(ctypes.Structure):
    """USBCommsInfo struct from C headers"""
    _fields_ = [("vendorID", ctypes.c_uint16),
                ("productID", ctypes.c_uint16),
                ("serialNumber", ctypes.c_char * 17),
                ("padding", ctypes.c_uint8 * 83)]


class _StageGroup(Enum):
    """StageGroup enum from C headers"""
    START = 0x0000
    Standard = 0x0000
    Peltier = 0x0001
    Gradient = 0x0002
    DifferentialScanningCalorimetry = 0x0003
    Vacuum = 0x0004
    Pressure = 0x0005
    MotorDriven = 0x0006
    TensileTest = 0x0007
    CambridgeShearingSystem = 0x0008
    TemperatureControlled = 0x0009
    Warm = 0x000A
    CorrelativeMicroscopy = 0x000B
    IndiumTinOxideWarm = 0x000C
    TemperatureControlledVacuum = 0x000D
    TensileTestV2 = 0x000E
    DifferentialScanningCalorimetryV2 = 0x000F
    FreezeDryingVialSystem = 0x0010
    MAX = 0x7FF


class _StageConfigFlags(ctypes.Structure):
    """StageConfig.flags struct from C headers"""
    _fields_ = [("standardStage", ctypes.c_uint, 1),
                ("highTempStage", ctypes.c_uint, 1),
                ("peltierStage", ctypes.c_uint, 1),
                ("gradedStage", ctypes.c_uint, 1),
                ("tensileStage", ctypes.c_uint, 1),
                ("dscStage", ctypes.c_uint, 1),
                ("warmStage", ctypes.c_uint, 1),
                ("itoStage", ctypes.c_uint, 1),
                ("css450Stage", ctypes.c_uint, 1),
                ("correlativeStage", ctypes.c_uint, 1),
                ("unused10", ctypes.c_uint, 1),
                ("unused11", ctypes.c_uint, 1),
                ("unused12", ctypes.c_uint, 1),
                ("unused13", ctypes.c_uint, 1),
                ("unused14", ctypes.c_uint, 1),
                ("unused15", ctypes.c_uint, 1),
                ("unused16", ctypes.c_uint, 1),
                ("unused17", ctypes.c_uint, 1),
                ("unused18", ctypes.c_uint, 1),
                ("unused19", ctypes.c_uint, 1),
                ("unused20", ctypes.c_uint, 1),
                ("coolingManual", ctypes.c_uint, 1),
                ("coolingAutomatic", ctypes.c_uint, 1),
                ("coolingDual", ctypes.c_uint, 1),
                ("coolingDualSpeedIndependent", ctypes.c_uint, 1),
                ("unused25", ctypes.c_uint, 1),
                ("heater1", ctypes.c_uint, 1),
                ("heater1TempCtrl", ctypes.c_uint, 1),
                ("heater1TempCtrlProbe", ctypes.c_uint, 1),
                ("unused29", ctypes.c_uint, 1),
                ("unused30", ctypes.c_uint, 1),
                ("unused31", ctypes.c_uint, 1),
                ("unused32", ctypes.c_uint, 1),
                ("unused33", ctypes.c_uint, 1),
                ("unused34", ctypes.c_uint, 1),
                ("unused35", ctypes.c_uint, 1),
                ("heater2", ctypes.c_uint, 1),
                ("heater12IndependentLimits", ctypes.c_uint, 1),
                ("unused38", ctypes.c_uint, 1),
                ("unused39", ctypes.c_uint, 1),
                ("unused40", ctypes.c_uint, 1),
                ("unused41", ctypes.c_uint, 1),
                ("unused42", ctypes.c_uint, 1),
                ("unused43", ctypes.c_uint, 1),
                ("unused44", ctypes.c_uint, 1),
                ("unused45", ctypes.c_uint, 1),
                ("waterCoolingSensorFitted", ctypes.c_uint, 1),
                ("home", ctypes.c_uint, 1),
                ("supportsVacuum", ctypes.c_uint, 1),
                ("motorX", ctypes.c_uint, 1),
                ("motorY", ctypes.c_uint, 1),
                ("motorZ", ctypes.c_uint, 1),
                ("supportsHumidity", ctypes.c_uint, 1),
                ("unused53", ctypes.c_uint, 1),
                ("unused54", ctypes.c_uint, 1),
                ("unused55", ctypes.c_uint, 1),
                ("unused56", ctypes.c_uint, 1),
                ("unused57", ctypes.c_uint, 1),
                ("unused58", ctypes.c_uint, 1),
                ("unused59", ctypes.c_uint, 1),
                ("unused60", ctypes.c_uint, 1),
                ("unused61", ctypes.c_uint, 1),
                ("unused62", ctypes.c_uint, 1),
                ("unused63", ctypes.c_uint, 1),]


class _StageConfig(ctypes.Union):
    """StageConfig union from C headers."""
    _fields_ = [("flags", _StageConfigFlags),
                ("value", _uint64_t)]


class _CMSStatusFlags(ctypes.Structure):
    """CMSStatus.flags struct from C headers"""
    _fields_ = [("on", ctypes.c_uint, 1),
                ("onNoLN2", ctypes.c_uint, 1),
                ("prime", ctypes.c_uint, 1),
                ("autoTopUp", ctypes.c_uint, 1),
                ("warmingUp", ctypes.c_uint, 1),
                ("WarmingUpFromCupboard", ctypes.c_uint, 1),
                ("unused6", ctypes.c_uint, 1),
                ("unused7", ctypes.c_uint, 1),
                ("light", ctypes.c_uint, 1),
                ("sampleDewarFillSignal", ctypes.c_uint, 1),
                ("mainDewarFillSignal", ctypes.c_uint, 1),
                ("unused11", ctypes.c_uint, 1),
                ("unused12", ctypes.c_uint, 1),
                ("unused13", ctypes.c_uint, 1),
                ("unused14", ctypes.c_uint, 1),
                ("unused15", ctypes.c_uint, 1),
                ("unused16", ctypes.c_uint, 1),
                ("unused17", ctypes.c_uint, 1),
                ("unused18", ctypes.c_uint, 1),
                ("unused19", ctypes.c_uint, 1),
                ("unused20", ctypes.c_uint, 1),
                ("unused21", ctypes.c_uint, 1),
                ("unused22", ctypes.c_uint, 1),
                ("unused23", ctypes.c_uint, 1),
                ("unused24", ctypes.c_uint, 1),
                ("unused25", ctypes.c_uint, 1),
                ("unused26", ctypes.c_uint, 1),
                ("unused27", ctypes.c_uint, 1),
                ("unused28", ctypes.c_uint, 1),
                ("unused29", ctypes.c_uint, 1),
                ("unused30", ctypes.c_uint, 1),
                ("unused31", ctypes.c_uint, 1) ]


class _CMSStatus(ctypes.Union):
    """CMSStatus union from C headers"""
    _fields_ = [("flags", _CMSStatusFlags),
                ("value", _uint32_t)]


class _CMSErrorFlags(ctypes.Structure):
    """CMSError.flags struct from C headers"""
    _fields_ = [("mainSensorOC", ctypes.c_uint, 1),
                ("mainSensorOver", ctypes.c_uint, 1),
                ("ln2SwitchSensorOC", ctypes.c_uint, 1),
                ("ln2SwitchSensorOver", ctypes.c_uint, 1),
                ("dewarSensorOC", ctypes.c_uint, 1),
                ("dewarSensorOver", ctypes.c_uint, 1),
                ("baseSensorOC", ctypes.c_uint, 1),
                ("baseSensorOver", ctypes.c_uint, 1),
                ("dewarEmpty", ctypes.c_uint, 1),
                ("motorPosnError", ctypes.c_uint, 1),
                ("unused10", ctypes.c_uint, 1),
                ("unused11", ctypes.c_uint, 1),
                ("unused12", ctypes.c_uint, 1),
                ("unused13", ctypes.c_uint, 1),
                ("unused14", ctypes.c_uint, 1),
                ("unused15", ctypes.c_uint, 1),
                ("unused16", ctypes.c_uint, 1),
                ("unused17", ctypes.c_uint, 1),
                ("unused18", ctypes.c_uint, 1),
                ("unused19", ctypes.c_uint, 1),
                ("unused20", ctypes.c_uint, 1),
                ("unused21", ctypes.c_uint, 1),
                ("unused22", ctypes.c_uint, 1),
                ("unused23", ctypes.c_uint, 1),
                ("unused24", ctypes.c_uint, 1),
                ("unused25", ctypes.c_uint, 1),
                ("unused26", ctypes.c_uint, 1),
                ("unused27", ctypes.c_uint, 1),
                ("unused28", ctypes.c_uint, 1),
                ("unused29", ctypes.c_uint, 1),
                ("unused30", ctypes.c_uint, 1),
                ("unused31", ctypes.c_uint, 1) ]


class _CMSError(ctypes.Union):
    """CMSError union from C headers"""
    _fields_ = [("flags", _CMSErrorFlags),
                ("value", _uint32_t)]


class _ConnectionStatusFlags(ctypes.Structure):
    """ConnectionStatus.flags structure from C headers"""
    _fields_ = [("connected", ctypes.c_uint, 1),
                ("errorNoDeviceFound", ctypes.c_uint, 1),
                ("errorMultipleDevicesFound", ctypes.c_uint, 1),
                ("errorTimeout", ctypes.c_uint, 1),
                ("errorHandleRegistrationFailed", ctypes.c_uint, 1),
                ("errorAllocationFailed", ctypes.c_uint, 1),
                ("errorSerialNumberRequired", ctypes.c_uint, 1),
                ("errorAlreadyOpen", ctypes.c_uint, 1),
                ("errorPropertiesIncorrect", ctypes.c_uint, 1),
                ("errorPortConfig", ctypes.c_uint, 1),
                ("errorCommsStreams", ctypes.c_uint, 1),
                ("errorUnhandled", ctypes.c_uint, 1),
                ("unused12", ctypes.c_uint, 1),
                ("unused13", ctypes.c_uint, 1),
                ("unused14", ctypes.c_uint, 1),
                ("unused15", ctypes.c_uint, 1),
                ("unused16", ctypes.c_uint, 1),
                ("unused17", ctypes.c_uint, 1),
                ("unused18", ctypes.c_uint, 1),
                ("unused19", ctypes.c_uint, 1),
                ("unused20", ctypes.c_uint, 1),
                ("unused21", ctypes.c_uint, 1),
                ("unused22", ctypes.c_uint, 1),
                ("unused23", ctypes.c_uint, 1),
                ("unused24", ctypes.c_uint, 1),
                ("unused25", ctypes.c_uint, 1),
                ("unused26", ctypes.c_uint, 1),
                ("unused27", ctypes.c_uint, 1),
                ("unused28", ctypes.c_uint, 1),
                ("unused29", ctypes.c_uint, 1),
                ("unused30", ctypes.c_uint, 1),
                ("unused31", ctypes.c_uint, 1) ]


class _ConnectionStatus(ctypes.Union):
    """ConnectionStatus union from C headers"""
    _fields_ = [("flags", _ConnectionStatusFlags),
                ("value", _uint32_t)]


class _ControllerStatusFlags(ctypes.Structure):
    """ControllerStatus.flags struct from C headers"""
    _fields_ = [("controllerError", ctypes.c_uint, 1),
                ("heater1RampSetPoint", ctypes.c_uint, 1),
                ("heater1Started", ctypes.c_uint, 1),
                ("heater2RampSetPoint", ctypes.c_uint, 1),
                ("heater2Started", ctypes.c_uint, 1),
                ("vacuumRampSetPoint", ctypes.c_uint, 1),
                ("vacuumCtrlStarted", ctypes.c_uint, 1),
                ("vacuumValveClosed", ctypes.c_uint, 1),
                ("vacuumValveOpen", ctypes.c_uint, 1),
                ("humidityRampSetPoint", ctypes.c_uint, 1),
                ("humidityCtrlStarted", ctypes.c_uint, 1),
                ("lnpCoolingPumpOn", ctypes.c_uint, 1),
                ("lnpCoolingPumpAuto", ctypes.c_uint, 1),
                ("unused13", ctypes.c_uint, 1),
                ("HumidityDesiccantConditioning", ctypes.c_uint, 1),
                ("unused15", ctypes.c_uint, 1),
                ("unused16", ctypes.c_uint, 1),
                ("unused17", ctypes.c_uint, 1),
                ("unused18", ctypes.c_uint, 1),
                ("unused19", ctypes.c_uint, 1),
                ("unused20", ctypes.c_uint, 1),
                ("unused21", ctypes.c_uint, 1),
                ("unused22", ctypes.c_uint, 1),
                ("unused23", ctypes.c_uint, 1),
                ("unused24", ctypes.c_uint, 1),
                ("unused25", ctypes.c_uint, 1),
                ("unused26", ctypes.c_uint, 1),
                ("unused27", ctypes.c_uint, 1),
                ("unused28", ctypes.c_uint, 1),
                ("unused29", ctypes.c_uint, 1),
                ("unused30", ctypes.c_uint, 1),
                ("unused31", ctypes.c_uint, 1),
                ("unused32", ctypes.c_uint, 1),
                ("unused33", ctypes.c_uint, 1),
                ("unused34", ctypes.c_uint, 1),
                ("unused35", ctypes.c_uint, 1),
                ("unused36", ctypes.c_uint, 1),
                ("unused37", ctypes.c_uint, 1),
                ("unused38", ctypes.c_uint, 1),
                ("unused39", ctypes.c_uint, 1),
                ("unused40", ctypes.c_uint, 1),
                ("motorTravelMinX", ctypes.c_uint, 1),
                ("motorTravelMaxX", ctypes.c_uint, 1),
                ("motorStoppedX", ctypes.c_uint, 1),
                ("motorTravelMinY", ctypes.c_uint, 1),
                ("motorTravelMaxY", ctypes.c_uint, 1),
                ("motorStoppedY", ctypes.c_uint, 1),
                ("motorTravelMinZ", ctypes.c_uint, 1),
                ("motorTravelMaxZ", ctypes.c_uint, 1),
                ("motorStoppedZ", ctypes.c_uint, 1),
                ("sampleCal", ctypes.c_uint, 1),
                ("motorDistanceCalTST", ctypes.c_uint, 1),
                ("cssRotMotorStopped", ctypes.c_uint, 1),
                ("cssGapMotorStopped", ctypes.c_uint, 1),
                ("cssLidOn", ctypes.c_uint, 1),
                ("cssRefLimit", ctypes.c_uint, 1),
                ("cssZeroLimit", ctypes.c_uint, 1),
                ("unused57", ctypes.c_uint, 1),
                ("unused58", ctypes.c_uint, 1),
                ("unused59", ctypes.c_uint, 1),
                ("unused60", ctypes.c_uint, 1),
                ("unused61", ctypes.c_uint, 1),
                ("unused62", ctypes.c_uint, 1),
                ("unused63", ctypes.c_uint, 1),]


class _ControllerStatus(ctypes.Union):
    """ControllerStatus union from C headers"""
    _fields_ = [("flags", _ControllerStatusFlags),
                ("value", _uint64_t)]


class _MDSStatusFlags(ctypes.Structure):
    """MDSStatus.flags struct from C headers"""
    _fields_ = [("xMinLimit", ctypes.c_uint, 1),
                ("xMaxLimit", ctypes.c_uint, 1),
                ("xMoveDone", ctypes.c_uint, 1),
                ("yMinLimit", ctypes.c_uint, 1),
                ("yMaxLimit", ctypes.c_uint, 1),
                ("yMoveDone", ctypes.c_uint, 1),
                ("unused6", ctypes.c_uint, 1),
                ("unused7", ctypes.c_uint, 1),
                ("unused8", ctypes.c_uint, 1),
                ("unused9", ctypes.c_uint, 1),
                ("unused10", ctypes.c_uint, 1),
                ("unused11", ctypes.c_uint, 1),
                ("unused12", ctypes.c_uint, 1),
                ("unused13", ctypes.c_uint, 1),
                ("unused14", ctypes.c_uint, 1),
                ("unused15", ctypes.c_uint, 1),
                ("unused16", ctypes.c_uint, 1),
                ("unused17", ctypes.c_uint, 1),
                ("unused18", ctypes.c_uint, 1),
                ("unused19", ctypes.c_uint, 1),
                ("unused20", ctypes.c_uint, 1),
                ("unused21", ctypes.c_uint, 1),
                ("unused22", ctypes.c_uint, 1),
                ("unused23", ctypes.c_uint, 1),
                ("unused24", ctypes.c_uint, 1),
                ("unused25", ctypes.c_uint, 1),
                ("unused26", ctypes.c_uint, 1),
                ("unused27", ctypes.c_uint, 1),
                ("unused28", ctypes.c_uint, 1),
                ("unused29", ctypes.c_uint, 1),
                ("unused30", ctypes.c_uint, 1),
                ("unused31", ctypes.c_uint, 1),]


class _MDSStatus(ctypes.Union):
    """MDSStatus union from C headers"""
    _fields_ = [("flags", _MDSStatusFlags),
                ("value", _uint32_t)]


class ControllerError(Enum):
    """ControllerError enum from C headers"""
    NoError                         =  0
    StageCableDisconnected          =  1
    StageCableError                 =  2
    StageTempSensorOpenOverrange    =  3
    LoadPowerOutputVoltageWrong     =  4
    T95RelayMissing                 =  5
    T95OptionBoardWongConfig        =  6
    OptionBoardCableDisconnect      =  7
    LoadPowerIncorrectForStage      =  8
    OptionBoardIncorrectCable       =  9
    OptionBoardSensorOenOverrange   = 10
    T95FanNotWorking                = 11
    LNP95Error                      = 12
    CommsError                      = 13
    CoolingWaterTooWarmNotFlowing   = 14
    CSS450MotorDriveOverTemp        = 15
    CSS450MotorWindingError1        = 16
    CSS450MotorWindingError2        = 17
    Reserved1                       = 18
    Reserved2                       = 19
    Reserved3                       = 20
    CMS196ChamberSensorOpen         = 21
    CMS196ChamberSensorOverrange    = 22
    CMS196LN2SwitchSensorOpen       = 23
    CMS196LN2SwitchSensorOverrange  = 24
    CMS196DewarSensorOpen           = 25
    CMS196DewarSensorOverrange      = 26
    CMS196DewarEmpty                = 27
    CMS196BaseSensorOpen            = 28
    CMS196BaseSensorOverrange       = 29
    CMS196MotorPosnError            = 30

##LinkamFunctionMsgCode enum from C headers.
class Msg(IntEnum):
    OpenComms                                        = 0x00000001
    #\param[in]      hDevice     A valid handle to a comms device/port returned by eLinkamFunctionMsgCode_OpenComms.
    CloseComms                                       = 0x00000002
    GetControllerConfig                              = 0x00000003
    GetControllerError                               = 0x00000004
    GetControllerName                                = 0x00000005
    GetControllerSerial                              = 0x00000006
    GetStatus                                        = 0x00000007
    GetStageConfig                                   = 0x00000008
    GetStageSerial                                   = 0x00000009
    GetStageName                                     = 0x0000000A
    GetMaxValue                                      = 0x0000000B
    GetMinValue                                      = 0x0000000C
    GetResolution                                    = 0x0000000D
    ApplySampleCals                                  = 0x0000000E
    SaveSampleCals                                   = 0x0000000F
    StartHeating                                     = 0x00000010
    StartVacuum                                      = 0x00000011
    StartHumidity                                    = 0x00000012
    StartHumidityDesiccantConditioning               = 0x00000013
    StartMotors                                      = 0x00000014
    GetValue                                         = 0x00000015
    SetValue                                         = 0x00000016
    TstCalibrateDistance                             = 0x00000017
    TstSetMode                                       = 0x00000018
    TstZeroForce                                     = 0x00000019
    TstZeroPosition                                  = 0x0000001A
    LnpSetMode                                       = 0x0000001B
    LnpSetSpeed                                      = 0x0000001C
    CssApplyValues                                   = 0x0000001D
    CssCheckValues                                   = 0x0000001E
    CssGotoReference                                 = 0x0000001F
    CssSensorCal                                     = 0x00000020
    CssStartJogGap                                   = 0x00000021
    CssStartJogRot                                   = 0x00000022
    EnableLogging                                    = 0x00000023
    DisableLogging                                   = 0x00000024
    GetControllerFirmwareVersion                     = 0x00000025
    GetControllerHardwareVersion                     = 0x00000026
    GetStageFirmwareVersion                          = 0x00000027
    GetStageHardwareVersion                          = 0x00000028
    GetDataRate                                      = 0x00000029
    SetDataRate                                      = 0x0000002A
    GetStageCableLimits                              = 0x0000002B
    SendDscGainValues                                = 0x0000002C
    SendDscPowerValue                                = 0x0000002D
    SendDscBaselinePowerValues                       = 0x0000002E
    SendDscTuaConstants                              = 0x0000002F
    SetDSCModulationData                             = 0x00000030
    GetOptionCardType                                = 0x00000031
    GetOptionCardSlot                                = 0x00000032
    GetOptionCardName                                = 0x00000033
    GetOptionCardSerial                              = 0x00000034
    GetOptionCardHardwareVersion                     = 0x00000035
    DoesOptionCardSupportSensors                     = 0x00000036
    #\see            eLinkamFunctionMsgCode_DoesOptionCardSupportSensors
    GetOptionCardSensorName                          = 0x00000037
    #\see            eLinkamFunctionMsgCode_DoesOptionCardSupportSensors
    GetOptionCardSensorSerial                        = 0x00000038
    #\see            eLinkamFunctionMsgCode_DoesOptionCardSupportSensors
    GetOptionCardSensorHardwareVersion               = 0x00000039
    GetStageGroup                                    = 0x0000003A
    HaveInstrumentBusDeviceType                      = 0x0000003B
    GetInstrumentBusDeviceName                       = 0x0000003C
    GetInstrumentBusDeviceSerial                     = 0x0000003D
    GetInstrumentBusDeviceFirmwareVersion            = 0x0000003E
    GetInstrumentBusDeviceHardwareVersion            = 0x0000003F
    GetHumidityControllerSensorName                  = 0x00000040
    GetHumidityControllerSensorSerial                = 0x00000041
    GetHumidityControllerSensorHardwareVersion       = 0x00000042
    IsControllerType                                 = 0x00000043
    GetControllerPSUDetails                          = 0x00000044
    SetControllerTriggerSignalEnable                 = 0x00000045
    SetControllerTriggerSignalDisable                = 0x00000046
    SetControllerMainsFrequency                      = 0x00000047
    InitialiseTriggerSignalPulse                     = 0x00000048
    SetTriggerSignalPulse                            = 0x00000049
    SetTriggerSignalPluseWidth                       = 0x0000004A
    GetProgramState                                  = 0x0000004B
    GetStageConfiguration                            = 0x0000004C
    GetControllerHeaterDetails                       = 0x0000004D
    CssSendGapVelocity                               = 0x0000004E
    CssSendGapOverride                               = 0x0000004F
    CssSendGap                                       = 0x00000050
    CssSendVelocity                                  = 0x00000051
    CssSendRate                                      = 0x00000052
    CssSendFrequency                                 = 0x00000053
    CssSendStrain                                    = 0x00000054
    CssSendDirection                                 = 0x00000055
    CssSendForceStop                                 = 0x00000056
    CssSendTorque                                    = 0x00000057
    TstSetCalibrationForce                           = 0x00000058
    ForceHeating                                     = 0x00000059
    ForceCooling                                     = 0x0000005A
    ForceHold                                        = 0x0000005B
    GetInstrumentBusDeviceIdent                      = 0x0000005C
    GetStageIdent                                    = 0x0000005D
    GetControllerIdent                               = 0x0000005F
    GetConnectionInformation                         = 0x00000060
    GetStageHeaterIdent                              = 0x00000061
    Max                                              = 0x0FFFFFFF


class ErrorCode(Enum):
    """ErrorCode enum from C headers"""
    NoError = 0xECF00000
    LibraryNotInitialised = 0xECF00001
    NoConnectionInfo = 0xECF00002
    DeviceRegistrationFailed = 0xECF00003
    DeviceCreationFailure = 0xECF00004
    SerialCommsInitialisationFailure = 0xECF00005
    SerialCommsHandshakeFailure = 0xECF00006
    SerialPortSocketCreationFailure = 0xECF00007
    SerialPortSocketConfigurationFailure = 0xECF00008
    SerialCommsRxError = 0xECF00009
    SerialCommsUnknownRxError = 0xECF0000A
    CommandBufferLimitReached = 0xECF0000B
    USBCommsInitialisationFailure = 0xECF0000C
    USBCommsHandshakeFailure = 0xECF0000D
    USBPortSocketCreationFailure = 0xECF0000E
    USBCommsRxError = 0xECF0000F
    USBCommsUnknownRxError = 0xECF00010
    USBCommsTxError = 0xECF00011
    USBCommsUnknownTxError = 0xECF00012
    SerialCommsTxError = 0xECF00013
    SerialCommsUnknownTxError = 0xECF00014
    Max = 0xECFFFFFF


class _StageValueType(Enum):
    """StageValueType enum from C headers"""
    Heater1Temp = 0
    HeaterRate = 1
    HeaterSetpoint = 2
    Heater1Power = 3
    Heater1LNPSpeed = 4
    Heater2Temp = 5
    Heater2Power = 8
    Heater2LNPSpeed = 9
    WaterCoolingTemp = 10
    HumidityTemp = 11
    Vacuum = 12
    VacuumSetpoint = 13
    Humidity = 14
    HumiditySetpoint = 15
    MotorPosX = 16
    MotorVelX = 17
    MotorSetpointX = 18
    MotorPosY = 19
    MotorVelY = 20
    MotorSetpointY = 21
    MotorPosZ = 22
    MotorVelZ = 23
    MotorSetpointZ = 24
    MotorDrivenStageStatus = 25
    VacuumBoardUnitOfMeasure = 26
    VacMotorValveStatus = 27
    VacMotorValvePos = 28
    VacMotorValveVel = 29
    VacMotorValveSetpoint = 30
    GradedMotorPos = 31
    GradedMotorVel = 32
    GradedMotorDistanceSetpoint = 33
    SampleRef1 = 34
    SampleAct1 = 35
    SampleRef2 = 36
    SampleAct2 = 37
    SampleRef3 = 38
    SampleAct3 = 39
    SampleRef4 = 40
    SampleAct4 = 41
    SampleRef5 = 42
    SampleAct5 = 43
    Heater3Temp = 44
    Dsc = 45
    TriggerSignalBlue = 46
    TriggerSignalGreen = 47
    TriggerSignalPink = 48
    TriggerSignalsEnabled = 49
    TemperatureResolution = 50
    Heater4Temp = 51
    CmsLight = 52
    CmsWarmingHeater = 53
    CmsSolenoidRefill = 54
    CmsSampleDewarFillSig = 55
    CmsStatus = 56
    CmsError = 57
    RampHoldTime = 58
    RampHoldRemaining = 59
    CmsMainDewarFillSig = 60
    CmsCondenserLEDLevel = 61
    TestMotion = 62
    MotorFeedbackYX = 63
    TstMotorPos = 64
    TstMotorVel = 65
    TstMotorDistanceSetpoint = 66
    TstForce = 67
    TstForceSetpoint = 68
    TstPidKp = 69
    TstPidKi = 70
    TstPidKd = 71
    TstForceGauge = 72
    CssMode = 73
    CssGapSetpoint = 74
    CssGapPos = 75
    CssStrainSetpoint = 76
    CssRateSetpoint = 77
    CssOcsFreq = 78
    CssDirn = 79
    CssJogRotVel = 80
    CssJogGapDis = 81
    CssDefaultGapRefVel = 82
    CssDefaultRotRefVel = 83
    CssStepDone = 84
    CssStepSuccess = 85
    CssStatus = 86
    CssForce = 87
    CssShareTime = 88
    CssRotMotorVelocitySetpoint = 89
    CssGapMotorVelocitySetpoint = 90
    CssOptionBoardSensorData = 91
    RS232OptionBoardSensorEnabled = 92
    VacuumOptionBoardSensor1Data = 93
    VacuumOptionBoardSensor1Enabled = 94
    VacuumOptionBoardSensor2Data = 95
    VacuumOptionBoardSensor2Enabled = 96
    VtoOptionBoardEnabled = 97
    CmsDewarTopTemperature = 98
    CmsAutoDewarFill = 99
    DscPower = 100
    DscGain1 = 101
    DscGain2 = 102
    DscGain3 = 103
    DscConstantTerm = 104
    DscPowerTerm1 = 105
    DscPowerTerm2 = 106
    DscPowerTerm3 = 107
    DscPowerTerm4 = 108
    DscPowerTerm5 = 109
    DscPowerTerm6 = 110
    DscBaselineConstTerm = 111
    DscBaselinePowerTerm1 = 112
    DscBaselinePowerTerm2 = 113
    DscBaselinePowerTerm3 = 114
    DscBaselinePowerTerm4 = 115
    DscTuaConst1 = 116
    DscTuaConst2 = 117
    DscOptionBoardSensorEnabled = 118
    TstJawToJawSize = 119
    TstTableDirection = 120
    TstSampleSize = 121
    TstStrainEngineeringUnits = 122
    TstStrainPercentage = 123
    TstShowAsForceDistance = 124
    TstCalForceValue = 125
    TstOptionBoardSensorEnabled = 126
    TstShowCalbData = 127
    TstStatus = 128
    TstJawPosition = 129
    TstStrain = 130
    TstStress = 131
    TstTableMode = 132
    StageHumidityUnitData = 133
    Pressure = 134
    MotorXOptionBoardSensorEnabled = 135
    MotorYOptionBoardSensorEnabled = 136
    MotorZOptionBoardSensorEnabled = 137
    MotorVacuumOptionBoardSensorEnabled = 138
    MotorFDVacuumOptionBoardSensorEnabled = 139
    MotorTstOptionBoardSensorEnabled = 140
    MotorGradientOptionBoardSensorEnabled = 141
    MotorXOptionBoardSensorData = 142
    MotorYOptionBoardSensorData = 143
    MotorZOptionBoardSensorData = 144
    MotorVacuumOptionBoardSensorData = 145
    MotorFDVacuumOptionBoardSensorData = 146
    MotorTstOptionBoardSensorData = 147
    MotorGradientOptionBoardSensorData = 148
    TtcOptionBoardEnabled = 149
    TtcOptionBoardSensor1Enabled = 150
    TtcOptionBoardSensor2Enabled = 151
    TtcOptionBoardSensor3Enabled = 152
    DtcOptionBoardSensor1Enabled = 153
    DtcOptionBoardSensor2Enabled = 154
    MotorXDefaultSpeed = 155
    MotorYDefaultSpeed = 156
    MotorZDefaultSpeed = 157
    MotorTstDefaultSpeed = 158
    MotorGsDefaultSpeed = 159
    MotorVacDefaultSpeed = 160
    MotorFDVacDefaultSpeed = 161
    HumidityDryingTimeSetpoint = 162
    HumiditySwapTimeSetpoint = 163
    HumidityPipeTempSetpoint = 164
    HumidityWaterTempSetpoint = 165
    HumidityDryingTimeLeft = 166
    HumiditySwapTimeLeft = 167
    HumidityWaterTemp = 168
    VtoVideoStandard = 169
    TriggerSignalPulseWidth = 170
    ConnectionType = 171
    VacuumSimulatorPlug = 172
    PressureSimulatorPlug = 173
    LNPSingle = 174
    LNPDual = 175
    LNP95 = 176
    LNP96 = 177
    UsingXenocsStageTestCables = 178
    UsingXenocsStageTestCableType1 = 179
    UsingXenocsStageTestCableType2 = 180
    UsingCalibrationPlug = 181
    UsingCalibrationCableB = 182
    UsingCalibrationCableC = 183
    UsingCalibrationCableA = 184
    VtoText = 185
    VtoTime = 186
    MotorZeroRefX = 187
    MotorZeroRefY = 188
    CmsXaxisGridCentre = 189
    CmsYaxisGridCentre = 190
    CmsLashWarning = 191
    CmsBaseHeaterLimit = 192
    CmsAlarmVolume = 193
    ManualHumiditySetpoint = 194
    FDVSColdTrapPumpSpeed = 195
    FDVSScanMotorPosition = 196
    ImagingStationBrightness = 197
    EnableJoyStick = 198
    DisableJoyStick = 199
    InvertJoyStickAxisX = 200
    InvertJoyStickAxisY = 201
    FDVSMotorVel = 202
    FDVSMotorDistanceSetpoint = 203
    CssDefaultGapChangeVel = 204
    MaxValue = 65535


class _Variant(ctypes.Union):
    """Variant union from C headers"""
    _fields_ = [("vChar", ctypes.c_char),
                ("vUint8", _uint8_t),
                ("vUint16", _uint16_t),
                ("vUint32", _uint32_t),
                ("vUint64", _uint64_t),
                ("vInt8", _int8_t),
                ("vInt16", _int16_t),
                ("vInt32", _int32_t),
                ("vInt64", _int64_t),
                ("vFloat32", ctypes.c_float),
                ("vFloat64", ctypes.c_double),
                ("vPtr", ctypes.c_void_p),
                ("vBoolean", ctypes.c_bool),
                #("vControllerConfig", _ControllerConfig),
                ("vControllerError", ctypes.c_uint), # _ControllerError enum
                ("vControllerStatus", _ControllerStatus),
                ("vConnectionStatus", _ConnectionStatus),
                #("vStageValueType", _StageValueType),
                #("vStageCableConfig", _StageCableConfig),
                ("vStageConfig", _StageConfig),
                ("vStageGroup", ctypes.c_uint), #_StageGroup enum
                #("vStageCableLimit", _StageCableLimit),
                #("vCSSStatus", _CSSStatus),
                #("vCSSCheckCodes", _CSSCheckCodes),
                #("vCSSMode", _CSSMode),
                #("vCSSState", _CSSState),
                ("vCMSStatus", _CMSStatus),
                ("vCMSError", _CMSError),
                #("vOptionBoardType", _OptionBoardType),
                #("vInstrumentBusDeviceType", _InstrumentBusDeviceType),
                #("vControllerType", _ControllerType),
                #("vTSTStatus", _TSTStatus),
                #("vTSTMode", _TSTMode),
                #("vTSTSampleSize", _TSTSampleSize),
                #("vMVStatus", _MVStatus),
                ("vMDSStatus", _MDSStatus),
                #("vCommsType", _CommsType),
                ]

    def __getattribute__(self, name):
        """Wrap enum variants with their python Enum for convenience"""
        val = super().__getattribute__(name)
        if name == "vStageGroup":
            return _StageGroup(val)
        elif name == "vControllerError":
            return ControllerError(val)
        else:
            return val


# Most GetValue calls return a Variant holding a float. A few pass back
# other types in the variant, so we map the StageValueType to the appropriate
# Variant member name.
_StageValueTypeToVariant = {
    _StageValueType.MotorDrivenStageStatus: "vMDSStatus", #MDSStatus
    _StageValueType.VacMotorValveStatus: "vUint32", # MVStatus - flags not yet supported
    _StageValueType.TriggerSignalsEnabled: "vBoolean",
    _StageValueType.CmsLight: "vBoolean",
    _StageValueType.CmsSampleDewarFillSig: "vBoolean",
    _StageValueType.CmsStatus: "vCMSStatus",
    _StageValueType.CmsError: "vCMSError",
    _StageValueType.CmsMainDewarFillSig: "vBoolean",
    _StageValueType.TestMotion: "vUint16",
    _StageValueType.MotorFeedbackYX: "vUint16",
    _StageValueType.CssMode: "vUint32", #CSSMode - enum not yet supported
    _StageValueType.CssDirn: "vBoolean",
    _StageValueType.CssStepDone: "vBoolean",
    _StageValueType.CssStepSuccess: "vBoolean",
    _StageValueType.CssStatus: "vUint32", #CSSStatus - flags not yet supported
    _StageValueType.RS232OptionBoardSensorEnabled: "vBoolean",
    _StageValueType.VacuumOptionBoardSensor1Enabled: "vBoolean",
    _StageValueType.VacuumOptionBoardSensor2Enabled: "vBoolean",
    _StageValueType.VtoOptionBoardEnabled: "vBoolean",
    _StageValueType.DscOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.TstTableDirection: "vBoolean",
    #_StageValueType.TstSampleSize: None, # TSTSampleSize - struct not yet supported
    _StageValueType.TstStrainEngineeringUnits: "vBoolean",
    _StageValueType.TstShowAsForceDistance: "vBoolean",
    _StageValueType.TstOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.TstStatus: "vUint32", #TSTStatus - flags not yet supported
    _StageValueType.TstTableMode: "vBoolean",
    _StageValueType.MotorXOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.MotorYOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.MotorVacuumOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.MotorFDVacuumOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.MotorFDVacuumOptionBoardSensorEnabled: "vBoolean",
    _StageValueType.MotorGradientOptionBoardSensorEnabled: "vBoolean",
}


class _LinkamBase(devices.FloatingDeviceMixin, devices.Device):
    """Base class for connecting to Linkam SDK devices.

    This class deals with SDK initialisation and setting callbacks to
    handle SDK events. It maintains a map of SDK handle to device instance
    so that SDK events result in updates to the correct instance.
    """
    # The ctypes library object. Value is None until SDK initialised.
    # This is encapsulated within a class so that this module will not break
    # tests on import in absence of the required library.
    _lib = None
    #_SDKInitialised = False
    # Map SDK handles to device instances
    _connectionMap = {}
    # We need to keep references to CFUNCTYPE callbacks.
    _callbacks = {}

    @staticmethod
    def get_sdk_version():
        """Fetch the SDK version."""
        b = ctypes.create_string_buffer(_max_version_length)
        __class__._lib.linkamGetVersion(b, _max_version_length)
        return b.value

    @staticmethod
    def init_sdk():
        """Initialise the SDK and set up event callbacks"""
        try:
            __class__._lib = ctypes.WinDLL("LinkamSDK.dll")
        except:
            # Not tested
            __class__._lib = ctypes.CDLL("libLinkamSDK.so")
        _lib = __class__._lib
        """Initialise the SDK, and create and set the callbacks."""
        # Omit conditional pending a fix for ctypes issues when optimisations in use.
        #if __debug__:
        #    sdk_log = b''
        #else:
        import os
        lpaths = ['', os.path.dirname(__file__), os.path.dirname(devices.__file__)]
        sdk_log = os.devnull
        while True:
            try:
                p = lpaths.pop()
            except IndexError:
                raise Exception("Could not init SDK: no linkam license file (Linkam.lsk) found.")
            lskpath = os.path.join(p, 'Linkam.lsk').encode()
            if (_lib.linkamInitialiseSDK(sdk_log, lskpath, True)):
                break
        # NewValue event callback
        cfunc = ctypes.CFUNCTYPE(_uint32_t, _CommsHandle, _ControllerStatus)(__class__._on_new_value)
        _lib.linkamSetCallbackNewValue(cfunc)
        __class__._callbacks[__class__._on_new_value] = cfunc
        # Connection event callback
        cfunc = ctypes.CFUNCTYPE(None, _CommsHandle)(__class__._on_connect)
        _lib.linkamSetCallbackControllerConnected(cfunc)
        __class__._callbacks[__class__._on_connect] = cfunc
        # Disconnection event callback
        cfunc = ctypes.CFUNCTYPE(None, _CommsHandle)(__class__._on_disconnect)
        _lib.linkamSetCallbackControllerDisconnected(cfunc)
        __class__._callbacks[__class__._on_disconnect] = cfunc
        # Error event callback
        cfunc = ctypes.CFUNCTYPE(None, _CommsHandle, _uint32_t)(__class__._on_error)
        _lib.linkamSetCallbackError(cfunc)
        __class__._callbacks[__class__._on_error] = cfunc

    @classmethod
    def _on_new_value(cls, h: _CommsHandle, status: _ControllerStatus):
        """NewValue callback"""
        stage = cls._connectionMap.get(h, None)
        if not stage:
            return 0
        stage._update_status(status)
        return 1

    @classmethod
    def _on_error(cls, h: _CommsHandle, errcode: _uint32_t):
        """Error event callback"""
        err = ErrorCode(errcode)
        stage = cls._connectionMap.get(h, None)
        if not stage:
            return
        if err in (ErrorCode.USBCommsTxError, ErrorCode.USBCommsRxError,
                   ErrorCode.SerialCommsTxError, ErrorCode.SerialCommsRxError):
            # Try to re-establish comms.
            stage._reopen_comms()
        return

    @classmethod
    def _on_connect(cls, h: _CommsHandle):
        """Connection event callback

        Connection event only seems to be generated by processing an
        OpenComms message - USB connection is not autodetected."""
        stage = cls._connectionMap.get(h, None)
        if not stage:
            return
        stage._post_connect()
        return

    @classmethod
    def _on_disconnect(cls, h: _CommsHandle):
        """Disconnection event callback

        Discconneciton event only seems to be generated by processing a
        CloseComms message."""
        stage = cls._connectionMap.get(h, None)
        if not stage:
            return 0
        stage._connectionstatus.flags.connected = 0
        return

    def __init__(self, **kwargs):
        """Initalise the device and, if necessary, the SDK."""
        # Connection handle, info struct and status struct.
        super().__init__(**kwargs)
        self._commsinfo = _CommsInfo()
        self._h = _CommsHandle()
        self._connectionstatus = _ConnectionStatus()
        self._stageconfig = _StageConfig()
        # Stage status struct, updated by the NewValue callback.
        self._status = _ControllerStatus()
        if __class__._lib is None:
            self.init_sdk()
        self._reconnect_thread = None

    def initialize(self):
        pass

    def _on_shutdown(self):
        pass

    def __del__(self):
        """Close comms on object deletion"""
        self._process_msg(Msg.CloseComms)

    def _post_connect(self):
        """Mixins should implement this method to do post-connection config."""
        pass

    def _process_msg(self, msg, param1=None, param2=None, param3=None, result=None):
        """As the SDK to process a message."""
        if result is None:
            result = _Variant()
        if not self._lib.linkamProcessMessage(ctypes.c_uint(msg),
                                        self._h,
                                        byref(result),
                                        param1, param2, param3):
            raise Exception("ProcessMessage error.")
        return result

    def check_connection(self):
        """Raise an exception if the connection is down."""
        if not self._connectionstatus.flags.connected:
            raise Exception("Stage not connected.")

    def get_data_rate(self):
        """Return the status update period in seconds."""
        return self._process_msg(Msg.GetDataRate).vUint32 / 1000

    def get_error(self):
        """Fetch the controller error."""
        return self._process_msg(Msg.GetControllerError).vControllerError

    def get_id(self):
        """Fetch the device's serial number"""
        buf = ctypes.create_string_buffer(18)
        self._process_msg(Msg.GetControllerSerial, byref(buf), 18)
        # Decode from bytes to string and strip trailing spaces.
        return buf.value.decode().rstrip()

    def get_value(self, svt, result=None):
        """Fetch a value from the device.

            svt: a StageValueType
            result: an existing Variant to use to return a result, or None.
        """
        # Don't self.check_connection on read as it can cause get_status to throw exception.
        # Ensure svt is an Enum member (not a raw value), as it is used as a key.
        if isinstance(svt, str):
            # Allow access using parameter names - useful for Pyro.
            svt = getattr(_StageValueType, svt)
        else:
            svt = _StageValueType(svt)
        # Determine the appropriate Variant member for the value type.
        vtype = _StageValueTypeToVariant.get(svt, "vFloat32")
        variant = self._process_msg(Msg.GetValue, svt.value, result=result)
        if result is not None:
            return result
        else:
            return getattr(variant, vtype)

    def get_value_limits(self, svt):
        """Returns the bounds for a StageValueType"""
        if isinstance(svt, str):
            # Allow access using parameter names - useful for Pyro.
            svt = getattr(_StageValueType, svt)
        else:
            svt = _StageValueType(svt)
        vtype = _StageValueTypeToVariant.get(svt, "vFloat32")
        vmin = self._process_msg(Msg.GetMinValue, svt.value)
        vmax = self._process_msg(Msg.GetMaxValue, svt.value)
        return tuple( getattr(v, vtype) for v in (vmin, vmax) )

    def set_value(self, svt, val):
        """Set value identified by svt to val"""
        self.check_connection()
        if isinstance(svt, str):
            # Allow access using parameter names - useful for Pyro.
            svt = getattr(_StageValueType, svt)
        else:
            svt = _StageValueType(svt)
        vtype = _StageValueTypeToVariant.get(svt, "vFloat32")
        v = _Variant(**{vtype: val})
        return self._process_msg(Msg.SetValue,
                                    _StageValueType(svt).value,
                                    _Variant(**{vtype: val})).vBoolean

    def is_moving(self, axis=None):
        """Returns True if the stage is moving, False if stopped

        This method isn't on the LinkamMDSMixin because the StageStatus motor
        stopped flags appear to be more reliable than the MDSStatus MoveDone
        flags."""
        if axis is not None and axis.upper() in 'XYZ':
            has_motor = getattr(self._stageconfig.flags, 'motor' + axis.upper())
            stopped = getattr(self._status.flags, 'motorStopped' + axis.upper())
            return has_motor and not stopped
        else:
            return any (self.is_moving(ax) for ax in 'XYZ')

    def close_comms(self):
        """Close the comms link"""
        self._process_msg(Msg.CloseComms, result=self._connectionstatus)

    def open_comms(self):
        """Open the comms link and store the comms handle."""
        self._process_msg(Msg.OpenComms,
                             byref(self._commsinfo),
                             byref(self._h),
                             result=self._connectionstatus)
        if self._h.value != 0:
            __class__._connectionMap[self._h.value] = self
            self._process_msg(Msg.GetStageConfig, result=self._stageconfig)
        else:
            raise Exception("Could not connect to stage.")

    def _reopen_comms(self):
        """Reopen communications.

        This is called by the error event callback, which runs in some thread in
        the library. If comms_close is called in that thread, the connection
        status isn't correctly updated, so reconnection must happen in another
        thread."""
        if self._reconnect_thread is not None and self._reconnect_thread.is_alive():
            # Already trying to reconnect
            return
        import threading
        self._reconnect_thread = threading.Thread(target=self._reopen_loop, daemon=True)
        self._reconnect_thread.start()

    def _reopen_loop(self):
        """Attempt to reopen comms."""
        self.close_comms()
        # Need a small delay to avoid false positive connected status.
        time.sleep(0.1)
        while not self._connectionstatus.flags.connected:
            time.sleep(0.5)
            try:
                self.open_comms()
            except:
                pass

    def _update_status(self, status):
        """Update status structures."""
        self._status = status

    def init_usb(self, uid):
        """Populate commsinfo struct with default USBCommsInfo"""
        # The uid is used to set serialNumber on the info object. The docs
        # suggest that an OpenComms message should open a connection to the
        # device with that serial number; with only one stage attached, it
        # appears that OpenComms ignores the value of serialNumber.
        if uid is None:
            uid = b''
        elif not isinstance(uid, bytes):
            uid = uid.encode()
        self._lib.linkamInitialiseUSBCommsInfo(byref(self._commsinfo), ctypes.c_char_p(uid))


    def init_serial(self, port):
        """Populate commsinfo struct with default SerialCommsInfo for given port"""
        self._lib.linkamInitialiseSerialCommsInfo(byref(self._commsinfo), port)


    def get_status(self, *args):
        """Called by a client to fetch status in a dict.

        Derived classes and mixins should implement this to add their own status.

        status = super().get_status(*args, status_structure, ...) in derived classes.
        # then add any other values with
        status[key] = ...
        """
        structs = args + (self._status, self._connectionstatus)
        status = {}
        for s in structs:
            names = filter(lambda n: not n.startswith('unused'),
                           (f[0] for f in s.flags._fields_) )
            status.update(dict(map( lambda n: (n, bool(getattr(s.flags, n))), names)))
        return status


class _LinkamMDSMixin():
    """A mixin for motor-driven stages"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mdsstatus = _MDSStatus()

    def _post_connect(self):
        """Set up motors: set velocities and add velocity settings."""
        for name, flag, svt in (("X_velocity", self._stageconfig.flags.motorX, _StageValueType.MotorVelX),
                                ("Y_velocity", self._stageconfig.flags.motorY, _StageValueType.MotorVelY),
                                ("Z_velocity", self._stageconfig.flags.motorZ, _StageValueType.MotorVelZ)):
            if flag:
                # Motors don't move unless their velocities have been written to,
                # despite velocities having a non-zero power-on default. There's no
                # way to tell if they've been written to, so write them once here.
                self.set_value(svt, self.get_value(svt))
                # Also add a Setting that clients can use to modify the velocity.
                self.add_setting(name, float,
                                 lambda svt=svt: self.get_value(svt),
                                 lambda val, svt=svt, s=self: self.set_value(svt, val),
                                 lambda svt=svt: self.get_value_limits(svt))

        super()._post_connect()

    def _update_status(self, status):
        """Call parent class update_status, then update MDS status structure."""
        super()._update_status(status)
        self.get_value(_StageValueType.MotorDrivenStageStatus, result=self._mdsstatus)

    def move_to(self, x=None, y=None, z=None):
        """Move to co-ordinates given by x and y"""
        # The default position set points are zero. If the motors are started without
        # writing to a set point, that motor will move to zero, so only start motors
        # if a target has been provided.
        if x is not None:
            self.set_value(_StageValueType.MotorSetpointX, x)
            self._process_msg(Msg.StartMotors, True, 0)
        if y is not None:
            self.set_value(_StageValueType.MotorSetpointY, y)
            self._process_msg(Msg.StartMotors, True, 1)
        if z is not None:
            self.set_value(_StageValueType.MotorSetpointZ, z)
            self._process_msg(Msg.StartMotors, True, 2)
        # Allow time for status structures to indicate stage is moving
        time.sleep(5 * self.get_data_rate())

    def get_status(self, *args):
        """Includes MDSStatus in the get_status call."""
        return super().get_status(*args, self._mdsstatus)

    def get_position(self):
        """Return the stage's position."""
        pos = {}
        for axis in 'ZYX':
            if getattr(self._stageconfig.flags, 'motor' + axis):
                pos[axis] = self.get_value(getattr(_StageValueType, 'MotorPos' + axis))
            else:
                pos[axis] = float('nan')
        return pos


class LinkamCMS(_LinkamMDSMixin, _LinkamBase):
    """Linkam correlative-microscopy stage."""
    _refill_map = {'sample': 'sampleDewarFillSignal',
                   'external': 'mainDewarFillSignal'}
    _heater_map = {'t_bridge': _StageValueType.Heater1Temp,
                   't_chamber': _StageValueType.Heater2Temp,
                   't_dewar': _StageValueType.Heater3Temp,
                   't_base': _StageValueType.Heater4Temp}

    class RefillTracker():
        # Is refill in progress?
        refilling = False
        # Time between last refills.
        dt = datetime.timedelta(0)
        # Last refill time.
        t = None

        def start_refill(self):
            """Start a refill: update status flag and last cycle time."""
            self.refilling = True
            if self.t is not None:
                self.dt = datetime.datetime.now() - self.t

        def end_refill(self):
            """End a refill: update status flag and last refill time."""
            self.refilling = False
            self.t = datetime.datetime.now()

        def as_dict(self):
            """Represent this object as a dict for status queries."""
            return dict(refilling=self.refilling, last=self.t, between_last=self.dt)

        def __repr__(self):
            """Display tracker properties in representation."""
            return "refilling: %s, t: %s, dt: %s" % (self.refilling, self.t, self.dt)


    def __init__(self, uid='', **kwargs):
        super().__init__(**kwargs)
        self.uid = uid
        self.init_usb(self.uid)
        self._cmsstatus = _CMSStatus()
        self._cmserror = _CMSError()
        # Refill tracking
        self._refills = dict({k:self.RefillTracker() for k in self._refill_map})
        # Condensor LED level when on
        self._condensor_level = 100
        self.add_setting("condensor", float,
                         self.get_condensor_level,
                         self.set_condensor_level,
                         (0, 100))
        # Connect to the stage.
        if self.uid:
            # Deviceserver needs uid to associate device to address, so call
            # open_comms directly to throw an exception on connection error.
            self.open_comms()
        else:
            # Device id not required - just keep trying to connect until success.
            self._reopen_comms()

    def _update_status(self, status):
        """Update status structures."""
        super()._update_status(status)
        self.get_value(_StageValueType.CmsStatus, result=self._cmsstatus)
        self.get_value(_StageValueType.CmsError, result=self._cmserror)
        # Update the refill timers.
        for (key, flagname) in self._refill_map.items():
            tracker = self._refills[key]
            is_refilling = getattr(self._cmsstatus.flags, flagname)
            if is_refilling and not tracker.refilling:
                tracker.start_refill()
            elif self._refills[key].refilling and not is_refilling:
                tracker.end_refill()

    def temperatures(self):
        """Return a dict of temperature sensor readings."""
        return dict( (key, self.get_value(svt)) for key, svt in self._heater_map.items())

    def set_light(self, state):
        """Set the state of the chamber light."""
        self.set_value(_StageValueType.CmsLight, state)

    def get_light(self):
        """Report the state of the chamber light."""
        return self.get_value(_StageValueType.CmsLight)

    def set_condensor(self, state):
        """Turn the condensor LED on or off."""
        if state:
            level = self._condensor_level
        else:
            level = 0
        self.set_value(_StageValueType.CmsCondenserLEDLevel, level)

    def set_condensor_level(self, level):
        """Set the condensor LED level"""
        self._condensor_level = level
        if self.get_value(_StageValueType.CmsCondenserLEDLevel) > 0:
            # Condnesor LED is on, so write out new level immediately.
            self.set_condensor(True)

    def get_condensor_level(self):
        """Return the condensor level"""
        return self._condensor_level

    def get_motors(self):
        """Return the position, set point and stopped status of available motors."""
        res = {}
        for axis in 'XYZ':
            if getattr(self._stageconfig.flags, 'motor' + axis):
                res[axis] = (self.get_value(getattr(_StageValueType, 'MotorPos' + axis)),
                             self.get_value(getattr(_StageValueType, 'MotorSetpoint' + axis)),
                             getattr(self._status.flags, 'motorStopped' + axis))
            else:
                res[axis] = None
        return res

    def refill_dewar(self, state=True):
        """Start a refill of the internal dewar from an external reservoir"""
        return self.set_value(_StageValueType.CmsMainDewarFillSig, True)

    def refill_chamber(self, state=True):
        """Start a refill of the sample chamber from the internal dewar"""
        return self.set_value(_StageValueType.CmsSampleDewarFillSig, True)

    def refill_stats(self):
        """Return information about refill times and cycle lengths."""
        return dict([(k, v.as_dict()) for k, v in self._refills.items()])

    def get_status(self, *args):
        """Return a dict containing aggregated stage status."""
        status = super().get_status(*args, self._cmsstatus)
        status.update(self.temperatures())
        status.update(refills=self.refill_stats())
        return status
