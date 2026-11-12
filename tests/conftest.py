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
    """The same series as `series_path`, read into memory with pydicom."""
    return image_helper.load_dcm_images_from_path(series_path)


@pytest.fixture()
def rtstruct_path(series_path) -> str:
    return os.path.join(series_path, "rt.dcm")


@pytest.fixture()
def new_rtstruct() -> RTStruct:
    return get_rtstruct("mock_data")


@pytest.fixture()
def oriented_series_path() -> RTStruct:
    return get_and_test_series_path("oriented_data")


@pytest.fixture()
def oriented_rtstruct() -> RTStruct:
    return get_rtstruct("oriented_data")


@pytest.fixture()
def one_slice_series_path() -> RTStruct:
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


def build_series(
    z_positions,
    rows: int = 32,
    columns: int = 32,
    pixel_spacing=(1.0, 1.0),
    orientation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    sop_instance_uids=None,
) -> List[pydicom.Dataset]:
    """A synthetic image series placed at the given slice positions.

    Spacing between slices follows from ``z_positions``, so an unevenly
    spaced stack is built by passing uneven values. Datasets are returned
    rather than written out, since the builder accepts either.
    """
    series_instance_uid = pydicom.uid.generate_uid()
    study_instance_uid = pydicom.uid.generate_uid()
    frame_of_reference_uid = pydicom.uid.generate_uid()

    series = []
    for index, z in enumerate(z_positions):
        ds = pydicom.Dataset()
        ds.file_meta = pydicom.dataset.FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        ds.file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage

        ds.SOPClassUID = pydicom.uid.CTImageStorage
        ds.SOPInstanceUID = (
            sop_instance_uids[index]
            if sop_instance_uids is not None
            else pydicom.uid.generate_uid()
        )
        ds.SeriesInstanceUID = series_instance_uid
        ds.StudyInstanceUID = study_instance_uid
        ds.FrameOfReferenceUID = frame_of_reference_uid

        ds.Modality = "CT"
        ds.PatientName = "Synthetic"
        ds.PatientID = "SYNTHETIC"
        ds.PatientBirthDate = ""
        ds.PatientSex = ""
        ds.StudyID = "1"
        ds.SeriesNumber = 1
        ds.InstanceNumber = index + 1
        ds.StudyDate = ds.SeriesDate = ds.ContentDate = "20200101"
        ds.StudyTime = ds.SeriesTime = ds.ContentTime = "000000"
        ds.AccessionNumber = ds.StudyDescription = ds.SeriesDescription = ""

        ds.Rows = rows
        ds.Columns = columns
        ds.PixelSpacing = list(pixel_spacing)
        ds.ImageOrientationPatient = list(orientation)
        ds.ImagePositionPatient = [0.0, 0.0, float(z)]

        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.PixelData = bytes(rows * columns * 2)

        series.append(ds)

    return series
