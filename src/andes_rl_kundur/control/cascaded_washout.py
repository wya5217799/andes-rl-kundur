"""Second-order washout seam for feasibility-native VSG coordination.

The filter is two identical discrete first-order high-pass stages in series::

    y[k] = alpha * (y[k-1] + x[k] - x[k-1])

Cascading the stages creates a mechanism distinct from the stopped R376-R379
first-order family.  This module only supplies the stateful filter; it does not
select gains, launch ANDES, or establish a scientific result.
"""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Mapping

import numpy as np

from andes_rl_kundur.control.feasibility_native_deterministic import (
    ACTION_CLIP,
    _frequency_vector,
    _laplacian,
)


class CascadedWashout:
    """Two-stage vector washout with deterministic reset semantics."""

    order = 2

    def __init__(self, *, device_count: int, alpha: float) -> None:
        self.device_count = int(device_count)
        self.alpha = float(alpha)
        if self.device_count < 1:
            raise ValueError("device_count must be positive")
        if not np.isfinite(self.alpha) or not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie inside (0, 1)")
        self.reset()

    def reset(self) -> None:
        """Clear both stages so independent episodes cannot share state."""
        shape = (self.order, self.device_count)
        self._state = np.zeros(shape, dtype=float)
        self._previous_input = np.zeros(shape, dtype=float)

    def step(self, values: Sequence[float] | np.ndarray) -> np.ndarray:
        """Advance both stages by one sample and return a fresh vector."""
        stage_input = np.asarray(values, dtype=float)
        if (
            stage_input.shape != (self.device_count,)
            or not np.all(np.isfinite(stage_input))
        ):
            raise ValueError("values must be a finite device vector")

        for stage in range(self.order):
            output = self.alpha * (
                self._state[stage]
                + stage_input
                - self._previous_input[stage]
            )
            self._state[stage] = output
            self._previous_input[stage] = stage_input
            stage_input = output
        return stage_input.copy()


class CascadedHPDampingDistributedController:
    """Dynamic-average common control plus second-order mutual damping."""

    architecture = "distributed_cascaded_hp_damping"

    def __init__(
        self,
        *,
        adjacency: Mapping[int, Sequence[int]],
        device_count: int,
        nominal_frequency_hz: float,
        kp_n_per_hz: float,
        ki_n_per_hz_s: float,
        ks_n_per_hz: float,
        kc_n_per_s: float,
        highpass_alpha: float,
        action_clip: float = ACTION_CLIP,
    ) -> None:
        self.device_count = int(device_count)
        self.nominal_frequency_hz = float(nominal_frequency_hz)
        self.kp_n = float(kp_n_per_hz)
        self.ki_n = float(ki_n_per_hz_s)
        self.ks_n = float(ks_n_per_hz)
        self.kc_n = float(kc_n_per_s)
        self.action_clip = float(action_clip)
        if min(self.kp_n, self.ki_n, self.ks_n, self.kc_n) < 0.0:
            raise ValueError("controller gains must be non-negative")
        if not 0.0 < self.action_clip <= 1.0:
            raise ValueError("action_clip must lie inside (0, 1]")
        self.laplacian = _laplacian(
            adjacency,
            device_count=self.device_count,
        )
        self._washout = CascadedWashout(
            device_count=self.device_count,
            alpha=highpass_alpha,
        )
        self.reset()

    def reset(self) -> None:
        self._common_estimate: np.ndarray | None = None
        self._previous_error: np.ndarray | None = None
        self._integral = np.zeros(self.device_count, dtype=float)
        self._was_clipped = np.zeros(self.device_count, dtype=bool)
        self._washout.reset()

    def act(
        self,
        *,
        frequencies_hz: Sequence[float] | np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray:
        frequency = _frequency_vector(
            frequencies_hz,
            device_count=self.device_count,
        )
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")

        error = self.nominal_frequency_hz - frequency
        if self._common_estimate is None:
            estimate = error.copy()
        else:
            assert self._previous_error is not None
            estimate = (
                self._common_estimate
                + error
                - self._previous_error
                - self.kc_n
                * dt
                * (self.laplacian @ self._common_estimate)
            )
        self._integral = self._integral + np.where(
            self._was_clipped,
            0.0,
            self.ki_n * estimate * dt,
        )
        common = self.kp_n * estimate + self._integral
        differential_message = self.laplacian @ frequency
        sync = -self.ks_n * self._washout.step(differential_message)
        raw = common + sync
        action = np.clip(raw, -self.action_clip, self.action_clip)

        self._was_clipped = ~np.isclose(raw, action, rtol=0.0, atol=1.0e-12)
        self._common_estimate = estimate
        self._previous_error = error.copy()
        return action.copy()
