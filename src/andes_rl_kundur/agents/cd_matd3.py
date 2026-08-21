"""Memoryless common--differential mode-aware multi-agent TD3 (CD-MATD3).

Implements the frozen R401 Gate A learner contract: four independently
executed deterministic actors (7-slot rows -> 2 tanh outputs), one twin
joint critic over the concatenated 4x7 observations and 4x2 actions, and
the two-component common/differential value pair with a Lagrangian
multiplier enforcing the frozen per-episode common budget.  The no-message
arm masks neighbour slots inside every online-actor and target-actor forward;
critic storage may still keep the full joint rows for centralized training.
No ANDES import: this module is pure and testable offline.  Historical
checkpoints are never loaded here.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from andes_rl_kundur.agents.networks import build_mlp

OBS_DIM = 7
ACTION_DIM = 2
AGENT_COUNT = 4
JOINT_OBS_DIM = AGENT_COUNT * OBS_DIM
JOINT_ACTION_DIM = AGENT_COUNT * ACTION_DIM
JOINT_INPUT_DIM = JOINT_OBS_DIM + JOINT_ACTION_DIM

NEIGHBOUR_SLOTS = (3, 4, 5, 6)


class DeterministicMDActor(nn.Module):
    """One per-VSG actor: 7-slot observation row to a 2-dim tanh action."""

    def __init__(self, hidden_sizes: list[int]) -> None:
        super().__init__()
        self.net = build_mlp(OBS_DIM, list(hidden_sizes), ACTION_DIM)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.net(obs))


class TwinJointCritic(nn.Module):
    """Two independent joint critics, each mapping (obs, actions) to the
    registered value components (2 for CD-MATD3, 1 for the scalar TD3)."""

    def __init__(self, hidden_sizes: list[int], out_dim: int) -> None:
        super().__init__()
        self.q1 = build_mlp(JOINT_INPUT_DIM, list(hidden_sizes), out_dim)
        self.q2 = build_mlp(JOINT_INPUT_DIM, list(hidden_sizes), out_dim)

    def forward(
        self, obs: torch.Tensor, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        x = torch.cat([obs, actions], dim=-1)
        return self.q1(x), self.q2(x)


class _ReplayRing:
    """Fixed-capacity numpy ring storing two reward channels."""

    def __init__(self, capacity: int, reward_dim: int) -> None:
        self.capacity = int(capacity)
        self.reward_dim = int(reward_dim)
        self.obs = np.zeros((capacity, JOINT_OBS_DIM), dtype=np.float32)
        self.actions = np.zeros((capacity, JOINT_ACTION_DIM), dtype=np.float32)
        self.rewards = np.zeros((capacity, reward_dim), dtype=np.float32)
        self.next_obs = np.zeros((capacity, JOINT_OBS_DIM), dtype=np.float32)
        self.dones = np.zeros((capacity, 1), dtype=np.float32)
        self.size = 0
        self._ptr = 0

    def add(
        self,
        obs: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.obs[self._ptr] = obs
        self.actions[self._ptr] = actions
        self.rewards[self._ptr] = rewards
        self.next_obs[self._ptr] = next_obs
        self.dones[self._ptr] = float(done)
        self._ptr = (self._ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, device: torch.device) -> dict[str, torch.Tensor]:
        idx = np.random.randint(0, self.size, size=batch_size)
        return {
            "obs": torch.FloatTensor(self.obs[idx]).to(device),
            "actions": torch.FloatTensor(self.actions[idx]).to(device),
            "rewards": torch.FloatTensor(self.rewards[idx]).to(device),
            "next_obs": torch.FloatTensor(self.next_obs[idx]).to(device),
            "dones": torch.FloatTensor(self.dones[idx]).to(device),
        }


class _JointTD3Base:
    """Shared scaffold: actors, twin joint critic, ring buffer, save/load."""

    def __init__(
        self,
        out_dim: int,
        hidden_sizes: list[int] | None = None,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 200000,
        batch_size: int = 256,
        policy_noise: float = 0.2,
        noise_clip: float = 0.5,
        explore_noise: float = 0.1,
        policy_delay: int = 2,
        device: str = "cpu",
        actor_neighbour_mask: bool = False,
    ) -> None:
        hidden = list(hidden_sizes or [256, 256])
        self.out_dim = int(out_dim)
        self.device = torch.device(device)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.batch_size = int(batch_size)
        self.policy_noise = float(policy_noise)
        self.noise_clip = float(noise_clip)
        self.explore_noise = float(explore_noise)
        self.policy_delay = int(policy_delay)
        self.actor_neighbour_mask = bool(actor_neighbour_mask)
        self.actors = nn.ModuleList(
            [DeterministicMDActor(hidden) for _ in range(AGENT_COUNT)]
        ).to(self.device)
        self.actor_targets = copy.deepcopy(self.actors).to(self.device)
        for parameters in self.actor_targets.parameters():
            parameters.requires_grad = False
        self.actor_optimizers = [
            optim.Adam(actor.parameters(), lr=lr) for actor in self.actors
        ]
        self.critic = TwinJointCritic(hidden, self.out_dim).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        for parameters in self.critic_target.parameters():
            parameters.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        self.buffer = _ReplayRing(buffer_size, self.out_dim)
        self._update_count = 0

    @property
    def lagrange(self) -> float:
        return float(getattr(self, "_lagrange", 0.0))

    def lagrange_step(
        self,
        episode_common_cost: float,
        budget: float,
        step: float,
        maximum: float,
    ) -> float:
        """Apply the frozen dual update after one episode."""

        updated = self.lagrange + float(step) * (
            float(episode_common_cost) - float(budget)
        )
        self._lagrange = float(np.clip(updated, 0.0, float(maximum)))
        return self.lagrange

    def store(
        self,
        obs: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.add(obs, actions, rewards, next_obs, done)

    def _actor_obs_row(
        self, joint_obs: torch.Tensor, actor_index: int
    ) -> torch.Tensor:
        """Return one actor row under the arm's execution information pattern."""

        start = actor_index * OBS_DIM
        row = joint_obs[:, start:start + OBS_DIM]
        if self.actor_neighbour_mask:
            row = row.clone()
            row[:, list(NEIGHBOUR_SLOTS)] = 0.0
        return row

    def act(
        self,
        actor_obs_joint: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        """Return the four-row joint action under the configured actor mask."""

        rows = np.asarray(actor_obs_joint, dtype=np.float32).reshape(
            AGENT_COUNT, OBS_DIM
        )
        if self.actor_neighbour_mask:
            rows = rows.copy()
            rows[:, list(NEIGHBOUR_SLOTS)] = 0.0
        actions = np.zeros((AGENT_COUNT, ACTION_DIM), dtype=np.float32)
        with torch.no_grad():
            for actor_index, actor in enumerate(self.actors):
                row = torch.FloatTensor(rows[actor_index]).unsqueeze(0).to(
                    self.device
                )
                action = actor(row).cpu().numpy().flatten()
                if not deterministic:
                    noise = np.random.normal(
                        0.0, self.explore_noise, size=action.shape
                    )
                    action = action + noise
                actions[actor_index] = action
        return np.clip(actions, -1.0, 1.0).astype(np.float32)

    def _target_actions(
        self, next_obs: torch.Tensor
    ) -> torch.Tensor:
        rows = [
            self.actor_targets[i](self._actor_obs_row(next_obs, i))
            for i in range(AGENT_COUNT)
        ]
        target = torch.cat(rows, dim=-1)
        noise = (
            torch.randn_like(target) * self.policy_noise
        ).clamp(-self.noise_clip, self.noise_clip)
        return (target + noise).clamp(-1.0, 1.0)

    def _critic_update(
        self, batch: Mapping[str, torch.Tensor]
    ) -> torch.Tensor:
        with torch.no_grad():
            next_actions = self._target_actions(batch["next_obs"])
            q1_next, q2_next = self.critic_target(
                batch["next_obs"], next_actions
            )
            q_next = torch.min(q1_next, q2_next)
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        loss.backward()
        self.critic_optimizer.step()
        return loss.detach()

    def _actor_objective(
        self,
        obs: torch.Tensor,
        actor_index: int,
        action_row: torch.Tensor,
        baseline_actions: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Value of the joint action with actor i replaced by action_row."""

        if baseline_actions is not None:
            joint = baseline_actions.clone()
            joint[:, actor_index * ACTION_DIM:(actor_index + 1) * ACTION_DIM] = (
                action_row
            )
        else:
            joint = action_row
        q1, _ = self.critic(obs, joint)
        return q1

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": 1,
            "out_dim": self.out_dim,
            "lagrange": self.lagrange,
            "actors": {
                str(i): actor.state_dict() for i, actor in enumerate(self.actors)
            },
            "critic": self.critic.state_dict(),
            "critic_target": self.critic_target.state_dict(),
            "actor_targets": {
                str(i): target.state_dict()
                for i, target in enumerate(self.actor_targets)
            },
        }
        torch.save(payload, str(path))

    def load(self, path: str | Path) -> None:
        payload = torch.load(str(path), map_location=self.device)
        if payload.get("schema_version") != 1 or payload.get("out_dim") != self.out_dim:
            raise ValueError("incompatible checkpoint payload")
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        for index, actor in enumerate(self.actors):
            actor.load_state_dict(payload["actors"][str(index)])
            self.actor_targets[index].load_state_dict(
                payload["actor_targets"][str(index)]
            )
        self._lagrange = float(payload.get("lagrange", 0.0))


class CDMATD3(_JointTD3Base):
    """CD-MATD3: twin joint critics return (Q_common, Q_differential) and
    every actor minimizes -(Q_differential + lambda * Q_common)."""

    def __init__(self, lagrange_initial: float = 1.0, **kwargs: Any) -> None:
        super().__init__(out_dim=2, **kwargs)
        self._lagrange = float(lagrange_initial)

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        critic_loss = self._critic_update(batch)
        actor_loss_mean = float("nan")
        if self._update_count % self.policy_delay == 0:
            with torch.no_grad():
                baseline_rows = [
                    self.actors[i](self._actor_obs_row(batch["obs"], i))
                    for i in range(AGENT_COUNT)
                ]
                baseline = torch.cat(baseline_rows, dim=-1)
            losses = []
            for i, optimizer in enumerate(self.actor_optimizers):
                row = self.actors[i](
                    self._actor_obs_row(batch["obs"], i)
                )
                q1 = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss = -torch.mean(q1[:, 0] + self.lagrange * q1[:, 1])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            for target, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        return {
            "critic_loss": float(critic_loss.cpu()),
            "actor_loss_mean": actor_loss_mean,
            "lagrange": self.lagrange,
        }


class FixedWeightCDMATD3(CDMATD3):
    """R403 successor with a common-channel weight that cannot collapse.

    The historical :class:`CDMATD3` remains unchanged for the sealed R402
    bundle.  This successor deliberately keeps the same network and update
    path while making the common weight immutable by construction.
    """

    def __init__(self, common_weight: float = 1.0, **kwargs: Any) -> None:
        weight = float(common_weight)
        if not np.isfinite(weight) or weight < 0.0:
            raise ValueError("common_weight must be finite and non-negative")
        self.common_weight = weight
        super().__init__(lagrange_initial=weight, **kwargs)

    @property
    def lagrange(self) -> float:
        """Compatibility name consumed by the shared actor-update path."""

        return self.common_weight

    def lagrange_step(
        self,
        episode_common_cost: float,
        budget: float,
        step: float,
        maximum: float,
    ) -> float:
        """Keep the fixed weight unchanged if an old runner calls this seam."""

        del episode_common_cost, budget, step, maximum
        return self.common_weight

    def update(self) -> dict[str, float] | None:
        """Return finite diagnostics with explicit actor-update state."""

        diagnostics = super().update()
        if diagnostics is None:
            return None
        policy_updated = self._update_count % self.policy_delay == 0
        if not policy_updated:
            diagnostics["actor_loss_mean"] = 0.0
        diagnostics["policy_updated"] = float(policy_updated)
        return diagnostics


class YangScalarTD3(_JointTD3Base):
    """Fresh Yang-compatible scalar-reward TD3: same four actors, one twin
    joint scalar critic, actor minimizes -Q_common scalar value."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(out_dim=1, **kwargs)

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        critic_loss = self._critic_update(batch)
        actor_loss_mean = float("nan")
        if self._update_count % self.policy_delay == 0:
            with torch.no_grad():
                baseline_rows = [
                    self.actors[i](self._actor_obs_row(batch["obs"], i))
                    for i in range(AGENT_COUNT)
                ]
                baseline = torch.cat(baseline_rows, dim=-1)
            losses = []
            for i, optimizer in enumerate(self.actor_optimizers):
                row = self.actors[i](
                    self._actor_obs_row(batch["obs"], i)
                )
                q1 = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss = -torch.mean(q1[:, 0])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            for target, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        return {
            "critic_loss": float(critic_loss.cpu()),
            "actor_loss_mean": actor_loss_mean,
        }


def mask_neighbour_slots(joint_obs: np.ndarray) -> np.ndarray:
    """Zero neighbour slots 3..6 of every observation row (no-message arm)."""

    masked = np.asarray(joint_obs, dtype=np.float32).reshape(
        AGENT_COUNT, OBS_DIM
    ).copy()
    masked[:, NEIGHBOUR_SLOTS] = 0.0
    return masked.reshape(-1)


def physical_costs(
    frequencies_hz: np.ndarray,
    rocof_hz_s: np.ndarray,
    p_es: np.ndarray,
    contract: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    """Return per-step (differential, common) costs on the physical base."""

    reward = contract["reward_contract"]["cd_matd3"]
    sigma_f = float(reward["sigma_f_hz"])
    sigma_p = float(reward["sigma_p_pu"])
    sigma_rocof = float(reward["sigma_rocof_hz_s"])
    nominal = float(contract["physical_nominal_frequency_hz"])
    transform = np.asarray(contract["differential_transform"], dtype=float)
    deviation = np.asarray(frequencies_hz, dtype=float) - nominal
    z_d = deviation @ transform.T
    p_d = np.asarray(p_es, dtype=float) @ transform.T
    rocof = np.asarray(rocof_hz_s, dtype=float)
    differential = (
        np.sum((z_d / sigma_f) ** 2, axis=1) / 3.0
        + np.sum((p_d / sigma_p) ** 2, axis=1) / 3.0
    )
    common = (
        np.mean((deviation / sigma_f) ** 2, axis=1)
        + np.mean((rocof / sigma_rocof) ** 2, axis=1)
    )
    return differential.astype(float), common.astype(float)


def physical_costs_with_action_effort(
    frequencies_hz: np.ndarray,
    rocof_hz_s: np.ndarray,
    p_es: np.ndarray,
    actions: np.ndarray,
    contract: Mapping[str, Any],
    action_weight: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return R403 differential/common costs plus normalized action effort.

    ``actions`` uses the executed normalized action basis with shape
    ``(steps, agents, action_dims)``.  The effort is the per-step mean across
    agents of the squared two-dimensional action norm, matching the frozen
    R403 repair contract.
    """

    weight = float(action_weight)
    if not np.isfinite(weight) or weight < 0.0:
        raise ValueError("action_weight must be finite and non-negative")
    action_array = np.asarray(actions, dtype=float)
    if action_array.ndim != 3 or action_array.shape[1:] != (
        AGENT_COUNT,
        ACTION_DIM,
    ):
        raise ValueError(
            "actions must have shape (steps, AGENT_COUNT, ACTION_DIM)"
        )
    differential, common = physical_costs(
        frequencies_hz,
        rocof_hz_s,
        p_es,
        contract=contract,
    )
    if action_array.shape[0] != differential.shape[0]:
        raise ValueError("actions and physical traces must have equal step counts")
    effort = np.mean(np.sum(action_array**2, axis=2), axis=1)
    repaired_differential = differential + weight * effort
    return (
        repaired_differential.astype(float),
        common.astype(float),
        effort.astype(float),
    )


def compute_rocof(
    initial_frequency_hz: np.ndarray,
    frequencies_hz: np.ndarray,
    dt: float,
) -> np.ndarray:
    """Finite-difference RoCoF including the recorded pre-step initial."""

    series = np.concatenate(
        [np.asarray(initial_frequency_hz, dtype=float)[None, :], frequencies_hz],
        axis=0,
    )
    return np.diff(series, axis=0) / float(dt)


# ── R418/B1 slew-state-aware bundle (appended; frozen classes untouched) ──

AUGMENTED_OBS_DIM: int = OBS_DIM + ACTION_DIM  # 9: 7 slots + 2 prev actions
SLW_CHECKPOINT_SCHEMA: int = 2


def project_slew_torch(
    previous_executed_action: torch.Tensor,
    normalized_target_action: torch.Tensor,
    *,
    slew_limit: float,
) -> torch.Tensor:
    """Almost-everywhere differentiable slew projection (torch path).

    Matches the historical clamp map of the runtime projector up to its
    conservative float32 one-ULP bookkeeping (R402 slew-representation
    repair).  Used inside target and online actor paths so the critic
    evaluates the same post-projection quantity the environment executes.
    """

    limit = float(slew_limit)
    if not np.isfinite(limit) or not 0.0 < limit <= 2.0:
        raise ValueError("slew_limit must be finite and lie in (0, 2]")
    if previous_executed_action.shape != normalized_target_action.shape:
        raise ValueError("previous action and target must have equal shape")
    previous = previous_executed_action.clamp(-1.0, 1.0)
    target = normalized_target_action.clamp(-1.0, 1.0)
    delta = (target - previous).clamp(-limit, limit)
    return (previous + delta).clamp(-1.0, 1.0)


def augment_joint_obs_np(
    joint_obs: np.ndarray,
    previous_executed_action: np.ndarray,
) -> np.ndarray:
    """Append the two previous executed components to each 7-slot row."""

    obs = np.asarray(joint_obs, dtype=np.float32).reshape(AGENT_COUNT, OBS_DIM)
    previous = np.asarray(previous_executed_action, dtype=np.float32).reshape(
        AGENT_COUNT, ACTION_DIM
    )
    if not np.all(np.isfinite(obs)) or not np.all(np.isfinite(previous)):
        raise ValueError("augmented observation must be finite")
    return np.concatenate([obs, previous], axis=-1).astype(np.float32)


class SlewAwareMDActor(nn.Module):
    """Per-VSG actor over the augmented 9-slot row (7 + previous executed)."""

    def __init__(self, hidden_sizes: list[int]) -> None:
        super().__init__()
        self.net = build_mlp(AUGMENTED_OBS_DIM, list(hidden_sizes), ACTION_DIM)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.net(obs))


class _SlewAwareReplayRing:
    """Replay ring storing the previous executed action alongside each step."""

    def __init__(self, capacity: int, reward_dim: int) -> None:
        self.capacity = int(capacity)
        self.reward_dim = int(reward_dim)
        self.obs = np.zeros((capacity, JOINT_OBS_DIM), dtype=np.float32)
        self.prev_actions = np.zeros((capacity, JOINT_ACTION_DIM), dtype=np.float32)
        self.actions = np.zeros((capacity, JOINT_ACTION_DIM), dtype=np.float32)
        self.rewards = np.zeros((capacity, reward_dim), dtype=np.float32)
        self.next_obs = np.zeros((capacity, JOINT_OBS_DIM), dtype=np.float32)
        self.dones = np.zeros((capacity, 1), dtype=np.float32)
        self.size = 0
        self._ptr = 0

    def add(
        self,
        obs: np.ndarray,
        prev_actions: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.obs[self._ptr] = obs
        self.prev_actions[self._ptr] = prev_actions
        self.actions[self._ptr] = actions
        self.rewards[self._ptr] = rewards
        self.next_obs[self._ptr] = next_obs
        self.dones[self._ptr] = float(done)
        self._ptr = (self._ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, device: torch.device) -> dict[str, torch.Tensor]:
        idx = np.random.randint(0, self.size, size=batch_size)
        return {
            "obs": torch.FloatTensor(self.obs[idx]).to(device),
            "prev_actions": torch.FloatTensor(self.prev_actions[idx]).to(device),
            "actions": torch.FloatTensor(self.actions[idx]).to(device),
            "rewards": torch.FloatTensor(self.rewards[idx]).to(device),
            "next_obs": torch.FloatTensor(self.next_obs[idx]).to(device),
            "dones": torch.FloatTensor(self.dones[idx]).to(device),
        }


class _SlewAwareJointTD3Base:
    """Slew-state-aware scaffold: augmented actor state, projected target and
    online actions, executed-action replay semantics.  Every other frozen
    hyperparameter matches the R401 contract."""

    def __init__(
        self,
        out_dim: int,
        hidden_sizes: list[int] | None = None,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        buffer_size: int = 200000,
        batch_size: int = 256,
        policy_noise: float = 0.2,
        noise_clip: float = 0.5,
        explore_noise: float = 0.1,
        policy_delay: int = 2,
        device: str = "cpu",
        actor_neighbour_mask: bool = False,
        action_slew_limit: float = 0.25,
    ) -> None:
        hidden = list(hidden_sizes or [256, 256])
        self.out_dim = int(out_dim)
        self.device = torch.device(device)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.batch_size = int(batch_size)
        self.policy_noise = float(policy_noise)
        self.noise_clip = float(noise_clip)
        self.explore_noise = float(explore_noise)
        self.policy_delay = int(policy_delay)
        self.actor_neighbour_mask = bool(actor_neighbour_mask)
        self.action_slew_limit = float(action_slew_limit)
        self.actors = nn.ModuleList(
            [SlewAwareMDActor(hidden) for _ in range(AGENT_COUNT)]
        ).to(self.device)
        self.actor_targets = copy.deepcopy(self.actors).to(self.device)
        for parameters in self.actor_targets.parameters():
            parameters.requires_grad = False
        self.actor_optimizers = [
            optim.Adam(actor.parameters(), lr=lr) for actor in self.actors
        ]
        self.critic = TwinJointCritic(hidden, self.out_dim).to(self.device)
        self.critic_target = copy.deepcopy(self.critic).to(self.device)
        for parameters in self.critic_target.parameters():
            parameters.requires_grad = False
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        self.buffer = _SlewAwareReplayRing(buffer_size, self.out_dim)
        self._update_count = 0

    @property
    def lagrange(self) -> float:
        return float(getattr(self, "_lagrange", 0.0))

    def lagrange_step(
        self,
        episode_common_cost: float,
        budget: float,
        step: float,
        maximum: float,
    ) -> float:
        updated = self.lagrange + float(step) * (
            float(episode_common_cost) - float(budget)
        )
        self._lagrange = float(np.clip(updated, 0.0, float(maximum)))
        return self.lagrange

    def store(
        self,
        obs: np.ndarray,
        prev_actions: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.add(obs, prev_actions, actions, rewards, next_obs, done)

    def _actor_obs_row(
        self,
        joint_augmented: torch.Tensor,
        actor_index: int,
    ) -> torch.Tensor:
        start = actor_index * AUGMENTED_OBS_DIM
        row = joint_augmented[:, start:start + AUGMENTED_OBS_DIM]
        if self.actor_neighbour_mask:
            row = row.clone()
            row[:, list(NEIGHBOUR_SLOTS)] = 0.0
        return row

    def _augmented_rows(
        self, joint_obs: torch.Tensor, prev_actions: torch.Tensor
    ) -> torch.Tensor:
        return torch.cat(
            [
                torch.cat(
                    [joint_obs[:, i * OBS_DIM:(i + 1) * OBS_DIM],
                     prev_actions[:, i * ACTION_DIM:(i + 1) * ACTION_DIM]],
                    dim=-1,
                )
                for i in range(AGENT_COUNT)
            ],
            dim=-1,
        )

    def act(
        self,
        augmented_actor_obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        """Return the four-row joint action from the augmented observation."""

        rows = np.asarray(augmented_actor_obs, dtype=np.float32).reshape(
            AGENT_COUNT, AUGMENTED_OBS_DIM
        )
        if self.actor_neighbour_mask:
            rows = rows.copy()
            rows[:, list(NEIGHBOUR_SLOTS)] = 0.0
        actions = np.zeros((AGENT_COUNT, ACTION_DIM), dtype=np.float32)
        with torch.no_grad():
            for actor_index, actor in enumerate(self.actors):
                row = torch.FloatTensor(rows[actor_index]).unsqueeze(0).to(
                    self.device
                )
                action = actor(row).cpu().numpy().flatten()
                if not deterministic:
                    noise = np.random.normal(
                        0.0, self.explore_noise, size=action.shape
                    )
                    action = action + noise
                actions[actor_index] = action
        return np.clip(actions, -1.0, 1.0).astype(np.float32)

    def _target_actions(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        augmented_next = self._augmented_rows(batch["next_obs"], batch["actions"])
        projected = []
        for i in range(AGENT_COUNT):
            raw = self.actor_targets[i](self._actor_obs_row(augmented_next, i))
            noise = (
                torch.randn_like(raw) * self.policy_noise
            ).clamp(-self.noise_clip, self.noise_clip)
            noisy = (raw + noise).clamp(-1.0, 1.0)
            previous = batch["actions"][:, i * ACTION_DIM:(i + 1) * ACTION_DIM]
            projected.append(
                project_slew_torch(
                    previous, noisy, slew_limit=self.action_slew_limit
                )
            )
        return torch.cat(projected, dim=-1)

    def _critic_update(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        with torch.no_grad():
            next_actions = self._target_actions(batch)
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(q1_next, q2_next)
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        loss.backward()
        self.critic_optimizer.step()
        return loss.detach()

    def _actor_objective(
        self,
        obs: torch.Tensor,
        actor_index: int,
        action_row: torch.Tensor,
        baseline_actions: torch.Tensor,
    ) -> torch.Tensor:
        joint = baseline_actions.clone()
        joint[:, actor_index * ACTION_DIM:(actor_index + 1) * ACTION_DIM] = (
            action_row
        )
        q1, _ = self.critic(obs, joint)
        return q1

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": SLW_CHECKPOINT_SCHEMA,
            "out_dim": self.out_dim,
            "lagrange": self.lagrange,
            "actors": {
                str(i): actor.state_dict() for i, actor in enumerate(self.actors)
            },
            "critic": self.critic.state_dict(),
            "critic_target": self.critic_target.state_dict(),
            "actor_targets": {
                str(i): target.state_dict()
                for i, target in enumerate(self.actor_targets)
            },
        }
        torch.save(payload, str(path))

    def load(self, path: str | Path) -> None:
        payload = torch.load(str(path), map_location=self.device)
        if (
            payload.get("schema_version") != SLW_CHECKPOINT_SCHEMA
            or payload.get("out_dim") != self.out_dim
        ):
            raise ValueError("incompatible slew-aware checkpoint payload")
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        for index, actor in enumerate(self.actors):
            actor.load_state_dict(payload["actors"][str(index)])
            self.actor_targets[index].load_state_dict(
                payload["actor_targets"][str(index)]
            )
        self._lagrange = float(payload.get("lagrange", 0.0))


class SlewAwareCDMATD3(_SlewAwareJointTD3Base):
    """B1 arm: slew-state-aware CD-MATD3 (out_dim 2, Lagrange common channel)."""

    def __init__(self, lagrange_initial: float = 1.0, **kwargs: Any) -> None:
        super().__init__(out_dim=2, **kwargs)
        self._lagrange = float(lagrange_initial)

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        critic_loss = self._critic_update(batch)
        actor_loss_mean = float("nan")
        if self._update_count % self.policy_delay == 0:
            augmented = self._augmented_rows(batch["obs"], batch["prev_actions"])
            with torch.no_grad():
                baseline_rows = []
                for i in range(AGENT_COUNT):
                    raw = self.actors[i](self._actor_obs_row(augmented, i))
                    baseline_rows.append(
                        project_slew_torch(
                            batch["prev_actions"][
                                :, i * ACTION_DIM:(i + 1) * ACTION_DIM
                            ],
                            raw,
                            slew_limit=self.action_slew_limit,
                        )
                    )
                baseline = torch.cat(baseline_rows, dim=-1)
            losses = []
            for i, optimizer in enumerate(self.actor_optimizers):
                raw = self.actors[i](self._actor_obs_row(augmented, i))
                row = project_slew_torch(
                    batch["prev_actions"][:, i * ACTION_DIM:(i + 1) * ACTION_DIM],
                    raw,
                    slew_limit=self.action_slew_limit,
                )
                q1 = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss = -torch.mean(q1[:, 0] + self.lagrange * q1[:, 1])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            for target, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        return {
            "critic_loss": float(critic_loss.cpu()),
            "actor_loss_mean": actor_loss_mean,
            "lagrange": self.lagrange,
        }


class SlewAwareYangScalarTD3(_SlewAwareJointTD3Base):
    """B1 arm: slew-state-aware scalar-reward TD3 (out_dim 1)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(out_dim=1, **kwargs)

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        critic_loss = self._critic_update(batch)
        actor_loss_mean = float("nan")
        if self._update_count % self.policy_delay == 0:
            augmented = self._augmented_rows(batch["obs"], batch["prev_actions"])
            with torch.no_grad():
                baseline_rows = []
                for i in range(AGENT_COUNT):
                    raw = self.actors[i](self._actor_obs_row(augmented, i))
                    baseline_rows.append(
                        project_slew_torch(
                            batch["prev_actions"][
                                :, i * ACTION_DIM:(i + 1) * ACTION_DIM
                            ],
                            raw,
                            slew_limit=self.action_slew_limit,
                        )
                    )
                baseline = torch.cat(baseline_rows, dim=-1)
            losses = []
            for i, optimizer in enumerate(self.actor_optimizers):
                raw = self.actors[i](self._actor_obs_row(augmented, i))
                row = project_slew_torch(
                    batch["prev_actions"][:, i * ACTION_DIM:(i + 1) * ACTION_DIM],
                    raw,
                    slew_limit=self.action_slew_limit,
                )
                q1 = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss = -torch.mean(q1[:, 0])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            for target, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        return {
            "critic_loss": float(critic_loss.cpu()),
            "actor_loss_mean": actor_loss_mean,
        }


__all__ = [
    "CDMATD3",
    "DeterministicMDActor",
    "FixedWeightCDMATD3",
    "JOINT_INPUT_DIM",
    "JOINT_OBS_DIM",
    "JOINT_ACTION_DIM",
    "NEIGHBOUR_SLOTS",
    "SlewAwareCDMATD3",
    "SlewAwareMDActor",
    "SlewAwareYangScalarTD3",
    "TwinJointCritic",
    "YangScalarTD3",
    "augment_joint_obs_np",
    "compute_rocof",
    "mask_neighbour_slots",
    "physical_costs",
    "physical_costs_with_action_effort",
    "project_slew_torch",
]
