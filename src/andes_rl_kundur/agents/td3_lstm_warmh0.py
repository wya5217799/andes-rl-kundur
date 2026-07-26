"""TD3-LSTM with warm-h_0 actor (Q-0022 / R96 implementation).

Drop-in extension of :class:`TD3LSTMAgent` that swaps
``RecurrentActor`` for :class:`WarmH0RecurrentActor` (both built in
R107). The actor learns ``(h_0, c_0) = (h_init(obs_0), c_init(obs_0))``
instead of zeros, eliminating the 10-step LSTM warm-up lag documented
in CLM-0174 / CLM-0183 / CLM-0188 / CLM-0193.

This file is **separate from td3_lstm.py** so concurrent training runs
(R83 obs-aug, R94 widen-bound, etc.) that depend on the vanilla
``TD3LSTMAgent`` are not perturbed.

Integration for R96 launch (NOT applied — preparatory code only):
1. ``scripts/train.py`` dispatcher gains ``--algo td3_lstm_warmh0`` →
   constructs ``TD3LSTMWarmH0Agent``.
2. ``checkpoint_loader.py`` gains ``elif algo == "td3_lstm_warmh0":``
   branch to load this class.
3. Training launches with the same R72_w4 hyperparameters
   (tau=0.005×, warmup=5 ep, h=64, paper-faithful obs) for direct
   comparison against the SOTA baseline.

The four override points vs ``TD3LSTMAgent``:

| Method | Reason for override |
|---|---|
| ``__init__`` | swap actor / actor_target to ``WarmH0RecurrentActor`` |
| ``select_action`` | pass ``obs_t`` to ``init_hidden(.., obs_for_warm=)`` at episode start |
| ``select_action_recurrent`` | same as above for stateless variant |
| ``update`` | pass ``obs[:, 0]`` for actor + actor_target init_hidden |

Critics remain on ``RecurrentDoubleQCritic`` with h=0 init — matches
the CLM-0183 / CLM-0188 forensics convention and limits the scope of
this experiment to actor-side warm-up only.
"""
from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import (
    HiddenState,
)
from andes_rl_kundur.agents.networks_warmh0 import WarmH0RecurrentActor
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent, _detach_h


class TD3LSTMWarmH0Agent(TD3LSTMAgent):
    """TD3-LSTM agent with learnable warm h_0 actor (Q-0022)."""

    algo_name: str = "td3_lstm_warmh0"
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
    ) -> None:
        super().__init__(
            obs_dim=obs_dim,
            action_dim=action_dim,
            hidden_sizes=hidden_sizes,
            lr=lr,
            gamma=gamma,
            tau=tau,
            buffer_size=buffer_size,
            batch_size=batch_size,
            device=device,
            policy_noise=policy_noise,
            noise_clip=noise_clip,
            explore_noise=explore_noise,
            policy_delay=policy_delay,
            seq_len=seq_len,
            burn_in=burn_in,
            max_grad_norm=max_grad_norm,
            lr_warmup_eps=lr_warmup_eps,
        )
        # Override the actor / actor_target with WarmH0 variant.
        # Critic stays RecurrentDoubleQCritic — actor-side warm-up only.
        hidden = self.hidden
        self.actor = WarmH0RecurrentActor(obs_dim, action_dim, hidden=hidden).to(device)
        self.actor_target = copy.deepcopy(self.actor).to(device)
        for p in self.actor_target.parameters():
            p.requires_grad = False
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

    # ─── Stateful rollout interface (override to thread obs_for_warm) ──

    def select_action(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
        if self._h_rollout is None:
            # First step of episode: use warm h_0 from obs_0.
            self._h_rollout = self.actor.init_hidden(
                1, self.device, obs_for_warm=obs_t
            )
        with torch.no_grad():
            action, h_new = self.actor(obs_t, self._h_rollout)
        self._h_rollout = h_new
        action_np = action.cpu().numpy().flatten()
        if not deterministic:
            noise = np.random.normal(0.0, self.explore_noise, size=action_np.shape)
            action_np = np.clip(action_np + noise, -1.0, 1.0)
        return action_np.astype(np.float32)

    def select_action_recurrent(
        self,
        obs: np.ndarray,
        h: HiddenState | None,
        deterministic: bool = True,
    ) -> tuple[np.ndarray, HiddenState]:
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
        if h is None:
            h = self.actor.init_hidden(1, self.device, obs_for_warm=obs_t)
        with torch.no_grad():
            action, h_new = self.actor(obs_t, h)
        action_np = action.cpu().numpy().flatten()
        if not deterministic:
            noise = np.random.normal(0.0, self.explore_noise, size=action_np.shape)
            action_np = np.clip(action_np + noise, -1.0, 1.0)
        return action_np.astype(np.float32), h_new

    # ─── Gradient update (override to thread obs[:, 0] for actor h_0) ──

    def update(self) -> dict[str, Any] | None:
        batch = self.buffer.sample(self.batch_size, self.device)
        if batch is None:
            return None

        if not self._this_episode_seen_update:
            self._episode_count += 1
            self._this_episode_seen_update = True
        self._apply_lr_warmup()
        self._update_count += 1

        obs = batch["obs"]
        actions = batch["actions"]
        rewards = batch["rewards"]
        next_obs = batch["next_obs"]
        dones = batch["dones"]
        B = obs.shape[0]

        # NEW: warm h_0 from first-step obs of each sequence.
        obs_first = obs[:, 0]

        with torch.no_grad():
            h_a = self.actor.init_hidden(B, self.device, obs_for_warm=obs_first)
            h_a_tgt = self.actor_target.init_hidden(
                B, self.device, obs_for_warm=obs_first
            )
            # Critics still zero-init (matches CLM-0183 forensics scope).
            h_c1 = self.critic.q1.init_hidden(B, self.device)
            h_c2 = self.critic.q2.init_hidden(B, self.device)
            h_c1_tgt = self.critic_target.q1.init_hidden(B, self.device)
            h_c2_tgt = self.critic_target.q2.init_hidden(B, self.device)

            for t in range(self.burn_in):
                _, h_a = self.actor(obs[:, t], h_a)
                _, h_a_tgt = self.actor_target(obs[:, t], h_a_tgt)
                _, h_c1 = self.critic.q1(obs[:, t], actions[:, t], h_c1)
                _, h_c2 = self.critic.q2(obs[:, t], actions[:, t], h_c2)
                _, h_c1_tgt = self.critic_target.q1(obs[:, t], actions[:, t], h_c1_tgt)
                _, h_c2_tgt = self.critic_target.q2(obs[:, t], actions[:, t], h_c2_tgt)
            _, h_a_tgt = self.actor_target(obs[:, self.burn_in], h_a_tgt)

        h_a = _detach_h(h_a)
        h_a_tgt = _detach_h(h_a_tgt)
        h_c1 = _detach_h(h_c1)
        h_c2 = _detach_h(h_c2)
        h_c1_tgt = _detach_h(h_c1_tgt)
        h_c2_tgt = _detach_h(h_c2_tgt)

        # ─── Critic loss roll (identical to base class) ───────────────
        h_c1_critic = h_c1
        h_c2_critic = h_c2
        critic_losses: list[torch.Tensor] = []
        for t in range(self.burn_in, self.burn_in + self.seq_len):
            with torch.no_grad():
                _, h_c1_tgt = self.critic_target.q1(
                    obs[:, t], actions[:, t], h_c1_tgt
                )
                _, h_c2_tgt = self.critic_target.q2(
                    obs[:, t], actions[:, t], h_c2_tgt
                )
                target_a_raw, h_a_tgt = self.actor_target(next_obs[:, t], h_a_tgt)
                noise = (
                    torch.randn_like(target_a_raw)
                    * self.policy_noise
                ).clamp(-self.noise_clip, self.noise_clip)
                target_a = (target_a_raw + noise).clamp(-1.0, 1.0)
                q1_tgt, _ = self.critic_target.q1(next_obs[:, t], target_a, h_c1_tgt)
                q2_tgt, _ = self.critic_target.q2(next_obs[:, t], target_a, h_c2_tgt)
                q_tgt = torch.min(q1_tgt, q2_tgt)
                y = rewards[:, t] + self.gamma * (1 - dones[:, t]) * q_tgt

            q1, h_c1_critic = self.critic.q1(obs[:, t], actions[:, t], h_c1_critic)
            q2, h_c2_critic = self.critic.q2(obs[:, t], actions[:, t], h_c2_critic)
            critic_losses.append(F.mse_loss(q1, y) + F.mse_loss(q2, y))

        critic_loss = torch.stack(critic_losses).mean()
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        actor_loss_value: float | None = None
        # Policy-delayed actor update + target Polyak (identical to base).
        if self._update_count % self.policy_delay == 0:
            h_c1_actor = h_c1
            h_a_actor = h_a
            actor_qs: list[torch.Tensor] = []
            for t in range(self.burn_in, self.burn_in + self.seq_len):
                a_new, h_a_actor = self.actor(obs[:, t], h_a_actor)
                q1_new, h_c1_actor = self.critic.q1(obs[:, t], a_new, h_c1_actor)
                actor_qs.append(q1_new)
            actor_loss = -torch.stack(actor_qs).mean()
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            actor_loss_value = float(actor_loss.detach().cpu())

            with torch.no_grad():
                for p, p_tgt in zip(self.actor.parameters(), self.actor_target.parameters()):
                    p_tgt.data.copy_(self.tau * p.data + (1 - self.tau) * p_tgt.data)
                for p, p_tgt in zip(self.critic.parameters(), self.critic_target.parameters()):
                    p_tgt.data.copy_(self.tau * p.data + (1 - self.tau) * p_tgt.data)

        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss":  actor_loss_value,
        }
