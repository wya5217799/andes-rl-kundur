"""Tests for the external deep-review intake lint (guardrails G.5).

The lint gates rounds that absorb an external deep-review package. Branches:

1. no external-review citation         -> OK        (exit 0)
2. citation + full intake              -> OK        (exit 0)
3. citation, no ARTIFACTS registration -> VIOLATION (exit 1)
4. citation, no hash record            -> VIOLATION (exit 1)
5. citation, feed without findings     -> VIOLATION (exit 1)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_TOOLS = ROOT / "memory" / "tools"


def _load_lint():
    spec = importlib.util.spec_from_file_location(
        "external_review_intake_lint", _TOOLS / "external_review_intake_lint.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_LINT = _load_lint()


def _make_round(tmp_path: Path, round_id: str, plan: str, feed: str | None = None,
                artifacts: dict | None = None, bundle_with_sha256sums: bool = False):
    rounds = tmp_path / "memory" / "rounds" / round_id
    rounds.mkdir(parents=True)
    (rounds / "plan.md").write_text(plan, encoding="utf-8")
    line_dir = tmp_path / "paper" / "test_line"
    feed_dir = line_dir / "reports"
    feed_dir.mkdir(parents=True, exist_ok=True)
    if feed is not None:
        (feed_dir / f"{round_id}.md").write_text(feed, encoding="utf-8")
    artifacts_payload = artifacts if artifacts is not None else {"artifacts": []}
    if artifacts is None:
        artifacts_payload["artifacts"].append(
            {"id": "feeds", "purpose": "experiment-feeds",
             "path": "paper/test_line/reports", "status": "active"}
        )
    (line_dir / "ARTIFACTS.json").write_text(json.dumps(artifacts_payload), encoding="utf-8")
    if bundle_with_sha256sums:
        bundle = line_dir / "working" / "review_bundle"
        bundle.mkdir(parents=True)
        (bundle / "SHA256SUMS").write_text("abc  review.md\n", encoding="utf-8")
        (bundle / "review.md").write_text("review body", encoding="utf-8")


_PLAN_WITH_CITATION = (
    "state: active\nround: R999\nmanuscript_line: test-line\n"
    "external deep review of the placebo wiring (deep-review package) was absorbed.\n"
)
_FEED_WITH_DISPOSITION = (
    "## Findings\nP0-1 routing: FIXED. P1-2 batch mixing: FIXED.\n"
    "## Verdict\nDISPROVED -> redesign adopted.\n"
)


def test_no_citation_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(tmp_path, "R999", "state: active\nround: R999\nplain round.\n")
    code, _ = _LINT.check("R999")
    assert code == 0


def test_full_intake_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    artifacts = {
        "artifacts": [
            {"id": "x", "purpose": "external-review",
             "path": "paper/test_line/working/review_bundle", "status": "active"}
        ]
    }
    _make_round(tmp_path, "R999", _PLAN_WITH_CITATION, _FEED_WITH_DISPOSITION,
                artifacts=artifacts, bundle_with_sha256sums=True)
    code, messages = _LINT.check("R999")
    assert code == 0, messages


def test_missing_registration_violation(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    _make_round(tmp_path, "R999", _PLAN_WITH_CITATION, _FEED_WITH_DISPOSITION)
    code, messages = _LINT.check("R999")
    assert code == 1
    assert any("ARTIFACTS.json" in m for m in messages)


def test_missing_hash_record_violation(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    artifacts = {
        "artifacts": [
            {"id": "x", "purpose": "external-review",
             "path": "paper/test_line/working/review_bundle", "status": "active"}
        ]
    }
    _make_round(tmp_path, "R999", _PLAN_WITH_CITATION, _FEED_WITH_DISPOSITION,
                artifacts=artifacts)
    code, messages = _LINT.check("R999")
    assert code == 1
    assert any("hash" in m for m in messages)


def test_feed_without_disposition_violation(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "ROOT", tmp_path)
    artifacts = {
        "artifacts": [
            {"id": "x", "purpose": "external-review",
             "path": "paper/test_line/working/review_bundle", "status": "active"}
        ]
    }
    _make_round(tmp_path, "R999", _PLAN_WITH_CITATION,
                "## Observations\nplain feed with only trajectory tables.\n",
                artifacts=artifacts, bundle_with_sha256sums=True)
    code, messages = _LINT.check("R999")
    assert code == 1
    assert any("feed" in m for m in messages)
