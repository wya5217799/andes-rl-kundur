"""Development-only diagnostics for fixed observer-feedback commands.

The public seams replay an already executed nominal trace, decompose its raw
command, run a privileged exact-state counterfactual, and derive one analytic
authority scale. They read no repository artifact and own no classification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.model_first_observer_lqr import (
    ObserverFeedbackTrace,
    ObserverLqrDesign,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class FeedbackCommandDiagnosis:
    """Observable replay and decomposition of one nominal observer trace."""

    true_augmented_states: np.ndarray
    estimation_errors: np.ndarray
    raw_observer_coordinate_actions: np.ndarray
    raw_observer_node_actions: np.ndarray
    true_state_coordinate_actions: np.ndarray
    true_state_node_actions: np.ndarray
    estimation_error_coordinate_actions: np.ndarray
    estimation_error_node_actions: np.ndarray
    projection_residual_node_actions: np.ndarray
    maximum_decomposition_error: float
    maximum_output_replay_error: float
    maximum_action_replay_error: float
    raw_node_power_ratio: float
    raw_node_ramp_ratio: float
    true_state_raw_node_power_ratio: float
    true_state_raw_node_ramp_ratio: float
    estimation_error_command_norm_ratio: float


@dataclass(frozen=True)
class ExactStateFeedbackTrace:
    """Privileged exact-state governed counterfactual for diagnosis only."""

    outputs: np.ndarray
    coordinate_actions: np.ndarray
    node_actions: np.ndarray
    raw_node_actions: np.ndarray
    soc: np.ndarray
    governor_intervention_count: int
    constraint_violation_count: int

    @property
    def output_energy(self) -> float:
        return float(np.sum(np.square(self.outputs)))


def _coordinate_basis() -> tuple[np.ndarray, np.ndarray]:
    basis = np.column_stack((np.ones(4), active_power_incidence()))
    return basis, np.linalg.inv(basis)


def _plant_matrices(
    realization: StateSpaceRealization,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    state = np.asarray(realization.state_matrix, dtype=float)
    inputs = np.asarray(realization.input_matrix, dtype=float)
    outputs = np.asarray(realization.output_matrix, dtype=float)
    feedthrough = np.asarray(realization.feedthrough_matrix, dtype=float)
    order = state.shape[0]
    if (
        state.shape != (order, order)
        or inputs.shape != (order, 4)
        or outputs.shape != (4, order)
        or feedthrough.shape != (4, 4)
        or not all(
            np.all(np.isfinite(value))
            for value in (state, inputs, outputs, feedthrough)
        )
    ):
        raise ValueError("realization must be a finite four-input/four-output model")
    return state, inputs, outputs, feedthrough


def _disturbances(values: object) -> np.ndarray:
    disturbances = np.asarray(values, dtype=float)
    if (
        disturbances.ndim != 2
        or disturbances.shape[0] < 1
        or disturbances.shape[1] != 4
        or not np.all(np.isfinite(disturbances))
    ):
        raise ValueError("disturbance_sequence must be finite steps-by-four data")
    return disturbances


def _project_node_action(
    raw: np.ndarray,
    previous: np.ndarray,
    soc: np.ndarray,
    limits: FeedbackLimits,
) -> tuple[np.ndarray, int]:
    ramped = np.clip(raw, previous - limits.node_ramp, previous + limits.node_ramp)
    powered = np.clip(ramped, -limits.node_power, limits.node_power)
    soc_factor = (
        limits.sample_period_seconds
        * limits.system_mva
        / (3600.0 * limits.energy_mwh)
    )
    maximum_discharge = (
        (soc - limits.minimum_soc) * limits.discharge_efficiency / soc_factor
    )
    maximum_charge = (
        (limits.maximum_soc - soc) / (limits.charge_efficiency * soc_factor)
    )
    projected = np.minimum(np.maximum(powered, -maximum_charge), maximum_discharge)
    return projected, int(np.any(np.abs(projected - raw) > 1.0e-12))


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


def _raw_ratios(actions: np.ndarray, limits: FeedbackLimits) -> tuple[float, float]:
    ramps = np.vstack((actions[:1], np.diff(actions, axis=0)))
    return (
        float(np.max(np.abs(actions)) / limits.node_power),
        float(np.max(np.abs(ramps)) / limits.node_ramp),
    )


def diagnose_observer_feedback_commands(
    plant_realization: StateSpaceRealization,
    disturbance_sequence: object,
    *,
    design: ObserverLqrDesign,
    trace: ObserverFeedbackTrace,
    limits: FeedbackLimits = FeedbackLimits(),
) -> FeedbackCommandDiagnosis:
    """Replay one nominal trace and split raw state and estimation commands."""

    disturbances = _disturbances(disturbance_sequence)
    state_matrix, input_matrix, output_matrix, feedthrough = _plant_matrices(
        plant_realization
    )
    steps = disturbances.shape[0]
    order = state_matrix.shape[0]
    estimate_order = order + 4
    if (
        trace.outputs.shape != (steps, 4)
        or trace.model_outputs.shape != (steps, 4)
        or trace.coordinate_actions.shape != (steps, 4)
        or trace.node_actions.shape != (steps, 4)
        or trace.estimates.shape != (steps, estimate_order)
        or design.feedback_gain.shape != (4, estimate_order)
    ):
        raise ValueError("trace and design dimensions do not match the plant")
    if not np.allclose(trace.outputs, trace.model_outputs, atol=1.0e-12, rtol=0.0):
        raise ValueError("command diagnosis accepts nominal traces only")

    basis, inverse_basis = _coordinate_basis()
    true_states = np.zeros((steps, estimate_order))
    replay_outputs = np.zeros((steps, 4))
    replay_coordinate_actions = np.zeros((steps, 4))
    state = np.zeros(order)
    previous_output = np.zeros(4)
    for step, disturbance in enumerate(disturbances):
        true_states[step] = np.concatenate((state, previous_output))
        replay_coordinate_actions[step] = inverse_basis @ trace.node_actions[step]
        total_input = disturbance + trace.coordinate_actions[step]
        replay_outputs[step] = output_matrix @ state + feedthrough @ total_input
        state = state_matrix @ state + input_matrix @ total_input
        previous_output = replay_outputs[step]

    estimation_errors = trace.estimates - true_states
    raw_observer_coordinate = -trace.estimates @ design.feedback_gain.T
    true_state_coordinate = -true_states @ design.feedback_gain.T
    estimation_error_coordinate = -estimation_errors @ design.feedback_gain.T
    raw_observer_node = raw_observer_coordinate @ basis.T
    true_state_node = true_state_coordinate @ basis.T
    estimation_error_node = estimation_error_coordinate @ basis.T
    projection_residual = raw_observer_node - trace.node_actions
    raw_power_ratio, raw_ramp_ratio = _raw_ratios(raw_observer_node, limits)
    true_power_ratio, true_ramp_ratio = _raw_ratios(true_state_node, limits)
    denominator = max(float(np.linalg.norm(raw_observer_node)), np.finfo(float).tiny)
    error_norm_ratio = float(np.linalg.norm(estimation_error_node) / denominator)
    return FeedbackCommandDiagnosis(
        true_augmented_states=true_states,
        estimation_errors=estimation_errors,
        raw_observer_coordinate_actions=raw_observer_coordinate,
        raw_observer_node_actions=raw_observer_node,
        true_state_coordinate_actions=true_state_coordinate,
        true_state_node_actions=true_state_node,
        estimation_error_coordinate_actions=estimation_error_coordinate,
        estimation_error_node_actions=estimation_error_node,
        projection_residual_node_actions=projection_residual,
        maximum_decomposition_error=float(
            np.max(
                np.abs(
                    raw_observer_node - true_state_node - estimation_error_node
                )
            )
        ),
        maximum_output_replay_error=float(
            np.max(np.abs(replay_outputs - trace.model_outputs))
        ),
        maximum_action_replay_error=float(
            np.max(np.abs(replay_coordinate_actions - trace.coordinate_actions))
        ),
        raw_node_power_ratio=raw_power_ratio,
        raw_node_ramp_ratio=raw_ramp_ratio,
        true_state_raw_node_power_ratio=true_power_ratio,
        true_state_raw_node_ramp_ratio=true_ramp_ratio,
        estimation_error_command_norm_ratio=error_norm_ratio,
    )


def simulate_exact_state_feedback(
    plant_realization: StateSpaceRealization,
    disturbance_sequence: object,
    *,
    design: ObserverLqrDesign,
    initial_soc: float | Sequence[float],
    limits: FeedbackLimits = FeedbackLimits(),
) -> ExactStateFeedbackTrace:
    """Run a privileged exact-augmented-state governed counterfactual."""

    disturbances = _disturbances(disturbance_sequence)
    state_matrix, input_matrix, output_matrix, feedthrough = _plant_matrices(
        plant_realization
    )
    order = state_matrix.shape[0]
    if design.feedback_gain.shape != (4, order + 4):
        raise ValueError("design dimensions do not match the plant")
    soc = np.broadcast_to(np.asarray(initial_soc, dtype=float), (4,)).copy()
    if (
        not np.all(np.isfinite(soc))
        or np.any(soc < limits.minimum_soc)
        or np.any(soc > limits.maximum_soc)
    ):
        raise ValueError("initial_soc is outside the frozen bounds")

    basis, inverse_basis = _coordinate_basis()
    state = np.zeros(order)
    previous_output = np.zeros(4)
    previous_node_action = np.zeros(4)
    outputs = np.zeros_like(disturbances)
    coordinate_actions = np.zeros_like(disturbances)
    node_actions = np.zeros_like(disturbances)
    raw_node_actions = np.zeros_like(disturbances)
    soc_history = np.zeros((disturbances.shape[0] + 1, 4))
    soc_history[0] = soc
    interventions = 0
    for step, disturbance in enumerate(disturbances):
        augmented_state = np.concatenate((state, previous_output))
        raw_coordinate = -design.feedback_gain @ augmented_state
        raw_node = basis @ raw_coordinate
        node_action, count = _project_node_action(
            raw_node, previous_node_action, soc, limits
        )
        coordinate_action = inverse_basis @ node_action
        total_input = disturbance + coordinate_action
        output = output_matrix @ state + feedthrough @ total_input
        state = state_matrix @ state + input_matrix @ total_input
        soc = _advance_soc(soc, node_action, limits)

        outputs[step] = output
        coordinate_actions[step] = coordinate_action
        node_actions[step] = node_action
        raw_node_actions[step] = raw_node
        soc_history[step + 1] = soc
        previous_output = output
        previous_node_action = node_action
        interventions += count

    ramps = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(np.abs(node_actions) > limits.node_power + 1.0e-12)
        or np.any(np.abs(ramps) > limits.node_ramp + 1.0e-12)
        or np.any(soc_history < limits.minimum_soc - 1.0e-12)
        or np.any(soc_history > limits.maximum_soc + 1.0e-12)
    )
    return ExactStateFeedbackTrace(
        outputs=outputs,
        coordinate_actions=coordinate_actions,
        node_actions=node_actions,
        raw_node_actions=raw_node_actions,
        soc=soc_history,
        governor_intervention_count=interventions,
        constraint_violation_count=violations,
    )


def derive_common_authority_scale(
    diagnoses: Sequence[FeedbackCommandDiagnosis],
) -> float:
    """Return the one common scalar satisfying observed raw power and ramp."""

    if not diagnoses:
        raise ValueError("at least one command diagnosis is required")
    ratios = [
        max(item.raw_node_power_ratio, item.raw_node_ramp_ratio)
        for item in diagnoses
    ]
    if not all(np.isfinite(value) and value >= 0.0 for value in ratios):
        raise ValueError("command ratios must be finite and non-negative")
    worst = max(ratios)
    return float(1.0 if worst <= 1.0 else 1.0 / worst)


def scale_observer_feedback_design(
    design: ObserverLqrDesign,
    scale: float,
) -> ObserverLqrDesign:
    """Scale only the feedback gain and recompute its nominal pole radius."""

    value = float(scale)
    if not np.isfinite(value) or value <= 0.0 or value > 1.0:
        raise ValueError("scale must be finite in (0, 1]")
    feedback = value * np.asarray(design.feedback_gain, dtype=float)
    augmented = design.augmented_model
    controller_radius = float(
        np.max(
            np.abs(
                np.linalg.eigvals(
                    augmented.state_matrix - augmented.input_matrix @ feedback
                )
            )
        )
    )
    if not np.isfinite(controller_radius):
        raise ValueError("scaled feedback has non-finite nominal poles")
    return ObserverLqrDesign(
        augmented_model=augmented,
        feedback_gain=feedback,
        filter_gain=np.asarray(design.filter_gain, dtype=float).copy(),
        output_scales=np.asarray(design.output_scales, dtype=float).copy(),
        action_scales=np.asarray(design.action_scales, dtype=float).copy(),
        controller_pole_radius=controller_radius,
        observer_pole_radius=design.observer_pole_radius,
    )
