"""Focused R279 tests for the size-matched centralized scalar TD3."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch

from andes_rl_kundur.agents.central_scalar_td3 import CentralScalarTD3
from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3
from andes_rl_kundur.control.area_inertia_residual import AREA_PATTERN


def _obs() -> dict[int, np.ndarray]:
    return {index: np.zeros(7, dtype=np.float32) for index in range(4)}


def test_actor_capacity_is_matched_within_six_parameters() -> None:
    shared = SharedAreaTD3()
    central = CentralScalarTD3()
    shared_count = sum(parameter.numel() for parameter in shared.actor.parameters())
    assert shared_count == 4737
    assert central.actor_parameter_count == 4731
    assert abs(shared_count - central.actor_parameter_count) == 6


def test_central_actor_emits_one_rank_one_environment_action() -> None:
    agent = CentralScalarTD3()
    raw = agent.select_raw_actions(_obs(), deterministic=True)
    assert raw.shape == (4,)
    assert np.allclose(raw[:2], raw[0], rtol=0.0, atol=1e-7)
    assert np.allclose(raw[2:], -raw[0], rtol=0.0, atol=1e-7)
    assert np.allclose(raw, AREA_PATTERN * raw[0], rtol=0.0, atol=1e-7)
    assert abs(float(np.sum(raw))) <= 1e-7


def test_projected_training_action_respects_previous_q_slew() -> None:
    agent = CentralScalarTD3()
    joint = np.zeros((1, 28), dtype=np.float32)
    joint.reshape(1, 4, 7)[:, :, 4] = AREA_PATTERN * 0.8
    with torch.no_grad():
        for parameter in agent.actor.parameters():
            parameter.zero_()
        agent.actor.net[-1].bias.fill_(-10.0)
    _raw, q_normalized = agent._project_actor(
        torch.as_tensor(joint),
        agent.actor,
    )
    assert q_normalized.shape == (1, 1)
    assert -1.0 <= float(q_normalized.item()) <= 1.0
    assert float(q_normalized.item()) >= -0.2 - 1e-6


def test_checkpoint_reload_is_deterministic() -> None:
    torch.manual_seed(279)
    agent = CentralScalarTD3()
    obs = _obs()
    before = agent.select_raw_actions(obs, deterministic=True)
    path = Path("results") / f"_r279_test_central_checkpoint_{os.getpid()}.pt"
    try:
        agent.save(path, metadata={"round": "R279", "seed": 17})

        restored = CentralScalarTD3()
        metadata = restored.load(path)
        after = restored.select_raw_actions(obs, deterministic=True)
        assert metadata == {"round": "R279", "seed": 17}
        assert np.array_equal(before, after)
    finally:
        path.unlink(missing_ok=True)


def test_central_agent_runs_critic_and_actor_updates() -> None:
    torch.manual_seed(279)
    rng = np.random.default_rng(279)
    agent = CentralScalarTD3(batch_size=8, buffer_size=32, policy_delay=2)
    for index in range(10):
        observation = rng.normal(size=28).astype(np.float32)
        next_observation = rng.normal(size=28).astype(np.float32)
        agent.store(
            observation,
            q_normalized=float(rng.uniform(-1.0, 1.0)),
            reward=float(rng.normal()),
            next_observation=next_observation,
            done=index == 9,
        )
    first = agent.update()
    second = agent.update()
    assert first is not None and np.isfinite(first["critic_loss"])
    assert second is not None and np.isfinite(second["critic_loss"])
    assert np.isfinite(second["actor_loss"])
    assert agent.actor_update_steps == 1
