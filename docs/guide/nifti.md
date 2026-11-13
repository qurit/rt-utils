# From NIfTI

```{code-block} bash
:caption: Needs SimpleITK

pip install "rt-utils[nifti]"
```

```{code-block} python
from rt_utils import RTStructBuilder
from rt_utils.nifti import nifti_to_mask

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")

mask = nifti_to_mask("segmentation.nii.gz", rtstruct.series_data)
rtstruct.add_roi(mask=mask, name="liver")

rtstruct.save("structures")
```

## Why a converter is needed

`add_roi` takes a bare NumPy array. It carries no affine, no orientation and
no spacing, so it can only assume the array already sits on the series' voxel
grid in `(Rows, Columns, Slices)` order.

A NIfTI does not satisfy that assumption by accident. It carries **its own
axis order** and **its own direction for each axis** in its affine, and
neither is guaranteed to match the series the segmentation was drawn on.
Handing `nibabel.get_fdata()` straight to `add_roi` is what makes an ROI come
back rotated, flipped or offset.

{func}`~rt_utils.nifti.nifti_to_mask` reads both geometries and resamples
between them, so the result is correct for any orientation, spacing or storage
order.

:::{danger}
No sequence of `transpose`, `flipud` and `rot90` is a substitute. The correct
rearrangement is whatever the two affines say it is, and it differs from file
to file. That is why a fix of that kind works on one dataset and silently
fails on the next.
:::

## Multi-label segmentations

TotalSegmentator and similar tools write one file with an integer per
structure. Pass `label=` to select one:

```{code-block} python
liver  = nifti_to_mask("segmentations.nii.gz", rtstruct.series_data, label=5)
spleen = nifti_to_mask("segmentations.nii.gz", rtstruct.series_data, label=1)
```

Without `label`, **any** non-zero voxel is foreground, which is right for a
single-structure mask and wrong for a label map.

A label not present in the resampled volume raises, listing the labels that
are:

```{code-block} text
ValueError: Label 7 is not present in the resampled volume.
Labels found: [1, 2, 3, 5].
```

### Converting a whole label map

```{code-block} python
import numpy as np
import SimpleITK as sitk
from rt_utils import RTStructBuilder
from rt_utils.nifti import nifti_to_mask

names = {1: "spleen", 2: "kidney_right", 3: "kidney_left", 5: "liver"}

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")

for label, name in names.items():
    mask = nifti_to_mask("segmentations.nii.gz", rtstruct.series_data, label=label)
    rtstruct.add_roi(mask=mask, name=name, roi_interpreted_type="ORGAN")

rtstruct.save("structures")
```

## What the conversion does

1. Reads the NIfTI with SimpleITK, which converts NIfTI's RAS convention to
   the LPS convention DICOM uses.
2. Builds an empty reference image describing the series' grid: size,
   spacing, origin and direction, taken from `ImageOrientationPatient`,
   `ImagePositionPatient` and `PixelSpacing`.
3. Resamples the volume onto that grid with an identity transform, since both
   are already in patient space.
4. Transposes SimpleITK's `(slice, row, column)` to the
   `(row, column, slice)` layout masks use.

Resampling is **nearest neighbour**, so the result only ever contains values
the input contained. Interpolating a label map would invent labels lying
between two real ones.

## Limits

**Uneven slice spacing.**
: The resampling grid is regular, as any image grid must be. On a series
  whose slice spacing varies, that grid follows the *average* spacing, so a
  voxel may be read from slightly the wrong plane. The contours themselves
  are still written at each slice's true position, since those come from the
  series.

**3D only.**
: A 4D file holds several volumes; select one before converting. Both the
  4D-image and the multi-component-voxel forms are detected and raise.

**Different patient, different geometry.**
: Nothing checks that the NIfTI and the series describe the same patient. If
  the two were never spatially aligned, resampling will produce a mask, just
  not a meaningful one.

## Going the other way

RT-Utils does not write NIfTI. Read the ROI as a mask and hand it to whatever
writes NIfTI in your pipeline:

```{code-block} python
import numpy as np
import SimpleITK as sitk
from rt_utils.nifti import series_reference_image

mask = rtstruct.get_roi_mask_by_name("liver")

# (row, column, slice) -> SimpleITK's (slice, row, column)
image = sitk.GetImageFromArray(np.transpose(mask, (2, 0, 1)).astype(np.uint8))
image.CopyInformation(series_reference_image(rtstruct.series_data))

sitk.WriteImage(image, "liver.nii.gz")
```

{func}`~rt_utils.nifti.series_reference_image` is the same geometry the
converter resamples onto, so the result lines up with the images.
