"""Tying each contour to the slice it belongs to.

A contour names the image it was drawn on by ReferencedSOPInstanceUID. When
none of those images is in the series being loaded, every contour is dropped
and the mask comes back entirely empty -- previously with no error, no
warning and no indication that anything had gone wrong. "I am getting a 3d
mask -> 0s", in the words of #76.

That happens for two quite different reasons:

* the series given is genuinely not the one the structures were drawn on, or
  is only one of several the structure set references (#76);
* the images were re-written after the structures were made. Anonymisation
  tools regenerate SOPInstanceUIDs, which breaks the link while leaving the
  geometry untouched (#106, and the likeliest cause behind #82).

The first is a mistake and must be reported. The second is recoverable,
because the contours still say where they are in the patient, so there is an
opt-in to match on position instead.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils import image_helper
from tests.conftest import build_series

POSITIONS = [0.0, 2.0, 4.0]
ROWS = COLUMNS = 32


def _structure_set():
    """An RTStruct over one series, plus a mask to compare against."""
    series = build_series(POSITIONS, rows=ROWS, columns=COLUMNS)
    rtstruct = RTStructBuilder.create_new(series)

    mask = np.zeros((ROWS, COLUMNS, len(POSITIONS)), dtype=bool)
    mask[10:20, 10:20, 0] = True
    mask[5:12, 20:28, 2] = True  # a different shape, on a different slice
    rtstruct.add_roi(mask=mask, name="organ")

    return rtstruct, series, mask


def _reidentified_series():
    """The same geometry with fresh SOPInstanceUIDs, as an anonymiser leaves."""
    return build_series(POSITIONS, rows=ROWS, columns=COLUMNS)


def _load_against(series, ds):
    with pytest.warns(UserWarning):
        return RTStructBuilder.create_from(series, ds, warn_only=True)


def test_an_unmatched_roi_raises_rather_than_returning_zeros():
    """The silent empty mask is the whole complaint in #76."""
    rtstruct, _, _ = _structure_set()
    loaded = _load_against(_reidentified_series(), rtstruct.ds)

    with pytest.raises(Exception) as error:
        loaded.get_roi_mask_by_name("organ")

    assert "could be matched to a slice" in str(error.value)


def test_the_error_explains_both_causes_and_the_way_out():
    """Someone hitting this needs to know which of the two it is."""
    rtstruct, _, _ = _structure_set()
    loaded = _load_against(_reidentified_series(), rtstruct.ds)

    with pytest.raises(Exception) as error:
        loaded.get_roi_mask_by_name("organ")

    message = str(error.value)
    assert "2 contour(s)" in message
    assert "anonymisation" in message
    assert 'match_by="position"' in message


def test_matching_by_position_recovers_the_mask():
    """Geometry is intact, so the contours can still be placed. This is #106."""
    rtstruct, _, mask = _structure_set()
    loaded = _load_against(_reidentified_series(), rtstruct.ds)

    recovered = loaded.get_roi_mask_by_name("organ", match_by="position")

    assert np.array_equal(recovered, mask)


def test_matching_by_position_puts_contours_on_the_right_slices():
    """Equal voxel counts would also pass if every contour landed on one slice."""
    rtstruct, _, mask = _structure_set()
    loaded = _load_against(_reidentified_series(), rtstruct.ds)

    recovered = loaded.get_roi_mask_by_name("organ", match_by="position")

    per_slice = [int(recovered[:, :, i].sum()) for i in range(len(POSITIONS))]
    assert per_slice == [int(mask[:, :, i].sum()) for i in range(len(POSITIONS))]
    assert per_slice[1] == 0, "the middle slice carries no contour"


def test_matching_by_uid_is_still_the_default():
    """The ordinary path must be untouched."""
    rtstruct, series, mask = _structure_set()
    loaded = RTStructBuilder.create_from(series, rtstruct.ds)

    assert np.array_equal(loaded.get_roi_mask_by_name("organ"), mask)


def test_position_matching_agrees_with_uid_matching_when_both_work():
    """Where the identifiers are intact, the two must not disagree."""
    rtstruct, series, mask = _structure_set()
    loaded = RTStructBuilder.create_from(series, rtstruct.ds)

    assert np.array_equal(
        loaded.get_roi_mask_by_name("organ", match_by="position"), mask
    )


def test_an_unrecognised_strategy_is_rejected():
    rtstruct, series, _ = _structure_set()
    loaded = RTStructBuilder.create_from(series, rtstruct.ds)

    with pytest.raises(ValueError, match="Invalid slice matching strategy"):
        loaded.get_roi_mask_by_name("organ", match_by="nearest-ish")


def test_an_roi_with_no_contours_at_all_is_still_empty_not_an_error():
    """An ROI may legitimately hold nothing; that is not a matching failure."""
    series = build_series(POSITIONS, rows=ROWS, columns=COLUMNS)
    mask = image_helper.create_series_mask_from_contour_sequence(series, [])

    assert mask.shape == (ROWS, COLUMNS, len(POSITIONS))
    assert not mask.any()
