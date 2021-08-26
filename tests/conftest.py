from rt_utils.rtstruct import RTStruct
import pytest
import os
from rt_utils import RTStructBuilder

@pytest.fixture()
def series_path() -> str:
    return get_and_test_series_path('mock_data')

@pytest.fixture()
def new_rtstruct() -> RTStruct:
    return get_rtstruct('mock_data')

@pytest.fixture()
def oriented_series_path() -> RTStruct:
    return get_and_test_series_path('oriented_data')

@pytest.fixture()
def oriented_rtstruct() -> RTStruct:
    return get_rtstruct('oriented_data')

@pytest.fixture()
def one_slice_series_path() -> RTStruct:
    return get_and_test_series_path('one_slice_data')

@pytest.fixture()
def one_slice_rtstruct() -> RTStruct:
    return get_rtstruct('one_slice_data')

def get_rtstruct(dirname) -> RTStruct:
    path = get_and_test_series_path(dirname)
    rtstruct = RTStructBuilder.create_new(path)
    return rtstruct

def get_and_test_series_path(dirname) -> str:
    series_path = os.path.join(os.path.dirname(__file__), dirname)
    assert os.path.exists(series_path)
    return series_path
    