"""Executed-action SAC with distinct actor and critic observation sources.

The source intervention is performed outside the learner.  This module only
stores the two observation views and guarantees that every Q path receives the
physically executed (amplitude- and slew-projected) action.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from andes_rl_kundur.agents.executed_action_sac import (
    ExecutedActionSACAgent,
    augment_state_torch,
    project_action_torch,
)


class SourceReplayBuffer:
    """Create-only-in-memory replay with separate actor/critic observations."""

    def __init__(self, obs_dim: int, action_dim: int, capacity: int) -> None:
        self.capacity = int(capacity)
        self.actor_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.critic_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.previous_executed_actions = np.zeros(
            (capacity, action_dim), dtype=np.float32
        )
        self.raw_actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.executed_actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.rewards = np.zeros((capacity, 1), dtype=np.float32)
        self.next_actor_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.next_critic_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.dones = np.zeros((capacity, 1), dtype=np.float32)
        self.size = 0
        self._ptr = 0

    def add(
        self,
        actor_obs: np.ndarray,
        critic_obs: np.ndarray,
        previous_executed_action: np.ndarray,
        raw_action: np.ndarray,
        executed_action: np.ndarray,
        reward: float,
        next_actor_obs: np.ndarray,
        next_critic_obs: np.ndarray,
        done: bool,
    ) -> None:
        i = self._ptr
        self.actor_obs[i] = actor_obs
        self.critic_obs[i] = critic_obs
        self.previous_executed_actions[i] = previous_executed_action
        self.raw_actions[i] = raw_action
        self.executed_actions[i] = executed_action
        self.rewards[i] = float(reward)
        self.next_actor_obs[i] = next_actor_obs
        self.next_critic_obs[i] = next_critic_obs
        self.dones[i] = float(done)
        self._ptr = (i + 1) % self.capacity
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
            "actor_obs": tensor(self.actor_obs),
            "critic_obs": tensor(self.critic_obs),
            "previous_executed_actions": tensor(self.previous_executed_actions),
            "raw_actions": tensor(self.raw_actions),
            "executed_actions": tensor(self.executed_actions),
            "rewards": tensor(self.rewards),
            "next_actor_obs": tensor(self.next_actor_obs),
            "next_critic_obs": tensor(self.next_critic_obs),
            "dones": tensor(self.dones),
        }

    def __len__(self) -> int:
        return self.size


class SourceFactorialSACAgent(ExecutedActionSACAgent):
    """U3 SAC seam extended only by separate actor/critic observation views."""

    algo_name = "source_factorial_executed_action_sac"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.buffer = SourceReplayBuffer(
            self.obs_dim, self.action_dim, capacity=self.buffer.capacity
        )

    def store_source_transition(
        self,
        actor_obs: np.ndarray,
        critic_obs: np.ndarray,
        previous_executed_action: np.ndarray,
        raw_action: np.ndarray,
        executed_action: np.ndarray,
        reward: float,
        next_actor_obs: np.ndarray,
        next_critic_obs: np.ndarray,
        done: bool,
    ) -> None:
        expected = self.execute_action(previous_executed_action, raw_action)
        actual = np.asarray(executed_action, dtype=np.float32)
        if not np.allclose(expected, actual, rtol=0.0, atol=1.0e-7):
            raise ValueError("executed action does not match the frozen projector")
        self.buffer.add(
            actor_obs,
            critic_obs,
            previous_executed_action,
            raw_action,
            actual,
            reward,
            next_actor_obs,
            next_critic_obs,
            done,
        )

    def source_loss_inputs(
        self,
        batch: dict[str, torch.Tensor],
        *,
        deterministic_target: bool = False,
    ) -> dict[str, torch.Tensor]:
        previous = batch["previous_executed_actions"]
        executed = batch["executed_actions"]
        actor_state = augment_state_torch(batch["actor_obs"], previous)
        critic_state = augment_state_torch(batch["critic_obs"], previous)
        next_actor_state = augment_state_torch(batch["next_actor_obs"], executed)
        next_critic_state = augment_state_torch(batch["next_critic_obs"], executed)
        with torch.no_grad():
            if deterministic_target:
                target_raw = self.actor.deterministic(next_actor_state)
                target_log_prob = torch.zeros(
                    (next_actor_state.shape[0], 1),
                    dtype=next_actor_state.dtype,
                    device=next_actor_state.device,
                )
            else:
                target_raw, target_log_prob = self.actor.sample(next_actor_state)
            target_executed = project_action_torch(
                executed, target_raw, slew_limit=self.slew_limit
            )
            q1_target, q2_target = self.critic_target(
                next_critic_state, target_executed
            )
            td_target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * (torch.minimum(q1_target, q2_target) - self.alpha * target_log_prob)

        actor_raw, actor_log_prob = self.actor.sample(actor_state)
        actor_executed = project_action_torch(
            previous, actor_raw, slew_limit=self.slew_limit
        )
        return {
            "actor_state": actor_state,
            "critic_state": critic_state,
            "next_actor_state": next_actor_state,
            "next_critic_state": next_critic_state,
            "critic_current_action_input": executed,
            "target_actor_raw_action": target_raw,
            "target_projected_action": target_executed,
            "critic_target_action_input": target_executed,
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
        paths = self.source_loss_inputs(batch)

        q1, q2 = self.critic(
            paths["critic_state"], paths["critic_current_action_input"]
        )
        critic_loss = F.mse_loss(q1, paths["td_target"]) + F.mse_loss(
            q2, paths["td_target"]
        )
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        q1_actor, q2_actor = self.critic(
            paths["critic_state"], paths["actor_critic_action_input"]
        )
        actor_loss = (
            self.alpha.detach() * paths["actor_log_prob"]
            - torch.minimum(q1_actor, q2_actor)
        ).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        grad_sq = torch.zeros((), dtype=torch.float32, device=self.device)
        for parameter in self.actor.parameters():
            if parameter.grad is not None:
                grad_sq += torch.sum(parameter.grad.detach() ** 2)
        actor_grad_norm = float(torch.sqrt(grad_sq).cpu())
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
            "actor_grad_norm": actor_grad_norm,
        }

    def export_state(self) -> dict[str, Any]:
        return {
            "actor": copy.deepcopy(self.actor.state_dict()),
            "critic": copy.deepcopy(self.critic.state_dict()),
            "critic_target": copy.deepcopy(self.critic_target.state_dict()),
            "log_alpha": self.log_alpha.detach().cpu().clone(),
        }

    def import_state(self, payload: dict[str, Any]) -> None:
        self.actor.load_state_dict(payload["actor"])
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        self.log_alpha.data = payload["log_alpha"].to(self.device)

    def save_source_checkpoint(
        self, path: str | Path, *, metadata: dict[str, Any]
    ) -> None:
        torch.save(
            {
                "schema_version": 1,
                "kind": "source-factorial-executed-action-sac",
                "obs_dim": self.obs_dim,
                "action_dim": self.action_dim,
                "slew_limit": self.slew_limit,
                "entropy_semantics": self.entropy_semantics,
                "metadata": metadata,
                **self.export_state(),
            },
            str(path),
        )

    def load_source_checkpoint(self, path: str | Path) -> dict[str, Any]:
        payload = torch.load(str(path), map_location=self.device, weights_only=True)
        if payload.get("kind") != "source-factorial-executed-action-sac":
            raise ValueError("not a source-factorial checkpoint")
        if int(payload["obs_dim"]) != self.obs_dim:
            raise ValueError("checkpoint observation dimension mismatch")
        if int(payload["action_dim"]) != self.action_dim:
            raise ValueError("checkpoint action dimension mismatch")
        self.import_state(payload)
        return dict(payload.get("metadata") or {})
