# Reading structure sets

## Loading

{meth}`RTStructBuilder.create_from <rt_utils.rtstruct_builder.RTStructBuilder.create_from>`
needs both the structure set and the image series it was drawn on:

```{code-block} python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_from(
    dicom_series_path="./series",
    rt_struct_path="./series/structures.dcm",
)
```

The images are not optional. Contours name their slices by identifier, and
every coordinate is interpreted through the series geometry.

The loaded structure set is also writable. `add_roi` and `delete_roi` work on
it, so this is how you add to an existing set.

### Validation

`create_from` checks that the file really is an RTStruct and that every image
it references is present in the series. A structure set that references images
you did not supply raises by default. To downgrade that to a warning:

```{code-block} python
rtstruct = RTStructBuilder.create_from(
    dicom_series_path="./series",
    rt_struct_path="./structures.dcm",
    warn_only=True,
)
```

Use `warn_only` when a set legitimately spans more than the series you are
working with, but note the limits in {doc}`troubleshooting`.

## Listing structures

```{code-block} python
rtstruct.get_roi_names()
# ['BODY', 'GTV', 'PTV', 'Cord', 'Marker-1']
```

Filter by `ContourGeometricType`:

```{code-block} python
rtstruct.get_roi_names(geometry="POINT")           # fiducials, seeds
rtstruct.get_roi_names(geometry="OPEN_PLANAR")     # catheters, centrelines
rtstruct.get_roi_names(geometry="CLOSED_PLANAR")   # ordinary structures
```

An ROI matches if **any** of its contours has that type, since a single ROI
can mix types across slices.

## Getting a mask

```{code-block} python
mask = rtstruct.get_roi_mask_by_name("GTV")
mask.shape      # (Rows, Columns, Slices)
mask.dtype      # bool
```

### Names that differ in case

Matching is exact by default. Planning systems disagree about capitalisation,
so:

```{code-block} python
mask = rtstruct.get_roi_mask_by_name("liver", case_sensitive=False)
```

Exact is the default deliberately: a structure set may contain both `Liver`
and `liver`, and those are *different structures*. With `case_sensitive=False`
the first in `StructureSetROISequence` wins and the other becomes unreachable.

### Identifiers that no longer match

```{code-block} python
mask = rtstruct.get_roi_mask_by_name("GTV", match_by="position")
```

For anonymised images whose `SOPInstanceUID`s were regenerated after the
structures were drawn. Read the caveats in
{doc}`../concepts/slice-matching` before using it.

## Working with the series

`rtstruct.series_data` is the sorted list of slice datasets, in the same order
axis 2 of every mask is in:

```{code-block} python
series = rtstruct.series_data

print(len(series))                            # number of slices
print(series[0].Rows, series[0].Columns)      # in-plane size
print(series[0].PixelSpacing)                 # [row spacing, column spacing]
print(series[0].ImagePositionPatient)         # first slice origin
```

## Measuring a structure

```{code-block} python
import numpy as np

mask = rtstruct.get_roi_mask_by_name("GTV")
reference = rtstruct.series_data[0]

row_mm, col_mm = (float(v) for v in reference.PixelSpacing)
slice_mm = abs(
    float(rtstruct.series_data[1].ImagePositionPatient[2])
    - float(rtstruct.series_data[0].ImagePositionPatient[2])
)

volume_mm3 = mask.sum() * row_mm * col_mm * slice_mm
print(f"{volume_mm3 / 1000:.2f} cm³")
```

:::{note}
This assumes even slice spacing. On an unevenly spaced series, sum each
slice's own thickness rather than multiplying by a single value.
:::

## Overlaying on the images

```{code-block} python
import matplotlib.pyplot as plt

k = mask.sum(axis=(0, 1)).argmax()

fig, ax = plt.subplots(figsize=(6, 6))
ax.imshow(rtstruct.series_data[k].pixel_array, cmap="gray")
ax.contour(mask[:, :, k], levels=[0.5], colors="magenta", linewidths=1)
ax.set_axis_off()
plt.show()
```

No transpose, no flip. If one appears to be needed, something upstream is
wrong; see {doc}`troubleshooting`.

## Exporting every structure

```{code-block} python
import numpy as np

masks = {
    name: rtstruct.get_roi_mask_by_name(name)
    for name in rtstruct.get_roi_names()
}

np.savez_compressed("masks.npz", **masks)
```

A label map, where each structure gets an integer, loses overlaps, and
structures in radiotherapy overlap constantly, a PTV inside a BODY. Keep
them separate unless you know they are disjoint.
