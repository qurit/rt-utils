import numpy as np
from . import ds_helper, image_helper

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

    def add_roi(self, roi_mask: np.ndarray):
        self.validate_mask(roi_mask)
        if np.sum(roi_mask) == 0:
            print("Skipping empty ROI mask")
            return

        roi_number = len(self.ds.StructureSetROISequence) + 1
        self.ds.ROIContourSequence.append(ds_helper.create_roi_contour_sequence(roi_mask, self.series_data))
        self.ds.StructureSetROISequence.append(ds_helper.create_structure_set_roi(roi_number, self.frame_of_reference_uid))
        self.ds.RTROIObservationsSequence.append(ds_helper.create_rtroi_observation(roi_number))
    
    def validate_mask(self, roi_mask: np.ndarray):
        if roi_mask.dtype != bool:
            raise Exception(f"Mask data type must be boolean. Got {roi_mask.dtype}")
        if roi_mask.ndim != 3:
            raise Exception(f"Mask must be 3 dimensional. Got {roi_mask.ndim}")
        if len(self.series_data) != np.shape(roi_mask)[2]:
            raise Exception("Mask must have the save number of layers as input series. " +
                f"Expected {len(self.series_data)}, got {np.shape(roi_mask)[2]}")


    def save(self):
        print("Writing file name to", self.get_file_name())
        self.ds.save_as(self.get_file_name())