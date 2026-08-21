from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_r387_regcv1_signed_authority_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r387_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runner_exposes_only_rehearse_prepare_execute() -> None:
    runner = _load_runner()

    parser = runner.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    assert set(subparsers.choices) == {"rehearse", "prepare", "execute"}


def test_execute_routes_to_r387_create_only_output(monkeypatch) -> None:
    runner = _load_runner()
    seen = {}

    def fake_execute(*, expected_sha256, out_dir):
        seen["expected_sha256"] = expected_sha256
        seen["out_dir"] = out_dir
        return "analysis-digest"

    monkeypatch.setattr(runner.lifecycle, "execute", fake_execute)

    result = runner.execute(expected_sha256="a" * 64)

    assert result == "analysis-digest"
    assert seen == {
        "expected_sha256": "a" * 64,
        "out_dir": ROOT / "results" / "research_loop" / "r387_regcv1_signed_authority_gate",
    }


def test_native_thread_limits_are_set_before_numpy_import() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    assert source.index('os.environ[_thread_variable] = "1"') < source.index("import numpy as np")
