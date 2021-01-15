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
  :class:`microscope.cameras.atmcd.AndotAtmcd`)
- Photometrics (:class:`microscope.cameras.pvcam.PVCamera`)
- QImaging (:class:`microscope.cameras.pvcam.PVCamera`)
- Ximea (:class:`microscope.cameras.ximea.XimeaCamera`)

Controllers
===========

- CoolLED (:class:`microscope.controllers.coolled.CoolLED`)
- Prior ProScan III (:class:`microscope.controllers.prior.ProScanIII`)
- Lumencor Spectra III light engine (:class:`microscope.controllers.lumencor.SpectraIIILightEngine`)
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

- Zaber (:class:`microscope.controllers.zaber.ZaberDaisyChain`)

Other
=====

- Aurox Clarity (:class:`microscope.filterwheels.aurox.Clarity`)
