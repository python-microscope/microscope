#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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

"""Simple GUIs for individual devices.

This is meant as a simple GUIs for help during development.  It does
not aim to be pretty; it aims to be simple, complete, and work on any
OS and Python without extra work.  It is not meant as the basis for a
full-fledged microscope GUI.

This module requires qtpy which is a requirement for the microscope
"GUI" extra, i.e., only installed by `pip` if microscope is installed
with ``pip install microscope[GUI]``.

"""

import argparse
import logging
import queue
import sys
import threading
import typing

import numpy
import Pyro4
from qtpy import QtCore, QtGui, QtWidgets

import microscope.abc


_logger = logging.getLogger(__name__)


# We use pickle so we can serialize numpy arrays for camera images and
# deformable mirrors patterns.
Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
Pyro4.config.SERIALIZER = "pickle"


class DeviceSettingsWidget(QtWidgets.QWidget):
    """Table of device settings and its values.

    This widget simply shows the available settings on the device and
    their current value.  In the future it may add the possibility to
    modify them.

    """

    def __init__(self, device: microscope.abc.Device, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        layout = QtWidgets.QFormLayout(self)
        for key, value in sorted(self._device.get_all_settings().items()):
            layout.addRow(key, QtWidgets.QLabel(parent=self, text=str(value)))
        self.setLayout(layout)


class ControllerWidget(QtWidgets.QWidget):
    """Show devices in a controller.

    This widget shows a series of buttons with the name of the
    multiple devices in a controller.  Toggling those buttons displays
    or hides a widget for that controlled device.

    """

    def __init__(
        self, device: microscope.abc.Controller, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        self._button2window: typing.Dict[
            QtWidgets.QPushButton, typing.Optional[QtWidgets.QMainWindow]
        ] = {}
        self._button2name: typing.Dict[QtWidgets.QPushButton, str] = {}

        self._button_grp = QtWidgets.QButtonGroup(self)
        self._button_grp.setExclusive(False)
        for name in self._device.devices.keys():
            button = QtWidgets.QPushButton(name, parent=self)
            button.setCheckable(True)
            self._button_grp.addButton(button)
            self._button2name[button] = name
            self._button2window[button] = None
        self._button_grp.buttonToggled.connect(self.toggleDeviceWidget)

        layout = QtWidgets.QVBoxLayout()
        for button in self._button_grp.buttons():
            layout.addWidget(button)
        self.setLayout(layout)

    def toggleDeviceWidget(
        self, button: QtWidgets.QAbstractButton, checked: bool
    ) -> None:
        if checked:
            device = self._device.devices[self._button2name[button]]
            widget_cls = _guess_device_widget(device)
            widget = widget_cls(device)
            window = MainWindow(widget, parent=self)
            self._button2window[button] = window
            window.show()
        else:
            window = self._button2window[button]
            if window is None:
                _logger.error(
                    "unchecking subdevice button but there's no window"
                )
            else:
                window.close()
                self._button2window[button] = None


class _DataQueue(queue.Queue):
    @Pyro4.expose
    def put(self, *args, **kwargs):
        return super().put(*args, **kwargs)


class _Imager(QtCore.QObject):
    """Helper for CameraWidget handling the internals of the camera trigger."""

    imageAcquired = QtCore.Signal(numpy.ndarray)

    def __init__(self, camera: microscope.abc.Camera) -> None:
        super().__init__()
        self._camera = camera
        self._data_queue = _DataQueue()
        if isinstance(self._camera, Pyro4.Proxy):
            pyro_daemon = Pyro4.Daemon()
            queue_uri = pyro_daemon.register(self._data_queue)
            self._camera.set_client(queue_uri)
            data_thread = threading.Thread(
                target=pyro_daemon.requestLoop, daemon=True
            )
            data_thread.start()
        else:
            self._device.set_client(self._data_queue)
        fetch_thread = threading.Thread(target=self.fetchLoop, daemon=True)
        fetch_thread.start()

        # Depending on the Qt backend this might not get called (seems
        # to work on PySide2 but not with PyQt5).  The device itself
        # should be removing clients that no longer work anyway.
        self.destroyed.connect(lambda: self._camera.set_client(None))

    def snap(self) -> None:
        self._camera.trigger()

    def fetchLoop(self) -> None:
        while True:
            # We may be getting images faster than we can display so
            # only get the last image in the queue and discard the
            # rest (we could do with a class that only has one item
            # and putting a new item will discard the previous instead
            # of blocking/queue).
            data = self._data_queue.get()
            while not self._data_queue.empty():
                data = self._data_queue.get()
            self.imageAcquired.emit(data)


class CameraWidget(QtWidgets.QWidget):
    """Display camera"""

    def __init__(self, device: microscope.abc.Camera, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._device = device
        self._imager = _Imager(self._device)
        self._imager.imageAcquired.connect(self.displayData)

        self._view = QtWidgets.QLabel(parent=self)
        self.displayData(
            numpy.zeros(self._device.get_sensor_shape(), dtype=numpy.uint8)
        )

        self._enable_check = QtWidgets.QCheckBox("Enabled", parent=self)
        self._enable_check.stateChanged.connect(self.updateEnableState)

        self._exposure_box = QtWidgets.QDoubleSpinBox(parent=self)
        self._exposure_box.setSuffix(" sec")
        self._exposure_box.setSingleStep(0.1)
        self._exposure_box.valueChanged.connect(self._device.set_exposure_time)

        self._snap_button = QtWidgets.QPushButton("Snap", parent=self)
        self._snap_button.clicked.connect(self._imager.snap)

        self.updateEnableState()

        layout = QtWidgets.QVBoxLayout()
        controls_row = QtWidgets.QHBoxLayout()
        for widget in [
            self._enable_check,
            self._exposure_box,
            self._snap_button,
        ]:
            controls_row.addWidget(widget)
        layout.addLayout(controls_row)
        layout.addWidget(self._view)
        self.setLayout(layout)

    def updateEnableState(self) -> None:
        """Update UI and camera state after enable check box"""
        if self._enable_check.isChecked():
            self._device.enable()
        else:
            self._device.disable()

        if self._enable_check.isChecked() != self._device.get_is_enabled():
            self._enable_check.setChecked(self._device.get_is_enabled())
            _logger.error(
                "failed to %s camera",
                "enable" if self._enable_check.isChecked() else "disable",
            )

        self._snap_button.setEnabled(self._device.get_is_enabled())
        self._exposure_box.setEnabled(self._device.get_is_enabled())

    def displayData(self, data: numpy.ndarray) -> None:
        np_to_qt = {
            numpy.dtype("uint8"): QtGui.QImage.Format_Grayscale8,
            numpy.dtype("uint16"): QtGui.QImage.Format_Grayscale16,
        }
        qt_img = QtGui.QImage(
            data.tobytes(), *data.shape, np_to_qt[data.dtype]
        )
        self._view.setPixmap(QtGui.QPixmap.fromImage(qt_img))


class DeformableMirrorWidget(QtWidgets.QWidget):
    """Display a slider for each actuator.

    Constructing this widget will set all actuators to their mid-point
    since the actuators position are not queryable..  The reset button
    does this too, i.e., it sets all actuators to their mid-point.
    """

    def __init__(
        self, device: microscope.abc.DeformableMirror, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        self._pattern = numpy.ndarray(shape=(self._device.n_actuators))
        self._actuators: typing.List[QtWidgets.QSlider] = []
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

        self._reset_button = QtWidgets.QPushButton("Reset", parent=self)
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
            raise ValueError(
                "index %d is invalid because DM has %d actuators"
                % (actuator_index, self._pattern.size)
            )
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

    def __init__(
        self, device: microscope.abc.FilterWheel, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        self._button_grp = QtWidgets.QButtonGroup(self)
        for i in range(self._device.n_positions):
            button = QtWidgets.QPushButton(str(i + 1), parent=self)
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


class LightSourceWidget(QtWidgets.QWidget):
    def __init__(
        self, device: microscope.abc.LightSource, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        self._enable_check = QtWidgets.QCheckBox("Enabled", parent=self)
        self._enable_check.stateChanged.connect(self.updateEnableState)

        self._set_power_box = QtWidgets.QDoubleSpinBox(parent=self)
        self._set_power_box.setMinimum(0.0)
        self._set_power_box.setMaximum(1.0)
        self._set_power_box.setValue(self._device.power)
        self._set_power_box.setSingleStep(0.01)
        self._set_power_box.setAlignment(QtCore.Qt.AlignRight)
        self._set_power_box.valueChanged.connect(
            lambda x: setattr(self._device, "power", x)
        )

        self._current_power = QtWidgets.QLineEdit(
            str(self._device.power), parent=self
        )
        self._current_power.setReadOnly(True)
        self._current_power.setAlignment(QtCore.Qt.AlignRight)

        self._get_power_timer = QtCore.QTimer(self)
        self._get_power_timer.timeout.connect(self.updateCurrentPower)
        self._get_power_timer.setInterval(500)  # msec

        self.updateEnableState()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._enable_check)
        power_layout = QtWidgets.QFormLayout()
        power_layout.addRow("Set power", self._set_power_box)
        power_layout.addRow("Current power", self._current_power)
        layout.addLayout(power_layout)
        self.setLayout(layout)

    def updateEnableState(self) -> None:
        """Update UI and light source state after enable check box"""
        if self._enable_check.isChecked():
            self._device.enable()
        else:
            self._device.disable()

        device_is_enabled = self._device.get_is_enabled()

        if self._enable_check.isChecked() != device_is_enabled:
            self._enable_check.setChecked(device_is_enabled)
            _logger.error(
                "failed to %s light",
                "enable" if self._enable_check.isChecked() else "disable",
            )

        self._current_power.setEnabled(device_is_enabled)
        if device_is_enabled:
            self._get_power_timer.start()
        else:
            self._get_power_timer.stop()
            self._current_power.setText("0.0")

    def updateCurrentPower(self) -> None:
        self._current_power.setText(str(self._device.power))


class StageWidget(QtWidgets.QWidget):
    """Stage widget displaying each of the axis position.

    This widget shows each of the axis, their limits, and a spin box
    to change the axis position.  This requires the stage to be
    enabled since otherwise it is not able to move it or query the
    limits.
    """

    def __init__(self, device: microscope.abc.Stage, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._device = device

        layout = QtWidgets.QFormLayout(self)
        for name, axis in self._device.axes.items():
            label = "%s (%s : %s)" % (
                name,
                axis.limits.lower,
                axis.limits.upper,
            )

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
    def __init__(self, widget: QtWidgets.QWidget, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        self.setCentralWidget(scroll)
        for key, slot in (
            (QtGui.QKeySequence.Quit, self.close),
            (QtGui.QKeySequence.Close, self.close),
        ):
            shortcut = QtWidgets.QShortcut(key, self)
            shortcut.activated.connect(slot)


def _guess_device_widget(device) -> QtWidgets.QWidget:
    if hasattr(device, "axes"):
        return StageWidget
    elif hasattr(device, "devices"):
        return ControllerWidget
    elif hasattr(device, "n_positions"):
        return FilterWheelWidget
    elif hasattr(device, "power"):
        return LightSourceWidget
    elif hasattr(device, "n_actuators"):
        return DeformableMirrorWidget
    elif hasattr(device, "get_sensor_shape"):
        return CameraWidget
    elif hasattr(device, "get_all_settings"):
        return DeviceSettingsWidget
    else:
        raise TypeError("device is not a Microscope Device")


def main(argv: typing.Sequence[str]) -> int:
    app = QtWidgets.QApplication(argv)
    app.setApplicationName("Microscope GUI")
    app.setOrganizationDomain("python-microscope.org")

    type_to_widget = {
        "Camera": CameraWidget,
        "Controller": ControllerWidget,
        "DeformableMirror": DeformableMirrorWidget,
        "DeviceSettings": DeviceSettingsWidget,
        "FilterWheel": FilterWheelWidget,
        "LightSourceWidget": LightSourceWidget,
        "Stage": StageWidget,
    }

    parser = argparse.ArgumentParser(prog="microscope-gui")

    # Although we have a function that can guess the device type from
    # the attributes on the proxy this is still useful.  For example,
    # to display the device settings instead of the device UI.  Or
    # maybe we're dealing with a device that implements more than one
    # interface (earlier iterations of aurox Clarity were both a
    # camera and a filterwheel).  This option provides a way to force
    # a specific widget.
    parser.add_argument(
        "type",
        action="store",
        type=str,
        metavar="DEVICE-TYPE",
        choices=type_to_widget.keys(),
        help="Type of device/widget to show",
    )

    parser.add_argument(
        "uri",
        action="store",
        type=str,
        metavar="DEVICE-URI",
        help="URI for device",
    )
    args = parser.parse_args(app.arguments()[1:])

    device = Pyro4.Proxy(args.uri)
    widget_cls = type_to_widget[args.type]
    widget = widget_cls(device)
    window = MainWindow(widget)
    window.show()

    return app.exec_()


def _setuptools_entry_point() -> int:
    # The setuptools entry point must be a function, we can't simply
    # name this module even if this module does work as a script.  We
    # also do not want to set the default of main() to sys.argv
    # because when the documentation is generated (with Sphinx's
    # autodoc extension), then sys.argv gets replaced with the
    # sys.argv value at the time docs were generated (see
    # https://stackoverflow.com/a/12087750 )
    return main(sys.argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
