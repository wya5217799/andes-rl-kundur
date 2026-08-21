"""Tests for the external-theory intake lint (CLAUDE.md External theory intake).

The lint gates rounds that cite external math/theory (GPT Pro, theory-audit
bundle, external solvers).  Its five branches are exercised here against
synthetic round directories via monkeypatching the module ROOT, so the
test is independent of the real ledger:

1. no external-theory citation            -> OK        (exit 0)
2. algebra-only citation                  -> HINT      (exit 0)
3. mechanism citation, no intake/register -> VIOLATION (exit 1)
4. mechanism + intake, no feed            -> PENDING   (exit 1)
5. mechanism + intake + feed verdict      -> OK        (exit 0)
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_TOOLS = ROOT / "memory" / "tools"

import importlib.util  # noqa: E402
import sys  # noqa: E402


def _load_lint():
    spec = importlib.util.spec_from_file_location(
        "external_theory_intake_lint", _TOOLS / "external_theory_intake_lint.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_LINT = _load_lint()


def _make_round(tmp_path: Path, round_id: str, plan: str, feed: str | None = None):
    rounds = tmp_path / "memory" / "rounds" / round_id
    rounds.mkdir(parents=True)
    (rounds / "plan.md").write_text(plan, encoding="utf-8")
    if feed is not None:
        feed_dir = tmp_path / "paper" / "test-line" / "reports"
        feed_dir.mkdir(parents=True)
        (feed_dir / f"{round_id}.md").write_text(feed, encoding="utf-8")


_HEADER = "state: active\nround: R999\nmanuscript_line: test-line\n"


def test_no_external_theory_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(tmp_path, "R999", _HEADER + "plain reward-shaping round, no theory cited.\n")
    assert _LINT.lint("R999") == 0


def test_algebra_only_hint(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER + "uses the GPT Pro Parseval identity decomposition verbatim.\n",
    )
    assert _LINT.lint("R999") == 0


def test_mechanism_no_intake_violation(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER + "GPT Pro predicts this mechanism hypothesis holds after training.\n",
    )
    assert _LINT.lint("R999") == 1


def test_mechanism_intake_no_feed_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER
        + "GPT Pro mechanism prediction.\n"
        + "## Theory intake\nobservable: lambda_eff\n"
        + "  source: multiplier_trace.json\n",
    )
    assert _LINT.lint("R999") == 1


def test_mechanism_intake_feed_verdict_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER
        + "GPT Pro mechanism prediction.\n"
        + "## Theory intake\nobservable: lambda_eff\n"
        + "  source: multiplier_trace.json\n",
        feed="## Follow-up\nprediction supported: lambda_eff < 1.\n",
    )
    assert _LINT.lint("R999") == 0


def test_mechanism_not_pursued_passes_plan_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER
        + "GPT Pro mechanism prediction, but not-pursued: state trace not logged.\n",
    )
    # not-pursued registration satisfies the plan gate; no feed yet -> PENDING.
    assert _LINT.lint("R999") == 1


def test_internal_hypothesis_requires_list(monkeypatch, tmp_path):
    """R435 lesson: an internal diagnostic hypothesis (no external citation)
    is still a mechanism prediction and needs the observable list."""
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER
        + "the R432-derived mechanism hypothesis predicts the multiplier "
        + "floor will lower the common cost.\n",
    )
    assert _LINT.lint("R999") == 1


def test_internal_hypothesis_with_intake_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(
        tmp_path,
        "R999",
        _HEADER
        + "the R432-derived mechanism hypothesis predicts the floor holds.\n"
        + "## Theory intake\nobservable: lagrange_final\n"
        + "  source: diagnostics_summary.json\n",
        feed="## Follow-up\nprediction refuted: lagrange held, cost unchanged.\n",
    )
    assert _LINT.lint("R999") == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
