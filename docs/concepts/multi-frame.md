# Series held in a single file

Most image series store one slice per file, and RT-Utils works on a list of
such files. Some modalities do not. A reconstructed **SPECT** study is a single
NM instance whose `NumberOfFrames` is the whole volume, and **Enhanced CT, MR
and PET** put a volume in one file too.

RT-Utils splits such a file into one slice per frame when it loads the series,
so everything downstream behaves exactly as it does for a folder of slices:

```{code-block} python
from rt_utils import RTStructBuilder

# A folder holding the single NM file, or the file itself.
rtstruct = RTStructBuilder.create_new(dicom_series_path="./spect/NM_1000")

len(rtstruct.series_data)  # 128, one entry per slice, not 1 per file
```

A mask still has shape `(Rows, Columns, Slices)` with one layer per frame, and
`add_roi` and `get_roi_mask_by_name` round trip as usual.

:::{note}
Before 2.5.0 a multi-frame file was skipped entirely: it has no
`ImageOrientationPatient` at the top level, so it did not look like an image
series, and loading failed with `No DICOM Images found in input path`.
:::

## Where the geometry comes from

A single-frame image states its position in `ImagePositionPatient`. A
multi-frame image states it in one of three other places, and RT-Utils reads
whichever is present:

```{list-table}
:header-rows: 1
:widths: 30 70

* - Layout
  - Geometry
* - Enhanced CT / MR / PET
  - `PerFrameFunctionalGroupsSequence`, one item per frame, with
    `PlanePositionSequence`, `PlaneOrientationSequence` and
    `PixelMeasuresSequence`. Values common to every frame may instead be
    stated once in `SharedFunctionalGroupsSequence`.
* - NM (SPECT)
  - `DetectorInformationSequence`, which holds one `ImagePositionPatient` and
    `ImageOrientationPatient` for the whole stack (PS3.3 C.8.4.8). Frames are
    spaced along the slice normal by `SpacingBetweenSlices`, in the order
    `SliceVector` gives.
* - Plain multi-frame
  - `ImagePositionPatient` and `ImageOrientationPatient` at the top level,
    with the frames stacked along the slice normal.
```

Because an Enhanced image positions every frame individually, an unevenly
spaced stack keeps its real spacing. For NM there is only one stated position,
so the slices are taken to be evenly spaced, which is what a reconstruction
produces.

:::{tip}
The NM stack runs from the stated position **along the slice normal**, the
cross product of the row and column directions, stepping by
`SpacingBetweenSlices`. A vendor that writes that spacing negative gets a
stack running the other way, as intended.

This was checked against a whole-body reconstruction of 228 slices at
4.795 mm, which stacks to 838.8 mm to 1927.3 mm where the CT acquired with it
spans 831.5 mm to 1926.5 mm, and against the anatomy the two have in common.

An NM file still states its direction once, where a CT states a position per
slice, so it costs little to confirm it the first time you use a new scanner
or export path:

```{code-block} python
first, last = rtstruct.series_data[0], rtstruct.series_data[-1]
print(first.ImagePositionPatient, last.ImagePositionPatient)
```
:::

## How contours reference a frame

Every frame of a file shares one `SOPInstanceUID`: the identifier belongs to
the instance, not to the frame. A contour therefore names its slice with
`ReferencedSOPInstanceUID` **and** `ReferencedFrameNumber`, counted from one
(PS3.3 C.8.8.6):

```{code-block} text
(3006,0016) Contour Image Sequence
  (0008,1150) Referenced SOP Class UID    1.2.840.10008.5.1.4.1.1.20
  (0008,1155) Referenced SOP Instance UID 1.3.12.2.1107.5.6...
  (0008,1160) Referenced Frame Number     42
```

Reading works the same way round. A structure set that names no frame, because
it was written by a tool that does not reference them, is taken to apply to
the image as a whole rather than being discarded.

## Frames that are not slices

Frames are not necessarily stacked in space. A tomographic NM **acquisition**
is stored as its projections: one frame per gantry angle, per detector head
and per energy window. The same file format holds both, and `ImageType` is
what tells them apart:

```{list-table}
:header-rows: 1
:widths: 35 65

* - `ImageType` contains
  - What the frames are
* - `RECON TOMO`
  - Slices of the reconstructed volume. This is what you contour.
* - `TOMO`
  - Projections, one per angle. Nothing can be contoured on them.
```

RT-Utils refuses the second case rather than laying the projections out as
though they were slices, which would produce a structure set that looks valid
and places every contour where the image never was:

```{code-block} text
NM image 1.3.12.2.1107.5.6... holds projection data, not a reconstructed
volume: Image Type is ['ORIGINAL', 'PRIMARY', 'TOMO', 'EMISSION'] and its 576
frames span 48 gantry angle(s), 2 detector(s) and 6 energy window(s). ...
```

A gated or multi-energy-window file is refused for the same reason: its frames
hold more than one volume, so there is no single stack to contour. Export the
one volume you want first.

## Pixels

Each slice reads its own plane from the parent file:

```{code-block} python
rtstruct.series_data[42].pixel_array   # one frame, shape (Rows, Columns)
```

The file is decoded once and cached, so iterating the series does not decode
the volume repeatedly. The slices are views onto the file they came from:
treat them as read-only rather than as datasets to edit and save.
