import numpy as np
import pytest

from rt_utils.image_helper import mask_to_edge_polygons
from rt_utils.utils import COLOR_PALETTE
from tests.test_rtstruct_builder import get_empty_mask


def test_single_voxel_edge_polygon():
    mask = np.zeros((3, 4), dtype=bool)
    mask[1, 2] = True

    polygons = mask_to_edge_polygons(mask)

    assert len(polygons) == 1
    assert set(map(tuple, polygons[0])) == {
        (1.5, 0.5),
        (2.5, 0.5),
        (2.5, 1.5),
        (1.5, 1.5),
    }


def test_rectangular_edge_polygon_merges_collinear_vertices():
    mask = np.zeros((6, 7), dtype=bool)
    mask[1:4, 2:6] = True

    polygon = mask_to_edge_polygons(mask)[0]

    assert len(polygon) == 4
    assert (polygon[:, 0].min(), polygon[:, 0].max()) == (1.5, 5.5)
    assert (polygon[:, 1].min(), polygon[:, 1].max()) == (0.5, 3.5)


def test_edge_polygons_preserve_holes_as_separate_loops():
    mask = np.ones((5, 5), dtype=bool)
    mask[2, 2] = False

    polygons = mask_to_edge_polygons(mask)

    assert len(polygons) == 2


def test_edge_polygons_handle_diagonally_touching_voxels():
    mask = np.eye(2, dtype=bool)

    polygons = mask_to_edge_polygons(mask)

    assert sum(len(polygon) for polygon in polygons) >= 6


VALID_COLORS = [
    ("fff", [255, 255, 255]),
    ("#fff", [255, 255, 255]),
    (None, COLOR_PALETTE[0]),
    (COLOR_PALETTE[1], COLOR_PALETTE[1]),
    ("#696969", [105, 105, 105]),
    ("a81414", [168, 20, 20]),
    ("#000", [0, 0, 0]),
]

INVALID_COLORS = [
    ("GGG", ValueError),
    ("red", ValueError),
    ("22", ValueError),
    ("[]", ValueError),
    ([], ValueError),
    ([24, 34], ValueError),
    ([24, 34, 454], ValueError),
    ([0, 344, 0], ValueError),
    ("a8141", ValueError),
    ("a814111", ValueError),
    (KeyboardInterrupt, ValueError),
]


@pytest.mark.parametrize("color", VALID_COLORS)
def test_mask_colors(new_rtstruct, color):
    color_in, color_out = color

    name = "Test ROI"
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1

    new_rtstruct.add_roi(mask, color=color_in, name=name)
    assert new_rtstruct.ds.ROIContourSequence[0].ROIDisplayColor == color_out


@pytest.mark.parametrize("color", INVALID_COLORS)
def test_mask_colors_fail(new_rtstruct, color):
    color_in, err = color

    name = "Test ROI"
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1

    with pytest.raises(err):
        new_rtstruct.add_roi(mask, color=color_in, name=name)
