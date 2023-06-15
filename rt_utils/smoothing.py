import SimpleITK as sitk
import numpy as np
from scipy import ndimage, signal
from typing import List, Union, Tuple, Dict
import logging

# A set of parameters that is know to work well
default_smoothing_parameters = {
    "iterations": 2,
    "crop_margins": [20, 20, 1],
    "np_kron": {"scaling_factor": 3},
    "ndimage_gaussian_filter": {"sigma": 2,
                                "radius": 3},
    "threshold": {"threshold": 0.4},
}
# A set of parameters that is know to work well
default_smoothing_parameters_2 = {
    "iterations": 3,
    "crop_margins": [20, 20, 1],
    "np_kron": {"scaling_factor": 2},
    "ndimage_gaussian_filter": {"sigma": 2,
                                "radius": 5},
    "threshold": {"threshold": 0.4},
}


def kron_upscale(mask: np.ndarray, params):
    """
    This function upscales masks like so

    1|2       1|1|2|2
    3|4  -->  1|1|2|2
              3|3|4|4
              3|3|4|4
    
    Scaling only in x and y direction          
    """

    scaling_array = (params["scaling_factor"], params["scaling_factor"], 1)
    
    return np.kron(mask, np.ones(scaling_array))

def gaussian_blur(mask: np.ndarray, params):
    return ndimage.gaussian_filter(mask, **params)

def binary_threshold(mask: np.ndarray, params):
    return mask > params["threshold"]

def get_new_margin(column, margin, column_length):
    """
    This functions takes a column (of x, y, or z) coordinates and adds a margin.
    If margin exceeds mask size, the margin is returned to most extreme possible values
    """
    new_min = column.min() - margin
    if new_min < 0:
        new_min = 0
    
    new_max = column.max() + margin
    if new_max > column_length:
        new_max = column_length

    return new_min, new_max
    
def crop_mask(mask: np.ndarray, crop_margins: np.ndarray) -> Tuple[np.ndarray, np.ndarray]: 
    """
    This function crops masks to non-zero pixels padded by crop_margins.
    Returns (cropped mask, bounding box)
    """ 
    x, y, z = np.nonzero(mask)

    x_min, x_max = get_new_margin(x, crop_margins[0], mask.shape[0])
    y_min, y_max = get_new_margin(y, crop_margins[1], mask.shape[1])
    z_min, z_max = get_new_margin(z, crop_margins[2], mask.shape[2])
    
    bbox = np.array([x_min, x_max, y_min, y_max, z_min, z_max])

    return mask[bbox[0]: bbox[1],
                bbox[2]: bbox[3],
                bbox[4]: bbox[5]], bbox

def restore_mask_dimensions(cropped_mask: np.ndarray, new_shape, bbox):
    """
    This funtion restores mask dimentions to the given shape.
    """
    new_mask = np.zeros(new_shape)

    new_mask[bbox[0]: bbox[1], bbox[2]: bbox[3], bbox[4]: bbox[5]] = cropped_mask
    return new_mask.astype(bool)

def iteration_2d(mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, ndimage_median_filter):
    """
    This is the actual set of filters. Applied iterative over z direction
    """
    cropped_mask = kron_upscale(mask=mask, params=np_kron)

    for z_idx in range(cropped_mask.shape[2]):
        slice = cropped_mask[:, :, z_idx]            
        slice = gaussian_blur(mask=slice, params=ndimage_gaussian_filter)
        slice = binary_threshold(mask=slice, params=threshold)

        cropped_mask[:, :, z_idx] = slice

    return cropped_mask

def iteration_3d(mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, ndimage_median_filter):
    """
    This is the actual filters applied iteratively in 3d.
    """
    cropped_mask = kron_upscale(mask=mask, params=np_kron)
    cropped_mask = gaussian_blur(mask=cropped_mask, params=ndimage_gaussian_filter)
    cropped_mask = binary_threshold(mask=cropped_mask, params=threshold)

    return cropped_mask

def pipeline(mask: np.ndarray,
             apply_smoothing: str,
             smoothing_parameters: Union[Dict, None]):
    """
    This is the entrypoint for smoothing a mask.
    """
    if not smoothing_parameters:
        smoothing_parameters = default_smoothing_parameters

    iterations = smoothing_parameters["iterations"]
    crop_margins = np.array(smoothing_parameters["crop_margins"])
    np_kron = smoothing_parameters["np_kron"]
    ndimage_gaussian_filter = smoothing_parameters["ndimage_gaussian_filter"]
    threshold = smoothing_parameters["threshold"]

    logging.info(f"Original mask shape {mask.shape}")
    logging.info(f"Cropping mask to non-zero")
    cropped_mask, bbox = crop_mask(mask, crop_margins=crop_margins)
    final_shape, final_bbox = get_final_mask_shape_and_bbox(mask=mask,
                                                            scaling_factor=np_kron["scaling_factor"],
                                                            iterations=iterations,
                                                            bbox=bbox)
    logging.info(f"Final scaling with factor of {np_kron['scaling_factor']} for {iterations} iterations")
    for i in range(iterations):
        logging.info(f"Iteration {i+1} out of {iterations}")
        logging.info(f"Applying filters")
        if apply_smoothing == "2d":
            cropped_mask = iteration_2d(cropped_mask,
                                np_kron=np_kron,
                                ndimage_gaussian_filter=ndimage_gaussian_filter,
                                threshold=threshold)
        elif apply_smoothing == "3d":
            cropped_mask = iteration_3d(cropped_mask,
                                np_kron=np_kron,
                                ndimage_gaussian_filter=ndimage_gaussian_filter,
                                threshold=threshold)
        else:
            raise Exception("Wrong dimension parameter. Use '2d' or '3d'.")
 
    # Restore dimensions
    logging.info("Restoring original mask shape")
    mask = restore_mask_dimensions(cropped_mask, final_shape, final_bbox)
    return mask

def get_final_mask_shape_and_bbox(mask, bbox, scaling_factor, iterations):
    """
    This function scales image shape and the bounding box which should be used for the final mask
    """

    final_scaling_factor = pow(scaling_factor, iterations)

    final_shape = np.array(mask.shape)
    final_shape[:2] *= final_scaling_factor

    bbox[:4] *= final_scaling_factor # Scale bounding box to final shape
    bbox[:4] -= round(final_scaling_factor * 0.5)  # Shift volumes to account for the shift that occurs as a result of the scaling
    logging.info("Final shape: ", final_shape)
    logging.info("Final bbox: ", bbox)
    return final_shape, bbox


