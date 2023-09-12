#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2023 Ian Dobbie <ian.dobbie@jhu.edu>
##
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

"""Raspberry Pi Value Logger module.
"""

import contextlib
import logging
import queue
import re
import threading
import time
import typing


try:
    from Adafruit_MCP9808 import MCP9808

    has_MCP9808 = True
except ModuleNotFoundError:
    has_MCP9808 = False

try:
    from TSYS01 import TSYS01

    has_TSYS01 = True
except ModuleNotFoundError:
    has_TSYS01 = False


import microscope.abc


# Support for async digital IO control on the Raspberryy Pi.
# Currently supports digital input and output via GPIO lines


# Use BCM GPIO references (naming convention for GPIO pins from Broadcom)
# instead of physical pin numbers on the Raspberry Pi board

_logger = logging.getLogger(__name__)


class RPiValueLogger(microscope.abc.ValueLogger):
    """ValueLogger device for a Raspberry Pi with support for
    MCP9808 and TSYS01 I2C thermometer chips."""

    def __init__(self, sensors=[], **kwargs):
        super().__init__(**kwargs)
        # setup Q for fetching data.
        self.inputQ = queue.Queue()
        self._sensors = []
        for sensor in sensors:
            sensor_type, i2c_address = sensor
            print(
                "adding sensor: " + sensor_type + " Adress: %d " % i2c_address
            )
            if sensor_type == "MCP9808":
                if not has_MCP9808:
                    raise microscope.LibraryLoadError(
                        "Adafruit_MCP9808 Python package not found"
                    )
                self._sensors.append(MCP9808.MCP9808(address=i2c_address))
                # starts the last one added
                self._sensors[-1].begin()
                print(self._sensors[-1].readTempC())
            elif sensor_type == "TSYS01":
                if not has_TSYS01:
                    raise microscope.LibraryLoadError(
                        "TSYS01 Python package not found"
                    )
                self._sensors.append(TSYS01.TSYS01(address=i2c_address))
                print(self._sensors[-1].readTempC())
            self.initialize()

    def initialize(self):
        self.updatePeriod = 1.0
        self.readsPerUpdate = 10
        # Open and start all temp sensors
        # A thread to record periodic temperature readings
        # This reads temperatures and logs them
        if self._sensors:
            # only strart thread if we have a sensor
            self.statusThread = threading.Thread(target=self.updateTemps)
            self.stopEvent = threading.Event()
            self.statusThread.Daemon = True
            self.statusThread.start()

    def debug_ret_Q(self):
        if not self.inputQ.empty():
            return self.inputQ.get()

    # functions required for a data device.
    def _fetch_data(self):
        # need to return data fetched from interupt driven state chnages.
        if self.inputQ.empty():
            return None
        temps = self.inputQ.get()
        if len(temps) == 1:
            outtemps = temps[0]
        else:
            outtemps = temps
        # print(self.inputQ.get())
        _logger.debug("Temp readings are %s" % str(outtemps))
        return outtemps

    def abort(self):
        pass

    def _do_enable(self):
        return True

    def _do_shutdown(self) -> None:
        # need to kill threads.
        self.stopEvent.set()

        # return the list of current temperatures.

    def get_temperature(self):
        return self.temperature

    # function to change updatePeriod
    def tempUpdatePeriod(self, period):
        self.updatePeriod = period

    # function to change readsPerUpdate
    def tempReadsPerUpdate(self, reads):
        self.readsPerUpdate = reads

    # needs to be re-written to push data into a queue which _fetch_data can
    # then send out to the server.

    # function to read temperature at set update frequency.
    # runs in a separate thread.
    def updateTemps(self):
        """Runs in a separate thread publish status updates."""
        self.temperature = [None] * len(self._sensors)
        tempave = [None] * len(self._sensors)

        #        self.create_rotating_log()

        if len(self._sensors) == 0:
            return ()

        while True:
            if self.stopEvent.is_set():
                break
            # zero the new averages.
            for i in range(len(self._sensors)):
                tempave[i] = 0.0
            # take readsPerUpdate measurements and average to reduce digitisation
            # errors and give better accuracy.
            for i in range(int(self.readsPerUpdate)):
                for i in range(len(self._sensors)):
                    try:
                        tempave[i] += self._sensors[i].readTempC()
                    except:
                        localTemperature = None
                time.sleep(self.updatePeriod / self.readsPerUpdate)
            for i in range(len(self._sensors)):
                self.temperature[i] = tempave[i] / self.readsPerUpdate
                _logger.debug(
                    "Temperature-%s =  %s" % (i, self.temperature[i])
                )
            self.inputQ.put(self.temperature)

    def getValues(self):
        """Reads all sensor values for running the value logger in remote
        pull mode"""

        if len(self._sensors) == 0:
            return ()

        self.temperature = [None] * len(self._sensors)

        for i in range(len(self._sensors)):
            try:
                self.temprature[i] = self._sensors[i].readTempC()
            except:
                raise Exception("Unable to read temparture value")
        return self.temprature
