"""Conformance test: rt-utils vs RTMaskConformanceTest analytic ground truth.

Runs only when the `conformance` extra is installed:

    pip install -e .[conformance]
    pytest tests/test_conformance.py -v

Without the extra, the module is skipped (importorskip), so default test
runs are unaffected.

rt-utils returns masks as in-memory numpy arrays. Empirically (verified
against the analytic ground truth across all seven primitives) the
populated array's axis order is ``(Y, X, Z)``: although
``image_helper.create_empty_series_mask`` allocates it nominally as
``(Columns, Rows, Slices)``, the cv2.fillPoly pass that fills the array
operates in ``(row, col)`` ≡ ``(Y, X)`` space and leaves the data in
``(Y, X, Z)`` order. The fixture transposes via ``np.transpose(2, 0, 1)``
to SimpleITK / NIfTI's ``(Z, Y, X)`` convention, copies the geometry from
the matching ground-truth NIfTI, and writes the prediction to disk so
``evaluate_one`` can do its geometry precheck and metric pass exactly as
it does for the file-based converters.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

# Skip cleanly if the conformance extra isn't installed, so that
# `pytest tests/` without the extra still passes.
rtmask_conformance = pytest.importorskip(  # noqa: F841
    "rtmask_conformance",
    reason="install the `conformance` extra: pip install -e .[conformance]",
)

import SimpleITK as sitk  # noqa: E402

from rtmask_conformance import CONFORMANCE_ROIS, generate_fixture, load_config  # noqa: E402
from rtmask_conformance.generate import GenerateOptions  # noqa: E402
from rtmask_conformance.verify import Status, evaluate_one  # noqa: E402

from rt_utils import RTStructBuilder  # noqa: E402

_CONFIG_YAML = Path(__file__).with_name("conformance.yaml")


@pytest.fixture(scope="session")
def conformance_fixture(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate the synthetic CT + RTSTRUCT + analytic GT NIfTIs once per session.

    ``n_quadrature=2`` keeps the fixture build under ~30 s; the published
    default of 8 is overkill for a CI gate.
    """
    out = tmp_path_factory.mktemp("conformance_fixture")
    generate_fixture(out, options=GenerateOptions(n_quadrature=2))
    return out


@pytest.fixture(scope="session")
def predictions(
    conformance_fixture: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """Drive ``RTStructBuilder.create_from`` once per session, write each ROI's
    mask to ``<roi>.nii.gz`` with the GT's geometry copied verbatim.

    Why we copy GT geometry rather than re-deriving it: rt-utils returns a
    bare numpy array with no spatial metadata, while ``evaluate_one`` runs a
    geometry precheck (origin / spacing / size / direction). The CT slices
    in the fixture and the analytic GT NIfTIs share the same geometry by
    construction, so copying the GT's metadata onto the prediction is
    equivalent to re-deriving it from the CT — and one less place to drift.

    Axis order: rt-utils' populated mask is ``(Y, X, Z)`` (see module
    docstring). SimpleITK's ``GetImageFromArray`` expects ``(Z, Y, X)``.
    ``transpose(2, 0, 1)`` is the bridge.
    """
    pred_dir = tmp_path_factory.mktemp("preds")

    rtstruct = RTStructBuilder.create_from(
        dicom_series_path=str(conformance_fixture / "refct"),
        rt_struct_path=str(conformance_fixture / "rtstruct" / "primitives_planar.dcm"),
    )

    gt_dir = conformance_fixture / "groundtruth"
    for roi in rtstruct.get_roi_names():
        # Skip ROIs that aren't part of the conformance suite (defensive — the
        # fixture only ships the seven, but a future fixture variant might add).
        gt_path = gt_dir / f"{roi}.nii.gz"
        if not gt_path.is_file():
            continue

        mask_yxz = rtstruct.get_roi_mask_by_name(roi)        # bool (Y, X, Z)
        mask_zyx = np.transpose(mask_yxz, (2, 0, 1)).astype(np.uint8)

        gt_img = sitk.ReadImage(str(gt_path))
        pred_img = sitk.GetImageFromArray(mask_zyx)
        pred_img.CopyInformation(gt_img)
        sitk.WriteImage(pred_img, str(pred_dir / f"{roi}.nii.gz"))

    return pred_dir


@pytest.fixture(scope="session")
def conformance_config():
    """Resolve thresholds: env var > tests/conformance.yaml > package defaults."""
    config_path = os.environ.get("RTMASK_CONFORMANCE_CONFIG")
    if config_path is None and _CONFIG_YAML.is_file():
        config_path = str(_CONFIG_YAML)
    return load_config(config_path)


@pytest.mark.parametrize("roi", CONFORMANCE_ROIS)
def test_conformance(
    roi: str, conformance_fixture: Path, predictions: Path, conformance_config
) -> None:
    pred = predictions / f"{roi}.nii.gz"
    gt = conformance_fixture / "groundtruth" / f"{roi}.nii.gz"
    result = evaluate_one(roi, pred, gt, conformance_config)
    if result.status != Status.PASS:
        pytest.fail(
            f"{roi}: {result.status.value}\n"
            f"  violations: {result.violations}\n"
            f"  metrics:    {result.metrics}\n"
            f"  thresholds: {result.thresholds}"
        )
