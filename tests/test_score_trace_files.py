"""Tests for the R78 canonical dual-eval helper.

``score_trace_files`` is the single source of truth for the post-run
summary used by every eval entry point. These tests pin:
  1. Output dict shape (6 keys, all serializable).
  2. End-to-end behavior on real pre-refactor baseline traces — exercises
     ``evaluate_trace`` + ``compute_global_cum_rf`` via the helper.
  3. Empty input + missing scenario fallback behavior.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.summary import (  # noqa: E402
    format_headline,
    score_trace_files,
)

BASELINE_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline_PRE_REFACTOR"

EXPECTED_KEYS = {
    "LS1", "LS2", "geo",
    "cum_rf", "cum_rf_LS1", "cum_rf_LS2",
}


def _baseline_paths():
    """Path dict to the 2 pre-refactor no-control fixtures."""
    return {
        "load_step_1": BASELINE_DIR / "no_control_load_step_1.json",
        "load_step_2": BASELINE_DIR / "no_control_load_step_2.json",
    }


def test_score_trace_files_dual_eval():
    """End-to-end: both scenarios scored → all 6 keys non-None.

    Uses no-control baseline (is_ddic=False) so axes 6-11 collapse to 0
    and the geo is pulled down accordingly — still numeric, not None.
    """
    paths = _baseline_paths()
    if not all(p.exists() for p in paths.values()):
        pytest.skip("PRE_REFACTOR baseline fixtures missing")

    summary = score_trace_files(paths, label="test_no_control", is_ddic=False)

    assert set(summary.keys()) == EXPECTED_KEYS
    for k in EXPECTED_KEYS:
        assert summary[k] is not None, f"{k} should be populated"

    # Sanity: geo is in [0, 1] floor-clamped range; cum_rf is negative
    # (sum of squared frequency deviations).
    assert 0.0 < summary["geo"] <= 1.0
    assert summary["cum_rf"] < 0.0
    assert summary["cum_rf"] == pytest.approx(
        summary["cum_rf_LS1"] + summary["cum_rf_LS2"]
    )

    # 6-axis pre-refactor regression bit-identical to other tests
    # (test_paper_grade_axes_regression).
    assert summary["LS1"] == pytest.approx(0.114101, abs=1e-6)
    assert summary["LS2"] == pytest.approx(0.077035, abs=1e-6)


def test_score_trace_files_one_scenario_only(tmp_path):
    """When only LS1 is supplied, LS2 keys come back None and the geo /
    cum_rf aggregates reflect just the supplied scenario."""
    paths = _baseline_paths()
    if not paths["load_step_1"].exists():
        pytest.skip("PRE_REFACTOR baseline fixtures missing")

    summary = score_trace_files(
        {"load_step_1": paths["load_step_1"]},
        label="test_one_only", is_ddic=False,
    )

    assert summary["LS1"] is not None
    assert summary["LS2"] is None
    assert summary["cum_rf_LS1"] is not None
    assert summary["cum_rf_LS2"] is None
    # Geo over one value should equal that value (within floor clamp).
    assert summary["geo"] == pytest.approx(summary["LS1"], abs=1e-6)
    assert summary["cum_rf"] == pytest.approx(summary["cum_rf_LS1"])


def test_score_trace_files_empty():
    """Empty input → every key None (no crash, well-formed JSON-ready dict)."""
    summary = score_trace_files({}, label="test_empty")
    assert set(summary.keys()) == EXPECTED_KEYS
    for k in EXPECTED_KEYS:
        assert summary[k] is None


def test_score_trace_files_unknown_scenario_ignored(tmp_path):
    """Scenarios not in PAPER are silently skipped, not crashed."""
    paths = _baseline_paths()
    if not paths["load_step_1"].exists():
        pytest.skip("PRE_REFACTOR baseline fixtures missing")

    summary = score_trace_files(
        {
            "load_step_1": paths["load_step_1"],
            "some_other_scenario": paths["load_step_2"],  # not in PAPER
        },
        label="test_unknown_scen", is_ddic=False,
    )
    assert summary["LS1"] is not None
    # Helper doesn't expose unknown-scen results — they just don't appear.
    assert "some_other_scenario" not in summary


def test_score_trace_files_rejects_tds_failed_trace(tmp_path):
    """A failed partial trace must never produce a headline score."""
    baseline = _baseline_paths()["load_step_1"]
    if not baseline.exists():
        pytest.skip("PRE_REFACTOR baseline fixture missing")

    with baseline.open(encoding="utf-8") as f:
        failed_trace = json.load(f)
    failed_trace["tds_failed"] = True
    failed_trace["traces"] = failed_trace["traces"][:1]
    failed_trace["n_steps"] = 1

    trace_path = tmp_path / "failed_load_step_1.json"
    trace_path.write_text(json.dumps(failed_trace), encoding="utf-8")

    with pytest.raises(ValueError, match="tds_failed"):
        score_trace_files(
            {"load_step_1": trace_path},
            label="failed_trace", is_ddic=False,
        )


def test_format_headline_handles_full_summary():
    """``format_headline`` returns a compact one-line string."""
    summary = {
        "LS1": 0.41, "LS2": 0.41, "geo": 0.4099,
        "cum_rf": -1.2345, "cum_rf_LS1": -0.62, "cum_rf_LS2": -0.61,
    }
    s = format_headline(summary)
    assert "geo=0.4099" in s
    assert "cum_rf=-1.2345" in s
    assert "LS1=" in s and "LS2=" in s


def test_format_headline_handles_none():
    """``format_headline`` prints '--' for missing fields."""
    summary = {
        "LS1": None, "LS2": None, "geo": None,
        "cum_rf": None, "cum_rf_LS1": None, "cum_rf_LS2": None,
    }
    s = format_headline(summary)
    assert "geo=--" in s
    assert "cum_rf=--" in s


def test_summary_json_serializable():
    """The summary dict must round-trip through json.dumps / json.loads."""
    paths = _baseline_paths()
    if not all(p.exists() for p in paths.values()):
        pytest.skip("PRE_REFACTOR baseline fixtures missing")

    summary = score_trace_files(paths, label="test_json", is_ddic=False)
    text = json.dumps(summary)
    parsed = json.loads(text)
    assert set(parsed.keys()) == EXPECTED_KEYS
    assert parsed["geo"] == pytest.approx(summary["geo"])
