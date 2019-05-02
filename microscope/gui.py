#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2017 David Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Simple GUIs for individual devices.

This is meant as a simple GUIs for help during development.  It does
not aim to be pretty; it aims to be simple, complete, and work on any
OS and Python without extra work.  It is not meant as the basis for a
full-fledged microscope GUI.

Tk was chosen for sake of simplicity.  It is part of Python core so
will be the easiest for users to test microscope and their hardware.
It also prevents the version compatibility problems we have had with
wxPython and PyQt.
"""

import tkinter

import numpy


class Device(tkinter.Frame):
    def __init__(self, device, master=None, *args, **kwargs):
        tkinter.Frame.__init__(self, master, *args, **kwargs)
        self.device = device
        seld.draw_table()

    def draw_table(self):
        row_idx = 0
        for key, val in sorted(self.device.get_all_settings().items()):
            tkinter.Label(self, text=key).grid(row=row_idx, column=0)
            entry = tkinter.Entry(self)
            entry.grid(row=row_idx, column=1)
            entry.insert(0, str(val))
            row_idx +=1


class DeformableMirror(tkinter.Frame):
    def __init__(self, dm, master=None, *args, **kwargs):
        tkinter.Frame.__init__(self, master, *args, **kwargs)

        self.dm = dm
        n = dm.n_actuators
        self.dm_pattern = numpy.full((n), 0.5)

        ## We have a lot of Scales so we want a scrollbar.  For this,
        ## create a Canvas and insert the Scales inside.  The Scrollbar is
        ## associated with the canvas and controls the Canvas window.
        ## However, we would be forced to manage the position of the
        ## Scales inside the Canvas so instead we create another Frame to
        ## hold the Scales and place that Frame inside the Canvas.
        ##
        ## This is because in tk, scrollbars are their own widgets that
        ## are associated to other widgets.  They can only be associated
        ## with a small set of Widgets, the ones that support the standard
        ## scrollbar interface, such as Listbox, Text, Canvas, and Entry.
        ## So we can't associated the Scrollbar directly with a Frame.

        self.canvas = tkinter.Canvas(self)
        self.canvas_frame = tkinter.Frame(self.canvas)

        zero_button = tkinter.Button(self.canvas_frame,
                                     text="Set all actuators to 0.5",
                                     command=self.zero)
        zero_button.pack(fill='x')
        self.zero_button = zero_button

        self.sliders = [None] * n
        for i in range(n):
            callback = lambda s,i=i: self.set_actuator(i, float(s))
            slider = tkinter.Scale(self.canvas_frame, orient='horizontal',
                                   from_=0, to=1, resolution=0.01,
                                   label="actuator #%i" % i,
                                   command=callback)
            slider.set(0.5)
            slider.pack(fill='x')
            self.sliders[i] = slider

        self.canvas.pack(side='left', fill='both', expand=True)

        self.scrollbar = tkinter.Scrollbar(self.canvas, command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=self.scrollbar.set,
                              scrollregion=self.canvas.bbox('all'))

        self.canvas_window = self.canvas.create_window((0,0),
                                                       window=self.canvas_frame,
                                                       anchor='nw')

        ## Moving scrollbar will trigger configure on canvas_frame.
        ## Resizing DeformableMirror Frame on the Y axis will trigger canvas.
        ## Resizing DeformableMirror Frame on the X axis will trigger both
        ## canvas and canvas_frame.
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        self.canvas_frame.bind('<Configure>', self.on_canvas_frame_configure)

    def on_canvas_configure(self, event):
        new_width = event.width - self.scrollbar.winfo_width()
        self.canvas.itemconfig(self.canvas_window, width=new_width)

    def on_canvas_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        ## We don't know what pattern is the DM currently set to, so set
        ## it to whatever is being displayed on the widget.
        self.dm.apply_pattern(self.dm_pattern)

    def set_actuator(self, i, val):
        self.dm_pattern[i] = val
        self.dm.apply_pattern(self.dm_pattern)

    def zero(self):
        for s in self.sliders:
            s.set(0.5)
        self.dm_pattern[:] = 0.5
        self.dm.apply_pattern(self.dm_pattern)


def make_app(frame_cls, *args, **kwargs):
    """Make a simple tkinter application from a single Frame.

    A utility function that wraps a single tkinter Frame into its own
    application.

    Args:
        frame_cls (tkinter.Frame): Frame class
        *args: Argument list to initialize `frame_cls`
        **kwargs: Keyword arguments to initialize `frame_cls`
    """
    toplevel = tkinter.Tk()
    frame = frame_cls(*args, master=toplevel, **kwargs)
    frame.pack(fill='both', expand=True)
    toplevel.mainloop()
