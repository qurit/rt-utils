
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from rt_utils.utils import SOPClassUID
import os
from skimage.measure import find_contours
import numpy as np


import matplotlib.pyplot as plt

"""
File contians helper methods for loading / formatting DICOM images and contours
"""
def load_sorted_image_series(dicom_series_path: str):
        series_data = load_CT_images_from_path(dicom_series_path)

        if len(series_data) == 0:
            raise Exception("No CT Images found in input path")

        # Sort slices in ascending order
        series_data.sort(key=lambda ds: ds.SliceLocation, reverse=False)

        return series_data

def load_CT_images_from_path(dicom_series_path: str):
    series_data = []
    for root, _, files in os.walk(dicom_series_path):
        for file in files:
            if file.endswith('.dcm'):
                ds = dcmread(os.path.join(root, file))
                # Only add CT images
                if ds.SOPClassUID == SOPClassUID.CT_IMAGE_STORAGE:
                    series_data.append(ds)
    return series_data

def get_contours_coords(mask_slice: np.ndarray, series_slice: Dataset):
    contours = find_contours(mask_slice)
    validate_contours(contours)
    contour = contours[0] # Expect only 1 contour so take first one found
    translated_contour = translate_contour_to_data_coordinants(contour, series_slice)
    dicom_formatted_contour = format_contour_for_dicom(translated_contour, series_slice)

    return dicom_formatted_contour 

def validate_contours(contours: list):
    if len(contours) == 0:
        raise Exception("Unable to find contour in non empty mask, please check your mask formatting"
    )

    # Method will find multiple contours if possible. Ensure only one is found
    if len(contours) > 1:
        print(
            "ERROR: unexpected number of counters in slice. " +
            f"Expected 1, got {len(contours)}"
            )

def translate_contour_to_data_coordinants(contour, series_slice: Dataset):
    offset = series_slice.ImagePositionPatient
    spacing = series_slice.PixelSpacing
    contour[:, 0] = (contour[:, 0]) * spacing[0] + offset[0]
    contour[:, 1] = (contour[:, 1]) * spacing[1] + offset[1]
    return contour

def format_contour_for_dicom(contour, series_slice: Dataset):
    # DICOM uses a 1d array of x, y, z coords
    z_indicies = np.ones((contour.shape[0], 1)) * series_slice.SliceLocation
    contour = np.concatenate((contour, z_indicies), axis = 1)
    contour = np.ravel(contour)
    contour = contour.tolist()
    return contour

def create_series_mask_from_contour_sequence(series_data, contour_sequence: Sequence):
    mask = create_empty_series_mask(series_data)

    # Iterate through each slice of the series, If it is a part of the contour, add the contour mask
    for i, series_slice in enumerate(series_data):
        slice_contour_data = get_slice_contour_data(series_slice, contour_sequence)
        if len(slice_contour_data):
            mask[:, :, i] = get_slice_mask_from_slice_contour_data(series_slice, slice_contour_data)
    return mask

def get_slice_contour_data(series_slice: Dataset, contour_sequence: Sequence):
    slice_contour_data = []
    
    # Traverse through sequence data and get all contour data pertaining to the given slice
    for contour in contour_sequence:
        for contour_image in contour.ContourImageSequence:
            if contour_image.ReferencedSOPInstanceUID == series_slice.SOPInstanceUID:
                slice_contour_data.append(contour.ContourData)

    return slice_contour_data

def get_slice_mask_from_slice_contour_data(series_slice: Dataset, slice_contour_data):
    slice_mask = create_empty_slice_mask(series_slice)
    for contour_coords in slice_contour_data:
        print(contour_coords)
        reshaped_contour_data = np.reshape(contour_coords, [len(contour_coords) // 3, 3]).astype(int)
        cols = reshaped_contour_data[:,0]
        rows = reshaped_contour_data[:,1]
        slice_mask[cols, rows] = True # Note the order of indices (cols before rows)
    return slice_mask

def create_empty_series_mask(series_data):
    ref_dicom_image = series_data[0]
    mask_dims = (int(ref_dicom_image.Columns), int(ref_dicom_image.Rows), len(series_data))
    mask = np.zeros(mask_dims)
    return mask

def create_empty_slice_mask(series_slice):
    mask_dims = (int(series_slice.Columns), int(series_slice.Rows))
    mask = np.zeros(mask_dims)
    return mask