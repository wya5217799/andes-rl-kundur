from __future__ import annotations

import numpy as np
import pytest
import torch

from andes_rl_kundur.agents.executed_action_sac import project_action_numpy
from andes_rl_kundur.agents.source_factorial_sac import SourceFactorialSACAgent


def _agent() -> SourceFactorialSACAgent:
    torch.manual_seed(17)
    return SourceFactorialSACAgent(
        obs_dim=7,
        action_dim=2,
        hidden_sizes=[16, 16],
        slew_limit=0.05,
        buffer_size=512,
        batch_size=8,
    )


def _fill(agent: SourceFactorialSACAgent) -> None:
    rng = np.random.default_rng(29)
    previous = np.zeros(2, dtype=np.float32)
    for _ in range(8):
        actor_obs = rng.normal(size=7).astype(np.float32)
        critic_obs = rng.normal(size=7).astype(np.float32)
        raw = np.tanh(rng.normal(size=2)).astype(np.float32)
        executed = project_action_numpy(previous, raw, slew_limit=0.05)
        agent.store_source_transition(
            actor_obs,
            critic_obs,
            previous,
            raw,
            executed,
            -0.1,
            actor_obs + 0.01,
            critic_obs - 0.01,
            False,
        )
        previous = executed


def test_every_critic_path_uses_executed_action_and_separate_views() -> None:
    agent = _agent()
    _fill(agent)
    batch = agent.buffer.sample(8, "cpu", indices=np.arange(8))
    torch.manual_seed(31)
    paths = agent.source_loss_inputs(batch)
    assert torch.equal(paths["critic_current_action_input"], batch["executed_actions"])
    assert torch.equal(paths["critic_target_action_input"], paths["target_projected_action"])
    assert torch.equal(paths["actor_critic_action_input"], paths["actor_projected_action"])
    assert torch.equal(paths["actor_state"][:, :7], batch["actor_obs"])
    assert torch.equal(paths["critic_state"][:, :7], batch["critic_obs"])
    assert not torch.equal(batch["actor_obs"], batch["critic_obs"])


def test_store_rejects_raw_action_as_executed_action() -> None:
    agent = _agent()
    previous = np.zeros(2, dtype=np.float32)
    raw = np.array([0.8, -0.8], dtype=np.float32)
    with pytest.raises(ValueError, match="executed action"):
        agent.store_source_transition(
            np.zeros(7, dtype=np.float32),
            np.zeros(7, dtype=np.float32),
            previous,
            raw,
            raw,
            0.0,
            np.zeros(7, dtype=np.float32),
            np.zeros(7, dtype=np.float32),
            False,
        )


def test_update_is_finite_and_changes_parameters() -> None:
    agent = _agent()
    _fill(agent)
    before = [parameter.detach().clone() for parameter in agent.actor.parameters()]
    np.random.seed(37)
    torch.manual_seed(37)
    result = agent.update()
    assert result is not None
    assert all(np.isfinite(list(result.values())))
    assert any(
        not torch.equal(left, right)
        for left, right in zip(before, agent.actor.parameters(), strict=True)
    )
