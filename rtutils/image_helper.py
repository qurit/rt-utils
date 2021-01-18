
from pydicom import dcmread
import os
import numpy as np
import pandas as pd

# to find the contours
from skimage.measure import find_contours

def load_sorted_image_series(dicom_series_path: str):
        series_data = []
        for root, _, files in os.walk(dicom_series_path):
            for file in files:
                if file.endswith('.dcm'):
                    ds = dcmread(os.path.join(root, file))
                    # Only add CT images
                    if ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.2': # CT Image Storage
                        series_data.append(ds)

        if len(series_data) == 0:
            raise Exception("No DICOM data found in input path")

        # Sort slices ascending
        series_data.sort(key=lambda ds: ds.SliceLocation, reverse=False)

        return series_data