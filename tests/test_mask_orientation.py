"""The in-plane axes of a mask, checked against the DICOM standard.

Every other test in this suite round-trips a mask through this library and
compares the result to the input. That proves the write and read paths agree
with *each other*, but not that either agrees with DICOM: a transposition
applied consistently in both directions round-trips perfectly and still puts
the ROI in the wrong place for everyone else.

These tests pin the absolute mapping instead. Patient coordinates are computed
here from PS3.3 C.7.6.2.1.1 and compared with what the library writes:

    P(column, row) = ImagePositionPatient
                   + column * PixelSpacing[1] * ImageOrientationPatient[0:3]
                   + row    * PixelSpacing[0] * ImageOrientationPatient[3:6]

The fixture used throughout is non-square (50 rows, 100 columns), with
anisotropic spacing and a tilted orientation, so a swapped axis cannot cancel
out.
"""

import numpy as np
import pydicom
import pytest

from rt_utils import RTStructBuilder


def _reference(series_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    return rtstruct, rtstruct.series_data[0]


def _patient_coordinate(series_slice: pydicom.Dataset, column: float, row: float):
    """Where a voxel centre lies in patient space, straight from the standard."""
    origin = np.array([float(v) for v in series_slice.ImagePositionPatient])
    row_spacing, column_spacing = (float(v) for v in series_slice.PixelSpacing)
    orientation = np.array([float(v) for v in series_slice.ImageOrientationPatient])
    along_row, down_column = orientation[:3], orientation[3:]

    return (
        origin + column * column_spacing * along_row + row * row_spacing * down_column
    )


def _only_contour(rtstruct) -> np.ndarray:
    contour = rtstruct.ds.ROIContourSequence[0].ContourSequence[0].ContourData
    return np.asarray(contour, dtype=float).reshape(-1, 3)


def _mask_shape(series_slice, slices: int):
    return (int(series_slice.Rows), int(series_slice.Columns), slices)


def test_fixture_is_non_square(one_slice_series_path):
    """A square series hides every axis-order mistake in this file."""
    _, reference = _reference(one_slice_series_path)

    assert int(reference.Rows) != int(reference.Columns)


def test_single_voxel_is_written_where_dicom_says_it_belongs(one_slice_series_path):
    """mask[row, column, slice] must land at the patient coordinate of that voxel.

    With the axes swapped the contour comes out 30 mm away on this fixture,
    which is the transposed position rather than anything subtly off.
    """
    rtstruct, reference = _reference(one_slice_series_path)
    row, column = 3, 10

    mask = np.zeros(_mask_shape(reference, 1), dtype=bool)
    mask[row, column, 0] = True
    rtstruct.add_roi(mask=mask, name="one_voxel")

    centroid = _only_contour(rtstruct).mean(axis=0)
    expected = _patient_coordinate(reference, column=column, row=row)

    assert np.allclose(centroid, expected, atol=1e-3), (
        f"voxel [row={row}, column={column}] was written to {centroid}, "
        f"but DICOM places it at {expected}; the transposed voxel sits at "
        f"{_patient_coordinate(reference, column=row, row=column)}"
    )


@pytest.mark.parametrize(
    "axis, orientation_slice, description",
    [
        (0, slice(3, 6), "down a column"),
        (1, slice(0, 3), "along a row"),
    ],
)
def test_each_mask_axis_follows_its_patient_direction(
    one_slice_series_path, axis, orientation_slice, description
):
    """Axis 0 must run down a column, axis 1 along a row.

    Checked as a direction rather than a coordinate, so it holds independently
    of the origin and of the test above.
    """
    rtstruct, reference = _reference(one_slice_series_path)
    expected_direction = np.array(
        [float(v) for v in reference.ImageOrientationPatient]
    )[orientation_slice]

    mask = np.zeros(_mask_shape(reference, 1), dtype=bool)
    index = [5, 5, 0]
    index[axis] = slice(None)
    mask[tuple(index)] = True
    rtstruct.add_roi(mask=mask, name="stripe", contour_mode="voxel_center")

    points = _only_contour(rtstruct)
    # The long axis of the stripe, as the principal direction of its points.
    # A bounding box would lose the sign of each component and so could not
    # distinguish directions that differ only in sign.
    centred = points - points.mean(axis=0)
    direction = np.linalg.svd(centred, full_matrices=False)[2][0]

    assert abs(float(direction @ expected_direction)) > 0.99, (
        f"a stripe varying mask axis {axis} should run {description}, "
        f"but runs along {direction}"
    )


def test_mask_matching_the_pixel_array_layout_is_accepted(one_slice_series_path):
    """A mask shaped like the images it was drawn on must be accepted.

    (Rows, Columns) is the shape pydicom returns from ``pixel_array``, so it
    is the shape of any mask produced by segmenting the series. Rejecting it
    sends the caller to transpose, which places the ROI incorrectly.
    """
    rtstruct, reference = _reference(one_slice_series_path)

    mask = np.zeros(_mask_shape(reference, 1), dtype=bool)
    mask[10:20, 10:20, 0] = True
    rtstruct.add_roi(mask=mask, name="ok")

    assert rtstruct.get_roi_names() == ["ok"]


def test_transposed_mask_is_rejected(one_slice_series_path):
    """The transpose must fail loudly rather than be silently mangled."""
    rtstruct, reference = _reference(one_slice_series_path)
    rows, columns = int(reference.Rows), int(reference.Columns)

    transposed = np.zeros((columns, rows, 1), dtype=bool)
    transposed[10:20, 10:20, 0] = True

    with pytest.raises(Exception, match="in-plane dimensions"):
        rtstruct.add_roi(mask=transposed, name="transposed")


def test_roi_in_the_far_columns_survives_a_round_trip(one_slice_series_path):
    """An ROI beyond column ``Rows`` must not disappear when read back.

    The read path allocated its mask as (Columns, Rows) while filling it with
    (row, column) indices. On a non-square series every column index past
    ``Rows`` then fell outside the array and was dropped, so an ROI in the
    right-hand part of the image came back empty, with no error.
    """
    rtstruct, reference = _reference(one_slice_series_path)
    rows, columns = int(reference.Rows), int(reference.Columns)
    assert columns > rows, "this fixture must be wider than it is tall"

    first_column = rows + 20
    mask = np.zeros(_mask_shape(reference, 1), dtype=bool)
    mask[5:15, first_column : first_column + 10, 0] = True
    rtstruct.add_roi(mask=mask, name="far_right")

    loaded = rtstruct.get_roi_mask_by_name("far_right")

    assert loaded.shape == mask.shape
    assert loaded.sum() > 0, "the ROI was lost entirely on the way back"
    assert np.array_equal(loaded, mask)


def test_loaded_mask_is_shaped_like_the_images(one_slice_series_path):
    """get_roi_mask_by_name must return (Rows, Columns, Slices)."""
    rtstruct, reference = _reference(one_slice_series_path)

    mask = np.zeros(_mask_shape(reference, 1), dtype=bool)
    mask[5:15, 5:15, 0] = True
    rtstruct.add_roi(mask=mask, name="roi")

    loaded = rtstruct.get_roi_mask_by_name("roi")

    assert loaded.shape == (int(reference.Rows), int(reference.Columns), 1)


# --- pin holes --------------------------------------------------------------
#
# draw_line_upwards_from_point sampled the mask as mask[(x, y)] while cv.line
# wrote to it as (x, y) = (column, row), so it tested the transposed pixel.
# A mask symmetric about y = x is unaffected, which is what every existing
# pin hole test used, so the defect was invisible. This is #115.


def _ring(rtstruct, symmetric: bool) -> np.ndarray:
    reference = rtstruct.series_data[0]
    rows, columns = int(reference.Rows), int(reference.Columns)
    mask = np.zeros((rows, columns, len(rtstruct.series_data)), dtype=bool)
    row_axis, column_axis = np.ogrid[:rows, :columns]

    if symmetric:
        distance = (row_axis - rows // 2) ** 2 + (column_axis - columns // 2) ** 2
        plane = (distance <= 80**2) & (distance >= 40**2)
    else:
        centre_row, centre_column = rows // 3, columns * 2 // 3
        outer = ((row_axis - centre_row) / 60.0) ** 2 + (
            (column_axis - centre_column) / 25.0
        ) ** 2 <= 1
        inner = ((row_axis - centre_row) / 25.0) ** 2 + (
            (column_axis - centre_column) / 10.0
        ) ** 2 <= 1
        plane = outer & ~inner

    mask[:, :, 0] = plane
    return mask


@pytest.mark.parametrize("symmetric", [True, False], ids=["symmetric", "asymmetric"])
def test_pin_hole_produces_a_single_contour(series_path, symmetric):
    """use_pin_hole must reduce a region with a hole to one contour.

    That is the entire purpose of the option: it cuts a channel from the hole
    out to the boundary so the region needs no nested contour, for consumers
    that cannot read them.

    The asymmetric case is the regression. With the transposed lookup the
    channel was never cut, the hole stayed a separate contour, and two were
    written while the caller had asked for one. No exception was raised, and
    the symmetric case kept passing throughout.
    """
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    mask = _ring(rtstruct, symmetric)

    rtstruct.add_roi(mask=mask, name="ring", use_pin_hole=True)

    contours = rtstruct.ds.ROIContourSequence[0].ContourSequence
    assert len(contours) == 1, (
        f"expected one contour after cutting a pin hole, got {len(contours)}; "
        "the hole was left as a nested contour"
    )
