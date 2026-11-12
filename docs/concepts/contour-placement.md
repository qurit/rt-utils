# Contour placement

A treatment planning system reads the **contour**, not your mask. Where the
contour is drawn relative to the voxels it came from therefore decides how
large the structure appears everywhere downstream.

## Two modes

`add_roi(..., contour_mode=...)` takes:

`"voxel_edge"` *(default since 2.0.0)*
: Traces the outer edges of the foreground voxels, so the polygon encloses
  exactly the area the mask occupies. Exact at every size.

`"voxel_center"`
: Traces through the centres of the boundary voxels. This understates the
  structure by half a voxel on every side. It is kept for reproducing output
  from releases before 2.0.0, where it was the only behaviour.

The error in `"voxel_center"` is a fixed half voxel per side, so it is
negligible for a large structure and severe for a small one. Measured against
the true extent of a square mask at 0.488 mm spacing:

```{list-table}
:header-rows: 1
:widths: 20 25 25 30

* - Mask
  - True area
  - `"voxel_center"`
  - Error
* - 3 × 3
  - 2.15 mm²
  - 0.95 mm²
  - **−55.6 %**
* - 5 × 5
  - 5.96 mm²
  - 3.81 mm²
  - −36.0 %
* - 10 × 10
  - 23.84 mm²
  - 19.31 mm²
  - −19.0 %
* - 50 × 50
  - 596.05 mm²
  - 572.44 mm²
  - −4.0 %
* - 100 × 100
  - 2384.18 mm²
  - 2336.74 mm²
  - −2.0 %
```

Fiducials, seeds, small nodes and thin structures are where this matters.

:::{note}
`approximate_contours` applies only to `"voxel_center"`. Edge tracing already
emits one vertex per corner, so there is nothing to approximate.
:::

## Reading is by voxel centre

A voxel is set when **its centre lies inside the contour**. That rule is
correct for contours traced on voxel boundaries and for contours traced
through voxel centres alike, so structure sets written by other software are
read accurately whichever convention they used.

Internally, polygons are filled at twice the image resolution and then sampled
at the voxel centres. `cv2.fillPoly` treats its vertices as inclusive, so
filling at image resolution would add a row and a column to any contour that
runs along voxel boundaries — a single voxel coming back as four.

:::{admonition} Why the old default survived so long
:class: seealso

Writing contours through voxel centres shrank every structure by half a voxel
per side; reading them back with an inclusive fill grew it again by the same
amount. The two errors cancelled inside the library and reappeared for every
other consumer of the file. A round-trip test cannot detect a symmetric error
— which is why the geometry tests in this project assert absolute position
against PS3.3 C.7.6.2.1.1 rather than comparing a mask to itself.
:::

Both modes now round trip exactly for every shape in the conformance suite:
solid shapes, an annulus, nested rings, disjoint regions, a concave outline, a
one-voxel-wide line and a single voxel, on square and non-square series.

## Geometric types

`ContourGeometricType` is set from the number of points in the contour, per
PS3.3 C.8.8.6.1:

```{list-table}
:header-rows: 1
:widths: 20 30 50

* - Points
  - Type written
  - Rasterised back as
* - 1
  - `POINT`
  - exactly one voxel
* - 2
  - `OPEN_PLANAR`
  - a one-voxel-wide line
* - 3 or more
  - `CLOSED_PLANAR`
  - the filled interior
```

On read, the type is honoured rather than assumed:

- `CLOSED_PLANAR` bounds a region and is filled.
- `OPEN_PLANAR` and `OPEN_NONPLANAR` are **paths with no interior** and are
  drawn as polylines.

Filling an open contour closes the path and claims everything between its two
ends. A C-shaped brachytherapy applicator channel of about 65 voxels came back
as a solid block of 579 before this distinction was made (fixed in 2.3.0).
Organ structures are closed, which is why they always looked right.

## Holes and nested contours

A structure with a hole — an annulus, a vessel wall — is written as nested
closed contours: an outer boundary and an inner one. That is the correct DICOM
representation, and RT-Utils reads it back correctly.

Some viewers cannot draw nested contours. For those, `use_pin_hole=True` cuts
a one-voxel channel from each hole out to the outer boundary, so each region
becomes a single contour with no nesting:

```{code-block} python
rtstruct.add_roi(mask=mask, name="vessel-wall", use_pin_hole=True)
```

The cost is a visible notch in the structure. Use it only if your viewer needs
it.

:::{warning}
`use_pin_hole` was broken before 2.2.0. It sampled the mask transposed, so on
any region not symmetric about `y = x` the channel was never cut and two
contours were written where one was asked for; on a non-square series it
raised `IndexError`.
:::
