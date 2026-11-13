# Contours from coordinates

When the geometry is already known as polygons, there is no reason to
rasterise it into a mask and trace it back out again.
{meth}`~rt_utils.rtstruct.RTStruct.add_roi_from_coordinates` writes the points
you give, exactly as given.

## Patient coordinates

The default. Each contour is a list of `[x, y, z]` points in millimetres:

```{code-block} python
rtstruct.add_roi_from_coordinates(
    coordinates=[
        [   # one contour, on one slice
            [-20.0, -170.0, -559.0],
            [ 30.0, -170.0, -559.0],
            [ 30.0, -110.0, -559.0],
            [-20.0, -110.0, -559.0],
        ],
        [   # another contour, on the next slice
            [-20.0, -170.0, -562.4],
            [ 30.0, -170.0, -562.4],
            [ 30.0, -110.0, -562.4],
            [-20.0, -110.0, -562.4],
        ],
    ],
    name="Target",
    color=[255, 0, 0],
)
```

Each contour is attached to the slice **nearest its own position**, measured
along the slice normal, so this works on oblique and non-axial series, and
you do not need to know the slice ordering.

## Pixel coordinates

An annotation tool working on the displayed images produces points on the
image grid. Pass `coordinate_space="pixel"` and give
`[column, row, slice_index]`:

```{code-block} python
rtstruct.add_roi_from_coordinates(
    coordinates=[[[60, 50, 0], [120, 50, 0], [120, 100, 0], [60, 100, 0]]],
    name="From an annotation tool",
    coordinate_space="pixel",
)
```

:::{note}
The order here is `[column, row, ...]`, the `(x, y)` convention of image
tools and OpenCV, not the `(row, column)` order a mask is indexed in.

It is the one place in the library where the two differ, because it is the
form annotation tools actually emit.
:::

Points are converted with the series' own pixel-to-patient transformation, so
the polygon is written exactly as supplied.

## When to use this instead of a mask

```{list-table}
:header-rows: 1
:widths: 45 55

* - Use `add_roi_from_coordinates`
  - Use `add_roi`
* - Contours drawn by hand or by an annotation tool
  - Output of a segmentation model
* - Geometry from another structure set or planning system
  - Anything that is naturally a volume
* - Shapes that must be written vertex for vertex
  - Shapes defined on the voxel grid
* - Open paths and single points
  - Closed regions
```

Round-tripping a polygon through a mask quantises it to the voxel grid and
then re-traces it. For a smooth hand-drawn contour that is a real loss.

## Geometric type

The type written follows the point count: one point is a `POINT`, two are
`OPEN_PLANAR`, three or more a `CLOSED_PLANAR`. See
{doc}`../concepts/contour-placement`.

This is the simplest way to write fiducial markers:

```{code-block} python
rtstruct.add_roi_from_coordinates(
    coordinates=[[[12.5, -40.0, -559.0]], [[18.2, -33.1, -562.4]]],
    name="Fiducials",
    roi_generation_algorithm=2,     # MANUAL
)
```

## Limits

- A contour must contain at least one point; an empty one raises `ValueError`.
- No mask validation runs, because there is no mask. Nothing checks that your
  points fall inside the image, and contours outside the imaged volume are
  written as given.
- Smoothing, pin holes and `contour_mode` do not apply; they are all mask
  operations.
