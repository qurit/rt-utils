"""What counts as a single image series.

``load_dcm_images_from_path`` walks a directory tree and accepts every file it
can read as an image, with no check that the result is one coherent stack. Two
ways of getting that wrong were silent:

* the same slices present twice in the tree — a backup folder, an export
  beside the original, a nested copy — stacked into a volume a whole multiple
  too long;
* two different images at one position — separate acquisitions, echoes or
  phases, or two overlapping series — stacked into a single axis, so a 128
  slice scan acquired twice became a 256 slice series.

Neither raised anything. The caller then had to build a mask for a volume
that does not exist, and the shape check rejected the mask they correctly
built from their own images. These are #122 and #98.
"""

import numpy as np
import pydicom
import pytest

from rt_utils import RTStructBuilder, image_helper
from tests.conftest import build_series


def test_repeated_copies_of_a_series_are_collapsed():
    """The same slices twice must load once. This is #122."""
    series = build_series([0.0, 2.0, 4.0, 6.0])
    duplicated = series + [copy_of(s) for s in series]

    loaded = image_helper.load_sorted_image_series(duplicated)

    assert len(loaded) == 4
    assert [float(s.ImagePositionPatient[2]) for s in loaded] == [0.0, 2.0, 4.0, 6.0]


def test_a_copy_does_not_have_to_be_the_same_object():
    """Deduplication is by SOPInstanceUID, not object identity.

    Files read twice from disk produce equal but distinct datasets.
    """
    series = build_series([0.0, 2.0])
    reread = [copy_of(s) for s in series]
    assert all(a is not b for a, b in zip(series, reread))

    loaded = image_helper.load_sorted_image_series(series + reread)

    assert len(loaded) == 2


def test_a_mask_for_the_real_series_is_accepted_despite_duplicates():
    """The symptom the reporter actually saw was a rejected mask."""
    series = build_series([0.0, 2.0, 4.0, 6.0])
    rtstruct = RTStructBuilder.create_new(series + [copy_of(s) for s in series])

    mask = np.zeros((32, 32, 4), dtype=bool)
    mask[10:20, 10:20, :] = True
    rtstruct.add_roi(mask=mask, name="roi")

    assert np.array_equal(rtstruct.get_roi_mask_by_name("roi"), mask)


def test_two_acquisitions_at_the_same_positions_are_refused():
    """Distinct images sharing a position must not be stacked. This is #98."""
    first = build_series([0.0, 2.0, 4.0])
    second = build_series([0.0, 2.0, 4.0])  # fresh SOPInstanceUIDs

    with pytest.raises(Exception) as error:
        image_helper.load_sorted_image_series(first + second)

    message = str(error.value)
    assert "same slice position" in message
    assert "acquisitions" in message


def test_the_refusal_names_the_position_and_both_images():
    """The message has to be enough to find the offending files."""
    first = build_series([0.0, 2.0])
    second = build_series([2.0])

    with pytest.raises(Exception) as error:
        image_helper.load_sorted_image_series(first + second)

    message = str(error.value)
    assert "2.0000" in message
    assert str(first[1].SOPInstanceUID) in message
    assert str(second[0].SOPInstanceUID) in message


def test_a_well_formed_series_is_untouched():
    """Nothing above may disturb the ordinary case."""
    series = build_series([4.0, 0.0, 2.0])  # deliberately out of order

    loaded = image_helper.load_sorted_image_series(series)

    assert len(loaded) == 3
    assert [float(s.ImagePositionPatient[2]) for s in loaded] == [0.0, 2.0, 4.0]


def test_positions_that_merely_sit_close_together_are_kept():
    """A fine but genuine slice increment is not a duplicate.

    The tolerance absorbs floating point noise only, so a 0.1 mm step must
    still load as two slices.
    """
    series = build_series([0.0, 0.1])

    loaded = image_helper.load_sorted_image_series(series)

    assert len(loaded) == 2


def copy_of(series_slice: pydicom.Dataset) -> pydicom.Dataset:
    """A separate dataset describing the same image, as a re-read would give."""
    duplicate = pydicom.Dataset(series_slice)
    duplicate.file_meta = series_slice.file_meta
    return duplicate
