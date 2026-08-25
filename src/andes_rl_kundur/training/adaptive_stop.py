"""Fail-closed adaptive stopping for stochastic training curves.

Motivation:
    A flat loss at one checkpoint is not evidence of convergence.  This module
    concentrates the full stopping policy behind one small interface so future
    round runners do not reimplement windowing, patience, probe, and numerical
    health rules.  The default policy is calibrated for the corrected-card SAC
    family but is not self-authorizing: a formal round must freeze its config
    before execution and validate physical checkpoint equivalence separately.

Usage:
    monitor = AdaptiveStopMonitor(AdaptiveStopConfig())
    decision = monitor.observe(
        interaction_steps=32_000,
        curves=curves,
        action_probe_drift=0.01,
        tds_failures=0,
    )
    if decision.should_stop:
        save_final_checkpoint(reason=decision.reason)

Failure modes:
    Missing, short, or non-finite histories fail closed and reset patience.
    Duplicate or off-grid observations do not advance patience.  Reaching
    ``max_steps`` stops because the frozen budget is exhausted, but reports
    ``converged=False`` unless the convergence gates also passed.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AdaptiveStopConfig:
    """Frozen policy for one training family."""

    min_steps: int = 30_000
    max_steps: int = 43_200
    check_interval: int = 2_000
    window_updates: int = 2_000
    required_checks: int = 3
    loss_relative_tolerance: float = 0.10
    alpha_relative_tolerance: float = 0.05
    alpha_floor: float = 0.005
    action_probe_drift_tolerance: float = 0.02
    gradient_relative_tolerance: float = 0.25
    gradient_floor: float = 1.0e-6

    def __post_init__(self) -> None:
        if self.min_steps < 1 or self.max_steps < self.min_steps:
            raise ValueError("require 1 <= min_steps <= max_steps")
        if self.check_interval < 1 or self.window_updates < 10:
            raise ValueError("check_interval and window_updates must be positive")
        if self.required_checks < 1:
            raise ValueError("required_checks must be positive")
        for name in (
            "loss_relative_tolerance",
            "alpha_relative_tolerance",
            "action_probe_drift_tolerance",
            "gradient_relative_tolerance",
        ):
            value = float(getattr(self, name))
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be in (0, 1)")
        if self.alpha_floor <= 0.0 or self.gradient_floor <= 0.0:
            raise ValueError("floors must be positive")

    @property
    def confirmation_span_steps(self) -> int:
        """Steps between the first and last qualifying patience checks."""

        return (self.required_checks - 1) * self.check_interval


@dataclass(frozen=True)
class StopDecision:
    """One auditable adaptive-stop decision."""

    should_stop: bool
    converged: bool
    checked: bool
    reason: str
    interaction_steps: int
    consecutive_passes: int
    evidence: Mapping[str, Any]


def _median_abs_log_ratio(values: Sequence[float], width: int) -> tuple[float, float, float]:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < 2 * width:
        raise ValueError("history shorter than two complete windows")
    tail = array[-2 * width :]
    if not np.all(np.isfinite(tail)):
        raise ValueError("history contains non-finite values")
    previous = float(np.median(np.abs(tail[:width])))
    current = float(np.median(np.abs(tail[width:])))
    ratio = abs(math.log(max(current, 1.0e-12) / max(previous, 1.0e-12)))
    return previous, current, ratio


class AdaptiveStopMonitor:
    """Stateful patience counter with fail-closed curve evaluation."""

    REQUIRED_CURVES = ("actor_loss", "critic_loss", "alpha", "actor_grad_norm")

    def __init__(self, config: AdaptiveStopConfig) -> None:
        self.config = config
        self._consecutive_passes = 0
        self._last_checked_step: int | None = None

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "config": asdict(self.config),
            "consecutive_passes": self._consecutive_passes,
            "last_checked_step": self._last_checked_step,
        }

    @classmethod
    def from_state_dict(cls, state: Mapping[str, Any]) -> AdaptiveStopMonitor:
        if state.get("schema_version") != 1:
            raise ValueError("unsupported adaptive-stop state schema")
        monitor = cls(AdaptiveStopConfig(**dict(state["config"])))
        monitor._consecutive_passes = int(state["consecutive_passes"])
        last = state.get("last_checked_step")
        monitor._last_checked_step = None if last is None else int(last)
        return monitor

    def observe(
        self,
        *,
        interaction_steps: int,
        curves: Mapping[str, Sequence[float]],
        action_probe_drift: float,
        tds_failures: int,
    ) -> StopDecision:
        """Evaluate one checkpoint and update patience.

        Callers may invoke this on every interaction step.  Only the frozen
        check grid advances patience; all other calls return ``checked=False``.
        """

        step = int(interaction_steps)
        if step < self.config.min_steps:
            return self._decision(False, False, False, "minimum_steps", step, {})
        if (
            step != self.config.max_steps
            and (step - self.config.min_steps) % self.config.check_interval
        ):
            return self._decision(False, False, False, "off_check_grid", step, {})
        if self._last_checked_step == step:
            return self._decision(False, False, False, "duplicate_check", step, {})

        self._last_checked_step = step
        evidence: dict[str, Any] = {
            "tds_failures": int(tds_failures),
            "action_probe_drift": float(action_probe_drift),
        }
        passed = int(tds_failures) == 0 and math.isfinite(action_probe_drift)
        passed = passed and action_probe_drift <= self.config.action_probe_drift_tolerance
        try:
            for name in self.REQUIRED_CURVES:
                previous, current, ratio = _median_abs_log_ratio(
                    curves[name], self.config.window_updates
                )
                evidence[name] = {
                    "previous_median_abs": previous,
                    "current_median_abs": current,
                    "absolute_log_ratio": ratio,
                }
            loss_limit = math.log1p(self.config.loss_relative_tolerance)
            passed = passed and all(
                evidence[name]["absolute_log_ratio"] <= loss_limit
                for name in ("actor_loss", "critic_loss")
            )
            alpha = evidence["alpha"]
            alpha_at_floor = (
                alpha["previous_median_abs"] <= self.config.alpha_floor * 1.01
                and alpha["current_median_abs"] <= self.config.alpha_floor * 1.01
            )
            passed = passed and (
                alpha_at_floor
                or alpha["absolute_log_ratio"] <= math.log1p(self.config.alpha_relative_tolerance)
            )
            gradient = evidence["actor_grad_norm"]
            passed = passed and (
                gradient["current_median_abs"] >= self.config.gradient_floor
                and gradient["absolute_log_ratio"]
                <= math.log1p(self.config.gradient_relative_tolerance)
            )
            evidence["alpha_at_floor"] = alpha_at_floor
        except (KeyError, TypeError, ValueError) as exc:
            passed = False
            evidence["history_error"] = str(exc)

        self._consecutive_passes = self._consecutive_passes + 1 if passed else 0
        converged = self._consecutive_passes >= self.config.required_checks
        if converged:
            reason = "converged"
        elif step >= self.config.max_steps:
            reason = "max_steps"
        else:
            reason = "patience" if passed else "gate_failed"
        return self._decision(
            converged or step >= self.config.max_steps,
            converged,
            True,
            reason,
            step,
            evidence,
        )

    def _decision(
        self,
        should_stop: bool,
        converged: bool,
        checked: bool,
        reason: str,
        interaction_steps: int,
        evidence: Mapping[str, Any],
    ) -> StopDecision:
        return StopDecision(
            should_stop=should_stop,
            converged=converged,
            checked=checked,
            reason=reason,
            interaction_steps=interaction_steps,
            consecutive_passes=self._consecutive_passes,
            evidence=evidence,
        )
