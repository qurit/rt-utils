from typing import List
from pydicom.dataset import Dataset
from pydicom.filereader import dcmread

from rt_utils.utils import SOPClassUID
from . import ds_helper, image_helper
from .rtstruct import RTStruct


class RTStructBuilder:
    """
    Class to help facilitate the two ways in one can instantiate the RTStruct wrapper
    """

    @staticmethod
    def create_new(dicom_series_path: str) -> RTStruct:
        """
        Method to generate a new rt struct from a DICOM series
        """

        series_data = image_helper.load_sorted_image_series(dicom_series_path)
        ds = ds_helper.create_rtstruct_dataset(series_data)
        return RTStruct(series_data, ds)

    @staticmethod
    def create_from(dicom_series_path: str, rt_struct_path: str) -> RTStruct:
        """
        Method to load an existing rt struct, given related DICOM series and existing rt struct
        """

        series_data = image_helper.load_sorted_image_series(dicom_series_path)
        ds = dcmread(rt_struct_path)
        RTStructBuilder.validate_rtstruct(ds)
        RTStructBuilder.validate_rtstruct_series_references(ds, series_data)

        # TODO create new frame of reference? Right now we assume the last frame of reference created is suitable 
        return RTStruct(series_data, ds)

    @staticmethod
    def validate_rtstruct(ds: Dataset):
        """
        Method to validate a dataset is a valid RTStruct containing the required fields
        """

        if ds.SOPClassUID != SOPClassUID.RTSTRUCT or \
                not hasattr(ds, 'ROIContourSequence') or \
                not hasattr(ds, 'StructureSetROISequence') or \
                not hasattr(ds, 'RTROIObservationsSequence'):
            raise Exception("Please check that the existing RTStruct is valid")

    @staticmethod
    def validate_rtstruct_series_references(ds: Dataset, series_data: List[Dataset]):
        """
        Method to validate RTStruct only references dicom images found within the input series_data
        """
        for refd_frame_of_ref in ds.ReferencedFrameOfReferenceSequence:
            for rt_refd_study in refd_frame_of_ref.RTReferencedStudySequence:
                for rt_refd_series in rt_refd_study.RTReferencedSeriesSequence:
                    for contour_image in rt_refd_series.ContourImageSequence:
                        RTStructBuilder.validate_contour_image_in_series_data(
                            contour_image, series_data)

    @staticmethod
    def validate_contour_image_in_series_data(contour_image: Dataset, series_data: List[Dataset]):
        """
        Method to validate that the ReferencedSOPInstanceUID of a given contour image exists within the series data
        """
        for series in series_data:
            if contour_image.ReferencedSOPInstanceUID == series.file_meta.MediaStorageSOPInstanceUID:
                return

        # ReferencedSOPInstanceUID is NOT available
        raise Exception(
            f'Loaded RTStruct references image(s) that are not contained in input series data. ' + 
            f'Problematic image has SOP Instance Id: {contour_image.ReferencedSOPInstanceUID}'
        )
