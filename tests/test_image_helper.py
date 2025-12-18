import pytest
import numpy as np

from rt_utils.image_helper import (
    load_sorted_image_series,
    create_empty_series_mask,
    find_mask_contours,
    draw_line_upwards_from_point,
)


def create_full_series_mask(series_data):
    ref_dicom_image = series_data[0]
    mask_dims = (
        int(ref_dicom_image.Columns),
        int(ref_dicom_image.Rows),
        len(series_data),
    )
    mask = np.ones(mask_dims).astype(bool)
    return mask


def test_find_mask_contours_with_empty_mask(series_path):
    series_data = load_sorted_image_series(series_path)
    empty_mask = create_empty_series_mask(series_data)[:, :, 0]

    # `hierarchy` is `None` in this case, thus `hierarchy = hierarchy[0]` fails
    with pytest.raises(TypeError):
        actual_contours, actual_hierarchy = find_mask_contours(empty_mask, True)


def test_find_mask_contours_with_full_mask(series_path):
    series_data = load_sorted_image_series(series_path)
    full_mask = create_full_series_mask(series_data)[:, :, 0]

    # Entire mask is a single contour
    expected_contours = [
        [
            [np.int32(0), np.int32(0)],
            [np.int32(0), np.int32(511)],
            [np.int32(511), np.int32(511)],
            [np.int32(511), np.int32(0)],
        ]
    ]
    expected_hierarchy = [[np.int32(-1), np.int32(-1), np.int32(-1), np.int32(-1)]]

    actual_contours, actual_hierarchy = find_mask_contours(full_mask, True)

    assert np.array_equal(expected_contours, actual_contours) == True
    assert np.array_equal(expected_hierarchy, actual_hierarchy) == True


def test_draw_line_upwards_from_point_with_empty_mask(series_path):
    series_data = load_sorted_image_series(series_path)
    empty_mask = create_empty_series_mask(series_data)[:, :, 0]
    start = (0, 0)

    # Should fill (0,0) and one point in each direction
    expected_binary_mask = empty_mask.copy()
    expected_binary_mask[0][0] = True
    expected_binary_mask[0][1] = True
    expected_binary_mask[1][0] = True

    actual_binary_mask = draw_line_upwards_from_point(empty_mask, start, 1)

    assert np.array_equal(expected_binary_mask, actual_binary_mask) == True


def test_draw_line_upwards_from_point_with_full_mask(series_path):
    series_data = load_sorted_image_series(series_path)
    full_mask = create_full_series_mask(series_data)[:, :, 0]
    start = (0, 0)

    # Should remain unchanged
    expected_binary_mask = full_mask.copy()

    actual_binary_mask = draw_line_upwards_from_point(full_mask, start, 1)

    assert np.array_equal(expected_binary_mask, actual_binary_mask) == True
