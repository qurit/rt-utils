from rt_utils.utils import SOPClassUID
from pydicom.filereader import dcmread
from .rtstruct import RTStruct
from . import ds_helper, image_helper

"""
Class to help facilitate the two ways in one can instantiate the RTStruct wrapper
"""
class RTStructBuilder():
    @staticmethod
    def create_new(dicom_series_path: str):
        series_data = image_helper.load_sorted_image_series(dicom_series_path)
        ds = ds_helper.create_rtstruct_dataset(series_data)
        return RTStruct(series_data, ds)

    @staticmethod
    def create_from(dicom_series_path: str, rt_struct_path: str):
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