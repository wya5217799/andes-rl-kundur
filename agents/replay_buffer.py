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
