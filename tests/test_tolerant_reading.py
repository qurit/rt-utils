"""Reading a directory that holds more than a clean image series.

Two things went wrong when a folder was not exactly a set of conformant
image slices:

* a file carrying pixel data but no ImageOrientationPatient — a secondary
  capture, a screenshot, a report — was taken for a slice and failed later
  with ``'FileDataset' object has no attribute 'ImageOrientationPatient'``;
* files written without the standard preamble or file meta, which some
  equipment and some anonymisation tools produce, could not be read at all.

This is #39.
"""

import os

import numpy as np
import pydicom
import pytest

from rt_utils import RTStructBuilder, image_helper
from tests.conftest import build_series, save_dataset


def _write(series, directory):
    for index, ds in enumerate(series):
        save_dataset(ds, os.path.join(directory, f"slice{index:03}.dcm"))


def test_an_image_without_orientation_is_not_part_of_the_series(tmp_path):
    """A secondary capture beside the images must be skipped, not stacked."""
    series = build_series([0.0, 2.0, 4.0])
    _write(series, tmp_path)

    capture = build_series([0.0])[0]
    del capture.ImageOrientationPatient
    capture.SOPInstanceUID = pydicom.uid.generate_uid()
    save_dataset(capture, os.path.join(tmp_path, "capture.dcm"))

    loaded = image_helper.load_sorted_image_series(str(tmp_path))

    assert len(loaded) == 3
    assert all(hasattr(s, "ImageOrientationPatient") for s in loaded)


def test_a_folder_of_only_unplaceable_images_says_so(tmp_path):
    """Returning nothing would be reported as 'No DICOM Images found'."""
    capture = build_series([0.0])[0]
    del capture.ImageOrientationPatient
    save_dataset(capture, os.path.join(tmp_path, "capture.dcm"))

    with pytest.raises(Exception) as error:
        image_helper.load_sorted_image_series(str(tmp_path))

    message = str(error.value)
    assert "Image Orientation" in message
    assert "1 image(s)" in message


def test_a_slice_missing_its_position_still_raises_rather_than_vanishing(tmp_path):
    """ImagePositionPatient is not used to filter.

    Dropping such a slice would quietly shorten the series. It must keep
    raising the explanation from require_image_position_patient instead.
    """
    series = build_series([0.0, 2.0])
    del series[1].ImagePositionPatient
    _write(series, tmp_path)

    with pytest.raises(AttributeError, match="ImagePositionPatient"):
        image_helper.load_sorted_image_series(str(tmp_path))


def test_files_without_file_meta_need_force(tmp_path):
    """Non-conformant files are unreadable by default and readable with force."""
    series = build_series([0.0, 2.0, 4.0])
    for index, ds in enumerate(series):
        # Written with no preamble and no file meta, as some equipment does.
        del ds.file_meta
        save_dataset(
            ds, os.path.join(tmp_path, f"raw{index:03}.dcm"), with_file_meta=False
        )

    with pytest.raises(Exception, match="No DICOM Images found"):
        image_helper.load_sorted_image_series(str(tmp_path))

    loaded = image_helper.load_sorted_image_series(str(tmp_path), force=True)
    assert len(loaded) == 3


def test_force_reaches_the_builder(tmp_path):
    """The parameter is only useful if callers can pass it."""
    series = build_series([0.0, 2.0, 4.0])
    for index, ds in enumerate(series):
        del ds.file_meta
        save_dataset(
            ds, os.path.join(tmp_path, f"raw{index:03}.dcm"), with_file_meta=False
        )

    rtstruct = RTStructBuilder.create_new(str(tmp_path), force=True)

    mask = np.zeros((32, 32, 3), dtype=bool)
    mask[10:20, 10:20, :] = True
    rtstruct.add_roi(mask=mask, name="roi")

    assert np.array_equal(rtstruct.get_roi_mask_by_name("roi"), mask)


def test_force_is_off_by_default(tmp_path):
    """Unrelated files must not be parsed as DICOM unless asked for."""
    series = build_series([0.0, 2.0])
    _write(series, tmp_path)
    (tmp_path / "README.txt").write_text("not a dicom file")

    loaded = image_helper.load_sorted_image_series(str(tmp_path))

    assert len(loaded) == 2
