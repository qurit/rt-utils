"""Smoothing a mask before its contours are generated.

A mask drawn on the image grid has stair-stepped edges, and tracing contours
from it reproduces those steps. Smoothing upscales the mask, blurs and
re-thresholds it, and traces contours at that higher resolution, dividing the
coordinates back down so the result sits on the original image's grid at
sub-voxel precision.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder, smoothing
from rt_utils.rtstruct import RTStruct


def _staircase(rtstruct: RTStruct) -> np.ndarray:
    """A deliberately stair-stepped diagonal edge."""
    ref = rtstruct.series_data[0]
    dims = (int(ref.Columns), int(ref.Rows), len(rtstruct.series_data))
    mask = np.zeros(dims, dtype=bool)
    for step in range(10):
        mask[100 + step * 8 : 108 + step * 8, 100 : 100 + (step + 1) * 8, :] = True
    return mask


def _contour_point_count(rtstruct: RTStruct, index: int = 0) -> int:
    return sum(
        int(contour.NumberOfContourPoints)
        for contour in rtstruct.ds.ROIContourSequence[index].ContourSequence
    )


@pytest.mark.parametrize("mode", ["2d", "3d"])
def test_smoothing_adds_sub_voxel_contour_detail(series_path, mode):
    """A smoothed ROI must describe its boundary with more points.

    Without smoothing the contour has one vertex per corner of the voxel
    staircase. With it, the boundary is traced on an upscaled mask, so it
    carries detail finer than the image grid.
    """
    plain = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(plain)
    plain.add_roi(mask=mask, name="plain")

    smoothed = RTStructBuilder.create_new(dicom_series_path=series_path)
    smoothed.add_roi(mask=mask, name="smoothed", apply_smoothing=mode)

    assert _contour_point_count(smoothed) > _contour_point_count(plain)


@pytest.mark.parametrize("mode", ["2d", "3d"])
def test_smoothed_contours_stay_on_the_image_grid(series_path, mode):
    """Upscaling must not leak into the written coordinates.

    Contours are traced on a mask several times larger, so if the scaling
    factor were not divided out the ROI would land far outside the image.
    """
    plain = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(plain)
    plain.add_roi(mask=mask, name="plain")
    reference = plain.get_roi_mask_by_name("plain")

    smoothed = RTStructBuilder.create_new(dicom_series_path=series_path)
    smoothed.add_roi(mask=mask, name="smoothed", apply_smoothing=mode)
    loaded = smoothed.get_roi_mask_by_name("smoothed")

    assert loaded.shape == reference.shape
    assert loaded.any(), "smoothed ROI reads back empty"

    # The smoothed boundary moves, but the ROI must stay in the same region.
    reference_points = np.argwhere(reference)
    loaded_points = np.argwhere(loaded)
    for axis in (0, 1):
        assert (
            abs(loaded_points[:, axis].mean() - reference_points[:, axis].mean()) < 20
        )


def test_smoothing_is_off_by_default(series_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(rtstruct)

    rtstruct.add_roi(mask=mask, name="plain")

    assert np.array_equal(rtstruct.get_roi_mask_by_name("plain"), mask)


def test_invalid_smoothing_mode_is_rejected(series_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(rtstruct)

    with pytest.raises(ValueError, match="Invalid smoothing mode"):
        rtstruct.add_roi(mask=mask, name="bad", apply_smoothing="4d")


def test_smoothing_an_empty_mask_is_rejected(series_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    ref = rtstruct.series_data[0]
    empty = np.zeros(
        (int(ref.Columns), int(ref.Rows), len(rtstruct.series_data)), dtype=bool
    )

    with pytest.raises(Exception):
        rtstruct.add_roi(mask=empty, name="empty", apply_smoothing="2d")


def test_custom_smoothing_parameters_are_used(series_path):
    """A smaller scaling factor must produce a correspondingly smaller mask."""
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(rtstruct)

    parameters = {
        "scaling_iterations": 1,
        "filter_iterations": 1,
        "crop_margins": [20, 20, 1],
        "np_kron": {"scaling_factor": 2},
        "ndimage_gaussian_filter": {"sigma": 1, "radius": 2},
        "threshold": {"threshold": 0.5},
    }

    result = smoothing.pipeline(
        mask=mask, apply_smoothing="2d", smoothing_parameters=parameters
    )

    assert result.shape[0] == mask.shape[0] * 2
    assert result.shape[1] == mask.shape[1] * 2
    assert result.shape[2] == mask.shape[2], "z must not be scaled"


def test_a_custom_smoothing_function_can_be_supplied(series_path):
    """smoothing_function is a hook, not a fixed implementation."""
    calls = []

    def passthrough(mask, apply_smoothing, smoothing_parameters):
        calls.append(apply_smoothing)
        return mask

    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(rtstruct)

    rtstruct.add_roi(
        mask=mask,
        name="custom",
        apply_smoothing="2d",
        smoothing_function=passthrough,
    )

    assert calls == ["2d"]
    # Returned unscaled, so the ROI is unchanged.
    assert np.array_equal(rtstruct.get_roi_mask_by_name("custom"), mask)


def test_pipeline_scales_x_and_y_but_not_z(series_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _staircase(rtstruct)

    result = smoothing.pipeline(mask=mask, apply_smoothing="2d")

    factor = smoothing.default_smoothing_parameters_2d["np_kron"]["scaling_factor"]
    iterations = smoothing.default_smoothing_parameters_2d["scaling_iterations"]
    assert result.shape[0] == mask.shape[0] * factor**iterations
    assert result.shape[2] == mask.shape[2]
