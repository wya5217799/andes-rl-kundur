from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r381_gate_b4_deterministic.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r381", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_freezes_only_the_three_formal_commands_and_closed_contract() -> None:
    runner = _load_runner()
    parser = runner.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert set(subparsers.choices) == {"rehearse", "prepare", "execute"}
    assert runner._contract_is_closed(runner.build_contract()) is True
    assert runner._source_paths()["runner"] == RUNNER
    assert "r379_analysis" in runner._parent_paths()
