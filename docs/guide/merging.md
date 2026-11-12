# Merging structure sets

Two structure sets for one image series — one for organs at risk, one for
targets — can be combined into a single file:

```{code-block} python
from rt_utils import RTStructMerger

merged = RTStructMerger.merge_rtstructs(
    dicom_series_path="./series",
    rt_struct_path1="./organs.dcm",
    rt_struct_path2="./targets.dcm",
)

merged.save("merged")
```

The structures of the first set are appended to the second, and the second is
returned. The files on disk are untouched.

## Requirements

Both sets must belong to the **same image series**. The merged file keeps one
frame of reference, and contours still name their images by
`ReferencedSOPInstanceUID`; structures drawn on a different series would
reference images the merged set does not describe.

## Renumbering and renaming

Two things are fixed up as structures are moved across:

**`ROINumber`.**
: Each incoming ROI is renumbered to one above the highest already in use in
  the destination — not to `len(sequence) + 1`, which collides wherever the
  destination has a gap. `ROINumber` is what joins the three sequences, so a
  collision would silently give two ROIs the same contours.

**`ROIName`.**
: Two sets for one series routinely name the same organ the same way. A name
  already taken gets a counting suffix — `Liver`, then `Liver_2`, then
  `Liver_3` — so merging a third set does not produce a second `Liver_2`.

:::{note}
Both of these were broken before 2.4.0. The rename path did
`struct_set_roi_seq += "_2"`, which adds a string to a `Dataset` rather than
to its `ROIName`, so merging two sets that shared any name raised
`TypeError`. That path had never run successfully.
:::

## Merging more than two

```{code-block} python
from rt_utils import RTStructBuilder, RTStructMerger

merged = RTStructMerger.merge_rtstructs("./series", "organs.dcm", "targets.dcm")
merged.save("tmp-merged")

merged = RTStructMerger.merge_rtstructs("./series", "tmp-merged.dcm", "nodes.dcm")
merged.save("all-structures")
```

Merging is not associative in naming — the order decides which copy keeps the
plain name and which gets the suffix.

## Copying individual structures

To take just a few structures rather than all of them, read and re-add:

```{code-block} python
source = RTStructBuilder.create_from("./series", "organs.dcm")
target = RTStructBuilder.create_from("./series", "targets.dcm")

for name in ["Cord", "Bladder"]:
    target.add_roi(
        mask=source.get_roi_mask_by_name(name),
        name=name,
        roi_interpreted_type="ORGAN",
    )

target.save("targets-plus-organs")
```

This round trips each structure through a mask, so it quantises to the voxel
grid — see {doc}`../concepts/contour-placement`. `merge_rtstructs` moves the
contour data itself and does not.
