"""Fixed disturbance-aware estimator primitives for the model-first line."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_discrete_are

from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class DisturbanceEstimatorDesign:
    """One steady-state estimator with an augmented unknown-input state."""

    transition_matrix: np.ndarray
    control_matrix: np.ndarray
    measurement_matrix: np.ndarray
    feedthrough_matrix: np.ndarray
    filter_gain: np.ndarray
    covariance: np.ndarray
    process_covariance: np.ndarray
    measurement_covariance: np.ndarray
    physical_state_order: int
    observability_rank: int
    covariance_symmetry_error: float
    covariance_minimum_eigenvalue: float
    normalized_covariance_residual: float
    error_pole_radius: float


@dataclass(frozen=True)
class DisturbanceEstimateStep:
    """Observable output of one causal correction-and-prediction step."""

    predicted_estimate: np.ndarray
    corrected_estimate: np.ndarray
    innovation: np.ndarray


def _positive_scales(values: object) -> np.ndarray:
    scales = np.asarray(values, dtype=float)
    if scales.shape != (4,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("output_scales must contain four positive finite values")
    return scales


def _realization_matrices(
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
        or not all(np.all(np.isfinite(matrix)) for matrix in (state, inputs, outputs, feedthrough))
    ):
        raise ValueError("realization must be a finite four-input/four-output model")
    return state, inputs, outputs, feedthrough


def _observability_rank(transition: np.ndarray, measured: np.ndarray) -> int:
    order = transition.shape[0]
    matrix = np.vstack(
        [measured @ np.linalg.matrix_power(transition, power) for power in range(order)]
    )
    return int(np.linalg.matrix_rank(matrix))


def _covariance_residual(
    transition: np.ndarray,
    measured: np.ndarray,
    covariance: np.ndarray,
    process_covariance: np.ndarray,
    measurement_covariance: np.ndarray,
) -> float:
    innovation_covariance = measured @ covariance @ measured.T + measurement_covariance
    correction = (
        transition
        @ covariance
        @ measured.T
        @ np.linalg.solve(
            innovation_covariance,
            measured @ covariance @ transition.T,
        )
    )
    residual = transition @ covariance @ transition.T - covariance - correction + process_covariance
    scale = max(
        float(np.linalg.norm(covariance, ord="fro")),
        float(np.linalg.norm(process_covariance, ord="fro")),
        np.finfo(float).eps,
    )
    return float(np.linalg.norm(residual, ord="fro") / scale)


def synthesize_disturbance_estimator(
    realization: StateSpaceRealization,
    *,
    output_scales: object,
    disturbance_scale: float = 0.05,
    measurement_fraction: float = 0.01,
) -> DisturbanceEstimatorDesign:
    """Build one fixed steady-state estimator for state plus unknown input."""

    state, inputs, outputs, feedthrough = _realization_matrices(realization)
    scales = _positive_scales(output_scales)
    disturbance = float(disturbance_scale)
    measurement = float(measurement_fraction)
    if not np.isfinite(disturbance) or disturbance <= 0.0:
        raise ValueError("disturbance_scale must be positive and finite")
    if not np.isfinite(measurement) or measurement <= 0.0:
        raise ValueError("measurement_fraction must be positive and finite")

    order = state.shape[0]
    augmented_order = order + 4
    transition = np.block([[state, inputs], [np.zeros((4, order)), np.eye(4)]])
    control = np.vstack((inputs, np.zeros((4, 4))))
    measured = np.hstack((outputs, feedthrough))
    observability_rank = _observability_rank(transition, measured)
    if observability_rank != augmented_order:
        raise ValueError("disturbance-augmented model must be observable")

    process_covariance = np.zeros((augmented_order, augmented_order))
    process_covariance[order:, order:] = np.square(disturbance) * np.eye(4)
    covariance_floor = 1.0e-12 * max(
        float(np.trace(process_covariance)) / augmented_order,
        np.finfo(float).eps,
    )
    process_covariance += covariance_floor * np.eye(augmented_order)
    measurement_covariance = np.diag(np.square(measurement * scales))
    try:
        covariance = solve_discrete_are(
            transition.T,
            measured.T,
            process_covariance,
            measurement_covariance,
        )
        innovation_covariance = measured @ covariance @ measured.T + measurement_covariance
        gain = np.linalg.solve(
            innovation_covariance,
            measured @ covariance,
        ).T
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise ValueError("disturbance-estimator covariance synthesis failed") from exc

    symmetry_error = float(np.max(np.abs(covariance - covariance.T)))
    minimum_eigenvalue = float(np.min(np.linalg.eigvalsh(0.5 * (covariance + covariance.T))))
    normalized_residual = _covariance_residual(
        transition,
        measured,
        covariance,
        process_covariance,
        measurement_covariance,
    )
    error_poles = np.linalg.eigvals((np.eye(augmented_order) - gain @ measured) @ transition)
    error_radius = float(np.max(np.abs(error_poles)))
    values = (
        transition,
        control,
        measured,
        feedthrough,
        gain,
        covariance,
        process_covariance,
        measurement_covariance,
        error_poles,
    )
    if not all(np.all(np.isfinite(value)) for value in values):
        raise ValueError("disturbance-estimator synthesis returned non-finite values")
    return DisturbanceEstimatorDesign(
        transition_matrix=transition,
        control_matrix=control,
        measurement_matrix=measured,
        feedthrough_matrix=feedthrough.copy(),
        filter_gain=gain,
        covariance=covariance,
        process_covariance=process_covariance,
        measurement_covariance=measurement_covariance,
        physical_state_order=order,
        observability_rank=observability_rank,
        covariance_symmetry_error=symmetry_error,
        covariance_minimum_eigenvalue=minimum_eigenvalue,
        normalized_covariance_residual=normalized_residual,
        error_pole_radius=error_radius,
    )


def advance_disturbance_estimate(
    design: DisturbanceEstimatorDesign,
    *,
    prior_estimate: object,
    previous_delivered_output: object,
    previous_executed_action: object,
) -> DisturbanceEstimateStep:
    """Correct the previous latent state and predict the current latent state."""

    prior = np.asarray(prior_estimate, dtype=float)
    delivered = np.asarray(previous_delivered_output, dtype=float)
    executed = np.asarray(previous_executed_action, dtype=float)
    order = design.transition_matrix.shape[0]
    if prior.shape != (order,) or not np.all(np.isfinite(prior)):
        raise ValueError("prior_estimate has invalid shape or values")
    if delivered.shape != (4,) or not np.all(np.isfinite(delivered)):
        raise ValueError("previous_delivered_output has invalid shape or values")
    if executed.shape != (4,) or not np.all(np.isfinite(executed)):
        raise ValueError("previous_executed_action has invalid shape or values")

    innovation = (
        delivered - design.feedthrough_matrix @ executed - design.measurement_matrix @ prior
    )
    corrected = prior + design.filter_gain @ innovation
    predicted = design.transition_matrix @ corrected + design.control_matrix @ executed
    if not all(np.all(np.isfinite(value)) for value in (innovation, corrected, predicted)):
        raise ValueError("disturbance-estimator step returned non-finite values")
    return DisturbanceEstimateStep(
        predicted_estimate=predicted,
        corrected_estimate=corrected,
        innovation=innovation,
    )
