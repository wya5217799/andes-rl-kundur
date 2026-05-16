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


def test_lr_warmup_ramps_lr_over_first_n_training_episodes():
    """R57-α (corrected semantic): lr-warmup linearly ramps the lr from
    ``target/warmup_eps`` at the first training episode (= first episode
    in which ``update()`` actually succeeded) to ``target`` at training
    episode ``warmup_eps``, then stays at target.

    Critically, the counter only advances when ``update()`` succeeds,
    NOT on every ``begin_episode``. The R57 v1 bug counted all
    begin_episode calls including env-warmup ones; the warmup window
    expired before training started."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    target = 1e-4
    warmup = 5
    agent = TD3LSTMAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        lr=target, lr_warmup_eps=warmup,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)

    seen_lrs = []
    for ep in range(8):
        agent.begin_episode()
        loss = agent.update()  # triggers _apply_lr_warmup
        assert loss is not None
        lr_after_first_update = agent.actor_optimizer.param_groups[0]["lr"]
        # Production calls update() N times per episode (n_epoch in
        # train.py). The counter must NOT advance on the 2nd+ call,
        # so the lr observed by later gradient steps within the same
        # episode must equal the lr from the first call. This is the
        # multi-update-per-episode regression that the
        # ``_this_episode_seen_update`` flag was designed to prevent.
        agent.update()
        agent.update()
        lr_after_third_update = agent.actor_optimizer.param_groups[0]["lr"]
        assert lr_after_first_update == lr_after_third_update, (
            f"lr changed within episode {ep + 1}: "
            f"{lr_after_first_update} -> {lr_after_third_update}"
        )
        seen_lrs.append(lr_after_first_update)

    # training ep 1: target * 1/5 = 2e-5
    # training ep 5: target = 1e-4
    # training ep 6,7,8: target (constant, snap-back at boundary)
    assert len(seen_lrs) == 8, f"loop must complete 8 episodes, got {len(seen_lrs)}"
    expected = [target * (i + 1) / warmup for i in range(warmup)] + [target] * 3
    for got, exp in zip(seen_lrs, expected, strict=True):
        assert abs(got - exp) < 1e-12, f"lr {got} != expected {exp}"


def test_lr_warmup_skips_episodes_without_updates():
    """Critical R57 bug regression: if ``begin_episode()`` is called
    but ``update()`` returns None (buffer too empty), the warmup
    counter must NOT advance. Otherwise the env-warmup phase would
    consume the warmup budget before any training happens."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    target = 1e-4
    warmup = 5
    agent = TD3LSTMAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        lr=target, lr_warmup_eps=warmup,
    )

    # Simulate 10 env-warmup episodes — begin_episode is called but
    # buffer is empty, so update returns None.
    for _ in range(10):
        agent.begin_episode()
        out = agent.update()
        assert out is None, "Empty buffer must yield None from update"

    # Counter must still be 0 — no training episodes have happened.
    assert agent._episode_count == 0

    # Now fill buffer and run 3 real training episodes. lr should ramp
    # starting from training-episode 1 (lr = target/5), NOT from
    # episode 11 (which would have skipped the warmup window).
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    seen = []
    for _ in range(3):
        agent.begin_episode()
        agent.update()
        seen.append(agent.actor_optimizer.param_groups[0]["lr"])
    assert abs(seen[0] - target * 1 / warmup) < 1e-12
    assert abs(seen[1] - target * 2 / warmup) < 1e-12
    assert abs(seen[2] - target * 3 / warmup) < 1e-12


def test_lr_warmup_zero_disables():
    """lr_warmup_eps=0 (default) keeps the lr constant at target."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    target = 1e-4
    agent = TD3LSTMAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        lr=target, lr_warmup_eps=0,
    )
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)

    for _ in range(5):
        agent.begin_episode()
        agent.update()
        assert agent.actor_optimizer.param_groups[0]["lr"] == target
        assert agent.critic_optimizer.param_groups[0]["lr"] == target


def test_lr_warmup_only_advances_on_successful_update():
    """``_episode_count`` advances only inside ``update()`` when a
    batch is actually returned, NOT on every ``begin_episode`` call."""
    from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent

    agent = TD3LSTMAgent(
        obs_dim=7, action_dim=2, hidden_sizes=[64],
        batch_size=4, seq_len=10, burn_in=2, policy_delay=1,
        lr_warmup_eps=5,
    )
    assert agent._episode_count == 0
    # begin_episode alone does not advance the counter.
    agent.begin_episode()
    assert agent._episode_count == 0
    agent.begin_episode()
    assert agent._episode_count == 0

    # update without batch (buffer empty) returns None, no advance.
    out = agent.update()
    assert out is None
    assert agent._episode_count == 0

    # Now fill buffer and run a real update — counter advances.
    _fill_buffer_with_episodes(agent, n_episodes=3, ep_len=15)
    agent.begin_episode()
    agent.update()
    assert agent._episode_count == 1
    # Multiple update calls within same episode → counter advances once.
    agent.update()
    agent.update()
    assert agent._episode_count == 1
    # New episode → counter advances on first successful update.
    agent.begin_episode()
    agent.update()
    assert agent._episode_count == 2


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
