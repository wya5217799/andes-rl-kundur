"""TD3 with multi-layer nn.LSTM actor/critic — R82-W2 depth variant.

R81 W8 hidden=128 single-layer LSTMCell 退化 (geo 0.282 vs baseline 0.391).
R82-W1 Transformer (rolling window K=10) 也 RED (geo 0.01, deterministic eval
collapse). R82-W2 试 depth: 2-layer nn.LSTM, hidden=64 each layer. capacity ≈
单层 hidden=128 但 depth=2 给更好的 sequence abstraction.

Subclass TD3LSTMAgent, override __init__ 用 MultiLayer{RecurrentActor,
RecurrentDoubleQCritic}. update / rollout / replay 代码 zero change — _detach_h
recursive duck-typed (R82 fix).
"""
from __future__ import annotations

import copy
from collections.abc import Sequence

import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks import (
    MultiLayerRecurrentActor,
    MultiLayerRecurrentDoubleQCritic,
)
from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent


class TD3LSTM2Agent(TD3LSTMAgent):
    """TD3 + multi-layer nn.LSTM actor/critic."""

    algo_name: str = "td3_lstm2"
    is_recurrent: bool = True

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: int | Sequence[int],
        lr: float = 1e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 200,
        batch_size: int = 32,
        device: str = "cpu",
        policy_noise: float = 0.2,
        noise_clip: float = 0.5,
        explore_noise: float = 0.1,
        policy_delay: int = 2,
        seq_len: int = 25,
        burn_in: int = 5,
        max_grad_norm: float = 10.0,
        lr_warmup_eps: int = 0,
        num_layers: int = 2,
    ) -> None:
        if isinstance(hidden_sizes, int):
            hidden = hidden_sizes
        else:
            hidden = int(hidden_sizes[0])

        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden = hidden
        self.batch_size = batch_size
        self.device = device
        self.gamma = gamma
        self.tau = tau
        self.policy_noise = policy_noise
        self.noise_clip = noise_clip
        self.explore_noise = explore_noise
        self.policy_delay = policy_delay
        self.seq_len = seq_len
        self.burn_in = burn_in
        self.max_grad_norm = max_grad_norm
        self.lr_warmup_eps = max(0, int(lr_warmup_eps))
        self._target_lr = float(lr)
        self._episode_count = 0
        self.num_layers = num_layers

        self.actor = MultiLayerRecurrentActor(
            obs_dim, action_dim, hidden=hidden, num_layers=num_layers,
        ).to(device)
        self.actor_target = copy.deepcopy(self.actor).to(device)
        for p in self.actor_target.parameters():
            p.requires_grad = False
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

        self.critic = MultiLayerRecurrentDoubleQCritic(
            obs_dim, action_dim, hidden=hidden, num_layers=num_layers,
        ).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

        self.buffer = SequenceReplayBuffer(
            obs_dim=obs_dim, action_dim=action_dim,
            seq_len=seq_len, burn_in=burn_in,
            capacity_episodes=buffer_size,
        )

        self._h_rollout = None
        self._current_episode = []
        self._update_count = 0
        self._this_episode_seen_update = False
        self._warmup_done = False

    def save(
        self,
        path: str,
        metadata: dict | None = None,
        save_buffer: bool = False,
    ) -> None:
        torch.save(
            {
                "actor": self.actor.state_dict(),
                "actor_target": self.actor_target.state_dict(),
                "critic": self.critic.state_dict(),
                "critic_target": self.critic_target.state_dict(),
                "actor_opt": self.actor_optimizer.state_dict(),
                "critic_opt": self.critic_optimizer.state_dict(),
                "metadata": metadata or {},
                "algo": "td3_lstm2",
                "hparams": {
                    "obs_dim": self.obs_dim,
                    "action_dim": self.action_dim,
                    "hidden": self.hidden,
                    "seq_len": self.seq_len,
                    "burn_in": self.burn_in,
                    "num_layers": self.num_layers,
                },
            },
            path,
        )
