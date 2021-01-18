from pydicom.sequence import Sequence
from . import ds_helper

# TODO handle overwriting existing file
class RTStruct:
    def __init__(self, dicom_series_path):
        self.dicom_series_path = dicom_series_path
        self.ds = ds_helper.generate_base_dataset(self.get_file_name())
        self.ds.ReferencedFrameOfReferenceSequence = Sequence()
        self.ds.StructureSetROISequence = Sequence()
        self.ds.ROIContourSequence = Sequence()
        self.ds.RTROIObservationsSequence = Sequence()
        # self.slice_positions = self.get_slice_positions()

    def __del__(self):
        self.save()

    def get_file_name(self):
        # Generates file name based on series data
        name = 'test'
        suffix = '.dcm'
        return name + suffix

    def insert_roi(self, roi_mask, reversed = False):
        # TODO test size of mask is the same as number of images in series 
        roi = ROIContour(roi_mask)
        # TODO change data to X, Y, Z array
        # TODO handle Referenced Frame of Reference Sequence
        # TODO handle structure set ROI sequence
        # TODO handle contour image sequence
        # TODO handle contour within sequence
        # TODO handle RT ROI observation sequence
        pass

    def save(self):
        print("Writing file name to", self.get_file_name())
        self.ds.save_as(self.get_file_name())

class ROIContour:
    def __init__(self, mask):
        self.mask = mask