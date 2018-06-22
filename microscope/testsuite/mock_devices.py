#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2018 David Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Mock devices to be used in test cases.

These classes mock the different hardware as much as needed for our
testing needs.  Their behaviour is based first on the specifications
we have, and second on what we actually experience.  Our experience is
that most hardware does not actually follow the specs.

To fake a specific device type for interactive usage, use the dummy
device classes instead.  There's a concrete class for each device
interface.
"""

import functools
import io

import serial.serialutil


class SerialMock(serial.serialutil.SerialBase):
    """Base class to mock devices controlled via serial.

    It has two :class:`io.BytesIO` buffers.  One `write()`s into the
    the output buffer and `read()`s from the input buffer.  After a
    write, the output buffer is analysed for a command.  If there is a
    command, stuff gets done.  This usually means adding to the input
    buffer and changing state of the device.
    """
    def __init__(self, *args, **kwargs):
        super(SerialMock, self).__init__(*args, **kwargs)
        self.in_buffer = io.BytesIO()
        self.out_buffer = io.BytesIO()

        ## Number of bytes in out buffer pending 'interpretation'.  A
        ## command is only interpreted and handled when EOL is seen.
        self.out_pending_bytes = 0
        self.out_parsed_bytes = 0

        ## Number of bytes in the input buffer that have been read
        self.in_read_bytes = 0

    def open(self):
        pass

    def close(self):
        self.in_buffer.close()
        self.out_buffer.close()

    def handle(self, command):
        raise NotImplementedError('sub classes need to implement handle()')

    def write(self, data):
        self.out_buffer.write(data)
        self.out_pending_bytes += len(data)

        if self.out_pending_bytes > len(data):
            ## we need to retrieve data from a previous write
            self.out_buffer.seek(-self.out_pending_bytes, 2)
            data = self.out_buffer.read(self.out_pending_bytes)

        for msg in data.split(self.eol)[:-1]:
            self.handle(msg)
            self.out_pending_bytes -= len(msg) + len(self.eol)
        return len(data)

    def _readx_wrapper(self, reader, *args, **kwargs):
        """Place pointer of input buffer before and after read methods"""
        self.in_buffer.seek(self.in_read_bytes)
        msg = reader(*args, **kwargs)
        self.in_read_bytes += len(msg)
        return msg

    def read(self, size=1):
        return self._readx_wrapper(self.in_buffer.read, size)

    def readline(self, size=-1):
        return self._readx_wrapper(self.in_buffer.readline, size)

    def reset_input_buffer(self):
        self.in_read_bytes = self.in_buffer.getbuffer().nbytes
        self.in_buffer.seek(0, 2)

    def reset_output_buffer(self):
        pass
