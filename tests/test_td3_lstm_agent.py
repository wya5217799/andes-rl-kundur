"""Tests for the R56 TD3LSTMAgent.

Critical contracts:
- Satisfies the BaseAgent Protocol (so train.py treats it like other agents).
- ``select_action`` is stateful: same obs at two consecutive calls produces
  different actions because the internal hidden state advances.
- ``store_transition`` flushes on ``done=True``.
- ``update()`` returns ``None`` until at least one full-length episode is
  in the buffer, then returns a loss dict.
- Gradients reach the actor LSTM weights after an actor-update step.
- ``save`` / ``load`` roundtrip preserves the actor outputs bit-exactly.
- The deterministic eval policy is time-varying within an episode (the
  defining R56 property that escapes the R49–R55 hexagon).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _fill_buffer_with_episodes(agent, n_episodes: int, ep_len: int = 50):
    """Append ``n_episodes`` synthetic episodes to ``agent.buffer``."""
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


def test_td3_lstm_satisfies_base_agent_protocol():
    from andes_rl_kundur.agents.base_agent import BaseAgent
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    assert isinstance(agent, BaseAgent)
    assert agent.is_recurrent is True
    assert agent.algo_name == "td3_lstm"


def test_select_action_is_stateful_and_time_varying():
    """Defining R56 property: a deterministic policy at the SAME obs
    must produce different actions at two consecutive calls within
    one episode (hidden state advances)."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    torch.manual_seed(0)
    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    agent.begin_episode()
    obs = np.zeros(7, dtype=np.float32)
    a1 = agent.select_action(obs, deterministic=True)
    a2 = agent.select_action(obs, deterministic=True)
    assert not np.allclose(a1, a2, atol=1e-7), (
        "Deterministic eval at constant obs should still drift via hidden state"
    )


def test_begin_episode_resets_hidden_state():
    """Two fresh episodes must produce identical first actions when
    obs is the same — proves the rollout hidden state was reset."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    torch.manual_seed(0)
    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    obs = np.zeros(7, dtype=np.float32)

    agent.begin_episode()
    a_first_ep1 = agent.select_action(obs, deterministic=True)
    # Walk a few steps to evolve the hidden state
    for _ in range(5):
        agent.select_action(obs, deterministic=True)

    agent.begin_episode()
    a_first_ep2 = agent.select_action(obs, deterministic=True)
    np.testing.assert_allclose(a_first_ep1, a_first_ep2, atol=1e-7)


def test_exploration_noise_clipped_to_range():
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64],
                         explore_noise=10.0)
    agent.begin_episode()
    obs = np.zeros(7, dtype=np.float32)
    for _ in range(10):
        a = agent.select_action(obs, deterministic=False)
        assert np.all(a >= -1.0) and np.all(a <= 1.0)


def test_store_transition_flushes_on_done():
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    agent.begin_episode()
    rng = np.random.default_rng(0)
    for t in range(30):
        agent.store_transition(
            obs=rng.standard_normal(7).astype(np.float32),
            action=rng.uniform(-1, 1, 2).astype(np.float32),
            reward=-1.0,
            next_obs=rng.standard_normal(7).astype(np.float32),
            done=(t == 29),
        )
    assert agent.buffer.n_episodes() == 1
    assert agent._current_episode == []


def test_update_returns_none_when_buffer_empty():
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    assert agent.update() is None


def test_update_returns_loss_dict_after_episode_stored():
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64],
                         batch_size=4, seq_len=10, burn_in=2,
                         policy_delay=1)
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    loss = agent.update()
    assert loss is not None
    assert "critic_loss" in loss
    assert "actor_loss" in loss
    assert np.isfinite(loss["critic_loss"])
    assert np.isfinite(loss["actor_loss"])


def test_update_gradients_reach_actor_lstm_weights():
    """Critical: backprop from actor loss must populate the LSTM weight
    gradients. If grad is None, the recurrent unroll is broken."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    torch.manual_seed(0)
    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64],
                         batch_size=4, seq_len=10, burn_in=2,
                         policy_delay=1)
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)

    # First update advances _update_count to 1; policy_delay=1 means
    # actor.step happens, so LSTM weights see their first gradient.
    agent.update()
    assert agent.actor.lstm.weight_ih.grad is not None
    assert agent.actor.lstm.weight_hh.grad is not None
    assert agent.actor.fc_out.weight.grad is not None


def test_save_load_roundtrip_preserves_deterministic_output():
    """Save → load on a fresh agent must reproduce the original
    deterministic action sequence bit-exactly."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    torch.manual_seed(0)
    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    # Drift parameters a bit via a random update (avoid trivial init match)
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=40)
    agent.update()

    # Capture reference trajectory
    rng = np.random.default_rng(42)
    obs_seq = [rng.standard_normal(7).astype(np.float32) for _ in range(20)]
    agent.begin_episode()
    ref_actions = [agent.select_action(o, deterministic=True) for o in obs_seq]

    # Save and load into a new agent
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "agent.pt")
        agent.save(path)

        loaded = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
        loaded.load(path)
        loaded.begin_episode()
        new_actions = [loaded.select_action(o, deterministic=True) for o in obs_seq]

    for a, b in zip(ref_actions, new_actions):
        np.testing.assert_allclose(a, b, atol=1e-6)


def test_select_action_recurrent_is_stateless():
    """select_action_recurrent does not mutate any agent state — two
    calls with the same h return the same action."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    torch.manual_seed(0)
    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    obs = np.zeros(7, dtype=np.float32)
    h = agent.actor.init_hidden(1, agent.device)
    a1, h1 = agent.select_action_recurrent(obs, h, deterministic=True)
    a2, h2 = agent.select_action_recurrent(obs, h, deterministic=True)
    np.testing.assert_allclose(a1, a2, atol=1e-7)
    # And the agent's internal rollout state is unchanged
    assert agent._h_rollout is None


def test_ckpt_carries_algo_field():
    """checkpoint_loader.detect_algo() must see ``td3_lstm`` so the
    eval path routes correctly."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(obs_dim=7, action_dim=2, hidden_sizes=[64])
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "agent_0_best.pt")
        agent.save(path)
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        assert ckpt["algo"] == "td3_lstm"
