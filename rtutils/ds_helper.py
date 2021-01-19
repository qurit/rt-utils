import datetime
from rtutils.image_helper import get_contours_coords
import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence

def generate_base_dataset(file_name: str) -> FileDataset:
    file_meta = get_file_meta()
    ds = FileDataset(file_name, {}, file_meta=file_meta, preamble=b"\0" * 128)
    add_required_elements_to_ds(ds)
    add_sequence_lists_to_ds(ds)
    return ds

def get_file_meta() -> FileMetaDataset:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    file_meta.MediaStorageSOPInstanceUID = "1.2.3"
    file_meta.ImplementationClassUID = "1.2.3.4"
    return file_meta

def add_required_elements_to_ds(ds: FileDataset):
    # Append data elements required by the DICOM standarad 
    ds.PatientName = "Test^Firstname"
    ds.PatientID = "123456"
    ds.Modality = 'RTSTRUCT'
    ds.Manufacturer = 'Qurit Lab'
    ds.InstitutionName = 'BC Cancer Research Center'
    # Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    # Set creation date/time
    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')
    # TODO add structure set time

def add_sequence_lists_to_ds(ds: FileDataset):
    ds.StructureSetROISequence = Sequence()
    ds.ROIContourSequence = Sequence()
    ds.RTROIObservationsSequence = Sequence()

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

def create_structure_set_roi(roi_number, frame_of_reference_uid):
    # Structure Set ROI Sequence: Structure Set ROI 1
    structure_set_roi = Dataset()
    structure_set_roi.ROINumber = str(roi_number)
    structure_set_roi.ReferencedFrameOfReferenceUID = frame_of_reference_uid
    structure_set_roi.ROIName = f'ROI-{roi_number}'
    structure_set_roi.ROIDescription = ''
    structure_set_roi.ROIGenerationAlgorithm = 'AUTOMATIC'
    return structure_set_roi

def create_roi_contour_sequence(roi_mask: np.ndarray, series_data):
    contour_sequence = Sequence()
    for i, series_slice in enumerate(series_data):
        roi_mask_slice = roi_mask[:,:,i]
        # Do not add ROI's for blank slices
        if np.sum(roi_mask_slice) == 0:
            print("Skipping empty mask layer")
            continue

        contour = create_contour(roi_mask_slice, series_slice)
        contour_sequence.append(contour)

    # Wrap in ROI contour
    roi_contour = Dataset()
    roi_contour.ROIDisplayColor = [255, 0, 255] # TODO random colour per ROI / add your own colour?
    roi_contour.ContourSequence = contour_sequence
    return roi_contour

def create_contour(roi_mask_slice: np.ndarray, series_slice):
    contour_image = Dataset()
    contour_image.ReferencedSOPClassUID = series_slice.file_meta.MediaStorageSOPClassUID
    contour_image.ReferencedSOPInstanceUID = series_slice.file_meta.MediaStorageSOPInstanceUID

    # Contour Image Sequence
    contour_image_sequence = Sequence()
    contour_image_sequence.append(contour_image)

    contour = Dataset()
    contour.ContourImageSequence = contour_image_sequence
    contour.ContourGeometricType = 'CLOSED_PLANAR' # TODO figure out how to get this value
    contour_coords = get_contours_coords(roi_mask_slice, series_slice)
    contour.NumberOfContourPoints = len(contour_coords) / 3  # Each point has an x, y, and z value
    contour.ContourData = contour_coords
    return contour


def create_rtroi_observation(roi_number: int) -> Dataset:
    rtroi_observation = Dataset()
    rtroi_observation.ObservationNumber = str(roi_number)
    rtroi_observation.ReferencedROINumber = str(roi_number)
    rtroi_observation.ROIObservationDescription = 'Type:Soft,Range:*/*,Fill:0,Opacity:0.0,Thickness:1,LineThickness:2,read-only:false'
    rtroi_observation.RTROIInterpretedType = ''
    rtroi_observation.ROIInterpreter = ''
    return rtroi_observation
