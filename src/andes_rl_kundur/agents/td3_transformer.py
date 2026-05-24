"""TD3 with Transformer actor/critic — R82 novel architecture explore.

R81 9-wave sweep (R72_w4 LSTM baseline ± single-axis) 0 突破, 证 R72_w4 hyper
是 narrow local basin. R82 走 novel architecture: 用 multi-head self-attention
over rolling obs window (K=10) 替换 LSTMCell stateful rollout.

设计 trick: subclass TD3LSTMAgent 仅 override `__init__` 用 TransformerActor /
TransformerDoubleQCritic. update / rollout / replay 代码 zero change — 都是
通过 `actor.forward(obs, h_prev) -> (out, h_new)` 接口走, 跟 hidden type 无关.

不动 TD3LSTMAgent (R72_w4 baseline 依赖).
"""
from __future__ import annotations

import copy
from collections.abc import Sequence

import torch
import torch.optim as optim

from andes_rl_kundur.agents.networks import (
    TransformerActor,
    TransformerDoubleQCritic,
)
from andes_rl_kundur.agents.replay_buffer import SequenceReplayBuffer
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent


class TD3TransformerAgent(TD3LSTMAgent):
    """TD3 + Transformer actor/critic.

    跟 TD3LSTMAgent 相同接口 (BaseAgent Protocol + is_recurrent=True), 但
    actor/critic 网络换成 TransformerActor / TransformerDoubleQCritic.
    """

    algo_name: str = "td3_transformer"
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
        window_k: int = 10,
        n_heads: int = 4,
        n_layers: int = 1,
    ) -> None:
        if isinstance(hidden_sizes, int):
            hidden = hidden_sizes
        else:
            hidden = int(hidden_sizes[0])

        # hidden 必须能被 n_heads 整除 (TransformerEncoderLayer 要求)
        if hidden % n_heads != 0:
            raise ValueError(
                f"hidden={hidden} 必须能被 n_heads={n_heads} 整除. "
                f"考虑 hidden=64 + n_heads=4 (R82 baseline) 或 hidden=128 + n_heads=4/8."
            )

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
        self.window_k = window_k
        self.n_heads = n_heads
        self.n_layers = n_layers

        # Transformer actor + target
        self.actor = TransformerActor(
            obs_dim, action_dim, hidden=hidden,
            window_k=window_k, n_heads=n_heads, n_layers=n_layers,
        ).to(device)
        self.actor_target = copy.deepcopy(self.actor).to(device)
        for p in self.actor_target.parameters():
            p.requires_grad = False
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

        # Transformer twin critics + target
        self.critic = TransformerDoubleQCritic(
            obs_dim, action_dim, hidden=hidden,
            window_k=window_k, n_heads=n_heads, n_layers=n_layers,
        ).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

        # Sequence replay buffer (跟 TD3LSTMAgent 完全相同)
        self.buffer = SequenceReplayBuffer(
            obs_dim=obs_dim,
            action_dim=action_dim,
            seq_len=seq_len,
            burn_in=burn_in,
            capacity_episodes=buffer_size,
        )

        # Stateful rollout bookkeeping (跟父类一致)
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
        """Override 父类 save: algo field = 'td3_transformer' 不是 'td3_lstm'."""
        torch.save(
            {
                "actor": self.actor.state_dict(),
                "actor_target": self.actor_target.state_dict(),
                "critic": self.critic.state_dict(),
                "critic_target": self.critic_target.state_dict(),
                "actor_opt": self.actor_optimizer.state_dict(),
                "critic_opt": self.critic_optimizer.state_dict(),
                "metadata": metadata or {},
                "algo": "td3_transformer",
                "hparams": {
                    "obs_dim": self.obs_dim,
                    "action_dim": self.action_dim,
                    "hidden": self.hidden,
                    "seq_len": self.seq_len,
                    "burn_in": self.burn_in,
                    "window_k": self.window_k,
                    "n_heads": self.n_heads,
                    "n_layers": self.n_layers,
                },
            },
            path,
        )
