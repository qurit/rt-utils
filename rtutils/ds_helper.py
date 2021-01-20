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
    file_meta.FileMetaInformationGroupLength = 202
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    file_meta.MediaStorageSOPInstanceUID = "2.16.840.1.114362.1.11940992.23790159890.563423606.667.93"
    file_meta.ImplementationClassUID = "2.16.840.1.114362.1"
    return file_meta
    
def add_required_elements_to_ds(ds: FileDataset):
    # Append data elements required by the DICOM standarad
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.InstanceCreationDate = '20201117'
    ds.InstanceCreationTime = '112805.668'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    ds.SOPInstanceUID = '2.16.840.1.114362.1.11940992.23790159890.563423606.667.93'
    ds.StudyDate = '20201112'
    ds.SeriesDate = '20201117'
    ds.StudyTime = '085023'
    ds.SeriesTime = '112805.668'
    ds.AccessionNumber = ''
    ds.Modality = 'RTSTRUCT'
    ds.Manufacturer = 'MIM Software Inc.'
    ds.InstitutionName = 'BC Cancer Research Centre'
    ds.ReferringPhysicianName = ''
    ds.StationName = ''
    ds.StudyDescription = ''
    ds.SeriesDescription = ''
    ds.OperatorsName = ''
    ds.ManufacturerModelName = 'MIM'
    ds.PatientName = 'PHANTOM_EXAMPLE'
    ds.PatientID = 'PHANTOM_EXAMPLE'
    ds.PatientBirthDate = ''
    ds.PatientSex = 'M'
    ds.PatientAge = '000Y'
    ds.PatientSize = "0.30000001192092"
    ds.PatientWeight = "1.0"
    ds.SoftwareVersions = '7.0.3'
    ds.StudyInstanceUID = '1.2.840.113619.2.405.3.84541899.902.1605198123.910'
    ds.SeriesInstanceUID = '2.16.840.1.114362.1.11940992.23790159890.563423606.667.93'
    ds.StudyID = '637'
    ds.SeriesNumber = "1"
    ds.StructureSetLabel = 'RTstruct'
    ds.StructureSetName = ''
    ds.StructureSetDate = '20201117'
    ds.StructureSetTime = '112805.668'
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    ds.SOPInstanceUID = '2.16.840.1.114362.1.11940992.23790159890.563423606.667.93'
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
    # ds.ContentDate = dt.strftime('%Y%m%d')
    ds.ApprovalStatus = 'UNAPPROVED'
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

def create_structure_set_roi(roi_data):
    # Structure Set ROI Sequence: Structure Set ROI 1
    structure_set_roi = Dataset()
    structure_set_roi.ROINumber = roi_data.roi_number
    structure_set_roi.ReferencedFrameOfReferenceUID = roi_data.frame_of_reference_uid
    structure_set_roi.ROIName = roi_data.roi_number
    structure_set_roi.ROIDescription = ''
    structure_set_roi.ROIGenerationAlgorithm = 'MANUAL'
    return structure_set_roi

def create_roi_contour_sequence(roi_data, series_data):
    roi_contour = Dataset()
    roi_contour.ROIDisplayColor = color
    roi_contour.ContourSequence = create_contour_sequence(roi_data, series_data)
    roi_contour.ReferencedROINumber = str(roi_data.roi_number)
    return roi_contour

def create_contour_sequence(roi_data, series_data):
    contour_sequence = Sequence()
    for i, series_slice in enumerate(series_data):
        roi_mask_slice = roi_data.roi_mask[:,:,i]
        # Do not add ROI's for blank slices
        if np.sum(roi_mask_slice) == 0:
            print("Skipping empty mask layer")
            continue

        contour = create_contour(roi_mask_slice, series_slice)
        contour_sequence.append(contour)
    return contour_sequence

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
    # print(contour_coords)
    # contour_coords = [-50.049, -42.481, 70, -49.805, -42.725, 70, -47.852, -42.725, 70, -47.607, -42.481, 70, -47.363, -42.236, 70, -46.875, -42.236, 70, -46.631, -41.992, 70, -46.387, -41.748, 70, -46.143, -41.504, 70, -45.898, -41.26, 70, -45.654, -41.016, 70, -45.41, -40.772, 70, -45.166, -40.527, 70, -45.166, -40.039, 70, -44.922, -39.795, 70, -44.678, -39.551, 70, -44.678, -36.133, 70, -44.922, -35.889, 70, -45.166, -35.645, 70, -45.166, -30.762, 70, -44.922, -30.518, 70, -44.678, -30.273, 70, -44.678, -26.856, 70, -44.922, -26.611, 70, -45.166, -26.367, 70, -45.166, -25.879, 70, -45.41, -25.635, 70, -45.654, -25.391, 70, -45.898, -25.147, 70, -46.387, -25.147, 70, -46.631, -24.902, 70, -46.875, -24.658, 70, -48.828, -24.658, 70, -49.072, -24.902, 70, -49.316, -25.147, 70, -49.805, -25.147, 70, -50.049, -25.391, 70, -50.293, -25.635, 70, -50.537, -25.879, 70, -50.781, -26.123, 70, -51.025, -26.367, 70, -51.025, -27.832, 70, -51.27, -28.076, 70, -51.514, -28.32, 70, -51.514, -29.785, 70, -51.758, -30.029, 70, -52.002, -30.273, 70, -52.002, -40.527, 70, -51.758, -40.772, 70, -51.514, -41.016, 70, -51.27, -41.26, 70, -51.025, -41.504, 70, -50.781, -41.748, 70, -50.537, -41.992, 70, -50.293, -42.236, 70]
    contour.NumberOfContourPoints = len(contour_coords) / 3  # Each point has an x, y, and z value
    contour.ContourData = contour_coords
    return contour


def create_rtroi_observation(roi_number: int) -> Dataset:
    rtroi_observation = Dataset()
    rtroi_observation.ObservationNumber = str(roi_number)
    rtroi_observation.ReferencedROINumber = str(roi_number)
    rtroi_observation.ROIObservationDescription = 'Type:Soft,Range:*/*,Fill:0,Opacity:0.0,Thickness:1,LineThickness:2,read-only:false'
    rtroi_observation.private_creators = 'Test'
    rtroi_observation.RTROIInterpretedType = ''
    rtroi_observation.ROIInterpreter = ''
    return rtroi_observation
