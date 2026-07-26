"""R278 parameter-shared actor with a centralized TD3 critic.

One actor is evaluated independently on four local observations.  Its four
raw votes are reduced by the frozen two-area projector to one executed action
coordinate.  The critic therefore learns the actual scalar action seen by the
plant rather than four non-identifiable raw votes.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch import optim

from andes_rl_kundur.agents.networks import DoubleQCritic, build_mlp
from andes_rl_kundur.agents.replay_buffer import ReplayBuffer
from andes_rl_kundur.control.area_inertia_residual import (
    project_raw_to_q_torch,
    q_from_signed_residual_observation,
    r278_area_inertia_contract,
)


class SharedDeterministicActor(nn.Module):
    """One memoryless deterministic actor reused for every VSG."""

    def __init__(
        self,
        obs_dim: int,
        hidden_sizes: list[int],
    ) -> None:
        super().__init__()
        self.net = build_mlp(obs_dim, hidden_sizes, 1)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.net(obs))


class SharedAreaTD3:
    """Centralized-training coordinator for the frozen R278 action seam."""

    algo_name = "shared_area_td3"

    def __init__(
        self,
        *,
        obs_dim: int = 7,
        agent_count: int = 4,
        hidden_sizes: list[int] | None = None,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 100_000,
        batch_size: int = 256,
        device: str = "cpu",
        policy_noise: float = 0.1,
        noise_clip: float = 0.2,
        explore_noise: float = 0.1,
        policy_delay: int = 2,
    ) -> None:
        if agent_count != 4:
            raise ValueError("R278 requires exactly four agents")
        if obs_dim <= 4:
            raise ValueError("obs_dim must include the previous residual slot")
        self.obs_dim = int(obs_dim)
        self.agent_count = int(agent_count)
        self.joint_obs_dim = self.obs_dim * self.agent_count
        self.hidden_sizes = list(hidden_sizes or [64, 64])
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.batch_size = int(batch_size)
        self.device = str(device)
        self.policy_noise = float(policy_noise)
        self.noise_clip = float(noise_clip)
        self.explore_noise = float(explore_noise)
        self.policy_delay = int(policy_delay)
        self.max_grad_norm = 10.0
        self._update_count = 0
        self.actor_update_steps = 0

        self.actor = SharedDeterministicActor(
            self.obs_dim,
            self.hidden_sizes,
        ).to(self.device)
        self.actor_target = copy.deepcopy(self.actor).to(self.device)
        for parameter in self.actor_target.parameters():
            parameter.requires_grad = False
        self.critic = DoubleQCritic(
            self.joint_obs_dim,
            1,
            self.hidden_sizes,
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        for parameter in self.critic_target.parameters():
            parameter.requires_grad = False

        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        self.buffer = ReplayBuffer(
            self.joint_obs_dim,
            1,
            capacity=buffer_size,
        )
        self.contract = r278_area_inertia_contract()

    def _agent_obs(self, joint_obs: torch.Tensor) -> torch.Tensor:
        if joint_obs.shape[-1] != self.joint_obs_dim:
            raise ValueError(
                f"expected joint obs dim {self.joint_obs_dim}, "
                f"got {joint_obs.shape[-1]}"
            )
        return joint_obs.reshape(-1, self.agent_count, self.obs_dim)

    def _project_actor(
        self,
        joint_obs: torch.Tensor,
        actor: SharedDeterministicActor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        agent_obs = self._agent_obs(joint_obs)
        flat = agent_obs.reshape(-1, self.obs_dim)
        raw = actor(flat).reshape(-1, self.agent_count)
        previous_q_normalized = q_from_signed_residual_observation(
            agent_obs[:, :, 4]
        )
        q, _residual = project_raw_to_q_torch(
            raw,
            previous_q=previous_q_normalized * self.contract.q_max,
            contract=self.contract,
        )
        return raw, (q / self.contract.q_max).unsqueeze(-1)

    def select_raw_actions(
        self,
        observations: dict[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Evaluate the one shared actor on all four local observations."""
        if isinstance(observations, dict):
            obs = np.stack(
                [np.asarray(observations[index], dtype=np.float32) for index in range(4)]
            )
        else:
            obs = np.asarray(observations, dtype=np.float32)
        if obs.shape != (self.agent_count, self.obs_dim):
            raise ValueError(
                f"observations must have shape {(self.agent_count, self.obs_dim)}, "
                f"got {obs.shape}"
            )
        with torch.no_grad():
            raw = self.actor(
                torch.as_tensor(obs, dtype=torch.float32, device=self.device)
            ).cpu().numpy().reshape(self.agent_count)
        if not deterministic:
            generator = rng or np.random.default_rng()
            raw = raw + generator.normal(
                0.0,
                self.explore_noise,
                size=raw.shape,
            )
        return np.clip(raw, -1.0, 1.0).astype(np.float32)

    def store(
        self,
        observation: np.ndarray,
        q_normalized: float,
        reward: float,
        next_observation: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.add(
            np.asarray(observation, dtype=np.float32).reshape(self.joint_obs_dim),
            np.asarray([q_normalized], dtype=np.float32),
            float(reward),
            np.asarray(next_observation, dtype=np.float32).reshape(
                self.joint_obs_dim
            ),
            bool(done),
        )

    def update(self) -> dict[str, float] | None:
        if len(self.buffer) < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        obs = batch["obs"]
        action = batch["actions"]
        reward = batch["rewards"]
        next_obs = batch["next_obs"]
        done = batch["dones"]

        with torch.no_grad():
            _next_raw, next_action = self._project_actor(
                next_obs,
                self.actor_target,
            )
            noise = (
                torch.randn_like(next_action) * self.policy_noise
            ).clamp(-self.noise_clip, self.noise_clip)
            next_action = (next_action + noise).clamp(-1.0, 1.0)
            q1_target, q2_target = self.critic_target(
                next_obs,
                next_action,
            )
            target = reward + self.gamma * (1.0 - done) * torch.min(
                q1_target,
                q2_target,
            )

        q1, q2 = self.critic(obs, action)
        critic_loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(
            self.critic.parameters(),
            self.max_grad_norm,
        )
        self.critic_optimizer.step()
        losses = {"critic_loss": float(critic_loss.item())}

        if self._update_count % self.policy_delay == 0:
            _raw, projected_action = self._project_actor(obs, self.actor)
            actor_loss = -self.critic.q1(obs, projected_action).mean()
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.actor.parameters(),
                self.max_grad_norm,
            )
            self.actor_optimizer.step()
            self.actor_update_steps += 1
            losses["actor_loss"] = float(actor_loss.item())

            for parameter, target_parameter in zip(
                self.actor.parameters(),
                self.actor_target.parameters(),
                strict=True,
            ):
                target_parameter.data.mul_(1.0 - self.tau).add_(
                    self.tau * parameter.data
                )
            for parameter, target_parameter in zip(
                self.critic.parameters(),
                self.critic_target.parameters(),
                strict=True,
            ):
                target_parameter.data.mul_(1.0 - self.tau).add_(
                    self.tau * parameter.data
                )
        return losses

    def save(
        self,
        path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        torch.save(
            {
                "algo": self.algo_name,
                "obs_dim": self.obs_dim,
                "agent_count": self.agent_count,
                "hidden_sizes": self.hidden_sizes,
                "actor": self.actor.state_dict(),
                "actor_target": self.actor_target.state_dict(),
                "critic": self.critic.state_dict(),
                "critic_target": self.critic_target.state_dict(),
                "actor_optimizer": self.actor_optimizer.state_dict(),
                "critic_optimizer": self.critic_optimizer.state_dict(),
                "update_count": self._update_count,
                "actor_update_steps": self.actor_update_steps,
                "metadata": metadata or {},
            },
            str(path),
        )

    def load(self, path: str | Path) -> dict[str, Any]:
        payload = torch.load(
            str(path),
            map_location=self.device,
            weights_only=True,
        )
        if payload.get("algo") != self.algo_name:
            raise ValueError(f"incompatible checkpoint algo: {payload.get('algo')}")
        if int(payload["obs_dim"]) != self.obs_dim:
            raise ValueError("checkpoint observation dimension mismatch")
        self.actor.load_state_dict(payload["actor"])
        self.actor_target.load_state_dict(payload["actor_target"])
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        self.actor_optimizer.load_state_dict(payload["actor_optimizer"])
        self.critic_optimizer.load_state_dict(payload["critic_optimizer"])
        self._update_count = int(payload.get("update_count", 0))
        self.actor_update_steps = int(payload.get("actor_update_steps", 0))
        return dict(payload.get("metadata", {}))
