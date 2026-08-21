"""Pure offline tests for the CD-MATD3 and Yang-scalar-TD3 learners.

No ANDES import: these bind the frozen R401 learner contract at the network,
cost, masking, multiplier, update, and checkpoint seams.
"""

from __future__ import annotations

import numpy as np
import torch

from andes_rl_kundur.agents.cd_matd3 import (
    AGENT_COUNT,
    ACTION_DIM,
    JOINT_OBS_DIM,
    OBS_DIM,
    CDMATD3,
    YangScalarTD3,
    compute_rocof,
    mask_neighbour_slots,
    physical_costs,
)
from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract


def _tiny_kwargs():
    return dict(
        hidden_sizes=[16, 16],
        buffer_size=2000,
        batch_size=64,
        policy_delay=2,
        device="cpu",
    )


def test_actor_output_shape_and_bounds():
    agent = CDMATD3(lagrange_initial=1.0, **_tiny_kwargs())
    obs = np.zeros(JOINT_OBS_DIM, dtype=np.float32)
    for deterministic in (True, False):
        action = agent.act(obs, deterministic=deterministic)
        assert action.shape == (AGENT_COUNT, ACTION_DIM)
        assert np.all(np.isfinite(action))
        assert np.all(action >= -1.0) and np.all(action <= 1.0)


def test_mask_neighbour_slots_zeros_only_neighbour_channels():
    obs = np.arange(JOINT_OBS_DIM, dtype=np.float32)
    masked = mask_neighbour_slots(obs).reshape(AGENT_COUNT, OBS_DIM)
    full = obs.reshape(AGENT_COUNT, OBS_DIM)
    assert np.all(masked[:, [3, 4, 5, 6]] == 0.0)
    assert np.all(masked[:, [0, 1, 2]] == full[:, [0, 1, 2]])


def test_physical_costs_zero_at_nominal_with_zero_rocof():
    contract = build_contract()
    frequencies = np.full((10, 4), 60.0)
    rocof = np.zeros((10, 4))
    power = np.zeros((10, 4))
    differential, common = physical_costs(
        frequencies, rocof, power, contract=contract
    )
    assert np.allclose(differential, 0.0)
    assert np.allclose(common, 0.0)


def test_physical_costs_scale_quadratically():
    contract = build_contract()
    frequencies = np.full((5, 4), 60.15)
    rocof = np.zeros((5, 4))
    power = np.zeros((5, 4))
    _, common = physical_costs(frequencies, rocof, power, contract=contract)
    frequencies_scaled = np.full((5, 4), 60.3)
    _, common_scaled = physical_costs(
        frequencies_scaled, rocof, power, contract=contract
    )
    ratio = common_scaled / common
    assert np.allclose(ratio, 4.0, rtol=1e-6)


def test_compute_rocof_includes_initial_step():
    initial = np.full(4, 60.0)
    frequencies = np.stack([np.full(4, 60.2), np.full(4, 60.1)])
    rocof = compute_rocof(initial, frequencies, dt=0.2)
    assert rocof.shape == (2, 4)
    assert np.allclose(rocof[0], 1.0)
    assert np.allclose(rocof[1], -0.5)


def test_lagrange_step_clips_to_frozen_bounds():
    agent = CDMATD3(lagrange_initial=1.0, **_tiny_kwargs())
    assert agent.lagrange == 1.0
    high = agent.lagrange_step(100.0, budget=3.0, step=0.05, maximum=10.0)
    assert np.isclose(high, 1.0 + 0.05 * 97.0)
    for _ in range(500):
        agent.lagrange_step(1000.0, budget=3.0, step=0.05, maximum=10.0)
    assert agent.lagrange == 10.0
    for _ in range(1000):
        agent.lagrange_step(0.0, budget=3.0, step=0.05, maximum=10.0)
    assert agent.lagrange == 0.0


def test_cd_matd3_update_is_finite():
    torch.manual_seed(0)
    np.random.seed(0)
    agent = CDMATD3(lagrange_initial=1.0, **_tiny_kwargs())
    for _ in range(200):
        obs = np.random.randn(JOINT_OBS_DIM).astype(np.float32)
        next_obs = np.random.randn(JOINT_OBS_DIM).astype(np.float32)
        action = agent.act(obs, deterministic=False)
        agent.store(
            obs, action.reshape(-1), np.array([-0.5, -0.2], dtype=np.float32),
            next_obs, False,
        )
    diagnostics = None
    for _ in range(10):
        diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["critic_loss"])
    assert np.isfinite(diagnostics["actor_loss_mean"])


def test_yang_scalar_td3_update_is_finite():
    torch.manual_seed(1)
    np.random.seed(1)
    agent = YangScalarTD3(**_tiny_kwargs())
    for _ in range(200):
        obs = np.random.randn(JOINT_OBS_DIM).astype(np.float32)
        next_obs = np.random.randn(JOINT_OBS_DIM).astype(np.float32)
        action = agent.act(obs, deterministic=False)
        agent.store(
            obs, action.reshape(-1), np.array([-0.5], dtype=np.float32),
            next_obs, False,
        )
    diagnostics = None
    for _ in range(10):
        diagnostics = agent.update()
    assert diagnostics is not None
    assert np.isfinite(diagnostics["critic_loss"])


def test_checkpoint_roundtrip_preserves_weights(tmp_path):
    torch.manual_seed(2)
    np.random.seed(2)
    agent = CDMATD3(lagrange_initial=2.5, **_tiny_kwargs())
    for _ in range(100):
        obs = np.random.randn(JOINT_OBS_DIM).astype(np.float32)
        action = agent.act(obs, deterministic=False)
        agent.store(
            obs, action.reshape(-1), np.array([-0.5, -0.2], dtype=np.float32),
            obs, False,
        )
        agent.update()
    before = agent.act(np.zeros(JOINT_OBS_DIM, dtype=np.float32), deterministic=True)
    path = tmp_path / "agent.pt"
    agent.save(path)
    restored = CDMATD3(lagrange_initial=0.0, **_tiny_kwargs())
    restored.load(path)
    assert restored.lagrange == 2.5
    after = restored.act(
        np.zeros(JOINT_OBS_DIM, dtype=np.float32), deterministic=True
    )
    assert np.allclose(before, after, atol=0.0)


def test_no_message_mask_is_enforced_inside_actor_update_paths():
    agent = CDMATD3(
        lagrange_initial=1.0,
        actor_neighbour_mask=True,
        **_tiny_kwargs(),
    )
    batch = torch.arange(
        2 * JOINT_OBS_DIM, dtype=torch.float32
    ).reshape(2, JOINT_OBS_DIM)
    for actor_index in range(AGENT_COUNT):
        row = agent._actor_obs_row(batch, actor_index)
        assert torch.all(row[:, [3, 4, 5, 6]] == 0.0)
        expected = batch[
            :, actor_index * OBS_DIM:(actor_index + 1) * OBS_DIM
        ]
        assert torch.all(row[:, [0, 1, 2]] == expected[:, [0, 1, 2]])


def test_message_arm_preserves_neighbour_slots_inside_update_paths():
    agent = CDMATD3(
        lagrange_initial=1.0,
        actor_neighbour_mask=False,
        **_tiny_kwargs(),
    )
    batch = torch.arange(
        2 * JOINT_OBS_DIM, dtype=torch.float32
    ).reshape(2, JOINT_OBS_DIM)
    for actor_index in range(AGENT_COUNT):
        row = agent._actor_obs_row(batch, actor_index)
        expected = batch[
            :, actor_index * OBS_DIM:(actor_index + 1) * OBS_DIM
        ]
        assert torch.equal(row, expected)

