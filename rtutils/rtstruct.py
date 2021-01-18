from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
import os
from . import ds_helper

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, dicom_series_path: str):
        self.series_data = self.get_series_data_from_path(dicom_series_path)
        self.ds = ds_helper.generate_base_dataset(self.get_file_name())

    def __del__(self):
        self.save()

    def get_series_data_from_path(self, dicom_series_path: str):
        series_data = []
        for root, _, files in os.walk(dicom_series_path):
            for file in files:
                if file.endswith('.dcm'):
                    series_data.append(dcmread(os.path.join(root, file)))

        if len(series_data) == 0:
            raise Exception("No DICOM data found in input path")

        return series_data

    def get_file_name(self):
        # Generates file name based on series data
        name = 'test'
        suffix = '.dcm'
        return name + suffix

    def add_roi(self, roi_mask):
        if len(self.series_data) != len(roi_mask):
            raise Exception(f"Mask must have the save number of layers as input series. Expected {len(self.series_data)}")
        
        contour_number = len(self.ds.StructureSetROISequence) + 1
        roi = ROIContour(roi_mask)
        # TODO change data to X, Y, Z array
        # TODO handle Referenced Frame of Reference Sequence
        # TODO handle structure set ROI sequence
        # TODO handle contour image sequence
        # TODO handle contour within sequence
        # TODO handle RT ROI observation sequence
        self.ds.RTROIObservationsSequence.append(ds_helper.create_rtroi_observation(contour_number))
        pass

    def save(self):
        print("Writing file name to", self.get_file_name())
        self.ds.save_as(self.get_file_name())

class ROIContour:
    def __init__(self, mask):
        self.mask = mask