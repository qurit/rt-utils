# Creating structure sets

## Starting from a series

{meth}`RTStructBuilder.create_new <rt_utils.rtstruct_builder.RTStructBuilder.create_new>`
builds an empty structure set that references an image series:

```{code-block} python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")
```

The series can be a directory path, an `os.PathLike`, or a list of datasets
already read with pydicom (see {doc}`in-memory`). Either way it is sorted by
slice position, so the two forms are interchangeable.

To add to a structure set that already exists, use
{meth}`~rt_utils.rtstruct_builder.RTStructBuilder.create_from` instead; see
{doc}`reading`.

### Non-conformant files

`force=True` is passed through to pydicom, allowing files without the standard
preamble or file meta to be read. Equipment and anonymisation tools produce
these routinely:

```{code-block} python
rtstruct = RTStructBuilder.create_new(dicom_series_path="./series", force=True)
```

## Adding an ROI

```{code-block} python
rtstruct.add_roi(
    mask=mask,                      # (Rows, Columns, Slices), dtype=bool
    name="GTV",
    color=[255, 0, 255],
    description="Gross tumour volume, auto-segmented",
    roi_interpreted_type="GTV",
)
```

Only `mask` is required. Everything else has a default.

:::{important}
The mask layout is not negotiable and is not checked for orientation. Read
{doc}`../concepts/mask-layout` first if the mask came from anywhere other than
segmenting this series.
:::

## Options

### `color`

An RGB list or a hex string. `'#f0f'`, `'#ff00ff'` and `[255, 0, 255]` are the
same colour.

If omitted, a colour is taken from the built-in palette by ROI number, so
successive ROIs are visually distinct without you choosing anything.

### `name`

Defaults to `ROI-{number}`. Names are not checked for uniqueness. Two ROIs
may share a name, and they then become difficult to tell apart in a viewer and
ambiguous to {meth}`~rt_utils.rtstruct.RTStruct.get_roi_mask_by_name`, which
returns the first match.

### `description`

Free text, written to `ROIDescription`. Empty by default.

### `roi_interpreted_type`

Sets `RTROIInterpretedType`, which says what kind of structure this is, so a
planning system can tell a target from an organ at risk:

```{code-block} python
rtstruct.add_roi(mask=ptv,    name="PTV",    roi_interpreted_type="PTV")
rtstruct.add_roi(mask=rectum, name="Rectum", roi_interpreted_type="ORGAN")
rtstruct.add_roi(mask=body,   name="BODY",   roi_interpreted_type="EXTERNAL")
```

PS3.3 C.8.8.8 gives these as *Defined Terms*, meaning the list is extensible,
so the value is not validated. {data}`rt_utils.utils.ROI_INTERPRETED_TYPES`
holds the standard ones for reference.

Defaults to `""` (unstated), which is what every version before 2.4.0 wrote,
leaving every structure to be reclassified by hand after import.

### `contour_mode`

`"voxel_edge"` (default) or `"voxel_center"`. See
{doc}`../concepts/contour-placement`.

### `use_pin_hole`

Cuts a channel from each hole out to the outer boundary, so a structure with
holes becomes a single non-nested contour. For viewers that cannot draw nested
contours. See {doc}`../concepts/contour-placement`.

### `approximate_contours`

Default `True`. Simplifies traced contours, which keeps the file small. Set to
`False` for maximum fidelity at the cost of considerably more contour data.

Applies only to `contour_mode="voxel_center"`.

### `roi_generation_algorithm`

`0` = `AUTOMATIC` (default), `1` = `SEMIAUTOMATIC`, `2` = `MANUAL`. A string
outside those three is accepted but logs a warning, since not every viewer
understands one.

### `apply_smoothing`

`"2d"` or `"3d"`. Smooths the mask before tracing, giving a boundary finer
than the voxel grid. See {doc}`smoothing`.

## ROI numbering

`ROINumber` is the key joining the three sequences that make up a structure
set, so RT-Utils never reuses one. A new ROI takes `max(existing) + 1`, not
`len(sequence) + 1`. Those differ as soon as anything has been deleted, and a
collision would silently give two ROIs the same contours.

Gaps left by {meth}`~rt_utils.rtstruct.RTStruct.delete_roi` are therefore
never filled. That is deliberate: renumbering survivors would re-point every
reference.

## Metadata

```{code-block} python
rtstruct.set_series_description("Auto-segmentation v3")
```

Patient, study and frame-of-reference information is copied from the image
series when the structure set is created.

## Saving

```{code-block} python
rtstruct.save("structures")        # .dcm is appended if absent
rtstruct.save("out/structures.dcm")
```

To get the bytes without touching the filesystem, see {doc}`in-memory`.

## Full example

```{code-block} python
:caption: Several structures in one set

import numpy as np
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")

for name, mask, kind, color in [
    ("BODY",   body_mask,   "EXTERNAL", [255, 255, 255]),
    ("GTV",    gtv_mask,    "GTV",      [255, 0, 0]),
    ("PTV",    ptv_mask,    "PTV",      [255, 128, 0]),
    ("Cord",   cord_mask,   "ORGAN",    [0, 200, 255]),
]:
    if not mask.any():
        continue                       # an absent structure is not an error
    rtstruct.add_roi(
        mask=mask,
        name=name,
        color=color,
        roi_interpreted_type=kind,
    )

rtstruct.set_series_description("Auto-segmentation")
rtstruct.save("structures")
```
