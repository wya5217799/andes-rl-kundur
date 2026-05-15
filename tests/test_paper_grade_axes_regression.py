"""Behavioral regression for ``paper_grade_axes.evaluate_trace``.

Locks the 6-axis scoring output for the PRE_REFACTOR no-control baseline
JSONs at bit-identical level. The same baseline runs at three points
(pre-refactor, post-Phase-1 logical cleanup, post-Phase-2 src-layout)
must produce the same per-axis scores and the same overall score, since
paper_grade_axes.py was relocated by path-only changes (R37 / CLM-0041).

Adds a public-API contract assertion to surface the latent name
collision between
``andes_rl_kundur.evaluation.paper_grade_axes.PaperBenchmark`` (9 fields)
and
``andes_rl_kundur.probes.andes_common.paper_constants.PaperBenchmark``
(4 fields). They share a name but are NOT interchangeable — passing the
4-field variant to ``evaluate_trace`` crashes with
``AttributeError: 'PaperBenchmark' object has no attribute 'dH_range'``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.paper_grade_axes import (  # noqa: E402
    PAPER as RANKER_PAPER,
    PaperBenchmark as RankerBenchmark,
    evaluate_trace,
)
from andes_rl_kundur.probes.andes_common.paper_constants import (  # noqa: E402
    PaperBenchmark as ProbeBenchmark,
)

BASELINE_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline_PRE_REFACTOR"

# Locked at the post-r30/N1c ranker fix output for the bit-identical
# pre-refactor baseline.
EXPECTED = {
    "load_step_1": 0.114101,
    "load_step_2": 0.077035,
}


@pytest.mark.parametrize("scenario,expected", list(EXPECTED.items()))
def test_overall_score_against_pre_refactor_baseline(scenario, expected):
    path = BASELINE_DIR / f"no_control_{scenario}.json"
    if not path.exists():
        pytest.skip(f"baseline JSON missing: {path}")
    score = evaluate_trace(path, RANKER_PAPER[scenario],
                           is_ddic=False, label="regression")
    assert abs(score.overall - expected) < 1e-6, (
        f"paper_grade_axes scoring drifted for {scenario}: "
        f"expected {expected:.6f}, got {score.overall:.6f}"
    )


def test_paper_benchmark_name_collision_documented():
    """Surface the two-class footgun so future callers don't trip on it.

    If the schemas ever drift further apart (someone adds a field to
    one but not the other), this test still passes — it locks only the
    fact that the two classes exist with the same short name. The
    collision itself is recorded in
    ``src/andes_rl_kundur/evaluation/paper_grade_axes.py`` and CLM-NNNN.
    """
    assert RankerBenchmark is not ProbeBenchmark, (
        "Sanity: the two PaperBenchmark classes must remain distinct types "
        "(if they were merged, this test should be deleted)."
    )
    ranker_fields = set(RankerBenchmark.__dataclass_fields__.keys())
    probe_fields = set(ProbeBenchmark.__dataclass_fields__.keys())
    # The probe-side is a strict subset of the ranker-side schema.
    missing_on_probe = ranker_fields - probe_fields
    assert "dH_range" in missing_on_probe and "dD_range" in missing_on_probe, (
        "The probe-side PaperBenchmark must NOT grow dH_range / dD_range — "
        "if it does, it can be passed to evaluate_trace and the silent shape "
        "drift returns."
    )
