"""Round-trip conformance tests across contour topologies.

Each test builds a mask of known geometry, writes it through ``add_roi``, reads
it back with ``get_roi_mask_by_name``, and compares the result to the input.

The point is coverage of *topology*, which is where contour bugs live: holes,
nested holes, disjoint regions, concave outlines, single-voxel structures.
Three separate defects fixed in 1.4.0 and 1.4.1 all produced wrong geometry
with no exception raised, and none were caught by the existing tests.

In the default contour mode every shape here round-trips **exactly**, so these
assert equality rather than a loosened similarity score. The two lossy modes
are tested separately with thresholds taken from measurement, each documented
with the reason it is lossy.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils.rtstruct import RTStruct


def _grid(rtstruct: RTStruct):
    """Mask dimensions for a series, matching create_empty_series_mask."""
    ref = rtstruct.series_data[0]
    return int(ref.Columns), int(ref.Rows), len(rtstruct.series_data)


def _blank(rtstruct: RTStruct) -> np.ndarray:
    return np.zeros(_grid(rtstruct), dtype=bool)


def _axes(dims):
    return np.arange(dims[0])[:, None], np.arange(dims[1])[None, :]


def _stack(dims, plane: np.ndarray) -> np.ndarray:
    mask = np.zeros(dims, dtype=bool)
    mask[:, :, :] = plane[:, :, None]
    return mask


# --- shapes -----------------------------------------------------------------


def solid_square(dims):
    mask = np.zeros(dims, dtype=bool)
    mask[dims[0] // 4 : dims[0] // 2, dims[1] // 4 : dims[1] // 2, :] = True
    return mask


def solid_disc(dims):
    a, b = _axes(dims)
    radius = min(dims[0], dims[1]) // 5
    plane = (a - dims[0] // 2) ** 2 + (b - dims[1] // 2) ** 2 <= radius**2
    return _stack(dims, plane)


def annulus(dims):
    """A ring. Exercises a hole inside an ROI."""
    a, b = _axes(dims)
    outer = min(dims[0], dims[1]) // 5
    inner = min(dims[0], dims[1]) // 10
    r = (a - dims[0] // 2) ** 2 + (b - dims[1] // 2) ** 2
    return _stack(dims, (r <= outer**2) & (r >= inner**2))


def nested_rings(dims):
    """Two concentric rings. Exercises several holes in one slice."""
    a, b = _axes(dims)
    unit = min(dims[0], dims[1]) // 16
    r = (a - dims[0] // 2) ** 2 + (b - dims[1] // 2) ** 2
    outer_ring = (r <= (unit * 5) ** 2) & (r >= (unit * 4) ** 2)
    inner_ring = (r <= (unit * 3) ** 2) & (r >= (unit * 2) ** 2)
    return _stack(dims, outer_ring | inner_ring)


def two_disjoint_blobs(dims):
    """Two separate regions, so a slice carries more than one contour."""
    a, b = _axes(dims)
    radius = min(dims[0], dims[1]) // 10
    first = (a - dims[0] // 4) ** 2 + (b - dims[1] // 4) ** 2 <= radius**2
    second = (a - 3 * dims[0] // 4) ** 2 + (b - 3 * dims[1] // 4) ** 2 <= radius**2
    return _stack(dims, first | second)


def l_shape(dims):
    """A concave outline, which a convex-hull approximation would distort."""
    mask = np.zeros(dims, dtype=bool)
    mask[dims[0] // 4 : dims[0] // 2, dims[1] // 4 : dims[1] // 2, :] = True
    mask[dims[0] // 2 : 3 * dims[0] // 5, dims[1] // 4 : 3 * dims[1] // 4, :] = True
    return mask


def thin_line(dims):
    """A one-voxel-wide structure, the degenerate end of contour handling."""
    mask = np.zeros(dims, dtype=bool)
    column = dims[1] // 2
    mask[dims[0] // 4 : dims[0] // 2, column : column + 1, :] = True
    return mask


def single_voxel(dims):
    """One voxel. Writes a POINT contour rather than a CLOSED_PLANAR one."""
    mask = np.zeros(dims, dtype=bool)
    mask[dims[0] // 2, dims[1] // 2, 0] = True
    return mask


SHAPES = {
    "solid_square": solid_square,
    "solid_disc": solid_disc,
    "annulus": annulus,
    "nested_rings": nested_rings,
    "two_disjoint_blobs": two_disjoint_blobs,
    "l_shape": l_shape,
    "thin_line": thin_line,
    "single_voxel": single_voxel,
}


# --- metrics ----------------------------------------------------------------


def dice_coefficient(a: np.ndarray, b: np.ndarray) -> float:
    total = a.sum() + b.sum()
    if total == 0:
        return 1.0
    return 2.0 * np.logical_and(a, b).sum() / total


def volume_relative_error(expected: np.ndarray, actual: np.ndarray) -> float:
    expected_volume = expected.sum()
    if expected_volume == 0:
        return 0.0
    return abs(int(actual.sum()) - int(expected_volume)) / int(expected_volume)


def round_trip(series_path: str, mask: np.ndarray, name: str, **add_roi_kwargs):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    rtstruct.add_roi(mask=mask, name=name, **add_roi_kwargs)
    return rtstruct.get_roi_mask_by_name(name)


# --- tests ------------------------------------------------------------------


@pytest.mark.parametrize("shape_name", sorted(SHAPES))
def test_shape_round_trips_exactly(series_path, shape_name):
    """Every topology must survive a round trip unchanged.

    This is an equality assertion, not a similarity threshold. In the default
    contour mode rt-utils reproduces each of these masks voxel for voxel, so
    anything less is a regression rather than an expected approximation.
    """
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = SHAPES[shape_name](_grid(rtstruct))
    assert mask.sum() > 0, "shape generator produced an empty mask"

    loaded = round_trip(series_path, mask, shape_name)

    assert loaded.shape == mask.shape
    assert dice_coefficient(mask, loaded) == 1.0, (
        f"{shape_name}: dice {dice_coefficient(mask, loaded):.4f}, "
        f"volume error {volume_relative_error(mask, loaded):.2%}"
    )
    assert np.array_equal(mask, loaded)


@pytest.mark.parametrize("shape_name", ["annulus", "solid_disc", "single_voxel"])
def test_shape_round_trips_on_non_square_series(one_slice_series_path, shape_name):
    """The same must hold when Rows and Columns differ.

    Masks are allocated as (Columns, Rows, Slices), so a non-square series is
    where an axis-order mistake would show up.
    """
    rtstruct = RTStructBuilder.create_new(dicom_series_path=one_slice_series_path)
    dims = _grid(rtstruct)
    assert dims[0] != dims[1], "this fixture is expected to be non-square"

    mask = SHAPES[shape_name](dims)
    loaded = round_trip(one_slice_series_path, mask, shape_name)

    assert np.array_equal(mask, loaded)


def test_pin_hole_is_lossy_but_bounded(series_path):
    """use_pin_hole cuts a channel from each hole to the outer boundary.

    That is how it represents holes without nested contours, so it removes a
    thin line of voxels and cannot round-trip exactly. Measured on this
    annulus: dice 0.9968, volume error 0.63%. The thresholds below sit just
    outside those values so a real regression still fails the test.
    """
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = annulus(_grid(rtstruct))

    loaded = round_trip(series_path, mask, "pin_hole", use_pin_hole=True)

    assert dice_coefficient(mask, loaded) >= 0.99
    assert volume_relative_error(mask, loaded) <= 0.01


def test_voxel_edge_mode_is_bounded(series_path):
    """voxel_edge places contours on voxel boundaries rather than centres.

    Rasterising those contours back therefore picks up the boundary row and
    column, so the mask grows slightly. Measured on this square: dice 0.9922,
    volume error 1.57%. This is the documented behaviour of the mode, not a
    defect; the assertion exists so the size of the effect cannot drift
    unnoticed.
    """
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = solid_square(_grid(rtstruct))

    loaded = round_trip(series_path, mask, "voxel_edge", contour_mode="voxel_edge")

    assert dice_coefficient(mask, loaded) >= 0.98
    assert volume_relative_error(mask, loaded) <= 0.03
    # The mode grows the mask; it must never shrink it.
    assert loaded.sum() >= mask.sum()


def test_exact_contours_round_trip_exactly(series_path):
    """approximate_contours=False must not be worse than the default."""
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = annulus(_grid(rtstruct))

    loaded = round_trip(series_path, mask, "exact_contours", approximate_contours=False)

    assert np.array_equal(mask, loaded)
