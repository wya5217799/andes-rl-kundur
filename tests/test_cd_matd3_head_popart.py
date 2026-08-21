from __future__ import annotations

import copy

import numpy as np
import pytest
import torch

from andes_rl_kundur.agents.cd_matd3 import JOINT_ACTION_DIM, JOINT_OBS_DIM
from andes_rl_kundur.agents.cd_matd3_head_popart import HeadSelectivePopArtCDMATD3


def _agent(heads: tuple[str, ...]) -> HeadSelectivePopArtCDMATD3:
    return HeadSelectivePopArtCDMATD3(
        normalized_heads=heads,
        hidden_sizes=[16, 16],
        batch_size=8,
        policy_noise=0.0,
    )


def _batch(seed: int = 1) -> dict[str, torch.Tensor]:
    generator = torch.Generator().manual_seed(seed)
    return {
        "obs": torch.randn(8, JOINT_OBS_DIM, generator=generator),
        "prev_actions": torch.zeros(8, JOINT_ACTION_DIM),
        "actions": torch.rand(8, JOINT_ACTION_DIM, generator=generator) * 2 - 1,
        "rewards": -torch.rand(8, 2, generator=generator) * 10,
        "next_obs": torch.randn(8, JOINT_OBS_DIM, generator=generator),
        "dones": torch.zeros(8, 1),
    }


@pytest.mark.parametrize(
    "heads", [(), ("differential",), ("common",), ("differential", "common")]
)
def test_popart_stats_preserve_original_outputs(heads: tuple[str, ...]) -> None:
    torch.manual_seed(3)
    agent = _agent(heads)
    obs = torch.randn(11, JOINT_OBS_DIM)
    action = torch.randn(11, JOINT_ACTION_DIM)
    with torch.no_grad():
        pre = [agent.original_scale(value) for value in agent.critic(obs, action)]
        pre_target = [
            agent.original_scale(value) for value in agent.critic_target(obs, action)
        ]
    agent.apply_popart_stats(torch.tensor([[-100.0, 25.0], [-80.0, 40.0]]))
    with torch.no_grad():
        post = [agent.original_scale(value) for value in agent.critic(obs, action)]
        post_target = [
            agent.original_scale(value) for value in agent.critic_target(obs, action)
        ]
    for left, right in zip(pre + pre_target, post + post_target):
        assert torch.allclose(left, right, atol=2e-5, rtol=2e-5)


def test_unselected_head_is_byte_unchanged() -> None:
    torch.manual_seed(4)
    agent = _agent(("common",))
    before = copy.deepcopy(agent.critic.state_dict())
    agent.apply_popart_stats(torch.tensor([[-100.0, 25.0], [-80.0, 40.0]]))
    after = agent.critic.state_dict()
    for branch in ("q1", "q2"):
        weight_key = f"{branch}.4.weight"
        bias_key = f"{branch}.4.bias"
        assert torch.equal(before[weight_key][0], after[weight_key][0])
        assert torch.equal(before[bias_key][0], after[bias_key][0])


def test_fixed_batch_update_is_finite_and_head_specific() -> None:
    torch.manual_seed(5)
    agent = _agent(("common",))
    result = agent.fixed_batch_update(_batch(), update_actor=False)
    assert np.isfinite(result["critic_loss"])
    assert np.isfinite(result["critic_loss_original"])
    assert result["popart_mu"][0] == pytest.approx(0.0)
    assert result["popart_sigma"][0] == pytest.approx(1.0)
    assert result["popart_mu"][1] != pytest.approx(0.0)


def test_save_load_mask_and_stats(tmp_path) -> None:
    torch.manual_seed(6)
    agent = _agent(("differential", "common"))
    agent.apply_popart_stats(torch.tensor([[-12.0, -4.0], [-8.0, -2.0]]))
    path = tmp_path / "checkpoint.pt"
    agent.save(path)
    restored = _agent(("differential", "common"))
    restored.load(path)
    assert restored.popart_mu == pytest.approx(agent.popart_mu)
    assert restored.popart_sigma == pytest.approx(agent.popart_sigma)
    with pytest.raises(ValueError, match="mask mismatch"):
        _agent(("differential",)).load(path)


def test_actor_step_reports_two_head_gradients() -> None:
    torch.manual_seed(7)
    agent = _agent(("common",))
    result = agent.actor_step(_batch(8))
    assert len(result["actors"]) == 4
    assert all(len(row["gradient_norms"]) == 5 for row in result["actors"])
    assert all(np.isfinite(row["differential_common_cosine"]) for row in result["actors"])


def test_popart_remap_leaves_unselected_adam_row_unchanged() -> None:
    torch.manual_seed(9)
    agent = _agent(("common",))
    agent.fixed_batch_update(_batch(10), update_actor=False)
    weight = next(
        layer.weight
        for layer in agent.critic.q1.modules()
        if isinstance(layer, torch.nn.Linear) and layer.out_features == 2
    )
    before_mean = agent.critic_optimizer.state[weight]["exp_avg"][0].clone()
    before_square = agent.critic_optimizer.state[weight]["exp_avg_sq"][0].clone()
    agent.apply_popart_stats(torch.tensor([[-50.0, 30.0], [-40.0, 20.0]]))
    assert torch.equal(before_mean, agent.critic_optimizer.state[weight]["exp_avg"][0])
    assert torch.equal(before_square, agent.critic_optimizer.state[weight]["exp_avg_sq"][0])
