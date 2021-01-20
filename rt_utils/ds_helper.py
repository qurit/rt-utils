import datetime
from rt_utils.image_helper import get_contours_coords
from rt_utils.utils import ROIData
import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence

def create_rtstruct_dataset(file_name: str, series_data):
    ds = generate_base_dataset(file_name)
    add_study_and_series_information(ds, series_data)
    add_patient_information(ds, series_data)
    add_refd_frame_of_ref_sequence(ds, series_data)
    return ds

def generate_base_dataset(file_name: str) -> FileDataset:
    file_meta = get_file_meta()
    ds = FileDataset(file_name, {}, file_meta=file_meta, preamble=b"\0" * 128)
    add_required_elements_to_ds(ds)
    add_sequence_lists_to_ds(ds)
    return ds

def get_file_meta() -> FileMetaDataset:
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 202
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    file_meta.MediaStorageSOPInstanceUID = "2.16.840.1.114362.1.11940992.23790159890.563423606.667.93"
    file_meta.ImplementationClassUID = "2.16.840.1.114362.1"
    return file_meta
    
def add_required_elements_to_ds(ds: FileDataset):
    dt = datetime.datetime.now()
    # Append data elements required by the DICOM standarad
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.InstanceCreationDate = dt.strftime('%Y%m%d')
    ds.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    ds.StructureSetLabel = 'RTstruct'
    # ds.StructureSetName = ''
    ds.StructureSetDate = dt.strftime('%Y%m%d')
    ds.StructureSetTime = dt.strftime('%H%M%S.%f')
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3' # RT Struct class
    ds.SOPInstanceUID = '2.16.840.1.114362.1.11940992.23790159890.563423606.667.93' # TODO Generate
    ds.Modality = 'RTSTRUCT'
    ds.Manufacturer = 'Qurit Lab'
    ds.ManufacturerModelName = 'rt-utils'
    ds.InstitutionName = 'BC Cancer Research Center'
    # Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    ds.ApprovalStatus = 'UNAPPROVED'

def add_sequence_lists_to_ds(ds: FileDataset):
    ds.StructureSetROISequence = Sequence()
    ds.ROIContourSequence = Sequence()
    ds.RTROIObservationsSequence = Sequence()

def add_study_and_series_information(ds: FileDataset, series_data):
    ds.StudyDate = '20201112'
    ds.SeriesDate = '20201117'
    ds.StudyTime = '085023'
    ds.SeriesTime = '112805.6168'
    ds.StudyDescription = ''
    ds.SeriesDescription = ''
    ds.StudyInstanceUID = '1.2.840.113619.2.405.3.84541899.902.1605198123.910'
    ds.SeriesInstanceUID = '2.16.840.1.114362.1.11940992.23790159890.563423606.667.93'
    ds.StudyID = '637'
    ds.SeriesNumber = "1"
    pass

def add_patient_information(ds: FileDataset, series_data):
    reference_ds = series_data[0] # All elements in series should have the same data
    ds.PatientName = reference_ds.PatientName
    ds.PatientID = reference_ds.PatientID
    ds.PatientBirthDate = reference_ds.PatientBirthDate
    ds.PatientSex = reference_ds.PatientSex
    ds.PatientAge = reference_ds.PatientAge
    ds.PatientSize = reference_ds.PatientSize
    ds.PatientWeight = reference_ds.PatientWeight

def add_refd_frame_of_ref_sequence(ds: FileDataset, series_data):
    refd_frame_of_ref = Dataset()
    # TODO somehow generate this UID
    refd_frame_of_ref.FrameOfReferenceUID = '1.2.840.113619.2.405.3.84541899.902.1605198123.912.6060.1'
    refd_frame_of_ref.RTReferencedStudySequence = create_frame_of_ref_study_sequence(series_data)

    # Add to sequence
    ds.ReferencedFrameOfReferenceSequence = Sequence()
    ds.ReferencedFrameOfReferenceSequence.append(refd_frame_of_ref)

def create_frame_of_ref_study_sequence(series_data):
    rt_refd_series = Dataset()
    rt_refd_series.SeriesInstanceUID = '2.16.840.1.114362.1.11940992.23790159890.563423471.893.88'
    rt_refd_series.ContourImageSequence = create_contour_image_sequence(series_data)

    rt_refd_series_sequence = Sequence()
    rt_refd_series_sequence.append(rt_refd_series)

    rt_refd_study = Dataset()
    rt_refd_study.ReferencedSOPClassUID = '1.2.840.10008.3.1.2.3.1' # Detached Study Management SOP Class
    rt_refd_study.ReferencedSOPInstanceUID = '1.2.840.113619.2.405.3.84541899.902.1605198123.910' # TODO generate dynamically
    rt_refd_study.RTReferencedSeriesSequence = rt_refd_series_sequence

    rt_refd_study_sequence = Sequence()
    rt_refd_study_sequence.append(rt_refd_study)
    return rt_refd_study_sequence

def create_contour_image_sequence(series_data):
    contour_image_sequence = Sequence()

    # Add each referenced image
    for series in series_data:
        contour_image = Dataset()
        contour_image.ReferencedSOPClassUID = series.file_meta.MediaStorageSOPClassUID
        contour_image.ReferencedSOPInstanceUID = series.file_meta.MediaStorageSOPInstanceUID
        contour_image_sequence.append(contour_image)
    return contour_image_sequence

def create_structure_set_roi(roi_data: ROIData):
    # Structure Set ROI Sequence: Structure Set ROI 1
    structure_set_roi = Dataset()
    structure_set_roi.ROINumber = roi_data.number
    structure_set_roi.ReferencedFrameOfReferenceUID = roi_data.frame_of_reference_uid
    structure_set_roi.ROIName = roi_data.name
    structure_set_roi.ROIDescription = roi_data.description
    structure_set_roi.ROIGenerationAlgorithm = 'MANUAL'
    return structure_set_roi

def create_roi_contour_sequence(roi_data: ROIData, series_data):
    roi_contour = Dataset()
    roi_contour.ROIDisplayColor = roi_data.color
    roi_contour.ContourSequence = create_contour_sequence(roi_data, series_data)
    roi_contour.ReferencedROINumber = str(roi_data.number)
    return roi_contour

def create_contour_sequence(roi_data: ROIData, series_data):
    contour_sequence = Sequence()
    for i, series_slice in enumerate(series_data):
        mask_slice = roi_data.mask[:,:,i]
        # Do not add ROI's for blank slices
        if np.sum(mask_slice) == 0:
            print("Skipping empty mask layer")
            continue

        contour = create_contour(mask_slice, series_slice)
        contour_sequence.append(contour)
    return contour_sequence

def create_contour(mask_slice: np.ndarray, series_slice):
    contour_image = Dataset()
    contour_image.ReferencedSOPClassUID = series_slice.file_meta.MediaStorageSOPClassUID
    contour_image.ReferencedSOPInstanceUID = series_slice.file_meta.MediaStorageSOPInstanceUID

    # Contour Image Sequence
    contour_image_sequence = Sequence()
    contour_image_sequence.append(contour_image)

    contour = Dataset()
    contour.ContourImageSequence = contour_image_sequence
    contour.ContourGeometricType = 'CLOSED_PLANAR' # TODO figure out how to get this value
    contour_coords = get_contours_coords(mask_slice, series_slice)
    contour.NumberOfContourPoints = len(contour_coords) / 3  # Each point has an x, y, and z value
    contour.ContourData = contour_coords
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
