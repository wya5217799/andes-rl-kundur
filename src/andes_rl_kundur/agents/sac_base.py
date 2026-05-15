"""Shared concrete base for the per-agent SAC variants.

Both :class:`SACAgent` (independent critic) and :class:`SACAgentCTDE`
(critic shared via :class:`CTDECoordinator`) duplicated ~80 lines of
constructor and a handful of methods (actor network, log_alpha + alpha
optimizer, per-agent replay buffer, ``select_action``,
``store_transition``, the ``alpha`` property). Lift them here so a fix
in any one place benefits all variants and so future SAC-shaped
algorithms (TD3, DDPG) reuse the same scaffold.

The :class:`BaseAgent` Protocol covers the *contract* this class implements;
this module covers the *implementation*.
"""
from __future__ import annotations

import math

import numpy as np
import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks import GaussianActor
from andes_rl_kundur.agents.replay_buffer import ReplayBuffer


class _SACBase:
    """Per-agent SAC scaffold — actor + alpha + replay buffer + select/store."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes,
        lr: float = 3e-4,
        buffer_size: int = 10000,
        batch_size: int = 256,
        device: str = "cpu",
        alpha_min: float = 0.005,
        alpha_max: float = 5.0,
    ) -> None:
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.batch_size = batch_size
        self.device = device

        self.actor = GaussianActor(obs_dim, action_dim, hidden_sizes).to(device)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

        self.target_entropy = -float(action_dim)
        self.log_alpha = torch.zeros(1, requires_grad=True, device=device)
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=lr)
        self._log_alpha_min = math.log(alpha_min)
        self._log_alpha_max = math.log(alpha_max)

        self.buffer = ReplayBuffer(obs_dim, action_dim, capacity=buffer_size)
        self.max_grad_norm = 1.0

    @property
    def alpha(self) -> torch.Tensor:
        return self.log_alpha.exp()

    def select_action(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        obs_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        with torch.no_grad():
            if deterministic:
                action = self.actor.deterministic(obs_t)
            else:
                action, _ = self.actor.sample(obs_t)
        return action.cpu().numpy().flatten()

    def store_transition(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.add(obs, action, reward, next_obs, done)
