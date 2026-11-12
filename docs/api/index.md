# API reference

Generated from the docstrings in the source.

## Public API

Everything exported from the top-level package:

```{code-block} python
from rt_utils import RTStruct, RTStructBuilder, RTStructMerger, __version__
```

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} `RTStructBuilder`
:link: builder
:link-type: doc

Creates a structure set from a series, or loads an existing one.
:::

:::{grid-item-card} `RTStruct`
:link: rtstruct
:link-type: doc

The structure set itself: add, read, delete, save.
:::

:::{grid-item-card} `RTStructMerger`
:link: merger
:link-type: doc

Combines two structure sets for one series.
:::

:::{grid-item-card} `rt_utils.nifti`
:link: nifti
:link-type: doc

NIfTI conversion. Optional; needs SimpleITK.
:::

::::

## Everything else

```{toctree}
:maxdepth: 1

builder
rtstruct
merger
nifti
smoothing
utils
internals
```

:::{note}
`rt_utils.image_helper` and `rt_utils.ds_helper` are implementation detail.
They are documented because they are useful when debugging geometry, not
because they are stable. See {doc}`internals`.
:::
