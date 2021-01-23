from rt_utils.rtstruct import RTStruct
import pytest
import os
from rt_utils import RTStructBuilder
from rt_utils.utils import SOPClassUID
from pydicom.dataset import validate_file_meta
import numpy as np


def test_create_from_empty_series_dir():
    assert os.path.exists(empty_dir_path := os.path.join(os.path.dirname(__file__), 'empty'))
    with pytest.raises(Exception):
        RTStructBuilder.create_new(empty_dir_path)


def test_only_images_loaded_into_series_data(new_rtstruct: RTStruct):
    assert len(new_rtstruct.series_data) > 0
    for ds in new_rtstruct.series_data:
        assert ds.SOPInstanceUID == SOPClassUID.CT_IMAGE_STORAGE


def test_valid_filemeta(new_rtstruct: RTStruct):
    try:
        validate_file_meta(new_rtstruct.ds.file_meta)
    except Exception:
        pytest.fail("Invalid file meta in RTStruct dataset")


def test_add_non_binary_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask.astype(float)
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.add_roi(mask)


def test_add_empty_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    mask = mask[:, :, 1:] # One less slice than expected
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.add_roi(mask)


def test_add_invalid_sized_roi(new_rtstruct: RTStruct):
    mask = get_empty_mask(new_rtstruct)
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.add_roi(mask)
    # Create ROI


def test_add_valid_roi(new_rtstruct: RTStruct):
    assert new_rtstruct.get_roi_names() == []
    assert len(new_rtstruct.ds.ROIContourSequence) == 0
    assert len(new_rtstruct.ds.StructureSetROISequence) == 0
    assert len(new_rtstruct.ds.RTROIObservationsSequence) == 0

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


def test_get_invalid_roi_mask_by_name(new_rtstruct: RTStruct):
    assert new_rtstruct.get_roi_names() == []
    with pytest.raises(RTStruct.ROIException):
        new_rtstruct.get_roi_mask_by_name("FAKE_NAME")


def test_loading_invalid_rt_struct():
    assert os.path.exists(series_path := os.path.join(os.path.dirname(__file__), 'mock_data'))
    assert os.path.exists(invalid_rt_struct_path := os.path.join(series_path, 'ct_1.dcm'))
    with pytest.raises(Exception):
        RTStructBuilder.create_from(series_path, invalid_rt_struct_path)


def test_loading_valid_rt_struct():
    assert os.path.exists(series_path := os.path.join(os.path.dirname(__file__), 'mock_data'))
    assert os.path.exists(valid_rt_struct_path := os.path.join(series_path, 'rt.dcm'))
    rtstruct = RTStructBuilder.create_from(series_path, valid_rt_struct_path)

    # Tests existing values predefined in the file are found
    assert hasattr(rtstruct.ds, 'ROIContourSequence')
    assert hasattr(rtstruct.ds, 'StructureSetROISequence')
    assert hasattr(rtstruct.ds, 'RTROIObservationsSequence')
    assert len(rtstruct.ds.ROIContourSequence) == 4
    assert len(rtstruct.ds.StructureSetROISequence) == 4
    assert len(rtstruct.ds.RTROIObservationsSequence) == 4

    # Test adding a new ROI
    mask = get_empty_mask(rtstruct)
    mask[50:100,50:100,0] = 1
    rtstruct.add_roi(mask)

    assert len(rtstruct.ds.ROIContourSequence) == 5 # 1 should be added
    assert len(rtstruct.ds.StructureSetROISequence) == 5 # 1 should be added
    assert len(rtstruct.ds.RTROIObservationsSequence) == 5 # 1 should be added
    new_roi = rtstruct.ds.StructureSetROISequence[-1]
    assert new_roi.ROIName == 'ROI-5'


def get_empty_mask(rtstruct) -> np.ndarray:
    ref_dicom_image = rtstruct.series_data[0]
    mask_dims = (int(ref_dicom_image.Columns), int(ref_dicom_image.Rows), len(rtstruct.series_data))
    mask = np.zeros(mask_dims)
    return mask.astype(bool)
    
    
@pytest.fixture
def new_rtstruct() -> RTStruct:
    assert os.path.exists(series_path := os.path.join(os.path.dirname(__file__), 'mock_data'))
    rtstruct = RTStructBuilder.create_new(series_path)
    return rtstruct