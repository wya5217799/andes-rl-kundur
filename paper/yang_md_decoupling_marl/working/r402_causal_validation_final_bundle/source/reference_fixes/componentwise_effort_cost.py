"""Executed-action effort terms for the prospective R402 causal interventions.

The historical CD objective had no action magnitude/TV term, while the scalar
arm penalized squared global means of decoded parameter changes.  Those means
can cancel under differential actions.  The functions below operate on the
post-slew executed normalized action and therefore measure the same object used
by the registered RMS/TV guards.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class EffortWeights:
    magnitude: float = 1.0
    increment_l1: float = 1.0

    def validate(self) -> None:
        if self.magnitude < 0.0 or self.increment_l1 < 0.0:
            raise ValueError("effort weights must be nonnegative")


def _prepend_zero_np(actions: np.ndarray) -> np.ndarray:
    return np.concatenate([np.zeros_like(actions[..., :1, :, :]), actions], axis=-3)


def effort_components_np(executed_actions: np.ndarray) -> dict[str, np.ndarray]:
    """Return per-trajectory magnitude and increment effort.

    Accepted shape is (..., time, agents, components).  The initial previous
    action is zero, matching the historical projector reset.
    """

    action = np.asarray(executed_actions, dtype=np.float64)
    if action.ndim < 3 or action.shape[-1] != 2:
        raise ValueError("actions must have shape (..., time, agents, 2)")
    if not np.all(np.isfinite(action)):
        raise ValueError("actions must be finite")
    delta = np.diff(_prepend_zero_np(action), axis=-3)
    return {
        "mean_squared_magnitude": np.mean(action**2, axis=(-3, -2, -1)),
        "mean_absolute_increment": np.mean(np.abs(delta), axis=(-3, -2, -1)),
        "rms": np.sqrt(np.mean(action**2, axis=(-3, -2, -1))),
        "total_variation": np.sum(np.mean(np.abs(delta), axis=(-2, -1)), axis=-1),
    }


def effort_loss_torch(
    executed_actions: torch.Tensor,
    *,
    magnitude_reference: float,
    tv_reference: float,
    weights: EffortWeights = EffortWeights(),
) -> torch.Tensor:
    """Differentiable normalized effort loss for a batch of trajectories.

    Input shape: (batch, time, agents, 2).  Reference scales must be frozen on
    a calibration bank before the causal experiment, not selected on outcomes.
    """

    weights.validate()
    if executed_actions.ndim != 4 or executed_actions.shape[-1] != 2:
        raise ValueError("executed_actions must have shape (batch, time, agents, 2)")
    if magnitude_reference <= 0.0 or tv_reference <= 0.0:
        raise ValueError("reference scales must be positive")
    zero = torch.zeros_like(executed_actions[:, :1])
    increments = torch.diff(torch.cat([zero, executed_actions], dim=1), dim=1)
    magnitude = torch.mean(executed_actions.square(), dim=(1, 2, 3))
    variation = torch.sum(torch.mean(torch.abs(increments), dim=(2, 3)), dim=1)
    return (
        weights.magnitude * magnitude / float(magnitude_reference)
        + weights.increment_l1 * variation / float(tv_reference)
    )


__all__ = ["EffortWeights", "effort_components_np", "effort_loss_torch"]
