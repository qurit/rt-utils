import datetime
from rt_utils.image_helper import get_contours_coords
from rt_utils.utils import ROIData, SOPClassUID
import numpy as np
from pydicom.uid import generate_uid
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ImplicitVRLittleEndian

"""
File contains helper methods that handles DICOM header creation/formatting
"""
def create_rtstruct_dataset(series_data) -> FileDataset:
    ds = generate_base_dataset()
    add_study_and_series_information(ds, series_data)
    add_patient_information(ds, series_data)
    add_refd_frame_of_ref_sequence(ds, series_data)
    return ds

def generate_base_dataset() -> FileDataset:
    file_name = 'rt-utils-struct'
    file_meta = get_file_meta()
    ds = FileDataset(file_name, {}, file_meta=file_meta, preamble=b"\0" * 128)
    add_required_elements_to_ds(ds)
    add_sequence_lists_to_ds(ds)
    return ds

def get_file_meta() -> FileMetaDataset:
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 202
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.TransferSyntaxUID = ImplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = SOPClassUID.RTSTRUCT
    file_meta.MediaStorageSOPInstanceUID = generate_uid() # TODO find out random generation is fine
    file_meta.ImplementationClassUID = SOPClassUID.RTSTRUCT_IMPLEMENTATION_CLASS
    return file_meta
    
def add_required_elements_to_ds(ds: FileDataset):
    dt = datetime.datetime.now()
    # Append data elements required by the DICOM standarad
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.InstanceCreationDate = dt.strftime('%Y%m%d')
    ds.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    ds.StructureSetLabel = 'RTstruct'
    ds.StructureSetDate = dt.strftime('%Y%m%d')
    ds.StructureSetTime = dt.strftime('%H%M%S.%f')
    ds.Modality = 'RTSTRUCT'
    ds.Manufacturer = 'Qurit'
    ds.ManufacturerModelName = 'rt-utils'
    ds.InstitutionName = 'Qurit'
    # Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    # Set values already defined in the file meta
    ds.SOPClassUID = ds.file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID

    ds.ApprovalStatus = 'UNAPPROVED'

def add_sequence_lists_to_ds(ds: FileDataset):
    ds.StructureSetROISequence = Sequence()
    ds.ROIContourSequence = Sequence()
    ds.RTROIObservationsSequence = Sequence()

def add_study_and_series_information(ds: FileDataset, series_data):
    reference_ds = series_data[0] # All elements in series should have the same data
    ds.StudyDate = reference_ds.StudyDate
    ds.SeriesDate = reference_ds.SeriesDate
    ds.StudyTime = reference_ds.StudyTime
    ds.SeriesTime = reference_ds.SeriesTime
    ds.StudyDescription = getattr(reference_ds, 'StudyDescription', '')
    ds.SeriesDescription = getattr(reference_ds, 'SeriesDescription', '')
    ds.StudyInstanceUID = reference_ds.StudyInstanceUID
    ds.SeriesInstanceUID = generate_uid() # TODO: find out if random generation is ok
    ds.StudyID = reference_ds.StudyID
    ds.SeriesNumber = "1" # TODO: find out if we can just use 1 (Should be fine since its a new series)

def add_patient_information(ds: FileDataset, series_data):
    reference_ds = series_data[0] # All elements in series should have the same data
    ds.PatientName = getattr(reference_ds, 'PatientName', '')
    ds.PatientID = getattr(reference_ds, 'PatientID', '')
    ds.PatientBirthDate = getattr(reference_ds, 'PatientBirthDate', '')
    ds.PatientSex = getattr(reference_ds, 'PatientSex', '')
    ds.PatientAge = getattr(reference_ds, 'PatientAge', '')
    ds.PatientSize = getattr(reference_ds, 'PatientSize', '')
    ds.PatientWeight = getattr(reference_ds, 'PatientWeight', '')


def add_refd_frame_of_ref_sequence(ds: FileDataset, series_data):
    refd_frame_of_ref = Dataset()
    refd_frame_of_ref.FrameOfReferenceUID = generate_uid() # TODO Find out if random generation is ok
    refd_frame_of_ref.RTReferencedStudySequence = create_frame_of_ref_study_sequence(series_data)

    # Add to sequence
    ds.ReferencedFrameOfReferenceSequence = Sequence()
    ds.ReferencedFrameOfReferenceSequence.append(refd_frame_of_ref)


def create_frame_of_ref_study_sequence(series_data) -> Sequence:
    reference_ds = series_data[0] # All elements in series should have the same data
    rt_refd_series = Dataset()
    rt_refd_series.SeriesInstanceUID = reference_ds.SeriesInstanceUID
    rt_refd_series.ContourImageSequence = create_contour_image_sequence(series_data)

    rt_refd_series_sequence = Sequence()
    rt_refd_series_sequence.append(rt_refd_series)

    rt_refd_study = Dataset()
    rt_refd_study.ReferencedSOPClassUID = SOPClassUID.DETACHED_STUDY_MANAGEMENT
    rt_refd_study.ReferencedSOPInstanceUID = reference_ds.StudyInstanceUID
    rt_refd_study.RTReferencedSeriesSequence = rt_refd_series_sequence

    rt_refd_study_sequence = Sequence()
    rt_refd_study_sequence.append(rt_refd_study)
    return rt_refd_study_sequence


def create_contour_image_sequence(series_data) -> Sequence:
    contour_image_sequence = Sequence()

    # Add each referenced image
    for series in series_data:
        contour_image = Dataset()
        contour_image.ReferencedSOPClassUID = series.file_meta.MediaStorageSOPClassUID
        contour_image.ReferencedSOPInstanceUID = series.file_meta.MediaStorageSOPInstanceUID
        contour_image_sequence.append(contour_image)
    return contour_image_sequence


def create_structure_set_roi(roi_data: ROIData) -> Dataset:
    # Structure Set ROI Sequence: Structure Set ROI 1
    structure_set_roi = Dataset()
    structure_set_roi.ROINumber = roi_data.number
    structure_set_roi.ReferencedFrameOfReferenceUID = roi_data.frame_of_reference_uid
    structure_set_roi.ROIName = roi_data.name
    structure_set_roi.ROIDescription = roi_data.description
    structure_set_roi.ROIGenerationAlgorithm = 'MANUAL'
    return structure_set_roi


def create_roi_contour(roi_data: ROIData, series_data) -> Dataset:
    roi_contour = Dataset()
    roi_contour.ROIDisplayColor = roi_data.color
    roi_contour.ContourSequence = create_contour_sequence(roi_data, series_data)
    roi_contour.ReferencedROINumber = str(roi_data.number)
    return roi_contour


def create_contour_sequence(roi_data: ROIData, series_data) -> Sequence:
    """
    Iterate through each slice of the mask
    For each connected segment within a slice, create a contour
    """

    contour_sequence = Sequence()
    for i, series_slice in enumerate(series_data):
        mask_slice = roi_data.mask[:,:,i]
        # Do not add ROI's for blank slices
        if np.sum(mask_slice) == 0:
            print("Skipping empty mask layer")
            continue

        contour_coords = get_contours_coords(mask_slice, series_slice, roi_data)
        for contour_data in contour_coords:
            contour = create_contour(series_slice, contour_data)
            contour_sequence.append(contour)

    return contour_sequence


def create_contour(series_slice: Dataset, contour_data: np.ndarray) -> Dataset:
    contour_image = Dataset()
    contour_image.ReferencedSOPClassUID = series_slice.file_meta.MediaStorageSOPClassUID
    contour_image.ReferencedSOPInstanceUID = series_slice.file_meta.MediaStorageSOPInstanceUID

    # Contour Image Sequence
    contour_image_sequence = Sequence()
    contour_image_sequence.append(contour_image)

    contour = Dataset()
    contour.ContourImageSequence = contour_image_sequence
    contour.ContourGeometricType = 'CLOSED_PLANAR' # TODO figure out how to get this value
    contour.NumberOfContourPoints = len(contour_data) / 3  # Each point has an x, y, and z value
    contour.ContourData = contour_data

    return contour


def create_rtroi_observation(roi_data: ROIData) -> Dataset:
    rtroi_observation = Dataset()
    rtroi_observation.ObservationNumber = roi_data.number
    rtroi_observation.ReferencedROINumber = roi_data.number
    # TODO figure out how to get observation description
    rtroi_observation.ROIObservationDescription = 'Type:Soft,Range:*/*,Fill:0,Opacity:0.0,Thickness:1,LineThickness:2,read-only:false'
    rtroi_observation.private_creators = 'Qurit Lab'
    rtroi_observation.RTROIInterpretedType = ''
    rtroi_observation.ROIInterpreter = ''
    return rtroi_observation


def get_contour_sequence_by_roi_number(ds, roi_number):
    for roi_contour in ds.ROIContourSequence:

        # Ensure same type
        if str(roi_contour.ReferencedROINumber) == str(roi_number):
            return roi_contour.ContourSequence

    raise Exception(f"Referenced ROI number '{roi_number}' not found")
