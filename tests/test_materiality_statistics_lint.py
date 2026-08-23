"""Tests for the materiality-statistics lint (guardrails G.3).

The lint scans claims for Holm/materiality wording and requires direct
boundary-test evidence. Branches:

1. no materiality wording                 -> OK        (exit 0)
2. materiality wording + boundary evidence -> OK        (exit 0)
3. materiality wording, no boundary test   -> VIOLATION (exit 1)
4. materiality wording + zero-null wording -> HINT      (exit 0)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_TOOLS = ROOT / "memory" / "tools"


def _load_lint():
    spec = importlib.util.spec_from_file_location(
        "materiality_statistics_lint", _TOOLS / "materiality_statistics_lint.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_LINT = _load_lint()


def test_no_materiality_wording_ok():
    code, _ = _LINT._classify("plain finding with no effect-size language.\n")
    assert code == "OK"


def test_boundary_evidence_ok():
    text = (
        "The effect is materially supported: direct sign-flip test at "
        "log(1.10) gives p=1/64, Holm-controlled (boundary test).\n"
    )
    code, _ = _LINT._classify(text)
    assert code == "OK"


def test_ci_lower_bound_only_violation():
    """The R473 failure mode: 'Holm-rejected' with a bootstrap CI lower
    bound but no direct boundary test must VIOLATE."""
    text = (
        "Holm-controlled p=0.015625, materially_supported=true; bootstrap "
        "CI95 lower bound 13.7% above the 10% materiality.\n"
    )
    code, notes = _LINT._classify(text)
    assert code == "VIOLATION"
    assert any("boundary" in note for note in notes)


def test_zero_null_with_boundary_hint():
    text = (
        "Zero-null sign-flip p=0.015625 and direct materiality test at the "
        "boundary log(1.10) p=2/64; Holm on the materiality p-values.\n"
    )
    code, notes = _LINT._classify(text)
    assert code in ("OK", "HINT")


def test_claim_file_missing_violation(monkeypatch, tmp_path):
    monkeypatch.setattr(_LINT, "CLAIMS_DIR", tmp_path)
    code, _ = _LINT.check_claim("CLM-9999")
    assert code == "VIOLATION"
