"""Smoothing of binary masks before contours are generated.

A mask drawn on the image grid has stair-stepped edges. Tracing contours from
it directly reproduces those steps. Smoothing upscales the mask, blurs and
re-thresholds it, and leaves the contour generator working at the higher
resolution, so the resulting contour follows a smoother boundary than the
original voxel grid can express.

The upscaled mask is only an intermediate. Contour coordinates are divided by
the scaling factor before being written, so the result is in the original
image's coordinates.
"""

import logging
from typing import Dict, Tuple, Union

import numpy as np
from scipy import ndimage

# A set of parameters that is known to work well.
default_smoothing_parameters_2d = {
    "scaling_iterations": 2,
    "filter_iterations": 3,
    "crop_margins": [20, 20, 1],
    "np_kron": {"scaling_factor": 3},
    "ndimage_gaussian_filter": {"sigma": 2, "radius": 3},
    "threshold": {"threshold": 0.5},
}


def kron_upscale(mask: np.ndarray, params: Dict) -> np.ndarray:
    """Upscale a mask in x and y, leaving z alone.

    1|2       1|1|2|2
    3|4  -->  1|1|2|2
              3|3|4|4
              3|3|4|4
    """
    scaling_array = (params["scaling_factor"], params["scaling_factor"], 1)

    return np.kron(mask, np.ones(scaling_array))


def gaussian_blur(mask: np.ndarray, params: Dict) -> np.ndarray:
    return ndimage.gaussian_filter(mask, **params)


def binary_threshold(mask: np.ndarray, params: Dict) -> np.ndarray:
    return mask > params["threshold"]


def get_new_margin(column, margin, column_length):
    """Add a margin to a coordinate range, clamped to the mask bounds."""
    new_min = column.min() - margin
    if new_min < 0:
        new_min = 0

    new_max = column.max() + margin
    if new_max > column_length:
        new_max = column_length

    return new_min, new_max


def crop_mask(
    mask: np.ndarray, crop_margins: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Crop to the non-zero region padded by crop_margins.

    Upscaling allocates scaling_factor**2 times the voxels, so cropping to the
    region that actually contains the ROI keeps that bounded.
    """
    x, y, z = np.nonzero(mask)

    x_min, x_max = get_new_margin(x, crop_margins[0], mask.shape[0])
    y_min, y_max = get_new_margin(y, crop_margins[1], mask.shape[1])
    z_min, z_max = get_new_margin(z, crop_margins[2], mask.shape[2])

    bbox = np.array([x_min, x_max, y_min, y_max, z_min, z_max])

    return mask[bbox[0] : bbox[1], bbox[2] : bbox[3], bbox[4] : bbox[5]], bbox


def restore_mask_dimensions(cropped_mask: np.ndarray, new_shape, bbox) -> np.ndarray:
    """Place a cropped mask back into a full-sized array."""
    new_mask = np.zeros(new_shape)

    new_mask[bbox[0] : bbox[1], bbox[2] : bbox[3], bbox[4] : bbox[5]] = cropped_mask
    return new_mask.astype(bool)


def iteration_2d(
    mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, filter_iterations
) -> np.ndarray:
    """Upscale once, then blur and threshold each slice independently."""
    cropped_mask = kron_upscale(mask=mask, params=np_kron)

    for _ in range(filter_iterations):
        for z_idx in range(cropped_mask.shape[2]):
            slice_mask = cropped_mask[:, :, z_idx]
            slice_mask = gaussian_blur(mask=slice_mask, params=ndimage_gaussian_filter)
            slice_mask = binary_threshold(mask=slice_mask, params=threshold)

            cropped_mask[:, :, z_idx] = slice_mask

    return cropped_mask


def iteration_3d(
    mask: np.ndarray, np_kron, ndimage_gaussian_filter, threshold, filter_iterations
) -> np.ndarray:
    """Upscale once, then blur and threshold the volume in three dimensions.

    Blurring across z as well as within each slice smooths the boundary
    between slices, which 2d smoothing leaves alone.
    """
    cropped_mask = kron_upscale(mask=mask, params=np_kron)

    for _ in range(filter_iterations):
        cropped_mask = gaussian_blur(mask=cropped_mask, params=ndimage_gaussian_filter)
        cropped_mask = binary_threshold(mask=cropped_mask, params=threshold)

    return cropped_mask


def get_final_mask_shape_and_bbox(mask, bbox, scaling_factor, scaling_iterations):
    """Shape and bounding box after all scaling iterations, in x and y only."""
    final_scaling_factor = scaling_factor**scaling_iterations

    final_shape = np.array(mask.shape)
    final_shape[:2] *= final_scaling_factor

    final_bbox = np.array(bbox)
    final_bbox[:4] *= final_scaling_factor

    return final_shape, final_bbox


def pipeline(
    mask: np.ndarray,
    apply_smoothing: str,
    smoothing_parameters: Union[Dict, None] = None,
) -> np.ndarray:
    """Smooth a mask, returning an upscaled mask.

    The returned mask is larger than the input in x and y by
    ``scaling_factor ** scaling_iterations``; z is unchanged. Contour
    coordinates are divided by that factor when they are written.
    """
    if not smoothing_parameters:
        smoothing_parameters = default_smoothing_parameters_2d

    if apply_smoothing not in ("2d", "3d"):
        raise ValueError(
            f"Invalid smoothing mode '{apply_smoothing}'. Expected one of "
            "['2d', '3d']."
        )

    if not mask.any():
        raise ValueError("Cannot smooth an empty mask")

    scaling_iterations = smoothing_parameters["scaling_iterations"]
    filter_iterations = smoothing_parameters["filter_iterations"]
    crop_margins = np.array(smoothing_parameters["crop_margins"])
    np_kron = smoothing_parameters["np_kron"]
    ndimage_gaussian_filter = smoothing_parameters["ndimage_gaussian_filter"]
    threshold = smoothing_parameters["threshold"]

    logging.info("Original mask shape %s", mask.shape)
    cropped_mask, bbox = crop_mask(mask, crop_margins=crop_margins)
    final_shape, final_bbox = get_final_mask_shape_and_bbox(
        mask=mask,
        scaling_factor=np_kron["scaling_factor"],
        scaling_iterations=scaling_iterations,
        bbox=bbox,
    )

    iteration = iteration_2d if apply_smoothing == "2d" else iteration_3d
    for i in range(scaling_iterations):
        logging.info("Scaling iteration %d of %d", i + 1, scaling_iterations)
        cropped_mask = iteration(
            cropped_mask,
            np_kron=np_kron,
            ndimage_gaussian_filter=ndimage_gaussian_filter,
            threshold=threshold,
            filter_iterations=filter_iterations,
        )

    return restore_mask_dimensions(cropped_mask, final_shape, final_bbox)
