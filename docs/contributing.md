# Contributing

Issues and pull requests are welcome:
[github.com/qurit/rt-utils](https://github.com/qurit/rt-utils). The process is
in
[CONTRIBUTING.md](https://github.com/qurit/rt-utils/blob/main/CONTRIBUTING.md);
this page is about the parts specific to working on the code.

## Setup

```{code-block} bash
git clone https://github.com/qurit/rt-utils.git
cd rt-utils
pip install -e ".[dev]"
pytest
```

The test suite builds its DICOM fixtures in memory. There is no sample data to
download, and the suite runs in seconds.

## The testing rule that matters

:::{danger}
**A round-trip test cannot detect a symmetric error.**
:::

This is not a hypothetical. The mask axis order was wrong from 2020 to 2.2.0
and 134 tests passed over it, because the same wrong transform was used to
read and to write. The error cancelled inside the library and reappeared for
every other consumer of the file. The averaged-slice-spacing bug fixed in
2.3.0 was the same shape, and so was the half-voxel contour offset fixed in
2.0.0 — writing shrank every structure by half a voxel and reading grew it
back.

So: **a geometry test asserts absolute position against the DICOM standard**,
PS3.3 C.7.6.2.1.1, not against what the library itself produces.

```{code-block} python
:caption: The form a geometry assertion takes

# Where the standard says this voxel is:
expected = (
    np.array(slice_ds.ImagePositionPatient)
    + column * slice_ds.PixelSpacing[1] * np.array(slice_ds.ImageOrientationPatient[0:3])
    + row * slice_ds.PixelSpacing[0] * np.array(slice_ds.ImageOrientationPatient[3:6])
)

# Where rt-utils put it:
assert np.allclose(written_point, expected, atol=1e-6)
```

Round-trip tests are still worth having — the conformance suite is one — but
they are a regression net, not a correctness proof.

## Fixtures

`tests/conftest.py` builds series in memory:

```{code-block} python
from tests.conftest import build_series

series = build_series(
    z_positions=[0, 2, 4, 20],        # uneven on purpose
    rows=50,
    columns=100,                      # non-square on purpose
    pixel_spacing=[0.5, 0.7],
    orientation=[1, 0, 0, 0, 1, 0],
)
```

Non-square and unevenly spaced series are where the interesting bugs live. A
square, evenly spaced series cannot distinguish a transpose from the truth.

`save_dataset(ds, path)` writes a dataset to disk — use it rather than
`save_as` directly, because `enforce_file_format` exists only in pydicom 3 and
Python 3.9 resolves to pydicom 2.

## Conventions

- **One pull request per concern.** A fix and a refactor go separately.
- Commit messages carry the reasoning, not just the change. Read a few in
  `git log` before writing one.
- `black` runs as a required check. Run it before pushing:

  ```{code-block} bash
  black rt_utils tests
  ```

- CI covers Python 3.9 to 3.13, plus a job pinned to OpenCV 4.x. The 4.x path
  is where several contour bugs actually bit — OpenCV 5 is more permissive.

## Building the documentation

```{code-block} bash
pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```

Then open `docs/_build/html/index.html`.

Read the Docs builds with `fail_on_warning`, so a broken cross-reference or a
page missing from a toctree fails the build. Check it locally the same way:

```{code-block} bash
sphinx-build -b html -W docs docs/_build/html
```

The API reference comes from the docstrings in the source, so documenting a
new public function means writing its docstring in NumPy style — nothing to
add here.

## Releasing

See
[RELEASING.md](https://github.com/qurit/rt-utils/blob/main/RELEASING.md).
Publication is triggered by a published GitHub Release tagged `vX.Y.Z`; the
workflow checks the tag against `rt_utils/_version.py`, refuses a version
already on PyPI, and smoke-tests the wheel in a clean virtualenv before
uploading.
