"""Removing an ROI from a structure set.

``add_roi`` had no inverse, so the only way to drop a structure was to edit
three pydicom sequences by hand and keep their ROINumbers consistent. This is
#46.

An ROI is spread across StructureSetROISequence (its name),
ROIContourSequence (its geometry) and RTROIObservationsSequence (its
interpretation), joined by ROINumber. Removing it means removing all three:
leaving any behind produces a structure set that viewers read
inconsistently, with contours belonging to an ROI that has no name, or a
name with nothing to draw.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils.rtstruct import RTStruct
from tests.conftest import build_series


def _rtstruct_with(*names):
    rtstruct = RTStructBuilder.create_new(build_series([0.0, 2.0], rows=32, columns=32))
    for index, name in enumerate(names):
        mask = np.zeros((32, 32, 2), dtype=bool)
        mask[5 + index : 12 + index, 5 + index : 12 + index, 0] = True
        rtstruct.add_roi(mask=mask, name=name)
    return rtstruct


def _sequence_lengths(rtstruct):
    return (
        len(rtstruct.ds.StructureSetROISequence),
        len(rtstruct.ds.ROIContourSequence),
        len(rtstruct.ds.RTROIObservationsSequence),
    )


def test_deleting_an_roi_removes_it_from_the_names():
    rtstruct = _rtstruct_with("liver", "spleen", "kidney")

    rtstruct.delete_roi("spleen")

    assert rtstruct.get_roi_names() == ["liver", "kidney"]


def test_all_three_sequences_are_kept_in_step():
    """A leftover entry in any one of them is a malformed structure set."""
    rtstruct = _rtstruct_with("liver", "spleen", "kidney")
    assert _sequence_lengths(rtstruct) == (3, 3, 3)

    rtstruct.delete_roi("spleen")

    assert _sequence_lengths(rtstruct) == (2, 2, 2)


def test_the_surviving_rois_keep_their_geometry():
    """Removing one must not disturb the others' contours."""
    rtstruct = _rtstruct_with("liver", "spleen", "kidney")
    before = {name: rtstruct.get_roi_mask_by_name(name) for name in ("liver", "kidney")}

    rtstruct.delete_roi("spleen")

    for name, mask in before.items():
        assert np.array_equal(rtstruct.get_roi_mask_by_name(name), mask)


def test_the_deleted_roi_can_no_longer_be_read():
    rtstruct = _rtstruct_with("liver", "spleen")

    rtstruct.delete_roi("spleen")

    with pytest.raises(RTStruct.ROIException, match="does not exist"):
        rtstruct.get_roi_mask_by_name("spleen")


def test_deleting_something_absent_raises():
    rtstruct = _rtstruct_with("liver")

    with pytest.raises(RTStruct.ROIException, match="does not exist"):
        rtstruct.delete_roi("pancreas")


def test_numbering_is_not_closed_up_after_a_delete():
    """ROINumber joins the three sequences, so survivors must keep theirs.

    Renumbering to close the gap would silently re-point every reference.
    """
    rtstruct = _rtstruct_with("liver", "spleen", "kidney")
    numbers = {
        roi.ROIName: int(roi.ROINumber) for roi in rtstruct.ds.StructureSetROISequence
    }

    rtstruct.delete_roi("spleen")

    after = {
        roi.ROIName: int(roi.ROINumber) for roi in rtstruct.ds.StructureSetROISequence
    }
    assert after == {"liver": numbers["liver"], "kidney": numbers["kidney"]}


def test_a_new_roi_after_a_delete_does_not_reuse_the_number():
    """The freed number must not collide with the contours still using it.

    Counting the sequence would hand out kidney's number again.
    """
    rtstruct = _rtstruct_with("liver", "spleen", "kidney")
    rtstruct.delete_roi("spleen")

    mask = np.zeros((32, 32, 2), dtype=bool)
    mask[20:28, 20:28, 1] = True
    rtstruct.add_roi(mask=mask, name="stomach")

    numbers = [int(roi.ROINumber) for roi in rtstruct.ds.StructureSetROISequence]
    assert len(numbers) == len(set(numbers)), f"duplicate ROINumber in {numbers}"
    assert np.array_equal(rtstruct.get_roi_mask_by_name("stomach"), mask)


def test_case_insensitive_deletion_is_available():
    rtstruct = _rtstruct_with("Liver")

    rtstruct.delete_roi("liver", case_sensitive=False)

    assert rtstruct.get_roi_names() == []


def test_case_sensitivity_is_the_default():
    """Names differing only in case are distinct structures."""
    rtstruct = _rtstruct_with("Liver")

    with pytest.raises(RTStruct.ROIException):
        rtstruct.delete_roi("liver")


def test_a_deleted_roi_stays_gone_through_a_save_and_reload(tmp_path):
    """The edit has to survive being written out, not just live in memory."""
    series = build_series([0.0, 2.0], rows=32, columns=32)
    rtstruct = RTStructBuilder.create_new(series)
    for name in ("liver", "spleen"):
        mask = np.zeros((32, 32, 2), dtype=bool)
        mask[5:12, 5:12, 0] = True
        rtstruct.add_roi(mask=mask, name=name)

    rtstruct.delete_roi("spleen")
    destination = str(tmp_path / "rt.dcm")
    rtstruct.save(destination)

    reloaded = RTStructBuilder.create_from(series, destination)
    assert reloaded.get_roi_names() == ["liver"]
    assert _sequence_lengths(reloaded) == (1, 1, 1)
