"""RTROIInterpretedType: what kind of structure an ROI is.

A planning system uses it to tell targets from organs at risk, and to find
the structure that defines the patient outline. rt-utils always wrote an
empty value, so every structure it produced was of unstated type and had to
be reclassified by hand after import. This is #73.
"""

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils.utils import ROI_INTERPRETED_TYPES
from tests.conftest import build_series


def _rtstruct():
    return RTStructBuilder.create_new(build_series([0.0, 2.0], rows=32, columns=32))


def _mask(rtstruct):
    mask = np.zeros((32, 32, len(rtstruct.series_data)), dtype=bool)
    mask[10:20, 10:20, 0] = True
    return mask


def _interpreted_types(rtstruct):
    return [
        observation.RTROIInterpretedType
        for observation in rtstruct.ds.RTROIObservationsSequence
    ]


@pytest.mark.parametrize("value", ["PTV", "ORGAN", "EXTERNAL", "BRACHY_CHANNEL"])
def test_the_type_reaches_the_observation(value):
    rtstruct = _rtstruct()

    rtstruct.add_roi(mask=_mask(rtstruct), name="roi", roi_interpreted_type=value)

    assert _interpreted_types(rtstruct) == [value]


def test_the_default_is_unstated():
    """Empty is what earlier versions always wrote, so nothing changes."""
    rtstruct = _rtstruct()

    rtstruct.add_roi(mask=_mask(rtstruct), name="roi")

    assert _interpreted_types(rtstruct) == [""]


def test_each_roi_keeps_its_own_type():
    """The value must follow the ROI, not leak between them."""
    rtstruct = _rtstruct()

    rtstruct.add_roi(mask=_mask(rtstruct), name="target", roi_interpreted_type="PTV")
    rtstruct.add_roi(mask=_mask(rtstruct), name="rectum", roi_interpreted_type="ORGAN")
    rtstruct.add_roi(mask=_mask(rtstruct), name="unclassified")

    assert _interpreted_types(rtstruct) == ["PTV", "ORGAN", ""]


def test_the_type_is_tied_to_the_right_roi_number():
    """RTROIObservationsSequence is joined to the others by ROINumber."""
    rtstruct = _rtstruct()
    rtstruct.add_roi(mask=_mask(rtstruct), name="target", roi_interpreted_type="PTV")
    rtstruct.add_roi(mask=_mask(rtstruct), name="rectum", roi_interpreted_type="ORGAN")

    by_number = {
        int(obs.ReferencedROINumber): obs.RTROIInterpretedType
        for obs in rtstruct.ds.RTROIObservationsSequence
    }
    names = {
        int(roi.ROINumber): roi.ROIName for roi in rtstruct.ds.StructureSetROISequence
    }

    assert {names[n]: t for n, t in by_number.items()} == {
        "target": "PTV",
        "rectum": "ORGAN",
    }


def test_the_type_survives_a_save_and_reload(tmp_path):
    series = build_series([0.0, 2.0], rows=32, columns=32)
    rtstruct = RTStructBuilder.create_new(series)
    mask = np.zeros((32, 32, 2), dtype=bool)
    mask[10:20, 10:20, 0] = True
    rtstruct.add_roi(mask=mask, name="target", roi_interpreted_type="PTV")

    destination = str(tmp_path / "rt.dcm")
    rtstruct.save(destination)

    reloaded = RTStructBuilder.create_from(series, destination)
    assert _interpreted_types(reloaded) == ["PTV"]


def test_a_non_standard_term_is_accepted():
    """PS3.3 C.8.8.8 gives Defined Terms, which are extensible.

    Rejecting anything outside the list would stop a site using a term its
    own system understands, so the value is passed through as given.
    """
    rtstruct = _rtstruct()

    rtstruct.add_roi(
        mask=_mask(rtstruct), name="roi", roi_interpreted_type="SITE_SPECIFIC"
    )

    assert _interpreted_types(rtstruct) == ["SITE_SPECIFIC"]


def test_the_standard_terms_are_published_for_reference():
    assert "PTV" in ROI_INTERPRETED_TYPES
    assert "ORGAN" in ROI_INTERPRETED_TYPES
    assert "EXTERNAL" in ROI_INTERPRETED_TYPES
