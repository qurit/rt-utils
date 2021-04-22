from rt_utils.rtstruct import RTStruct
import pytest
import os
from rt_utils import RTStructBuilder

@pytest.fixture()
def series_path() -> str:
    return get_and_test_series_path()

@pytest.fixture()
def new_rtstruct() -> RTStruct:
    path = get_and_test_series_path()
    rtstruct = RTStructBuilder.create_new(path)
    return rtstruct

def get_and_test_series_path() -> str:
    series_path = os.path.join(os.path.dirname(__file__), 'mock_data/')
    assert os.path.exists(series_path)
    return series_path
    