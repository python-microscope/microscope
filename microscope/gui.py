#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
#
# Microscope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Microscope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""Simple GUIs for individual devices.

This is meant as a simple GUIs for help during development.  It does
not aim to be pretty; it aims to be simple, complete, and work on any
OS and Python without extra work.  It is not meant as the basis for a
full-fledged microscope GUI.

This module requires PySide2 which is an requirement for the
microscope "GUI" extra, i.e., only installed by `pip` if microscope is
installed with ``pip install microscope[GUI]``.

"""

import argparse
import sys
import typing

import numpy
import Pyro4
from qtpy import QtCore, QtGui, QtWidgets

import microscope.devices


# We use pickle so we can serialize numpy arrays for camera images and
# deformable mirrors patterns.
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'


class DeviceSettingsWidget(QtWidgets.QWidget):
    """Table of device settings and its values.

    This widget simply shows the available settings on the device and
    their current value.  In the future it may add the possibility to
    modify them.

    """
    def __init__(self, device: microscope.devices.Device,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        layout = QtWidgets.QFormLayout(self)
        for key, value in sorted(self._device.get_all_settings().items()):
            layout.addRow(key, QtWidgets.QLabel(parent=self, text=str(value)))
        self.setLayout(layout)


class DeformableMirrorWidget(QtWidgets.QWidget):
    """Display a slider for each actuator.

    Constructing this widget will set all actuators to their mid-point
    since the actuators position are not queryable..  The reset button
    does this too, i.e., it sets all actuators to their mid-point.
    """
    def __init__(self, device: microscope.devices.DeformableMirror,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        self._pattern = numpy.ndarray(shape=(self._device.n_actuators))
        self._actuators = [] # type: typing.List[QtWidgets.QSlider]
        for i in range(self._device.n_actuators):
            actuator = QtWidgets.QSlider(QtCore.Qt.Horizontal, parent=self)
            actuator.setMinimum(0)
            actuator.setMaximum(100)
            def setThisActuator(value, actuator_index=i):
                self.setActuatorValue(actuator_index, value)
            actuator.valueChanged.connect(setThisActuator)
            self._actuators.append(actuator)
        # We don't know the pattern currently applied to the mirror so
        # we reset it which also updates the slider positions.
        self.resetPattern()

        self._reset_button = QtWidgets.QPushButton('Reset', parent=self)
        self._reset_button.clicked.connect(self.resetPattern)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._reset_button)

        actuators_layout = QtWidgets.QFormLayout()
        actuators_layout.setLabelAlignment(QtCore.Qt.AlignRight)
        for i, actuator in enumerate(self._actuators, start=1):
            actuators_layout.addRow(str(i), actuator)
        main_layout.addLayout(actuators_layout)

        self.setLayout(main_layout)


    def setActuatorValue(self, actuator_index: int, value: int) -> None:
        if not (0 < actuator_index < self._pattern.size):
            raise ValueError('index %d is invalid because DM has %d actuators'
                             % (actuator_index, self._pattern.size))
        self._pattern[actuator_index] = value / 100.0
        self._device.apply_pattern(self._pattern)

    def resetPattern(self) -> None:
        """Set all actuators to their mid-point (0.5)."""
        self._pattern.fill(0.5)
        self._device.apply_pattern(self._pattern)
        for i, actuator in enumerate(self._actuators):
            actuator.blockSignals(True)
            actuator.setSliderPosition(int(self._pattern[i] * 100))
            actuator.blockSignals(False)


class FilterWheelWidget(QtWidgets.QWidget):
    """Group of toggle push buttons to change filter position.

    This widget shows a table of toggle buttons with the filterwheel
    position numbers.
    """
    def __init__(self, device: microscope.devices.FilterWheelBase,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        self._button_grp = QtWidgets.QButtonGroup(self)
        for i in range(self._device.n_positions):
            button = QtWidgets.QPushButton(str(i+1), parent=self)
            button.setCheckable(True)
            self._button_grp.addButton(button, i)
        self._button_grp.button(self._device.position).setChecked(True)

        # We use buttonClicked instead of idClicked because that
        # requires Qt 5.15 which is too recent.  Once we can use
        # idClicked, then the slot will automatically get the wanted
        # position.
        self._button_grp.buttonClicked.connect(self.setFilterWheelPosition)

        layout = QtWidgets.QVBoxLayout()
        for button in self._button_grp.buttons():
            layout.addWidget(button)
        self.setLayout(layout)

    def setFilterWheelPosition(self) -> None:
        self._device.position = self._button_grp.checkedId()


class StageWidget(QtWidgets.QWidget):
    """Stage widget displaying each of the axis position.

    This widget shows each of the axis, their limits, and a spin box
    to change the axis position.  This requires the stage to be
    enabled since otherwise it is not able to move it or query the
    limits.
    """
    def __init__(self, device: microscope.devices.StageDevice,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device = device

        layout = QtWidgets.QFormLayout(self)
        for name, axis in self._device.axes.items():
            label = ('%s (%s : %s)'
                     % (name, axis.limits.lower, axis.limits.upper))

            position_box = QtWidgets.QDoubleSpinBox(parent=self)
            position_box.setMinimum(axis.limits.lower)
            position_box.setMaximum(axis.limits.upper)
            position_box.setValue(axis.position)
            position_box.setSingleStep(1.0)
            def setPositionSlot(position: float, name: str = name):
                return self.setPosition(name, position)
            position_box.valueChanged.connect(setPositionSlot)

            layout.addRow(label, position_box)
        self.setLayout(layout)

    def setPosition(self, name: str, position: float) -> None:
        self._device.axes[name].move_to(position)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, widget: QtWidgets.QWidget) -> None:
        super().__init__()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        self.setCentralWidget(scroll)
        for key, slot in ((QtGui.QKeySequence.Quit, self.close),
                          (QtGui.QKeySequence.Close, self.close),):
            shortcut = QtWidgets.QShortcut(key, self)
            shortcut.activated.connect(slot)


def main(argv=sys.argv) -> int:
    app = QtWidgets.QApplication(argv)
    app.setApplicationName('Microscope GUI')
    app.setOrganizationDomain('python-microscope.org')

    type_to_widget = {
        'DeformableMirror' : DeformableMirrorWidget,
        'DeviceSettings' : DeviceSettingsWidget,
        'FilterWheel' : FilterWheelWidget,
        'Stage' : StageWidget,
    }

    parser = argparse.ArgumentParser(prog='microscope-gui')
    parser.add_argument('type', action='store', type=str, metavar='DEVICE-TYPE',
                        choices=type_to_widget.keys(), help='Type of device')
    parser.add_argument('uri', action='store', type=str, metavar='DEVICE-URI',
                        help='URI for device')
    args = parser.parse_args(app.arguments()[1:])

    device = Pyro4.Proxy(args.uri)
    widget_cls = type_to_widget[args.type]
    widget = widget_cls(device)
    window = MainWindow(widget)
    window.show()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
