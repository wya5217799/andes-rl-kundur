"""Composable action functions for hybrid controller evaluation.

R252 found that the learned R201 controller and classical droop occupy
opposite ends of the project's ``geo``/``cum_rf`` Pareto frontier.  This
module provides the small, reusable seam needed to test controller
composition without changing the environment or the trained checkpoints.

The functions operate in the normalized two-dimensional V4 action space:
``[delta_M_norm, delta_D_norm]`` in ``[-1, 1]``.  They are deliberately
independent of ANDES so their action semantics can be unit-tested on Windows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.paper_path import ActionFn


def _validate_action_maps(
    primary_actions: dict[int, np.ndarray],
    secondary_actions: dict[int, np.ndarray],
    n_agents: int,
) -> None:
    expected = set(range(n_agents))
    if set(primary_actions) != expected:
        raise ValueError("primary controller returned incomplete agent actions")
    if set(secondary_actions) != expected:
        raise ValueError("secondary controller returned incomplete agent actions")


def _blend_action_maps(
    primary_actions: dict[int, np.ndarray],
    secondary_actions: dict[int, np.ndarray],
    *,
    alpha: float,
    n_agents: int,
) -> dict[int, np.ndarray]:
    _validate_action_maps(primary_actions, secondary_actions, n_agents)
    actions: dict[int, np.ndarray] = {}
    for i in range(n_agents):
        first = np.asarray(primary_actions[i], dtype=np.float32)
        second = np.asarray(secondary_actions[i], dtype=np.float32)
        if first.shape != (2,) or second.shape != (2,):
            raise ValueError(
                f"agent {i} actions must both have shape (2,), got {first.shape} and {second.shape}"
            )
        if alpha == 0.0:
            mixed = first
        elif alpha == 1.0:
            mixed = second
        else:
            mixed = first + alpha * (second - first)
        actions[i] = np.clip(mixed, -1.0, 1.0).astype(np.float32)
    return actions


def proportional_damping_action_fn(k_droop: float) -> ActionFn:
    """Return the R85 magnitude-droop law in normalized action space.

    For agent ``i``:

    ``delta_M_norm = 0``
    ``delta_D_norm = clip(k_droop * abs(obs[i][1]), 0, 1)``

    ``obs[i][1]`` is the normalized local frequency deviation used by V4.
    """
    if not np.isfinite(k_droop) or k_droop < 0:
        raise ValueError(f"k_droop must be finite and non-negative, got {k_droop!r}")

    def _fn(
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        del step
        if len(obs) != n_agents:
            raise ValueError(f"expected {n_agents} observations, got {len(obs)}")

        actions: dict[int, np.ndarray] = {}
        for i in range(n_agents):
            if i not in obs:
                raise ValueError(f"observation mapping is missing agent {i}")
            obs_i = np.asarray(obs[i])
            if obs_i.size < 2:
                raise ValueError(f"agent {i} observation must have at least 2 elements")
            delta_d = float(np.clip(k_droop * abs(float(obs_i[1])), 0.0, 1.0))
            actions[i] = np.array([0.0, delta_d], dtype=np.float32)
        return actions

    return _fn


def compose_bounded_droop_residual_actions(
    obs: dict[int, np.ndarray],
    residual_actions: dict[int, np.ndarray],
    *,
    n_agents: int,
    k_droop: float,
    residual_scale: float,
) -> dict[int, np.ndarray]:
    """Compose a bounded learned residual around the R85 droop prior.

    The actor output remains in ``[-1, 1]`` and is interpreted as a residual:

    ``u_exec = clip(u_droop + residual_scale * u_residual, -1, 1)``.

    This pure function is the single source of truth shared by training and
    deterministic evaluation.  It deliberately does not depend on ANDES.
    """
    if not np.isfinite(residual_scale) or not 0.0 <= residual_scale <= 1.0:
        raise ValueError(
            "residual_scale must be finite and in [0, 1], "
            f"got {residual_scale!r}"
        )
    expected = set(range(n_agents))
    if set(obs) != expected:
        raise ValueError(f"expected observations for agents {sorted(expected)}")
    if set(residual_actions) != expected:
        raise ValueError(f"expected residual actions for agents {sorted(expected)}")

    prior_actions = proportional_damping_action_fn(k_droop)(0, obs, n_agents)
    executed: dict[int, np.ndarray] = {}
    for i in range(n_agents):
        residual = np.asarray(residual_actions[i], dtype=np.float32)
        if residual.shape != (2,):
            raise ValueError(
                f"agent {i} residual action must have shape (2,), got {residual.shape}"
            )
        if not np.all(np.isfinite(residual)):
            raise ValueError(f"agent {i} residual action is not finite")
        bounded_residual = np.clip(residual, -1.0, 1.0)
        action = prior_actions[i] + residual_scale * bounded_residual
        executed[i] = np.clip(action, -1.0, 1.0).astype(np.float32)
    return executed


@dataclass
class BoundedDroopResidualController:
    """Residual-aware action function with scenario-local telemetry."""

    residual_controller: ActionFn
    k_droop: float
    residual_scale: float
    residual_linf_history: list[float] = field(default_factory=list, init=False)
    executed_linf_history: list[float] = field(default_factory=list, init=False)
    clipped_component_count: int = field(default=0, init=False)
    component_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        proportional_damping_action_fn(self.k_droop)
        if not np.isfinite(self.residual_scale) or not 0.0 <= self.residual_scale <= 1.0:
            raise ValueError(
                "residual_scale must be finite and in [0, 1], "
                f"got {self.residual_scale!r}"
            )

    def __call__(
        self,
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        if step == 0:
            self.residual_linf_history.clear()
            self.executed_linf_history.clear()
            self.clipped_component_count = 0
            self.component_count = 0
        residual_actions = self.residual_controller(step, obs, n_agents)
        prior_actions = proportional_damping_action_fn(self.k_droop)(step, obs, n_agents)
        for i in range(n_agents):
            residual = np.asarray(residual_actions[i], dtype=np.float32)
            if residual.shape != (2,) or not np.all(np.isfinite(residual)):
                raise ValueError(f"agent {i} residual action must be finite with shape (2,)")
            bounded = np.clip(residual, -1.0, 1.0)
            preclip = prior_actions[i] + self.residual_scale * bounded
            self.residual_linf_history.append(float(np.max(np.abs(bounded))))
            self.executed_linf_history.append(
                float(np.max(np.abs(np.clip(preclip, -1.0, 1.0))))
            )
            self.clipped_component_count += int(np.count_nonzero(np.abs(preclip) > 1.0))
            self.component_count += int(preclip.size)
        return compose_bounded_droop_residual_actions(
            obs,
            residual_actions,
            n_agents=n_agents,
            k_droop=self.k_droop,
            residual_scale=self.residual_scale,
        )

    def telemetry(self) -> dict[str, float | int]:
        n_values = len(self.residual_linf_history)
        return {
            "n_agent_steps": n_values,
            "residual_scale": self.residual_scale,
            "k_droop": self.k_droop,
            "residual_linf_mean": (
                float(np.mean(self.residual_linf_history)) if n_values else 0.0
            ),
            "residual_linf_max": (
                float(np.max(self.residual_linf_history)) if n_values else 0.0
            ),
            "executed_linf_max": (
                float(np.max(self.executed_linf_history)) if n_values else 0.0
            ),
            "executed_clipped_component_fraction": (
                self.clipped_component_count / self.component_count
                if self.component_count
                else 0.0
            ),
        }


def bounded_droop_residual_action_fn(
    residual_controller: ActionFn,
    *,
    k_droop: float,
    residual_scale: float,
) -> BoundedDroopResidualController:
    """Wrap an actor action function with the training-time residual contract."""
    return BoundedDroopResidualController(
        residual_controller=residual_controller,
        k_droop=k_droop,
        residual_scale=residual_scale,
    )


def convex_blend_action_fn(
    primary: ActionFn,
    secondary: ActionFn,
    *,
    alpha: float,
) -> ActionFn:
    """Blend two normalized controller outputs and clip to the action box.

    ``alpha=0`` is exactly ``primary``; ``alpha=1`` is exactly ``secondary``.
    Both functions are called at every step so stateful controllers advance
    consistently throughout a sweep, including at the endpoint settings.
    """
    if not np.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be finite and in [0, 1], got {alpha!r}")

    def _fn(
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        primary_actions = primary(step, obs, n_agents)
        secondary_actions = secondary(step, obs, n_agents)
        return _blend_action_maps(
            primary_actions,
            secondary_actions,
            alpha=alpha,
            n_agents=n_agents,
        )

    return _fn


@dataclass
class ModeRatioGatedBlend:
    """State-dependent droop residual with auditable gate telemetry.

    The shared gate separates common and differential frequency modes from
    V4's local frequency observation ``obs[i][1]``:

    ``rho = std(x) / (abs(mean(x)) + std(x) + epsilon)``
    ``alpha = alpha_cap * clip(rho / ratio_full_scale, 0, 1)``

    The resulting action is ``primary + alpha * (secondary - primary)``.
    ``alpha_history`` is reset whenever ``step == 0`` so callers can persist
    one scenario's gate trajectory without reaching inside the environment.
    """

    primary: ActionFn
    secondary: ActionFn
    alpha_cap: float
    ratio_full_scale: float = 0.05
    epsilon: float = 1e-8
    alpha_history: list[float] = field(default_factory=list, init=False)
    ratio_history: list[float] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if not np.isfinite(self.alpha_cap) or not 0.0 <= self.alpha_cap <= 1.0:
            raise ValueError(f"alpha_cap must be finite and in [0, 1], got {self.alpha_cap!r}")
        if not np.isfinite(self.ratio_full_scale) or self.ratio_full_scale <= 0:
            raise ValueError(
                f"ratio_full_scale must be finite and positive, got {self.ratio_full_scale!r}"
            )
        if not np.isfinite(self.epsilon) or self.epsilon <= 0:
            raise ValueError(f"epsilon must be finite and positive, got {self.epsilon!r}")

    def _raw_alpha(
        self,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> tuple[float, float]:
        """Return the pre-registered mode ratio and raw blend coefficient."""
        if set(obs) != set(range(n_agents)):
            raise ValueError(f"expected observations for {n_agents} agents")

        frequency_state: list[float] = []
        for i in range(n_agents):
            obs_i = np.asarray(obs[i], dtype=float)
            if obs_i.size < 2:
                raise ValueError(f"agent {i} observation must have at least 2 elements")
            value = float(obs_i[1])
            if not np.isfinite(value):
                raise ValueError(f"agent {i} frequency observation is not finite")
            frequency_state.append(value)

        values = np.asarray(frequency_state, dtype=float)
        common_magnitude = abs(float(np.mean(values)))
        differential_magnitude = float(np.std(values))
        ratio = differential_magnitude / (common_magnitude + differential_magnitude + self.epsilon)
        alpha = self.alpha_cap * float(np.clip(ratio / self.ratio_full_scale, 0.0, 1.0))
        return ratio, alpha

    def __call__(
        self,
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        if step == 0:
            self.alpha_history.clear()
            self.ratio_history.clear()
        ratio, alpha = self._raw_alpha(obs, n_agents)
        self.ratio_history.append(ratio)
        self.alpha_history.append(alpha)

        primary_actions = self.primary(step, obs, n_agents)
        secondary_actions = self.secondary(step, obs, n_agents)
        return _blend_action_maps(
            primary_actions,
            secondary_actions,
            alpha=alpha,
            n_agents=n_agents,
        )

    def telemetry(self) -> dict[str, Any]:
        """Summarise the current scenario's gate trajectory."""
        if not self.alpha_history:
            return {
                "alpha_mean": None,
                "alpha_max": None,
                "active_fraction": None,
                "saturated_fraction": None,
                "ratio_mean": None,
                "n_steps": 0,
            }
        alpha = np.asarray(self.alpha_history, dtype=float)
        ratio = np.asarray(self.ratio_history, dtype=float)
        return {
            "alpha_mean": float(np.mean(alpha)),
            "alpha_max": float(np.max(alpha)),
            "active_fraction": float(np.mean(alpha > 1e-12)),
            "saturated_fraction": float(
                np.mean(np.isclose(alpha, self.alpha_cap, rtol=0.0, atol=1e-8))
            ),
            "ratio_mean": float(np.mean(ratio)),
            "n_steps": int(alpha.size),
        }


@dataclass
class SlewLimitedModeRatioGatedBlend(ModeRatioGatedBlend):
    """Mode-ratio blend with a symmetric hard bound on alpha increments.

    The first control step is transparent and executes the raw gate.  Every
    later step projects the raw coefficient onto the interval centred at the
    previously executed coefficient:

    ``alpha_exec = clip(alpha_raw, alpha_prev - delta, alpha_prev + delta)``.

    Only the selector coefficient is limited.  The component controller
    actions are neither filtered nor delayed.
    """

    delta_alpha_max: float = 0.02895
    raw_alpha_history: list[float] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if (
            not np.isfinite(self.delta_alpha_max)
            or self.delta_alpha_max <= 0
            or self.delta_alpha_max > self.alpha_cap
        ):
            raise ValueError(
                "delta_alpha_max must be finite and in (0, alpha_cap], "
                f"got {self.delta_alpha_max!r}"
            )

    def __call__(
        self,
        step: int,
        obs: dict[int, np.ndarray],
        n_agents: int,
    ) -> dict[int, np.ndarray]:
        if step == 0:
            self.alpha_history.clear()
            self.ratio_history.clear()
            self.raw_alpha_history.clear()

        ratio, raw_alpha = self._raw_alpha(obs, n_agents)
        if not self.alpha_history:
            executed_alpha = raw_alpha
        else:
            previous = self.alpha_history[-1]
            executed_alpha = float(
                np.clip(
                    raw_alpha,
                    previous - self.delta_alpha_max,
                    previous + self.delta_alpha_max,
                )
            )

        self.ratio_history.append(ratio)
        self.raw_alpha_history.append(raw_alpha)
        self.alpha_history.append(executed_alpha)

        primary_actions = self.primary(step, obs, n_agents)
        secondary_actions = self.secondary(step, obs, n_agents)
        return _blend_action_maps(
            primary_actions,
            secondary_actions,
            alpha=executed_alpha,
            n_agents=n_agents,
        )

    def telemetry(self) -> dict[str, Any]:
        """Summarise raw and executed alpha trajectories."""
        summary = super().telemetry()
        summary["delta_alpha_max"] = self.delta_alpha_max
        if not self.alpha_history:
            summary.update(
                {
                    "raw_alpha_mean": None,
                    "raw_alpha_max": None,
                    "slew_limited_fraction": None,
                    "max_abs_executed_delta_alpha": None,
                }
            )
            return summary

        executed = np.asarray(self.alpha_history, dtype=float)
        raw = np.asarray(self.raw_alpha_history, dtype=float)
        summary.update(
            {
                "raw_alpha_mean": float(np.mean(raw)),
                "raw_alpha_max": float(np.max(raw)),
                "slew_limited_fraction": float(
                    np.mean(~np.isclose(executed, raw, rtol=0.0, atol=1e-12))
                ),
                "max_abs_executed_delta_alpha": float(
                    np.max(np.abs(np.diff(executed))) if executed.size > 1 else 0.0
                ),
            }
        )
        return summary


def mode_ratio_gated_blend_action_fn(
    primary: ActionFn,
    secondary: ActionFn,
    *,
    alpha_cap: float,
    ratio_full_scale: float = 0.05,
    epsilon: float = 1e-8,
) -> ModeRatioGatedBlend:
    """Build the pre-registered common/differential-mode gated residual."""
    return ModeRatioGatedBlend(
        primary=primary,
        secondary=secondary,
        alpha_cap=alpha_cap,
        ratio_full_scale=ratio_full_scale,
        epsilon=epsilon,
    )


def slew_limited_mode_ratio_gated_blend_action_fn(
    primary: ActionFn,
    secondary: ActionFn,
    *,
    alpha_cap: float,
    delta_alpha_max: float,
    ratio_full_scale: float = 0.05,
    epsilon: float = 1e-8,
) -> SlewLimitedModeRatioGatedBlend:
    """Build the Q-0029 alpha-slew common/differential-mode residual."""
    return SlewLimitedModeRatioGatedBlend(
        primary=primary,
        secondary=secondary,
        alpha_cap=alpha_cap,
        ratio_full_scale=ratio_full_scale,
        epsilon=epsilon,
        delta_alpha_max=delta_alpha_max,
    )


def interpolate_static_frontier_geo(
    rows: list[dict[str, Any]],
    *,
    cum_rf: float,
) -> float | None:
    """Interpolate the measured static-blend geo at a target ``cum_rf``.

    ``rows`` must contain finite ``cum_rf`` and ``geo`` values. Duplicate
    ``cum_rf`` coordinates retain the largest geo. Values outside the measured
    range return ``None`` rather than extrapolating a scientific baseline.
    """
    if not np.isfinite(cum_rf):
        raise ValueError(f"cum_rf must be finite, got {cum_rf!r}")
    points: dict[float, float] = {}
    for row in rows:
        try:
            x = float(row["cum_rf"])
            y = float(row["geo"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("frontier rows require numeric cum_rf and geo") from exc
        if not np.isfinite(x) or not np.isfinite(y):
            raise ValueError("frontier rows require finite cum_rf and geo")
        points[x] = max(points.get(x, -np.inf), y)
    if len(points) < 2:
        raise ValueError("frontier interpolation requires at least two points")
    ordered = sorted(points.items())
    x_values = np.asarray([point[0] for point in ordered], dtype=float)
    y_values = np.asarray([point[1] for point in ordered], dtype=float)
    if cum_rf < x_values[0] or cum_rf > x_values[-1]:
        return None
    return float(np.interp(cum_rf, x_values, y_values))
