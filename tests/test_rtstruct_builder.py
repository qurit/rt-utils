import pytest
import os
from rt_utils import RTStructBuilder
from pydicom.dataset import validate_file_meta


def test_create_from_empty_series_dir():
    assert os.path.exists(empty_dir_path := os.path.join(os.path.dirname(__file__), 'empty'))
    with pytest.raises(Exception):
        rtstruct = RTStructBuilder.create_new(empty_dir_path)

def test_only_images_loaded_into_series_data(new_rtstruct):
    assert len(new_rtstruct.series_data) > 0
    for ds in new_rtstruct.series_data:
        assert ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.2' # CT Image Storage

def valid_filemeta(new_rtstruct):
    try:
        validate_file_meta(new_rtstruct.ds)
    except Exception:
        pytest.fail("Invalid file meta in RTStruct dataset")

def test_add_non_binary_roi(new_rtstruct):
    # Create ROI
    pass

def test_add_non_binary_roi(new_rtstruct):
    # Create ROI
    pass

def test_add_valid_roi(new_rtstruct):
    COLOR = [123, 321, 456]
    # Create ROI
    pass

@pytest.fixture
def new_rtstruct():
    assert os.path.exists(series_path := os.path.join(os.path.dirname(__file__), 'mock_data'))
    rtstruct = RTStructBuilder.create_new(series_path)
    return rtstruct