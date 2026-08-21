from __future__ import annotations

import numpy as np
import torch

from andes_rl_kundur.agents.executed_action_sac import (
    ENTROPY_SEMANTICS,
    ExecutedActionSACAgent,
    project_action_numpy,
    project_action_torch,
)
from andes_rl_kundur.control.per_vsg_md import PerVSGMDActionProjector


def _agent(*, batch_size: int = 2) -> ExecutedActionSACAgent:
    torch.manual_seed(17)
    return ExecutedActionSACAgent(
        obs_dim=7,
        action_dim=2,
        hidden_sizes=[16, 16],
        slew_limit=0.25,
        batch_size=batch_size,
        buffer_size=16,
    )


def test_numpy_projection_matches_runtime_projector_multistep() -> None:
    rng = np.random.default_rng(5)
    runtime = PerVSGMDActionProjector(action_slew_limit=0.25)
    previous = np.zeros((4, 2), dtype=np.float32)
    for raw in rng.uniform(-3.0, 3.0, size=(50, 4, 2)).astype(np.float32):
        expected = runtime.project(raw)
        actual = project_action_numpy(previous, raw, slew_limit=0.25)
        np.testing.assert_array_equal(actual, expected)
        previous = actual.copy()


def test_torch_projector_matches_numpy_within_contract() -> None:
    rng = np.random.default_rng(11)
    previous = rng.uniform(-1.0, 1.0, size=(256, 2)).astype(np.float32)
    raw = rng.uniform(-4.0, 4.0, size=(256, 2)).astype(np.float32)
    expected = project_action_numpy(previous, raw, slew_limit=0.25)
    actual = project_action_torch(
        torch.from_numpy(previous), torch.from_numpy(raw), slew_limit=0.25
    )
    assert float(np.max(np.abs(actual.numpy() - expected))) <= 1.0e-7


def test_replay_preserves_previous_raw_and_executed_actions() -> None:
    agent = _agent(batch_size=1)
    obs = np.arange(7, dtype=np.float32)
    previous = np.asarray([0.1, -0.2], dtype=np.float32)
    raw = np.asarray([0.9, -0.9], dtype=np.float32)
    executed = agent.execute_action(previous, raw)
    agent.store_transition(obs, previous, raw, executed, 1.5, obs + 1.0, False)
    batch = agent.buffer.sample(1, "cpu", indices=np.asarray([0]))
    np.testing.assert_array_equal(batch["previous_executed_actions"].numpy()[0], previous)
    np.testing.assert_array_equal(batch["raw_actions"].numpy()[0], raw)
    np.testing.assert_array_equal(batch["executed_actions"].numpy()[0], executed)


def test_every_critic_path_uses_executed_or_projected_action() -> None:
    agent = _agent(batch_size=1)
    obs = np.zeros(7, dtype=np.float32)
    previous = np.asarray([0.5, -0.5], dtype=np.float32)
    raw = np.asarray([-0.8, 0.8], dtype=np.float32)
    executed = agent.execute_action(previous, raw)
    agent.store_transition(obs, previous, raw, executed, 0.25, obs, False)
    batch = agent.buffer.sample(1, "cpu", indices=np.asarray([0]))
    torch.manual_seed(23)
    paths = agent.loss_inputs(batch)
    torch.testing.assert_close(
        paths["critic_current_action_input"], batch["executed_actions"]
    )
    torch.testing.assert_close(
        paths["critic_target_action_input"], paths["target_projected_action"]
    )
    torch.testing.assert_close(
        paths["actor_critic_action_input"], paths["actor_projected_action"]
    )
    assert not torch.equal(batch["raw_actions"], batch["executed_actions"])
    assert agent.entropy_semantics == ENTROPY_SEMANTICS


def test_deterministic_target_matches_hand_bellman_value() -> None:
    agent = _agent(batch_size=1)
    agent.gamma = 0.9
    with torch.no_grad():
        for network, value in ((agent.critic_target.q1, 2.0), (agent.critic_target.q2, 3.0)):
            for parameter in network.parameters():
                parameter.zero_()
            network.net[-1].bias.fill_(value)
    obs = np.zeros(7, dtype=np.float32)
    previous = np.zeros(2, dtype=np.float32)
    raw = np.asarray([0.9, -0.9], dtype=np.float32)
    executed = agent.execute_action(previous, raw)
    agent.store_transition(obs, previous, raw, executed, 1.25, obs + 0.1, False)
    batch = agent.buffer.sample(1, "cpu", indices=np.asarray([0]))
    paths = agent.loss_inputs(batch, deterministic_target=True)
    expected = 1.25 + 0.9 * 2.0
    assert abs(float(paths["td_target"].item()) - expected) <= 1.0e-6
    torch.testing.assert_close(
        paths["next_state"][:, -2:], batch["executed_actions"]
    )


def test_update_runs_with_executed_action_replay() -> None:
    agent = _agent(batch_size=2)
    previous = np.zeros(2, dtype=np.float32)
    for index in range(2):
        obs = np.full(7, index, dtype=np.float32)
        raw = np.asarray([0.8 - index, -0.8 + index], dtype=np.float32)
        executed = agent.execute_action(previous, raw)
        agent.store_transition(obs, previous, raw, executed, 0.1, obs + 0.2, index == 1)
        previous = executed
    diagnostics = agent.update()
    assert diagnostics is not None
    assert all(np.isfinite(value) for value in diagnostics.values())
