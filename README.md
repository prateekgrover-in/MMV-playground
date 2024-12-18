# MMV-playground

[![License BSD-3](https://img.shields.io/pypi/l/MMV-playground.svg?color=green)](https://github.com/MMV-Lab/MMV-playground/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/MMV-playground.svg?color=green)](https://pypi.org/project/MMV-playground)
[![Python Version](https://img.shields.io/pypi/pyversions/MMV-playground.svg?color=green)](https://python.org)
[![tests](https://github.com/MMV-Lab/MMV-playground/workflows/tests/badge.svg)](https://github.com/MMV-Lab/MMV-playground/actions)
[![codecov](https://codecov.io/gh/MMV-Lab/MMV-playground/branch/main/graph/badge.svg)](https://codecov.io/gh/MMV-Lab/MMV-playground)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/MMV-playground)](https://napari-hub.org/plugins/MMV-playground)

This plugin is aimed at researchers in biology and medicine who want to segment and analyze 2D microscopy images. It offers intuitive tools for common pre-processing and analysis tasks.

----------------------------------

This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/cookiecutter-napari-plugin#getting-started

and review the napari docs for plugin developers:
https://napari.org/stable/plugins/index.html
-->

## Installation

You can install `MMV-playground` via [pip]:

    pip install MMV-playground

To install latest development version :

    pip install git+https://github.com/MMV-Lab/MMV-playground.git

## Documentation

This plugin for the graphics software Napari is designed to evaluate two-dimensional microscopy images. Images should be provided in grayscale format, as colored images are not supported. The plugin offers seven core functions for image analysis:

1. Intensity normalization

2. Smoothing

3. Background correction

4. Spot-shape filter

5. Filament-shape filter

6. Thresholding

7. Topology-preserving thinning
   
#### How is the plugin started and operated?

To start the plugin, open Napari, go to the "Plugins" menu, and select "MMV-playground (MMV-playground)". The MMV-playground interface will appear on the left side of the Napari window, displaying seven buttons - each corresponding to one of the available functions. Clicking a button opens a dialog box where you can select an image, adjust the parameters for the chosen function, and execute it by pressing the run button. Clicking the function button again collapses the dialog box.

#### Intensity normalization

Intensity normalization requires two percentage values: a lower percentage (0–5%) and an upper percentage (95–100%). The plugin calculates the corresponding percentiles for these values. Pixel intensities below the lower percentile are clipped to this value, and those above the upper percentile are clipped to the upper limit. Finally, the image intensities are rescaled to a range of 0 to 1.

#### Smoothing

The smoothing function offers two methods: Gaussian smoothing and edge-preserving smoothing. The Gaussian method utilizes [scipy.ndimage.gaussian_filter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html), while the edge-preserving method is implemented using [itk.GradientAnisotropicDiffusionImageFilter](https://itk.org/Doxygen/html/classitk_1_1GradientAnisotropicDiffusionImageFilter.html).

#### Background correction

Background correction requires specifying a kernel size (range: 1–100). The function [scipy.ndimage.white_tophat](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.white_tophat.html) is used to perform the correction based on the provided kernel size. This approach is particularly effective for images with a dark background.

#### Spot-shape filter

The spot-shape filter detects edges using the [scipy.ndimage.gaussian_laplace](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_laplace.html) function. It requires a sigma parameter, which can be set between 0.5 and 10.

#### Filament-shape filter

The filament-shape filter uses the [aicssegmentation.core.vessel.vesselness2D](https://allencell.org/segmenter.html) function, with a sigma parameter adjustable in the range of 0.25 to 5.

#### Thresholding

Thresholding allows users to select one of the following methods for determining the threshold: "Otsu," "Li," "Triangle," or "Sauvola." The output is a binary image where pixels above the threshold are set to 1, and all others are set to 0.

#### Topology-preserving thinning

The topology-preserving thinning function requires two parameters: "minimum thickness" (range: 0.5–5) and "thin" (range: 1–5).

#### What is missing

Until now the unit tests are not ready. The internal documentation of the source code is also not ready now.

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"MMV-playground" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/MMV-Lab/MMV-playground/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
