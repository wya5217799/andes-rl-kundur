"""Regression tests for the R430 explicit-output-root successor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r430_adapted_sac_successor.py"


def _load():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("r430_successor_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_changes_only_engineering_successor_metadata() -> None:
    runner = _load()
    contract = runner.build_contract()
    assert contract["engineering_successor"]["successor_of"] == "R429"
    assert contract["engineering_successor"]["explicit_sac_out_root"] is True
    assert contract["training_contract"]["total_interaction_steps"] == 43_200
    assert contract["training_seeds"] == [401, 402, 403]


def test_every_training_shard_resolves_to_r430_only() -> None:
    runner = _load()
    probe = runner.output_root_probe()
    assert probe["passed"] is True
    assert set(probe["resolved"].values()) == {
        "results/research_loop/r430_adapted_sac_successor"
    }


def test_sac_dispatch_passes_explicit_out_root(monkeypatch) -> None:
    runner = _load()
    captured = {}
    monkeypatch.setattr(runner.base, "_assert_wsl_scratch", lambda: None)
    monkeypatch.setattr(runner.base, "load_seal", lambda: {})

    def fake_train(*args, **kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(runner.base, "_train_sac_arm_seed", fake_train)
    result = runner.train_arm_seed("cd_matd3_message", 401)
    assert result == "ok"
    assert captured["out_root"] == runner.OUT
    assert captured["require_seal"] is True


def test_shard_grammar_is_inherited() -> None:
    runner = _load()
    assert runner._parse_shard("train|cd_matd3_no_message|403") == (
        "train",
        "cd_matd3_no_message",
        403,
    )
