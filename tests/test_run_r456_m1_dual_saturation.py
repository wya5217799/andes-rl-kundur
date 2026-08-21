from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r456_m1_dual_saturation",
    ROOT / "scripts/run_r456_m1_dual_saturation.py",
)
assert SPEC is not None and SPEC.loader is not None
R456 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R456)


def test_successor_rebinds_every_round_owned_path() -> None:
    assert R456.BASE.ROUND_ID == "R456"
    assert "R456" in str(R456.BASE.PLAN)
    assert "R456" in str(R456.BASE.CAPACITY)
    assert "R456" in str(R456.BASE.REHEARSAL)
    assert "R456" in str(R456.BASE.SEAL)
    assert "r456_" in str(R456.BASE.OUT)
    assert "r456_" in str(R456.BASE.STATE_SHARDS)
    assert "r456_" in str(R456.BASE.EVAL_SHARDS)


def test_shared_driver_shard_interface_dispatches_by_registered_arity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(R456.BASE, "run_state_shard", lambda value: f"state:{value}")
    monkeypatch.setattr(R456.BASE, "run_eval_shard", lambda value: f"eval:{value}")
    assert R456.dispatch_shard("cd_matd3_message|401") == ("state:cd_matd3_message|401")
    assert R456.dispatch_shard("U10_eta050|cd_matd3_message|401") == (
        "eval:U10_eta050|cd_matd3_message|401"
    )
    with pytest.raises(ValueError):
        R456.dispatch_shard("bad")


def test_successor_scientific_contract_keeps_inventory_and_thresholds() -> None:
    contract = R456.BASE.build_contract()
    assert contract["round"] == "R456"
    assert len(R456.BASE.state_shard_ids()) == 6
    assert len(R456.BASE.eval_shard_ids()) == 30
    assert contract["state_trajectory_count"] == 144
    assert contract["evaluation_trajectory_count"] == 720
    assert contract["dual_replay_steps"] == 20
    assert contract["actor_update_steps"] == 16


def test_successor_authority_is_round_aware_and_output_absent() -> None:
    checks = R456.authority_checks()
    assert checks["active_plan"] is True
    assert checks["output_absence"] is True
    assert all(checks.values())
