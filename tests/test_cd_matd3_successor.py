"""Offline regression tests for the R403 repaired CD-MATD3 successor."""

from __future__ import annotations

import numpy as np
import torch

from andes_rl_kundur.agents.cd_matd3 import (
    FixedWeightCDMATD3,
    physical_costs_with_action_effort,
)
from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract


def _tiny_kwargs() -> dict[str, object]:
    return {
        "hidden_sizes": [16, 16],
        "buffer_size": 128,
        "batch_size": 8,
        "policy_delay": 2,
        "device": "cpu",
    }


def test_common_weight_cannot_collapse_through_dual_updates() -> None:
    agent = FixedWeightCDMATD3(common_weight=1.0, **_tiny_kwargs())

    for _ in range(100):
        returned = agent.lagrange_step(
            episode_common_cost=0.0,
            budget=3.0,
            step=0.05,
            maximum=10.0,
        )

    assert returned == 1.0
    assert agent.lagrange == 1.0


def test_action_effort_is_added_only_to_differential_cost() -> None:
    contract = build_contract()
    frequencies = np.full((2, 4), 60.0)
    rocof = np.zeros((2, 4))
    power = np.zeros((2, 4))
    actions = np.array(
        [
            [[1.0, 0.0]] * 4,
            [[0.5, 0.5]] * 4,
        ],
        dtype=float,
    )

    differential, common, effort = physical_costs_with_action_effort(
        frequencies,
        rocof,
        power,
        actions,
        contract=contract,
        action_weight=1.0,
    )

    assert np.allclose(effort, [1.0, 0.5])
    assert np.allclose(differential, effort)
    assert np.allclose(common, 0.0)


def test_update_state_is_explicit_and_every_diagnostic_is_finite() -> None:
    torch.manual_seed(4)
    np.random.seed(4)
    agent = FixedWeightCDMATD3(common_weight=1.0, **_tiny_kwargs())
    for _ in range(8):
        obs = np.random.randn(28).astype(np.float32)
        action = agent.act(obs, deterministic=False)
        agent.store(
            obs,
            action.reshape(-1),
            np.array([-0.5, -0.2], dtype=np.float32),
            obs,
            False,
        )

    critic_only = agent.update()
    actor_update = agent.update()

    assert critic_only is not None and actor_update is not None
    assert critic_only["policy_updated"] == 0.0
    assert actor_update["policy_updated"] == 1.0
    assert all(np.isfinite(float(value)) for value in critic_only.values())
    assert all(np.isfinite(float(value)) for value in actor_update.values())
