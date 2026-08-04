"""Pure offline feedback primitives for the model-first research line.

The module synthesizes and evaluates delayed common/differential output
feedback from already authorized finite state-space realizations.  It reads no
repository artifact, runs no simulator, and owns no scientific classification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class DcInverseGainFamily:
    """Matched retained-cross and cross-deleted base gains."""

    averaged_dc_gain: np.ndarray
    retained_cross_base: np.ndarray
    cross_deleted_base: np.ndarray
    condition_number: float


@dataclass(frozen=True)
class FeedbackLimits:
    """Node-space actuator and energy limits used by the offline governor."""

    sample_period_seconds: float = 0.2
    node_power: float = 0.36
    node_ramp: float = 0.072
    system_mva: float = 100.0
    energy_mwh: float = 28.0
    charge_efficiency: float = 0.9848857802
    discharge_efficiency: float = 0.9848857802
    minimum_soc: float = 0.2
    maximum_soc: float = 0.8

    def __post_init__(self) -> None:
        positive = (
            self.sample_period_seconds,
            self.node_power,
            self.node_ramp,
            self.system_mva,
            self.energy_mwh,
            self.charge_efficiency,
            self.discharge_efficiency,
        )
        if not all(np.isfinite(value) and value > 0.0 for value in positive):
            raise ValueError("feedback limits must be finite and positive")
        if not 0.0 <= self.minimum_soc < self.maximum_soc <= 1.0:
            raise ValueError("SOC limits must lie in [0, 1]")


@dataclass(frozen=True)
class FeedbackTrace:
    """Observable result of one delayed-feedback simulation."""

    outputs: np.ndarray
    model_outputs: np.ndarray
    coordinate_actions: np.ndarray
    node_actions: np.ndarray
    soc: np.ndarray
    governor_intervention_count: int
    constraint_violation_count: int

    @property
    def output_energy(self) -> float:
        return float(np.sum(np.square(self.outputs)))

    @property
    def coordinate_action_energy(self) -> float:
        return float(np.sum(np.square(self.coordinate_actions)))


@dataclass(frozen=True)
class FeedbackCase:
    """One named, point-bound disturbance used by scalar selection."""

    point: str
    name: str
    disturbance: np.ndarray
    initial_soc: float


@dataclass(frozen=True)
class GainSelection:
    """Selected scalar and its development-bank diagnostics."""

    scalar: float
    gain: np.ndarray
    maximum_pole_radius: float
    mean_output_energy_ratio: float
    worst_output_energy_ratio: float
    candidate_count: int
    case_count: int
    governor_intervention_count: int
    constraint_violation_count: int


class NoFeasibleFeedbackGain(ValueError):
    """Raised when the frozen scalar grid contains no feasible gain."""


def _coordinate_basis() -> tuple[np.ndarray, np.ndarray]:
    basis = np.column_stack((np.ones(4), active_power_incidence()))
    return basis, np.linalg.inv(basis)


def _project_node_action(
    raw_node_action: np.ndarray,
    previous_node_action: np.ndarray,
    soc: np.ndarray,
    limits: FeedbackLimits,
) -> tuple[np.ndarray, int]:
    ramped = np.clip(
        raw_node_action,
        previous_node_action - limits.node_ramp,
        previous_node_action + limits.node_ramp,
    )
    powered = np.clip(ramped, -limits.node_power, limits.node_power)
    soc_factor = (
        limits.sample_period_seconds
        * limits.system_mva
        / (3600.0 * limits.energy_mwh)
    )
    maximum_discharge = (
        (soc - limits.minimum_soc)
        * limits.discharge_efficiency
        / soc_factor
    )
    maximum_charge = (
        (limits.maximum_soc - soc)
        / (limits.charge_efficiency * soc_factor)
    )
    projected = np.minimum(np.maximum(powered, -maximum_charge), maximum_discharge)
    interventions = int(
        np.any(np.abs(projected - raw_node_action) > 1.0e-12)
    )
    return projected, interventions


def _advance_soc(
    soc: np.ndarray,
    node_action: np.ndarray,
    limits: FeedbackLimits,
) -> np.ndarray:
    factor = (
        limits.sample_period_seconds
        * limits.system_mva
        / (3600.0 * limits.energy_mwh)
    )
    delta = np.where(
        node_action >= 0.0,
        -factor * node_action / limits.discharge_efficiency,
        -factor * node_action * limits.charge_efficiency,
    )
    return soc + delta


def simulate_delayed_output_feedback(
    realization: StateSpaceRealization,
    disturbance_sequence: object,
    *,
    gain: object,
    initial_soc: float | Sequence[float],
    limits: FeedbackLimits = FeedbackLimits(),
    mismatch_transform: object | None = None,
) -> FeedbackTrace:
    """Simulate causal one-sample delayed feedback with a node-space governor."""

    disturbances = np.asarray(disturbance_sequence, dtype=float)
    gain_matrix = np.asarray(gain, dtype=float)
    if (
        disturbances.ndim != 2
        or disturbances.shape[0] < 1
        or disturbances.shape[1] != 4
        or not np.all(np.isfinite(disturbances))
    ):
        raise ValueError("disturbance_sequence must be finite steps-by-four data")
    if gain_matrix.shape != (4, 4) or not np.all(np.isfinite(gain_matrix)):
        raise ValueError("gain must be a finite four-by-four matrix")
    mismatch = (
        np.zeros((4, 4))
        if mismatch_transform is None
        else np.asarray(mismatch_transform, dtype=float)
    )
    if mismatch.shape != (4, 4) or not np.all(np.isfinite(mismatch)):
        raise ValueError("mismatch_transform must be a finite four-by-four matrix")

    state = np.zeros(realization.state_matrix.shape[0])
    previous_output = np.zeros(4)
    previous_node_action = np.zeros(4)
    soc = np.broadcast_to(np.asarray(initial_soc, dtype=float), (4,)).copy()
    if (
        not np.all(np.isfinite(soc))
        or np.any(soc < limits.minimum_soc)
        or np.any(soc > limits.maximum_soc)
    ):
        raise ValueError("initial_soc is outside the frozen bounds")

    basis, inverse_basis = _coordinate_basis()
    outputs = np.zeros_like(disturbances)
    model_outputs = np.zeros_like(disturbances)
    coordinate_actions = np.zeros_like(disturbances)
    node_actions = np.zeros_like(disturbances)
    soc_history = np.zeros((disturbances.shape[0] + 1, 4))
    soc_history[0] = soc
    interventions = 0

    for step, disturbance in enumerate(disturbances):
        raw_coordinate_action = -gain_matrix @ previous_output
        raw_node_action = basis @ raw_coordinate_action
        node_action, count = _project_node_action(
            raw_node_action,
            previous_node_action,
            soc,
            limits,
        )
        interventions += count
        coordinate_action = inverse_basis @ node_action
        total_input = disturbance + coordinate_action
        model_output = (
            realization.output_matrix @ state
            + realization.feedthrough_matrix @ total_input
        )
        output = model_output + mismatch @ model_output
        state = realization.state_matrix @ state + realization.input_matrix @ total_input
        soc = _advance_soc(soc, node_action, limits)

        outputs[step] = output
        model_outputs[step] = model_output
        coordinate_actions[step] = coordinate_action
        node_actions[step] = node_action
        soc_history[step + 1] = soc
        previous_output = output
        previous_node_action = node_action

    ramp_deltas = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(np.abs(node_actions) > limits.node_power + 1.0e-12)
        or np.any(np.abs(ramp_deltas) > limits.node_ramp + 1.0e-12)
        or np.any(soc_history < limits.minimum_soc - 1.0e-12)
        or np.any(soc_history > limits.maximum_soc + 1.0e-12)
    )
    return FeedbackTrace(
        outputs=outputs,
        model_outputs=model_outputs,
        coordinate_actions=coordinate_actions,
        node_actions=node_actions,
        soc=soc_history,
        governor_intervention_count=interventions,
        constraint_violation_count=violations,
    )


def augmented_closed_loop_radius(
    realization: StateSpaceRealization,
    gain: object,
) -> float:
    """Return the exact nominal pole radius for one-sample delayed feedback."""

    gain_matrix = np.asarray(gain, dtype=float)
    if gain_matrix.shape != (4, 4) or not np.all(np.isfinite(gain_matrix)):
        raise ValueError("gain must be a finite four-by-four matrix")
    state = np.asarray(realization.state_matrix, dtype=float)
    inputs = np.asarray(realization.input_matrix, dtype=float)
    outputs = np.asarray(realization.output_matrix, dtype=float)
    feedthrough = np.asarray(realization.feedthrough_matrix, dtype=float)
    augmented = np.block(
        [
            [state, -inputs @ gain_matrix],
            [outputs, -feedthrough @ gain_matrix],
        ]
    )
    return float(np.max(np.abs(np.linalg.eigvals(augmented))))


def select_scalar_multiplier(
    realizations: dict[str, StateSpaceRealization],
    cases: Sequence[FeedbackCase],
    *,
    base_gain: object,
    scalar_candidates: Sequence[float],
    limits: FeedbackLimits = FeedbackLimits(),
    maximum_pole_radius: float,
) -> GainSelection:
    """Select the feasible scalar minimizing frozen worst/mean energy ratios."""

    if not realizations or not cases:
        raise ValueError("realizations and cases must be non-empty")
    base = np.asarray(base_gain, dtype=float)
    if base.shape != (4, 4) or not np.all(np.isfinite(base)):
        raise ValueError("base_gain must be a finite four-by-four matrix")
    scalars = tuple(float(value) for value in scalar_candidates)
    if (
        not scalars
        or len(set(scalars)) != len(scalars)
        or not all(np.isfinite(value) and value > 0.0 for value in scalars)
    ):
        raise ValueError("scalar_candidates must be unique positive finite values")
    radius_limit = float(maximum_pole_radius)
    if not np.isfinite(radius_limit) or not 0.0 < radius_limit < 1.0:
        raise ValueError("maximum_pole_radius must be in (0, 1)")
    for case in cases:
        if case.point not in realizations:
            raise ValueError(f"unknown realization point: {case.point}")

    zero_gain = np.zeros((4, 4))
    zero_energy: dict[str, float] = {}
    for case in cases:
        trace = simulate_delayed_output_feedback(
            realizations[case.point],
            case.disturbance,
            gain=zero_gain,
            initial_soc=case.initial_soc,
            limits=limits,
        )
        if trace.output_energy <= np.finfo(float).tiny:
            raise ValueError(f"zero-control case has no output energy: {case.name}")
        zero_energy[case.name] = trace.output_energy

    feasible: list[tuple[tuple[float, float, float], GainSelection]] = []
    for scalar in scalars:
        gain = scalar * base
        maximum_radius = max(
            augmented_closed_loop_radius(realization, gain)
            for realization in realizations.values()
        )
        if not np.isfinite(maximum_radius) or maximum_radius > radius_limit:
            continue
        ratios: list[float] = []
        interventions = 0
        violations = 0
        for case in cases:
            trace = simulate_delayed_output_feedback(
                realizations[case.point],
                case.disturbance,
                gain=gain,
                initial_soc=case.initial_soc,
                limits=limits,
            )
            ratios.append(trace.output_energy / zero_energy[case.name])
            interventions += trace.governor_intervention_count
            violations += trace.constraint_violation_count
        if violations:
            continue
        selection = GainSelection(
            scalar=scalar,
            gain=gain,
            maximum_pole_radius=maximum_radius,
            mean_output_energy_ratio=float(np.mean(ratios)),
            worst_output_energy_ratio=float(np.max(ratios)),
            candidate_count=len(scalars),
            case_count=len(cases),
            governor_intervention_count=interventions,
            constraint_violation_count=violations,
        )
        feasible.append(
            (
                (
                    selection.worst_output_energy_ratio,
                    selection.mean_output_energy_ratio,
                    selection.scalar,
                ),
                selection,
            )
        )
    if not feasible:
        raise NoFeasibleFeedbackGain("no scalar candidate passed pole and constraint gates")
    return min(feasible, key=lambda item: item[0])[1]


def synthesize_dc_inverse_gains(
    realizations: Sequence[StateSpaceRealization],
    *,
    maximum_condition_number: float = 1.0e6,
) -> DcInverseGainFamily:
    """Invert the equally weighted DC gain and delete only common/diff blocks."""

    if not realizations:
        raise ValueError("at least one realization is required")
    dc_gains: list[np.ndarray] = []
    for realization in realizations:
        state = np.asarray(realization.state_matrix, dtype=float)
        inputs = np.asarray(realization.input_matrix, dtype=float)
        outputs = np.asarray(realization.output_matrix, dtype=float)
        feedthrough = np.asarray(realization.feedthrough_matrix, dtype=float)
        if (
            state.ndim != 2
            or state.shape[0] != state.shape[1]
            or inputs.shape[0] != state.shape[0]
            or outputs.shape[1] != state.shape[0]
            or feedthrough.shape != (outputs.shape[0], inputs.shape[1])
            or outputs.shape[0] != 4
            or inputs.shape[1] != 4
            or not all(
                np.all(np.isfinite(matrix))
                for matrix in (state, inputs, outputs, feedthrough)
            )
        ):
            raise ValueError("realization must be a finite four-input/four-output model")
        dc_gains.append(
            outputs @ np.linalg.solve(np.eye(state.shape[0]) - state, inputs)
            + feedthrough
        )
    averaged = np.mean(dc_gains, axis=0)
    condition = float(np.linalg.cond(averaged))
    if (
        not np.isfinite(condition)
        or condition > float(maximum_condition_number)
    ):
        raise ValueError("averaged DC gain is too ill-conditioned to invert")
    retained = np.linalg.inv(averaged)
    deleted = retained.copy()
    deleted[0, 1:] = 0.0
    deleted[1:, 0] = 0.0
    return DcInverseGainFamily(
        averaged_dc_gain=averaged,
        retained_cross_base=retained,
        cross_deleted_base=deleted,
        condition_number=condition,
    )
