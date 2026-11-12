"""Turn a NIfTI volume into a mask on a DICOM series' own grid.

``add_roi`` takes a bare numpy array. It carries no affine, no orientation and
no spacing, so it can only assume the array already sits on the series' voxel
grid, indexed ``(Rows, Columns, Slices)``.

A NIfTI does not satisfy that assumption by accident. It carries its own axis
order and its own direction for each axis in its affine, and neither is
guaranteed to match the series the segmentation was drawn on. Handing
``nibabel.get_fdata()`` straight to ``add_roi`` is what makes an ROI come back
rotated, flipped or offset, and no fixed sequence of transposes and flips can
be right for arbitrary input: the correct rearrangement is whatever the two
affines say it is, and it differs per file.

``nifti_to_mask`` reads both geometries and resamples between them, so the
result is correct for any orientation, spacing or storage order:

    from rt_utils import RTStructBuilder
    from rt_utils.nifti import nifti_to_mask

    rtstruct = RTStructBuilder.create_new(dicom_series_path=series)
    mask = nifti_to_mask("segmentation.nii.gz", rtstruct.series_data)
    rtstruct.add_roi(mask=mask, name="liver")

This needs SimpleITK, which is an optional dependency: ``pip install
rt-utils[nifti]``. SimpleITK is used rather than nibabel because it reads the
NIfTI affine and resamples in one step, and because it converts NIfTI's RAS
convention to the LPS convention DICOM uses on the caller's behalf.
"""

from typing import List, Optional, Union
import os

import numpy as np
from pydicom.dataset import Dataset

from rt_utils import image_helper

SIMPLEITK_REQUIRED = (
    "nifti_to_mask needs SimpleITK, which rt-utils does not install by "
    "default. Install it with 'pip install rt-utils[nifti]' or "
    "'pip install SimpleITK'."
)


def _import_sitk():
    try:
        import SimpleITK as sitk
    except ImportError as error:  # pragma: no cover - depends on environment
        raise ImportError(SIMPLEITK_REQUIRED) from error

    return sitk


def series_reference_image(series_data: List[Dataset]):
    """An empty SimpleITK image describing the series' grid.

    Carries the geometry and nothing else: size, spacing, origin and
    direction. It exists to be a resampling target, so the pixel values are
    irrelevant and are never read.

    The direction matrix is built from ImageOrientationPatient. Its columns
    are the patient-space directions of the three index axes: along a row for
    increasing column index, down a column for increasing row index, and the
    slice normal. SimpleITK takes that matrix flattened in row-major order.
    """
    sitk = _import_sitk()

    reference_slice = series_data[0]
    rows = int(reference_slice.Rows)
    columns = int(reference_slice.Columns)
    row_spacing, column_spacing = (float(v) for v in reference_slice.PixelSpacing)
    slice_spacing = float(image_helper.get_spacing_between_slices(series_data))
    along_row, down_column, normal = image_helper.get_slice_directions(reference_slice)

    # SimpleITK indexes (x, y, z) = (column, row, slice), the transpose of the
    # mask layout, and demands a positive spacing on every axis.
    image = sitk.Image(columns, rows, len(series_data), sitk.sitkUInt8)
    image.SetOrigin(
        tuple(
            float(v)
            for v in image_helper.require_image_position_patient(reference_slice)
        )
    )
    image.SetSpacing((column_spacing, row_spacing, abs(slice_spacing) or 1.0))
    image.SetDirection(
        (
            float(along_row[0]),
            float(down_column[0]),
            float(normal[0]),
            float(along_row[1]),
            float(down_column[1]),
            float(normal[1]),
            float(along_row[2]),
            float(down_column[2]),
            float(normal[2]),
        )
    )

    return image


def nifti_to_mask(
    nifti: Union[str, os.PathLike],
    dicom_series: Union[str, os.PathLike, List[Dataset]],
    label: Optional[int] = None,
) -> np.ndarray:
    """Resample a NIfTI segmentation onto a DICOM series' grid.

    Parameters
    ----------
    nifti :
        Path to a NIfTI file (``.nii`` or ``.nii.gz``).
    dicom_series :
        The series to resample onto: a path to a directory, a list of
        datasets, or an ``RTStruct.series_data``.
    label :
        Which value in the volume to take as foreground. By default any
        non-zero voxel is foreground, which is what a single-structure mask
        wants. Give a label to pull one structure out of a multi-label
        segmentation, as produced by TotalSegmentator and similar tools.

    Returns
    -------
    np.ndarray
        A boolean mask shaped ``(Rows, Columns, Slices)``, ready for
        ``add_roi``.

    Notes
    -----
    Resampling uses nearest neighbour, so the result only ever contains
    values the input contained. Interpolating a label map would invent
    labels that lie between two real ones.

    The resampling grid is regular, as any image grid must be. On an
    unevenly spaced series the slice positions of that grid therefore follow
    the average spacing rather than each slice's own position, and a voxel
    may be read from slightly the wrong plane. The slice positions
    themselves are unaffected, since those come from the series when the
    contours are written.
    """
    sitk = _import_sitk()

    series_data = image_helper.load_sorted_image_series(dicom_series)
    volume = sitk.ReadImage(str(nifti))

    if volume.GetDimension() != 3:
        raise ValueError(
            f"Expected a 3D NIfTI volume, got {volume.GetDimension()} "
            "dimensions. A 4D file holds several volumes; select one before "
            "converting it."
        )

    if volume.GetNumberOfComponentsPerPixel() != 1:
        # A 4D NIfTI may also arrive as a 3D image of multi-component pixels
        # rather than as a 4D image, depending on how it was written.
        raise ValueError(
            "Expected a 3D NIfTI volume with one value per voxel, got "
            f"{volume.GetNumberOfComponentsPerPixel()} components per voxel. "
            "This holds several volumes; select one before converting it."
        )

    resampled = sitk.Resample(
        volume,
        series_reference_image(series_data),
        sitk.Transform(),  # identity: both are already in patient space
        sitk.sitkNearestNeighbor,
        0.0,
        volume.GetPixelID(),
    )

    # SimpleITK hands back (slice, row, column); masks are (row, column, slice).
    array = np.transpose(sitk.GetArrayFromImage(resampled), (1, 2, 0))

    if label is None:
        return array != 0

    mask = array == label
    if not mask.any():
        present = sorted(int(v) for v in np.unique(array) if v != 0)
        raise ValueError(
            f"Label {label} is not present in the resampled volume. "
            f"Labels found: {present or 'none'}."
        )

    return mask
