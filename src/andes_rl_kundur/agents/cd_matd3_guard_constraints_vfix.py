"""R425 sign-corrected guard-aligned action-constraint subclasses.

R424 (CLM-1285) found the constraint terms entered the actor loss inside the
negated mean — gradient descent MAXIMIZED the executed-action energy and TV
statistics (reward-sign defect, gradient probe inner product -97.6 versus
the penalty direction).  This module is the R425 single factor: the SAME two
guard-aligned statistics with the same per-episode projected multipliers,
entered with the penalty sign — ``loss = -mean(Q_d + lambda*Q_c) + mu_RMS*RMS
+ mu_TV*TV`` — matching the R424 plan's frozen "append two terms onto the
loss" wording.  Everything else is verbatim R424/R419.

Lives in a separate module so the R424-sealed learner file
(``cd_matd3_guard_constraints.py``) never drifts from the R424 seal.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch

from andes_rl_kundur.agents.cd_matd3 import (
    ACTION_DIM,
    AGENT_COUNT,
    SLW_CHECKPOINT_SCHEMA,
    SlewAwareCDMATD3,
    project_slew_torch,
)

GUARD_MULTIPLIER_STEP = 0.05  # frozen R425 dual step (mirrors lagrange_step)
GUARD_MULTIPLIER_MAX = 10.0  # frozen R425 multiplier ceiling (mirrors lagrange)
GUARD_RESIDUAL_EPSILON = 1.0e-9  # frozen floor for relative residuals


class GuardConstrainedSlewAwareCDMATD3Signfix(SlewAwareCDMATD3):
    """CD arm with the frozen R425 sign-corrected guard-aligned constraints.

    The override replicates the sealed base ``update()`` actor section
    verbatim and appends the two analytic terms OUTSIDE the negated mean
    (penalty semantics), weighted by the guard multipliers.  The critic
    update, the Lagrange step, and the reward seam are inherited unchanged.
    """

    def __init__(self, lagrange_initial: float = 1.0, **kwargs: Any) -> None:
        super().__init__(lagrange_initial=lagrange_initial, **kwargs)
        self._mu_rms = 0.0
        self._mu_tv = 0.0

    @property
    def mu_rms(self) -> float:
        return float(self._mu_rms)

    @property
    def mu_tv(self) -> float:
        return float(self._mu_tv)

    def guard_multiplier_step(
        self,
        rms_residual_relative: float,
        tv_residual_relative: float,
    ) -> tuple[float, float]:
        """Per-episode dual ascent on the relative action-constraint residuals."""
        self._mu_rms = float(
            np.clip(
                self._mu_rms
                + GUARD_MULTIPLIER_STEP * float(rms_residual_relative),
                0.0,
                GUARD_MULTIPLIER_MAX,
            )
        )
        self._mu_tv = float(
            np.clip(
                self._mu_tv
                + GUARD_MULTIPLIER_STEP * float(tv_residual_relative),
                0.0,
                GUARD_MULTIPLIER_MAX,
            )
        )
        return self.mu_rms, self.mu_tv

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
                previous_row = batch["prev_actions"][
                    :, i * ACTION_DIM:(i + 1) * ACTION_DIM
                ]
                row = project_slew_torch(
                    previous_row,
                    raw,
                    slew_limit=self.action_slew_limit,
                )
                q1 = self._actor_objective(
                    batch["obs"], i, row, baseline_actions=baseline
                )
                # R425 single factor: guard-aligned action-stress terms on
                # the executed (post-slew) action row — the exact trace the
                # guards read — appended OUTSIDE the negated mean so they
                # penalize (R424's reward-sign defect corrected).
                rms_term = torch.mean(row**2)
                tv_term = torch.mean(torch.abs(row - previous_row))
                loss = -torch.mean(
                    q1[:, 0] + self.lagrange * q1[:, 1]
                ) + self._mu_rms * rms_term + self._mu_tv * tv_term
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
            "mu_rms": self.mu_rms,
            "mu_tv": self.mu_tv,
        }

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": SLW_CHECKPOINT_SCHEMA,
            "out_dim": self.out_dim,
            "lagrange": self.lagrange,
            "mu_rms": self.mu_rms,
            "mu_tv": self.mu_tv,
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
        self._mu_rms = float(payload.get("mu_rms", 0.0))
        self._mu_tv = float(payload.get("mu_tv", 0.0))
