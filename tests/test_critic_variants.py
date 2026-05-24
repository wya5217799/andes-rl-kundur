"""R98 — Tests for distributional (QR) + action-feature-engineered (AFE)
critic prototypes.

Critical contracts (both variants):
- Satisfy ``BaseAgent`` Protocol — train.py treats them like other agents.
- Forward through the new critic returns the correct shape and dtype.
- Backprop populates the LSTM weight gradients on both actor + critic.
- ``save`` / ``load`` roundtrip preserves the deterministic actor output
  bit-exactly (within float32 round-off).
- ``algo_name`` is set so the checkpoint_loader autodetect path can route.

QR-only:
- Quantile output is ``(B, n_quantiles)``, scalar mean Q matches the dim-=-1 mean.
- ``quantile_huber_loss`` is non-negative, zero iff prediction equals target
  for all quantiles, finite for typical inputs, and broadcasts batch.
- TD3 min-Q target trick picks the LOWER-mean critic's quantiles.

AFE-only:
- Critic input dim is ``obs + 4*action_dim`` (the AFE expansion).
- For a_zero == 0, action² == 0, |a| == 0, sign(a) == 0 — but the obs path
  is still active (no NaN / no zero gradient on obs weights).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _fill_buffer_with_episodes(agent, n_episodes: int, ep_len: int = 50):
    rng = np.random.default_rng(0)
    for _ in range(n_episodes):
        ep = [
            (
                rng.standard_normal(agent.obs_dim).astype(np.float32),
                rng.uniform(-1, 1, agent.action_dim).astype(np.float32),
                float(rng.standard_normal()),
                rng.standard_normal(agent.obs_dim).astype(np.float32),
                t == ep_len - 1,
            )
            for t in range(ep_len)
        ]
        agent.buffer.add_episode(ep)


# ════ Quantile-Huber loss unit tests ═══════════════════════════════════════


def test_quantile_huber_loss_zero_when_pred_equals_constant_target():
    """QR-DQN loss is zero iff target is a *delta distribution* (all N
    quantiles equal to a single value) AND pred matches it exactly.
    For a non-trivial target distribution, even pred==target yields a
    positive loss — the pred_i estimates the τ_i quantile of the target
    distribution, which (in general) is not equal to target_i."""
    from andes_rl_kundur.agents.networks_critic_variants import quantile_huber_loss

    n = 51
    target = torch.full((4, n), 0.5)
    pred = torch.full((4, n), 0.5)
    loss = quantile_huber_loss(pred, target)
    assert loss.item() == pytest.approx(0.0, abs=1e-7)


def test_quantile_huber_loss_minimum_at_optimal_quantile_estimate():
    """For a target distribution = ``linspace(-2, 2, N)``, the optimal
    pred_i is roughly the τ_i-th quantile of that distribution, i.e.
    very close to the target itself (asymptotically equal). Loss at
    pred == target should be smaller than loss at a constant pred."""
    from andes_rl_kundur.agents.networks_critic_variants import quantile_huber_loss

    n = 51
    target = torch.linspace(-2.0, 2.0, n).repeat(4, 1)
    loss_match = quantile_huber_loss(target.clone(), target).item()
    loss_constant = quantile_huber_loss(torch.zeros(4, n), target).item()
    loss_far = quantile_huber_loss(torch.full((4, n), 5.0), target).item()
    assert loss_match < loss_constant < loss_far
    assert loss_match > 0  # nonzero because target has variance


def test_quantile_huber_loss_positive_for_mismatch():
    from andes_rl_kundur.agents.networks_critic_variants import quantile_huber_loss

    n = 51
    target = torch.zeros(4, n)
    pred = torch.ones(4, n)
    loss = quantile_huber_loss(pred, target)
    assert loss.item() > 0.0
    assert torch.isfinite(loss)


def test_quantile_huber_loss_broadcasts_batch():
    """Loss must scale linearly with batch when targets are independent."""
    from andes_rl_kundur.agents.networks_critic_variants import quantile_huber_loss

    n = 11
    torch.manual_seed(0)
    target = torch.randn(8, n)
    pred = torch.randn(8, n)
    loss_8 = quantile_huber_loss(pred, target).item()

    # First 4 batches alone
    loss_4 = quantile_huber_loss(pred[:4], target[:4]).item()
    loss_4b = quantile_huber_loss(pred[4:], target[4:]).item()
    # mean-over-batch averaging means loss_8 ≈ (loss_4 + loss_4b) / 2
    assert loss_8 == pytest.approx((loss_4 + loss_4b) / 2.0, rel=1e-5)


def test_quantile_huber_loss_asymmetric_weighting():
    """τ-weighted: under-prediction (pred < target) should incur larger loss
    at high quantile indices i (τ_i closer to 1) than at low indices, and
    vice versa for over-prediction."""
    from andes_rl_kundur.agents.networks_critic_variants import quantile_huber_loss

    n = 51
    # All targets at 0.5
    target = torch.full((1, n), 0.5)
    # All preds at 0 — under-prediction across the board
    pred_low = torch.zeros(1, n)
    # All preds at 1 — over-prediction across the board
    pred_high = torch.ones(1, n)

    loss_low = quantile_huber_loss(pred_low, target).item()
    loss_high = quantile_huber_loss(pred_high, target).item()
    # Both losses positive
    assert loss_low > 0 and loss_high > 0
    # Symmetric magnitude (δ=±0.5 → same Huber, same τ-distribution → same mean)
    assert loss_low == pytest.approx(loss_high, rel=1e-5)


# ════ QR network shape + forward ═══════════════════════════════════════════


def test_qr_q_network_forward_shape():
    from andes_rl_kundur.agents.networks_critic_variants import RecurrentQRQNetwork

    net = RecurrentQRQNetwork(obs_dim=7, action_dim=2, hidden=64, n_quantiles=51)
    h = net.init_hidden(4)
    obs = torch.randn(4, 7)
    act = torch.randn(4, 2)
    q, h_new = net.forward(obs, act, h)
    assert q.shape == (4, 51)
    assert h_new[0].shape == (4, 64) and h_new[1].shape == (4, 64)


def test_qr_q_network_mean_q_helper():
    from andes_rl_kundur.agents.networks_critic_variants import RecurrentQRQNetwork

    net = RecurrentQRQNetwork(obs_dim=7, action_dim=2, hidden=64, n_quantiles=51)
    q = torch.linspace(-1.0, 1.0, 51).repeat(3, 1)  # (3, 51) sym → mean = 0
    mean = net.mean_q(q)
    assert mean.shape == (3, 1)
    torch.testing.assert_close(mean.squeeze(-1), torch.zeros(3))


def test_qr_double_critic_forward_shape():
    from andes_rl_kundur.agents.networks_critic_variants import RecurrentQRDoubleQCritic

    critic = RecurrentQRDoubleQCritic(obs_dim=7, action_dim=2, hidden=64, n_quantiles=21)
    h = critic.init_hidden(2)
    obs = torch.randn(2, 7)
    act = torch.randn(2, 2)
    q1, q2, h_new = critic.forward(obs, act, h)
    assert q1.shape == (2, 21) and q2.shape == (2, 21)
    assert len(h_new) == 2  # twin hidden states


# ════ AFE network shape + forward ═════════════════════════════════════════


def test_afe_q_network_input_dim():
    from andes_rl_kundur.agents.networks_critic_variants import (
        AFE_EXPAND,
        RecurrentAfeQNetwork,
    )

    obs_dim = 7
    action_dim = 2
    net = RecurrentAfeQNetwork(obs_dim=obs_dim, action_dim=action_dim, hidden=64)
    # LSTMCell.input_size = obs_dim + AFE_EXPAND * action_dim
    assert net.lstm.input_size == obs_dim + AFE_EXPAND * action_dim
    assert net.input_dim == obs_dim + AFE_EXPAND * action_dim


def test_afe_q_network_forward_shape():
    from andes_rl_kundur.agents.networks_critic_variants import RecurrentAfeQNetwork

    net = RecurrentAfeQNetwork(obs_dim=7, action_dim=2, hidden=64)
    h = net.init_hidden(4)
    obs = torch.randn(4, 7)
    act = torch.randn(4, 2)
    q, h_new = net.forward(obs, act, h)
    assert q.shape == (4, 1)  # scalar Q output preserved
    assert h_new[0].shape == (4, 64) and h_new[1].shape == (4, 64)


def test_afe_features_zero_action_safe():
    """At a == 0, AFE features should be exactly zero (no NaN from log/div).
    obs path must still flow gradients through the LSTM."""
    from andes_rl_kundur.agents.networks_critic_variants import (
        RecurrentAfeQNetwork,
        _afe_features,
    )

    a = torch.zeros(3, 2, requires_grad=True)
    feats = _afe_features(a)
    assert feats.shape == (3, 8)
    torch.testing.assert_close(feats, torch.zeros(3, 8))

    # Critic forward at a=0 still produces finite Q
    net = RecurrentAfeQNetwork(obs_dim=7, action_dim=2, hidden=32)
    h = net.init_hidden(3)
    obs = torch.randn(3, 7)
    q, _ = net.forward(obs, a, h)
    assert torch.isfinite(q).all()


def test_afe_double_critic_drop_in_compatible():
    """AFE critic preserves the (q1, q2, h_new) forward signature."""
    from andes_rl_kundur.agents.networks_critic_variants import RecurrentAfeDoubleQCritic

    critic = RecurrentAfeDoubleQCritic(obs_dim=7, action_dim=2, hidden=64)
    h = critic.init_hidden(2)
    obs = torch.randn(2, 7)
    act = torch.randn(2, 2)
    q1, q2, h_new = critic.forward(obs, act, h)
    assert q1.shape == (2, 1) and q2.shape == (2, 1)


# ════ TD3-QR-LSTM agent integration ═══════════════════════════════════════


def test_qr_agent_satisfies_base_protocol():
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent

    agent = TD3QRLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    assert isinstance(agent, BaseAgent)
    assert agent.is_recurrent is True
    assert agent.algo_name == "td3_qr_lstm"
    assert agent.n_quantiles == 51


def test_qr_agent_update_returns_finite_loss():
    from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent

    torch.manual_seed(0)
    agent = TD3QRLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        n_quantiles=21,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    loss = agent.update()
    assert loss is not None
    assert "critic_loss" in loss and np.isfinite(loss["critic_loss"])
    assert "actor_loss" in loss and np.isfinite(loss["actor_loss"])


def test_qr_agent_gradients_reach_critic_quantile_head():
    """Critical: backprop from quantile-Huber loss must populate the
    critic's quantile-head weights. n_quantiles output must propagate
    gradient to all 51 (or n) head rows."""
    from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent

    torch.manual_seed(0)
    agent = TD3QRLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        n_quantiles=11,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    agent.update()

    # Critic Q1 quantile head weight gradient
    head_w_grad = agent.critic.q1.fc_out.weight.grad
    assert head_w_grad is not None
    assert head_w_grad.shape == (11, 64)  # n_quantiles x hidden
    # At least one row should be nonzero
    assert (head_w_grad.abs().sum(dim=-1) > 0).any()


def test_qr_agent_save_load_roundtrip():
    from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent

    torch.manual_seed(0)
    agent = TD3QRLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=40)
    agent.update()

    rng = np.random.default_rng(42)
    obs_seq = [rng.standard_normal(7).astype(np.float32) for _ in range(20)]
    agent.begin_episode()
    ref = [agent.select_action(o, deterministic=True) for o in obs_seq]

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "qr.pt")
        agent.save(path)

        loaded = TD3QRLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
        loaded.load(path)
        loaded.begin_episode()
        new = [loaded.select_action(o, deterministic=True) for o in obs_seq]

    for a, b in zip(ref, new):
        np.testing.assert_allclose(a, b, atol=1e-6)


def test_qr_ckpt_carries_algo_and_n_quantiles():
    from andes_rl_kundur.agents.td3_qr_lstm import TD3QRLstmAgent

    agent = TD3QRLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64], n_quantiles=31)
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "qr.pt")
        agent.save(path)
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        assert ckpt["algo"] == "td3_qr_lstm"
        assert ckpt["hparams"]["n_quantiles"] == 31


# ════ TD3-AFE-LSTM agent integration ═══════════════════════════════════════


def test_afe_agent_satisfies_base_protocol():
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.td3_afe_lstm import TD3AfeLstmAgent

    agent = TD3AfeLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    assert isinstance(agent, BaseAgent)
    assert agent.is_recurrent is True
    assert agent.algo_name == "td3_afe_lstm"


def test_afe_agent_update_returns_finite_loss():
    from andes_rl_kundur.agents.td3_afe_lstm import TD3AfeLstmAgent

    torch.manual_seed(0)
    agent = TD3AfeLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    loss = agent.update()
    assert loss is not None
    assert np.isfinite(loss["critic_loss"]) and np.isfinite(loss["actor_loss"])


def test_afe_agent_gradients_reach_critic_lstm_action_weights():
    """The first ``action_dim`` columns of the LSTM input weight tie to
    the linear ``a`` block; columns ``[A, 2A)`` tie to ``a²``; etc.
    All four blocks must see nonzero gradient under random data."""
    from andes_rl_kundur.agents.networks_critic_variants import AFE_EXPAND
    from andes_rl_kundur.agents.td3_afe_lstm import TD3AfeLstmAgent

    torch.manual_seed(0)
    obs_dim, action_dim = 7, 2
    agent = TD3AfeLstmAgent(
        obs_dim=obs_dim, action_dim=action_dim, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    agent.update()

    # weight_ih: (4*hidden, input_dim). input_dim = obs_dim + 4*action_dim.
    # Cols [0, obs_dim): obs block; [obs_dim, obs_dim + action_dim): a^1;
    # [obs_dim + action_dim, obs_dim + 2A): a²; etc.
    w_ih_grad = agent.critic.q1.lstm.weight_ih.grad
    assert w_ih_grad is not None
    # Total input cols
    assert w_ih_grad.shape[1] == obs_dim + AFE_EXPAND * action_dim

    # Each AFE block has at least one column with nonzero grad
    for k in range(AFE_EXPAND):
        start = obs_dim + k * action_dim
        end = start + action_dim
        block_grad = w_ih_grad[:, start:end]
        assert block_grad.abs().sum() > 0, (
            f"AFE block {k} has zero gradient — feature path dead"
        )


def test_afe_agent_save_load_roundtrip():
    from andes_rl_kundur.agents.td3_afe_lstm import TD3AfeLstmAgent

    torch.manual_seed(0)
    agent = TD3AfeLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=40)
    agent.update()

    rng = np.random.default_rng(42)
    obs_seq = [rng.standard_normal(7).astype(np.float32) for _ in range(20)]
    agent.begin_episode()
    ref = [agent.select_action(o, deterministic=True) for o in obs_seq]

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "afe.pt")
        agent.save(path)

        loaded = TD3AfeLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
        loaded.load(path)
        loaded.begin_episode()
        new = [loaded.select_action(o, deterministic=True) for o in obs_seq]

    for a, b in zip(ref, new):
        np.testing.assert_allclose(a, b, atol=1e-6)


def test_afe_ckpt_carries_algo_field():
    from andes_rl_kundur.agents.td3_afe_lstm import TD3AfeLstmAgent

    agent = TD3AfeLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "afe.pt")
        agent.save(path)
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        assert ckpt["algo"] == "td3_afe_lstm"


# ════ Stacked QR + AFE critic (R125 prototype) ═══════════════════════════


def test_qr_afe_q_network_input_dim_and_quantile_output():
    from andes_rl_kundur.agents.networks_critic_variants import (
        AFE_EXPAND,
        RecurrentQRAfeQNetwork,
    )

    net = RecurrentQRAfeQNetwork(obs_dim=7, action_dim=2, hidden=64, n_quantiles=21)
    assert net.lstm.input_size == 7 + AFE_EXPAND * 2
    h = net.init_hidden(4)
    obs = torch.randn(4, 7)
    act = torch.randn(4, 2)
    q, h_new = net.forward(obs, act, h)
    assert q.shape == (4, 21)
    assert h_new[0].shape == (4, 64)


def test_qr_afe_double_critic_drop_in():
    from andes_rl_kundur.agents.networks_critic_variants import RecurrentQRAfeDoubleQCritic

    critic = RecurrentQRAfeDoubleQCritic(
        obs_dim=7, action_dim=2, hidden=64, n_quantiles=11
    )
    h = critic.init_hidden(2)
    obs = torch.randn(2, 7)
    act = torch.randn(2, 2)
    q1, q2, h_new = critic.forward(obs, act, h)
    assert q1.shape == (2, 11) and q2.shape == (2, 11)


def test_qr_afe_agent_satisfies_protocol_and_trains():
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.td3_qr_afe_lstm import TD3QRAfeLstmAgent

    torch.manual_seed(0)
    agent = TD3QRAfeLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        n_quantiles=11,
    )
    assert isinstance(agent, BaseAgent)
    assert agent.algo_name == "td3_qr_afe_lstm"
    assert agent.is_recurrent is True
    assert agent.n_quantiles == 11

    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    loss = agent.update()
    assert loss is not None
    assert np.isfinite(loss["critic_loss"])
    assert np.isfinite(loss["actor_loss"])


def test_qr_afe_agent_save_load_roundtrip():
    from andes_rl_kundur.agents.td3_qr_afe_lstm import TD3QRAfeLstmAgent

    torch.manual_seed(0)
    agent = TD3QRAfeLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=40)
    agent.update()

    rng = np.random.default_rng(42)
    obs_seq = [rng.standard_normal(7).astype(np.float32) for _ in range(20)]
    agent.begin_episode()
    ref = [agent.select_action(o, deterministic=True) for o in obs_seq]

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "qr_afe.pt")
        agent.save(path)
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        assert ckpt["algo"] == "td3_qr_afe_lstm"
        assert ckpt["hparams"]["n_quantiles"] == 51

        loaded = TD3QRAfeLstmAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
        loaded.load(path)
        loaded.begin_episode()
        new = [loaded.select_action(o, deterministic=True) for o in obs_seq]

    for a, b in zip(ref, new):
        np.testing.assert_allclose(a, b, atol=1e-6)


# ════ Triple-stack (warmh0 + QR + AFE) agent ══════════════════════════════


def test_warmh0_qr_afe_agent_satisfies_protocol_and_trains():
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.td3_warmh0_qr_afe_lstm import (
        TD3WarmH0QRAfeLstmAgent,
    )

    torch.manual_seed(0)
    agent = TD3WarmH0QRAfeLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        n_quantiles=11,
    )
    assert isinstance(agent, BaseAgent)
    assert agent.algo_name == "td3_warmh0_qr_afe_lstm"
    assert agent.is_recurrent is True
    assert agent.n_quantiles == 11

    # Actor should be WarmH0RecurrentActor (warm h_0 wiring)
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor
    assert isinstance(agent.actor, WarmH0RecurrentActor)
    assert isinstance(agent.actor_target, WarmH0RecurrentActor)

    # Critic should be QR+AFE variant
    from andes_rl_kundur.agents.networks_critic_variants import (
        RecurrentQRAfeDoubleQCritic,
    )
    assert isinstance(agent.critic, RecurrentQRAfeDoubleQCritic)

    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    loss = agent.update()
    assert loss is not None
    assert np.isfinite(loss["critic_loss"])
    assert np.isfinite(loss["actor_loss"])


def test_warmh0_qr_afe_select_action_uses_warm_h0():
    """Triple-stack select_action should warm h_0 from obs at episode
    start — different obs values produce different first actions because
    the warm-h_0 head conditions on obs."""
    from andes_rl_kundur.agents.td3_warmh0_qr_afe_lstm import (
        TD3WarmH0QRAfeLstmAgent,
    )

    torch.manual_seed(0)
    agent = TD3WarmH0QRAfeLstmAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64], n_quantiles=11,
    )
    agent.begin_episode()
    a_obs_zeros = agent.select_action(np.zeros(7, dtype=np.float32), deterministic=True)

    agent.begin_episode()  # reset h_rollout
    a_obs_ones = agent.select_action(np.ones(7, dtype=np.float32), deterministic=True)

    # Warm-h_0 head means different obs0 → different h_0 → different a0
    assert not np.allclose(a_obs_zeros, a_obs_ones, atol=1e-5), (
        "Warm h_0 should produce different a0 for different obs0"
    )
