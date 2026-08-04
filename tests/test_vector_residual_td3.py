from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from andes_rl_kundur.agents.vector_residual_td3 import (
    CentralVectorTD3,
    DistributedEdgeTD3,
)


def _observations() -> dict[int, np.ndarray]:
    return {
        index: np.asarray(
            [0.1 * index, -0.2 * index, 0.05 * index, 0.03 * index, sign],
            dtype=np.float32,
        )
        for index, sign in enumerate((1.0, 1.0, -1.0, -1.0))
    }


def test_distributed_edge_action_is_independent_of_non_endpoint_nodes() -> None:
    torch.manual_seed(292)
    agent = DistributedEdgeTD3(hidden_sizes=[16, 16])
    original = _observations()
    changed = {index: value.copy() for index, value in original.items()}
    changed[2][:4] += 100.0
    changed[3][:4] -= 100.0

    first = agent.select_edge_actions(original, deterministic=True)
    second = agent.select_edge_actions(changed, deterministic=True)

    assert first.shape == (3,)
    assert np.array_equal(first[0:1], second[0:1])


def test_central_and_distributed_actors_share_edge_space_and_matched_capacity() -> None:
    distributed = DistributedEdgeTD3()
    central = CentralVectorTD3()

    distributed_count = sum(
        parameter.numel() for parameter in distributed.actor.parameters()
    )
    central_count = sum(parameter.numel() for parameter in central.actor.parameters())
    assert distributed_count == 4929
    assert central_count == 4959
    assert abs(central_count - distributed_count) / distributed_count < 0.01
    assert central.select_edge_actions(
        _observations(), deterministic=True
    ).shape == (3,)


def test_both_architectures_update_on_executed_three_edge_actions() -> None:
    rng = np.random.default_rng(292)
    for agent_class in (DistributedEdgeTD3, CentralVectorTD3):
        agent = agent_class(batch_size=4, buffer_size=32, policy_delay=2)
        for index in range(8):
            observation = rng.normal(size=20).astype(np.float32)
            next_observation = rng.normal(size=20).astype(np.float32)
            agent.store(
                observation,
                rng.uniform(-1.0, 1.0, size=3).astype(np.float32),
                reward=-float(index),
                next_observation=next_observation,
                done=index == 7,
            )

        first = agent.update()
        second = agent.update()

        assert first is not None and np.isfinite(first["critic_loss"])
        assert second is not None and np.isfinite(second["critic_loss"])
        assert np.isfinite(second["actor_loss"])


def test_vector_checkpoint_roundtrip_preserves_policy_and_metadata(
    tmp_path: Path,
) -> None:
    for agent_class in (DistributedEdgeTD3, CentralVectorTD3):
        original = agent_class()
        expected = original.select_edge_actions(
            _observations(), deterministic=True
        )
        checkpoint = tmp_path / f"{original.algo_name}.pt"
        original.save(checkpoint, metadata={"round": "R292", "seed": 101})

        restored = agent_class()
        metadata = restored.load(checkpoint)
        actual = restored.select_edge_actions(
            _observations(), deterministic=True
        )

        assert metadata == {"round": "R292", "seed": 101}
        assert np.array_equal(actual, expected)
