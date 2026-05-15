"""TD3 (Twin Delayed DDPG) agent — alternative to SAC for the V4 env.

TD3 is structurally similar to SAC (twin Q critics, target networks,
replay buffer, soft target updates) but **has no entropy bonus**. The
research hypothesis is that SAC's entropy regularization is what pulls
the actor toward near-zero action and produces the 0.137 multi-seed
attractor (R29-R33 negative findings). TD3 should break that pull.

This test file covers the contract; full multi-seed training results
go in R38/verdict.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_td3_agent_satisfies_base_agent_protocol():
    """TD3Agent must structurally satisfy the BaseAgent Protocol so
    train.py can swap SACAgent ↔ TD3Agent without changing the loop."""
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.td3 import TD3Agent
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    assert isinstance(agent, BaseAgent)


def test_td3_agent_inherits_sac_scaffold():
    """TD3Agent reuses _SACBase's actor + buffer + select/store paths."""
    from andes_rl_kundur.agents.sac_base import _SACBase
    from andes_rl_kundur.agents.td3 import TD3Agent
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64])
    assert isinstance(agent, _SACBase)
    # TD3-specific state
    assert hasattr(agent, "actor_target")
    assert hasattr(agent, "critic")
    assert hasattr(agent, "critic_target")
    assert hasattr(agent, "policy_delay")
    assert hasattr(agent, "explore_noise")


def test_td3_deterministic_action_has_no_noise():
    """select_action(deterministic=True) returns the mean action,
    no exploration noise added."""
    from andes_rl_kundur.agents.td3 import TD3Agent
    torch.manual_seed(0)
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64],
                     explore_noise=0.5)
    obs = np.zeros(7, dtype=np.float32)
    a1 = agent.select_action(obs, deterministic=True)
    a2 = agent.select_action(obs, deterministic=True)
    np.testing.assert_array_equal(a1, a2)
    assert a1.shape == (2,)


def test_td3_exploration_action_is_clipped():
    """Action with exploration noise is clipped to [-1, 1]."""
    from andes_rl_kundur.agents.td3 import TD3Agent
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64],
                     explore_noise=10.0)  # absurdly large to force clip
    obs = np.zeros(7, dtype=np.float32)
    for _ in range(20):
        a = agent.select_action(obs, deterministic=False)
        assert np.all(a >= -1.0) and np.all(a <= 1.0)


def test_td3_update_runs_when_buffer_has_enough():
    """update() returns a loss dict after the buffer is filled."""
    from andes_rl_kundur.agents.td3 import TD3Agent
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64],
                     batch_size=8)
    for _ in range(20):
        agent.store_transition(
            obs=np.random.randn(7).astype(np.float32),
            action=np.random.uniform(-1, 1, 2).astype(np.float32),
            reward=-1.0,
            next_obs=np.random.randn(7).astype(np.float32),
            done=False,
        )
    loss = agent.update()
    assert loss is not None
    assert "critic_loss" in loss


def test_td3_no_entropy_alpha_loss():
    """TD3 has no entropy bonus, so update() must NOT report alpha_loss
    (the SAC-specific entropy regularization signal)."""
    from andes_rl_kundur.agents.td3 import TD3Agent
    agent = TD3Agent(obs_dim=7, action_dim=2, hidden_sizes=[64, 64],
                     batch_size=8, policy_delay=1)
    for _ in range(20):
        agent.store_transition(
            obs=np.random.randn(7).astype(np.float32),
            action=np.random.uniform(-1, 1, 2).astype(np.float32),
            reward=-1.0,
            next_obs=np.random.randn(7).astype(np.float32),
            done=False,
        )
    loss = agent.update()
    assert "alpha_loss" not in loss, (
        "TD3 has no entropy regularization; alpha_loss key must not appear"
    )
