"""Tests for ``scripts/score_run.py`` — the consolidated paper-grade scoring
helper that replaces the ~6 copy-pasted ``_r{N}_score_*.py`` drivers that
accumulated in R38–R49 and got archived to ``scripts/_archive/round_scripts/``
during Codex's R45.

R50 optimization E covers only the testable surface:
``aggregate_scores(per_seed_overalls)`` — pure function that aggregates
{seed: {LS1, LS2, geo}} records into mean / range / std summary. The
ANDES-side ``score_seed(ckpt_dir, ...)`` driver is a thin wrapper around
load_agents + paper_path.run_scenario + paper_grade_axes.evaluate_trace
and only exercised by smoke / integration tests when a real ckpt is around.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_aggregate_scores_mean_and_range():
    from score_run import aggregate_scores

    per_seed = {
        49: {"LS1": 0.20, "LS2": 0.30, "geo": 0.25},
        50: {"LS1": 0.30, "LS2": 0.40, "geo": 0.35},
        51: {"LS1": 0.40, "LS2": 0.50, "geo": 0.45},
    }
    summary = aggregate_scores(per_seed)

    assert summary["n_seeds"] == 3
    assert abs(summary["mean_geo"] - 0.35) < 1e-9
    assert summary["min_geo"] == 0.25
    assert summary["max_geo"] == 0.45


def test_aggregate_scores_preserves_per_seed_records():
    from score_run import aggregate_scores

    per_seed = {49: {"LS1": 0.2, "LS2": 0.3, "geo": 0.25}}
    summary = aggregate_scores(per_seed)

    assert summary["per_seed"] == per_seed


def test_aggregate_scores_empty_input_yields_zero_seeds():
    from score_run import aggregate_scores

    summary = aggregate_scores({})

    assert summary["n_seeds"] == 0
    # No NaN landmines for downstream JSON serialization:
    assert summary["mean_geo"] is None
    assert summary["min_geo"] is None
    assert summary["max_geo"] is None


def test_aggregate_scores_includes_std_when_multiple_seeds():
    from score_run import aggregate_scores

    per_seed = {
        49: {"LS1": 0.1, "LS2": 0.1, "geo": 0.10},
        50: {"LS1": 0.2, "LS2": 0.2, "geo": 0.20},
    }
    summary = aggregate_scores(per_seed)

    # 0.1 and 0.2 → mean 0.15, sample std = 0.0707...
    assert abs(summary["std_geo"] - 0.07071067811865477) < 1e-6
