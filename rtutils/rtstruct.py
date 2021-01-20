import numpy as np
from . import ds_helper, image_helper
from rtutils.utils import ROIData

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, dicom_series_path: str):
        self.series_data = image_helper.load_sorted_image_series(dicom_series_path)
        self.ds = ds_helper.create_new_rts_dataset(self.get_file_name(), self.series_data)
        self.frame_of_reference_uid = self.ds.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID # Use first strucitured set ROI

    def __del__(self):
        # Will not save if an exception occured before generating the dataset
        if hasattr(self, 'ds'):
            self.save()

    def get_file_name(self):
        # Generates file name based on series data
        name = 'test'
        suffix = '.dcm'
        return name + suffix

    def get_roi_names(self):
        if not self.ds.StructureSetROISequence:
            return []

        roi_names = []
        for structure_roi in self.ds.StructureSetROISequence:
            roi_names.append(structure_roi.ROIName)
        return roi_names

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

    def save(self):
        print("Writing file to", self.get_file_name())
        self.ds.save_as(self.get_file_name())
