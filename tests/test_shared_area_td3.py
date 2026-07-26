from __future__ import annotations

import numpy as np
import pytest
import torch

from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3


def _joint_obs(previous_q_normalized: float = 0.0) -> np.ndarray:
    obs = np.zeros((4, 7), dtype=np.float32)
    obs[:, 0] = [0.2, 0.1, -0.1, -0.2]
    obs[:, 2] = [0.3, 0.2, -0.2, -0.3]
    obs[:, 4] = (
        previous_q_normalized
        * np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)
    )
    obs[:, 6] = [1.0, 1.0, -1.0, -1.0]
    return obs.reshape(-1)


def test_one_actor_object_generates_four_agent_votes() -> None:
    agent = SharedAreaTD3(batch_size=4, hidden_sizes=[16, 16])
    observations = _joint_obs().reshape(4, 7)
    raw = agent.select_raw_actions(observations, deterministic=True)
    assert raw.shape == (4,)
    assert np.all(np.abs(raw) <= 1.0)
    parameter_ids = {id(parameter) for parameter in agent.actor.parameters()}
    assert len(parameter_ids) == len(list(agent.actor.parameters()))
    optimizer_parameter_ids = {
        id(parameter)
        for parameter in agent.actor_optimizer.param_groups[0]["params"]
    }
    assert optimizer_parameter_ids == parameter_ids


def test_projected_actor_action_uses_previous_q_from_observation() -> None:
    agent = SharedAreaTD3(batch_size=4, hidden_sizes=[8])
    with torch.no_grad():
        for parameter in agent.actor.parameters():
            parameter.zero_()
        final = agent.actor.net[-1]
        final.bias.copy_(torch.tensor([10.0]))

    obs = torch.tensor(
        np.stack([_joint_obs(previous_q_normalized=-1.0)]),
        dtype=torch.float32,
    )
    _raw, q_normalized = agent._project_actor(obs, agent.actor)
    # Raw votes are identical, hence the two area means cancel exactly even
    # though each local actor output is near +1.
    assert float(q_normalized.item()) == pytest.approx(0.0, abs=1e-7)


def test_update_has_one_delayed_actor_step() -> None:
    torch.manual_seed(7)
    np.random.seed(7)
    agent = SharedAreaTD3(
        batch_size=4,
        buffer_size=32,
        hidden_sizes=[16, 16],
        policy_delay=2,
    )
    for index in range(8):
        obs = _joint_obs(previous_q_normalized=0.0)
        next_obs = _joint_obs(previous_q_normalized=0.1)
        agent.store(
            obs,
            q_normalized=0.1,
            reward=-float(index + 1) / 10.0,
            next_observation=next_obs,
            done=index % 4 == 3,
        )
    first = agent.update()
    second = agent.update()
    assert first is not None and second is not None
    assert "actor_loss" not in first
    assert "actor_loss" in second
    assert agent.actor_update_steps == 1


def test_checkpoint_reload_preserves_deterministic_raw_actions(tmp_path) -> None:
    torch.manual_seed(11)
    agent = SharedAreaTD3(batch_size=4, hidden_sizes=[16, 16])
    obs = _joint_obs().reshape(4, 7)
    expected = agent.select_raw_actions(obs, deterministic=True)
    path = tmp_path / "shared_area_td3.pt"
    agent.save(path, metadata={"round": "R278", "seed": 49})

    restored = SharedAreaTD3(batch_size=4, hidden_sizes=[16, 16])
    metadata = restored.load(path)
    actual = restored.select_raw_actions(obs, deterministic=True)
    np.testing.assert_array_equal(actual, expected)
    assert metadata == {"round": "R278", "seed": 49}
