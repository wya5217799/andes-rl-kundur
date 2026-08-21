from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r451_m3_message_factorial_test",
    ROOT / "scripts/run_r451_m3_message_factorial.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_factorial_is_complete_and_placebo_is_separate() -> None:
    assert len(MODULE.FACTORIAL_ARMS) == 8
    assert len(set(MODULE.FACTORIAL_ARMS)) == 8
    assert MODULE.SHUFFLED_ARM not in MODULE.FACTORIAL_ARMS
    assert MODULE.arm_factors("a0_c1_r0") == {
        "actor_access": False,
        "critic_access": True,
        "reward_access": False,
        "shuffled": False,
    }


def test_actor_and_critic_masks_are_independent_and_only_touch_neighbours() -> None:
    row = torch.arange(MODULE.base.OBS_DIM, dtype=torch.float32).reshape(1, -1)
    masked = MODULE.SplitAccessSACAgent._masked_tensor(row, False)
    assert torch.equal(masked[..., :3], row[..., :3])
    assert torch.all(masked[..., 3:7] == 0)
    assert torch.equal(MODULE.SplitAccessSACAgent._masked_tensor(row, True), row)


def test_shuffle_preserves_pooled_marginal_but_breaks_pairing() -> None:
    rows = np.arange(
        MODULE.base.AGENT_COUNT * MODULE.base.OBS_DIM, dtype=np.float32
    ).reshape(MODULE.base.AGENT_COUNT, MODULE.base.OBS_DIM)
    shuffled = MODULE.shuffle_neighbour_blocks(rows)
    assert np.array_equal(rows[:, :3], shuffled[:, :3])
    assert np.array_equal(
        np.sort(rows[:, 3:7], axis=0), np.sort(shuffled[:, 3:7], axis=0)
    )
    assert not np.array_equal(rows[:, 3:7], shuffled[:, 3:7])


def test_reward_access_matches_parent_semantics() -> None:
    obs = np.zeros((MODULE.base.AGENT_COUNT, MODULE.base.OBS_DIM), dtype=np.float32)
    obs[:, 1] = 0.1
    obs[:, 3] = 0.05
    obs[:, 4] = -0.05
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = dm.copy()
    off = MODULE.step_rewards(obs, dm, dd, reward_access=False)
    on = MODULE.step_rewards(obs, dm, dd, reward_access=True)
    reference = MODULE.parent.channel_step_rewards(obs, dm, dd, rew_masked=True)
    assert np.allclose(off, reference, atol=1e-7)
    assert np.all(on <= off + 1e-9)
    assert np.any(on < off - 1e-9)


def test_bootstrap_improvement_direction_is_pinned() -> None:
    candidate = [0.5, 0.6, 0.4, 0.55, 0.45]
    reference = [1.0] * 5
    result = MODULE._bootstrap_improvement(candidate, reference)
    assert result["ci90"][0] > 0
    assert result["positive_pairs"] == 5


def test_contract_pins_replay_mask_and_objective() -> None:
    contract = MODULE.build_contract()["r451"]
    assert contract["neighbour_slots"] == [3, 4, 5, 6]
    assert contract["reward"] == {
        "phi_f": 100.0,
        "phi_abs": 50.0,
        "phi_h": 0.0056,
        "phi_d": 0.0056,
        "eta_off": 0.0,
        "eta_on": 1.0,
    }
