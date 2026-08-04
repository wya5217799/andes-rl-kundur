from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "diagnose_r290_topology_initialization.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("r290_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result(*, passed: bool, test_ok: bool, positive: int, max_real: float) -> dict:
    return {
        "passed": passed,
        "pflow_return": True,
        "changed_lines": ["Line_2"],
        "initialization_flags": {
            "system.exit_code": 0 if test_ok else 1,
            "tds.test_ok": test_ok,
        },
        "residual_pass": test_ok,
        "eigenvalue_finite": True,
        "positive_real_count": positive,
        "max_real": max_real,
    }


def test_diagnostic_classifies_fixed_initialization_but_physical_positive_mode() -> None:
    adapter = _load_adapter()
    results = {
        "nominal": {
            **_result(passed=True, test_ok=True, positive=0, max_real=0.0),
            "changed_lines": [],
        },
        "post_setup_direct": _result(
            passed=False,
            test_ok=False,
            positive=2,
            max_real=0.0455,
        ),
        "post_setup_set": _result(
            passed=False,
            test_ok=True,
            positive=2,
            max_real=0.0458,
        ),
        "post_setup_set_connectivity": _result(
            passed=False,
            test_ok=True,
            positive=2,
            max_real=0.0458,
        ),
        "pre_setup_set": _result(
            passed=False,
            test_ok=True,
            positive=2,
            max_real=0.0458,
        ),
    }

    analysis = adapter.classify_diagnostic(results)

    assert analysis["classification"] == "ROOT-CAUSE-BOUNDED-NO-VALID-PATH"
    assert analysis["direct_mutation_initialization_bug"] is True
    assert analysis["positive_mode_persists_after_valid_initialization"] is True
    assert analysis["eligible_methods"] == []


def test_adapter_freezes_methods_and_formal_commands() -> None:
    adapter = _load_adapter()

    assert adapter.ROUND_ID == "R290"
    assert adapter.QUESTION_ID == "Q-0047"
    assert adapter.TARGET_LINE == "Line_2"
    assert adapter.METHODS == (
        "post_setup_direct",
        "post_setup_set",
        "post_setup_set_connectivity",
        "pre_setup_set",
    )
    assert set(adapter.build_parser()._subparsers._group_actions[0].choices) == {
        "reproduce",
        "prepare",
        "run",
    }
