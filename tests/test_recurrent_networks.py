"""Unit tests for the R56 recurrent networks.

The RecurrentActor's defining property is that ``π(obs_t, h_t)`` is
structurally time-varying — feeding the SAME obs at two consecutive
calls must produce DIFFERENT actions, because the hidden state carries
trajectory information from the prior call. This property is what
escapes the R49–R55 hexagon's static-setpoint attractor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_recurrent_actor_produces_time_varying_output_given_constant_obs():
    """The key R56 property: identical obs at t and t+1 still gives
    different actions because h_t evolves. This is the structural
    escape from the R49–R55 noise-hijack channel."""
    from andes_rl_kundur.agents.networks import RecurrentActor

    torch.manual_seed(0)
    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(1, 7)
    h = actor.init_hidden(1)
    a1, h1 = actor(obs, h)
    a2, h2 = actor(obs, h1)
    # Strong inequality: a single forward should perturb h_t enough
    # to shift the tanh-output detectably even with same obs.
    assert not torch.allclose(a1, a2, atol=1e-6), (
        "RecurrentActor failed the time-varying-output property — "
        "structural memory not engaged"
    )


def test_recurrent_actor_batched_forward_preserves_shapes():
    """Batched forward returns (B, A) action and per-element hidden state."""
    from andes_rl_kundur.agents.networks import RecurrentActor

    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(32, 7)
    h = actor.init_hidden(32)
    a, (h_new, c_new) = actor(obs, h)
    assert a.shape == (32, 2)
    assert h_new.shape == (32, 64)
    assert c_new.shape == (32, 64)


def test_recurrent_actor_output_in_tanh_range():
    """Output passes through tanh — must lie in [-1, 1]."""
    from andes_rl_kundur.agents.networks import RecurrentActor

    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(16, 7) * 100  # force large pre-tanh activations
    h = actor.init_hidden(16)
    a, _ = actor(obs, h)
    assert (a >= -1.0).all() and (a <= 1.0).all()


def test_recurrent_actor_init_hidden_zeros_and_correct_device():
    """Initial hidden state is zero on the requested device."""
    from andes_rl_kundur.agents.networks import RecurrentActor

    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    h, c = actor.init_hidden(4, device="cpu")
    assert torch.equal(h, torch.zeros(4, 64))
    assert torch.equal(c, torch.zeros(4, 64))
    assert h.device.type == "cpu"


def test_recurrent_critic_returns_two_qs_and_two_hidden_states():
    """RecurrentDoubleQCritic.forward returns (q1, q2, (h1_new, h2_new))."""
    from andes_rl_kundur.agents.networks import RecurrentDoubleQCritic

    critic = RecurrentDoubleQCritic(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(8, 7)
    action = torch.randn(8, 2)
    h_prev = critic.init_hidden(8)
    q1, q2, (h1_new, h2_new) = critic(obs, action, h_prev)
    assert q1.shape == (8, 1)
    assert q2.shape == (8, 1)
    assert h1_new[0].shape == (8, 64)
    assert h2_new[0].shape == (8, 64)


def test_recurrent_critic_q1_q2_independent_params():
    """Q1 and Q2 must not share parameters — required for the TD3 min-Q
    target trick to remain unbiased."""
    from andes_rl_kundur.agents.networks import RecurrentDoubleQCritic

    critic = RecurrentDoubleQCritic(obs_dim=7, action_dim=2, hidden=64)
    q1_params = list(critic.q1.parameters())
    q2_params = list(critic.q2.parameters())
    # Object-identity check: no shared tensors
    q1_ids = {id(p) for p in q1_params}
    q2_ids = {id(p) for p in q2_params}
    assert q1_ids.isdisjoint(q2_ids)


def test_recurrent_actor_gradients_flow_to_lstm_weights():
    """Critical contract for the R56 training loop: backprop from a
    loss on the actor output must populate ``actor.lstm.weight_ih_l0.grad``.
    If grad is None, the recurrent unroll is broken (R2D2-style burn-in
    gradient leakage was the original source of this class of bug)."""
    from andes_rl_kundur.agents.networks import RecurrentActor

    torch.manual_seed(0)
    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(4, 7)
    h = actor.init_hidden(4)
    a, _ = actor(obs, h)
    loss = a.pow(2).sum()
    loss.backward()
    # nn.LSTMCell exposes weight_ih / weight_hh (no _l0 suffix because
    # it's a single-layer cell, unlike nn.LSTM).
    assert actor.lstm.weight_ih.grad is not None, (
        "Gradient did not reach LSTMCell.weight_ih — recurrent unroll broken"
    )
    assert actor.lstm.weight_hh.grad is not None
    assert actor.fc_out.weight.grad is not None


def test_recurrent_actor_deterministic_alias_matches_forward():
    """deterministic(obs, h) is an alias for forward(obs, h) — exposed
    for API symmetry with GaussianActor.deterministic()."""
    from andes_rl_kundur.agents.networks import RecurrentActor

    torch.manual_seed(0)
    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(2, 7)
    h = actor.init_hidden(2)
    a_fwd, h_fwd = actor.forward(obs, h)
    a_det, h_det = actor.deterministic(obs, h)
    assert torch.equal(a_fwd, a_det)
    assert torch.equal(h_fwd[0], h_det[0])
    assert torch.equal(h_fwd[1], h_det[1])
