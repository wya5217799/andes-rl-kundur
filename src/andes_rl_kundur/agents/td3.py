"""TD3 (Twin Delayed DDPG) — alternative to SAC for the V4 env.

Architectural relationship to SAC:
- Same actor / critic / target / replay scaffold (inherited from
  :class:`_SACBase`).
- Twin Q critics (same DoubleQCritic).
- **No entropy regularization**: actor minimises -Q(s, a) directly.
- **Deterministic action** at execution (mean of GaussianActor output);
  Gaussian noise added only for exploration at training time.
- **Target policy smoothing**: clipped noise added to target action
  before computing the Bellman target.
- **Delayed policy updates**: actor and target networks update every
  ``policy_delay`` critic steps.

Research hypothesis (CLM-0012, CLM-0014 follow-up): SAC's entropy bonus
pulls the actor toward near-zero action and produces the 0.137
multi-seed attractor on V4 env. TD3 has no such pull; this code lets
us test the hypothesis with a minimal swap (``--algo td3``) in train.py.
"""
from __future__ import annotations

import copy
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import DoubleQCritic
from andes_rl_kundur.agents.sac_base import _SACBase


class TD3Agent(_SACBase):
    """Deterministic-policy actor with twin critics + delayed updates."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 10000,
        batch_size: int = 256,
        device: str = "cpu",
        policy_noise: float = 0.2,
        noise_clip: float = 0.5,
        explore_noise: float = 0.1,
        policy_delay: int = 2,
    ) -> None:
        super().__init__(
            obs_dim=obs_dim, action_dim=action_dim,
            hidden_sizes=hidden_sizes, lr=lr,
            buffer_size=buffer_size, batch_size=batch_size,
            device=device,
        )
        # Disable the _SACBase entropy optimizer — TD3 doesn't tune alpha
        # but the field is still on the object for memory layout parity.
        self.log_alpha.requires_grad_(False)

        self.gamma = gamma
        self.tau = tau
        self.policy_noise = policy_noise
        self.noise_clip = noise_clip
        self.explore_noise = explore_noise
        self.policy_delay = policy_delay
        self._update_count = 0

        # Target actor (TD3-specific; SAC doesn't have one)
        self.actor_target = copy.deepcopy(self.actor).to(device)
        for p in self.actor_target.parameters():
            p.requires_grad = False

        # Twin Q critics (same architecture as SAC)
        self.critic = DoubleQCritic(obs_dim, action_dim, hidden_sizes).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)
        for p in self.critic_target.parameters():
            p.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

    def select_action(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        """Deterministic policy + optional Gaussian exploration noise.

        Overrides :py:meth:`_SACBase.select_action` (SAC samples from a
        Gaussian distribution; TD3 takes the mean and adds noise
        externally only when ``deterministic=False``).
        """
        obs_t = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        with torch.no_grad():
            action = self.actor.deterministic(obs_t)
        action_np = action.cpu().numpy().flatten()
        if not deterministic:
            noise = np.random.normal(0.0, self.explore_noise, size=action_np.shape)
            action_np = np.clip(action_np + noise, -1.0, 1.0)
        return action_np.astype(np.float32)

    def update(self) -> dict[str, Any] | None:
        """TD3 update step.

        Always updates the twin critics. Updates the actor + target nets
        only every ``policy_delay`` steps (the "delayed" in TD3).
        Adds clipped noise to the target action before computing the
        Bellman target (the "target policy smoothing" trick).
        """
        if len(self.buffer) < self.batch_size:
            return None

        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        obs = batch["obs"]
        actions = batch["actions"]
        rewards = batch["rewards"]
        next_obs = batch["next_obs"]
        dones = batch["dones"]

        # ─── Twin-critic update ──────────────────────────────────────
        with torch.no_grad():
            # Target policy smoothing: clipped Gaussian noise on target action
            noise = (
                torch.randn_like(actions) * self.policy_noise
            ).clamp(-self.noise_clip, self.noise_clip)
            next_actions = (
                self.actor_target.deterministic(next_obs) + noise
            ).clamp(-1.0, 1.0)
            q1_target, q2_target = self.critic_target(next_obs, next_actions)
            q_target = torch.min(q1_target, q2_target)
            y = rewards + self.gamma * (1.0 - dones) * q_target

        q1, q2 = self.critic(obs, actions)
        critic_loss = F.mse_loss(q1, y) + F.mse_loss(q2, y)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        loss_info: dict[str, Any] = {"critic_loss": critic_loss.item()}

        # ─── Delayed actor + target update ──────────────────────────
        if self._update_count % self.policy_delay == 0:
            new_actions = self.actor.deterministic(obs)
            q1_new, _ = self.critic(obs, new_actions)
            actor_loss = -q1_new.mean()

            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            loss_info["actor_loss"] = actor_loss.item()

            # Soft-update both target networks
            for p, p_tgt in zip(self.actor.parameters(), self.actor_target.parameters()):
                p_tgt.data.mul_(1.0 - self.tau).add_(self.tau * p.data)
            for p, p_tgt in zip(self.critic.parameters(), self.critic_target.parameters()):
                p_tgt.data.mul_(1.0 - self.tau).add_(self.tau * p.data)

        return loss_info

    # ─── Persistence ───────────────────────────────────────────────

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
                "algo": "td3",
            },
            path,
        )
        if save_buffer:
            self.buffer.save(str(path).replace(".pt", "_buffer.npz"))

    def load(self, path: str) -> dict:
        ckpt = torch.load(path, map_location=self.device, weights_only=True)
        self.actor.load_state_dict(ckpt["actor"])
        if "actor_target" in ckpt:
            self.actor_target.load_state_dict(ckpt["actor_target"])
        if "critic" in ckpt:
            self.critic.load_state_dict(ckpt["critic"])
            self.critic_target.load_state_dict(ckpt["critic_target"])
            self.critic_optimizer.load_state_dict(ckpt["critic_opt"])
        self.actor_optimizer.load_state_dict(ckpt["actor_opt"])
        return ckpt.get("metadata", {})
