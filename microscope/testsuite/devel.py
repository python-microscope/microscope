#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016-2017 Mick Phillips <mick.phillips@gmail.com>
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
import time
import Pyro4

from microscope import devices
#
# class __MockMethod__(object):
#     def __init__(self, parent, attr):
#         self.__parent__ = parent
#         self.__mname__ = attr
#
#     def __call__(self, *args, **kwargs):
#         self.__parent__._logger.info(self.__mname__, args, kwargs)
#
#
# @Pyro4.expose
# @Pyro4.behavior('single')
# class LoggingMock(devices.Device):
#     def __init__(self):
#         super(self.__class__, self).__init__(self)
#
#     def __getattr__(self, attr):
#         try:
#             return super(self.__class__, self).__getattr__(attr)
#         except AttributeError:
#             return __MockMethod__(self, attr)
#
#     def initialize(self, *args, **kwargs):
#         pass
#
#     def _on_shutdown(self):
#         pass

@Pyro4.expose
@Pyro4.behavior('single')
class DummyDSP(devices.Device):
    def __init__(self, *args, **kwargs):
        devices.Device.__init__(self, args, kwargs)
        self._digi = 0
        self._ana = [0,0,0,0]
        self._client = None

    def initialize(self, *args, **kwargs):
        pass

    def _on_shutdown(self):
        pass

    def Abort(self):
        self._logger.info('Abort')

# self.connection.receiveClient(uri)
    def WriteDigital(self, value):
        self._logger.info('WriteDigital: %s' % "{0:b}".format(value))
        self._digi = value

    def MoveAbsoluteADU(self, aline, pos):
        self._logger.info('MoveAbsoluteADU: line %d, value %d' % (line, pos))
        self._ana[aline] = pos

    def arcl(self, mask, pairs):
        self._logger.info('arcl: %s, %s' % (mask, pairs))

    def profileSet(self, pstr, digitals, *analogs):
        self._logger.info('profileSet ...')
        self._logger.info('... ', pstr)
        self._logger.info('... ', digitals)
        self._logger.info('... ', analogs)

    def DownloadProfile(self):
        self._logger.info('DownloadProfile')

    def InitProfile(self, numReps):
        self._logger.info('InitProfile')

    def trigCollect(self, *args, **kwargs):
        self._logger.info('trigCollect: ... ')
        self._logger.info(args)
        self._logger.info(kwargs)

    def ReadPosition(self, aline):
        self._logger.info('ReadPosition: %d' % aline)
        return self._ana[aline]

    def ReadDigital(self):
        self._logger.info('ReadDigital')
        return self._digi

DummyDSP.receiveClient = devices.DataDevice.receiveClient.im_func
DummyDSP.set_client = devices.DataDevice.set_client.im_func