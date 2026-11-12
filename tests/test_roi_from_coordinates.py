"""Adding an ROI from contours given as patient-space coordinates.

``add_roi_from_coordinates`` writes the supplied contours directly, rather
than deriving them from a rasterised mask, so it is the route to take when
the geometry is already known in millimetres.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils.rtstruct import RTStruct
from rt_utils import ds_helper, image_helper


def _square_at(z: float, size: float = 25.0):
    """An axis-aligned square contour on the plane z."""
    return [
        [-size, -size, z],
        [-size, size, z],
        [size, size, z],
        [size, -size, z],
    ]


def _slice_positions(rtstruct: RTStruct):
    return [image_helper.get_slice_position(s) for s in rtstruct.series_data]


def test_add_roi_from_coordinates_populates_the_sequences(new_rtstruct: RTStruct):
    assert new_rtstruct.get_roi_names() == []

    name = "from-coordinates"
    color = [123, 123, 232]
    z_positions = _slice_positions(new_rtstruct)
    coordinates = [_square_at(z) for z in z_positions]

    new_rtstruct.add_roi_from_coordinates(coordinates, color=color, name=name)

    assert len(new_rtstruct.ds.ROIContourSequence) == 1
    assert len(new_rtstruct.ds.ROIContourSequence[0].ContourSequence) == len(
        coordinates
    )
    assert len(new_rtstruct.ds.StructureSetROISequence) == 1
    assert len(new_rtstruct.ds.RTROIObservationsSequence) == 1
    assert new_rtstruct.ds.ROIContourSequence[0].ROIDisplayColor == color
    assert new_rtstruct.get_roi_names() == [name]


def test_contour_data_matches_the_given_coordinates(new_rtstruct: RTStruct):
    """The points must be written through unchanged, just flattened."""
    z = _slice_positions(new_rtstruct)[0]
    square = _square_at(z)

    new_rtstruct.add_roi_from_coordinates([square], name="square")

    contour = new_rtstruct.ds.ROIContourSequence[0].ContourSequence[0]
    expected = [coordinate for point in square for coordinate in point]

    assert int(contour.NumberOfContourPoints) == len(square)
    assert [float(value) for value in contour.ContourData] == pytest.approx(expected)


def test_each_contour_attaches_to_the_nearest_slice(new_rtstruct: RTStruct):
    """A contour must land on the slice closest to its own position."""
    positions = _slice_positions(new_rtstruct)
    assert len(positions) >= 2, "fixture needs at least two slices"

    # Offset each contour slightly so it does not sit exactly on a slice.
    coordinates = [_square_at(position + 0.1) for position in positions]

    new_rtstruct.add_roi_from_coordinates(coordinates, name="nearest")

    referenced = [
        contour.ContourImageSequence[0].ReferencedSOPInstanceUID
        for contour in new_rtstruct.ds.ROIContourSequence[0].ContourSequence
    ]
    expected = [s.SOPInstanceUID for s in new_rtstruct.series_data]

    assert referenced == expected


def test_roi_number_does_not_collide(new_rtstruct: RTStruct):
    """Must use the same numbering rule as add_roi.

    Deriving the number from len(StructureSetROISequence) reuses one that is
    still in use when an ROI was deleted elsewhere.
    """
    z = _slice_positions(new_rtstruct)[0]
    for name in ["A", "B", "C"]:
        new_rtstruct.add_roi_from_coordinates([_square_at(z)], name=name)

    del new_rtstruct.ds.StructureSetROISequence[1]
    del new_rtstruct.ds.ROIContourSequence[1]

    new_rtstruct.add_roi_from_coordinates([_square_at(z)], name="D")

    numbers = [int(r.ROINumber) for r in new_rtstruct.ds.StructureSetROISequence]
    assert len(numbers) == len(set(numbers)), f"duplicate ROINumber: {numbers}"


def test_mixing_with_add_roi_keeps_numbers_unique(new_rtstruct: RTStruct):
    """Both entry points share one numbering sequence."""
    ref = new_rtstruct.series_data[0]
    mask = np.zeros(
        (int(ref.Rows), int(ref.Columns), len(new_rtstruct.series_data)), dtype=bool
    )
    mask[50:100, 50:100, 0] = True

    new_rtstruct.add_roi(mask=mask, name="from-mask")
    new_rtstruct.add_roi_from_coordinates(
        [_square_at(_slice_positions(new_rtstruct)[0])], name="from-coords"
    )

    numbers = [int(r.ROINumber) for r in new_rtstruct.ds.StructureSetROISequence]
    assert numbers == [1, 2]
    assert new_rtstruct.get_roi_names() == ["from-mask", "from-coords"]


def test_empty_contour_is_rejected(new_rtstruct: RTStruct):
    with pytest.raises(ValueError):
        new_rtstruct.add_roi_from_coordinates([[]], name="empty")


def test_nearest_slice_is_orientation_aware(oriented_rtstruct: RTStruct):
    """Slice matching must project along the slice normal, not along z.

    The oriented fixture is not axial, so comparing raw z would pick the wrong
    slice.
    """
    positions = _slice_positions(oriented_rtstruct)
    _, _, normal = image_helper.get_slice_directions(oriented_rtstruct.series_data[0])

    for expected_slice, position in zip(oriented_rtstruct.series_data, positions):
        # Build a point that sits on this slice's plane.
        point = (np.asarray(normal, dtype=float) * position).tolist()
        chosen = ds_helper.find_closest_slice(oriented_rtstruct.series_data, point)

        assert chosen.SOPInstanceUID == expected_slice.SOPInstanceUID


# --- polygons given on the image grid --------------------------------------


def test_pixel_polygon_lands_where_it_was_drawn(new_rtstruct: RTStruct, series_path):
    """A polygon in pixel coordinates must rasterise back to its own extent."""
    polygon = [[60, 50, 0], [120, 50, 0], [120, 100, 0], [60, 100, 0]]

    new_rtstruct.add_roi_from_coordinates(
        [polygon], name="pixels", coordinate_space="pixel"
    )

    mask = new_rtstruct.get_roi_mask_by_name("pixels")
    filled = np.argwhere(mask[:, :, 0])

    # Inclusive of both bounds: 61 columns by 51 rows.
    assert int(mask.sum()) == 61 * 51
    assert filled[:, 0].min() == 50 and filled[:, 0].max() == 100
    assert filled[:, 1].min() == 60 and filled[:, 1].max() == 120


def test_pixel_and_patient_spaces_agree(new_rtstruct: RTStruct, series_path):
    """The same polygon expressed either way must produce the same contour."""
    pixel_polygon = [[60, 50, 0], [120, 50, 0], [120, 100, 0], [60, 100, 0]]
    patient_polygon = image_helper.pixel_polygons_to_patient_coordinates(
        [pixel_polygon], new_rtstruct.series_data
    )[0]

    from_pixels = RTStructBuilder.create_new(dicom_series_path=series_path)
    from_pixels.add_roi_from_coordinates(
        [pixel_polygon], name="roi", coordinate_space="pixel"
    )
    from_patient = RTStructBuilder.create_new(dicom_series_path=series_path)
    from_patient.add_roi_from_coordinates([patient_polygon], name="roi")

    assert np.array_equal(
        from_pixels.get_roi_mask_by_name("roi"),
        from_patient.get_roi_mask_by_name("roi"),
    )


def test_pixel_polygon_spanning_slices_is_rejected(new_rtstruct: RTStruct):
    with pytest.raises(ValueError, match="one slice"):
        new_rtstruct.add_roi_from_coordinates(
            [[[60, 50, 0], [120, 50, 1]]], name="bad", coordinate_space="pixel"
        )


def test_pixel_polygon_outside_the_series_is_rejected(new_rtstruct: RTStruct):
    outside = len(new_rtstruct.series_data) + 5
    with pytest.raises(ValueError, match="outside the series"):
        new_rtstruct.add_roi_from_coordinates(
            [[[60, 50, outside], [120, 50, outside], [120, 100, outside]]],
            name="bad",
            coordinate_space="pixel",
        )


def test_unknown_coordinate_space_is_rejected(new_rtstruct: RTStruct):
    with pytest.raises(ValueError, match="Invalid coordinate space"):
        new_rtstruct.add_roi_from_coordinates(
            [[[0, 0, 0]]], name="bad", coordinate_space="world"
        )
