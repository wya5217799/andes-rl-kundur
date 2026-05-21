"""Unit tests for R107 + R109 warm-h_0 modules.

Covers:
- ``WarmH0RecurrentActor`` forward pass + zero-vs-warm init contract
- ``from_pretrained`` round-trip bit-identicality on LSTM weights
- ``TD3LSTMWarmH0Agent`` end-to-end smoke (instantiate + 6-step rollout)
- Algo-name + is_recurrent flag for checkpoint_loader compatibility
"""
from __future__ import annotations

import sys
import types

import numpy as np
import pytest
import torch


@pytest.fixture(autouse=True, scope="module")
def _stub_andes():
    """`andes_rl_kundur` package imports the ``andes`` Simulink package
    transitively. Stub it so these unit tests run on Windows host
    Python (where ANDES is not installed)."""
    if "andes" not in sys.modules:
        sys.modules["andes"] = types.ModuleType("andes")
    yield


def test_warm_h0_actor_zero_init_is_zero():
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor

    actor = WarmH0RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    h, c = actor.init_hidden(8, "cpu")
    assert torch.allclose(h, torch.zeros_like(h))
    assert torch.allclose(c, torch.zeros_like(c))


def test_warm_h0_actor_warm_init_is_nonzero():
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor

    actor = WarmH0RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(8, 7) * 0.25
    h, c = actor.init_hidden(8, "cpu", obs_for_warm=obs)
    # Random-init MLP unlikely to map all 8 obs to exactly zero
    assert h.norm() > 1e-3
    assert c.norm() > 1e-3
    assert h.shape == (8, 64)
    assert c.shape == (8, 64)


def test_warm_h0_actor_forward_shapes():
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor

    actor = WarmH0RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(4, 7) * 0.25
    h0 = actor.init_hidden(4, "cpu", obs_for_warm=obs)
    a, h_new = actor(obs, h0)
    assert a.shape == (4, 2)
    assert h_new[0].shape == (4, 64)
    assert h_new[1].shape == (4, 64)
    # tanh-bounded
    assert a.abs().max() <= 1.0 + 1e-6


def test_warm_h0_obs_for_warm_batch_mismatch_raises():
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor

    actor = WarmH0RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(8, 7)
    with pytest.raises(ValueError, match="batch"):
        actor.init_hidden(4, "cpu", obs_for_warm=obs)  # 8 != 4


def test_warm_h0_from_pretrained_copies_lstm_bit_identical():
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor
    from andes_rl_kundur.agents.networks import RecurrentActor

    vanilla = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    booted = WarmH0RecurrentActor.from_pretrained(
        vanilla.state_dict(), obs_dim=7, action_dim=2, hidden=64
    )
    # LSTM weights match
    assert torch.allclose(vanilla.lstm.weight_ih, booted.lstm.weight_ih)
    assert torch.allclose(vanilla.lstm.weight_hh, booted.lstm.weight_hh)
    assert torch.allclose(vanilla.lstm.bias_ih, booted.lstm.bias_ih)
    assert torch.allclose(vanilla.lstm.bias_hh, booted.lstm.bias_hh)
    # fc_out matches
    assert torch.allclose(vanilla.fc_out.weight, booted.fc_out.weight)
    assert torch.allclose(vanilla.fc_out.bias, booted.fc_out.bias)
    # h_init / c_init present but at random init (have nonzero weight norm)
    assert booted.h_init[0].weight.norm() > 0
    assert booted.c_init[0].weight.norm() > 0


def test_warm_h0_param_count_overhead():
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor
    from andes_rl_kundur.agents.networks import RecurrentActor

    vanilla = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    warm = WarmH0RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    n_v = sum(p.numel() for p in vanilla.parameters())
    n_w = sum(p.numel() for p in warm.parameters())
    # Expected overhead = 2 × (Linear(7,32)=7*32+32=256 + Linear(32,64)=32*64+64=2112) = 4736
    assert n_w - n_v == 4736, f"Overhead {n_w - n_v} != expected 4736"


def test_td3_lstm_warmh0_agent_smoke():
    from andes_rl_kundur.agents.td3_lstm_warmh0 import TD3LSTMWarmH0Agent
    from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor

    ag = TD3LSTMWarmH0Agent(
        obs_dim=7, action_dim=2, hidden_sizes=64, device="cpu"
    )
    assert ag.algo_name == "td3_lstm_warmh0"
    assert ag.is_recurrent is True
    assert isinstance(ag.actor, WarmH0RecurrentActor)
    assert isinstance(ag.actor_target, WarmH0RecurrentActor)

    ag.begin_episode()
    for _ in range(6):
        obs = np.random.randn(7).astype(np.float32) * 0.3
        a = ag.select_action(obs, deterministic=True)
        assert a.shape == (2,)
        assert np.all(np.isfinite(a))
        assert np.all(np.abs(a) <= 1.0 + 1e-6)


def test_td3_lstm_warmh0_select_action_recurrent():
    """Stateless variant: caller manages hidden state. First call (h=None)
    must build warm h_0 from current obs."""
    from andes_rl_kundur.agents.td3_lstm_warmh0 import TD3LSTMWarmH0Agent

    ag = TD3LSTMWarmH0Agent(obs_dim=7, action_dim=2, hidden_sizes=64)
    obs = np.random.randn(7).astype(np.float32) * 0.3
    a, h = ag.select_action_recurrent(obs, h=None, deterministic=True)
    assert a.shape == (2,)
    # h is a non-zero warm state
    h_tensor, c_tensor = h
    assert h_tensor.norm() > 1e-3
    # Subsequent call advances h, doesn't re-warm
    obs2 = np.random.randn(7).astype(np.float32) * 0.3
    a2, h2 = ag.select_action_recurrent(obs2, h=h, deterministic=True)
    assert a2.shape == (2,)
    # h advanced (not identical)
    assert not torch.allclose(h2[0], h_tensor)
