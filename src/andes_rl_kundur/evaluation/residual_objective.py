"""Auditable physical objective terms for bounded residual VSG control.

The objective separates physical common-mode restoration, differential
synchronisation, learned-residual effort, and learned-residual movement.
Every term is dimensionless and lower is better.  The module is independent
of ANDES so the same arithmetic can be tested before it is connected to a
training environment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ResidualObjectiveConfig:
    """Fixed normalization and scalarization for the residual objective."""

    frequency_band_hz: float = 0.05
    residual_effort_normalizer: float = 2.0
    residual_variation_normalizer: float = 4.0
    common_weight: float = 1.0
    differential_weight: float = 1.0
    residual_effort_weight: float = 1.0
    residual_variation_weight: float = 1.0

    def __post_init__(self) -> None:
        positive = {
            "frequency_band_hz": self.frequency_band_hz,
            "residual_effort_normalizer": self.residual_effort_normalizer,
            "residual_variation_normalizer": self.residual_variation_normalizer,
        }
        for name, value in positive.items():
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        weights = {
            "common_weight": self.common_weight,
            "differential_weight": self.differential_weight,
            "residual_effort_weight": self.residual_effort_weight,
            "residual_variation_weight": self.residual_variation_weight,
        }
        for name, value in weights.items():
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")

    def to_dict(self) -> dict[str, float]:
        return {key: float(value) for key, value in asdict(self).items()}


def _frequency_vector(delta_f_physical_hz: Any) -> np.ndarray:
    values = np.asarray(delta_f_physical_hz, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("delta_f_physical_hz must be a non-empty 1-D vector")
    if not np.all(np.isfinite(values)):
        raise ValueError("delta_f_physical_hz contains non-finite values")
    return values


def _residual_matrix(residual_actions: Any, *, n_agents: int | None = None) -> np.ndarray:
    actions = np.asarray(residual_actions, dtype=float)
    if actions.ndim != 2 or actions.shape[1] != 2 or actions.shape[0] == 0:
        raise ValueError("residual_actions must have shape [agent, 2]")
    if n_agents is not None and actions.shape[0] != n_agents:
        raise ValueError(
            f"expected residual actions for {n_agents} agents, got {actions.shape[0]}"
        )
    if not np.all(np.isfinite(actions)):
        raise ValueError("residual_actions contains non-finite values")
    if np.any(np.abs(actions) > 1.0 + 1e-7):
        raise ValueError("residual_actions must remain inside [-1, 1]")
    return np.clip(actions, -1.0, 1.0)


def frequency_mode_terms(
    delta_f_physical_hz: Any,
    *,
    config: ResidualObjectiveConfig | None = None,
) -> dict[str, float]:
    """Return common and differential physical-frequency terms for one step."""

    cfg = config or ResidualObjectiveConfig()
    delta_f = _frequency_vector(delta_f_physical_hz)
    common_hz = float(np.mean(delta_f))
    differential_mse_hz2 = float(np.mean(np.square(delta_f - common_hz)))
    common = abs(common_hz) / cfg.frequency_band_hz
    differential = differential_mse_hz2 / cfg.frequency_band_hz**2
    return {
        "common_mode_hz": common_hz,
        "common_abs_hz": abs(common_hz),
        "differential_mse_hz2": differential_mse_hz2,
        "common": float(common),
        "differential": float(differential),
    }


def residual_action_terms(
    residual_actions: Any,
    *,
    previous_residual_actions: Any | None = None,
    config: ResidualObjectiveConfig | None = None,
) -> dict[str, float]:
    """Return residual-specific effort and movement terms for one step."""

    cfg = config or ResidualObjectiveConfig()
    actions = _residual_matrix(residual_actions)
    effort_l1 = float(np.mean(np.sum(np.abs(actions), axis=1)))
    if previous_residual_actions is None:
        variation_l1 = 0.0
    else:
        previous = _residual_matrix(
            previous_residual_actions,
            n_agents=actions.shape[0],
        )
        variation_l1 = float(
            np.mean(np.sum(np.abs(actions - previous), axis=1))
        )
    return {
        "residual_effort_l1": effort_l1,
        "residual_variation_l1": variation_l1,
        "residual_effort": effort_l1 / cfg.residual_effort_normalizer,
        "residual_variation": variation_l1 / cfg.residual_variation_normalizer,
    }


def residual_objective_terms(
    delta_f_physical_hz: Any,
    residual_actions: Any,
    *,
    previous_residual_actions: Any | None = None,
    config: ResidualObjectiveConfig | None = None,
) -> dict[str, float]:
    """Return all four terms and their fixed weighted scalar loss."""

    cfg = config or ResidualObjectiveConfig()
    frequency = frequency_mode_terms(delta_f_physical_hz, config=cfg)
    residual = residual_action_terms(
        residual_actions,
        previous_residual_actions=previous_residual_actions,
        config=cfg,
    )
    total = (
        cfg.common_weight * frequency["common"]
        + cfg.differential_weight * frequency["differential"]
        + cfg.residual_effort_weight * residual["residual_effort"]
        + cfg.residual_variation_weight * residual["residual_variation"]
    )
    return {
        **frequency,
        **residual,
        "total": float(total),
    }


def summarise_frequency_objective(
    delta_f_physical_hz: Any,
    *,
    sample_interval_s: float,
    config: ResidualObjectiveConfig | None = None,
) -> dict[str, float | int]:
    """Aggregate frequency terms while retaining physical endpoint identities."""

    cfg = config or ResidualObjectiveConfig()
    values = np.asarray(delta_f_physical_hz, dtype=float)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError(
            "delta_f_physical_hz must have shape [time, agent] with non-zero axes"
        )
    if not np.all(np.isfinite(values)):
        raise ValueError("delta_f_physical_hz contains non-finite values")
    if not np.isfinite(sample_interval_s) or sample_interval_s <= 0.0:
        raise ValueError("sample_interval_s must be finite and positive")

    common = np.mean(values, axis=1)
    common_abs = np.abs(common)
    differential_mse = np.mean(np.square(values - common[:, None]), axis=1)
    common_normalized = common_abs / cfg.frequency_band_hz
    differential_normalized = differential_mse / cfg.frequency_band_hz**2
    return {
        "n_steps": int(values.shape[0]),
        "n_agents": int(values.shape[1]),
        "vsg_mean_iae_hz_s": float(np.sum(common_abs) * sample_interval_s),
        "normalized_sync_loss_hz2": float(np.mean(differential_mse)),
        "common_normalized_mean": float(np.mean(common_normalized)),
        "common_normalized_sum": float(np.sum(common_normalized)),
        "differential_normalized_mean": float(
            np.mean(differential_normalized)
        ),
        "frequency_scalar_mean": float(
            cfg.common_weight * np.mean(common_normalized)
            + cfg.differential_weight * np.mean(differential_normalized)
        ),
    }


def summarise_residual_objective(
    residual_actions: Any,
    *,
    config: ResidualObjectiveConfig | None = None,
) -> dict[str, float | int]:
    """Aggregate residual effort and inter-step movement over a trajectory."""

    cfg = config or ResidualObjectiveConfig()
    actions = np.asarray(residual_actions, dtype=float)
    if (
        actions.ndim != 3
        or actions.shape[0] == 0
        or actions.shape[1] == 0
        or actions.shape[2] != 2
    ):
        raise ValueError("residual_actions must have shape [time, agent, 2]")
    if not np.all(np.isfinite(actions)):
        raise ValueError("residual_actions contains non-finite values")
    if np.any(np.abs(actions) > 1.0 + 1e-7):
        raise ValueError("residual_actions must remain inside [-1, 1]")
    actions = np.clip(actions, -1.0, 1.0)

    effort = np.mean(np.sum(np.abs(actions), axis=2), axis=1)
    variation = np.zeros(actions.shape[0], dtype=float)
    if actions.shape[0] > 1:
        variation[1:] = np.mean(
            np.sum(np.abs(np.diff(actions, axis=0)), axis=2),
            axis=1,
        )
    effort_normalized = effort / cfg.residual_effort_normalizer
    variation_normalized = variation / cfg.residual_variation_normalizer
    return {
        "n_steps": int(actions.shape[0]),
        "n_agents": int(actions.shape[1]),
        "residual_effort_l1_mean": float(np.mean(effort)),
        "residual_total_variation": float(np.sum(variation)),
        "residual_effort_normalized_mean": float(np.mean(effort_normalized)),
        "residual_variation_normalized_mean": float(
            np.mean(variation_normalized)
        ),
        "residual_scalar_mean": float(
            cfg.residual_effort_weight * np.mean(effort_normalized)
            + cfg.residual_variation_weight * np.mean(variation_normalized)
        ),
    }
