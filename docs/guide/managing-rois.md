# Editing a structure set

A structure set loaded with
{meth}`~rt_utils.rtstruct_builder.RTStructBuilder.create_from` is fully
writable: add structures, remove them, rename the series, save it back.

## Adding to an existing set

```{code-block} python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_from(
    dicom_series_path="./series",
    rt_struct_path="./structures.dcm",
)

rtstruct.add_roi(mask=new_mask, name="GTV-auto", roi_interpreted_type="GTV")
rtstruct.save("structures-v2")
```

Saving under a new name keeps the original. `save` overwrites without asking.

## Removing a structure

```{code-block} python
rtstruct.delete_roi("GTV-auto")
rtstruct.delete_roi("liver", case_sensitive=False)
```

An ROI lives in three sequences joined by `ROINumber`:
`StructureSetROISequence` names it, `ROIContourSequence` holds its geometry,
and `RTROIObservationsSequence` its interpretation.
{meth}`~rt_utils.rtstruct.RTStruct.delete_roi` removes all three. Leaving any
behind produces a structure set viewers read inconsistently: contours
belonging to an ROI with no name, or a name with nothing to draw.

A name that does not exist raises `RTStruct.ROIException`.

:::{note}
Numbering is deliberately left with a gap. `ROINumber` is the key those
sequences are joined by, so renumbering the survivors to close it would
silently re-point every reference. A later `add_roi` takes the next number
above the highest still in use, so the gap is never reused.
:::

## Replacing a structure

There is no `replace`; delete and add:

```{code-block} python
mask = rtstruct.get_roi_mask_by_name("GTV")
edited = some_edit(mask)

rtstruct.delete_roi("GTV")
rtstruct.add_roi(mask=edited, name="GTV", roi_interpreted_type="GTV")
```

The new ROI gets a new number and goes to the end of the sequences. Its
colour is re-picked from the palette unless you pass `color`, so pass the
original if the colour matters:

```{code-block} python
def roi_color(rtstruct, name):
    number = next(
        str(roi.ROINumber)
        for roi in rtstruct.ds.StructureSetROISequence
        if roi.ROIName == name
    )
    return [
        int(c) for roi in rtstruct.ds.ROIContourSequence
        if str(roi.ReferencedROINumber) == number
        for c in roi.ROIDisplayColor
    ]

color = roi_color(rtstruct, "GTV")
rtstruct.delete_roi("GTV")
rtstruct.add_roi(mask=edited, name="GTV", color=color)
```

## Renaming

RT-Utils has no rename method. Edit the dataset directly, since `ROIName` is in
`StructureSetROISequence`:

```{code-block} python
for structure_roi in rtstruct.ds.StructureSetROISequence:
    if structure_roi.ROIName == "ROI-1":
        structure_roi.ROIName = "Bladder"

rtstruct.save("structures")
```

Nothing references an ROI by name, so this is safe. Do **not** edit
`ROINumber` the same way.

## Series description

```{code-block} python
rtstruct.set_series_description("Auto-segmentation v3")
```

## Reaching the raw dataset

`rtstruct.ds` is the pydicom `FileDataset`. Anything RT-Utils does not expose
can be done there:

```{code-block} python
rtstruct.ds.StructureSetLabel = "AutoContours"
rtstruct.ds.StructureSetName = "nnU-Net v2"
rtstruct.ds.StructureSetDate = "20251112"

rtstruct.ds.save_as("structures.dcm")
```

:::{warning}
`ROINumber` and `ReferencedROINumber` tie the three sequences together, and
`ReferencedSOPInstanceUID` ties each contour to its image. Editing any of
those by hand will produce a file that still parses and no longer means what
it says.
:::

## Checking the result

```{code-block} python
for structure_roi in rtstruct.ds.StructureSetROISequence:
    print(structure_roi.ROINumber, structure_roi.ROIName)

for observation in rtstruct.ds.RTROIObservationsSequence:
    print(observation.ReferencedROINumber, observation.RTROIInterpretedType)
```

Reading each structure back as a mask is the stronger check, since it
exercises the contours themselves:

```{code-block} python
for name in rtstruct.get_roi_names():
    mask = rtstruct.get_roi_mask_by_name(name)
    print(f"{name:20s} {mask.sum():>8d} voxels")
```
