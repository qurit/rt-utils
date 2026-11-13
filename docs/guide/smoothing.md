# Smoothing

A mask drawn on the image grid has stair-stepped edges, and tracing contours
from it reproduces those steps. Smoothing upscales the mask, blurs and
re-thresholds it, and traces contours at that higher resolution, so the
boundary carries detail finer than the voxel grid can express:

```{code-block} python
rtstruct.add_roi(mask=mask, name="GTV", apply_smoothing="2d")
```

`"2d"`
: Blurs each slice independently. In-plane edges are smoothed; the structure
  keeps its slice-by-slice extent exactly.

`"3d"`
: Blurs across slices as well, so the structure is smooth through the stack
  too.

On a stair-stepped test shape the traced boundary length falls from 307 to
298 with `"2d"` and 287 with `"3d"`.

:::{warning}
`"3d"` erodes volume noticeably on short series. Blurring along the slice
axis has few slices to work with, and the structure loses its first and last
slices where there is nothing on the far side to balance the blur. Check the
volume before and after if it matters.
:::

## What happens to the coordinates

The upscaled mask is only an intermediate. Contour coordinates are divided by
the scaling factor before they are written, so the output is in the image's
own coordinates, so there is no change of grid to account for downstream.

The returned structure set is unaffected in every other way: the mask you
passed is not modified, and the slice count does not change.

## Tuning

```{code-block} python
:caption: The defaults, spelled out

rtstruct.add_roi(
    mask=mask,
    name="GTV",
    apply_smoothing="2d",
    smoothing_parameters={
        "scaling_iterations": 2,
        "filter_iterations": 3,
        "crop_margins": [20, 20, 1],
        "np_kron": {"scaling_factor": 3},
        "ndimage_gaussian_filter": {"sigma": 2, "radius": 3},
        "threshold": {"threshold": 0.5},
    },
)
```

```{list-table}
:header-rows: 1
:widths: 32 68

* - Parameter
  - Effect
* - `scaling_iterations`
  - How many times the upscale-blur-threshold cycle runs. The mask grows by
    `scaling_factor` each time, so cost grows quickly.
* - `np_kron.scaling_factor`
  - Upscale factor per iteration. The default 3 over 2 iterations gives 9× in
    plane.
* - `filter_iterations`
  - Blur passes per iteration. More rounds corners further.
* - `ndimage_gaussian_filter`
  - Passed to {func}`scipy.ndimage.gaussian_filter`. A larger `sigma` smooths
    more and shrinks convex structures more.
* - `threshold.threshold`
  - Where the blurred mask is cut back to binary. Below 0.5 dilates the
    structure, above 0.5 erodes it.
* - `crop_margins`
  - Margin kept around the structure's bounding box, in voxels, as
    `[rows, columns, slices]`. The mask is cropped before upscaling so memory
    stays bounded; the margin must be wide enough that the blur does not
    reach the crop edge.
```

Memory is the practical limit. A 512 × 512 slice at the default 9× in plane
is 21 megavoxels per slice before cropping, which is why cropping to the
bounding box happens first.

## Substituting your own

`smoothing_function` is a hook. It receives the mask and the parameters and
must return a mask upscaled in the first two axes by a whole factor, with the
slice axis unchanged:

```{code-block} python
def my_smoothing(mask, apply_smoothing, smoothing_parameters):
    ...
    return upscaled_mask        # shape (rows * k, columns * k, slices)

rtstruct.add_roi(
    mask=mask,
    name="GTV",
    apply_smoothing="2d",
    smoothing_function=my_smoothing,
)
```

The scaling factor is derived from the returned shape, and a function that
returns something smaller than the image raises
`RTStruct.ROIException`.

## When not to use it

Smoothing is a cosmetic operation on the boundary. It does not add
information, and it will not rescue a bad segmentation. For a small structure,
one only a few voxels across, the blur removes a meaningful fraction of the
volume.

Smoothing an empty mask raises `ValueError`.
