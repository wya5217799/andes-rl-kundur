"""Fixed scheduled action basis for controller-agnostic attainability tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.hybrid import (
    ActionFn,
    proportional_damping_action_fn,
)

AREA_PATTERN = np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)
COMMON_PATTERN = np.ones(4, dtype=np.float32)


@dataclass(frozen=True)
class ScheduledBasisSpec:
    """One fixed early-transient residual direction."""

    name: str
    component: str
    pattern: tuple[float, float, float, float]

    def residual_matrix(self, amplitude: float) -> np.ndarray:
        if self.component not in {"M", "D"}:
            raise ValueError(f"unsupported component: {self.component!r}")
        if not np.isfinite(amplitude) or not 0.0 <= amplitude <= 1.0:
            raise ValueError("amplitude must be finite and in [0, 1]")
        residual = np.zeros((4, 2), dtype=np.float32)
        column = 0 if self.component == "M" else 1
        residual[:, column] = amplitude * np.asarray(
            self.pattern,
            dtype=np.float32,
        )
        return residual


CANDIDATE_SPECS: tuple[ScheduledBasisSpec, ...] = (
    ScheduledBasisSpec("common_M_pos", "M", (1.0, 1.0, 1.0, 1.0)),
    ScheduledBasisSpec("common_M_neg", "M", (-1.0, -1.0, -1.0, -1.0)),
    ScheduledBasisSpec("common_D_pos", "D", (1.0, 1.0, 1.0, 1.0)),
    ScheduledBasisSpec("common_D_neg", "D", (-1.0, -1.0, -1.0, -1.0)),
    ScheduledBasisSpec("area_M_pos", "M", (1.0, 1.0, -1.0, -1.0)),
    ScheduledBasisSpec("area_M_neg", "M", (-1.0, -1.0, 1.0, 1.0)),
    ScheduledBasisSpec("area_D_pos", "D", (1.0, 1.0, -1.0, -1.0)),
    ScheduledBasisSpec("area_D_neg", "D", (-1.0, -1.0, 1.0, 1.0)),
)


def candidate_contract(
    *,
    amplitude: float,
    active_steps: int,
    k_droop: float,
) -> dict[str, Any]:
    if not np.isfinite(amplitude) or not 0.0 <= amplitude <= 1.0:
        raise ValueError("amplitude must be finite and in [0, 1]")
    if not isinstance(active_steps, int) or active_steps <= 0:
        raise ValueError("active_steps must be a positive integer")
    proportional_damping_action_fn(k_droop)
    return {
        "composition": "clip(droop + scheduled_residual, -1, 1)",
        "amplitude": float(amplitude),
        "active_steps": active_steps,
        "k_droop": float(k_droop),
        "area_of_agent": [1, 1, 2, 2],
        "candidates": [
            {
                "name": spec.name,
                "component": spec.component,
                "pattern": list(spec.pattern),
            }
            for spec in CANDIDATE_SPECS
        ],
    }


@dataclass
class ScheduledBasisResidualController:
    """Add one fixed basis residual to droop for an initial time window."""

    spec: ScheduledBasisSpec
    amplitude: float = 0.25
    active_steps: int = 15
    k_droop: float = 10.0
    clipped_component_count: int = field(default=0, init=False)
    component_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        candidate_contract(
            amplitude=self.amplitude,
            active_steps=self.active_steps,
            k_droop=self.k_droop,
        )

    def __call__(
        self,
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        if n_agents != 4:
            raise ValueError(f"scheduled basis requires 4 agents, got {n_agents}")
        if step == 0:
            self.clipped_component_count = 0
            self.component_count = 0
        prior = proportional_damping_action_fn(self.k_droop)(step, obs, n_agents)
        residual = (
            self.spec.residual_matrix(self.amplitude)
            if step < self.active_steps
            else np.zeros((4, 2), dtype=np.float32)
        )
        actions: dict[int, np.ndarray] = {}
        for i in range(n_agents):
            preclip = np.asarray(prior[i], dtype=np.float32) + residual[i]
            self.clipped_component_count += int(
                np.count_nonzero(np.abs(preclip) > 1.0)
            )
            self.component_count += int(preclip.size)
            actions[i] = np.clip(preclip, -1.0, 1.0).astype(np.float32)
        return actions

    def telemetry(self) -> dict[str, float | int | str]:
        return {
            "candidate": self.spec.name,
            "amplitude": float(self.amplitude),
            "active_steps": self.active_steps,
            "k_droop": float(self.k_droop),
            "executed_clipped_component_fraction": (
                self.clipped_component_count / self.component_count
                if self.component_count
                else 0.0
            ),
        }


def scheduled_basis_action_fn(
    spec: ScheduledBasisSpec,
    *,
    amplitude: float = 0.25,
    active_steps: int = 15,
    k_droop: float = 10.0,
) -> ActionFn:
    return ScheduledBasisResidualController(
        spec=spec,
        amplitude=amplitude,
        active_steps=active_steps,
        k_droop=k_droop,
    )
