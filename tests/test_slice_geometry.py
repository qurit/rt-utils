"""Where a contour is placed along the slice axis.

A contour's patient coordinates used to come from the first slice's position
plus ``slice_index * average_spacing``. That average equals the real step only
when the slices are evenly spaced. On an unevenly spaced series — a scout image
left in the folder, a stack acquired with a varying increment, slices that were
partly culled — every slice between the first and the last was written to a
position no slice occupies.

Nothing failed when that happened: the RTStruct was valid, and the ROI simply
described the wrong anatomy. These tests pin each contour to the position of
the slice it was drawn on, which is exact whatever the spacing does. This is
#97.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from tests.conftest import build_series

UNEVEN = [0.0, 2.0, 4.0, 20.0]
EVEN = [0.0, 2.0, 4.0, 6.0]


def _add_block(rtstruct, rows=32, columns=32):
    mask = np.zeros((rows, columns, len(rtstruct.series_data)), dtype=bool)
    mask[10:20, 10:20, :] = True
    rtstruct.add_roi(mask=mask, name="block")
    return mask


def _contour_z_by_slice(rtstruct):
    """The z each slice's contour was written at, in series order."""
    written = {}
    for contour in rtstruct.ds.ROIContourSequence[0].ContourSequence:
        referenced = contour.ContourImageSequence[0].ReferencedSOPInstanceUID
        points = np.asarray(contour.ContourData, dtype=float).reshape(-1, 3)
        written[referenced] = points[:, 2]
    return [written[s.SOPInstanceUID] for s in rtstruct.series_data]


@pytest.mark.parametrize("positions", [EVEN, UNEVEN], ids=["even", "uneven"])
def test_contours_are_written_at_their_own_slice_position(positions):
    """Every point of a slice's contour must carry that slice's z.

    On the uneven stack the average spacing is 6.67 mm, so the slice at
    z = 2 used to have its contour written at z = 6.67 — closer to no slice
    at all than to the one it came from.
    """
    rtstruct = RTStructBuilder.create_new(build_series(positions))
    _add_block(rtstruct)

    for expected_z, written_z in zip(positions, _contour_z_by_slice(rtstruct)):
        assert np.allclose(written_z, expected_z), (
            f"contour for the slice at z={expected_z} was written at "
            f"z={sorted(set(written_z.tolist()))}"
        )


@pytest.mark.parametrize("positions", [EVEN, UNEVEN], ids=["even", "uneven"])
def test_mask_round_trips_on_an_unevenly_spaced_series(positions):
    """Reading back must undo the writing, whatever the spacing."""
    rtstruct = RTStructBuilder.create_new(build_series(positions))
    mask = _add_block(rtstruct)

    loaded = rtstruct.get_roi_mask_by_name("block")

    assert np.array_equal(loaded, mask)


def test_uneven_spacing_does_not_shift_the_contour_in_plane():
    """The in-plane position must not depend on the slice axis either.

    The inverse transform measured pixel coordinates from the first slice's
    origin. Any component of a later slice's offset that is not along the
    slice normal then leaked into the in-plane coordinates.
    """
    rtstruct = RTStructBuilder.create_new(build_series(UNEVEN))
    _add_block(rtstruct)

    for contour in rtstruct.ds.ROIContourSequence[0].ContourSequence:
        points = np.asarray(contour.ContourData, dtype=float).reshape(-1, 3)
        # The block spans columns 10-20 and rows 10-20 on a 1 mm grid at the
        # origin, so x and y must fall in that range on every slice.
        assert points[:, 0].min() >= 9.0 and points[:, 0].max() <= 21.0
        assert points[:, 1].min() >= 9.0 and points[:, 1].max() <= 21.0


def test_single_slice_series_still_works():
    """One slice has no spacing to average; it must not divide by zero."""
    rtstruct = RTStructBuilder.create_new(build_series([5.0]))
    mask = _add_block(rtstruct)

    assert np.array_equal(rtstruct.get_roi_mask_by_name("block"), mask)
    points = np.asarray(
        rtstruct.ds.ROIContourSequence[0].ContourSequence[0].ContourData, dtype=float
    ).reshape(-1, 3)
    assert np.allclose(points[:, 2], 5.0)


def test_coordinates_given_on_the_image_grid_follow_the_same_rule():
    """add_roi_from_coordinates places by slice index, so it is affected too."""
    series = build_series(UNEVEN)
    rtstruct = RTStructBuilder.create_new(series)

    # A square on the slice at index 1, which sits at z = 2.0.
    rtstruct.add_roi_from_coordinates(
        coordinates=[[[10, 10, 1], [20, 10, 1], [20, 20, 1], [10, 20, 1]]],
        name="from-pixels",
        coordinate_space="pixel",
    )

    points = np.asarray(
        rtstruct.ds.ROIContourSequence[0].ContourSequence[0].ContourData, dtype=float
    ).reshape(-1, 3)
    assert np.allclose(
        points[:, 2], 2.0
    ), f"expected the polygon on the z=2.0 slice, got z={set(points[:, 2].tolist())}"
