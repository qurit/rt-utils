import os
from typing import List

import pydicom
import pytest

from rt_utils import RTStructBuilder, image_helper
from rt_utils.rtstruct import RTStruct


@pytest.fixture()
def series_path() -> str:
    return get_and_test_series_path("mock_data")


@pytest.fixture()
def series_datasets(series_path) -> List[pydicom.Dataset]:
    return image_helper.load_dcm_images_from_path(series_path)


@pytest.fixture()
def rtstruct_path(series_path) -> str:
    return os.path.join(series_path, "rt.dcm")


@pytest.fixture()
def new_rtstruct() -> RTStruct:
    return get_rtstruct("mock_data")


@pytest.fixture()
def oriented_series_path() -> str:
    return get_and_test_series_path("oriented_data")


@pytest.fixture()
def oriented_rtstruct() -> RTStruct:
    return get_rtstruct("oriented_data")


@pytest.fixture()
def one_slice_series_path() -> str:
    return get_and_test_series_path("one_slice_data")


@pytest.fixture()
def one_slice_rtstruct() -> RTStruct:
    return get_rtstruct("one_slice_data")


def get_rtstruct(dirname) -> RTStruct:
    path = get_and_test_series_path(dirname)
    rtstruct = RTStructBuilder.create_new(path)
    return rtstruct


def get_and_test_series_path(dirname) -> str:
    series_path = os.path.join(os.path.dirname(__file__), dirname)
    assert os.path.exists(series_path)
    return series_path
