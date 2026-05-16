"""Circular replay buffer for SAC agents."""
from __future__ import annotations

import numpy as np
import torch


class ReplayBuffer:
    """Stores (obs, action, reward, next_obs, done) tuples in a fixed-size ring buffer.

    Internal arrays (obs, actions, rewards, next_obs, dones, size) are exposed as
    public attributes so that CTDECoordinator can gather aligned samples across agents
    using shared random indices.
    """

    def __init__(self, obs_dim: int, action_dim: int, capacity: int = 10_000) -> None:
        self.capacity = capacity
        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.rewards = np.zeros((capacity, 1), dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.dones = np.zeros((capacity, 1), dtype=np.float32)
        self.size: int = 0
        self._ptr: int = 0

    def add(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.obs[self._ptr] = obs
        self.actions[self._ptr] = action
        self.rewards[self._ptr] = float(reward)
        self.next_obs[self._ptr] = next_obs
        self.dones[self._ptr] = float(done)
        self._ptr = (self._ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, device: str) -> dict[str, torch.Tensor]:
        idx = np.random.randint(0, self.size, size=batch_size)

        def _t(arr: np.ndarray) -> torch.Tensor:
            return torch.FloatTensor(arr[idx]).to(device)

        return {
            'obs': _t(self.obs),
            'actions': _t(self.actions),
            'rewards': _t(self.rewards),
            'next_obs': _t(self.next_obs),
            'dones': _t(self.dones),
        }

    def clear(self) -> None:
        self.size = 0
        self._ptr = 0

    def save(self, path: str) -> None:
        np.savez_compressed(
            path,
            obs=self.obs[:self.size],
            actions=self.actions[:self.size],
            rewards=self.rewards[:self.size],
            next_obs=self.next_obs[:self.size],
            dones=self.dones[:self.size],
        )

    def load(self, path: str) -> None:
        data = np.load(path)
        n = min(int(data['obs'].shape[0]), self.capacity)
        self.obs[:n] = data['obs'][:n]
        self.actions[:n] = data['actions'][:n]
        self.rewards[:n] = data['rewards'][:n]
        self.next_obs[:n] = data['next_obs'][:n]
        self.dones[:n] = data['dones'][:n]
        self.size = n
        self._ptr = n % self.capacity

    def __len__(self) -> int:
        return self.size


# ──────────────────────────────────────────────────────────────────────
# Sequence replay (R56 — TD3+LSTM)
#
# Recurrent actors need correlated sequences (not random transitions) so
# that the hidden state's role in shaping the policy can be learned. We
# store whole episodes and sample fixed-length subsequences from them
# (the R2D2 pattern). The first ``burn_in`` steps of each sampled
# subsequence warm the LSTM hidden state with no gradient; gradient is
# computed over the remaining ``seq_len`` steps.
# ──────────────────────────────────────────────────────────────────────


class SequenceReplayBuffer:
    """Episode-keyed replay buffer that samples fixed-length subsequences.

    Stores transitions grouped by episode in a circular per-episode ring.
    ``sample(batch_size)`` returns a dict of tensors shaped
    ``(B, T, dim)`` where ``T = burn_in + seq_len``.

    Episodes shorter than ``T`` are stored but excluded from sampling.
    If no stored episode is long enough, ``sample`` returns ``None`` so
    the caller can skip the gradient step gracefully.

    Notes
    -----
    * Subsequences are sampled with stride 1 (any valid start index in
      ``[0, ep_len - T]``).
    * The episode buffer is a circular ring of capacity
      ``capacity_episodes``; oldest episodes evict first.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        seq_len: int = 25,
        burn_in: int = 5,
        capacity_episodes: int = 200,
    ) -> None:
        if seq_len < 1:
            raise ValueError(f"seq_len must be >= 1, got {seq_len}")
        if burn_in < 0:
            raise ValueError(f"burn_in must be >= 0, got {burn_in}")
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.seq_len = seq_len
        self.burn_in = burn_in
        self.capacity = capacity_episodes
        self._episodes: list[dict[str, np.ndarray]] = []
        self._ptr = 0

    @property
    def T(self) -> int:
        """Total subsequence length (burn-in + training window)."""
        return self.burn_in + self.seq_len

    def add_episode(
        self, transitions: list[tuple[np.ndarray, np.ndarray, float, np.ndarray, bool]]
    ) -> None:
        """Append a complete episode.

        Parameters
        ----------
        transitions
            List of ``(obs, action, reward, next_obs, done)`` tuples,
            one per env step.
        """
        if not transitions:
            return
        n = len(transitions)
        obs = np.zeros((n, self.obs_dim), dtype=np.float32)
        actions = np.zeros((n, self.action_dim), dtype=np.float32)
        rewards = np.zeros((n, 1), dtype=np.float32)
        next_obs = np.zeros((n, self.obs_dim), dtype=np.float32)
        dones = np.zeros((n, 1), dtype=np.float32)
        for i, (o, a, r, no, d) in enumerate(transitions):
            obs[i] = o
            actions[i] = a
            rewards[i, 0] = float(r)
            next_obs[i] = no
            dones[i, 0] = float(d)
        ep = {
            "obs": obs,
            "actions": actions,
            "rewards": rewards,
            "next_obs": next_obs,
            "dones": dones,
        }
        if len(self._episodes) < self.capacity:
            self._episodes.append(ep)
        else:
            self._episodes[self._ptr % self.capacity] = ep
        self._ptr += 1

    def n_episodes(self) -> int:
        return len(self._episodes)

    def n_valid_episodes(self) -> int:
        """Number of stored episodes long enough to sample a subsequence."""
        return sum(1 for ep in self._episodes if len(ep["obs"]) >= self.T)

    def sample(
        self, batch_size: int, device: str = "cpu"
    ) -> dict[str, torch.Tensor] | None:
        """Sample a batch of fixed-length subsequences.

        Returns
        -------
        dict or None
            Tensors shaped ``(B, T, dim)`` keyed by
            ``obs / actions / rewards / next_obs / dones``, or
            ``None`` if no stored episode is long enough.
        """
        valid_idxs = [
            i for i, ep in enumerate(self._episodes)
            if len(ep["obs"]) >= self.T
        ]
        if not valid_idxs:
            return None

        T = self.T
        chosen = np.random.choice(valid_idxs, size=batch_size, replace=True)
        out: dict[str, list[np.ndarray]] = {
            k: [] for k in ("obs", "actions", "rewards", "next_obs", "dones")
        }
        for ep_idx in chosen:
            ep = self._episodes[ep_idx]
            ep_len = len(ep["obs"])
            start = (
                0 if ep_len == T
                else int(np.random.randint(0, ep_len - T + 1))
            )
            stop = start + T
            for k in out:
                out[k].append(ep[k][start:stop])

        return {
            k: torch.from_numpy(np.stack(v)).to(device)
            for k, v in out.items()
        }

    def clear(self) -> None:
        self._episodes = []
        self._ptr = 0

    def __len__(self) -> int:
        return len(self._episodes)
