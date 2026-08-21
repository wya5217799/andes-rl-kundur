"""SAC seam whose Bellman action is the statefully executed action.

The actuator applies an amplitude bound followed by a per-step slew bound.  That
makes the previous executed action part of the Markov state.  This module keeps
the raw policy action for diagnostics, but replay and every critic path use the
executed action.  The entropy term remains a raw tanh-policy regularizer; this
module deliberately makes no executed-action density claim.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import DoubleQCritic, GaussianActor


ENTROPY_SEMANTICS = "raw_policy_entropy_regularizer"


def project_action_numpy(
    previous_executed_action: np.ndarray,
    raw_action: np.ndarray,
    *,
    slew_limit: float,
) -> np.ndarray:
    """Apply amplitude then slew limits with conservative float32 recording."""

    previous = np.asarray(previous_executed_action, dtype=np.float32)
    raw = np.asarray(raw_action, dtype=np.float32)
    if previous.shape != raw.shape or previous.ndim < 1:
        raise ValueError("previous and raw actions must have the same non-scalar shape")
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(raw)):
        raise ValueError("actions must be finite")
    limit = float(slew_limit)
    if not np.isfinite(limit) or not 0.0 < limit <= 2.0:
        raise ValueError("slew_limit must lie in (0, 2]")

    amplitude = np.clip(raw, -1.0, 1.0).astype(np.float32)
    previous64 = previous.astype(np.float64)
    delta64 = np.clip(
        amplitude.astype(np.float64) - previous64,
        -limit,
        limit,
    )
    executed = np.clip(previous64 + delta64, -1.0, 1.0).astype(np.float32)
    overshoot = executed.astype(np.float64) - previous64 > limit
    undershoot = executed.astype(np.float64) - previous64 < -limit
    if np.any(overshoot):
        executed[overshoot] = np.nextafter(
            executed[overshoot], np.float32(-np.inf)
        )
    if np.any(undershoot):
        executed[undershoot] = np.nextafter(
            executed[undershoot], np.float32(np.inf)
        )
    return np.clip(executed, -1.0, 1.0).astype(np.float32)


def project_action_torch(
    previous_executed_action: torch.Tensor,
    raw_action: torch.Tensor,
    *,
    slew_limit: float,
) -> torch.Tensor:
    """Differentiable amplitude/slew projection used by actor and target paths."""

    if previous_executed_action.shape != raw_action.shape:
        raise ValueError("previous and raw actions must have the same shape")
    limit = float(slew_limit)
    if not math.isfinite(limit) or not 0.0 < limit <= 2.0:
        raise ValueError("slew_limit must lie in (0, 2]")
    amplitude = torch.clamp(raw_action, -1.0, 1.0)
    delta = torch.clamp(amplitude - previous_executed_action, -limit, limit)
    return torch.clamp(previous_executed_action + delta, -1.0, 1.0)


def augment_state_numpy(obs: np.ndarray, previous: np.ndarray) -> np.ndarray:
    obs_array = np.asarray(obs, dtype=np.float32)
    previous_array = np.asarray(previous, dtype=np.float32)
    return np.concatenate([obs_array, previous_array], axis=-1).astype(np.float32)


def augment_state_torch(obs: torch.Tensor, previous: torch.Tensor) -> torch.Tensor:
    return torch.cat([obs, previous], dim=-1)


class ExecutedActionReplayBuffer:
    """Ring buffer preserving both policy output and physical Bellman action."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        capacity: int = 10_000,
    ) -> None:
        self.capacity = int(capacity)
        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.previous_executed_actions = np.zeros(
            (capacity, action_dim), dtype=np.float32
        )
        self.raw_actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.executed_actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.rewards = np.zeros((capacity, 1), dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.dones = np.zeros((capacity, 1), dtype=np.float32)
        self.size = 0
        self._ptr = 0

    def add(
        self,
        obs: np.ndarray,
        previous_executed_action: np.ndarray,
        raw_action: np.ndarray,
        executed_action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        index = self._ptr
        self.obs[index] = obs
        self.previous_executed_actions[index] = previous_executed_action
        self.raw_actions[index] = raw_action
        self.executed_actions[index] = executed_action
        self.rewards[index] = float(reward)
        self.next_obs[index] = next_obs
        self.dones[index] = float(done)
        self._ptr = (index + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(
        self,
        batch_size: int,
        device: str | torch.device,
        *,
        indices: np.ndarray | None = None,
    ) -> dict[str, torch.Tensor]:
        if self.size <= 0:
            raise ValueError("cannot sample an empty replay buffer")
        if indices is None:
            indices = np.random.randint(0, self.size, size=int(batch_size))
        else:
            indices = np.asarray(indices, dtype=np.int64)

        def tensor(array: np.ndarray) -> torch.Tensor:
            return torch.from_numpy(array[indices]).to(device)

        return {
            "obs": tensor(self.obs),
            "previous_executed_actions": tensor(self.previous_executed_actions),
            "raw_actions": tensor(self.raw_actions),
            "executed_actions": tensor(self.executed_actions),
            "rewards": tensor(self.rewards),
            "next_obs": tensor(self.next_obs),
            "dones": tensor(self.dones),
        }

    def save(self, path: str | Path) -> None:
        np.savez_compressed(
            path,
            obs=self.obs[: self.size],
            previous_executed_actions=self.previous_executed_actions[: self.size],
            raw_actions=self.raw_actions[: self.size],
            executed_actions=self.executed_actions[: self.size],
            rewards=self.rewards[: self.size],
            next_obs=self.next_obs[: self.size],
            dones=self.dones[: self.size],
        )

    def __len__(self) -> int:
        return self.size


class ExecutedActionSACAgent:
    """Per-agent SAC with an augmented actuator state and executed-action Q."""

    algo_name = "executed_action_sac"
    entropy_semantics = ENTROPY_SEMANTICS

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_sizes: list[int],
        *,
        slew_limit: float,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 10_000,
        batch_size: int = 256,
        device: str = "cpu",
        alpha_min: float = 0.005,
        alpha_max: float = 5.0,
    ) -> None:
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.state_dim = self.obs_dim + self.action_dim
        self.slew_limit = float(slew_limit)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.batch_size = int(batch_size)
        self.device = torch.device(device)

        self.actor = GaussianActor(
            self.state_dim, self.action_dim, hidden_sizes
        ).to(self.device)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic = DoubleQCritic(
            self.state_dim, self.action_dim, hidden_sizes
        ).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        for parameter in self.critic_target.parameters():
            parameter.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)

        self.target_entropy = -float(self.action_dim)
        self.log_alpha = torch.zeros(1, requires_grad=True, device=self.device)
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=lr)
        self._log_alpha_min = math.log(float(alpha_min))
        self._log_alpha_max = math.log(float(alpha_max))
        self.buffer = ExecutedActionReplayBuffer(
            self.obs_dim, self.action_dim, capacity=buffer_size
        )
        self.max_grad_norm = 1.0

    @property
    def alpha(self) -> torch.Tensor:
        return self.log_alpha.exp()

    def select_raw_action(
        self,
        obs: np.ndarray,
        previous_executed_action: np.ndarray,
        *,
        deterministic: bool = False,
    ) -> np.ndarray:
        state = augment_state_numpy(obs, previous_executed_action)
        state_tensor = torch.from_numpy(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            if deterministic:
                raw = self.actor.deterministic(state_tensor)
            else:
                raw, _ = self.actor.sample(state_tensor)
        return raw.squeeze(0).cpu().numpy().astype(np.float32)

    def execute_action(
        self,
        previous_executed_action: np.ndarray,
        raw_action: np.ndarray,
    ) -> np.ndarray:
        return project_action_numpy(
            previous_executed_action, raw_action, slew_limit=self.slew_limit
        )

    def store_transition(
        self,
        obs: np.ndarray,
        previous_executed_action: np.ndarray,
        raw_action: np.ndarray,
        executed_action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        expected = self.execute_action(previous_executed_action, raw_action)
        actual = np.asarray(executed_action, dtype=np.float32)
        if not np.allclose(expected, actual, rtol=0.0, atol=1.0e-7):
            raise ValueError("executed action does not match the frozen projector")
        self.buffer.add(
            obs,
            previous_executed_action,
            raw_action,
            actual,
            reward,
            next_obs,
            done,
        )

    def loss_inputs(
        self,
        batch: dict[str, torch.Tensor],
        *,
        deterministic_target: bool = False,
    ) -> dict[str, torch.Tensor]:
        """Return the action/state tensors used by every Bellman path."""

        obs = batch["obs"]
        previous = batch["previous_executed_actions"]
        executed = batch["executed_actions"]
        state = augment_state_torch(obs, previous)
        next_state = augment_state_torch(batch["next_obs"], executed)
        with torch.no_grad():
            if deterministic_target:
                target_raw = self.actor.deterministic(next_state)
                target_log_prob = torch.zeros(
                    (next_state.shape[0], 1),
                    dtype=next_state.dtype,
                    device=next_state.device,
                )
            else:
                target_raw, target_log_prob = self.actor.sample(next_state)
            target_executed = project_action_torch(
                executed, target_raw, slew_limit=self.slew_limit
            )
            q1_target, q2_target = self.critic_target(
                next_state, target_executed
            )
            target_min = torch.minimum(q1_target, q2_target)
            td_target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * (target_min - self.alpha * target_log_prob)

        actor_raw, actor_log_prob = self.actor.sample(state)
        actor_executed = project_action_torch(
            previous, actor_raw, slew_limit=self.slew_limit
        )
        return {
            "state": state,
            "next_state": next_state,
            "critic_current_action_input": executed,
            "target_actor_raw_action": target_raw,
            "target_projected_action": target_executed,
            "critic_target_action_input": target_executed,
            "q1_target": q1_target,
            "q2_target": q2_target,
            "td_target": td_target,
            "actor_raw_action": actor_raw,
            "actor_projected_action": actor_executed,
            "actor_critic_action_input": actor_executed,
            "actor_log_prob": actor_log_prob,
        }

    def update(self) -> dict[str, float] | None:
        if len(self.buffer) < self.batch_size:
            return None
        batch = self.buffer.sample(self.batch_size, self.device)
        paths = self.loss_inputs(batch)

        q1, q2 = self.critic(
            paths["state"], paths["critic_current_action_input"]
        )
        critic_loss = F.mse_loss(q1, paths["td_target"]) + F.mse_loss(
            q2, paths["td_target"]
        )
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        q1_actor, q2_actor = self.critic(
            paths["state"], paths["actor_critic_action_input"]
        )
        actor_q = torch.minimum(q1_actor, q2_actor)
        actor_loss = (
            self.alpha.detach() * paths["actor_log_prob"] - actor_q
        ).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
        self.actor_optimizer.step()

        alpha_loss = -(
            self.log_alpha
            * (paths["actor_log_prob"].detach() + self.target_entropy)
        ).mean()
        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        self.alpha_optimizer.step()
        with torch.no_grad():
            self.log_alpha.clamp_(self._log_alpha_min, self._log_alpha_max)
            for source, target in zip(
                self.critic.parameters(), self.critic_target.parameters(), strict=True
            ):
                target.mul_(1.0 - self.tau).add_(source, alpha=self.tau)

        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss": float(actor_loss.detach().cpu()),
            "alpha_loss": float(alpha_loss.detach().cpu()),
            "alpha": float(self.alpha.detach().cpu()),
        }

    def save(self, path: str | Path) -> None:
        torch.save(
            {
                "schema_version": 1,
                "kind": "executed-action-sac",
                "obs_dim": self.obs_dim,
                "action_dim": self.action_dim,
                "slew_limit": self.slew_limit,
                "entropy_semantics": self.entropy_semantics,
                "actor": self.actor.state_dict(),
                "critic": self.critic.state_dict(),
                "critic_target": self.critic_target.state_dict(),
                "log_alpha": self.log_alpha.detach().cpu(),
            },
            str(path),
        )

    def load(self, path: str | Path) -> dict[str, Any]:
        payload = torch.load(str(path), map_location=self.device, weights_only=True)
        if payload.get("kind") != "executed-action-sac":
            raise ValueError("not an executed-action SAC checkpoint")
        if int(payload["obs_dim"]) != self.obs_dim:
            raise ValueError("checkpoint observation dimension mismatch")
        if int(payload["action_dim"]) != self.action_dim:
            raise ValueError("checkpoint action dimension mismatch")
        if not math.isclose(float(payload["slew_limit"]), self.slew_limit):
            raise ValueError("checkpoint slew limit mismatch")
        self.actor.load_state_dict(payload["actor"])
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        self.log_alpha.data = payload["log_alpha"].to(self.device)
        return payload
