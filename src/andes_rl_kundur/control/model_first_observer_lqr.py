"""Pure observer-LQR primitives for the model-first research line.

The module builds and evaluates one-sample-delay augmented controllers from
already authorized finite state-space models. It reads no repository artifact,
runs no simulator, and owns no scientific classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
from scipy.linalg import solve_discrete_are

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class DelayAugmentedModel:
    """Exact state, input, measurement, and regulated-output matrices."""

    state_matrix: np.ndarray
    input_matrix: np.ndarray
    measurement_matrix: np.ndarray
    regulated_output_matrix: np.ndarray
    feedthrough_matrix: np.ndarray


@dataclass(frozen=True)
class ObserverLqrDesign:
    """One fixed full-order regulator and corrected-state observer."""

    augmented_model: DelayAugmentedModel
    feedback_gain: np.ndarray
    filter_gain: np.ndarray
    output_scales: np.ndarray
    action_scales: np.ndarray
    controller_pole_radius: float
    observer_pole_radius: float


@dataclass(frozen=True)
class ObserverFeedbackTrace:
    """Observable result of one causal observer-feedback simulation."""

    outputs: np.ndarray
    model_outputs: np.ndarray
    coordinate_actions: np.ndarray
    node_actions: np.ndarray
    soc: np.ndarray
    estimates: np.ndarray
    innovations: np.ndarray
    governor_intervention_count: int
    constraint_violation_count: int

    @property
    def output_energy(self) -> float:
        return float(np.sum(np.square(self.outputs)))

    @property
    def innovation_energy(self) -> float:
        return float(np.sum(np.square(self.innovations)))

    @property
    def coordinate_action_energy(self) -> float:
        return float(np.sum(np.square(self.coordinate_actions)))


def build_delay_augmented_model(
    realization: StateSpaceRealization,
) -> DelayAugmentedModel:
    """Augment ``x[k]`` with the delivered measurement ``y[k-1]``."""

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
            np.all(np.isfinite(matrix))
            for matrix in (state, inputs, outputs, feedthrough)
        )
    ):
        raise ValueError("realization must be a finite four-input/four-output model")
    return DelayAugmentedModel(
        state_matrix=np.block(
            [[state, np.zeros((order, 4))], [outputs, np.zeros((4, 4))]]
        ),
        input_matrix=np.vstack((inputs, feedthrough)),
        measurement_matrix=np.hstack((np.zeros((4, order)), np.eye(4))),
        regulated_output_matrix=np.hstack((outputs, np.zeros((4, 4)))),
        feedthrough_matrix=feedthrough.copy(),
    )


def delete_common_differential_markov_blocks(markov_parameters: object) -> np.ndarray:
    """Delete only common-to-differential and differential-to-common blocks."""

    markov = np.asarray(markov_parameters, dtype=float)
    if markov.ndim != 3 or markov.shape[1:] != (4, 4) or not np.all(
        np.isfinite(markov)
    ):
        raise ValueError("markov_parameters must be finite steps-by-four-by-four data")
    deleted = markov.copy()
    deleted[:, 0, 1:] = 0.0
    deleted[:, 1:, 0] = 0.0
    return deleted


def _positive_scales(values: object, *, name: str) -> np.ndarray:
    scales = np.asarray(values, dtype=float)
    if scales.shape != (4,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError(f"{name} must contain four positive finite values")
    return scales


def synthesize_observer_lqr(
    realization: StateSpaceRealization,
    *,
    output_scales: object,
    action_scales: object,
    disturbance_scale: float = 0.05,
    measurement_fraction: float = 0.01,
) -> ObserverLqrDesign:
    """Solve one generalized output-energy LQR and one dual Riccati observer."""

    y_scales = _positive_scales(output_scales, name="output_scales")
    u_scales = _positive_scales(action_scales, name="action_scales")
    disturbance = float(disturbance_scale)
    measurement = float(measurement_fraction)
    if not np.isfinite(disturbance) or disturbance <= 0.0:
        raise ValueError("disturbance_scale must be positive and finite")
    if not np.isfinite(measurement) or measurement <= 0.0:
        raise ValueError("measurement_fraction must be positive and finite")

    augmented = build_delay_augmented_model(realization)
    state = augmented.state_matrix
    inputs = augmented.input_matrix
    measured = augmented.measurement_matrix
    regulated = augmented.regulated_output_matrix
    feedthrough = augmented.feedthrough_matrix
    output_weight = np.diag(np.square(1.0 / y_scales))
    action_weight = np.diag(np.square(1.0 / u_scales))
    state_cost = regulated.T @ output_weight @ regulated
    cross_cost = regulated.T @ output_weight @ feedthrough
    action_cost = feedthrough.T @ output_weight @ feedthrough + action_weight

    try:
        control_solution = solve_discrete_are(
            state,
            inputs,
            state_cost,
            action_cost,
            s=cross_cost,
        )
        feedback = np.linalg.solve(
            action_cost + inputs.T @ control_solution @ inputs,
            inputs.T @ control_solution @ state + cross_cost.T,
        )

        input_covariance = np.square(disturbance) * (inputs @ inputs.T)
        covariance_floor = 1.0e-12 * max(
            float(np.trace(input_covariance)) / state.shape[0],
            np.finfo(float).eps,
        )
        process_covariance = input_covariance + covariance_floor * np.eye(
            state.shape[0]
        )
        measurement_covariance = np.diag(np.square(measurement * y_scales))
        prediction_covariance = solve_discrete_are(
            state.T,
            measured.T,
            process_covariance,
            measurement_covariance,
        )
        filter_gain = np.linalg.solve(
            measured @ prediction_covariance @ measured.T
            + measurement_covariance,
            measured @ prediction_covariance,
        ).T
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise ValueError("observer-LQR Riccati synthesis failed") from exc

    controller_radius = float(
        np.max(np.abs(np.linalg.eigvals(state - inputs @ feedback)))
    )
    observer_radius = float(
        np.max(
            np.abs(
                np.linalg.eigvals(
                    (np.eye(state.shape[0]) - filter_gain @ measured) @ state
                )
            )
        )
    )
    if not all(
        np.all(np.isfinite(value))
        for value in (feedback, filter_gain, control_solution, prediction_covariance)
    ) or not np.isfinite(controller_radius + observer_radius):
        raise ValueError("observer-LQR synthesis returned non-finite values")
    return ObserverLqrDesign(
        augmented_model=augmented,
        feedback_gain=feedback,
        filter_gain=filter_gain,
        output_scales=y_scales.copy(),
        action_scales=u_scales.copy(),
        controller_pole_radius=controller_radius,
        observer_pole_radius=observer_radius,
    )


def _coordinate_basis() -> tuple[np.ndarray, np.ndarray]:
    basis = np.column_stack((np.ones(4), active_power_incidence()))
    return basis, np.linalg.inv(basis)


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


def simulate_observer_lqr_feedback(
    plant_realization: StateSpaceRealization,
    disturbance_sequence: object,
    *,
    design: ObserverLqrDesign,
    initial_soc: float | Sequence[float],
    limits: FeedbackLimits = FeedbackLimits(),
    mismatch_transform: object | None = None,
) -> ObserverFeedbackTrace:
    """Run delayed corrected-state feedback on one full retained-cross plant."""

    disturbances = np.asarray(disturbance_sequence, dtype=float)
    if (
        disturbances.ndim != 2
        or disturbances.shape[0] < 1
        or disturbances.shape[1] != 4
        or not np.all(np.isfinite(disturbances))
    ):
        raise ValueError("disturbance_sequence must be finite steps-by-four data")
    mismatch = (
        np.zeros((4, 4))
        if mismatch_transform is None
        else np.asarray(mismatch_transform, dtype=float)
    )
    if mismatch.shape != (4, 4) or not np.all(np.isfinite(mismatch)):
        raise ValueError("mismatch_transform must be a finite four-by-four matrix")

    plant_state = np.asarray(plant_realization.state_matrix, dtype=float)
    plant_inputs = np.asarray(plant_realization.input_matrix, dtype=float)
    plant_outputs = np.asarray(plant_realization.output_matrix, dtype=float)
    plant_feedthrough = np.asarray(plant_realization.feedthrough_matrix, dtype=float)
    plant_order = plant_state.shape[0]
    estimate_order = design.augmented_model.state_matrix.shape[0]
    if (
        plant_state.shape != (plant_order, plant_order)
        or plant_inputs.shape != (plant_order, 4)
        or plant_outputs.shape != (4, plant_order)
        or plant_feedthrough.shape != (4, 4)
        or design.feedback_gain.shape != (4, estimate_order)
        or design.filter_gain.shape != (estimate_order, 4)
    ):
        raise ValueError("plant and observer dimensions are inconsistent")

    soc = np.broadcast_to(np.asarray(initial_soc, dtype=float), (4,)).copy()
    if (
        not np.all(np.isfinite(soc))
        or np.any(soc < limits.minimum_soc)
        or np.any(soc > limits.maximum_soc)
    ):
        raise ValueError("initial_soc is outside the frozen bounds")

    state = np.zeros(plant_order)
    estimate_prediction = np.zeros(estimate_order)
    previous_output = np.zeros(4)
    previous_node_action = np.zeros(4)
    basis, inverse_basis = _coordinate_basis()
    outputs = np.zeros_like(disturbances)
    model_outputs = np.zeros_like(disturbances)
    coordinate_actions = np.zeros_like(disturbances)
    node_actions = np.zeros_like(disturbances)
    innovations = np.zeros_like(disturbances)
    estimates = np.zeros((disturbances.shape[0], estimate_order))
    soc_history = np.zeros((disturbances.shape[0] + 1, 4))
    soc_history[0] = soc
    interventions = 0

    for step, disturbance in enumerate(disturbances):
        innovation = (
            previous_output
            - design.augmented_model.measurement_matrix @ estimate_prediction
        )
        corrected_estimate = estimate_prediction + design.filter_gain @ innovation
        raw_coordinate_action = -design.feedback_gain @ corrected_estimate
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
        model_output = plant_outputs @ state + plant_feedthrough @ total_input
        output = model_output + mismatch @ model_output
        state = plant_state @ state + plant_inputs @ total_input
        soc = _advance_soc(soc, node_action, limits)
        estimate_prediction = (
            design.augmented_model.state_matrix @ corrected_estimate
            + design.augmented_model.input_matrix @ coordinate_action
        )

        outputs[step] = output
        model_outputs[step] = model_output
        coordinate_actions[step] = coordinate_action
        node_actions[step] = node_action
        innovations[step] = innovation
        estimates[step] = corrected_estimate
        soc_history[step + 1] = soc
        previous_output = output
        previous_node_action = node_action

    ramp_deltas = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(~np.isfinite(estimates))
        or np.any(~np.isfinite(innovations))
        or np.any(np.abs(node_actions) > limits.node_power + 1.0e-12)
        or np.any(np.abs(ramp_deltas) > limits.node_ramp + 1.0e-12)
        or np.any(soc_history < limits.minimum_soc - 1.0e-12)
        or np.any(soc_history > limits.maximum_soc + 1.0e-12)
    )
    return ObserverFeedbackTrace(
        outputs=outputs,
        model_outputs=model_outputs,
        coordinate_actions=coordinate_actions,
        node_actions=node_actions,
        soc=soc_history,
        estimates=estimates,
        innovations=innovations,
        governor_intervention_count=interventions,
        constraint_violation_count=violations,
    )
