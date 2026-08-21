"""R427 critic target normalization subclasses (DR-menu P1, PopArt-style).

The R427 single factor (bounded literature menu
``paper/yang_md_decoupling_marl/working/r423_value_estimation_repair_deep_research_2026-08-17.md``,
P1): the CD-arm critic's DIFFERENTIAL-channel TD target gains a PopArt-style
running mean/std normalization with exact output correction, layered on the
R425 bundle.  The common channel (critic second output column, bootstrap
second column, the lambda Lagrange machinery, the R419 reward seam) and the
scalar arm stay verbatim.

Frozen protocol (exact formulas; the semantic gate in SKILL.md section 2
requires them written here verbatim):

    bootstrap (no-grad): a_next = _target_actions(next_obs)   # R425 verbatim
        q1', q2' = critic_target(next_obs, a_next)            # (B, 2)
        q'_min = min(q1', q2')
        q'_min[:, 0] = sigma_d * q'_min[:, 0] + mu_d          # differential
        t = r + gamma * (1 - d) * q'_min                      # raw target
    stats update (no-grad, BEFORE the loss):
        batch_mean = mean(t[:, 0]);  batch_var = var(t[:, 0], unbiased=False)
        mu_d    <- (1 - beta) * mu_d + beta * batch_mean
        sigma_d <- clip(sqrt((1 - beta) * sigma_d^2 + beta * batch_var),
                        sigma_min, inf)
    normalized loss (post-update stats):
        t_d_norm = (t[:, 0] - mu_d) / sigma_d;   t_c = t[:, 1]
        L = MSE(q1[:, 0], t_d_norm) + MSE(q1[:, 1], t_c)
          + MSE(q2[:, 0], t_d_norm) + MSE(q2[:, 1], t_c)
    original-scale reconstruction (readout only; exact identity):
        L_orig = sigma_d^2 * (MSE(q1[:, 0], t_d_norm) + MSE(q2[:, 0], t_d_norm))
               + MSE(q1[:, 1], t_c) + MSE(q2[:, 1], t_c)
               == MSE(sigma_d*q1[:, 0] + mu_d, t[:, 0]) + MSE(q1[:, 1], t_c)
                + MSE(sigma_d*q2[:, 0] + mu_d, t[:, 0]) + MSE(q2[:, 1], t_c)
    actor output correction (_actor_objective):
        q1_actor[:, 0] = sigma_d * q1[:, 0] + mu_d   (actor gradient on the
        differential channel is linearly scaled by sigma_d -- declared part
        of the mechanism, not a hidden change)

Lives in a separate module so the sealed R425 learner file
(``cd_matd3_guard_constraints_vfix.py``) never drifts from the R425 seal.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch
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

CRITIC_NORM_BETA = 1.0e-3  # frozen R427 EMA decay for mu_d/sigma_d
CRITIC_NORM_SIGMA_MIN = 1.0e-4  # frozen R427 sigma floor
CRITIC_NORM_MU_INIT = 0.0  # frozen R427 mu init
CRITIC_NORM_SIGMA_INIT = 1.0  # frozen R427 sigma init


class PopArtDifferentialCriticSlewAwareCDMATD3Signfix(
    GuardConstrainedSlewAwareCDMATD3Signfix
):
    """CD arm with the frozen R427 repair: differential-channel critic
    target normalization (PopArt-style running mean/std + output
    correction) on top of the R425 sign-corrected guard-aligned
    constraints.

    The overrides replicate the sealed R425 computation verbatim and
    insert exactly the frozen normalization seam in the critic update and
    the actor's critic read; the guard-aligned actor terms, the Lagrange
    machinery, and the reward seam are inherited unchanged.
    """

    def __init__(self, lagrange_initial: float = 1.0, **kwargs: Any) -> None:
        super().__init__(lagrange_initial=lagrange_initial, **kwargs)
        self._mu_d = float(CRITIC_NORM_MU_INIT)
        self._sigma_d = float(CRITIC_NORM_SIGMA_INIT)
        self._last_critic_loss_original = float("nan")

    @property
    def mu_d(self) -> float:
        return float(self._mu_d)

    @property
    def sigma_d(self) -> float:
        return float(self._sigma_d)

    def _apply_critic_stats_update(
        self, batch_mean: float, batch_var: float
    ) -> tuple[float, float]:
        """Frozen EMA stats update (factored out for the directed tests and
        the rehearsal semantics probe).  Returns the post-update pair."""
        self._mu_d = (
            (1.0 - CRITIC_NORM_BETA) * self._mu_d
            + CRITIC_NORM_BETA * float(batch_mean)
        )
        self._sigma_d = float(
            np.clip(
                np.sqrt(
                    (1.0 - CRITIC_NORM_BETA) * self._sigma_d**2
                    + CRITIC_NORM_BETA * float(batch_var)
                ),
                CRITIC_NORM_SIGMA_MIN,
                None,
            )
        )
        return self.mu_d, self.sigma_d

    def _critic_update(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        with torch.no_grad():
            next_actions = self._target_actions(batch)
            q1_next, q2_next = self.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(q1_next, q2_next)
            # R427 single factor: differential-column output correction on
            # the bootstrap; the common column is verbatim.
            q_next_rescaled = q_next.clone()
            q_next_rescaled[:, 0] = (
                self._sigma_d * q_next[:, 0] + self._mu_d
            )
            target = batch["rewards"] + self.gamma * (
                1.0 - batch["dones"]
            ) * q_next_rescaled
            t_d = target[:, 0]
            batch_mean = float(torch.mean(t_d).cpu())
            batch_var = float(torch.var(t_d, unbiased=False).cpu())
            # Frozen order: stats update BEFORE the normalization loss.
            self._apply_critic_stats_update(batch_mean, batch_var)
        q1, q2 = self.critic(batch["obs"], batch["actions"])
        t_d_norm = (t_d - self._mu_d) / self._sigma_d
        t_c = target[:, 1]
        loss = (
            F.mse_loss(q1[:, 0], t_d_norm)
            + F.mse_loss(q1[:, 1], t_c)
            + F.mse_loss(q2[:, 0], t_d_norm)
            + F.mse_loss(q2[:, 1], t_c)
        )
        with torch.no_grad():
            loss_original = (
                self._sigma_d**2
                * (
                    F.mse_loss(q1[:, 0], t_d_norm)
                    + F.mse_loss(q2[:, 0], t_d_norm)
                )
                + F.mse_loss(q1[:, 1], t_c)
                + F.mse_loss(q2[:, 1], t_c)
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
        q1 = super()._actor_objective(
            obs, actor_index, action_row, baseline_actions=baseline_actions
        )
        # R427 single factor: output correction on the differential column
        # so the actor keeps original-scale value semantics; sigma_d is a
        # plain scalar state, so the actor gradient is scaled linearly.
        q1 = q1.clone()
        q1[:, 0] = self._sigma_d * q1[:, 0] + self._mu_d
        return q1

    def update(self) -> dict[str, float] | None:
        if self.buffer.size < self.batch_size:
            return None
        self._update_count += 1
        batch = self.buffer.sample(self.batch_size, self.device)
        critic_loss = self._critic_update(batch)
        actor_loss_mean = float("nan")
        actor_grad_norm_log10 = float("nan")
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
            grad_norms = []
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
                rms_term = torch.mean(row**2)
                tv_term = torch.mean(torch.abs(row - previous_row))
                loss = -torch.mean(
                    q1[:, 0] + self.lagrange * q1[:, 1]
                ) + self._mu_rms * rms_term + self._mu_tv * tv_term
                optimizer.zero_grad()
                loss.backward()
                # log-only (no RNG): per-actor gradient norm before step.
                grad_norm = float(
                    sum(
                        (p.grad.detach().norm() ** 2).item()
                        for p in self.actors[i].parameters()
                        if p.grad is not None
                    )
                    ** 0.5
                )
                grad_norms.append(grad_norm)
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            actor_loss_mean = float(np.mean(losses))
            if grad_norms:
                actor_grad_norm_log10 = float(
                    np.log10(max(float(np.mean(grad_norms)), 1.0e-30))
                )
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
            "critic_loss_original": self._last_critic_loss_original,
            "actor_loss_mean": actor_loss_mean,
            "lagrange": self.lagrange,
            "mu_rms": self.mu_rms,
            "mu_tv": self.mu_tv,
            "mu_d": self.mu_d,
            "sigma_d": self.sigma_d,
            "actor_grad_norm_log10": actor_grad_norm_log10,
        }

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": SLW_CHECKPOINT_SCHEMA,
            "out_dim": self.out_dim,
            "lagrange": self.lagrange,
            "mu_rms": self.mu_rms,
            "mu_tv": self.mu_tv,
            "mu_d": self.mu_d,
            "sigma_d": self.sigma_d,
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
        self._mu_d = float(payload.get("mu_d", CRITIC_NORM_MU_INIT))
        self._sigma_d = float(payload.get("sigma_d", CRITIC_NORM_SIGMA_INIT))
