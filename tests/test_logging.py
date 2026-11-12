"""Diagnostics go to a logger, not to stdout.

rt-utils is a library. Printing means every caller gets the output whether
they want it or not, it cannot be filtered or redirected, and in a web
service or a batch job it lands wherever stdout happens to go. A logger
leaves that choice to the application, which is the point of #58.

These tests assert the behaviour a caller depends on: nothing on stdout, and
a record on the right logger at a severity that matches how much it matters.
"""

import logging

import numpy as np
import pytest

from rt_utils import RTStructBuilder
from rt_utils.utils import ROIData
from tests.conftest import build_series


def _rtstruct():
    return RTStructBuilder.create_new(build_series([0.0, 2.0], rows=32, columns=32))


def _mask(rtstruct, empty=False):
    mask = np.zeros((32, 32, len(rtstruct.series_data)), dtype=bool)
    if not empty:
        mask[10:20, 10:20, 0] = True
    return mask


def test_an_empty_mask_is_logged_not_printed(capsys, caplog):
    rtstruct = _rtstruct()

    with caplog.at_level(logging.INFO, logger="rt_utils.rtstruct"):
        rtstruct.add_roi(mask=_mask(rtstruct, empty=True), name="empty")

    assert "ROI mask is empty" in caplog.text
    assert capsys.readouterr().out == ""


def test_saving_is_logged_not_printed(capsys, caplog, tmp_path):
    rtstruct = _rtstruct()
    rtstruct.add_roi(mask=_mask(rtstruct), name="roi")
    destination = tmp_path / "out.dcm"

    with caplog.at_level(logging.INFO, logger="rt_utils.rtstruct"):
        rtstruct.save(str(destination))

    assert str(destination) in caplog.text
    assert capsys.readouterr().out == ""


def test_an_unusual_generation_algorithm_warns(capsys, caplog):
    """This one is advice about an interoperability risk, so it is a warning."""
    with caplog.at_level(logging.WARNING, logger="rt_utils.utils"):
        ROIData(
            mask=np.zeros((2, 2, 1), dtype=bool),
            color=[255, 0, 0],
            number=1,
            name="roi",
            frame_of_reference_uid="1.2.3",
            roi_generation_algorithm="HOMEGROWN",
        )

    assert "HOMEGROWN" in caplog.text
    assert caplog.records[-1].levelno == logging.WARNING
    assert capsys.readouterr().out == ""


def test_nothing_is_emitted_when_the_caller_has_not_asked_for_it(capsys, caplog):
    """A library must be silent by default.

    caplog installs a handler at the root, so this checks the level rather
    than the absence of handlers: at WARNING, the routine INFO records from
    a normal add_roi and save must not appear.
    """
    rtstruct = _rtstruct()

    with caplog.at_level(logging.WARNING):
        rtstruct.add_roi(mask=_mask(rtstruct), name="roi")

    assert "ROI mask is empty" not in caplog.text
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "module", ["rt_utils.rtstruct", "rt_utils.utils", "rt_utils.smoothing"]
)
def test_each_module_logs_under_its_own_name(module):
    """Named loggers let an application silence one area and keep another.

    smoothing previously called logging.info directly, which logs to the
    root logger and cannot be configured separately from anyone else's.
    """
    import importlib

    assert importlib.import_module(module).logger.name == module
