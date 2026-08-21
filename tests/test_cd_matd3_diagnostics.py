"""Directed tests for the B3 diagnostic instrumentation classes.

The load-bearing property is bit-comparability: under identical seeds and
identical stores, the diagnostic subclass must produce the exact same
weights as the frozen learner, and the added diagnostics must be finite.
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
    CDMATD3,
    SlewAwareCDMATD3,
    YangScalarTD3,
)
from andes_rl_kundur.agents.cd_matd3_diagnostics import (  # noqa: E402
    DiagnosticCDMATD3,
    DiagnosticSlewAwareCDMATD3,
    DiagnosticYangScalarTD3,
)


def _kwargs() -> dict:
    return dict(
        hidden_sizes=[32, 32],
        lr=1e-3,
        buffer_size=256,
        batch_size=32,
        policy_delay=1,
        device="cpu",
    )


def _run_episode(agent, rng: np.random.RandomState, reward_dim: int = 2) -> None:
    obs = rng.normal(size=28).astype(np.float32)
    for _ in range(40):
        raw = agent.act(obs, deterministic=False)
        action = np.clip(raw, -1.0, 1.0).astype(np.float32)
        next_obs = obs + 0.01 * rng.normal(size=28)
        rewards = (
            np.array([-0.5, -0.2], dtype=np.float32)
            if reward_dim == 2
            else np.array([-0.5], dtype=np.float32)
        )
        agent.store(
            obs,
            action.reshape(-1),
            rewards,
            next_obs.astype(np.float32),
            False,
        )
        obs = next_obs.astype(np.float32)
        agent.update()


def test_diagnostic_cd_bit_identical() -> None:
    # Bit-comparability under identical seeds: each agent runs its own
    # fresh seeding context (the per-run single-process semantic), then
    # the weights must match exactly.
    torch.manual_seed(7)
    np.random.seed(7)
    frozen = CDMATD3(**_kwargs())
    frozen_rng = np.random.RandomState(7)
    for _ in range(3):
        _run_episode(frozen, frozen_rng, reward_dim=2)

    torch.manual_seed(7)
    np.random.seed(7)
    diagnostic = DiagnosticCDMATD3(**_kwargs())
    diagnostic_rng = np.random.RandomState(7)
    for _ in range(3):
        _run_episode(diagnostic, diagnostic_rng, reward_dim=2)

    for frozen_param, diag_param in zip(
        frozen.actors[0].parameters(), diagnostic.actors[0].parameters()
    ):
        assert torch.equal(frozen_param, diag_param)
    for frozen_param, diag_param in zip(
        frozen.critic.parameters(), diagnostic.critic.parameters()
    ):
        assert torch.equal(frozen_param, diag_param)


def test_diagnostic_scalar_bit_identical() -> None:
    torch.manual_seed(9)
    np.random.seed(9)
    frozen = YangScalarTD3(**_kwargs())
    frozen_rng = np.random.RandomState(9)
    for _ in range(3):
        _run_episode(frozen, frozen_rng, reward_dim=1)

    torch.manual_seed(9)
    np.random.seed(9)
    diagnostic = DiagnosticYangScalarTD3(**_kwargs())
    diagnostic_rng = np.random.RandomState(9)
    for _ in range(3):
        _run_episode(diagnostic, diagnostic_rng, reward_dim=1)

    for frozen_param, diag_param in zip(
        frozen.critic.parameters(), diagnostic.critic.parameters()
    ):
        assert torch.equal(frozen_param, diag_param)


def _run_slew_episode(agent, rng: np.random.RandomState) -> None:
    obs = rng.normal(size=28).astype(np.float32)
    prev = np.zeros((4, 2), dtype=np.float32)
    for _ in range(40):
        augmented = np.concatenate(
            [obs.reshape(4, 7), prev], axis=-1
        ).astype(np.float32)
        raw = agent.act(augmented.reshape(-1), deterministic=False)
        action = np.clip(raw, -1.0, 1.0).astype(np.float32)
        next_obs = obs + 0.01 * rng.normal(size=28)
        agent.store(
            obs,
            prev.reshape(-1).astype(np.float32),
            action.reshape(-1),
            np.array([-0.5, -0.2], dtype=np.float32),
            next_obs.astype(np.float32),
            False,
        )
        obs = next_obs.astype(np.float32)
        prev = action.reshape(4, 2).astype(np.float32)
        agent.update()


def test_diagnostic_slew_aware_bit_identical() -> None:
    torch.manual_seed(13)
    np.random.seed(13)
    frozen = SlewAwareCDMATD3(**_kwargs())
    frozen_rng = np.random.RandomState(13)
    for _ in range(2):
        _run_slew_episode(frozen, frozen_rng)

    torch.manual_seed(13)
    np.random.seed(13)
    diagnostic = DiagnosticSlewAwareCDMATD3(**_kwargs())
    diagnostic_rng = np.random.RandomState(13)
    for _ in range(2):
        _run_slew_episode(diagnostic, diagnostic_rng)

    for frozen_param, diag_param in zip(
        frozen.actors[0].parameters(), diagnostic.actors[0].parameters()
    ):
        assert torch.equal(frozen_param, diag_param)
    for frozen_param, diag_param in zip(
        frozen.critic.parameters(), diagnostic.critic.parameters()
    ):
        assert torch.equal(frozen_param, diag_param)


def test_diagnostics_fields_present_and_finite() -> None:
    torch.manual_seed(11)
    np.random.seed(11)
    agent = DiagnosticCDMATD3(**_kwargs())
    rng = np.random.RandomState(11)
    _run_episode(agent, rng)
    # run one more update after the buffer holds a batch
    obs = rng.normal(size=28).astype(np.float32)
    for _ in range(40):
        raw = agent.act(obs, deterministic=False)
        action = np.clip(raw, -1.0, 1.0).astype(np.float32)
        next_obs = obs + 0.01
        agent.store(
            obs,
            action.reshape(-1),
            np.array([-0.5, -0.2], dtype=np.float32),
            next_obs.astype(np.float32),
            False,
        )
        obs = next_obs.astype(np.float32)
    diagnostics = agent.update()
    assert diagnostics is not None
    for key in (
        "critic_loss",
        "actor_loss_mean",
        "lagrange",
        "bellman_residual_mean",
        "bellman_residual_abs_max",
        "bellman_residual_std",
        "bellman_residual_q25",
        "bellman_residual_q50",
        "bellman_residual_q75",
        "critic_grad_norm_mean",
        "critic_grad_norm_max",
        "actor_grad_norm_mean",
        "actor_grad_norm_max",
        "td_error_std",
        "sampled_state_variance_mean",
    ):
        assert key in diagnostics, key
        assert np.isfinite(diagnostics[key]), key
