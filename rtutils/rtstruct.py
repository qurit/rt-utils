import numpy as np
from . import ds_helper, image_helper
from dataclasses import dataclass
from random import randrange

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, dicom_series_path: str):
        self.series_data = image_helper.load_sorted_image_series(dicom_series_path)
        self.ds = ds_helper.generate_base_dataset(self.get_file_name())
        ds_helper.add_patient_information(self.ds, self.series_data)
        ds_helper.add_refd_frame_of_ref_sequence(self.ds, self.series_data)
        self.frame_of_reference_uid = self.ds.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID # Use first strucitured set ROI

    def __del__(self):
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

    def add_roi(self, roi_mask: np.ndarray, color=None, roi_name=''):
        self.validate_mask(roi_mask)
        frame_of_reference_uid = self.frame_of_reference_uid
        roi_number = len(self.ds.StructureSetROISequence) + 1
        roi_data = {roi_mask, color, roi_number, roi_name, frame_of_reference_uid}
        self.ds.ROIContourSequence.append(ds_helper.create_roi_contour_sequence(roi_data, self.series_data))
        self.ds.StructureSetROISequence.append(ds_helper.create_structure_set_roi(roi_data))
        self.ds.RTROIObservationsSequence.append(ds_helper.create_rtroi_observation(roi_data))


    def validate_mask(self, roi_mask: np.ndarray):
        if roi_mask.dtype != bool:
            raise Exception(f"Mask data type must be boolean. Got {roi_mask.dtype}")
        if roi_mask.ndim != 3:
            raise Exception(f"Mask must be 3 dimensional. Got {roi_mask.ndim}")
        if len(self.series_data) != np.shape(roi_mask)[2]:
            raise Exception("Mask must have the save number of layers as input series. " +
                f"Expected {len(self.series_data)}, got {np.shape(roi_mask)[2]}")
        if np.sum(roi_mask) == 0:
            raise Exception("Mask cannot be empty")


    def save(self):
        print("Writing file name to", self.get_file_name())
        self.ds.save_as(self.get_file_name())

    @dataclass
    class ROIData:
        """Class to easily pass ROI data to helper methods."""
        roi_mask: str
        color: list
        roi_number: int
        roi_name: str
        frame_of_reference_uid: int

        def __post_init__(self):
            if self.color == None:
                self.color = self.get_random_colour()

            if self.roi_name == None:
                self.roi_name = f"ROI-{self.roi_number}"
        
        def get_random_colour(self):
            max = 256
            return [randrange(max), randrange(max), randrange(max)]


