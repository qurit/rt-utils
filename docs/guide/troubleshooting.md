# Troubleshooting

Most problems with RTStructs are silent: the file is valid, it opens in a
viewer, and it describes the wrong anatomy. This page is organised by what you
see.

:::{tip}
Before anything else, check your version. Eight distinct silent wrong-data
bugs were fixed between 2.1.1 and 2.4.0.

```{code-block} python
import rt_utils; print(rt_utils.__version__)
```
:::

## The ROI is rotated, flipped or transposed

**Almost always a mask that was not in `(Rows, Columns, Slices)` order.**

Masks are indexed the way `pixel_array` is read. A mask from a NIfTI file, or
from a tool with its own conventions, probably is not. See
{doc}`../concepts/mask-layout`.

For NIfTI, use {func}`~rt_utils.nifti.nifti_to_mask` — not a transpose. The
correct rearrangement differs from file to file.

Check it before writing anything:

```{code-block} python
k = mask.sum(axis=(0, 1)).argmax()
plt.imshow(rtstruct.series_data[k].pixel_array, cmap="gray")
plt.contour(mask[:, :, k], colors="magenta")
```

If that overlay is wrong, the structure set will be wrong in exactly the same
way.

## The ROI is on the wrong slices

**The mask's axis 2 was not in the series' spatial order.**

`series_data` is sorted by position along the slice normal. That is not the
order of a directory listing, and not `InstanceNumber` order — which descends
in plenty of real acquisitions. Build the volume from `series_data`:

```{code-block} python
volume = np.stack([s.pixel_array for s in rtstruct.series_data], axis=-1)
```

**Or the whole structure is offset by a constant number of slices.**

That is the signature of a reversed slice axis: an ROI at slice `k` appearing
at `N - 1 - k`, so the offset changes with series length. Try
`mask[:, :, ::-1]`, and check with the overlay above.

## The ROI comes back empty

`get_roi_mask_by_name` returns all zeros, or raises:

```{code-block} text
None of this ROI's N contour(s) could be matched to a slice of the input series
```

**The series is not the one the structures were drawn on.** Each contour names
its image by `ReferencedSOPInstanceUID`, and none of those images is in the
series you supplied.

**Or the images were re-written after the structures were made.**
Anonymisation tools regenerate `SOPInstanceUID`s, which breaks the link while
leaving the geometry intact. For that case:

```{code-block} python
mask = rtstruct.get_roi_mask_by_name("GTV", match_by="position")
```

Read the caveats in {doc}`../concepts/slice-matching` first — position
matching always succeeds, including when it should not.

:::{note}
Before 2.3.0 this returned an array of zeros with no error, indistinguishable
from a structure genuinely absent from the patient.
:::

## An open contour comes back as a solid blob

**Fixed in 2.3.0.** `ContourGeometricType` was ignored on read, so an
`OPEN_PLANAR` path — a brachytherapy channel, a catheter, a vessel centreline
— had the entire area between its two ends filled in. A C-shaped channel of 65
voxels came back as a solid 579.

Upgrade. Closed contours were never affected, which is why organ structures
always looked right.

## `Mask must have the same number of layers as the input series`

The mask's slice count does not match the series.

**If the number is a whole multiple of the real one** — twice, three times —
the directory contains copies of the series, in a backup folder or a nested
export. Fixed in 2.3.0, where copies sharing a `SOPInstanceUID` are collapsed.

**Otherwise** the directory holds more than one series, or files that are not
part of the stack. Point RT-Utils at a directory containing exactly the one
series.

## `Two images share slice position`

Two *different* images at the same couch position: two acquisitions, two echoes,
or two series mixed in one folder. They are not a stack, and stacking them
would interleave two volumes. Separate them first.

## `No DICOM Images found in input path`

**The path holds no images** — or none RT-Utils recognises as such.

Files without `ImageOrientationPatient` are skipped: secondary captures,
screenshots, dose reports, structure sets. Those carry no geometry to contour
against.

For files written without the standard preamble or file meta:

```{code-block} python
RTStructBuilder.create_new(dicom_series_path="./series", force=True)
```

:::{note}
Before 2.3.0, whether a file was an image was decided by *decoding* its
pixels, so a compressed transfer syntax with no handler installed made a
perfectly good series vanish behind this message. Nothing in RT-Utils reads
pixel values; presence of the element is now enough.
:::

## `Mask must have the same in-plane dimensions as the input series`

The mask is sized for a different series, or is transposed on a non-square
one. The expected shape is `(Rows, Columns)` — the `pixel_array` layout.

:::{warning}
On a **square** series this check cannot catch a transpose: `512 × 512`
transposed is still `512 × 512`. It guards against the wrong series, not the
wrong orientation.
:::

## The structure is slightly too small everywhere

**Half a voxel on every side**, which is a large fraction of a small
structure: a 3 × 3 voxel region exports at about 44 % of its true area.

That was the default before 2.0.0. Upgrade, or pass the current default
explicitly:

```{code-block} python
rtstruct.add_roi(mask=mask, name="seed", contour_mode="voxel_edge")
```

See {doc}`../concepts/contour-placement`.

## A single voxel comes back as four, or five

**As four:** a contour tracing voxel boundaries, rasterised with an inclusive
fill. Fixed in 2.0.0 — contours are now sampled at voxel centres.

**As five:** a point contour drawn as a radius-1 circle. Fixed in 1.4.0; a
`POINT` now sets exactly the voxel it names.

## Contours are at positions no slice occupies

**Fixed in 2.3.0.** Coordinates came from the first slice's position plus
`index × average_spacing`. On an unevenly spaced series — a scout image in the
folder, a varying increment, a partly culled stack — every slice between the
first and the last was written somewhere no slice is. A stack at z = 0, 2, 4,
20 put the z = 2 contour at z = 6.67.

The first and last slices always land correctly, which is what makes this easy
to miss in a viewer.

## Merging raises `TypeError`, or structures share a number

**Fixed in 2.4.0.** The duplicate-name path in `RTStructMerger` had never run
successfully, so merging two sets that both contained a `Liver` — the ordinary
case — raised. Numbering also collided wherever the destination had a gap.

## Nothing is printed any more

**Changed in 2.4.0, deliberately.** Diagnostics go to module loggers now, not
to stdout. To see them:

```{code-block} python
import logging
logging.basicConfig(level=logging.INFO)
```

Or just the library:

```{code-block} python
logging.getLogger("rt_utils").setLevel(logging.INFO)
```

## A viewer will not draw holes

Use `use_pin_hole=True` when writing. See
{doc}`../concepts/contour-placement`.

## Known limits

**A structure set spanning several series.**
: `series_data` is one stack and `get_roi_mask_by_name` returns one array, so
  only the part of a structure set belonging to the series you supplied can
  be read. Load the structure set once per series:

  ```{code-block} python
  for series_path in series_paths:
      rtstruct = RTStructBuilder.create_from(
          series_path, "structures.dcm", warn_only=True
      )
      for name in rtstruct.get_roi_names():
          try:
              masks[(series_path, name)] = rtstruct.get_roi_mask_by_name(name)
          except Exception:
              pass        # this ROI was not drawn on this series
  ```

  Do **not** reach for `match_by="position"` here. Overlapping series would
  attract each other's contours.

**A volume stored in a single file.**
: Some SPECT and enhanced multi-frame objects hold the whole volume in one
  file. RT-Utils assumes one file per slice.

**Contours outside the imaged volume.**
: A couch, an applicator or a bolus contoured beyond the image extent has
  nowhere to rasterise to.

**Copying structures between sets for *different* series.**
: Geometry drawn on one series has to be resampled onto another, which
  RT-Utils does not do.

## Still stuck

Open an issue at [github.com/qurit/rt-utils/issues](https://github.com/qurit/rt-utils/issues).
What makes a report actionable:

- `rt_utils.__version__`, `pydicom.__version__` and your Python version;
- the series' `Rows`, `Columns`, `PixelSpacing`, `ImageOrientationPatient`
  and the number of slices;
- whether the series is square, and whether the slice spacing is even;
- a short script that reproduces it, ideally with a synthetic series rather
  than patient data.
