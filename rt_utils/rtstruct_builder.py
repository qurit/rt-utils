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

        # TODO create new frame of reference?
        return RTStruct(series_data, ds)

    @staticmethod
    def validate_rtstruct(ds):
        if ds.SOPClassUID != SOPClassUID.RTSTRUCT or \
                not hasattr(ds, 'ROIContourSequence') or \
                not hasattr(ds, 'StructureSetROISequence') or \
                not hasattr(ds, 'RTROIObservationsSequence'):
            raise Exception("Please check that the existing RTStruct is valid")
