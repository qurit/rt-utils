# Mask layout

Every mask RT-Utils accepts or returns is a 3D boolean array indexed
`mask[row, column, slice]`.

```{list-table}
:header-rows: 1
:widths: 12 20 68

* - Axis
  - Index
  - Runs
* - `0`
  - row
  - down a column, along `ImageOrientationPatient[3:6]`
* - `1`
  - column
  - along a row, along `ImageOrientationPatient[0:3]`
* - `2`
  - slice
  - through the series in **ascending slice position**
```

```{raw} html
<div class="rtu-figure">
<svg viewBox="0 0 760 340" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="A mask is indexed by row, column and slice. Axis 0 runs down a column, axis 1 along a row, axis 2 through the stack in ascending slice position.">
  <defs>
    <marker id="rtu-arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>
    </marker>
  </defs>

  <g stroke="currentColor" fill="none" opacity="0.28" stroke-width="1">
    <path d="M70 80 h220 M70 124 h220 M70 168 h220 M70 212 h220 M70 256 h220 M70 300 h220"/>
    <path d="M70 80 v220 M114 80 v220 M158 80 v220 M202 80 v220 M246 80 v220 M290 80 v220"/>
  </g>
  <rect x="158" y="124" width="44" height="44" fill="#5b35c7" opacity="0.5"/>
  <text x="180" y="152" text-anchor="middle" font-size="12" fill="#ffffff"
        font-family="system-ui, sans-serif">1</text>

  <g color="currentColor" stroke="currentColor" fill="none" stroke-width="1.8">
    <line x1="70" y1="60" x2="290" y2="60" marker-end="url(#rtu-arrow)"/>
    <line x1="50" y1="80" x2="50" y2="300" marker-end="url(#rtu-arrow)"/>
  </g>
  <text x="180" y="48" text-anchor="middle" font-size="13" fill="currentColor"
        font-family="system-ui, sans-serif" font-weight="600">axis 1 · column</text>
  <text x="300" y="64" font-size="11" fill="currentColor" opacity="0.7"
        font-family="system-ui, sans-serif">IOP[0:3]</text>
  <text x="34" y="190" text-anchor="middle" font-size="13" fill="currentColor"
        font-family="system-ui, sans-serif" font-weight="600"
        transform="rotate(-90 34 190)">axis 0 · row</text>
  <text x="56" y="318" font-size="11" fill="currentColor" opacity="0.7"
        font-family="system-ui, sans-serif">IOP[3:6]</text>
  <text x="180" y="186" text-anchor="middle" font-size="11" fill="currentColor"
        opacity="0.75" font-family="system-ui, sans-serif">mask[1, 2, k]</text>

  <g stroke="currentColor" fill="none" opacity="0.2">
    <path d="M460 268 l120 -46 l120 46 l-120 46 z"/>
  </g>
  <g opacity="0.85">
    <path d="M460 268 l120 -46 l120 46 l-120 46 z" fill="#5b35c7" opacity="0.18"
          stroke="currentColor" stroke-width="1.2"/>
    <path d="M460 208 l120 -46 l120 46 l-120 46 z" fill="#2563eb" opacity="0.18"
          stroke="currentColor" stroke-width="1.2"/>
    <path d="M460 148 l120 -46 l120 46 l-120 46 z" fill="#0891b2" opacity="0.18"
          stroke="currentColor" stroke-width="1.2"/>
  </g>
  <g color="currentColor" stroke="currentColor" fill="none" stroke-width="1.8">
    <line x1="420" y1="300" x2="420" y2="110" marker-end="url(#rtu-arrow)"/>
  </g>
  <text x="404" y="208" text-anchor="middle" font-size="13" fill="currentColor"
        font-family="system-ui, sans-serif" font-weight="600"
        transform="rotate(-90 404 208)">axis 2 · slice</text>
  <text x="712" y="292" font-size="11" fill="currentColor" opacity="0.7"
        font-family="system-ui, sans-serif">k = 0</text>
  <text x="712" y="172" font-size="11" fill="currentColor" opacity="0.7"
        font-family="system-ui, sans-serif">k = n</text>
  <text x="580" y="330" text-anchor="middle" font-size="11" fill="currentColor"
        opacity="0.75" font-family="system-ui, sans-serif">ascending slice position</text>
</svg>
<p class="caption">The first two axes are the image grid as pydicom reads it.
The third runs through the series in spatial order, not file order and not
<code>InstanceNumber</code> order.</p>
</div>
```

## Why this order

The first two axes are ordered exactly as `pixel_array`, so a mask produced by
segmenting the series already has the right layout and needs no rearrangement:

```{code-block} python
import numpy as np

series = rtstruct.series_data
volume = np.stack([s.pixel_array for s in series], axis=-1)
mask = volume > threshold          # ready for add_roi
```

The mask and the images overlay directly, slice for slice:

```{code-block} python
plt.imshow(series[k].pixel_array, cmap="gray")
plt.contour(mask[:, :, k])         # no transpose
```

## Axis 2 is spatial order, not file order

`RTStruct.series_data` is the series sorted by position along the slice
normal, ascending. That is the order axis 2 must be in.

It is **not** necessarily the order the files appear in a directory listing,
and it is not `InstanceNumber` order, which descends in plenty of real
acquisitions. If you build a volume yourself, iterate `series_data`
rather than globbing the directory:

```{code-block} python
# Right: the order rt-utils sorted into
volume = np.stack([s.pixel_array for s in rtstruct.series_data], axis=-1)

# Wrong: whatever order the filesystem returned
volume = np.stack([pydicom.dcmread(f).pixel_array for f in glob("*.dcm")], axis=-1)
```

A mask stacked in the wrong order writes every contour to the wrong slice and
produces a perfectly valid structure set describing the wrong anatomy.

## A mask from somewhere else

A mask that came from another tool carries that tool's conventions. The two
things that differ are the **axis order** and the **direction** each axis runs
in, and a volume can disagree on both at once.

:::{danger}
There is no fixed sequence of `transpose`, `flipud` and `rot90` that converts
correctly. The right rearrangement is whatever the two geometries say it is,
and it differs from file to file. That is exactly why advice of that kind
works on one dataset and silently fails on the next.
:::

For NIfTI, use the converter, which reads both affines and resamples between
them:

```{code-block} python
from rt_utils.nifti import nifti_to_mask

mask = nifti_to_mask("segmentation.nii.gz", rtstruct.series_data)
rtstruct.add_roi(mask=mask, name="liver")
```

See {doc}`../guide/nifti`.

For anything else, the test is absolute, not relative: pick a voxel you can
identify anatomically, and check that the mask marks it on the same slice and
at the same place as the image does.

## Validation

{meth}`~rt_utils.rtstruct.RTStruct.add_roi` checks the mask before writing
anything and raises `RTStruct.ROIException` if:

- the dtype is not `bool`;
- the array is not 3-dimensional;
- `mask.shape[2]` is not the number of slices in the series;
- `mask.shape[:2]` is not `(Rows, Columns)` of the series.

An empty mask is logged, not raised. A structure legitimately absent from a
patient is not an error.

:::{warning}
On a **square** series the first two checks cannot tell a transposed mask from
a correct one. `512 × 512` transposed is still `512 × 512`. The shape check is
a guard against a mask sized for a different series, not a proof of
orientation.
:::

## History

Before 2.2.0 masks were *allocated and validated* as `(Columns, Rows, Slices)`
while every geometric computation used the opposite order. On a square series
the two are indistinguishable, which is how the discrepancy survived from 2020.
On a non-square series it was wrong in both directions: ROIs past the shorter
dimension read back as zero voxels, and correct masks were rejected.

If you transposed your masks to work around that on a non-square series,
**remove the transpose** when upgrading to 2.2.0 or later. Square series are
unaffected in plane.
