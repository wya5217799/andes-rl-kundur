"""Head-selective, output-preserving PopArt for the R457 M2 audit.

The historical R427 learner rescales critic reads but does not remap the
critic output layer when running statistics move.  R457 keeps that historical
implementation immutable and provides a separate, symmetric two-head
intervention.  For every selected head and both twins/targets, a statistics
change ``(mu_old, sigma_old) -> (mu_new, sigma_new)`` applies

``W_new = sigma_old / sigma_new * W_old`` and
``b_new = (sigma_old * b_old + mu_old - mu_new) / sigma_new``.

Consequently ``sigma_new * q_new + mu_new`` is equal (up to float roundoff)
to ``sigma_old * q_old + mu_old`` before the gradient update.  Differential
is column 0 and common is column 1, matching the sealed R425/R427 reward seam.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from andes_rl_kundur.agents.cd_matd3 import (
    ACTION_DIM,
    AGENT_COUNT,
    SLW_CHECKPOINT_SCHEMA,
    project_slew_torch,
)
from andes_rl_kundur.agents.cd_matd3_guard_constraints_vfix import (
    GuardConstrainedSlewAwareCDMATD3Signfix,
)

HEAD_NAMES = ("differential", "common")
POPART_BETA = 1.0e-3
POPART_SIGMA_MIN = 1.0e-4


def _last_linear(module: nn.Module) -> nn.Linear:
    rows = [row for row in module.modules() if isinstance(row, nn.Linear)]
    if not rows:
        raise TypeError("critic branch has no linear output layer")
    layer = rows[-1]
    if layer.out_features != 2 or layer.bias is None:
        raise TypeError("R457 requires a biased two-head critic output layer")
    return layer


class HeadSelectivePopArtCDMATD3(GuardConstrainedSlewAwareCDMATD3Signfix):
    """R425 learner with a symmetric, selectable PopArt mask."""

    def __init__(
        self,
        *,
        normalized_heads: Sequence[str] = (),
        lagrange_initial: float = 1.0,
        popart_beta: float = POPART_BETA,
        popart_sigma_min: float = POPART_SIGMA_MIN,
        **kwargs: Any,
    ) -> None:
        selected = frozenset(str(value) for value in normalized_heads)
        unknown = selected.difference(HEAD_NAMES)
        if unknown:
            raise ValueError(f"unknown critic heads: {sorted(unknown)}")
        if not 0.0 < float(popart_beta) <= 1.0:
            raise ValueError("popart_beta must lie in (0, 1]")
        if not np.isfinite(popart_sigma_min) or float(popart_sigma_min) <= 0.0:
            raise ValueError("popart_sigma_min must be finite and positive")
        super().__init__(lagrange_initial=lagrange_initial, **kwargs)
        self._popart_mask = np.asarray(
            [name in selected for name in HEAD_NAMES], dtype=bool
        )
        self._popart_mu = np.zeros(2, dtype=np.float64)
        self._popart_sigma = np.ones(2, dtype=np.float64)
        self.popart_beta = float(popart_beta)
        self.popart_sigma_min = float(popart_sigma_min)
        self._last_critic_loss_original = float("nan")

    @property
    def normalized_heads(self) -> tuple[str, ...]:
        return tuple(
            name for index, name in enumerate(HEAD_NAMES) if self._popart_mask[index]
        )

    @property
    def popart_mu(self) -> tuple[float, float]:
        return tuple(float(value) for value in self._popart_mu)

    @property
    def popart_sigma(self) -> tuple[float, float]:
        return tuple(float(value) for value in self._popart_sigma)

    def original_scale(self, values: torch.Tensor) -> torch.Tensor:
        """Convert normalized critic columns to original return units."""

        result = values.clone()
        for index, selected in enumerate(self._popart_mask):
            if selected:
                result[:, index] = (
                    float(self._popart_sigma[index]) * values[:, index]
                    + float(self._popart_mu[index])
                )
        return result

    def normalized_target(self, target: torch.Tensor) -> torch.Tensor:
        result = target.clone()
        for index, selected in enumerate(self._popart_mask):
            if selected:
                result[:, index] = (
                    target[:, index] - float(self._popart_mu[index])
                ) / float(self._popart_sigma[index])
        return result

    def _remap_optimizer_state(
        self, parameter: torch.Tensor, *, index: int, scale: float
    ) -> None:
        state = self.critic_optimizer.state.get(parameter)
        if not state:
            return
        # Under theta_new = scale * theta_old + shift, gradients transform
        # inversely.  Preserve Adam's coordinate semantics for its moments.
        if "exp_avg" in state:
            state["exp_avg"][index].div_(float(scale))
        if "exp_avg_sq" in state:
            state["exp_avg_sq"][index].div_(float(scale) ** 2)
        if "max_exp_avg_sq" in state:
            state["max_exp_avg_sq"][index].div_(float(scale) ** 2)

    def _remap_branch(
        self,
        branch: nn.Module,
        *,
        index: int,
        mu_old: float,
        sigma_old: float,
        mu_new: float,
        sigma_new: float,
        optimizer_state: bool,
    ) -> None:
        layer = _last_linear(branch)
        scale = float(sigma_old / sigma_new)
        with torch.no_grad():
            layer.weight[index].mul_(scale)
            layer.bias[index].mul_(float(sigma_old))
            layer.bias[index].add_(float(mu_old - mu_new))
            layer.bias[index].div_(float(sigma_new))
        if optimizer_state:
            self._remap_optimizer_state(layer.weight, index=index, scale=scale)
            self._remap_optimizer_state(layer.bias, index=index, scale=scale)

    def apply_popart_stats(self, target: torch.Tensor) -> dict[str, list[float]]:
        """Update selected statistics and preserve all original-scale outputs."""

        if target.ndim != 2 or target.shape[1] != 2:
            raise ValueError("PopArt target must have shape (batch, 2)")
        old_mu = self._popart_mu.copy()
        old_sigma = self._popart_sigma.copy()
        new_mu = old_mu.copy()
        new_sigma = old_sigma.copy()
        with torch.no_grad():
            for index, selected in enumerate(self._popart_mask):
                if not selected:
                    continue
                column = target[:, index]
                mean = float(torch.mean(column).cpu())
                variance = float(torch.var(column, unbiased=False).cpu())
                new_mu[index] = (
                    (1.0 - self.popart_beta) * old_mu[index]
                    + self.popart_beta * mean
                )
                new_sigma[index] = max(
                    float(
                        np.sqrt(
                            (1.0 - self.popart_beta) * old_sigma[index] ** 2
                            + self.popart_beta * variance
                        )
                    ),
                    self.popart_sigma_min,
                )
                for branch in (self.critic.q1, self.critic.q2):
                    self._remap_branch(
                        branch,
                        index=index,
                        mu_old=float(old_mu[index]),
                        sigma_old=float(old_sigma[index]),
                        mu_new=float(new_mu[index]),
                        sigma_new=float(new_sigma[index]),
                        optimizer_state=True,
                    )
                for branch in (self.critic_target.q1, self.critic_target.q2):
                    self._remap_branch(
                        branch,
                        index=index,
                        mu_old=float(old_mu[index]),
                        sigma_old=float(old_sigma[index]),
                        mu_new=float(new_mu[index]),
                        sigma_new=float(new_sigma[index]),
                        optimizer_state=False,
                    )
        self._popart_mu = new_mu
        self._popart_sigma = new_sigma
        return {
            "mu_old": old_mu.tolist(),
            "sigma_old": old_sigma.tolist(),
            "mu_new": new_mu.tolist(),
            "sigma_new": new_sigma.tolist(),
        }

    def _critic_update(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        with torch.no_grad():
            next_actions = self._target_actions(batch)
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next_original = torch.min(
                self.original_scale(q1_next), self.original_scale(q2_next)
            )
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next_original
            self.apply_popart_stats(target)
            target_normalized = self.normalized_target(target)
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        loss = F.mse_loss(q1, target_normalized) + F.mse_loss(q2, target_normalized)
        with torch.no_grad():
            q1_original = self.original_scale(q1)
            q2_original = self.original_scale(q2)
            loss_original = F.mse_loss(q1_original, target) + F.mse_loss(
                q2_original, target
            )
        self._last_critic_loss_original = float(loss_original.cpu())
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
        values = super()._actor_objective(
            obs, actor_index, action_row, baseline_actions=baseline_actions
        )
        return self.original_scale(values)

    def soft_update_targets(self, *, include_actors: bool) -> None:
        if include_actors:
            for target, actor in zip(self.actor_targets, self.actors):
                for target_param, param in zip(target.parameters(), actor.parameters()):
                    target_param.data.mul_(1.0 - self.tau)
                    target_param.data.add_(self.tau * param.data)
        for target_param, param in zip(
            self.critic_target.parameters(), self.critic.parameters()
        ):
            target_param.data.mul_(1.0 - self.tau)
            target_param.data.add_(self.tau * param.data)

    def actor_step(self, batch: Mapping[str, torch.Tensor]) -> dict[str, Any]:
        """Apply one R425 actor step and log unweighted head gradients."""

        augmented = self._augmented_rows(batch["obs"], batch["prev_actions"])
        with torch.no_grad():
            baseline_rows = []
            for index in range(AGENT_COUNT):
                raw = self.actors[index](self._actor_obs_row(augmented, index))
                start = index * ACTION_DIM
                baseline_rows.append(
                    project_slew_torch(
                        batch["prev_actions"][:, start:start + ACTION_DIM],
                        raw,
                        slew_limit=self.action_slew_limit,
                    )
                )
            baseline = torch.cat(baseline_rows, dim=-1)
        rows: list[dict[str, Any]] = []
        for index, optimizer in enumerate(self.actor_optimizers):
            parameters = list(self.actors[index].parameters())
            raw = self.actors[index](self._actor_obs_row(augmented, index))
            start = index * ACTION_DIM
            previous = batch["prev_actions"][:, start:start + ACTION_DIM]
            action = project_slew_torch(
                previous, raw, slew_limit=self.action_slew_limit
            )
            q1 = self._actor_objective(
                batch["obs"], index, action, baseline_actions=baseline
            )
            loss_d = -torch.mean(q1[:, 0])
            loss_c = -float(self.lagrange) * torch.mean(q1[:, 1])
            loss_rms = float(self.mu_rms) * torch.mean(action**2)
            loss_tv = float(self.mu_tv) * torch.mean(torch.abs(action - previous))
            total = loss_d + loss_c + loss_rms + loss_tv
            grads = []
            for term in (loss_d, loss_c, loss_rms, loss_tv, total):
                values = torch.autograd.grad(
                    term,
                    parameters,
                    retain_graph=True,
                    allow_unused=True,
                )
                grads.append(
                    torch.cat(
                        [
                            torch.zeros_like(parameter).reshape(-1)
                            if value is None
                            else value.reshape(-1)
                            for parameter, value in zip(parameters, values)
                        ]
                    )
                )
            if not all(torch.isfinite(value).all() for value in grads):
                raise FloatingPointError("nonfinite R457 actor gradient")
            optimizer.zero_grad()
            total.backward()
            optimizer.step()
            def norm(value: torch.Tensor) -> float:
                return float(torch.linalg.vector_norm(value).detach().cpu())
            cosine_den = norm(grads[0]) * norm(grads[1])
            cosine = 0.0 if cosine_den <= 1.0e-20 else float(
                torch.dot(grads[0], grads[1]).detach().cpu() / cosine_den
            )
            rows.append(
                {
                    "actor_index": index,
                    "losses": [float(value.detach().cpu()) for value in (loss_d, loss_c, loss_rms, loss_tv, total)],
                    "gradient_norms": [norm(value) for value in grads],
                    "differential_common_cosine": cosine,
                }
            )
        return {"actors": rows}

    def fixed_batch_update(
        self,
        batch: Mapping[str, torch.Tensor],
        *,
        update_actor: bool,
    ) -> dict[str, Any]:
        """One deterministic-index update for the two-phase R457 runner."""

        self._update_count += 1
        critic_loss = self._critic_update(batch)
        actor = None
        policy_step = self._update_count % self.policy_delay == 0
        if update_actor and policy_step:
            actor = self.actor_step(batch)
        if policy_step:
            self.soft_update_targets(include_actors=bool(update_actor))
        return {
            "critic_loss": float(critic_loss.cpu()),
            "critic_loss_original": self._last_critic_loss_original,
            "popart_mu": list(self.popart_mu),
            "popart_sigma": list(self.popart_sigma),
            "actor": actor,
            "policy_step": policy_step,
        }

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": SLW_CHECKPOINT_SCHEMA,
            "out_dim": self.out_dim,
            "normalized_heads": list(self.normalized_heads),
            "popart_mu": list(self.popart_mu),
            "popart_sigma": list(self.popart_sigma),
            "lagrange": self.lagrange,
            "mu_rms": self.mu_rms,
            "mu_tv": self.mu_tv,
            "actors": {str(i): actor.state_dict() for i, actor in enumerate(self.actors)},
            "critic": self.critic.state_dict(),
            "critic_target": self.critic_target.state_dict(),
            "actor_targets": {str(i): target.state_dict() for i, target in enumerate(self.actor_targets)},
        }
        torch.save(payload, str(path))

    def load(self, path: str | Path) -> None:
        payload = torch.load(str(path), map_location=self.device)
        if payload.get("schema_version") != SLW_CHECKPOINT_SCHEMA or payload.get("out_dim") != 2:
            raise ValueError("incompatible R457 checkpoint payload")
        if tuple(payload.get("normalized_heads", ())) != self.normalized_heads:
            raise ValueError("R457 checkpoint head mask mismatch")
        self.critic.load_state_dict(payload["critic"])
        self.critic_target.load_state_dict(payload["critic_target"])
        for index, actor in enumerate(self.actors):
            actor.load_state_dict(payload["actors"][str(index)])
            self.actor_targets[index].load_state_dict(payload["actor_targets"][str(index)])
        self._popart_mu = np.asarray(payload["popart_mu"], dtype=np.float64)
        self._popart_sigma = np.asarray(payload["popart_sigma"], dtype=np.float64)
        self._lagrange = float(payload.get("lagrange", 0.0))
        self._mu_rms = float(payload.get("mu_rms", 0.0))
        self._mu_tv = float(payload.get("mu_tv", 0.0))


__all__ = [
    "HEAD_NAMES",
    "POPART_BETA",
    "POPART_SIGMA_MIN",
    "HeadSelectivePopArtCDMATD3",
]
