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
    PaperBenchmark,
    evaluate_trace,
)
from andes_rl_kundur.probes.andes_common.paper_constants import (  # noqa: E402
    LSFigureBenchmark,
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


def test_paperbenchmark_no_name_collision():
    """The ranker's ``PaperBenchmark`` (9 fields) and the probe layer's
    ``LSFigureBenchmark`` (4 fields) must NOT share a class name.

    Pre-2026-05-16 both classes were named ``PaperBenchmark`` — a foot-
    gun: importing the probe-side one and passing it to
    ``evaluate_trace`` crashes with ``AttributeError: 'PaperBenchmark'
    object has no attribute 'dH_range'``. The rename to
    ``LSFigureBenchmark`` makes the boundary explicit.
    """
    import andes_rl_kundur.probes.andes_common.paper_constants as pc
    assert not hasattr(pc, "PaperBenchmark"), (
        "probes.andes_common.paper_constants must NOT expose a "
        "PaperBenchmark symbol — that name belongs to the ranker. "
        "Use LSFigureBenchmark for the 4-field paper Fig.6/8 baseline."
    )
    assert PaperBenchmark.__name__ == "PaperBenchmark"
    assert LSFigureBenchmark.__name__ == "LSFigureBenchmark"

    # The probe-side stays narrower in scope (no action box / smoothness)
    ranker_fields = set(PaperBenchmark.__dataclass_fields__.keys())
    probe_fields = set(LSFigureBenchmark.__dataclass_fields__.keys())
    assert probe_fields < ranker_fields  # strict subset
    assert {"dH_range", "dD_range"} & ranker_fields == {"dH_range", "dD_range"}
    assert {"dH_range", "dD_range"} & probe_fields == set()


def test_action_utilization_docstring_doctest_runs():
    """R50 opt D: the _action_utilization docstring carries 4 doctest
    assertions that lock the formula (proj_span/paper_span, clipped [0,1]).
    Without this test the doctests don't run under the default
    ``testpaths = ['tests']`` config and would silently rot."""
    import doctest

    from andes_rl_kundur.evaluation import paper_grade_axes

    # _action_utilization is module-private; doctest.testmod finds it via the
    # module's __test__ + member walk.
    results = doctest.testmod(paper_grade_axes, verbose=False, raise_on_error=False)
    assert results.failed == 0, (
        f"paper_grade_axes doctests failed: {results.failed} of {results.attempted}"
    )
    assert results.attempted >= 4, (
        f"expected at least 4 doctests (the _action_utilization examples), "
        f"found only {results.attempted}"
    )
