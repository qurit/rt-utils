# Quickstart

Three things, each complete on its own: write a structure set, read one back,
and check the result.

## 1. Write an ROI into a new structure set

```{code-block} python
:emphasize-lines: 8

from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")

# mask is a 3D boolean array shaped (Rows, Columns, Slices); see below
rtstruct.add_roi(mask=mask, name="GTV", color=[255, 0, 255])

rtstruct.save("structures")       # writes structures.dcm
```

`create_new` reads the image series, sorts it by position, and builds an empty
structure set that references those images. `add_roi` traces the contours of
each slice of the mask and writes them in patient coordinates.

:::{important}
The mask is indexed `(Rows, Columns, Slices)`, the same layout
`pydicom`'s `pixel_array` is read in. A mask segmented from the series already
has the right shape; a mask from a NIfTI file or another tool probably does
not. {doc}`concepts/mask-layout` explains what goes wrong and how to convert.
:::

## 2. Read an existing ROI back as a mask

```{code-block} python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_from(
    dicom_series_path="./series",
    rt_struct_path="./series/structures.dcm",
)

print(rtstruct.get_roi_names())
# ['GTV', 'Liver', 'Cord']

mask = rtstruct.get_roi_mask_by_name("GTV")
print(mask.shape, mask.dtype, mask.sum())
# (512, 512, 160) bool 8423
```

Reading needs the image series as well as the structure set: the contours name
the slices they were drawn on, and all the geometry comes from the images.

## 3. Look at it

```{code-block} python
import matplotlib.pyplot as plt

slice_index = mask.sum(axis=(0, 1)).argmax()   # the busiest slice

plt.imshow(rtstruct.series_data[slice_index].pixel_array, cmap="gray")
plt.contour(mask[:, :, slice_index], colors="magenta", linewidths=0.8)
plt.show()
```

Because the mask and `pixel_array` share their in-plane layout, the two
overlay directly with no transposing. If the contour lands somewhere
unexpected, that is the first thing to check. See
{doc}`guide/troubleshooting`.

## A complete round trip

```{code-block} python
:caption: Segment, write, read back, measure

import numpy as np
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")

# A crude "segmentation": everything above a threshold.
series = rtstruct.series_data
volume = np.stack([s.pixel_array for s in series], axis=-1)
mask = volume > 400

rtstruct.add_roi(mask=mask, name="Bone", roi_interpreted_type="ORGAN")
rtstruct.save("structures")

# ... later, in another process
loaded = RTStructBuilder.create_from("./series", "structures.dcm")
again = loaded.get_roi_mask_by_name("Bone")

print(f"{mask.sum()} voxels written, {again.sum()} read back")
```

The two counts will be close but not always identical: a mask becomes polygons
and polygons become a mask again, and a one-voxel-wide spur has no interior to
rasterise. {doc}`concepts/contour-placement` describes what round trips exactly
and what does not.

## Where to go next

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} Mask layout
:link: concepts/mask-layout
:link-type: doc
The axis order, and converting masks from elsewhere.
:::

:::{grid-item-card} Creating structure sets
:link: guide/creating
:link-type: doc
Every option on `add_roi`, and what each one is for.
:::

:::{grid-item-card} From NIfTI
:link: guide/nifti
:link-type: doc
Converting a `.nii.gz` segmentation correctly.
:::

:::{grid-item-card} Troubleshooting
:link: guide/troubleshooting
:link-type: doc
Rotated, flipped, offset, empty or doubled ROIs.
:::

::::
