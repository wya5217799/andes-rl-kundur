"""Separate control and physical-disturbance inputs for model-first control.

The R339/R341 predictor has four controller channels followed by four
physical-load channels.  This module keeps those channel families distinct;
it never represents a physical load as a static combination of controller
commands.  It reads no repository artifact and runs no physical simulator.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_discrete_are

from andes_rl_kundur.control.model_first_constrained_horizon import (
    ConstrainedHorizonDesign,
)
from andes_rl_kundur.control.model_first_constrained_qp import (
    SparseConstrainedActionResult,
    SparseConstrainedHorizonSolver,
)
from andes_rl_kundur.control.model_first_observer_lqr import DelayAugmentedModel
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class SeparateInputRealization:
    """One four-control/four-disturbance sampled realization."""

    state_matrix: np.ndarray
    control_input_matrix: np.ndarray
    disturbance_input_matrix: np.ndarray
    output_matrix: np.ndarray
    control_feedthrough_matrix: np.ndarray
    disturbance_feedthrough_matrix: np.ndarray
    retained_singular_values: np.ndarray

    @classmethod
    def from_joint(cls, realization: StateSpaceRealization) -> SeparateInputRealization:
        """Split ``[u_common, u_edge0:2, d_bus7/8/14/15]`` exactly once."""

        state = np.asarray(realization.state_matrix, dtype=float)
        inputs = np.asarray(realization.input_matrix, dtype=float)
        outputs = np.asarray(realization.output_matrix, dtype=float)
        feedthrough = np.asarray(realization.feedthrough_matrix, dtype=float)
        singular_values = np.asarray(realization.retained_singular_values, dtype=float)
        order = state.shape[0]
        matrices = (state, inputs, outputs, feedthrough, singular_values)
        if (
            state.shape != (order, order)
            or inputs.shape != (order, 8)
            or outputs.shape != (4, order)
            or feedthrough.shape != (4, 8)
            or singular_values.ndim != 1
            or not all(np.all(np.isfinite(value)) for value in matrices)
        ):
            raise ValueError(
                "joint realization must be a finite four-control/four-disturbance model"
            )
        return cls(
            state_matrix=state.copy(),
            control_input_matrix=inputs[:, :4].copy(),
            disturbance_input_matrix=inputs[:, 4:].copy(),
            output_matrix=outputs.copy(),
            control_feedthrough_matrix=feedthrough[:, :4].copy(),
            disturbance_feedthrough_matrix=feedthrough[:, 4:].copy(),
            retained_singular_values=singular_values.copy(),
        )

    def as_joint_realization(self) -> StateSpaceRealization:
        """Return the source-order eight-input realization."""

        return StateSpaceRealization(
            state_matrix=self.state_matrix.copy(),
            input_matrix=np.hstack((self.control_input_matrix, self.disturbance_input_matrix)),
            output_matrix=self.output_matrix.copy(),
            feedthrough_matrix=np.hstack(
                (
                    self.control_feedthrough_matrix,
                    self.disturbance_feedthrough_matrix,
                )
            ),
            retained_singular_values=self.retained_singular_values.copy(),
        )

    def as_control_realization(self) -> StateSpaceRealization:
        """Return the controller-input view without collapsing disturbances."""

        return StateSpaceRealization(
            state_matrix=self.state_matrix.copy(),
            input_matrix=self.control_input_matrix.copy(),
            output_matrix=self.output_matrix.copy(),
            feedthrough_matrix=self.control_feedthrough_matrix.copy(),
            retained_singular_values=self.retained_singular_values.copy(),
        )


@dataclass(frozen=True)
class SeparateInputEstimatorDesign:
    """Steady-state state/disturbance estimator with a separate control path."""

    transition_matrix: np.ndarray
    control_matrix: np.ndarray
    measurement_matrix: np.ndarray
    control_feedthrough_matrix: np.ndarray
    filter_gain: np.ndarray
    covariance: np.ndarray
    process_covariance: np.ndarray
    measurement_covariance: np.ndarray
    physical_state_order: int
    observability_rank: int
    normalized_covariance_residual: float
    error_pole_radius: float


@dataclass(frozen=True)
class SeparateInputEstimateStep:
    """Observable result of one causal correction-and-prediction step."""

    predicted_estimate: np.ndarray
    corrected_estimate: np.ndarray
    innovation: np.ndarray


@dataclass(frozen=True)
class SeparateInputHorizonStep:
    """One causal estimate, solve, and bounded request at the physical seam."""

    estimate: SeparateInputEstimateStep
    achieved_control_coordinates: np.ndarray
    requested_control_coordinates: np.ndarray
    requested_node_power: np.ndarray
    solver: SparseConstrainedActionResult
    used_fallback: bool
    fallback_reason: str | None


@dataclass(frozen=True)
class SeparateInputControllerIdentity:
    """Serializable controller semantics fixed before any physical bridge."""

    information_pattern: str
    input_contract: str
    request_semantics: str
    achieved_semantics: str
    solver: str
    fallback: str
    horizon_steps: int
    output_scales: tuple[float, float, float, float]
    action_scales: tuple[float, float, float, float]
    disturbance_scale: float
    measurement_fraction: float
    maximum_solver_iterations: int
    absolute_solver_tolerance: float
    relative_solver_tolerance: float
    feasibility_tolerance: float


def _separate_matrices(
    model: SeparateInputRealization,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    state = np.asarray(model.state_matrix, dtype=float)
    control = np.asarray(model.control_input_matrix, dtype=float)
    disturbance = np.asarray(model.disturbance_input_matrix, dtype=float)
    output = np.asarray(model.output_matrix, dtype=float)
    control_feedthrough = np.asarray(model.control_feedthrough_matrix, dtype=float)
    disturbance_feedthrough = np.asarray(
        model.disturbance_feedthrough_matrix,
        dtype=float,
    )
    order = state.shape[0]
    matrices = (
        state,
        control,
        disturbance,
        output,
        control_feedthrough,
        disturbance_feedthrough,
    )
    if (
        state.shape != (order, order)
        or control.shape != (order, 4)
        or disturbance.shape != (order, 4)
        or output.shape != (4, order)
        or control_feedthrough.shape != (4, 4)
        or disturbance_feedthrough.shape != (4, 4)
        or not all(np.all(np.isfinite(value)) for value in matrices)
    ):
        raise ValueError(
            "separate realization must be a finite four-control/four-disturbance model"
        )
    return matrices


def _observability_rank(transition: np.ndarray, measurement: np.ndarray) -> int:
    order = transition.shape[0]
    observability = np.vstack(
        [measurement @ np.linalg.matrix_power(transition, power) for power in range(order)]
    )
    return int(np.linalg.matrix_rank(observability))


def _normalized_covariance_residual(
    transition: np.ndarray,
    measurement: np.ndarray,
    covariance: np.ndarray,
    process_covariance: np.ndarray,
    measurement_covariance: np.ndarray,
) -> float:
    innovation_covariance = measurement @ covariance @ measurement.T + measurement_covariance
    correction = (
        transition
        @ covariance
        @ measurement.T
        @ np.linalg.solve(
            innovation_covariance,
            measurement @ covariance @ transition.T,
        )
    )
    residual = transition @ covariance @ transition.T - covariance - correction + process_covariance
    scale = max(
        float(np.linalg.norm(covariance, ord="fro")),
        float(np.linalg.norm(process_covariance, ord="fro")),
        np.finfo(float).eps,
    )
    return float(np.linalg.norm(residual, ord="fro") / scale)


def synthesize_separate_input_estimator(
    model: SeparateInputRealization,
    *,
    output_scales: object,
    disturbance_scale: float = 0.05,
    measurement_fraction: float = 0.01,
) -> SeparateInputEstimatorDesign:
    """Estimate physical state and four load inputs without imposing ``Bd=Bu M``."""

    state, control, disturbance, output, control_direct, disturbance_direct = _separate_matrices(
        model
    )
    scales = np.asarray(output_scales, dtype=float)
    disturbance_sigma = float(disturbance_scale)
    measurement_sigma = float(measurement_fraction)
    if scales.shape != (4,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("output_scales must contain four positive finite values")
    if not np.isfinite(disturbance_sigma) or disturbance_sigma <= 0.0:
        raise ValueError("disturbance_scale must be positive and finite")
    if not np.isfinite(measurement_sigma) or measurement_sigma <= 0.0:
        raise ValueError("measurement_fraction must be positive and finite")

    order = state.shape[0]
    augmented_order = order + 4
    transition = np.block([[state, disturbance], [np.zeros((4, order)), np.eye(4)]])
    control_matrix = np.vstack((control, np.zeros((4, 4))))
    measurement_matrix = np.hstack((output, disturbance_direct))
    observability_rank = _observability_rank(transition, measurement_matrix)
    if observability_rank != augmented_order:
        raise ValueError("separate-input disturbance-augmented model must be observable")

    process_covariance = np.zeros((augmented_order, augmented_order))
    process_covariance[order:, order:] = np.square(disturbance_sigma) * np.eye(4)
    covariance_floor = 1.0e-12 * max(
        float(np.trace(process_covariance)) / augmented_order,
        np.finfo(float).eps,
    )
    process_covariance += covariance_floor * np.eye(augmented_order)
    measurement_covariance = np.diag(np.square(measurement_sigma * scales))
    try:
        covariance = solve_discrete_are(
            transition.T,
            measurement_matrix.T,
            process_covariance,
            measurement_covariance,
        )
        innovation_covariance = (
            measurement_matrix @ covariance @ measurement_matrix.T + measurement_covariance
        )
        gain = np.linalg.solve(
            innovation_covariance,
            measurement_matrix @ covariance,
        ).T
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise ValueError("separate-input estimator covariance synthesis failed") from exc

    error_poles = np.linalg.eigvals(
        (np.eye(augmented_order) - gain @ measurement_matrix) @ transition
    )
    values = (
        covariance,
        process_covariance,
        measurement_covariance,
        gain,
        error_poles,
    )
    if not all(np.all(np.isfinite(value)) for value in values):
        raise ValueError("separate-input estimator synthesis returned non-finite values")
    return SeparateInputEstimatorDesign(
        transition_matrix=transition,
        control_matrix=control_matrix,
        measurement_matrix=measurement_matrix,
        control_feedthrough_matrix=control_direct.copy(),
        filter_gain=gain,
        covariance=covariance,
        process_covariance=process_covariance,
        measurement_covariance=measurement_covariance,
        physical_state_order=order,
        observability_rank=observability_rank,
        normalized_covariance_residual=_normalized_covariance_residual(
            transition,
            measurement_matrix,
            covariance,
            process_covariance,
            measurement_covariance,
        ),
        error_pole_radius=float(np.max(np.abs(error_poles))),
    )


def advance_separate_input_estimate(
    design: SeparateInputEstimatorDesign,
    *,
    prior_estimate: object,
    previous_delivered_output: object,
    previous_executed_control: object,
) -> SeparateInputEstimateStep:
    """Advance using delivered output and achieved control from the prior sample."""

    prior = np.asarray(prior_estimate, dtype=float)
    delivered = np.asarray(previous_delivered_output, dtype=float)
    executed = np.asarray(previous_executed_control, dtype=float)
    order = design.transition_matrix.shape[0]
    if prior.shape != (order,) or not np.all(np.isfinite(prior)):
        raise ValueError("prior_estimate has invalid shape or values")
    if delivered.shape != (4,) or not np.all(np.isfinite(delivered)):
        raise ValueError("previous_delivered_output has invalid shape or values")
    if executed.shape != (4,) or not np.all(np.isfinite(executed)):
        raise ValueError("previous_executed_control has invalid shape or values")

    innovation = (
        delivered - design.control_feedthrough_matrix @ executed - design.measurement_matrix @ prior
    )
    corrected = prior + design.filter_gain @ innovation
    predicted = design.transition_matrix @ corrected + design.control_matrix @ executed
    if not all(np.all(np.isfinite(value)) for value in (innovation, corrected, predicted)):
        raise ValueError("separate-input estimator step returned non-finite values")
    return SeparateInputEstimateStep(
        predicted_estimate=predicted,
        corrected_estimate=corrected,
        innovation=innovation,
    )


def _control_basis() -> tuple[np.ndarray, np.ndarray]:
    basis = np.column_stack((np.ones(4), active_power_incidence()))
    return basis, np.linalg.inv(basis)


def fallback_separate_input_node_power(
    *,
    previous_commanded_node_power: object,
    soc: object,
    limits: FeedbackLimits = FeedbackLimits(),
) -> np.ndarray:
    """Return the closest ramp-, power-, and energy-feasible move toward zero."""

    previous = np.asarray(previous_commanded_node_power, dtype=float)
    current_soc = np.asarray(soc, dtype=float)
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_commanded_node_power must contain four finite values")
    if current_soc.shape != (4,) or not np.all(np.isfinite(current_soc)):
        raise ValueError("soc must contain four finite values")
    if np.any(np.abs(previous) > limits.node_power):
        raise ValueError("previous_commanded_node_power is outside the power limit")
    if np.any(current_soc < limits.minimum_soc) or np.any(
        current_soc > limits.maximum_soc
    ):
        raise ValueError("soc is outside the frozen bounds")

    ramped = previous + np.clip(-previous, -limits.node_ramp, limits.node_ramp)
    powered = np.clip(ramped, -limits.node_power, limits.node_power)
    soc_factor = (
        limits.sample_period_seconds
        * limits.system_mva
        / (3600.0 * limits.energy_mwh)
    )
    maximum_discharge = (
        (current_soc - limits.minimum_soc)
        * limits.discharge_efficiency
        / soc_factor
    )
    maximum_charge = (
        (limits.maximum_soc - current_soc)
        / (limits.charge_efficiency * soc_factor)
    )
    return np.minimum(np.maximum(powered, -maximum_charge), maximum_discharge)


class SeparateInputHorizonController:
    """Full-output constrained bridge controller with separate disturbance state."""

    def __init__(
        self,
        model: SeparateInputRealization,
        *,
        output_scales: object,
        action_scales: object,
        horizon_steps: int,
        limits: FeedbackLimits = FeedbackLimits(),
        disturbance_scale: float = 0.05,
        measurement_fraction: float = 0.01,
        maximum_solver_iterations: int = 20_000,
        absolute_solver_tolerance: float = 1.0e-9,
        relative_solver_tolerance: float = 1.0e-9,
        feasibility_tolerance: float = 1.0e-8,
    ) -> None:
        estimator = synthesize_separate_input_estimator(
            model,
            output_scales=output_scales,
            disturbance_scale=disturbance_scale,
            measurement_fraction=measurement_fraction,
        )
        y_scales = np.asarray(output_scales, dtype=float)
        u_scales = np.asarray(action_scales, dtype=float)
        horizon = int(horizon_steps)
        if y_scales.shape != (4,) or not np.all(np.isfinite(y_scales)) or np.any(
            y_scales <= 0.0
        ):
            raise ValueError("output_scales must contain four positive finite values")
        if u_scales.shape != (4,) or not np.all(np.isfinite(u_scales)) or np.any(
            u_scales <= 0.0
        ):
            raise ValueError("action_scales must contain four positive finite values")
        if horizon < 1:
            raise ValueError("horizon_steps must be positive")

        augmented_model = DelayAugmentedModel(
            state_matrix=estimator.transition_matrix.copy(),
            input_matrix=estimator.control_matrix.copy(),
            measurement_matrix=estimator.measurement_matrix.copy(),
            regulated_output_matrix=estimator.measurement_matrix.copy(),
            feedthrough_matrix=estimator.control_feedthrough_matrix.copy(),
        )
        error_transition = (
            np.eye(estimator.transition_matrix.shape[0])
            - estimator.filter_gain @ estimator.measurement_matrix
        ) @ estimator.transition_matrix
        horizon_design = ConstrainedHorizonDesign(
            augmented_model=augmented_model,
            filter_gain=estimator.filter_gain.copy(),
            output_scales=y_scales.copy(),
            action_scales=u_scales.copy(),
            horizon_steps=horizon,
            observer_poles=np.linalg.eigvals(error_transition),
            observer_target_max_abs_error=0.0,
        )
        self.model = model
        self.estimator = estimator
        self.horizon_design = horizon_design
        self.limits = limits
        self.identity = SeparateInputControllerIdentity(
            information_pattern="full-output-centralized",
            input_contract="separate-control-and-disturbance",
            request_semantics="node-power-before-physical-projection",
            achieved_semantics="measured-node-power",
            solver="osqp-direct",
            fallback="bounded-ramp-toward-zero",
            horizon_steps=horizon,
            output_scales=tuple(float(value) for value in y_scales),
            action_scales=tuple(float(value) for value in u_scales),
            disturbance_scale=float(disturbance_scale),
            measurement_fraction=float(measurement_fraction),
            maximum_solver_iterations=int(maximum_solver_iterations),
            absolute_solver_tolerance=float(absolute_solver_tolerance),
            relative_solver_tolerance=float(relative_solver_tolerance),
            feasibility_tolerance=float(feasibility_tolerance),
        )
        self._basis, self._inverse_basis = _control_basis()
        self._solver = SparseConstrainedHorizonSolver(
            horizon_design,
            limits,
            maximum_iterations=maximum_solver_iterations,
            absolute_tolerance=absolute_solver_tolerance,
            relative_tolerance=relative_solver_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )

    def reset(self) -> None:
        """Reset solver warm-start state at an episode or case boundary."""

        self._solver.reset()

    def step(
        self,
        *,
        prior_estimate: object,
        previous_delivered_output: object,
        previous_achieved_node_power: object,
        previous_commanded_node_power: object,
        soc: object,
    ) -> SeparateInputHorizonStep:
        """Estimate from achieved power, then issue one constrained request."""

        achieved_node = np.asarray(previous_achieved_node_power, dtype=float)
        if achieved_node.shape != (4,) or not np.all(np.isfinite(achieved_node)):
            raise ValueError("previous_achieved_node_power must contain four finite values")
        achieved_coordinates = self._inverse_basis @ achieved_node
        estimate = advance_separate_input_estimate(
            self.estimator,
            prior_estimate=prior_estimate,
            previous_delivered_output=previous_delivered_output,
            previous_executed_control=achieved_coordinates,
        )
        solver = self._solver.solve(
            corrected_estimate=estimate.predicted_estimate,
            previous_node_action=previous_commanded_node_power,
            soc=soc,
        )
        if solver.solution.feasible:
            requested_coordinates = solver.solution.coordinate_action.copy()
            requested_node = solver.solution.node_action.copy()
            used_fallback = False
            fallback_reason = None
        else:
            requested_node = fallback_separate_input_node_power(
                previous_commanded_node_power=previous_commanded_node_power,
                soc=soc,
                limits=self.limits,
            )
            requested_coordinates = self._inverse_basis @ requested_node
            used_fallback = True
            fallback_reason = solver.solution.message
        return SeparateInputHorizonStep(
            estimate=estimate,
            achieved_control_coordinates=achieved_coordinates,
            requested_control_coordinates=requested_coordinates,
            requested_node_power=requested_node,
            solver=solver,
            used_fallback=used_fallback,
            fallback_reason=fallback_reason,
        )
