The following is a summary of the user-visible changes for each of
python-microscope releases.

Version 0.7.0 (upcoming)
------------------------

* Selected most important, backwards incompatible, changes:

  * The `Camera.get_trigger_type` method, deprecated on version 0.6.0,
    has been removed as well as the multiple `TRIGGER_*` constants it
    returned.  Use the `Camera.trigger_type` and `Camera.trigger_mode`
    properties.  Note that, despite the similar names, the removed
    `Camera.get_trigger_type` does not return the same as
    `Camera.trigger_type` property.

* New devices supported:

  * Toptica iChrome MLE

* The device server logging was broken in version 0.6.0 for Windows
  and macOS (systems not using fork for multiprocessing).  This
  version fixes that issue.

* Microscope is now dependent on Python 3.7 or later.


Version 0.6.0 (2021/01/14)
--------------------------

* Selected most important, backwards incompatible, changes:

  * The `LaserDevice` has changed the methods to set laser power to
    use fractional values in the [0 1] range instead of milliwatts.
    Effectively, the following methods have been removed:

    * `LaserDevice.get_max_power_mw`
    * `LaserDevice.get_min_power_mw`
    * `LaserDevice.get_power_mw`
    * `LaserDevice.get_set_power_mw`
    * `LaserDevice.set_power_mw`

    And have been replaced with a `LaserDevice.power` property and
    `LaserDevice.get_set_power` method.

* Changes to device ABCs:

  * Device:

    * The `make_safe` method was removed.  This was not an abstract
      method and was not implemented in most devices.  In few cases
      where it was implemented, it can be replaced with `disable`.

  * Camera:

    * The `get_sensor_temperature` method was removed.  This was not
      an abstract method was only implemented on `AndorAtmcd` and
      `XimeaCamera`.  It is now available under the settings
      dictionary under camera specific terms if supported by the
      device.

  * FilterWheel:

    * The `get_filters` method and the constructor `filters` argument
      have been removed.

    * New `position` and `n_positions` properties added to replace
      `get_position`, `set_position`, and `get_num_positions` methods.

  * Laser:

    * This has been renamed `LightSource` since it was being used for
      non-laser light sources.  The name remains for backwards
      compatibility.  Similarly, all modules in ``microscope.lasers``
      were moved to ``microscope.lights`` and previous names remain
      for backwards compatibility.

  * LightSource:

    * Now implement the `TriggerTargetMixin` interface so the trigger
      type can be configured.

  * TriggerTargetMixIn:

    * New `trigger` method for software triggers.

* Device specific changes:

  * Thorlabs filterwheels:

    * Positions were using base 1.  This has been fixed and now uses
      base 0.

    * Instead of using the individual `ThorlabsFW102C` and
      `ThorlabsFW212C`, use the base `ThorlabsFilterWheel` which will
      works for both models.

* New program `microscope-gui` to display simple GUIs given a Pyro URI
  for a microscope device.

* New optional requirement on QtPy for the GUI extra.  This
  effectively adds a dependency on one of the Qt interfaces such as
  PySide2 or PyQt5.

* The `microscope.gui` module was completely rewritten to provide Qt
  widgets instead of Tkinter.

* New `TestController`, `TestStage` and `TestStageAxis` classes.

* The `microscope.devices.device` function, used to define a device
  for the device server, is now part of the `microscope.device_server`
  module.

* The `AxisLimits, `Binning`, `ROI`, `TriggerMode`, and `TriggerType`
  classes are now available on the `microscope` module.

* New `microscope.simulators.stage_aware_camera` module which provides
  the components to simulate a microscope by simulating a camera that
  returns regions of a larger image based on the coordinates of a
  simulated stage and the position of a simulated filter wheel.

* The multiple classes that simulate the different device types, i.e.,
  the `Test*` classes in the `microscope.testsuite.devices` module,
  were moved to the `microscope.simulators` subpackage.


Version 0.5.0 (2020/03/10)
--------------------------

* New devices supported:

  * CoolLED pE-300 series.

* Changes to device ABCs:

  * New ABCs `StageDevice` and `StageAxis`.

* Device specific changes:

  * Ximea Camera:

    * Instead of device id (`dev_id`), the constructor now requires
      the camera serial number.  This is required only if there are
      multiple Ximea cameras on the system.

    * Support for hardware triggers was completely rewritten and now
      implements the `TriggerTargetMixIn` interface.  The default
      trigger type is now software only; previously it would default
      to trigger on rising edge while simultaneously accepting
      software trigers.  In addition to the `TriggerTargetMixIn`
      interface, the trigger type can also be set via the 'trigger
      source' setting.

    * Added support for ROIs and temperature readings.

  * AndorSDK3 (Andor CMOS cameras):

    * Fixed acquisition of non-square images.

  * AndorAtmcd (Andor (EM)CCD cameras):

    * Fixed 0.4.0 regression on its settings that caused
      initialization to always fail.


Version 0.4.0 (2020/01/07)
--------------------------

* Selected most important, backwards incompatible, changes:

  * The `Setting` class is now private.  The only supported method to
    add settings to a `Device` is via its `add_setting` method.

* New devices supported:

  * Coherent Obis laser
  * Lumencor Spectra III light engine
  * Prior ProScan III controller
  * Prior filter wheels
  * Toptica iBeam laser
  * Zaber LED controllers
  * Zaber filter wheels and cube turrets
  * Zaber stages

* Changes to device ABCs:

  * Device:

    * The `Device._logger` attribute has been removed.  It is
      recommended to use a logger for the module.

  * DeformableMirror:

    * Concrete classes must implement the `n_actuators` public
      property instead of the private _n_actuators`.

* Device specific changes:

  * Ximea Camera:

    * Support for the ximea cameras was completely rewritten to
      support hardware triggers, as well as fix multiple minor issues.

* The device server and clients no longer force pickle protocol
  version 2.  If the client and server are running different Python
  versions it may be necessary to specify a version number.  This
  should be done on the side with the highest support version number
  by setting `Pyro4.config.PICKLE_PROTOCOL_VERSION`.


Version 0.3.0 (2019/11/07)
--------------------------

* Selected most important, backwards incompatible, changes:

  * `microscope.device`, function used to create a device definition,
    changed signature.  The arguments to the device constructor must
    now be passed as a dictionary.

  * Python 2 is no longer supported.

  * New requirements:

    * Python >= 3.5
    * hidapi

* New devices supported:

  * Andor (EM)CCD cameras (requires Andor's atmcd C library)
  * Aurox Clarity (requires hidapi Python package)
  * Imagine Optic Mirao 52-e deformable mirror (requires mirao52e C library)
  * Linkam Correlative Microscopy Stage (requires LinkamSDK C library)
  * Ximea cameras (requires Ximea's xiAPI Python package)

* Changes to device ABCs:

  * New ABC `ControllerDevice` for controller devices.

  * Laser devices:

    * New abstract methods:

      * `LaserDevice.get_min_power_mw`
      * `LaserDevice.is_alive`

    * `LaserDevice.set_power_mw` now clips the set value to the device
      actual range.  Previously, the behaviour was undefined and
      device specific.

  * Camera devices:

    * Added ROIs and binning support.

    * New abstract methods:

      * `CameraDevice._get_binning`
      * `CameraDevice._get_roi`
      * `CameraDevice._set_binning`
      * `CameraDevice._set_roi`

  * DataDevices:

    * Data clients are now on a stack to facilitate temporary
      redirection of data to some other client.

  * Filterwheel devices:

    * New method `FilterWheelBase.get_num_positions`

    * New abstract methods:

      * `FilterWheelBase.get_position`
      * `FilterWheelBase.set_position`

* Device specific changes:

  * Omicron TA Deepstar laser:

    * Now returns actual laser power instead of the set laser power.
      Requires device to be fitted with the APC option.

  * Test camera:

    * Added new setting to control created image.  In addition of
      noise, can also return stripes, spots, or gradients.  See
      `microscope.testsuite.devices.ImageGenerator`.

* Removed requirements:

  * enum34
  * six

* The `deviceserver` program can now be used as a Windows service.

* Fixed PyPI releases to include the `microscope.mirrorq and
  `microscope.filterwheels` subpackages.

* New `microscope.devices.ROI` and `microscope.devices.Binning`
  classes to represent those camera settings.


Version 0.2.0 (2018/06/13)
--------------------------

* New classes:

  * DeformableMirror
  * TriggerTargetMixIn
  * SerialDeviceMixIn
  * TriggerType
  * TriggerMode

* New hardware supported:

  * Alpao deformable mirrors
  * Boston Micromachines Corporation (BMC) deformable mirrors
  * Thorlabs filter wheels

* Abstract class for FilterWheel moved to the `microscope.devices`
  module, where all other abstract device class are.

* New module `microscope.gui` for simple testing of individual
  devices.

* Now dependent on the enum34 package for python pre 3.4.

* Multiple fixes to support Python 3.

* This is the last release with planned support for Python 2.


Version 0.1.0 (2017/05/04)
--------------------------

* New abstract class FilterWheel.

* New classes Client and DataClient.

* New dependency on six.

* Removed dependency on PyME.

* Now works in Linux too.

* Start writing of user documentation.


Version 0.0.1 (2016/11/24)
--------------------------

* Initial release of python-microscope.
