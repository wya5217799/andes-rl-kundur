"""Size-matched centralized scalar TD3 ablation for R279.

The actor consumes the same 28-value joint observation available to the R278
central critic and emits the same single environment coordinate ``q``. Its
55-55 MLP has 4,731 parameters versus 4,737 in the R278 shared 7-64-64-1
actor, isolating the multi-agent factorization rather than model capacity.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn, optim

from andes_rl_kundur.agents.networks import build_mlp
from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3
from andes_rl_kundur.control.area_inertia_residual import (
    AREA_PATTERN,
    q_from_signed_residual_observation,
)


class CentralDeterministicActor(nn.Module):
    """One direct joint-observation-to-scalar deterministic actor."""

    def __init__(
        self,
        joint_obs_dim: int = 28,
        hidden_sizes: list[int] | None = None,
    ) -> None:
        super().__init__()
        self.hidden_sizes = list(hidden_sizes or [55, 55])
        self.net = build_mlp(joint_obs_dim, self.hidden_sizes, 1)

    def forward(self, joint_obs: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.net(joint_obs))


class CentralScalarTD3(SharedAreaTD3):
    """TD3 with one size-matched centralized scalar actor."""

    algo_name = "central_scalar_td3"

    def __init__(
        self,
        *,
        obs_dim: int = 7,
        agent_count: int = 4,
        critic_hidden_sizes: list[int] | None = None,
        actor_hidden_sizes: list[int] | None = None,
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
        super().__init__(
            obs_dim=obs_dim,
            agent_count=agent_count,
            hidden_sizes=list(critic_hidden_sizes or [64, 64]),
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
        )
        self.actor_hidden_sizes = list(actor_hidden_sizes or [55, 55])
        self.actor = CentralDeterministicActor(
            self.joint_obs_dim,
            self.actor_hidden_sizes,
        ).to(self.device)
        self.actor_target = copy.deepcopy(self.actor).to(self.device)
        for parameter in self.actor_target.parameters():
            parameter.requires_grad = False
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

    @property
    def actor_parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.actor.parameters())

    def _project_actor(
        self,
        joint_obs: torch.Tensor,
        actor: CentralDeterministicActor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        agent_obs = self._agent_obs(joint_obs)
        raw_scalar = actor(joint_obs).reshape(-1)
        previous_q_normalized = q_from_signed_residual_observation(
            agent_obs[:, :, 4]
        )
        target_q = raw_scalar * self.contract.q_max
        previous_q = previous_q_normalized * self.contract.q_max
        q = torch.maximum(
            torch.minimum(target_q, previous_q + self.contract.q_slew_max),
            previous_q - self.contract.q_slew_max,
        ).clamp(-self.contract.q_max, self.contract.q_max)
        return raw_scalar.unsqueeze(-1), (q / self.contract.q_max).unsqueeze(-1)

    def select_raw_actions(
        self,
        observations: dict[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
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
        joint_obs = obs.reshape(1, self.joint_obs_dim)
        with torch.no_grad():
            target = float(
                self.actor(
                    torch.as_tensor(
                        joint_obs,
                        dtype=torch.float32,
                        device=self.device,
                    )
                ).cpu().item()
            )
        if not deterministic:
            generator = rng or np.random.default_rng()
            target += float(generator.normal(0.0, self.explore_noise))
        target = float(np.clip(target, -1.0, 1.0))
        return (AREA_PATTERN * np.float32(target)).astype(np.float32)

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
                "critic_hidden_sizes": self.hidden_sizes,
                "actor_hidden_sizes": self.actor_hidden_sizes,
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
        if list(payload["actor_hidden_sizes"]) != self.actor_hidden_sizes:
            raise ValueError("checkpoint central actor size mismatch")
        self.actor.load_state_dict(payload["actor"])
        self.actor_target.load_state_dict(payload["actor_target"])
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        self.actor_optimizer.load_state_dict(payload["actor_optimizer"])
        self.critic_optimizer.load_state_dict(payload["critic_optimizer"])
        self._update_count = int(payload.get("update_count", 0))
        self.actor_update_steps = int(payload.get("actor_update_steps", 0))
        return dict(payload.get("metadata", {}))
