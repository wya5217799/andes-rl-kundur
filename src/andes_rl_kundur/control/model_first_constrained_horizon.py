"""Actuator-constrained finite-horizon output-feedback primitives.

The module builds one fixed corrected-state observer and solves model-only
finite-horizon control actions against explicit node power, ramp, and energy
constraints. It reads no repository artifacts, runs no physical simulator,
and owns no scientific classification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linear_sum_assignment, minimize
from scipy.signal import place_poles

from andes_rl_kundur.control.model_first_observer_lqr import (
    DelayAugmentedModel,
    build_delay_augmented_model,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class ConstrainedHorizonDesign:
    """Fixed model, observer, normalization, and horizon for one controller."""

    augmented_model: DelayAugmentedModel
    filter_gain: np.ndarray
    output_scales: np.ndarray
    action_scales: np.ndarray
    horizon_steps: int
    observer_poles: np.ndarray
    observer_target_max_abs_error: float


@dataclass(frozen=True)
class ConstrainedActionSolution:
    """Observable optimizer result for one causal control sample."""

    feasible: bool
    coordinate_action: np.ndarray
    node_action: np.ndarray
    predicted_coordinate_actions: np.ndarray
    predicted_node_actions: np.ndarray
    predicted_soc_lower_envelope: np.ndarray
    predicted_soc_upper_envelope: np.ndarray
    objective_value: float
    solver_iterations: int
    maximum_constraint_residual: float
    message: str


@dataclass(frozen=True)
class ConstrainedHorizonTrace:
    """Observable result of one causal constrained-feedback simulation."""

    outputs: np.ndarray
    model_outputs: np.ndarray
    coordinate_actions: np.ndarray
    node_actions: np.ndarray
    soc: np.ndarray
    estimates: np.ndarray
    innovations: np.ndarray
    solver_iterations: np.ndarray
    solver_failure_count: int
    maximum_constraint_residual: float
    constraint_violation_count: int

    @property
    def output_energy(self) -> float:
        return float(np.sum(np.square(self.outputs)))

    @property
    def coordinate_action_energy(self) -> float:
        return float(np.sum(np.square(self.coordinate_actions)))


class ConstrainedHorizonInfeasible(RuntimeError):
    """Raised before actuation when one finite-horizon solve is infeasible."""


def _positive_scales(values: object, *, name: str) -> np.ndarray:
    scales = np.asarray(values, dtype=float)
    if scales.shape != (4,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError(f"{name} must contain four positive finite values")
    return scales


def _observer_target(values: object, dimension: int) -> np.ndarray:
    target = np.asarray(values, dtype=complex)
    if target.shape != (dimension,) or not np.all(np.isfinite(target)):
        raise ValueError("observer_target_poles must match the augmented state")
    return target


def _target_error(achieved: np.ndarray, target: np.ndarray) -> float:
    cost = np.abs(achieved.reshape(-1, 1) - target.reshape(1, -1))
    rows, columns = linear_sum_assignment(cost)
    return float(np.max(cost[rows, columns]))


def _coordinate_basis() -> tuple[np.ndarray, np.ndarray]:
    basis = np.column_stack((np.ones(4), active_power_incidence()))
    return basis, np.linalg.inv(basis)


def _prediction_matrices(
    model: DelayAugmentedModel,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray]:
    state = model.state_matrix
    inputs = model.input_matrix
    regulated = model.regulated_output_matrix
    feedthrough = model.feedthrough_matrix
    order = state.shape[0]
    free = np.zeros((4 * horizon, order))
    forced = np.zeros((4 * horizon, 4 * horizon))
    powers = [np.eye(order)]
    for _ in range(horizon):
        powers.append(powers[-1] @ state)
    for step in range(horizon):
        row = slice(4 * step, 4 * (step + 1))
        free[row] = regulated @ powers[step]
        for action_step in range(step):
            column = slice(4 * action_step, 4 * (action_step + 1))
            forced[row, column] = (
                regulated @ powers[step - 1 - action_step] @ inputs
            )
        column = slice(4 * step, 4 * (step + 1))
        forced[row, column] += feedthrough
    return free, forced


def _ramp_to_zero_initial_sequence(
    previous: np.ndarray,
    *,
    horizon: int,
    ramp: float,
) -> np.ndarray:
    sequence = np.zeros((horizon, 4))
    current = previous.copy()
    for step in range(horizon):
        current = current + np.clip(-current, -ramp, ramp)
        sequence[step] = current
    return sequence


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


def synthesize_constrained_horizon(
    realization: StateSpaceRealization,
    *,
    output_scales: object,
    action_scales: object,
    observer_target_poles: object,
    horizon_steps: int,
    method: str = "YT",
    relative_tolerance: float = 1.0e-6,
    maximum_iterations: int = 100,
) -> ConstrainedHorizonDesign:
    """Place one fixed corrected-state observer for finite-horizon control."""

    y_scales = _positive_scales(output_scales, name="output_scales")
    u_scales = _positive_scales(action_scales, name="action_scales")
    horizon = int(horizon_steps)
    tolerance = float(relative_tolerance)
    iterations = int(maximum_iterations)
    if horizon < 1:
        raise ValueError("horizon_steps must be positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("relative_tolerance must be positive and finite")
    if iterations < 1:
        raise ValueError("maximum_iterations must be positive")

    augmented = build_delay_augmented_model(realization)
    state = augmented.state_matrix
    measured = augmented.measurement_matrix
    target = _observer_target(observer_target_poles, state.shape[0])
    placement = place_poles(
        state.T,
        (measured @ state).T,
        target,
        method=method,
        rtol=tolerance,
        maxiter=iterations,
    )
    filter_gain = np.asarray(placement.gain_matrix.T, dtype=float)
    poles = np.linalg.eigvals(
        (np.eye(state.shape[0]) - filter_gain @ measured) @ state
    )
    if not np.all(np.isfinite(filter_gain)) or not np.all(np.isfinite(poles)):
        raise ValueError("observer placement returned non-finite values")
    return ConstrainedHorizonDesign(
        augmented_model=augmented,
        filter_gain=filter_gain,
        output_scales=y_scales.copy(),
        action_scales=u_scales.copy(),
        horizon_steps=horizon,
        observer_poles=poles,
        observer_target_max_abs_error=_target_error(poles, target),
    )


def solve_constrained_horizon_action(
    design: ConstrainedHorizonDesign,
    *,
    corrected_estimate: object,
    previous_node_action: object,
    soc: object,
    limits: FeedbackLimits = FeedbackLimits(),
    maximum_iterations: int = 200,
    function_tolerance: float = 1.0e-9,
    feasibility_tolerance: float = 1.0e-8,
) -> ConstrainedActionSolution:
    """Solve one deterministic constrained finite-horizon action sequence."""

    estimate = np.asarray(corrected_estimate, dtype=float)
    previous = np.asarray(previous_node_action, dtype=float)
    current_soc = np.asarray(soc, dtype=float)
    order = design.augmented_model.state_matrix.shape[0]
    horizon = design.horizon_steps
    if estimate.shape != (order,) or not np.all(np.isfinite(estimate)):
        raise ValueError("corrected_estimate has invalid shape or values")
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_node_action must contain four finite values")
    if current_soc.shape != (4,) or not np.all(np.isfinite(current_soc)):
        raise ValueError("soc must contain four finite values")
    if np.any(np.abs(previous) > limits.node_power + feasibility_tolerance):
        raise ValueError("previous_node_action is outside the power limit")
    if (
        np.any(current_soc < limits.minimum_soc)
        or np.any(current_soc > limits.maximum_soc)
    ):
        raise ValueError("soc is outside the frozen bounds")
    iterations = int(maximum_iterations)
    ftol = float(function_tolerance)
    tolerance = float(feasibility_tolerance)
    if iterations < 1 or not np.isfinite(ftol) or ftol <= 0.0:
        raise ValueError("solver budget must be positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")

    _basis, inverse_basis = _coordinate_basis()
    node_to_coordinate = np.kron(np.eye(horizon), inverse_basis)
    free, forced = _prediction_matrices(design.augmented_model, horizon)
    output_weight = np.kron(
        np.eye(horizon), np.diag(1.0 / design.output_scales)
    )
    action_weight = np.kron(
        np.eye(horizon), np.diag(1.0 / design.action_scales)
    )
    output_map = output_weight @ forced @ node_to_coordinate
    free_output = output_weight @ free @ estimate
    action_map = action_weight @ node_to_coordinate
    quadratic = output_map.T @ output_map + action_map.T @ action_map
    linear = output_map.T @ free_output
    constant = float(free_output @ free_output)
    action_count = 4 * horizon
    def objective(values: np.ndarray) -> float:
        node = values[:action_count]
        return float(
            node @ quadratic @ node
            + 2.0 * linear @ node
            + constant
        )

    def gradient(values: np.ndarray) -> np.ndarray:
        node = values[:action_count]
        return np.concatenate(
            (
                2.0 * (quadratic @ node + linear),
                np.zeros(action_count),
            )
        )

    identity = np.eye(action_count)
    absolute_constraint = LinearConstraint(
        np.block([[-identity, identity], [identity, identity]]),
        np.zeros(2 * action_count),
        np.full(2 * action_count, np.inf),
    )
    ramp_matrix = np.zeros((action_count, action_count))
    for step in range(horizon):
        row = slice(4 * step, 4 * (step + 1))
        ramp_matrix[row, row] = np.eye(4)
        if step:
            previous_column = slice(4 * (step - 1), 4 * step)
            ramp_matrix[row, previous_column] = -np.eye(4)
    ramp_lower = np.tile(np.full(4, -limits.node_ramp), horizon)
    ramp_upper = np.tile(np.full(4, limits.node_ramp), horizon)
    ramp_lower[:4] += previous
    ramp_upper[:4] += previous
    ramp_constraint = LinearConstraint(
        np.hstack((ramp_matrix, np.zeros_like(ramp_matrix))),
        ramp_lower,
        ramp_upper,
    )

    soc_factor = (
        limits.sample_period_seconds
        * limits.system_mva
        / (3600.0 * limits.energy_mwh)
    )
    cumulative = np.kron(np.tril(np.ones((horizon, horizon))), np.eye(4))
    discharge_capacity = (
        (current_soc - limits.minimum_soc)
        * limits.discharge_efficiency
        / soc_factor
    )
    charge_capacity = (
        (limits.maximum_soc - current_soc)
        / (limits.charge_efficiency * soc_factor)
    )
    cumulative_capacity = np.tile(
        np.minimum(discharge_capacity, charge_capacity), horizon
    )
    soc_constraint = LinearConstraint(
        np.hstack((np.zeros_like(cumulative), cumulative)),
        np.full(action_count, -np.inf),
        cumulative_capacity,
    )

    initial_node = _ramp_to_zero_initial_sequence(
        previous, horizon=horizon, ramp=limits.node_ramp
    ).reshape(-1)
    initial = np.concatenate((initial_node, np.abs(initial_node)))
    bounds = Bounds(
        np.concatenate(
            (
                np.full(action_count, -limits.node_power),
                np.zeros(action_count),
            )
        ),
        np.full(2 * action_count, limits.node_power),
    )
    result = minimize(
        objective,
        initial,
        jac=gradient,
        method="SLSQP",
        bounds=bounds,
        constraints=(absolute_constraint, ramp_constraint, soc_constraint),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )

    values = np.asarray(result.x, dtype=float)
    node_actions = values[:action_count].reshape(horizon, 4)
    absolute_actions = values[action_count:].reshape(horizon, 4)
    coordinate_actions = (node_to_coordinate @ values[:action_count]).reshape(
        horizon, 4
    )
    ramp_deltas = np.vstack(
        (node_actions[:1] - previous.reshape(1, 4), np.diff(node_actions, axis=0))
    )
    cumulative_absolute = np.cumsum(absolute_actions, axis=0)
    soc_lower = current_soc - (
        soc_factor / limits.discharge_efficiency
    ) * cumulative_absolute
    soc_upper = current_soc + (
        soc_factor * limits.charge_efficiency
    ) * cumulative_absolute
    residuals = np.array(
        [
            np.max(np.abs(node_actions) - limits.node_power),
            np.max(np.abs(ramp_deltas) - limits.node_ramp),
            np.max(np.abs(node_actions) - absolute_actions),
            np.max(limits.minimum_soc - soc_lower),
            np.max(soc_upper - limits.maximum_soc),
        ]
    )
    maximum_residual = float(max(0.0, np.max(residuals)))
    feasible = bool(
        result.success
        and np.all(np.isfinite(values))
        and np.isfinite(result.fun)
        and maximum_residual <= tolerance
    )
    return ConstrainedActionSolution(
        feasible=feasible,
        coordinate_action=coordinate_actions[0].copy(),
        node_action=node_actions[0].copy(),
        predicted_coordinate_actions=coordinate_actions,
        predicted_node_actions=node_actions,
        predicted_soc_lower_envelope=soc_lower,
        predicted_soc_upper_envelope=soc_upper,
        objective_value=float(result.fun),
        solver_iterations=int(result.nit),
        maximum_constraint_residual=maximum_residual,
        message=str(result.message),
    )


def simulate_constrained_horizon_feedback(
    plant_realization: StateSpaceRealization,
    disturbance_sequence: object,
    *,
    design: ConstrainedHorizonDesign,
    initial_soc: float | Sequence[float],
    limits: FeedbackLimits = FeedbackLimits(),
    mismatch_transform: object | None = None,
    maximum_solver_iterations: int = 200,
    function_tolerance: float = 1.0e-9,
    feasibility_tolerance: float = 1.0e-8,
) -> ConstrainedHorizonTrace:
    """Run causal output feedback without a post-solve actuator projection."""

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
        or design.filter_gain.shape != (estimate_order, 4)
    ):
        raise ValueError("plant and constrained observer dimensions are inconsistent")

    current_soc = np.broadcast_to(np.asarray(initial_soc, dtype=float), (4,)).copy()
    if (
        not np.all(np.isfinite(current_soc))
        or np.any(current_soc < limits.minimum_soc)
        or np.any(current_soc > limits.maximum_soc)
    ):
        raise ValueError("initial_soc is outside the frozen bounds")

    state = np.zeros(plant_order)
    estimate_prediction = np.zeros(estimate_order)
    previous_output = np.zeros(4)
    previous_node_action = np.zeros(4)
    outputs = np.zeros_like(disturbances)
    model_outputs = np.zeros_like(disturbances)
    coordinate_actions = np.zeros_like(disturbances)
    node_actions = np.zeros_like(disturbances)
    estimates = np.zeros((disturbances.shape[0], estimate_order))
    innovations = np.zeros_like(disturbances)
    solver_iterations = np.zeros(disturbances.shape[0], dtype=int)
    soc_history = np.zeros((disturbances.shape[0] + 1, 4))
    soc_history[0] = current_soc
    maximum_residual = 0.0

    for step, disturbance in enumerate(disturbances):
        innovation = (
            previous_output
            - design.augmented_model.measurement_matrix @ estimate_prediction
        )
        corrected_estimate = estimate_prediction + design.filter_gain @ innovation
        solution = solve_constrained_horizon_action(
            design,
            corrected_estimate=corrected_estimate,
            previous_node_action=previous_node_action,
            soc=current_soc,
            limits=limits,
            maximum_iterations=maximum_solver_iterations,
            function_tolerance=function_tolerance,
            feasibility_tolerance=feasibility_tolerance,
        )
        maximum_residual = max(
            maximum_residual, solution.maximum_constraint_residual
        )
        if not solution.feasible:
            raise ConstrainedHorizonInfeasible(
                f"step {step} finite-horizon solve failed: {solution.message}"
            )
        coordinate_action = solution.coordinate_action
        node_action = solution.node_action
        total_input = disturbance + coordinate_action
        model_output = plant_outputs @ state + plant_feedthrough @ total_input
        output = model_output + mismatch @ model_output
        state = plant_state @ state + plant_inputs @ total_input
        current_soc = _advance_soc(current_soc, node_action, limits)
        estimate_prediction = (
            design.augmented_model.state_matrix @ corrected_estimate
            + design.augmented_model.input_matrix @ coordinate_action
        )

        outputs[step] = output
        model_outputs[step] = model_output
        coordinate_actions[step] = coordinate_action
        node_actions[step] = node_action
        estimates[step] = corrected_estimate
        innovations[step] = innovation
        solver_iterations[step] = solution.solver_iterations
        soc_history[step + 1] = current_soc
        previous_output = output
        previous_node_action = node_action

    ramp_deltas = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(~np.isfinite(estimates))
        or np.any(~np.isfinite(innovations))
        or np.any(np.abs(node_actions) > limits.node_power + feasibility_tolerance)
        or np.any(np.abs(ramp_deltas) > limits.node_ramp + feasibility_tolerance)
        or np.any(soc_history < limits.minimum_soc - feasibility_tolerance)
        or np.any(soc_history > limits.maximum_soc + feasibility_tolerance)
    )
    return ConstrainedHorizonTrace(
        outputs=outputs,
        model_outputs=model_outputs,
        coordinate_actions=coordinate_actions,
        node_actions=node_actions,
        soc=soc_history,
        estimates=estimates,
        innovations=innovations,
        solver_iterations=solver_iterations,
        solver_failure_count=0,
        maximum_constraint_residual=maximum_residual,
        constraint_violation_count=violations,
    )
