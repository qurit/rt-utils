"""Filtering get_roi_names by ContourGeometricType."""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils.rtstruct import RTStruct


def _block(rtstruct: RTStruct, offset: int = 50) -> np.ndarray:
    ref = rtstruct.series_data[0]
    dims = (int(ref.Columns), int(ref.Rows), len(rtstruct.series_data))
    mask = np.zeros(dims, dtype=bool)
    mask[offset : offset + 50, offset : offset + 50, 0] = True
    return mask


def _single_voxel(rtstruct: RTStruct, slice_index: int = 0) -> np.ndarray:
    ref = rtstruct.series_data[0]
    dims = (int(ref.Columns), int(ref.Rows), len(rtstruct.series_data))
    mask = np.zeros(dims, dtype=bool)
    mask[200, 200, slice_index] = True
    return mask


def test_default_returns_every_roi(new_rtstruct: RTStruct):
    new_rtstruct.add_roi(mask=_block(new_rtstruct), name="a")
    new_rtstruct.add_roi(mask=_block(new_rtstruct, 150), name="b")

    assert new_rtstruct.get_roi_names() == ["a", "b"]
    assert new_rtstruct.get_roi_names(geometry="ALL") == ["a", "b"]


def test_filters_to_a_single_geometric_type(new_rtstruct: RTStruct):
    """A single-voxel ROI writes a POINT in voxel_center mode."""
    new_rtstruct.add_roi(
        mask=_block(new_rtstruct), name="planar", contour_mode="voxel_center"
    )
    new_rtstruct.add_roi(
        mask=_single_voxel(new_rtstruct), name="point", contour_mode="voxel_center"
    )

    assert new_rtstruct.get_roi_names(geometry="POINT") == ["point"]
    assert new_rtstruct.get_roi_names(geometry="CLOSED_PLANAR") == ["planar"]


def test_an_roi_mixing_types_matches_either(new_rtstruct: RTStruct):
    """Contours of one ROI can differ in type between slices.

    Classifying an ROI by its first contour alone would hide it from a
    filter it genuinely matches.
    """
    ref = new_rtstruct.series_data[0]
    dims = (int(ref.Columns), int(ref.Rows), len(new_rtstruct.series_data))
    mask = np.zeros(dims, dtype=bool)
    mask[50:100, 50:100, 0] = True  # a planar region
    mask[200, 200, 1] = True  # a single voxel on the next slice

    new_rtstruct.add_roi(mask=mask, name="mixed", contour_mode="voxel_center")

    types = [
        contour.ContourGeometricType
        for contour in new_rtstruct.ds.ROIContourSequence[0].ContourSequence
    ]
    assert "CLOSED_PLANAR" in types and "POINT" in types

    assert new_rtstruct.get_roi_names(geometry="CLOSED_PLANAR") == ["mixed"]
    assert new_rtstruct.get_roi_names(geometry="POINT") == ["mixed"]


def test_geometry_is_matched_by_roi_number_not_position(new_rtstruct: RTStruct):
    """The two sequences need not be in the same order.

    ROIContourSequence is tied to StructureSetROISequence through
    ReferencedROINumber, so pairing them by index can attribute one ROI's
    geometry to another.
    """
    new_rtstruct.add_roi(
        mask=_block(new_rtstruct), name="planar", contour_mode="voxel_center"
    )
    new_rtstruct.add_roi(
        mask=_single_voxel(new_rtstruct), name="point", contour_mode="voxel_center"
    )

    # Reverse one sequence only, as a real-world file may well have them.
    new_rtstruct.ds.ROIContourSequence.reverse()

    assert new_rtstruct.get_roi_names(geometry="POINT") == ["point"]
    assert new_rtstruct.get_roi_names(geometry="CLOSED_PLANAR") == ["planar"]


def test_no_match_returns_an_empty_list(new_rtstruct: RTStruct):
    new_rtstruct.add_roi(
        mask=_block(new_rtstruct), name="planar", contour_mode="voxel_center"
    )

    assert new_rtstruct.get_roi_names(geometry="OPEN_NONPLANAR") == []


def test_unknown_geometry_raises(new_rtstruct: RTStruct):
    """A typo must not silently look like 'no ROIs of that type'."""
    new_rtstruct.add_roi(mask=_block(new_rtstruct), name="planar")

    with pytest.raises(ValueError, match="Unrecognised geometric type"):
        new_rtstruct.get_roi_names(geometry="CLOSED PLANAR")


def test_empty_structure_set_returns_empty(new_rtstruct: RTStruct):
    assert new_rtstruct.get_roi_names() == []
    assert new_rtstruct.get_roi_names(geometry="POINT") == []
