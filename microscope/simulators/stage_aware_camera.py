#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
## Copyright (C) 2020 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
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

"""Simulation of a full setup based on a given image file.
"""

import logging
import time
import typing

import numpy as np
import PIL.Image
import scipy.ndimage

import microscope
import microscope.abc
from microscope.simulators import (
    SimulatedCamera,
    SimulatedFilterWheel,
    SimulatedStage,
)


_logger = logging.getLogger(__name__)


class StageAwareCamera(SimulatedCamera):
    """Simulated camera that returns subregions of image based on stage
    position.

    Instead of using this class directly, consider using the
    :func:`simulated_setup_from_image` function which will generate
    all the required simulated devices for a given image file.

    Args:
        image: the image from which regions will be cropped based on
            the stage and filter wheel positions.
        stage: stage to read coordinates from.  Must have an "x",
            "y", and "z" axis.
        filterwheel: filter wheel to read position.

    """

    def __init__(
        self,
        image: np.ndarray,
        stage: microscope.abc.Stage,
        filterwheel: microscope.abc.FilterWheel,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._image = image
        self._stage = stage
        self._filterwheel = filterwheel
        self._pixel_size = 1.0

        if not all([name in stage.axes.keys() for name in ["x", "y", "z"]]):
            raise microscope.InitialiseError(
                "stage for StageAwareCamera requires x, y, and z axis"
            )
        if image.shape[2] != self._filterwheel.n_positions:
            raise ValueError(
                "image has %d channels but filterwheel has %d positions"
            )

        # Empty the settings dict, most of them are for testing
        # settings, and the rest is specific to the image generator
        # which we don't need.  We probably should have a simpler
        # SimulatedCamera that we could subclass.
        self._settings = {}

        self.add_setting(
            "pixel size",
            "float",
            lambda: self._pixel_size,
            lambda pxsz: setattr(self, "_pixel_size", pxsz),
            # technically should be: (nextafter(0.0, inf), nextafter(inf, 0.0))
            values=(0.0, float("inf")),
        )

    def _fetch_data(self) -> typing.Optional[np.ndarray]:
        if not self._acquiring or self._triggered == 0:
            return None

        time.sleep(self._exposure_time)
        self._triggered -= 1
        _logger.info("Creating image")

        # Use filter wheel position to select the image channel.
        channel = self._filterwheel.position

        width = self._roi.width // self._binning.h
        height = self._roi.height // self._binning.v

        # Use stage position to compute bounding box.
        xstart = int(
            (self._stage.position["x"] / self._pixel_size) - (width / 2)
        )
        ystart = int(
            (self._stage.position["y"] / self._pixel_size) - (height / 2)
        )
        xend = xstart + width
        yend = ystart + height

        # Need to check that the bounding box in entirely within the
        # source image (see #231).
        if (
            xstart < 0
            or ystart < 0
            or xend > self._image.shape[1]
            or yend > self._image.shape[0]
        ):
            # If part of image is out of bounds, pad with zeros, ...
            subsection = np.zeros((height, width), dtype=self._image.dtype)
            # work out the relevant parts of input image ...
            img_x0 = max(0, xstart)
            img_x1 = min(xend, self._image.shape[1])
            img_y0 = max(0, ystart)
            img_y1 = min(yend, self._image.shape[0])
            # and work out where to place it in output image.
            sub_x0 = max(-xstart, 0)
            sub_y0 = max(-ystart, 0)
            sub_x1 = sub_x0 + (img_x1 - img_x0)
            sub_y1 = sub_y0 + (img_y1 - img_y0)

            subsection[sub_y0:sub_y1, sub_x0:sub_x1] = self._image[
                img_y0:img_y1, img_x0:img_x1, channel
            ]
        else:
            subsection = self._image[ystart:yend, xstart:xend, channel]

        # Gaussian filter on abs Z position to simulate being out of
        # focus (Z position zero is in focus).
        blur = abs((self._stage.position["z"]) / 10.0)
        image = scipy.ndimage.gaussian_filter(subsection, blur)

        self._sent += 1
        # Not sure this flipping is correct but it's required to make
        # cockpit mosaic work.  This is probably related to not having
        # defined what the image origin should be (see issue #89).
        return np.fliplr(np.flipud(image))


def simulated_setup_from_image(
    filepath: str, **kwargs
) -> typing.Dict[str, microscope.abc.Device]:
    """Create simulated devices given an image file.

    To use with the `device-server`::

        DEVICES = [
            device(simulated_setup_from_image, 'localhost', 8000,
                   conf={'filepath': path_to_image_file}),
        ]
    """
    # PIL will error if trying to open very large images to avoid
    # decompression bomb DOS attack.  However, this is used to fake a
    # stage and will really have very very large images, so remove
    # remove the PIL limit temporarily.
    original_pil_max_image_pixels = PIL.Image.MAX_IMAGE_PIXELS
    try:
        PIL.Image.MAX_IMAGE_PIXELS = None
        image = np.array(PIL.Image.open(filepath))
    finally:
        PIL.Image.MAX_IMAGE_PIXELS = original_pil_max_image_pixels

    if len(image.shape) < 3:
        raise ValueError("not an RGB image")

    stage = SimulatedStage(
        {
            "x": microscope.AxisLimits(0, image.shape[1]),
            "y": microscope.AxisLimits(0, image.shape[0]),
            "z": microscope.AxisLimits(-50, 50),
        }
    )
    filterwheel = SimulatedFilterWheel(positions=image.shape[2])
    camera = StageAwareCamera(image, stage, filterwheel)

    return {
        "camera": camera,
        "filterwheel": filterwheel,
        "stage": stage,
    }
