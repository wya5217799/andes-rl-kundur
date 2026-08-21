"""Targeted contract tests for the R429 adapted-SAC runner."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r429_adapted_sac.py"


def _load_runner():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("run_r429_adapted_sac_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_keeps_matched_bundle_and_declares_real_sac_endpoint() -> None:
    runner = _load_runner()
    contract = runner.build_contract()
    assert contract["training_seeds"] == [401, 402, 403]
    assert contract["training_contract"]["total_interaction_steps"] == 43_200
    assert contract["adapted_sac_contract"]["critic"] == "per-agent-twin-q"
    assert contract["adapted_sac_contract"]["reward"]["phi_abs"] == 50.0
    assert contract["arm_algorithm_map"][runner.MESSAGE_ARM].endswith("-message")


def test_adapted_wrapper_uses_historical_sac_without_slew_projection() -> None:
    runner = _load_runner()
    wrapper = runner.agent_for(runner.MESSAGE_ARM, "cpu")
    assert wrapper.agents[0].__class__.__module__ == "andes_rl_kundur.agents.sac"
    assert wrapper.agents[0].critic.__class__.__name__ == "DoubleQCritic"
    action = wrapper.act(np.zeros((4, 7), dtype=np.float32), deterministic=True)
    assert action.shape == (4, 2)
    assert np.all(np.abs(action) <= 1.0)


def test_masked_reward_contains_phi_abs_and_normalized_action_cost() -> None:
    runner = _load_runner()
    rows = np.zeros((4, 7), dtype=np.float32)
    rows[:, 1] = 0.1
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    reward = runner.adapted_step_rewards(rows, dm, dd, masked=True)
    own_hz = 0.3 / (2.0 * np.pi)
    expected = (
        runner.PHI_ABS * -(own_hz**2)
        + runner.PHI_H * -(np.mean(dm) / 600.0) ** 2
        + runner.PHI_D * -(np.mean(dd) / 600.0) ** 2
    )
    np.testing.assert_allclose(reward, expected, rtol=0.0, atol=1.0e-6)


def test_parallel_shard_ids_cover_training_and_evaluation() -> None:
    runner = _load_runner()
    assert runner._parse_shard("train|cd_matd3_message|401") == (
        "train",
        "cd_matd3_message",
        401,
    )
    deterministic = runner.build_contract()["deterministic_arm_id"]
    assert runner._parse_shard(f"eval|{deterministic}|none") == (
        "eval",
        deterministic,
        None,
    )
