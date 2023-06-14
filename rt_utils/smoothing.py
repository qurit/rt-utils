import SimpleITK as sitk
import numpy as np
from scipy import ndimage, signal
from typing import Union, Tuple, Dict
import logging

default_smoothing_parameters = {
    "iterations": 3,
    "np_kron": {"scaling_factor": 2},
    "ndimage_gaussian_filter": {"sigma": 2,
                                "radius": 3},
    "threshold": {"threshold": 0.4},
    "ndimage_median_filter": {"size": 3,
                              "mode": "nearest"}
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

def crop_mask(mask: np.ndarray):
    three_d = (len(mask.shape) == 3)
    if three_d:
        x, y, z = np.nonzero(mask)
        x_max = (x.max() + 1) if x.max() < mask.shape[0] else x.max()
        y_max = (y.max() + 1) if y.max() < mask.shape[1] else y.max()
        z_max = (z.max() + 1) if z.max() < mask.shape[2] else z.max()
        bbox = np.array([x.min(), x_max, y.min(), y_max, z.min(), z_max])

        return mask[bbox[0]: bbox[1],
                    bbox[2]: bbox[3],
                    bbox[4]: bbox[5]], bbox
    else:
        x, y = np.nonzero(mask)
        x_max = (x.max() + 1) if x.max() < mask.shape[0] else x.max()
        y_max = (y.max() + 1) if y.max() < mask.shape[1] else y.max()
        bbox = [x.min(), x_max, y.min(), y_max]

        return mask[bbox[0]: bbox[1],
                    bbox[2]: bbox[3]], bbox

def restore_mask_dimensions(cropped_mask: np.ndarray, new_shape, bbox):
    new_mask = np.zeros(new_shape)

    new_mask[bbox[0]: bbox[1], bbox[2]: bbox[3], bbox[4]: bbox[5]] = cropped_mask
    return new_mask.astype(bool)

def iteration_2d(mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, ndimage_median_filter):
    cropped_mask = kron_upscale(mask=cropped_mask, **np_kron)

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
    np_kron = smoothing_parameters["np_kron"]
    ndimage_gaussian_filter = smoothing_parameters["ndimage_gaussian_filter"]
    threshold = smoothing_parameters["threshold"]
    ndimage_median_filter = smoothing_parameters["ndimage_median_filter"]

    logging.info(f"Original mask shape {mask.shape}")
    logging.info(f"Cropping mask to non-zero")
    cropped_mask, bbox = crop_mask(mask)
    final_shape, final_bbox = get_final_mask_shape_and_bbox(mask=mask,
                                                            scaling_factor=np_kron["scaling_factor"],
                                                            iterations=iterations,
                                                            bbox=bbox)
    logging.info(f"Final scaling with factor: {np_kron['scaling_factor']} in {iterations} iterations")
    for i in range(iterations):
        logging.info(f"Iteration {i} out of {iterations}")
        logging.info(f"Applying filters")

        if apply_smoothing == "2d":
            mask = iteration_2d(mask,
                                np_kron=np_kron,
                                ndimage_gaussian_filter=ndimage_gaussian_filter,
                                threshold=threshold,
                                ndimage_median_filter=ndimage_median_filter)
        elif apply_smoothing == "3d":
            mask = iteration_3d(mask,
                                np_kron=np_kron,
                                ndimage_gaussian_filter=ndimage_gaussian_filter,
                                threshold=threshold,
                                ndimage_median_filter=ndimage_median_filter)
        else:
            raise Exception("Wrong dimension parameter. Use '2d' or '3d'.")

    # Restore dimensions
    logging.info("Restoring original mask shape")
    mask = restore_mask_dimensions(cropped_mask, final_shape, final_bbox)
    return mask

def get_final_mask_shape_and_bbox(mask, bbox, scaling_factor, iterations):
    final_scaling_factor = pow(scaling_factor, iterations)

    final_shape = np.array(mask.shape)
    final_shape[:2] *= final_scaling_factor
    bbox[:4] *= final_scaling_factor
    logging.info("Final shape: ", final_shape)
    logging.info("Final bbox: ", bbox)
    return final_shape, bbox


