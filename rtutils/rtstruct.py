import numpy as np
from numpy.lib.type_check import imag
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
import os
from . import ds_helper, image_helper

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, dicom_series_path: str):
        self.series_data = image_helper.load_sorted_image_series(dicom_series_path)
        self.ds = ds_helper.generate_base_dataset(self.get_file_name())
        ds_helper.add_refd_frame_of_ref_sequence(self.ds, self.series_data)
        self.frame_of_reference_uid = self.ds.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID # Use first strucitured set ROI

    def __del__(self):
        self.save()

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