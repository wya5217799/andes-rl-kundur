"""Tests for checkpoint_loader auto-detection of hidden_size / obs_dim.

R50 optimization A — eliminate the "load_agents fails with shape mismatch
when ckpt's hidden_size differs from default" footgun. Two prior rounds
(R48 h=64, R49 INCLUDE_OWN_ACTION_OBS=1) needed inline workarounds.

Behaviors under test:
1. load_agents auto-detects hidden_sizes from ckpt['actor']['net.0.weight'].shape[0]
   when the kwarg is None.
2. load_agents auto-detects obs_dim from ckpt['actor']['net.0.weight'].shape[1]
   when no explicit obs_dim kwarg is passed.
3. Explicit hidden_sizes kwarg still wins over auto-detection (backward compat).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import torch

from andes_rl_kundur.agents.checkpoint_loader import load_agents
from andes_rl_kundur.agents.td3 import TD3Agent
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4


def _save_synthetic_td3_ckpt(
    ckpt_dir: Path,
    *,
    n_agents: int,
    obs_dim: int,
    hidden_size: int,
) -> None:
    """Create N synthetic TD3 ckpts in ckpt_dir for testing."""
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_agents):
        agent = TD3Agent(
            obs_dim=obs_dim,
            action_dim=2,
            hidden_sizes=(hidden_size,) * 4,
            device="cpu",
        )
        agent.save(str(ckpt_dir / f"agent_{i}_best.pt"))


def test_load_agents_autodetects_hidden_size_from_ckpt(tmp_path: Path) -> None:
    """RED test 1: load_agents with no hidden_sizes kwarg loads h=64 ckpts
    without shape mismatch."""
    n_agents = AndesMultiVSGEnvV4.N_AGENTS
    _save_synthetic_td3_ckpt(
        tmp_path,
        n_agents=n_agents,
        obs_dim=AndesMultiVSGEnvV4.OBS_DIM,
        hidden_size=64,
    )

    # No hidden_sizes kwarg — should auto-detect 64 from ckpt
    agents = load_agents(tmp_path, suffix="best")

    assert len(agents) == n_agents
    # Verify the loaded actor really has h=64 (not default h=128)
    assert agents[0].actor.net[0].weight.shape[0] == 64


def test_load_agents_autodetects_obs_dim_from_ckpt(tmp_path: Path) -> None:
    """RED test 2: load_agents auto-detects obs_dim=9 from ckpts trained with
    INCLUDE_OWN_ACTION_OBS=1, even when the env class attr says OBS_DIM=7."""
    n_agents = AndesMultiVSGEnvV4.N_AGENTS
    _save_synthetic_td3_ckpt(
        tmp_path,
        n_agents=n_agents,
        obs_dim=9,  # 7 + 2 for INCLUDE_OWN_ACTION_OBS
        hidden_size=64,
    )

    agents = load_agents(tmp_path, suffix="best")

    assert agents[0].actor.net[0].weight.shape[1] == 9


def test_load_agents_explicit_hidden_sizes_overrides_autodetect(tmp_path: Path) -> None:
    """Backward compat: an explicit hidden_sizes kwarg matching the ckpt's
    actual dimensions still works (no regression on R48-β workaround use)."""
    n_agents = AndesMultiVSGEnvV4.N_AGENTS
    _save_synthetic_td3_ckpt(
        tmp_path,
        n_agents=n_agents,
        obs_dim=AndesMultiVSGEnvV4.OBS_DIM,
        hidden_size=64,
    )

    # Explicit kwarg matches ckpt — should still load
    agents = load_agents(tmp_path, suffix="best", hidden_sizes=(64,) * 4)

    assert agents[0].actor.net[0].weight.shape[0] == 64


def test_load_agents_explicit_mismatch_still_raises(tmp_path: Path) -> None:
    """If caller insists on wrong hidden_sizes via explicit kwarg, fail loudly
    rather than silently auto-detect — explicit user intent wins."""
    n_agents = AndesMultiVSGEnvV4.N_AGENTS
    _save_synthetic_td3_ckpt(
        tmp_path,
        n_agents=n_agents,
        obs_dim=AndesMultiVSGEnvV4.OBS_DIM,
        hidden_size=64,
    )

    with pytest.raises(RuntimeError, match="size mismatch"):
        load_agents(tmp_path, suffix="best", hidden_sizes=(128,) * 4)
