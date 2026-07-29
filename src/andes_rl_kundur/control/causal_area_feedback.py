"""Prospectively bounded causal comparator for R279.

The controller uses only the area-mean frequency and RoCoF differences already
present in the R278 joint observation. It emits four synthetic votes whose
existing R278 projector executes exactly one scalar ``q`` on
``[1, 1, -1, -1]``. This is a causal classical comparator, not a reproduction
of a particular mutual-damping paper.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from andes_rl_kundur.control.area_inertia_residual import AREA_PATTERN


@dataclass(frozen=True)
class CausalAreaFeedbackContract:
    """Frozen gain and normalization contract for one R279 candidate."""

    k_frequency: float
    k_rocof: float
    frequency_scale_hz: float = 0.05
    rocof_scale_hz_s: float = 0.5
    q_max: float = 0.25
    q_slew_max: float = 0.25
    active_steps: int = 15
    control_dt_seconds: float = 0.2

    def __post_init__(self) -> None:
        if self.k_frequency < 0.0 or self.k_rocof < 0.0:
            raise ValueError("causal gains must be non-negative")
        if self.k_frequency == 0.0 and self.k_rocof == 0.0:
            raise ValueError("at least one causal gain must be non-zero")
        if self.frequency_scale_hz <= 0.0 or self.rocof_scale_hz_s <= 0.0:
            raise ValueError("normalization scales must be positive")
        if self.q_max <= 0.0 or not 0.0 < self.q_slew_max <= 2.0 * self.q_max:
            raise ValueError("invalid q magnitude or slew contract")
        if self.active_steps <= 0:
            raise ValueError("active_steps must be positive")

    @property
    def name(self) -> str:
        return (
            f"causal_kf_{self.k_frequency:g}_kr_{self.k_rocof:g}"
            .replace(".", "p")
        )

    def telemetry(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "schema_version": 1,
                "name": self.name,
                "law": (
                    "q_target=q_max*tanh(-(k_frequency*delta_f_ab/"
                    "frequency_scale_hz+k_rocof*delta_rocof_ab/"
                    "rocof_scale_hz_s))"
                ),
                "available_information": "current R278 joint observation only",
                "executed_residual": "q*[1,1,-1,-1]",
            }
        )
        return payload


R279_CAUSAL_GAIN_GRID: tuple[tuple[float, float], ...] = (
    (0.25, 0.0),
    (0.5, 0.0),
    (1.0, 0.0),
    (0.0, 0.25),
    (0.0, 0.5),
    (0.0, 1.0),
    (0.25, 0.25),
    (0.5, 0.25),
    (0.5, 0.5),
)


def r279_causal_contracts() -> tuple[CausalAreaFeedbackContract, ...]:
    """Return the prospectively fixed nine-candidate development family."""
    return tuple(
        CausalAreaFeedbackContract(k_frequency=kf, k_rocof=kr)
        for kf, kr in R279_CAUSAL_GAIN_GRID
    )


def _observation_array(
    observations: Mapping[int, np.ndarray] | np.ndarray,
) -> np.ndarray:
    if isinstance(observations, Mapping):
        if set(observations) != set(range(4)):
            raise ValueError("observations must contain exactly agents 0..3")
        array = np.stack(
            [np.asarray(observations[index], dtype=np.float32) for index in range(4)]
        )
    else:
        array = np.asarray(observations, dtype=np.float32)
    if array.shape != (4, 7):
        raise ValueError(f"observations must have shape (4, 7), got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError("observations must be finite")
    return array


def area_feedback_features(
    observations: Mapping[int, np.ndarray] | np.ndarray,
) -> tuple[float, float]:
    """Return physical ``Delta f_AB`` and ``Delta RoCoF_AB`` from R278 obs."""
    obs = _observation_array(observations)
    delta_f_hz = obs[:, 0].astype(np.float64) * 0.1
    rocof_hz_s = obs[:, 3].astype(np.float64) * 0.5
    delta_f_ab = float(np.mean(delta_f_hz[:2]) - np.mean(delta_f_hz[2:]))
    delta_rocof_ab = float(np.mean(rocof_hz_s[:2]) - np.mean(rocof_hz_s[2:]))
    return delta_f_ab, delta_rocof_ab


class CausalAreaFeedbackController:
    """Memoryless negative feedback followed by the existing q projection."""

    def __init__(self, contract: CausalAreaFeedbackContract) -> None:
        self.contract = contract

    def reset(self) -> None:
        """Reset hook for a common controller interface; no hidden state exists."""

    def normalized_target(
        self,
        observations: Mapping[int, np.ndarray] | np.ndarray,
    ) -> float:
        delta_f_ab, delta_rocof_ab = area_feedback_features(observations)
        drive = -(
            self.contract.k_frequency
            * delta_f_ab
            / self.contract.frequency_scale_hz
            + self.contract.k_rocof
            * delta_rocof_ab
            / self.contract.rocof_scale_hz_s
        )
        return float(np.tanh(drive))

    def select_raw_actions(
        self,
        observations: Mapping[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool = True,
    ) -> np.ndarray:
        if not deterministic:
            raise ValueError("causal comparator has no stochastic execution mode")
        target = self.normalized_target(observations)
        return (AREA_PATTERN * np.float32(target)).astype(np.float32)
