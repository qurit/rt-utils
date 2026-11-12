"""Working with DICOM data already in memory, rather than paths on disk.

``RTStructBuilder.create_new`` and ``create_from`` accept either a path or
pydicom objects, and ``RTStruct.save_to_memory`` returns a buffer instead of
writing a file. Together these let a caller read, modify and hand on an
RTStruct without touching the filesystem.
"""

import numpy as np
import pydicom
import pytest

from rt_utils import RTStructBuilder
from rt_utils.rtstruct import RTStruct


def _mask_for(rtstruct: RTStruct) -> np.ndarray:
    ref = rtstruct.series_data[0]
    dims = (int(ref.Rows), int(ref.Columns), len(rtstruct.series_data))
    mask = np.zeros(dims, dtype=bool)
    mask[50:100, 50:100, 0] = True
    return mask


# --- input: a series already in memory --------------------------------------


@pytest.mark.parametrize("series_fixture", ["series_path", "series_datasets"])
def test_create_new_accepts_path_or_datasets(series_fixture, request):
    rtstruct = RTStructBuilder.create_new(request.getfixturevalue(series_fixture))

    assert len(rtstruct.series_data) > 0
    assert (
        len(rtstruct.ds.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence)
        != 0
    )


def test_path_and_datasets_produce_the_same_series(series_path, series_datasets):
    """Both input forms must yield the same slices in the same order."""
    from_path = RTStructBuilder.create_new(series_path)
    from_memory = RTStructBuilder.create_new(series_datasets)

    assert len(from_path.series_data) == len(from_memory.series_data)
    assert [ds.SOPInstanceUID for ds in from_path.series_data] == [
        ds.SOPInstanceUID for ds in from_memory.series_data
    ]


def test_unsorted_datasets_are_sorted_by_slice_position(series_path, series_datasets):
    """Order of the supplied list must not matter.

    Slices are sorted by spatial position, the same key used when reading from
    disk. Sorting by InstanceNumber instead would not be equivalent, and an
    out-of-order series silently produces masks on the wrong slices.
    """
    expected = [
        ds.SOPInstanceUID for ds in RTStructBuilder.create_new(series_path).series_data
    ]

    reversed_input = list(reversed(series_datasets))
    rtstruct = RTStructBuilder.create_new(reversed_input)

    assert [ds.SOPInstanceUID for ds in rtstruct.series_data] == expected


def test_caller_list_is_not_reordered(series_datasets):
    """Passing a list must not reorder it under the caller."""
    supplied = list(reversed(series_datasets))
    before = [ds.SOPInstanceUID for ds in supplied]

    RTStructBuilder.create_new(supplied)

    assert [ds.SOPInstanceUID for ds in supplied] == before


def test_mask_round_trips_through_in_memory_series(series_datasets):
    rtstruct = RTStructBuilder.create_new(series_datasets)
    mask = _mask_for(rtstruct)
    rtstruct.add_roi(mask=mask, name="in-memory")

    assert np.array_equal(rtstruct.get_roi_mask_by_name("in-memory"), mask)


# --- input: an existing RTStruct already in memory --------------------------


@pytest.mark.parametrize("series_fixture", ["series_path", "series_datasets"])
def test_create_from_accepts_path_or_datasets(series_fixture, rtstruct_path, request):
    rtstruct = RTStructBuilder.create_from(
        request.getfixturevalue(series_fixture), rtstruct_path
    )

    assert hasattr(rtstruct.ds, "ROIContourSequence")
    assert hasattr(rtstruct.ds, "StructureSetROISequence")


def test_create_from_accepts_an_in_memory_rtstruct(series_datasets, rtstruct_path):
    """The RTStruct itself may be a Dataset rather than a path."""
    existing = pydicom.dcmread(rtstruct_path)

    rtstruct = RTStructBuilder.create_from(series_datasets, existing)

    assert (
        rtstruct.get_roi_names()
        == RTStructBuilder.create_from(series_datasets, rtstruct_path).get_roi_names()
    )


def test_create_from_still_validates_an_in_memory_rtstruct(series_datasets):
    """Validation must not be skipped just because the input is a Dataset."""
    not_an_rtstruct = pydicom.Dataset()

    with pytest.raises(Exception):
        RTStructBuilder.create_from(series_datasets, not_an_rtstruct)


# --- output: saving without touching the filesystem -------------------------


def test_save_to_memory_returns_a_readable_buffer(series_datasets):
    rtstruct = RTStructBuilder.create_new(series_datasets)
    rtstruct.add_roi(mask=_mask_for(rtstruct), name="buffered")

    buffer = rtstruct.save_to_memory()

    assert buffer.tell() == 0, "buffer should be rewound ready for reading"
    reloaded = pydicom.dcmread(buffer)
    assert [roi.ROIName for roi in reloaded.StructureSetROISequence] == ["buffered"]


def test_save_to_memory_round_trips_a_mask(series_datasets):
    """A buffer written in memory must reload into the same mask."""
    rtstruct = RTStructBuilder.create_new(series_datasets)
    mask = _mask_for(rtstruct)
    rtstruct.add_roi(mask=mask, name="buffered")

    buffer = rtstruct.save_to_memory()
    reloaded = RTStructBuilder.create_from(series_datasets, pydicom.dcmread(buffer))

    assert np.array_equal(reloaded.get_roi_mask_by_name("buffered"), mask)
