"""Contours that are paths rather than boundaries.

``ContourGeometricType`` says what a contour means. ``CLOSED_PLANAR`` bounds a
region; ``OPEN_PLANAR`` and ``OPEN_NONPLANAR`` are paths with no interior at
all. Reading a mask back used to ignore the attribute and fill every contour
of three or more points as though it were closed.

For a structure stored as an open path -- a brachytherapy applicator channel,
a catheter, a vessel centreline -- that claims the whole area between the
path's two ends. A C-shaped channel of about 65 voxels came back as a solid
block of 579. This is the shape of the failure reported in #60, where organ
contours load correctly and an applicator does not.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from tests.conftest import build_series

ROWS = COLUMNS = 40

# A 'C': an open path enclosing a large area if its ends were joined.
C_SHAPE = [
    [8, 5, 0],
    [8, 15, 0],
    [8, 25, 0],
    [20, 30, 0],
    [32, 25, 0],
    [32, 15, 0],
    [32, 5, 0],
]


def _rtstruct():
    return RTStructBuilder.create_new(
        build_series([0.0, 2.0, 4.0], rows=ROWS, columns=COLUMNS)
    )


def _add_path(rtstruct, name, geometric_type):
    rtstruct.add_roi_from_coordinates([C_SHAPE], name=name, coordinate_space="pixel")
    contour = rtstruct.ds.ROIContourSequence[-1].ContourSequence[0]
    contour.ContourGeometricType = geometric_type
    return rtstruct.get_roi_mask_by_name(name)


@pytest.mark.parametrize("geometric_type", ["OPEN_PLANAR", "OPEN_NONPLANAR"])
def test_an_open_contour_is_drawn_as_a_path(geometric_type):
    """Only the path itself, not the area its ends would enclose."""
    mask = _add_path(_rtstruct(), "channel", geometric_type)

    set_voxels = int(mask.sum())
    assert 40 <= set_voxels <= 120, (
        f"a 7-point polyline should cover on the order of 65 voxels, got "
        f"{set_voxels}; filling the path instead gives about 579"
    )


def test_the_interior_of_an_open_contour_stays_empty():
    """The giveaway: the middle of the C must not be set."""
    mask = _add_path(_rtstruct(), "channel", "OPEN_PLANAR")

    # Well inside the C's mouth, far from any segment of the path.
    assert not mask[20, 15, 0]
    assert not mask[20, 20, 0]


def test_the_path_itself_is_present():
    """Drawing nothing at all would also pass a 'not filled' assertion."""
    mask = _add_path(_rtstruct(), "channel", "OPEN_PLANAR")

    # The two uprights of the C, which the path runs along.
    assert mask[10, 8, 0]
    assert mask[10, 32, 0]


def test_a_closed_contour_of_the_same_points_is_still_filled():
    """The change must not reach closed contours, which do bound a region."""
    mask = _add_path(_rtstruct(), "region", "CLOSED_PLANAR")

    assert mask[20, 15, 0]
    assert int(mask.sum()) > 400


def test_mixed_geometry_within_one_roi_is_handled_per_contour():
    """One ROI may hold a closed organ contour and an open path.

    Classifying the ROI by its first contour would rasterise the rest wrongly.
    """
    rtstruct = _rtstruct()
    rtstruct.add_roi_from_coordinates(
        [
            [[5, 5, 0], [15, 5, 0], [15, 15, 0], [5, 15, 0]],  # closed, slice 0
            [[8, 5, 1], [8, 25, 1], [20, 30, 1], [32, 25, 1], [32, 5, 1]],  # slice 1
        ],
        name="mixed",
        coordinate_space="pixel",
    )
    contours = rtstruct.ds.ROIContourSequence[-1].ContourSequence
    by_slice = {c.ContourImageSequence[0].ReferencedSOPInstanceUID: c for c in contours}
    open_contour = by_slice[rtstruct.series_data[1].SOPInstanceUID]
    open_contour.ContourGeometricType = "OPEN_PLANAR"

    mask = rtstruct.get_roi_mask_by_name("mixed")

    # The closed square on slice 0 is filled.
    assert mask[10, 10, 0]
    # The open path on slice 1 is not.
    assert not mask[20, 18, 1]
    assert mask[10, 8, 1]


def test_round_tripping_a_mask_is_unaffected():
    """add_roi writes CLOSED_PLANAR, so masks must behave exactly as before."""
    rtstruct = _rtstruct()
    mask = np.zeros((ROWS, COLUMNS, 3), dtype=bool)
    mask[10:30, 12:28, :] = True
    mask[16:24, 18:22, :] = False  # a hole, to exercise nested contours

    rtstruct.add_roi(mask=mask, name="ring")

    assert np.array_equal(rtstruct.get_roi_mask_by_name("ring"), mask)
