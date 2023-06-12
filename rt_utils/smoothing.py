import SimpleITK as sitk
import numpy as np
from scipy import ndimage, signal
from typing import Union, Tuple
default_smoothing_parameters = {
    "scaling_factor": (3, 3, 1),
    "sigma": 2,
    "threshold": 0.4,
    "kernel_size": (3, 3, 1),
    "iterations": 2
}
def kron_upscale(mask: np.ndarray, scaling_factor: Tuple[int, ...]):
    return np.kron(mask, np.ones(scaling_factor))


def gaussian_blur(mask: np.ndarray, sigma: float):
    return ndimage.gaussian_filter(mask, sigma=sigma)


def binary_threshold(mask: np.ndarray, threshold: float):
    return mask > threshold

def median_filter(mask: np.ndarray, kernel_size: Union[int, Tuple[int, ...]]):
    return ndimage.median_filter(mask.astype(float), size=kernel_size, mode="nearest")

def pipeline_3d(mask: np.ndarray,
                iterations: int,
                scaling_factor: int,
                sigma: float,
                threshold: float,
                kernel_size: Union[int, Tuple[int, ...]]):
    scaling_factor = (scaling_factor, scaling_factor, 1)
    for i in range(iterations):
        mask = kron_upscale(mask=mask, scaling_factor=scaling_factor)
        mask = gaussian_blur(mask=mask, sigma=sigma)
        mask = binary_threshold(mask=mask, threshold=threshold)
        mask = median_filter(mask=mask, kernel_size=kernel_size)
        mask = mask.astype(bool)
    return mask

def pipeline_2d(mask: np.ndarray,
                iterations: int,
                scaling_factor: int,
                sigma: float,
                threshold: float,
                kernel_size: Union[int, Tuple[int, ...]]):
    scaling_factor = (scaling_factor, scaling_factor, 1)
    for i in range(iterations):
        mask = kron_upscale(mask=mask, scaling_factor=scaling_factor)
        for z in range(mask.shape[2]):
            slice = mask[:, : , z]
            slice = gaussian_blur(mask=slice, sigma=sigma)
            slice = binary_threshold(mask=slice, threshold=threshold)
            slice = median_filter(mask=slice, kernel_size=kernel_size)
            mask[:, :, z] = slice
        mask = mask.astype(bool)
    return mask

