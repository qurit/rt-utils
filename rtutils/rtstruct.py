import os
import tempfile
import datetime

import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset

class RTStruct:
    # TODO handle overwriting existing file
    def __init__(self, dicom_series_path):
        self.dicom_series_path = dicom_series_path
        self.generate_base_file()
        self.slice_positions = self.get_slice_positions()

    def __del__(self):
        self.save()

    def generate_base_file(self):
        file_meta = self.get_file_meta()
        self.ds = FileDataset(self.get_file_name(), {}, file_meta=file_meta, preamble=b"\0" * 128)
        self.append_required_elements()

    def get_file_meta(self):
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        file_meta.MediaStorageSOPInstanceUID = "1.2.3"
        file_meta.ImplementationClassUID = "1.2.3.4"
        return file_meta

    def append_required_elements(self):
        # Appends data elements required by the DICOM standarad 
        self.ds.PatientName = "Test^Firstname"
        self.ds.PatientID = "123456"
        # Set the transfer syntax
        self.ds.is_little_endian = True
        self.ds.is_implicit_VR = True
        # Set creation date/time
        dt = datetime.datetime.now()
        self.ds.ContentDate = dt.strftime('%Y%m%d')

    def get_file_name(self):
        # Generates file name based on series data
        name = 'test'
        suffix = '.dcm'
        return name + suffix

    def insert_roi(self, roi_mask, reversed = False):
        # TODO test size of mask is the same as number of images in series 
        roi = ROIContour(roi_mask)
        pass

    def save(self):
        print("Writing file name to", self.get_file_name())
        self.ds.save_as(self.get_file_name())

class ROIContour:
    def __init__(self, mask):
        self.mask = mask