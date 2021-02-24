import pytest
from rt_utils import ds_helper, image_helper

def test_correctly_acquire_optional_ds_field(series_path):
    series_data = image_helper.load_sorted_image_series(series_path)

    patient_age = series_data[0]['PatientAge'].value    
    ds = ds_helper.create_rtstruct_dataset(series_data)

    assert ds.PatientAge == patient_age

def test_ds_creation_without_patient_age(series_path):
    # Ensure only 1 file in series data so ds_helper uses the file for header reference
    series_data = image_helper.load_sorted_image_series(series_path)
    series_data = [series_data[0]]

    # Remove optional field
    original_age = series_data[0]['PatientAge'].value
    del series_data[0]['PatientAge']
    with pytest.raises(Exception):
        access = series_data[0]['PatientAge']
    
    ds = ds_helper.create_rtstruct_dataset(series_data)

    assert ds.PatientAge != original_age
    assert ds.PatientAge == ''
    
