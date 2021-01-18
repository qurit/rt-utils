import numpy as np
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
import os
from . import ds_helper

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, dicom_series_path: str):
        self.series_data = self.get_series_image_data_from_path(dicom_series_path)
        self.ds = ds_helper.generate_base_dataset(self.get_file_name())
        ds_helper.add_refd_frame_of_ref_sequence(self.ds, self.series_data)
        self.frame_of_reference_uid = self.ds.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID # Use first strucitured set ROI

    def __del__(self):
        self.save()

    def get_series_image_data_from_path(self, dicom_series_path: str):
        series_data = []
        for root, _, files in os.walk(dicom_series_path):
            for file in files:
                if file.endswith('.dcm'):
                    dc = dcmread(os.path.join(root, file))
                    # Only add CT images
                    if dc.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.2': # CT Image Storage
                        series_data.append(dc)

        if len(series_data) == 0:
            raise Exception("No DICOM data found in input path")

        # TODO sort series

        return series_data

    def get_file_name(self):
        # Generates file name based on series data
        name = 'test'
        suffix = '.dcm'
        return name + suffix

    def add_roi(self, roi_mask: np.ndarray):
        if len(self.series_data) != len(roi_mask):
            raise Exception(f"Mask must have the save number of layers as input series. Expected {len(self.series_data)}")
        
        roi_number = len(self.ds.StructureSetROISequence) + 1
        # self.ds.ROIContourSequence.append(ds_helper.create_roi_contour_sequence(roi_mask, self.series_data))
        self.ds.StructureSetROISequence.append(ds_helper.create_structure_set_roi(roi_number, self.frame_of_reference_uid))
        self.ds.RTROIObservationsSequence.append(ds_helper.create_rtroi_observation(roi_number))

    def save(self):
        print("Writing file name to", self.get_file_name())
        self.ds.save_as(self.get_file_name())