import pytest

from rt_utils.utils import COLOR_PALETTE
from tests.test_rtstruct_builder import get_empty_mask


VALID_COLORS = [
    ('fff', [255, 255, 255]),
    ('#fff', [255, 255, 255]),
    (None, COLOR_PALETTE[0]),
    (COLOR_PALETTE[1], COLOR_PALETTE[1]),
    ('#696969', [105, 105, 105]),
    ('a81414', [168, 20, 20]),
    ('#000', [0, 0, 0]),
]

INVALID_COLORS = [
    ('GGG', ValueError),
    ('red', ValueError),
    ('22', ValueError),
    ('[]', ValueError),
    ([], ValueError),
    ([24, 34], ValueError),
    ([24, 34, 454], ValueError),
    ([0, 344, 0], ValueError),
    ('a8141', ValueError),
    ('a814111', ValueError),
    (KeyboardInterrupt, ValueError),
]


@pytest.mark.parametrize('color', VALID_COLORS)
def test_mask_colors(new_rtstruct, color):
    color_in, color_out = color

    name = "Test ROI"
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1

    new_rtstruct.add_roi(mask, color=color_in, name=name)
    assert new_rtstruct.ds.ROIContourSequence[0].ROIDisplayColor == color_out


@pytest.mark.parametrize('color', INVALID_COLORS)
def test_mask_colors_fail(new_rtstruct, color):
    color_in, err = color

    name = "Test ROI"
    mask = get_empty_mask(new_rtstruct)
    mask[50:100, 50:100, 0] = 1

    with pytest.raises(err):
        new_rtstruct.add_roi(mask, color=color_in, name=name)
