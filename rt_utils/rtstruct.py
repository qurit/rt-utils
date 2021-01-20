import numpy as np
import os

from pydicom.dataset import FileDataset
from . import ds_helper, image_helper
from rt_utils.utils import ROIData

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, series_data, ds: FileDataset):
        self.series_data = series_data
        self.ds = ds
        self.frame_of_reference_uid = ds.ReferencedFrameOfReferenceSequence[-1].FrameOfReferenceUID # Use last strucitured set ROI

    def add_roi(self, mask: np.ndarray, color=None, name=None):
        self.validate_mask(mask)
        roi_number = len(self.ds.StructureSetROISequence) + 1
        roi_data = ROIData(mask, color, roi_number, name, self.frame_of_reference_uid)

        self.ds.ROIContourSequence.append(ds_helper.create_roi_contour_sequence(roi_data, self.series_data))
        self.ds.StructureSetROISequence.append(ds_helper.create_structure_set_roi(roi_data))
        self.ds.RTROIObservationsSequence.append(ds_helper.create_rtroi_observation(roi_data))

    def validate_mask(self, mask: np.ndarray):
        if mask.dtype != bool:
            raise Exception(f"Mask data type must be boolean. Got {mask.dtype}")
        
        if mask.ndim != 3:
            raise Exception(f"Mask must be 3 dimensional. Got {mask.ndim}")

        if len(self.series_data) != np.shape(mask)[2]:
            raise Exception("Mask must have the save number of layers as input series. " +
                f"Expected {len(self.series_data)}, got {np.shape(mask)[2]}")
                
        if np.sum(mask) == 0:
            raise Exception("Mask cannot be empty")

    def get_roi_names(self):
        if not self.ds.StructureSetROISequence:
            return []

        roi_names = []
        for structure_roi in self.ds.StructureSetROISequence:
            roi_names.append(structure_roi.ROIName)
        return roi_names

    def save(self, file_path):
        try:
            open(file_path, 'w')
            # Opening worked, we should have a valid file_path
            print("Writing file to", file_path)
            self.ds.save_as(file_path)
        except OSError:
            raise Exception(f"Cannot write to file path '{file_path}'")
