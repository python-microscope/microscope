#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
##
## This file is part of Microscope.
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

import logging
import time
from enum import IntEnum

import microscope.abc

# These classes were originally in testsuite but have been moved to
# their own subpackage, these imports are for backwards compatibility.
from microscope.simulators import (
    SimulatedCamera,
    SimulatedController as TestController,
    SimulatedDeformableMirror as TestDeformableMirror,
    SimulatedFilterWheel as TestFilterWheel,
    SimulatedLightSource,
    SimulatedStage as TestStage,
)


_logger = logging.getLogger(__name__)


class CamEnum(IntEnum):
    A = 1
    B = 2
    C = 3
    D = 4


class TestCamera(SimulatedCamera):
    # This adds a series of weird settings to the base simulated
    # camera which are only useful to test settings in cockpit.
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Enum-setting tests
        self._intEnum = CamEnum.A
        self.add_setting(
            "intEnum",
            "enum",
            lambda: self._intEnum,
            lambda val: setattr(self, "_intEnum", val),
            CamEnum,
        )
        self._dictEnum = 0
        self.add_setting(
            "dictEnum",
            "enum",
            lambda: self._dictEnum,
            lambda val: setattr(self, "_dictEnum", val),
            {0: "A", 8: "B", 13: "C", 22: "D"},
        )
        self._listEnum = 0
        self.add_setting(
            "listEnum",
            "enum",
            lambda: self._listEnum,
            lambda val: setattr(self, "_listEnum", val),
            ["A", "B", "C", "D"],
        )
        self._tupleEnum = 0
        self.add_setting(
            "tupleEnum",
            "enum",
            lambda: self._tupleEnum,
            lambda val: setattr(self, "_tupleEnum", val),
            ("A", "B", "C", "D"),
        )


class TestLaser(SimulatedLightSource):
    # Deprecated, kept for backwards compatibility.
    pass


class DummySLM(microscope.abc.Device):
    # This only exists to test cockpit.  There is no corresponding
    # device type in microscope yet.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sim_diffraction_angle = 0.0
        self.sequence_params = []
        self.sequence_index = 0

    def _do_shutdown(self) -> None:
        pass

    def set_sim_diffraction_angle(self, theta):
        _logger.info("set_sim_diffraction_angle %f", theta)
        self.sim_diffraction_angle = theta

    def get_sim_diffraction_angle(self):
        return self.sim_diffraction_angle

    def run(self):
        self.enabled = True
        _logger.info("run")
        return

    def stop(self):
        self.enabled = False
        _logger.info("stop")
        return

    def get_sim_sequence(self):
        return self.sequence_params

    def set_sim_sequence(self, seq):
        _logger.info("set_sim_sequence")
        self.sequence_params = seq
        return

    def get_sequence_index(self):
        return self.sequence_index


class DummyDSP(microscope.abc.Device):
    # This only exists to test cockpit.  There is no corresponding
    # device type in microscope yet.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._digi = 0
        self._ana = [0, 0, 0, 0]
        self._client = None
        self._actions = []

    def _do_shutdown(self) -> None:
        pass

    def Abort(self):
        _logger.info("Abort")

    def WriteDigital(self, value):
        _logger.info("WriteDigital: %s", bin(value))
        self._digi = value

    def MoveAbsolute(self, aline, pos):
        _logger.info("MoveAbsoluteADU: line %d, value %d", aline, pos)
        self._ana[aline] = pos

    def arcl(self, mask, pairs):
        _logger.info("arcl: %s, %s", mask, pairs)

    def profileSet(self, pstr, digitals, *analogs):
        _logger.info("profileSet ...")
        _logger.info("... ", pstr)
        _logger.info("... ", digitals)
        _logger.info("... ", analogs)

    def DownloadProfile(self):
        _logger.info("DownloadProfile")

    def InitProfile(self, numReps):
        _logger.info("InitProfile")

    def trigCollect(self, *args, **kwargs):
        _logger.info("trigCollect: ... ")
        _logger.info(args)
        _logger.info(kwargs)

    def ReadPosition(self, aline):
        _logger.info(
            "ReadPosition   : line %d, value %d", aline, self._ana[aline]
        )
        return self._ana[aline]

    def ReadDigital(self):
        _logger.info("ReadDigital: %s", bin(self._digi))
        return self._digi

    def PrepareActions(self, actions, numReps=1):
        _logger.info("PrepareActions")
        self._actions = actions
        self._repeats = numReps

    def RunActions(self):
        _logger.info("RunActions ...")
        for i in range(self._repeats):
            for a in self._actions:
                _logger.info(a)
                time.sleep(a[0] / 1000.0)
        if self._client:
            self._client.receiveData("DSP done")
        _logger.info("... RunActions done.")

    def receiveClient(self, *args, **kwargs):
        # XXX: maybe this should be on its own mixin instead of on DataDevice
        return microscope.abc.DataDevice.receiveClient(self, *args, **kwargs)

    def set_client(self, *args, **kwargs):
        # XXX: maybe this should be on its own mixin instead of on DataDevice
        return microscope.abc.DataDevice.set_client(self, *args, **kwargs)


class TestFloatingDevice(
    microscope.abc.FloatingDeviceMixin, microscope.abc.Device
):
    """Simple device with a UID after having been initialized.

    Floating devices are devices where we can't specify which one to
    get, we can only construct it and after initialisation check its
    UID.  In this class for test units we can check which UID to get.

    """

    def __init__(self, uid: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._initialized = False
        self._uid = uid
        self.initialize()

    def initialize(self) -> None:
        super().initialize()
        self._initialized = True

    def get_index(self) -> int:
        """Expose private _index for testing purposes."""
        return self._index

    def get_id(self) -> str:
        if self._initialized:
            return self._uid
        else:
            raise microscope.IncompatibleStateError(
                "uid is not available until after initialisation"
            )

    def _do_shutdown(self) -> None:
        pass
