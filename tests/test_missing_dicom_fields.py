"""Behaviour when a series omits DICOM elements rt-utils reads.

Two elements raised an opaque AttributeError when absent, but they warrant
opposite treatment. StudyID is Type 2, so a series without one is still
conformant and should not stop an RTStruct being written.
ImagePositionPatient is Type 1 and every contour coordinate is derived from
it, so a default would place the ROI somewhere else in the patient while
still producing a file that looks valid.
"""

import glob
import os
import shutil

import numpy as np
import pydicom
import pytest

from rt_utils import RTStructBuilder


def _series_without(tmp_path, series_path: str, element: str) -> str:
    """Copy a series, dropping one element from every slice."""
    destination = tmp_path / f"without_{element}"
    destination.mkdir()

    for path in glob.glob(os.path.join(series_path, "ct_*.dcm")):
        dataset = pydicom.dcmread(path)
        if element in dataset:
            delattr(dataset, element)
        dataset.save_as(destination / os.path.basename(path))

    return str(destination)


def _mask_for(rtstruct):
    ref = rtstruct.series_data[0]
    dims = (int(ref.Columns), int(ref.Rows), len(rtstruct.series_data))
    mask = np.zeros(dims, dtype=bool)
    mask[50:100, 50:100, 0] = True
    return mask


def test_series_without_study_id_still_works(tmp_path, series_path):
    """StudyID is Type 2: required to be present, permitted to be empty.

    A series omitting it is close enough to conformant that refusing to write
    an RTStruct would be our problem, not the file's.
    """
    path = _series_without(tmp_path, series_path, "StudyID")

    rtstruct = RTStructBuilder.create_new(dicom_series_path=path)
    rtstruct.add_roi(mask=_mask_for(rtstruct), name="roi")

    assert rtstruct.ds.StudyID == ""
    assert rtstruct.get_roi_names() == ["roi"]


def test_series_without_image_position_is_refused(tmp_path, series_path):
    """ImagePositionPatient is Type 1 and cannot be defaulted.

    Every contour coordinate is computed from it. Substituting an origin
    would relocate the ROI and still produce a plausible looking RTStruct, so
    the failure has to be loud and has to say why.
    """
    path = _series_without(tmp_path, series_path, "ImagePositionPatient")

    with pytest.raises(AttributeError) as error:
        RTStructBuilder.create_new(dicom_series_path=path)

    message = str(error.value)
    assert "ImagePositionPatient" in message
    assert "cannot be defaulted" in message


def test_unchanged_series_is_unaffected(series_path):
    rtstruct = RTStructBuilder.create_new(dicom_series_path=series_path)
    rtstruct.add_roi(mask=_mask_for(rtstruct), name="roi")

    assert rtstruct.ds.StudyID == rtstruct.series_data[0].StudyID
    assert rtstruct.get_roi_names() == ["roi"]
