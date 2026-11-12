# How contours find their slice

A contour is a flat polygon in patient coordinates. To rasterise it into a
mask, RT-Utils has to decide **which slice it belongs to** and then project it
onto that slice's grid. Both steps have a failure mode worth understanding.

## Matching: identifier or position

Every contour names the image it was drawn on, in
`ContourImageSequence.ReferencedSOPInstanceUID`. That is what DICOM intends,
it is unambiguous, and it is the default:

```{code-block} python
mask = rtstruct.get_roi_mask_by_name("GTV")                      # by identifier
mask = rtstruct.get_roi_mask_by_name("GTV", match_by="position") # by geometry
```

`match_by="position"` instead assigns each contour to the slice nearest its
own position along the slice normal.

Use it when the identifiers no longer line up although the geometry is
unchanged. The usual cause is anonymisation: many tools regenerate
`SOPInstanceUID`s on the images, which breaks the link to structures that were
drawn before.

:::{warning}
Position matching is not the default because it always succeeds. It will
happily attach contours to a series they were never drawn on, as long as the
positions are close — two scans of the same patient at the same couch
positions, for instance. Matching by identifier raises in that case instead.

Do not reach for it to work around a structure set that spans several series,
either: overlapping series will attract each other's contours.
:::

If nothing matches at all, RT-Utils raises rather than returning an empty
mask:

```{code-block} text
None of this ROI's 42 contour(s) could be matched to a slice of the input
series, so the mask would be empty. ...
```

Before 2.3.0 this returned an array of zeros, indistinguishable from a
structure that is genuinely absent.

## Projection: each slice uses its own origin

Once a contour is assigned to a slice, it is projected with a transformation
built from **that slice's own `ImagePositionPatient`**.

That matters on an unevenly spaced series. Older versions derived every
position from the first slice plus `index × average_spacing`, so any series
whose increment was not constant wrote contours to positions no slice
occupies:

```{list-table}
:header-rows: 1
:widths: 25 25 25 25

* - Slice
  - True position
  - Written as (pre-2.3.0)
  - 
* - 0
  - z = 0
  - z = 0
  - ✓
* - 1
  - z = 2
  - z = 6.67
  - ✗
* - 2
  - z = 4
  - z = 13.3
  - ✗
* - 3
  - z = 20
  - z = 20
  - ✓
```

The first and last slices always land correctly, which is what made this easy
to miss when spot-checking in a viewer. Uneven spacing arises from a scout
image left in the folder, a varying increment, or a partly culled series.

## Slice ordering and duplicates

`RTStruct.series_data` is the series sorted by projection onto the slice
normal, ascending. Sorting along the normal rather than along *z* is what
makes non-axial series work.

Two integrity checks run while the series is loaded:

**Repeated instances are collapsed.**
: A directory tree is walked in full, so a series that also exists in a backup
  folder or a nested export is read more than once. Copies sharing a
  `SOPInstanceUID` are reduced to one. Previously the stack came out a whole
  multiple too long and every mask was then rejected for having the wrong
  number of layers.

**Distinct images sharing a position raise.**
: Two different acquisitions at the same couch position are not a stack. They
  used to be sorted into one axis, interleaving two volumes.

**Files without `ImageOrientationPatient` are skipped.**
: Secondary captures, screenshots and reports are in the folder but are not
  part of the geometry.

## Which files count as images

Whether a file is an image is decided by the **presence** of a pixel data
element — `PixelData`, `FloatPixelData` or `DoubleFloatPixelData` — not by
decoding it.

Nothing in RT-Utils reads pixel values, so a compressed transfer syntax with
no handler installed is no obstacle. Before 2.3.0 the pixels were decoded to
make this decision, so an undecodable series disappeared behind
`No DICOM Images found in input path`.

For files written without the standard preamble or file meta, pass `force`:

```{code-block} python
rtstruct = RTStructBuilder.create_new(dicom_series_path="./series", force=True)
```
