import SimpleITK as sitk
import numpy as np
from scipy import ndimage, signal
from typing import List, Union, Tuple, Dict
import logging

default_smoothing_parameters = {
    "iterations": 3,
    "crop_margins": [10, 10, 1],
    "np_kron": {"scaling_factor": 2},
    "ndimage_gaussian_filter": {"sigma": 2,
                                "radius": 3},
    "threshold": {"threshold": 0.4},
    "ndimage_median_filter": {"size": 3}
}

def kron_upscale(mask: np.ndarray, **kwargs):
    scaling_factor = (kwargs["scaling_factor"], kwargs["scaling_factor"], 1)
    return np.kron(mask, np.ones(scaling_factor))

def gaussian_blur(mask: np.ndarray, **kwargs):
    return ndimage.gaussian_filter(mask, **kwargs)

def binary_threshold(mask: np.ndarray, **kwargs):
    return mask > kwargs["threshold"]

def median_filter(mask: np.ndarray, **kwargs):
    return ndimage.median_filter(mask.astype(float), **kwargs)

def get_new_margin(column, margin, column_length):
    new_min = column.min() - margin
    if new_min < 0:
        new_min = 0
    
    new_max = column.max() + margin
    if new_max > column_length:
        new_max = column_length

    return new_min, new_max
    
def crop_mask(mask: np.ndarray, crop_margins: List[int]):  
    x, y, z = np.nonzero(mask)

    x_min, x_max = get_new_margin(x, crop_margins[0], mask.shape[0])
    y_min, y_max = get_new_margin(y, crop_margins[1], mask.shape[1])
    z_min, z_max = get_new_margin(z, crop_margins[2], mask.shape[2])
    
    bbox = np.array([x_min, x_max, y_min, y_max, z_min, z_max])

    return mask[bbox[0]: bbox[1],
                bbox[2]: bbox[3],
                bbox[4]: bbox[5]], bbox

def restore_mask_dimensions(cropped_mask: np.ndarray, new_shape, bbox):
    new_mask = np.zeros(new_shape)

    new_mask[bbox[0]: bbox[1], bbox[2]: bbox[3], bbox[4]: bbox[5]] = cropped_mask
    return new_mask.astype(bool)

def iteration_2d(mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, ndimage_median_filter):
    cropped_mask = kron_upscale(mask=mask, **np_kron)
    return cropped_mask
    for z_idx in range(cropped_mask.shape[2]):
        slice = cropped_mask[:, :, z_idx]            
        slice = gaussian_blur(mask=slice, **ndimage_gaussian_filter)
        slice = binary_threshold(mask=slice, **threshold)
        slice = median_filter(mask=slice, **ndimage_median_filter)

        cropped_mask[:, :, z_idx] = slice

    return cropped_mask

def iteration_3d(mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, ndimage_median_filter):
    cropped_mask = kron_upscale(mask=mask, **np_kron)
    cropped_mask = gaussian_blur(mask=cropped_mask, **ndimage_gaussian_filter)
    cropped_mask = binary_threshold(mask=cropped_mask, **threshold)
    cropped_mask = median_filter(mask=cropped_mask, **ndimage_median_filter)

    return cropped_mask

def pipeline(mask: np.ndarray,
             apply_smoothing: str,
             smoothing_parameters: Union[Dict, None]):

    if not smoothing_parameters:
        smoothing_parameters = default_smoothing_parameters

    iterations = smoothing_parameters["iterations"]
    crop_margins = smoothing_parameters["crop_margins"]

    np_kron = smoothing_parameters["np_kron"]
    ndimage_gaussian_filter = smoothing_parameters["ndimage_gaussian_filter"]
    threshold = smoothing_parameters["threshold"]
    ndimage_median_filter = smoothing_parameters["ndimage_median_filter"]

    print(f"Original mask shape {mask.shape}")
    print(f"Cropping mask to non-zero")
    cropped_mask, bbox = crop_mask(mask, crop_margins=crop_margins)
    final_shape, final_bbox = get_final_mask_shape_and_bbox(mask=mask,
                                                            scaling_factor=np_kron["scaling_factor"],
                                                            iterations=iterations,
                                                            bbox=bbox)
    print(f"Final scaling with factor of {np_kron['scaling_factor']} for {iterations} iterations")
    for i in range(iterations):
        print(f"Iteration {i+1} out of {iterations}")
        print(f"Applying filters")
        if apply_smoothing == "2d":
            cropped_mask = iteration_2d(cropped_mask,
                                np_kron=np_kron,
                                ndimage_gaussian_filter=ndimage_gaussian_filter,
                                threshold=threshold,
                                ndimage_median_filter=ndimage_median_filter)
        elif apply_smoothing == "3d":
            cropped_mask = iteration_3d(cropped_mask,
                                np_kron=np_kron,
                                ndimage_gaussian_filter=ndimage_gaussian_filter,
                                threshold=threshold,
                                ndimage_median_filter=ndimage_median_filter)
        else:
            raise Exception("Wrong dimension parameter. Use '2d' or '3d'.")
 
    # Restore dimensions
    print("Restoring original mask shape")
    mask = restore_mask_dimensions(cropped_mask, final_shape, final_bbox)
    return mask

def get_final_mask_shape_and_bbox(mask, bbox, scaling_factor, iterations):
    final_scaling_factor = pow(scaling_factor, iterations)

    final_shape = np.array(mask.shape)
    final_shape[:2] *= final_scaling_factor
    bbox[:4] *= final_scaling_factor
    print("Final shape: ", final_shape)
    print("Final bbox: ", bbox)
    return final_shape, bbox


