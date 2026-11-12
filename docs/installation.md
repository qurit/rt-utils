# Installation

```{code-block} bash
pip install rt-utils
```

RT-Utils supports **Python 3.9 and newer** and is tested on 3.9 through 3.13.

## Dependencies

Installed automatically:

```{list-table}
:header-rows: 1
:widths: 30 70

* - Package
  - Used for
* - `pydicom`
  - Reading and writing DICOM
* - `numpy`
  - Masks, and the pixel-to-patient transformations
* - `opencv-python-headless`
  - Tracing contours from masks and rasterising them back
* - `scipy`
  - Mask smoothing
```

:::{note}
The dependency is `opencv-python-headless`, not `opencv-python`, so no
`libGL` system package is needed on a headless host or in a slim container.

Both packages provide the `cv2` module and the last one installed wins. If you
rely on `cv2.imshow` elsewhere in the same environment, pin `opencv-python`
explicitly.
:::

## Optional: NIfTI conversion

{func}`rt_utils.nifti.nifti_to_mask` needs SimpleITK, which is not installed by
default because it is large and most users do not need it:

```{code-block} bash
pip install "rt-utils[nifti]"
```

See {doc}`guide/nifti`.

## From source

```{code-block} bash
git clone https://github.com/qurit/rt-utils.git
cd rt-utils
pip install -e ".[dev]"
```

The `dev` extra adds `pytest`, `black`, `build`, `twine` and SimpleITK, which
is what CI installs. Run the suite with:

```{code-block} bash
pytest
```

The tests build their DICOM fixtures in memory, so no sample data download is
required.

## Checking the install

```{code-block} python
import rt_utils

print(rt_utils.__version__)
```
