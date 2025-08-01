.. Copyright (C) 2020 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>

   This work is licensed under the Creative Commons
   Attribution-ShareAlike 4.0 International License.  To view a copy of
   this license, visit http://creativecommons.org/licenses/by-sa/4.0/.

.. _supported-devices:

Supported Devices
*****************

The following group of devices is currently supported.  To request
support for more devices, open an issue on the issue tracker.

Cameras
=======

- Andor (:class:`microscope.cameras.andorsdk3.AndorSDK3` and
  :class:`microscope.cameras.atmcd.AndorAtmcd`)
- Hamamatsu (:class:`microscope.cameras.hamamatsu.HamamatsuCamera`)
- Photometrics (:class:`microscope.cameras.pvcam.PVCamera`)
- QImaging (:class:`microscope.cameras.pvcam.PVCamera`)
- Raspberry Pi camera (:class:`microscope.cameras.picamera.PiCamera`)
- Ximea (:class:`microscope.cameras.ximea.XimeaCamera`)

Controllers
===========

- ASI MS2000 (:class:`microscope.controllers.asi.ASIMS2000`)
- CoolLED (:class:`microscope.controllers.coolled.CoolLED`)
- Ludl MC 2000 (:class:`microscope.controllers.ludl.LudlMC2000`)
- Lumencor Spectra III light engine
  (:class:`microscope.controllers.lumencor.SpectraIIILightEngine`)
- Prior ProScan III (:class:`microscope.controllers.prior.ProScanIII`)
- Toptica iChrome MLE (:class:`microscope.controllers.toptica.iChromeMLE`)
- Zaber daisy chain devices
  (:class:`microscope.controllers.zaber.ZaberDaisyChain`)
- Zaber LED controller (:class:`microscope.controllers.zaber.ZaberDaisyChain`)

Deformable Mirrors
==================

- Alpao (:class:`microscope.mirror.alpao.AlpaoDeformableMirror`)
- Boston Micromachines Corporation
  (:class:`microscope.mirror.bmc.BMCDeformableMirror`)
- Imagine Optic Mirao 52e (:class:`microscope.mirror.mirao52e.Mirao52e`)

Filter Wheels
=============

- Prior (:mod:`microscope.controllers.prior`)
- Thorlabs (:mod:`microscope.filterwheels.thorlabs`)
- Thorlabs ELL sliders (:mod:'microscope.filterwheels.ell_slider')
- Zaber (:class:`microscope.controllers.zaber.ZaberDaisyChain`)

Light Sources
=============

- Cobolt (:class:`microscope.lights.cobolt.CoboltLaser`)
- Coherent Obis (:class:`microscope.lights.obis.ObisLaser`)
- Coherent Sapphire (:class:`microscope.lights.sapphire.SapphireLaser`)
- Omicron Deepstar (:class:`microscope.lights.deepstar.DeepstarLaser`)
- Toptica iBeam (:class:`microscope.lights.toptica.TopticaiBeam`)

Stages
======

- Linkam CMS196 (:class:`microscope.stages.linkam.LinkamCMS`)
- Ludl (:class:`microscope.controllers.ludl.LudlMC2000`)
- Zaber (:class:`microscope.controllers.zaber.ZaberDaisyChain`)

DigitalIO
=========

- Raspberry Pi (:class:`microscope.digitalio.raspberrypi.RPiDIO`)


ValueLogger
===========

- Raspberry Pi
  (:class:`microscope.valuelogger.raspberrypi.RPiValueLogger`)
  includes support for the MCP9808 and TSYS01 I2C temperature sensors


Other
=====

- Aurox Clarity (:class:`microscope.filterwheels.aurox.Clarity`)
