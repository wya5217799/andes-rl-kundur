"""Unit tests for the R56 SequenceReplayBuffer.

Covers shape contracts, valid/invalid episode bookkeeping, the
empty-buffer ``None`` return, circular eviction at capacity, and
basic determinism under fixed numpy seed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _make_episode(n: int, obs_dim: int = 7, action_dim: int = 2):
    rng = np.random.default_rng(0)
    return [
        (
            rng.standard_normal(obs_dim).astype(np.float32),
            rng.uniform(-1, 1, action_dim).astype(np.float32),
            float(rng.standard_normal()),
            rng.standard_normal(obs_dim).astype(np.float32),
            i == n - 1,  # last step is done
        )
        for i in range(n)
    ]


def test_sequence_buffer_sample_returns_correct_shapes():
    """Standard happy path: 50-step episode, seq_len=25, burn_in=5,
    batch=4 → tensors (4, 30, dim)."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(
        obs_dim=7, action_dim=2, seq_len=25, burn_in=5,
        capacity_episodes=10,
    )
    buf.add_episode(_make_episode(50))
    np.random.seed(0)
    batch = buf.sample(4)
    assert batch is not None
    assert batch["obs"].shape == (4, 30, 7)
    assert batch["actions"].shape == (4, 30, 2)
    assert batch["rewards"].shape == (4, 30, 1)
    assert batch["next_obs"].shape == (4, 30, 7)
    assert batch["dones"].shape == (4, 30, 1)


def test_sequence_buffer_returns_none_when_no_valid_episodes():
    """When every stored episode is shorter than burn_in + seq_len,
    sample() must return None (caller skips the update step)."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(
        obs_dim=7, action_dim=2, seq_len=25, burn_in=5,
    )
    buf.add_episode(_make_episode(10))  # too short
    buf.add_episode(_make_episode(20))  # also too short (< 30)
    assert buf.n_episodes() == 2
    assert buf.n_valid_episodes() == 0
    assert buf.sample(4) is None


def test_sequence_buffer_returns_none_when_empty():
    """Empty buffer → None."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(obs_dim=7, action_dim=2, seq_len=25, burn_in=5)
    assert buf.sample(4) is None


def test_sequence_buffer_only_samples_from_valid_episodes():
    """If episodes have mixed lengths, samples only come from those
    with len >= T. Mix one valid (50) and one too-short (10); sample
    1000 times and confirm every drawn subsequence has shape T."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(
        obs_dim=7, action_dim=2, seq_len=25, burn_in=5,
    )
    buf.add_episode(_make_episode(50))
    buf.add_episode(_make_episode(10))
    assert buf.n_valid_episodes() == 1
    np.random.seed(1)
    for _ in range(20):
        b = buf.sample(8)
        assert b is not None
        assert b["obs"].shape == (8, 30, 7)


def test_sequence_buffer_circular_eviction():
    """Capacity-bound: adding capacity+1 episodes evicts the first."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(
        obs_dim=7, action_dim=2, seq_len=5, burn_in=0, capacity_episodes=3,
    )
    # Inject distinguishable first-element values per episode.
    for tag in range(5):
        ep = _make_episode(10)
        marked = []
        for (o, a, r, no, d) in ep:
            o2 = o.copy()
            o2[0] = float(tag)
            marked.append((o2, a, r, no, d))
        buf.add_episode(marked)
    assert buf.n_episodes() == 3

    # Verify the three retained episodes are tag 2, 3, 4 (in some
    # storage order — the ring overwrites tag 0 then tag 1).
    first_obs_tags = sorted(
        float(ep["obs"][0, 0]) for ep in buf._episodes
    )
    assert first_obs_tags == [2.0, 3.0, 4.0]


def test_sequence_buffer_exact_length_episode():
    """Episode whose length equals T must be sampleable with start=0."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(
        obs_dim=7, action_dim=2, seq_len=20, burn_in=10,  # T = 30
    )
    buf.add_episode(_make_episode(30))
    assert buf.n_valid_episodes() == 1
    b = buf.sample(2)
    assert b is not None
    assert b["obs"].shape == (2, 30, 7)


def test_sequence_buffer_constructor_rejects_invalid_args():
    """Negative seq_len or burn_in is a programmer error — raise."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer
    import pytest

    with pytest.raises(ValueError):
        SequenceReplayBuffer(obs_dim=7, action_dim=2, seq_len=0, burn_in=5)
    with pytest.raises(ValueError):
        SequenceReplayBuffer(obs_dim=7, action_dim=2, seq_len=25, burn_in=-1)


def test_sequence_buffer_T_property():
    """T = burn_in + seq_len convenience property."""
    from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer

    buf = SequenceReplayBuffer(obs_dim=7, action_dim=2, seq_len=25, burn_in=5)
    assert buf.T == 30
