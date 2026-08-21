"""B3 diagnostic instrumentation for the CD-MATD3 learner family.

These subclasses replicate the frozen update computations exactly (bit-
comparable to the sealed learners under identical seeds) and add read-only
failure-attribution diagnostics: critic/actor losses, Bellman-residual
statistics, log-scale gradient norms, and replay-coverage proxies
(P3, feedback_loop_deep_research_2026-08-17.md).

The classes live in this separate module so that the sealed learner file
(``andes_rl_kundur/agents/cd_matd3.py``) never drifts from the R410/R419
seals when diagnostics are added.  Import them here, never from cd_matd3.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from andes_rl_kundur.agents.cd_matd3 import (
    ACTION_DIM,
    AGENT_COUNT,
    CDMATD3,
    SlewAwareCDMATD3,
    YangScalarTD3,
    project_slew_torch,
)


def _grad_norm_metrics(module: nn.Module, prefix: str) -> dict[str, float]:
    """Log-scale gradient statistics over one module's parameters."""
    norms = [
        float(param.grad.detach().norm().item())
        for param in module.parameters()
        if param.grad is not None
    ]
    if not norms:
        return {
            f"{prefix}_grad_norm_mean": 0.0,
            f"{prefix}_grad_norm_max": 0.0,
        }
    log_norms = np.log(np.asarray(norms, dtype=float) + 1e-12)
    return {
        f"{prefix}_grad_norm_mean": float(np.mean(log_norms)),
        f"{prefix}_grad_norm_max": float(np.max(log_norms)),
    }


def _residual_metrics(
    target: torch.Tensor, q1: torch.Tensor
) -> dict[str, float]:
    """Bellman-residual statistics from the critic update tensors (no RNG)."""
    residual = (target.detach() - q1.detach()).reshape(-1)
    mean = float(residual.mean().item())
    std = float(residual.std().item())
    abs_max = float(residual.abs().max().item())
    percentiles = [
        float(value)
        for value in torch.quantile(residual, torch.tensor([0.25, 0.5, 0.75]))
        .cpu()
        .numpy()
    ]
    return {
        "bellman_residual_mean": mean,
        "bellman_residual_abs_max": abs_max,
        "bellman_residual_std": std,
        "bellman_residual_q25": percentiles[0],
        "bellman_residual_q50": percentiles[1],
        "bellman_residual_q75": percentiles[2],
    }


def _coverage_metrics(
    batch: Mapping[str, torch.Tensor], residual: torch.Tensor
) -> dict[str, float]:
    """Registered replay-coverage proxies: TD-error spread and batch-state
    variance from the sampled batch (no added sampling, no RNG)."""
    residual_flat = residual.detach().reshape(-1)
    td_error_std = float(residual_flat.std().item())
    obs = batch["obs"]
    state_var_mean = float(obs.var(dim=0).mean().item())
    return {
        "td_error_std": td_error_std,
        "sampled_state_variance_mean": state_var_mean,
    }


class DiagnosticCDMATD3(CDMATD3):
    """CD-MATD3 with read-only failure-attribution diagnostics."""

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        with torch.no_grad():
            next_actions = self._target_actions(batch["next_obs"])
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(q1_next, q2_next)
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        diagnostics = {
            "critic_loss": float(
                (F.mse_loss(q1, target) + F.mse_loss(q2, target)).detach().cpu()
            )
        }
        diagnostics.update(_residual_metrics(target, q1))
        diagnostics.update(_coverage_metrics(batch, target - q1))
        loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        loss.backward()
        diagnostics.update(_grad_norm_metrics(self.critic, "critic"))
        self.critic_optimizer.step()
        actor_loss_mean = float("nan")
        if self._update_count % self.policy_delay == 0:
            with torch.no_grad():
                baseline_rows = [
                    self.actors[i](self._actor_obs_row(batch["obs"], i))
                    for i in range(AGENT_COUNT)
                ]
                baseline = torch.cat(baseline_rows, dim=-1)
            losses = []
            actor_grad_means = []
            actor_grad_maxes = []
            for i, optimizer in enumerate(self.actor_optimizers):
                row = self.actors[i](self._actor_obs_row(batch["obs"], i))
                q1_actor = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss_actor = -torch.mean(
                    q1_actor[:, 0] + self.lagrange * q1_actor[:, 1]
                )
                optimizer.zero_grad()
                loss_actor.backward()
                norms = [
                    float(param.grad.detach().norm().item())
                    for param in self.actors[i].parameters()
                    if param.grad is not None
                ]
                if norms:
                    log_norms = np.log(np.asarray(norms, dtype=float) + 1e-12)
                    actor_grad_means.append(float(np.mean(log_norms)))
                    actor_grad_maxes.append(float(np.max(log_norms)))
                optimizer.step()
                losses.append(float(loss_actor.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            diagnostics["actor_grad_norm_mean"] = (
                float(np.mean(actor_grad_means)) if actor_grad_means else 0.0
            )
            diagnostics["actor_grad_norm_max"] = (
                float(np.max(actor_grad_maxes)) if actor_grad_maxes else 0.0
            )
            for target_net, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target_net.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        diagnostics["actor_loss_mean"] = actor_loss_mean
        diagnostics["lagrange"] = self.lagrange
        return diagnostics


class DiagnosticYangScalarTD3(YangScalarTD3):
    """Scalar-reward TD3 with the same read-only diagnostic instrumentation."""

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        with torch.no_grad():
            next_actions = self._target_actions(batch["next_obs"])
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(q1_next, q2_next)
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        diagnostics = {
            "critic_loss": float(
                (F.mse_loss(q1, target) + F.mse_loss(q2, target)).detach().cpu()
            )
        }
        diagnostics.update(_residual_metrics(target, q1))
        diagnostics.update(_coverage_metrics(batch, target - q1))
        loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        loss.backward()
        diagnostics.update(_grad_norm_metrics(self.critic, "critic"))
        self.critic_optimizer.step()
        actor_loss_mean = float("nan")
        if self._update_count % self.policy_delay == 0:
            with torch.no_grad():
                baseline_rows = [
                    self.actors[i](self._actor_obs_row(batch["obs"], i))
                    for i in range(AGENT_COUNT)
                ]
                baseline = torch.cat(baseline_rows, dim=-1)
            losses = []
            actor_grad_means = []
            actor_grad_maxes = []
            for i, optimizer in enumerate(self.actor_optimizers):
                row = self.actors[i](self._actor_obs_row(batch["obs"], i))
                q1_actor = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss_actor = -torch.mean(q1_actor[:, 0])
                optimizer.zero_grad()
                loss_actor.backward()
                norms = [
                    float(param.grad.detach().norm().item())
                    for param in self.actors[i].parameters()
                    if param.grad is not None
                ]
                if norms:
                    log_norms = np.log(np.asarray(norms, dtype=float) + 1e-12)
                    actor_grad_means.append(float(np.mean(log_norms)))
                    actor_grad_maxes.append(float(np.max(log_norms)))
                optimizer.step()
                losses.append(float(loss_actor.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            diagnostics["actor_grad_norm_mean"] = (
                float(np.mean(actor_grad_means)) if actor_grad_means else 0.0
            )
            diagnostics["actor_grad_norm_max"] = (
                float(np.max(actor_grad_maxes)) if actor_grad_maxes else 0.0
            )
            for target_net, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target_net.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        diagnostics["actor_loss_mean"] = actor_loss_mean
        return diagnostics


class DiagnosticSlewAwareCDMATD3(SlewAwareCDMATD3):
    """Slew-aware CD-MATD3 with the same read-only diagnostic hooks."""

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        with torch.no_grad():
            next_actions = self._target_actions(batch)
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(q1_next, q2_next)
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        diagnostics = {
            "critic_loss": float(
                (F.mse_loss(q1, target) + F.mse_loss(q2, target)).detach().cpu()
            )
        }
        diagnostics.update(_residual_metrics(target, q1))
        diagnostics.update(_coverage_metrics(batch, target - q1))
        loss = F.mse_loss(q1, target) + F.mse_loss(q2, target)
        self.critic_optimizer.zero_grad()
        loss.backward()
        diagnostics.update(_grad_norm_metrics(self.critic, "critic"))
        self.critic_optimizer.step()
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
            actor_grad_means = []
            actor_grad_maxes = []
            for i, optimizer in enumerate(self.actor_optimizers):
                raw = self.actors[i](self._actor_obs_row(augmented, i))
                row = project_slew_torch(
                    batch["prev_actions"][:, i * ACTION_DIM:(i + 1) * ACTION_DIM],
                    raw,
                    slew_limit=self.action_slew_limit,
                )
                q1_actor = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                loss_actor = -torch.mean(
                    q1_actor[:, 0] + self.lagrange * q1_actor[:, 1]
                )
                optimizer.zero_grad()
                loss_actor.backward()
                norms = [
                    float(param.grad.detach().norm().item())
                    for param in self.actors[i].parameters()
                    if param.grad is not None
                ]
                if norms:
                    log_norms = np.log(np.asarray(norms, dtype=float) + 1e-12)
                    actor_grad_means.append(float(np.mean(log_norms)))
                    actor_grad_maxes.append(float(np.max(log_norms)))
                optimizer.step()
                losses.append(float(loss_actor.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            diagnostics["actor_grad_norm_mean"] = (
                float(np.mean(actor_grad_means)) if actor_grad_means else 0.0
            )
            diagnostics["actor_grad_norm_max"] = (
                float(np.max(actor_grad_maxes)) if actor_grad_maxes else 0.0
            )
            for target_net, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(
                    target_net.parameters(), actor.parameters()
                ):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
            for target_param, param in zip(
                self.critic_target.parameters(), self.critic.parameters()
            ):
                target_param.data.mul_(1.0 - self.tau)
                target_param.data.add_(self.tau * param.data)
        diagnostics["actor_loss_mean"] = actor_loss_mean
        diagnostics["lagrange"] = self.lagrange
        return diagnostics


__all__ = [
    "DiagnosticCDMATD3",
    "DiagnosticSlewAwareCDMATD3",
    "DiagnosticYangScalarTD3",
]
