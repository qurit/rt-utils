---
hide-toc: true
---

# RT-Utils

```{raw} html
<div class="rtu-hero">
  <p class="rtu-tagline">A minimal Python library for DICOM RT Struct manipulation</p>
  <p class="rtu-badges">
    <a href="https://pypi.org/project/rt-utils"><img src="https://badge.fury.io/py/rt-utils.svg" alt="PyPI version" height="20"></a>
    <img src="https://img.shields.io/pypi/pyversions/rt-utils" alt="Supported Python versions" height="20">
    <a href="https://doi.org/10.21105/joss.07361"><img src="https://joss.theoj.org/papers/10.21105/joss.07361/status.svg" alt="JOSS paper" height="20"></a>
    <img src="https://img.shields.io/github/license/qurit/rt-utils?color=g" alt="MIT licence" height="20">
  </p>
</div>
```

RT-Utils reads and writes the DICOM **RT Structure Set**, the file a treatment
planning system stores contoured anatomy in. It turns an RTStruct into a NumPy
mask you can compute on, and turns a mask back into a conformant RTStruct a
planning system or viewer will open.

```python
from rt_utils import RTStructBuilder

rtstruct = RTStructBuilder.create_new(dicom_series_path="./series")
rtstruct.add_roi(mask=mask_from_your_model, name="GTV", color=[255, 0, 255])
rtstruct.save("structures")
```

Install it with:

```{code-block} bash
pip install rt-utils
```

---

## Start here

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`rocket;1.2em` Quickstart
:link: quickstart
:link-type: doc

Create a structure set, add an ROI and read one back: the whole round trip in
a few lines.
:::

:::{grid-item-card} {octicon}`stack;1.2em` Mask layout
:link: concepts/mask-layout
:link-type: doc

What `(Rows, Columns, Slices)` means, and why an ROI comes back rotated when it
is ignored. **Read this before your first `add_roi`.**
:::

:::{grid-item-card} {octicon}`book;1.2em` User guide
:link: guide/creating
:link-type: doc

Creating, reading, editing and merging structure sets; NIfTI conversion;
contours given as coordinates; smoothing.
:::

:::{grid-item-card} {octicon}`code;1.2em` API reference
:link: api/index
:link-type: doc

Every public class and function, generated from the docstrings in the source.
:::

::::

## What it does

```{list-table}
:header-rows: 1
:widths: 30 70

* - Task
  - How
* - Turn a segmentation into an RTStruct
  - {meth}`RTStruct.add_roi <rt_utils.rtstruct.RTStruct.add_roi>`
* - Turn an RTStruct ROI into a mask
  - {meth}`RTStruct.get_roi_mask_by_name <rt_utils.rtstruct.RTStruct.get_roi_mask_by_name>`
* - Convert a NIfTI segmentation onto the series grid
  - {func}`rt_utils.nifti.nifti_to_mask`
* - Write contours you already have in patient or pixel coordinates
  - {meth}`RTStruct.add_roi_from_coordinates <rt_utils.rtstruct.RTStruct.add_roi_from_coordinates>`
* - Remove a structure
  - {meth}`RTStruct.delete_roi <rt_utils.rtstruct.RTStruct.delete_roi>`
* - Combine two structure sets for one series
  - {meth}`RTStructMerger.merge_rtstructs <rt_utils.rtstruct_merger.RTStructMerger.merge_rtstructs>`
```

## What it does not do

RT-Utils is deliberately small. It does not plan, does not compute dose, and
does not resample images. A few limits are worth knowing before you start:

- One frame of reference and one image series per structure set. A structure
  set spanning several series is only partly supported. See
  {doc}`guide/troubleshooting`.
- Nested contours (a hole inside a structure) are written as nested closed
  contours. Viewers that cannot draw those need `use_pin_hole=True`.
- Reading requires the image series the structures were drawn on. The contours
  name their slices by identifier, and the geometry comes from the images.

## Citing

If RT-Utils contributes to published work, please cite the JOSS paper. See
{doc}`citing`.

```{toctree}
:hidden:
:caption: Getting started

installation
quickstart
```

```{toctree}
:hidden:
:caption: Concepts

concepts/mask-layout
concepts/contour-placement
concepts/slice-matching
```

```{toctree}
:hidden:
:caption: User guide

guide/creating
guide/reading
guide/coordinates
guide/nifti
guide/managing-rois
guide/merging
guide/smoothing
guide/in-memory
guide/troubleshooting
```

```{toctree}
:hidden:
:caption: Reference

api/index
changelog
contributing
citing
```
