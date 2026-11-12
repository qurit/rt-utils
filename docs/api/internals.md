# Internals

:::{warning}
These modules are implementation detail. Their signatures change without a
major version bump. They are documented because the geometry functions are
genuinely useful when working out why a contour landed where it did.
:::

## rt_utils.image_helper

Loading and sorting series, the pixel-to-patient transformations, tracing
contours from masks and rasterising them back.

```{eval-rst}
.. automodule:: rt_utils.image_helper
   :members:
   :member-order: bysource
```

## rt_utils.ds_helper

Building the DICOM datasets and sequences that make up a structure set.

```{eval-rst}
.. automodule:: rt_utils.ds_helper
   :members:
   :member-order: bysource
```
