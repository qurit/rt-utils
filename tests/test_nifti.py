"""Converting a NIfTI segmentation onto a DICOM series' grid.

The point of ``nifti_to_mask`` is that it does not care how the NIfTI happens
to be stored. The same structure written with permuted axes, flipped axes or
a different voxel size must come back as the same mask, because the affine
says where each voxel really is.

So these tests do not compare against a hand-written expected array. They take
a mask on the series grid, push it out to a NIfTI with its storage
deliberately rearranged, convert it back, and require the original mask
exactly. A transpose-and-hope implementation passes the untouched case and
fails every rearranged one.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from tests.conftest import build_series, save_dataset

sitk = pytest.importorskip("SimpleITK", reason="SimpleITK is an optional extra")

from rt_utils.nifti import nifti_to_mask, series_reference_image  # noqa: E402

# Non-square and anisotropic, so an axis or spacing mix-up cannot cancel out.
ROWS, COLUMNS, SLICES = 24, 40, 6
SPACING = (3.0, 1.5)  # (between rows, between columns)


def _series():
    return build_series(
        [0.0, 2.0, 4.0, 6.0, 8.0, 10.0],
        rows=ROWS,
        columns=COLUMNS,
        pixel_spacing=SPACING,
    )


def _known_mask():
    """An asymmetric block, so every axis is distinguishable."""
    mask = np.zeros((ROWS, COLUMNS, SLICES), dtype=bool)
    mask[4:10, 25:35, 1:4] = True
    return mask


def _write_nifti(mask, series_data, path, rearrange=None, value=1):
    """Store a mask as a NIfTI, optionally rearranging how it is laid out.

    ``rearrange`` is applied in SimpleITK's physical space, so it changes the
    storage order and the affine together, exactly as a different exporter
    would. The structure stays where it is in the patient.
    """
    reference = series_reference_image(series_data)

    # Masks are (row, column, slice); SimpleITK wants (slice, row, column).
    array = np.transpose(mask.astype(np.uint8) * value, (2, 0, 1))
    volume = sitk.GetImageFromArray(array)
    volume.CopyInformation(reference)

    if rearrange is not None:
        volume = rearrange(volume)

    sitk.WriteImage(volume, str(path))
    return volume


REARRANGEMENTS = {
    "untouched": None,
    "axes_permuted": lambda v: sitk.PermuteAxes(v, [2, 0, 1]),
    "axes_flipped": lambda v: sitk.Flip(v, [True, False, True]),
    "permuted_and_flipped": lambda v: sitk.Flip(
        sitk.PermuteAxes(v, [1, 2, 0]), [False, True, True]
    ),
}


@pytest.mark.parametrize("name", list(REARRANGEMENTS))
def test_the_mask_survives_however_the_nifti_is_stored(tmp_path, name):
    """However the volume is laid out, the affine says where it belongs."""
    series_data = _series()
    mask = _known_mask()
    path = tmp_path / "seg.nii.gz"
    _write_nifti(mask, series_data, path, REARRANGEMENTS[name])

    converted = nifti_to_mask(path, series_data)

    assert converted.shape == mask.shape
    assert np.array_equal(converted, mask)


def test_reading_the_array_directly_is_not_equivalent(tmp_path):
    """Show the failure this function exists to prevent.

    Handing the stored array straight to add_roi, as the reports in #102 and
    #110 do, gives a different structure - when it is even the right shape.
    """
    series_data = _series()
    mask = _known_mask()
    path = tmp_path / "seg.nii.gz"
    _write_nifti(mask, series_data, path, REARRANGEMENTS["permuted_and_flipped"])

    raw = sitk.GetArrayFromImage(sitk.ReadImage(str(path))) != 0
    converted = nifti_to_mask(path, series_data)

    assert np.array_equal(converted, mask)
    assert raw.shape != mask.shape or not np.array_equal(raw, mask)


def test_a_different_voxel_size_is_resampled(tmp_path):
    """A segmentation drawn at another resolution still lands correctly."""
    series_data = _series()
    mask = _known_mask()
    path = tmp_path / "seg.nii.gz"
    volume = _write_nifti(mask, series_data, path)

    # Re-grid to half the voxel size, keeping the same physical extent.
    fine = sitk.Resample(
        volume,
        [s * 2 for s in volume.GetSize()],
        sitk.Transform(),
        sitk.sitkNearestNeighbor,
        volume.GetOrigin(),
        [s / 2 for s in volume.GetSpacing()],
        volume.GetDirection(),
        0.0,
        volume.GetPixelID(),
    )
    sitk.WriteImage(fine, str(path))

    converted = nifti_to_mask(path, series_data)

    # Nearest neighbour through two re-grids of a block with straight edges
    # is exact; anything else would mean the geometry is off.
    assert np.array_equal(converted, mask)


def test_label_selects_one_structure(tmp_path):
    """Multi-label segmentations are what TotalSegmentator and friends emit."""
    series_data = _series()
    first = _known_mask()
    second = np.zeros_like(first)
    second[12:18, 5:15, 2:5] = True

    combined = np.zeros((ROWS, COLUMNS, SLICES), dtype=np.uint8)
    combined[first] = 3
    combined[second] = 7

    reference = series_reference_image(series_data)
    volume = sitk.GetImageFromArray(np.transpose(combined, (2, 0, 1)))
    volume.CopyInformation(reference)
    path = tmp_path / "multi.nii.gz"
    sitk.WriteImage(volume, str(path))

    assert np.array_equal(nifti_to_mask(path, series_data, label=3), first)
    assert np.array_equal(nifti_to_mask(path, series_data, label=7), second)
    # Without a label, every non-zero voxel is foreground.
    assert np.array_equal(nifti_to_mask(path, series_data), first | second)


def test_a_missing_label_says_which_are_present(tmp_path):
    series_data = _series()
    path = tmp_path / "seg.nii.gz"
    _write_nifti(_known_mask(), series_data, path, value=5)

    with pytest.raises(ValueError) as error:
        nifti_to_mask(path, series_data, label=9)

    assert "Labels found: [5]" in str(error.value)


def test_a_genuinely_four_dimensional_file_is_refused(tmp_path):
    """Several volumes in one file cannot be resolved to a single mask."""
    series_data = _series()
    one = sitk.GetImageFromArray(np.zeros((SLICES, ROWS, COLUMNS), np.uint8))
    volume = sitk.JoinSeries([one, one])
    assert volume.GetDimension() == 4
    path = tmp_path / "fourd.nii.gz"
    sitk.WriteImage(volume, str(path))

    with pytest.raises(ValueError, match="3D NIfTI"):
        nifti_to_mask(path, series_data)


def test_multi_component_voxels_are_refused(tmp_path):
    """The same file can instead arrive as 3D with several values per voxel.

    SimpleITK reports that as three dimensions, so checking the dimension
    alone lets it through, and the array then has one axis too many.
    """
    series_data = _series()
    volume = sitk.GetImageFromArray(
        np.zeros((SLICES, ROWS, COLUMNS, 3), np.uint8), isVector=True
    )
    assert volume.GetDimension() == 3
    path = tmp_path / "vector.nii.gz"
    sitk.WriteImage(volume, str(path))

    with pytest.raises(ValueError, match="components per voxel"):
        nifti_to_mask(path, series_data)


def test_the_result_is_accepted_by_add_roi(tmp_path):
    """The whole point: the output must drop straight into add_roi."""
    series_data = _series()
    mask = _known_mask()
    path = tmp_path / "seg.nii.gz"
    _write_nifti(mask, series_data, path, REARRANGEMENTS["axes_permuted"])

    rtstruct = RTStructBuilder.create_new(series_data)
    rtstruct.add_roi(mask=nifti_to_mask(path, series_data), name="from-nifti")

    assert np.array_equal(rtstruct.get_roi_mask_by_name("from-nifti"), mask)


def test_a_series_path_works_as_well_as_datasets(tmp_path):
    """dicom_series accepts whatever create_new accepts."""
    import os

    series_data = _series()
    series_dir = tmp_path / "series"
    series_dir.mkdir()
    for index, ds in enumerate(series_data):
        save_dataset(ds, os.path.join(series_dir, f"s{index:03}.dcm"))

    mask = _known_mask()
    path = tmp_path / "seg.nii.gz"
    _write_nifti(mask, series_data, path)

    assert np.array_equal(nifti_to_mask(path, str(series_dir)), mask)
