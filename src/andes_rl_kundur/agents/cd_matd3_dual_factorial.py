"""R455 fixed-bank diagnostics for the R425 projected guard dual.

The functions in this module do not train a critic and do not recreate the
historical replay or optimizer state (neither was saved by R425).  They expose
the exact scalar projected-dual recurrence and a checkpoint-local, full-bank,
fresh-Adam actor intervention with gradient decomposition.  The deliberately
narrow API keeps the diagnostic semantics separate from production learners.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import torch

from andes_rl_kundur.agents.cd_matd3 import (
    ACTION_DIM,
    AGENT_COUNT,
    project_slew_torch,
)


def projected_dual_step(mu: float, residual: float, *, eta: float, ceiling: float) -> float:
    """Apply ``clip(mu + eta * residual, 0, ceiling)`` with strict validation."""

    values = np.asarray([mu, residual, eta, ceiling], dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("dual update inputs must be finite")
    if eta <= 0.0 or ceiling <= 0.0 or not 0.0 <= mu <= ceiling:
        raise ValueError("dual update requires eta>0, ceiling>0, and mu in [0, ceiling]")
    return float(np.clip(mu + eta * residual, 0.0, ceiling))


def replay_projected_dual(
    initial_mu: float,
    residuals: Sequence[float],
    *,
    eta: float,
    ceiling: float,
) -> dict[str, Any]:
    """Replay a sealed residual sequence and retain every pre/post value."""

    mu = float(initial_mu)
    trace: list[dict[str, float]] = []
    for index, residual_raw in enumerate(residuals):
        residual = float(residual_raw)
        post = projected_dual_step(mu, residual, eta=eta, ceiling=ceiling)
        trace.append(
            {
                "index": int(index),
                "mu_pre": mu,
                "residual_pre": residual,
                "mu_post": post,
            }
        )
        mu = post
    return {"initial_mu": float(initial_mu), "final_mu": mu, "trace": trace}


def balanced_dual_replay(
    initial_mu: float,
    profile_residuals: Mapping[str, float],
    *,
    eta: float,
    ceiling: float,
    steps: int,
    per_profile: bool,
) -> dict[str, Any]:
    """Integrate equally exposed aggregate or per-profile fixed residuals."""

    if steps <= 0 or not profile_residuals:
        raise ValueError("balanced replay requires positive steps and profiles")
    ordered = {str(key): float(profile_residuals[key]) for key in sorted(profile_residuals)}
    if not np.all(np.isfinite(list(ordered.values()))):
        raise ValueError("profile residuals must be finite")
    if per_profile:
        traces = {
            profile: replay_projected_dual(
                initial_mu,
                [residual] * int(steps),
                eta=eta,
                ceiling=ceiling,
            )
            for profile, residual in ordered.items()
        }
        return {
            "kind": "per_profile",
            "profiles": traces,
            "final_by_profile": {
                profile: float(payload["final_mu"]) for profile, payload in traces.items()
            },
        }
    mean_residual = float(np.mean(list(ordered.values())))
    trace = replay_projected_dual(
        initial_mu,
        [mean_residual] * int(steps),
        eta=eta,
        ceiling=ceiling,
    )
    return {
        "kind": "aggregate",
        "profile_balanced_mean_residual": mean_residual,
        "trace": trace,
        "final": float(trace["final_mu"]),
    }


def _flat_grads(
    loss: torch.Tensor,
    parameters: Sequence[torch.nn.Parameter],
    *,
    retain_graph: bool,
) -> torch.Tensor:
    grads = torch.autograd.grad(
        loss,
        parameters,
        retain_graph=retain_graph,
        allow_unused=True,
    )
    rows = [
        torch.zeros_like(parameter).reshape(-1) if grad is None else grad.reshape(-1)
        for parameter, grad in zip(parameters, grads)
    ]
    return torch.cat(rows)


def _norm(vector: torch.Tensor) -> float:
    return float(torch.linalg.vector_norm(vector).detach().cpu())


def _cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    denominator = torch.linalg.vector_norm(left) * torch.linalg.vector_norm(right)
    if float(denominator.detach().cpu()) <= 1.0e-20:
        return 0.0
    return float((torch.dot(left, right) / denominator).detach().cpu())


def _state_dict_digest_payload(module: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in module.state_dict().items()}


def state_dict_equal(left: Mapping[str, torch.Tensor], right: Mapping[str, torch.Tensor]) -> bool:
    """Return exact tensor equality for two state dictionaries."""

    return bool(set(left) == set(right) and all(torch.equal(left[key], right[key]) for key in left))


def _mu_row_weights(
    labels: Sequence[str], values: float | Mapping[str, float], device: torch.device
) -> torch.Tensor:
    if isinstance(values, Mapping):
        raw = [float(values[str(label)]) for label in labels]
    else:
        raw = [float(values)] * len(labels)
    tensor = torch.as_tensor(raw, dtype=torch.float32, device=device)
    if not torch.isfinite(tensor).all():
        raise ValueError("multiplier weights must be finite")
    return tensor


def fixed_bank_actor_intervention(
    agent: Any,
    *,
    observations: np.ndarray,
    previous_actions: np.ndarray,
    profile_labels: Sequence[str],
    mu_rms: float | Mapping[str, float],
    mu_tv: float | Mapping[str, float],
    actor_lr: float,
    update_steps: int,
) -> dict[str, Any]:
    """Run the frozen-critic R455 actor-only intervention.

    ``observations`` are the 28-slot joint observations expected by the critic;
    ``previous_actions`` are the flattened 8-slot executed rows used by the
    slew-aware actors.  Every update uses the complete bank.
    """

    obs_np = np.asarray(observations, dtype=np.float32)
    previous_np = np.asarray(previous_actions, dtype=np.float32)
    if obs_np.ndim != 2 or previous_np.shape != (obs_np.shape[0], AGENT_COUNT * ACTION_DIM):
        raise ValueError("fixed bank has incompatible observation/action shapes")
    if len(profile_labels) != obs_np.shape[0] or update_steps <= 0 or actor_lr <= 0.0:
        raise ValueError("fixed bank labels, update_steps, or actor_lr are invalid")
    if not np.all(np.isfinite(obs_np)) or not np.all(np.isfinite(previous_np)):
        raise ValueError("fixed bank arrays must be finite")

    device = agent.device
    obs = torch.as_tensor(obs_np, dtype=torch.float32, device=device)
    previous = torch.as_tensor(previous_np, dtype=torch.float32, device=device)
    rms_weights = _mu_row_weights(profile_labels, mu_rms, device)
    tv_weights = _mu_row_weights(profile_labels, mu_tv, device)

    critic_before = _state_dict_digest_payload(agent.critic)
    critic_target_before = _state_dict_digest_payload(agent.critic_target)
    actor_targets_before = [_state_dict_digest_payload(target) for target in agent.actor_targets]
    for parameter in agent.critic.parameters():
        parameter.requires_grad_(False)

    optimizers = [
        torch.optim.Adam(actor.parameters(), lr=float(actor_lr)) for actor in agent.actors
    ]
    initial_parameters = [
        torch.cat([parameter.detach().reshape(-1).cpu() for parameter in actor.parameters()])
        for actor in agent.actors
    ]

    def current_actions() -> torch.Tensor:
        augmented = agent._augmented_rows(obs, previous)
        rows = []
        for actor_index in range(AGENT_COUNT):
            raw = agent.actors[actor_index](agent._actor_obs_row(augmented, actor_index))
            start = actor_index * ACTION_DIM
            rows.append(
                project_slew_torch(
                    previous[:, start : start + ACTION_DIM],
                    raw,
                    slew_limit=agent.action_slew_limit,
                )
            )
        return torch.cat(rows, dim=-1)

    with torch.no_grad():
        initial_actions = current_actions().detach().cpu()

    trace: list[dict[str, Any]] = []
    for update_index in range(int(update_steps)):
        augmented = agent._augmented_rows(obs, previous)
        with torch.no_grad():
            baseline_rows = []
            for actor_index in range(AGENT_COUNT):
                raw = agent.actors[actor_index](agent._actor_obs_row(augmented, actor_index))
                start = actor_index * ACTION_DIM
                baseline_rows.append(
                    project_slew_torch(
                        previous[:, start : start + ACTION_DIM],
                        raw,
                        slew_limit=agent.action_slew_limit,
                    )
                )
            baseline = torch.cat(baseline_rows, dim=-1)

        actor_rows: list[dict[str, Any]] = []
        for actor_index, optimizer in enumerate(optimizers):
            parameters = list(agent.actors[actor_index].parameters())
            raw = agent.actors[actor_index](agent._actor_obs_row(augmented, actor_index))
            start = actor_index * ACTION_DIM
            previous_row = previous[:, start : start + ACTION_DIM]
            row = project_slew_torch(previous_row, raw, slew_limit=agent.action_slew_limit)
            q1 = agent._actor_objective(obs, actor_index, row, baseline_actions=baseline)
            value_samples = -(q1[:, 0] + float(agent.lagrange) * q1[:, 1])
            rms_samples = torch.mean(row**2, dim=1)
            tv_samples = torch.mean(torch.abs(row - previous_row), dim=1)
            value_loss = torch.mean(value_samples)
            rms_loss = torch.mean(rms_samples)
            tv_loss = torch.mean(tv_samples)
            weighted_rms_loss = torch.mean(rms_weights * rms_samples)
            weighted_tv_loss = torch.mean(tv_weights * tv_samples)
            total_loss = value_loss + weighted_rms_loss + weighted_tv_loss

            grad_value = _flat_grads(value_loss, parameters, retain_graph=True)
            grad_rms = _flat_grads(rms_loss, parameters, retain_graph=True)
            grad_tv = _flat_grads(tv_loss, parameters, retain_graph=True)
            grad_weighted_rms = _flat_grads(weighted_rms_loss, parameters, retain_graph=True)
            grad_weighted_tv = _flat_grads(weighted_tv_loss, parameters, retain_graph=True)
            grad_total = _flat_grads(total_loss, parameters, retain_graph=True)
            gradient_vectors = (
                grad_value,
                grad_rms,
                grad_tv,
                grad_weighted_rms,
                grad_weighted_tv,
                grad_total,
            )
            if not all(torch.isfinite(vector).all() for vector in gradient_vectors):
                raise FloatingPointError("nonfinite fixed-bank actor gradient")
            if not all(
                torch.isfinite(loss)
                for loss in (
                    value_loss,
                    rms_loss,
                    tv_loss,
                    weighted_rms_loss,
                    weighted_tv_loss,
                    total_loss,
                )
            ):
                raise FloatingPointError("nonfinite fixed-bank actor loss")
            active = (
                (raw > previous_row - float(agent.action_slew_limit))
                & (raw < previous_row + float(agent.action_slew_limit))
                & (raw > -1.0)
                & (raw < 1.0)
            )
            actor_rows.append(
                {
                    "actor_index": actor_index,
                    "losses": {
                        "value": float(value_loss.detach().cpu()),
                        "rms_unweighted": float(rms_loss.detach().cpu()),
                        "tv_unweighted": float(tv_loss.detach().cpu()),
                        "rms_weighted": float(weighted_rms_loss.detach().cpu()),
                        "tv_weighted": float(weighted_tv_loss.detach().cpu()),
                        "total": float(total_loss.detach().cpu()),
                    },
                    "gradient_norms": {
                        "value": _norm(grad_value),
                        "rms_unweighted": _norm(grad_rms),
                        "tv_unweighted": _norm(grad_tv),
                        "rms_weighted": _norm(grad_weighted_rms),
                        "tv_weighted": _norm(grad_weighted_tv),
                        "total": _norm(grad_total),
                    },
                    "gradient_cosines": {
                        "value_vs_rms_weighted": _cosine(grad_value, grad_weighted_rms),
                        "value_vs_tv_weighted": _cosine(grad_value, grad_weighted_tv),
                        "rms_vs_tv_weighted": _cosine(grad_weighted_rms, grad_weighted_tv),
                    },
                    "gradient_gram": [
                        [
                            float(torch.dot(left, right).detach().cpu())
                            for right in (grad_value, grad_weighted_rms, grad_weighted_tv)
                        ]
                        for left in (grad_value, grad_weighted_rms, grad_weighted_tv)
                    ],
                    "projection_active_fraction": float(
                        active.to(torch.float32).mean().detach().cpu()
                    ),
                }
            )
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
        trace.append({"update_index": update_index, "actors": actor_rows})

    with torch.no_grad():
        final_actions = current_actions().detach().cpu()
    final_parameters = [
        torch.cat([parameter.detach().reshape(-1).cpu() for parameter in actor.parameters()])
        for actor in agent.actors
    ]
    parameter_deltas = []
    for initial, final in zip(initial_parameters, final_parameters):
        denominator = max(float(torch.linalg.vector_norm(initial)), 1.0e-20)
        parameter_deltas.append(float(torch.linalg.vector_norm(final - initial)) / denominator)
    action_delta = final_actions - initial_actions
    action_denominator = max(float(torch.sqrt(torch.mean(initial_actions**2))), 1.0e-20)

    critic_after = _state_dict_digest_payload(agent.critic)
    critic_target_after = _state_dict_digest_payload(agent.critic_target)
    actor_targets_after = [_state_dict_digest_payload(target) for target in agent.actor_targets]
    frozen_unchanged = {
        "critic": state_dict_equal(critic_before, critic_after),
        "critic_target": state_dict_equal(critic_target_before, critic_target_after),
        "actor_targets": all(
            state_dict_equal(before, after)
            for before, after in zip(actor_targets_before, actor_targets_after)
        ),
    }
    return {
        "trace": trace,
        "initial_actions": initial_actions.numpy(),
        "final_actions": final_actions.numpy(),
        "parameter_relative_deltas": parameter_deltas,
        "action_rms_delta": float(torch.sqrt(torch.mean(action_delta**2))),
        "action_relative_rms_delta": float(
            torch.sqrt(torch.mean(action_delta**2)) / action_denominator
        ),
        "frozen_networks_unchanged": frozen_unchanged,
    }


def clone_agent(agent: Any) -> Any:
    """Deep-copy helper kept explicit for rehearsal tests."""

    return copy.deepcopy(agent)


__all__ = [
    "balanced_dual_replay",
    "clone_agent",
    "fixed_bank_actor_intervention",
    "projected_dual_step",
    "replay_projected_dual",
    "state_dict_equal",
]
