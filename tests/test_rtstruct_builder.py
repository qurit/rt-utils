from rt_utils.rtstruct import RTStruct
import pytest
import os
from rt_utils import RTStructBuilder
from pydicom.dataset import validate_file_meta
import numpy as np


def test_create_from_empty_series_dir():
    assert os.path.exists(empty_dir_path := os.path.join(os.path.dirname(__file__), 'empty'))
    with pytest.raises(Exception):
        rtstruct = RTStructBuilder.create_new(empty_dir_path)

def test_only_images_loaded_into_series_data(new_rtstruct: RTStruct):
    assert len(new_rtstruct.series_data) > 0
    for ds in new_rtstruct.series_data:
        assert ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.2' # CT Image Storage

def test_valid_filemeta(new_rtstruct: RTStruct):
    # TODO, get test working
    return
    try:
        validate_file_meta(new_rtstruct.ds)
    except Exception:
        pytest.fail("Invalid file meta in RTStruct dataset")

def test_add_non_binary_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask.astype(float)
    with pytest.raises(Exception):
        new_rtstruct.add_roi(mask)

def test_add_empty_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    with pytest.raises(Exception):
        new_rtstruct.add_roi(mask)


def test_add_invalid_sized_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    with pytest.raises(Exception):
        new_rtstruct.add_roi(mask)
    # Create ROI

def test_add_valid_roi(new_rtstruct: RTStruct):
    NAME = "Test ROI"
    COLOR = [123, 321, 456]
    mask = get_empty_mask(new_rtstruct)
    mask[50:100,50:100,0] = 1
    
    new_rtstruct.add_roi(mask, color=COLOR, name=NAME)

    assert len(new_rtstruct.ds.ROIContourSequence) == 1
    assert len(new_rtstruct.ds.ROIContourSequence[0].ContourSequence) == 1 # Only 1 slice was added to
    assert len(new_rtstruct.ds.StructureSetROISequence) == 1
    assert len(new_rtstruct.ds.RTROIObservationsSequence) == 1
    assert new_rtstruct.ds.ROIContourSequence[0].ROIDisplayColor == COLOR
    assert new_rtstruct.get_roi_names() == [NAME]


def get_empty_mask(rtstruct) -> np.ndarray:
    ref_dicom_image = rtstruct.series_data[0]
    ConstPixelDims = (int(ref_dicom_image.Columns), int(ref_dicom_image.Rows), len(rtstruct.series_data))
    mask = np.zeros(ConstPixelDims)
    return mask.astype(bool)
    

@pytest.fixture
def new_rtstruct() -> RTStruct:
    assert os.path.exists(series_path := os.path.join(os.path.dirname(__file__), 'mock_data'))
    rtstruct = RTStructBuilder.create_new(series_path)
    return rtstruct