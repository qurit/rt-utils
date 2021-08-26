import os
from typing import List
from enum import IntEnum

import cv2 as cv
import numpy as np
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from rt_utils.utils import ROIData, SOPClassUID


def load_sorted_image_series(dicom_series_path: str):
    """
    File contains helper methods for loading / formatting DICOM images and contours
    """

    series_data = load_dcm_images_from_path(dicom_series_path)

    if len(series_data) == 0:
        raise Exception("No DICOM Images found in input path")

    # Sort slices in ascending order
    series_data.sort(key=get_slice_position, reverse=False)

    return series_data


def load_dcm_images_from_path(dicom_series_path: str) -> List[Dataset]:
    series_data = []
    for root, _, files in os.walk(dicom_series_path):
        for file in files:
            try:
                ds = dcmread(os.path.join(root, file))
                if hasattr(ds, 'pixel_array'):
                    series_data.append(ds)

            except Exception:
                # Not a valid DICOM file
                continue

    return series_data


def get_contours_coords(roi_data: ROIData, series_data):
    transformation_matrix = get_pixel_to_patient_transformation_matrix(series_data)

    series_contours = []
    for i, series_slice in enumerate(series_data):
        mask_slice = roi_data.mask[:, :, i]

        # Do not add ROI's for blank slices
        if np.sum(mask_slice) == 0:
            series_contours.append([])
            print("Skipping empty mask layer")
            continue

        # Create pin hole mask if specified
        if roi_data.use_pin_hole:
            mask_slice = create_pin_hole_mask(mask_slice, roi_data.approximate_contours)

        # Get contours from mask
        contours, _ = find_mask_contours(mask_slice, roi_data.approximate_contours)
        validate_contours(contours)

        # Format for DICOM
        formatted_contours = []
        for contour in contours:
            # Add z index
            contour = np.concatenate((np.array(contour), np.full((len(contour), 1), i)), axis=1)

            transformed_contour = apply_transformation_to_3d_points(contour, transformation_matrix)
            dicom_formatted_contour = np.ravel(transformed_contour).tolist()
            formatted_contours.append(dicom_formatted_contour)

        series_contours.append(formatted_contours)

    return series_contours


def find_mask_contours(mask: np.ndarray, approximate_contours: bool):
    approximation_method = cv.CHAIN_APPROX_SIMPLE if approximate_contours else cv.CHAIN_APPROX_NONE 
    contours, hierarchy = cv.findContours(mask.astype(np.uint8), cv.RETR_TREE, approximation_method)
    # Format extra array out of data
    for i, contour in enumerate(contours):
        contours[i] = [[pos[0][0], pos[0][1]] for pos in contour]
    hierarchy = hierarchy[0] # Format extra array out of data

    return contours, hierarchy


def create_pin_hole_mask(mask: np.ndarray, approximate_contours: bool):
    """
    Creates masks with pin holes added to contour regions with holes.
    This is done so that a given region can be represented by a single contour.
    """

    contours, hierarchy = find_mask_contours(mask, approximate_contours)
    pin_hole_mask = mask.copy()

    # Iterate through the hierarchy, for child nodes, draw a line upwards from the first point
    for i, array in enumerate(hierarchy):
        parent_contour_index = array[Hierarchy.parent_node]
        if parent_contour_index == -1: continue # Contour is not a child

        child_contour = contours[i]
        
        line_start = tuple(child_contour[0])

        pin_hole_mask = draw_line_upwards_from_point(pin_hole_mask, line_start, fill_value=0)
    return pin_hole_mask


def draw_line_upwards_from_point(mask: np.ndarray, start, fill_value: int) -> np.ndarray:
    line_width = 2
    end = (start[0], start[1] - 1)
    mask = mask.astype(np.uint8) # Type that OpenCV expects
    # Draw one point at a time until we hit a point that already has the desired value
    while mask[end] != fill_value:
        cv.line(mask, start, end, fill_value, line_width)

        # Update start and end to the next positions
        start = end
        end = (start[0], start[1] - line_width)
    return mask.astype(bool)


def validate_contours(contours: list):
    if len(contours) == 0:
        raise Exception("Unable to find contour in non empty mask, please check your mask formatting")

def get_pixel_to_patient_transformation_matrix(series_data):
    """
    https://nipy.org/nibabel/dicom/dicom_orientation.html
    """

    first_slice = series_data[0]

    offset = np.array(first_slice.ImagePositionPatient)
    row_spacing, column_spacing = first_slice.PixelSpacing
    slice_spacing = get_spacing_between_slices(series_data)
    row_direction, column_direction, slice_direction = get_slice_directions(first_slice)

    mat = np.identity(4, dtype=np.float32)
    mat[:3, 0] = row_direction * row_spacing
    mat[:3, 1] = column_direction * column_spacing
    mat[:3, 2] = slice_direction * slice_spacing
    mat[:3, 3] = offset

    return mat

def get_patient_to_pixel_transformation_matrix(series_data):
    first_slice = series_data[0]

    offset = np.array(first_slice.ImagePositionPatient)
    row_spacing, column_spacing = first_slice.PixelSpacing
    slice_spacing = get_spacing_between_slices(series_data)
    row_direction, column_direction, slice_direction = get_slice_directions(first_slice)

    # M = [ rotation&scaling   translation ]
    #     [        0                1      ]
    #
    # inv(M) = [ inv(rotation&scaling)   -inv(rotation&scaling) * translation ]
    #          [          0                                1                  ]

    linear = np.identity(3, dtype=np.float32)
    linear[0, :3] = row_direction / row_spacing
    linear[1, :3] = column_direction / column_spacing
    linear[2, :3] = slice_direction / slice_spacing

    mat = np.identity(4, dtype=np.float32)
    mat[:3, :3] = linear
    mat[:3, 3] = offset.dot(-linear.T)

    return mat

def apply_transformation_to_3d_points(points: np.ndarray, transformation_matrix: np.ndarray):
    """
        * Augment each point with a '1' as the fourth coordinate to allow translation
        * Multiply by a 4x4 transformation matrix
        * Throw away added '1's
    """
    vec = np.concatenate((points, np.ones((points.shape[0], 1))), axis=1)
    return vec.dot(transformation_matrix.T)[:, :3]

def get_slice_position(series_slice: Dataset):
    _, _, slice_direction = get_slice_directions(series_slice)
    return np.dot(slice_direction, series_slice.ImagePositionPatient)

def get_slice_directions(series_slice: Dataset):
    orientation = series_slice.ImageOrientationPatient
    row_direction = np.array(orientation[:3])
    column_direction = np.array(orientation[3:])
    slice_direction = np.cross(row_direction, column_direction)

    if not np.allclose(np.dot(row_direction, column_direction), 0.0, atol=1e-3) or\
            not np.allclose(np.linalg.norm(slice_direction), 1.0, atol=1e-3):
        raise Exception("Invalid Image Orientation (Patient) attribute")

    return row_direction, column_direction, slice_direction

def get_spacing_between_slices(series_data):
    if len(series_data) > 1:
        first = get_slice_position(series_data[0])
        last = get_slice_position(series_data[-1])
        return (last - first) / (len(series_data) - 1)

    # Return nonzero value for one slice just to make the transformation matrix invertible
    return 1.0


def create_series_mask_from_contour_sequence(series_data, contour_sequence: Sequence):
    mask = create_empty_series_mask(series_data)
    transformation_matrix = get_patient_to_pixel_transformation_matrix(series_data)

    # Iterate through each slice of the series, If it is a part of the contour, add the contour mask
    for i, series_slice in enumerate(series_data):
        slice_contour_data = get_slice_contour_data(series_slice, contour_sequence)
        if len(slice_contour_data):
            mask[:, :, i] = get_slice_mask_from_slice_contour_data(series_slice, slice_contour_data,
                transformation_matrix)
    return mask


def get_slice_contour_data(series_slice: Dataset, contour_sequence: Sequence):
    slice_contour_data = []
    
    # Traverse through sequence data and get all contour data pertaining to the given slice
    for contour in contour_sequence:
        for contour_image in contour.ContourImageSequence:
            if contour_image.ReferencedSOPInstanceUID == series_slice.SOPInstanceUID:
                slice_contour_data.append(contour.ContourData)

    return slice_contour_data


def get_slice_mask_from_slice_contour_data(series_slice: Dataset, slice_contour_data,
        transformation_matrix: np.ndarray):
    slice_mask = create_empty_slice_mask(series_slice)
    for contour_coords in slice_contour_data:
        fill_mask = get_contour_fill_mask(series_slice, contour_coords, transformation_matrix)
        # Invert values in the region to be filled. This will create holes where needed if contours are stacked on top of each other
        slice_mask[fill_mask == 1] = np.invert(slice_mask[fill_mask == 1])
    return slice_mask


def get_contour_fill_mask(series_slice: Dataset, contour_coords, transformation_matrix: np.ndarray):
    # Format data
    reshaped_contour_data = np.reshape(contour_coords, [len(contour_coords) // 3, 3])
    translated_contour_data = apply_transformation_to_3d_points(reshaped_contour_data, transformation_matrix)
    polygon = [np.around([translated_contour_data[:, :2]]).astype(np.int32)]

    # Create mask for the region. Fill with 1 for ROI
    fill_mask = create_empty_slice_mask(series_slice).astype(np.uint8)
    cv.fillPoly(img=fill_mask, pts=polygon, color=1)
    return fill_mask


def create_empty_series_mask(series_data):
    ref_dicom_image = series_data[0]
    mask_dims = (int(ref_dicom_image.Columns), int(ref_dicom_image.Rows), len(series_data))
    mask = np.zeros(mask_dims).astype(bool)
    return mask


def create_empty_slice_mask(series_slice):
    mask_dims = (int(series_slice.Columns), int(series_slice.Rows))
    mask = np.zeros(mask_dims).astype(bool)
    return mask


class Hierarchy(IntEnum):
    """
    Enum class for what the positions in the OpenCV hierarchy array mean
    """

    next_node = 0
    previous_node = 1
    first_child = 2
    parent_node = 3
