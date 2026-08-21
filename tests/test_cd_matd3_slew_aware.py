"""Directed tests for the B1 slew-state-aware learner classes.

The frozen CDMATD3/YangScalarTD3 paths are covered elsewhere; these tests
pin the new augmented-observation, executed-action replay, and projected
target/online semantics of the R418 bundle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    ACTION_DIM,
    AGENT_COUNT,
    AUGMENTED_OBS_DIM,
    CDMATD3,
    NEIGHBOUR_SLOTS,
    OBS_DIM,
    SlewAwareCDMATD3,
    SlewAwareMDActor,
    SlewAwareYangScalarTD3,
    augment_joint_obs_np,
    project_slew_torch,
)


def test_project_slew_torch_math() -> None:
    previous = torch.tensor([[0.2, -0.1]], dtype=torch.float32)
    target = torch.tensor([[0.8, 0.9]], dtype=torch.float32)
    out = project_slew_torch(previous, target, slew_limit=0.25)
    expected = torch.tensor([[0.45, 0.15]], dtype=torch.float32)
    assert torch.allclose(out, expected, atol=1e-6)
    # slew bound respected
    assert torch.all(torch.abs(out - previous) <= 0.25 + 1e-6)
    # differentiable at the interior
    previous.requires_grad_(True)
    out = project_slew_torch(previous, target, slew_limit=0.25)
    out.sum().backward()
    assert previous.grad is not None
    with pytest.raises(ValueError):
        project_slew_torch(previous.detach(), target, slew_limit=3.0)
    with pytest.raises(ValueError):
        project_slew_torch(
            previous.detach(), target[:, :1], slew_limit=0.25
        )


def test_augment_joint_obs_np() -> None:
    obs = np.arange(AGENT_COUNT * OBS_DIM, dtype=np.float32).reshape(
        AGENT_COUNT, OBS_DIM
    )
    prev = np.zeros((AGENT_COUNT, ACTION_DIM), dtype=np.float32)
    prev[:, 1] = 1.0
    augmented = augment_joint_obs_np(obs.reshape(-1), prev.reshape(-1))
    assert augmented.shape == (AGENT_COUNT, AUGMENTED_OBS_DIM)
    assert np.allclose(augmented[:, :OBS_DIM], obs)
    assert np.allclose(augmented[:, OBS_DIM], 0.0)
    assert np.allclose(augmented[:, OBS_DIM + 1], 1.0)


def test_slew_aware_actor_dimensions() -> None:
    actor = SlewAwareMDActor([32, 32])
    row = torch.zeros((2, AUGMENTED_OBS_DIM))
    out = actor(row)
    assert out.shape == (2, ACTION_DIM)
    assert torch.all(torch.abs(out) <= 1.0 + 1e-6)


def _learner_kwargs() -> dict:
    return dict(
        hidden_sizes=[32, 32],
        lr=1e-3,
        buffer_size=512,
        batch_size=32,
        policy_delay=1,
        device="cpu",
    )


def test_cd_update_smoke() -> None:
    agent = SlewAwareCDMATD3(actor_neighbour_mask=True, **_learner_kwargs())
    obs = np.random.RandomState(0).normal(size=(4, OBS_DIM)).astype(np.float32)
    prev = np.zeros((4, ACTION_DIM), dtype=np.float32)
    for _ in range(64):
        augmented = augment_joint_obs_np(obs.reshape(-1), prev.reshape(-1))
        raw = agent.act(augmented, deterministic=False)
        executed = np.clip(raw, -1.0, 1.0).astype(np.float32)
        next_obs = obs + 0.01 * np.random.RandomState(1).normal(size=obs.shape)
        rewards = np.array([-0.5, -0.2], dtype=np.float32)
        agent.store(
            obs.reshape(-1),
            prev.reshape(-1),
            executed.reshape(-1),
            rewards,
            next_obs.reshape(-1).astype(np.float32),
            False,
        )
        prev = executed
        obs = next_obs.astype(np.float32)
    diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["critic_loss"])
    assert np.isfinite(diagnostics["actor_loss_mean"])


def test_scalar_update_smoke() -> None:
    agent = SlewAwareYangScalarTD3(**_learner_kwargs())
    obs = np.random.RandomState(2).normal(size=(4, OBS_DIM)).astype(np.float32)
    prev = np.zeros((4, ACTION_DIM), dtype=np.float32)
    for _ in range(64):
        augmented = augment_joint_obs_np(obs.reshape(-1), prev.reshape(-1))
        raw = agent.act(augmented, deterministic=False)
        executed = np.clip(raw, -1.0, 1.0).astype(np.float32)
        next_obs = obs + 0.01
        agent.store(
            obs.reshape(-1),
            prev.reshape(-1),
            executed.reshape(-1),
            np.array([-0.5], dtype=np.float32),
            next_obs.reshape(-1).astype(np.float32),
            False,
        )
        prev = executed
        obs = next_obs.astype(np.float32)
    diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["critic_loss"])


def test_mask_composition_keeps_prev_action() -> None:
    agent = SlewAwareCDMATD3(actor_neighbour_mask=True, **_learner_kwargs())
    augmented = np.zeros((4, AUGMENTED_OBS_DIM), dtype=np.float32)
    augmented[:, list(NEIGHBOUR_SLOTS)] = 5.0  # neighbour slots would leak
    augmented[:, OBS_DIM] = 0.7  # previous action survives the mask
    rows = torch.FloatTensor(augmented.reshape(-1)).unsqueeze(0)
    for i in range(AGENT_COUNT):
        row = agent._actor_obs_row(rows, i)
        assert row.shape == (1, AUGMENTED_OBS_DIM)
        assert torch.all(row[:, list(NEIGHBOUR_SLOTS)] == 0.0)
        assert torch.all(row[:, OBS_DIM] == 0.7)


def test_save_load_roundtrip(tmp_path: Path) -> None:
    agent = SlewAwareCDMATD3(**_learner_kwargs())
    agent._lagrange = 2.5
    path = tmp_path / "slew.pt"
    agent.save(path)
    restored = SlewAwareCDMATD3(**_learner_kwargs())
    restored.load(path)
    assert abs(restored.lagrange - 2.5) < 1e-9
    for original, loaded in zip(agent.actors, restored.actors):
        for original_param, loaded_param in zip(
            original.parameters(), loaded.parameters()
        ):
            assert torch.equal(original_param, loaded_param)


def test_load_rejects_historical_schema(tmp_path: Path) -> None:
    historical = CDMATD3(**_learner_kwargs())
    path = tmp_path / "historical.pt"
    historical.save(path)
    restored = SlewAwareCDMATD3(**_learner_kwargs())
    with pytest.raises(ValueError):
        restored.load(path)


def test_target_actions_within_slew_of_previous() -> None:
    torch.manual_seed(0)
    agent = SlewAwareCDMATD3(**_learner_kwargs())
    obs = np.random.RandomState(3).normal(size=(4, OBS_DIM)).astype(np.float32)
    prev = np.zeros((4, ACTION_DIM), dtype=np.float32)
    for _ in range(48):
        augmented = augment_joint_obs_np(obs.reshape(-1), prev.reshape(-1))
        raw = agent.act(augmented, deterministic=False)
        executed = np.clip(raw, -1.0, 1.0).astype(np.float32)
        next_obs = obs + 0.01
        agent.store(
            obs.reshape(-1),
            prev.reshape(-1),
            executed.reshape(-1),
            np.array([-0.5, -0.2], dtype=np.float32),
            next_obs.reshape(-1).astype(np.float32),
            False,
        )
        prev = executed
        obs = next_obs.astype(np.float32)
    batch = agent.buffer.sample(32, agent.device)
    targets = agent._target_actions(batch)
    assert targets.shape == (32, 8)
    for i in range(AGENT_COUNT):
        previous = batch["actions"][:, i * 2:(i + 1) * 2]
        row = targets[:, i * 2:(i + 1) * 2]
        assert torch.all(torch.abs(row - previous) <= 0.25 + 1e-5)
