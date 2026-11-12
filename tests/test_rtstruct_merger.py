"""Merging two structure sets for one series.

``RTStructMerger`` had no tests at all, which is #72. Writing them found two
bugs, one of which meant the duplicate-name path had never run successfully.
"""

import os

import numpy as np
import pytest

from rt_utils import RTStructBuilder, RTStructMerger
from tests.conftest import build_series, save_dataset

ROWS = COLUMNS = 32
SLICES = 2


@pytest.fixture()
def series_dir(tmp_path):
    series = build_series([0.0, 2.0], rows=ROWS, columns=COLUMNS)
    directory = tmp_path / "series"
    directory.mkdir()
    for index, ds in enumerate(series):
        save_dataset(ds, os.path.join(directory, f"s{index:03}.dcm"))
    return str(directory)


def _mask(offset: int) -> np.ndarray:
    """A distinguishable block, so each ROI's geometry can be told apart."""
    mask = np.zeros((ROWS, COLUMNS, SLICES), dtype=bool)
    mask[5 + offset : 10 + offset, 5:10, 0] = True
    return mask


def _structure_set(series_dir, tmp_path, filename, names):
    rtstruct = RTStructBuilder.create_new(series_dir)
    masks = {}
    for offset, name in enumerate(names):
        masks[name] = _mask(offset)
        rtstruct.add_roi(mask=masks[name], name=name)
    path = str(tmp_path / filename)
    rtstruct.save(path)
    return path, masks


def test_every_roi_from_both_sets_is_present(series_dir, tmp_path):
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver", "spleen"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["kidney"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    assert sorted(merged.get_roi_names()) == ["kidney", "liver", "spleen"]


def test_the_geometry_of_each_roi_survives(series_dir, tmp_path):
    """Names alone would pass even if the contours were attached wrongly."""
    first, first_masks = _structure_set(
        series_dir, tmp_path, "a.dcm", ["liver", "spleen"]
    )
    second, second_masks = _structure_set(series_dir, tmp_path, "b.dcm", ["kidney"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    for name, mask in {**first_masks, **second_masks}.items():
        assert np.array_equal(merged.get_roi_mask_by_name(name), mask), name


def test_roi_numbers_stay_unique(series_dir, tmp_path):
    """ROINumber joins the three sequences; a duplicate merges two ROIs."""
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver", "spleen"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["kidney", "stomach"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    numbers = [int(roi.ROINumber) for roi in merged.ds.StructureSetROISequence]
    assert len(numbers) == len(set(numbers)), numbers


def test_the_three_sequences_stay_in_step(series_dir, tmp_path):
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver", "spleen"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["kidney"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    assert (
        len(merged.ds.StructureSetROISequence)
        == len(merged.ds.ROIContourSequence)
        == len(merged.ds.RTROIObservationsSequence)
        == 3
    )


def test_every_contour_points_at_an_roi_that_exists(series_dir, tmp_path):
    """A dangling ReferencedROINumber is a malformed structure set."""
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver", "spleen"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["kidney"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    defined = {int(roi.ROINumber) for roi in merged.ds.StructureSetROISequence}
    referenced = {
        int(roi.ReferencedROINumber) for roi in merged.ds.ROIContourSequence
    } | {int(obs.ReferencedROINumber) for obs in merged.ds.RTROIObservationsSequence}
    assert referenced == defined


def test_a_duplicate_name_is_renamed(series_dir, tmp_path):
    """Two sets for one series routinely name the same organ the same way.

    This path previously raised: it did `struct_set_roi_seq += "_2"`, adding
    a string to a Dataset rather than to its ROIName, so it had never run
    successfully.
    """
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["liver"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    assert sorted(merged.get_roi_names()) == ["liver", "liver_2"]


def test_both_structures_are_still_readable_after_a_rename(series_dir, tmp_path):
    """Renaming must not detach a structure from its contours."""
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["liver"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)

    for name in ("liver", "liver_2"):
        assert merged.get_roi_mask_by_name(name).sum() > 0, name


def test_a_third_set_does_not_produce_a_second_liver_2(series_dir, tmp_path):
    """Suffixes count upward rather than always appending _2."""
    first, _ = _structure_set(series_dir, tmp_path, "a.dcm", ["liver"])
    second, _ = _structure_set(series_dir, tmp_path, "b.dcm", ["liver"])
    merged_path = str(tmp_path / "merged.dcm")
    RTStructMerger.merge_rtstructs(series_dir, first, second).save(merged_path)

    third, _ = _structure_set(series_dir, tmp_path, "c.dcm", ["liver"])
    merged = RTStructMerger.merge_rtstructs(series_dir, third, merged_path)

    names = sorted(merged.get_roi_names())
    assert names == ["liver", "liver_2", "liver_3"], names


def test_the_merged_set_survives_a_save_and_reload(series_dir, tmp_path):
    first, first_masks = _structure_set(series_dir, tmp_path, "a.dcm", ["liver"])
    second, second_masks = _structure_set(series_dir, tmp_path, "b.dcm", ["kidney"])

    merged = RTStructMerger.merge_rtstructs(series_dir, first, second)
    destination = str(tmp_path / "merged.dcm")
    merged.save(destination)

    reloaded = RTStructBuilder.create_from(series_dir, destination)
    assert sorted(reloaded.get_roi_names()) == ["kidney", "liver"]
    for name, mask in {**first_masks, **second_masks}.items():
        assert np.array_equal(reloaded.get_roi_mask_by_name(name), mask), name
