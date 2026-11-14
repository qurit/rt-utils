import os
from typing import List

import numpy as np
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
        ds.file_meta.MediaStorageSOPInstanceUID = (
            sop_instance_uids[index]
            if sop_instance_uids is not None
            else pydicom.uid.generate_uid()
        )

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


# pydicom 3 replaced save_as's write_like_original with enforce_file_format.
# Python 3.9 resolves to pydicom 2, so tests that write files need both.
PYDICOM_3 = int(str(pydicom.__version__).split(".")[0]) >= 3


def save_dataset(ds: pydicom.Dataset, path, with_file_meta: bool = True) -> None:
    """Write a dataset, under either pydicom major version.

    ``with_file_meta=False`` writes the bare dataset with no preamble and no
    file meta, as some equipment and some anonymisation tools do. Such a file
    states no transfer syntax, so reading it needs force=True.
    """
    path = str(path)

    if PYDICOM_3:
        if with_file_meta:
            ds.save_as(path, enforce_file_format=True)
        else:
            ds.save_as(
                path, enforce_file_format=False, little_endian=True, implicit_vr=False
            )
        return

    if with_file_meta:
        ds.save_as(path, write_like_original=False)
        return

    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(path, write_like_original=True)


NM_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.20"
ENHANCED_CT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.2.1"


def _multiframe_base(sop_class_uid: str, frames: int, rows: int, columns: int):
    """The patient, study and series attributes every multi-frame image needs."""
    ds = pydicom.Dataset()
    ds.file_meta = pydicom.dataset.FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    sop_instance_uid = pydicom.uid.generate_uid()
    ds.file_meta.MediaStorageSOPClassUID = sop_class_uid
    ds.file_meta.MediaStorageSOPInstanceUID = sop_instance_uid

    ds.SOPClassUID = sop_class_uid
    ds.SOPInstanceUID = sop_instance_uid
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()

    ds.PatientName = "Synthetic"
    ds.PatientID = "SYNTHETIC"
    ds.PatientBirthDate = ""
    ds.PatientSex = ""
    ds.StudyID = "1"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.StudyDate = ds.SeriesDate = ds.ContentDate = "20200101"
    ds.StudyTime = ds.SeriesTime = ds.ContentTime = "000000"
    ds.AccessionNumber = ds.StudyDescription = ds.SeriesDescription = ""

    ds.Rows = rows
    ds.Columns = columns
    ds.NumberOfFrames = frames

    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.PixelData = (
        np.arange(frames * rows * columns, dtype=np.uint16) % 1000
    ).tobytes()

    return ds


def build_multiframe_nm(
    frames: int = 8,
    rows: int = 32,
    columns: int = 32,
    pixel_spacing=(2.0, 2.0),
    spacing_between_slices: float = 5.0,
    orientation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    origin=(0.0, 0.0, 0.0),
    slice_vector=None,
    image_type=("ORIGINAL", "PRIMARY", "RECON TOMO", "EMISSION"),
) -> pydicom.Dataset:
    """A reconstructed SPECT: one NM file holding a whole volume.

    This is the layout rt-utils has to split into slices itself. Position and
    orientation are stated once, in the Detector Information Sequence, and the
    frames are the slices of the volume.
    """
    ds = _multiframe_base(NM_IMAGE_STORAGE, frames, rows, columns)

    ds.Modality = "NM"
    ds.ImageType = list(image_type)
    ds.PixelSpacing = list(pixel_spacing)
    ds.SpacingBetweenSlices = spacing_between_slices
    ds.NumberOfSlices = frames
    ds.SliceVector = (
        list(slice_vector) if slice_vector is not None else list(range(1, frames + 1))
    )
    ds.NumberOfEnergyWindows = 1
    ds.EnergyWindowVector = [1] * frames
    ds.NumberOfDetectors = 1
    ds.DetectorVector = [1] * frames

    detector = pydicom.Dataset()
    detector.ImagePositionPatient = [float(value) for value in origin]
    detector.ImageOrientationPatient = [float(value) for value in orientation]
    ds.DetectorInformationSequence = pydicom.Sequence([detector])

    return ds


def build_enhanced_multiframe(
    frames: int = 4,
    rows: int = 16,
    columns: int = 16,
    pixel_spacing=(1.0, 1.0),
    orientation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    z_positions=None,
    shared_orientation: bool = True,
) -> pydicom.Dataset:
    """An Enhanced CT: geometry stated per frame in functional groups.

    With ``shared_orientation`` the orientation and pixel measures are stated
    once in the Shared Functional Groups Sequence, which is how a volume whose
    frames are parallel is normally written; otherwise every frame states its
    own.
    """
    ds = _multiframe_base(ENHANCED_CT_IMAGE_STORAGE, frames, rows, columns)
    ds.Modality = "CT"
    ds.ImageType = ["ORIGINAL", "PRIMARY", "VOLUME", "NONE"]

    positions = (
        list(z_positions)
        if z_positions is not None
        else [index * 3.0 for index in range(frames)]
    )

    def measures():
        item = pydicom.Dataset()
        item.PixelSpacing = list(pixel_spacing)
        item.SliceThickness = 3.0
        return pydicom.Sequence([item])

    def plane_orientation():
        item = pydicom.Dataset()
        item.ImageOrientationPatient = [float(value) for value in orientation]
        return pydicom.Sequence([item])

    if shared_orientation:
        shared = pydicom.Dataset()
        shared.PlaneOrientationSequence = plane_orientation()
        shared.PixelMeasuresSequence = measures()
        ds.SharedFunctionalGroupsSequence = pydicom.Sequence([shared])

    per_frame = pydicom.Sequence()
    for z in positions:
        groups = pydicom.Dataset()

        position = pydicom.Dataset()
        position.ImagePositionPatient = [0.0, 0.0, float(z)]
        groups.PlanePositionSequence = pydicom.Sequence([position])

        if not shared_orientation:
            groups.PlaneOrientationSequence = plane_orientation()
            groups.PixelMeasuresSequence = measures()

        per_frame.append(groups)

    ds.PerFrameFunctionalGroupsSequence = per_frame

    return ds
