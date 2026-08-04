"""Sparse-QP execution for the fixed model-first constrained controller.

The mathematical program is the one defined by
``model_first_constrained_horizon``.  This module changes only its numerical
solution path: matrices that do not vary within a case are cached and the
convex quadratic program is sent to a pinned sparse solver.  It owns no case
selection, scientific admission rule, or result classification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import osqp
from scipy import sparse

from andes_rl_kundur.control.model_first_constrained_horizon import (
    ConstrainedActionSolution,
    ConstrainedHorizonDesign,
    ConstrainedHorizonInfeasible,
    ConstrainedHorizonTrace,
    _advance_soc,
    _coordinate_basis,
    _prediction_matrices,
    _ramp_to_zero_initial_sequence,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class SparseConstrainedActionResult:
    """One controller action plus independently inspectable solver evidence."""

    solution: ConstrainedActionSolution
    predicted_outputs: np.ndarray
    primal_residual: float
    dual_residual: float
    primal_tolerance: float
    dual_tolerance: float
    primal_residual_ratio: float
    dual_residual_ratio: float
    duality_gap: float
    status_value: int


@dataclass(frozen=True)
class SparseConstrainedHorizonTrace:
    """Causal trace with per-sample sparse-solver diagnostics."""

    base: ConstrainedHorizonTrace
    steps: tuple[SparseConstrainedActionResult, ...]

    @property
    def maximum_primal_residual(self) -> float:
        return float(max(step.primal_residual for step in self.steps))

    @property
    def maximum_dual_residual(self) -> float:
        return float(max(step.dual_residual for step in self.steps))

    @property
    def maximum_primal_residual_ratio(self) -> float:
        return float(max(step.primal_residual_ratio for step in self.steps))

    @property
    def maximum_dual_residual_ratio(self) -> float:
        return float(max(step.dual_residual_ratio for step in self.steps))


class SparseConstrainedHorizonSolver:
    """Solve one fixed controller design with a reusable sparse-QP workspace."""

    def __init__(
        self,
        design: ConstrainedHorizonDesign,
        limits: FeedbackLimits = FeedbackLimits(),
        *,
        maximum_iterations: int = 20_000,
        absolute_tolerance: float = 1.0e-9,
        relative_tolerance: float = 1.0e-9,
        feasibility_tolerance: float = 1.0e-8,
        adaptive_rho_interval: int = 25,
    ) -> None:
        self.design = design
        self.limits = limits
        self.maximum_iterations = int(maximum_iterations)
        self.absolute_tolerance = float(absolute_tolerance)
        self.relative_tolerance = float(relative_tolerance)
        self.feasibility_tolerance = float(feasibility_tolerance)
        self.adaptive_rho_interval = int(adaptive_rho_interval)
        if self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be positive")
        if (
            not np.isfinite(self.absolute_tolerance)
            or self.absolute_tolerance <= 0.0
            or not np.isfinite(self.relative_tolerance)
            or self.relative_tolerance <= 0.0
            or not np.isfinite(self.feasibility_tolerance)
            or self.feasibility_tolerance <= 0.0
        ):
            raise ValueError("solver tolerances must be positive and finite")
        if self.adaptive_rho_interval < 1:
            raise ValueError("adaptive_rho_interval must be positive")

        self.horizon = int(design.horizon_steps)
        self.action_count = 4 * self.horizon
        _basis, inverse_basis = _coordinate_basis()
        self.node_to_coordinate = np.kron(np.eye(self.horizon), inverse_basis)
        prediction_free, prediction_forced = _prediction_matrices(
            design.augmented_model, self.horizon
        )
        self.prediction_free = prediction_free
        self.prediction_forced = prediction_forced
        output_weight = np.kron(np.eye(self.horizon), np.diag(1.0 / design.output_scales))
        action_weight = np.kron(np.eye(self.horizon), np.diag(1.0 / design.action_scales))
        self.free_output_map = output_weight @ prediction_free
        self.output_map = output_weight @ prediction_forced @ self.node_to_coordinate
        action_map = action_weight @ self.node_to_coordinate
        raw_quadratic = self.output_map.T @ self.output_map + action_map.T @ action_map
        self.quadratic = 0.5 * (raw_quadratic + raw_quadratic.T)
        self.minimum_action_hessian_eigenvalue = float(
            np.min(np.linalg.eigvalsh(2.0 * self.quadratic))
        )

        identity = np.eye(self.action_count)
        absolute_matrix = np.block([[-identity, identity], [identity, identity]])
        ramp_matrix = np.zeros((self.action_count, self.action_count))
        for step in range(self.horizon):
            row = slice(4 * step, 4 * (step + 1))
            ramp_matrix[row, row] = np.eye(4)
            if step:
                previous_column = slice(4 * (step - 1), 4 * step)
                ramp_matrix[row, previous_column] = -np.eye(4)
        self.ramp_augmented = np.hstack((ramp_matrix, np.zeros_like(ramp_matrix)))
        cumulative = np.kron(np.tril(np.ones((self.horizon, self.horizon))), np.eye(4))
        self.soc_augmented = np.hstack((np.zeros_like(cumulative), cumulative))
        self.soc_factor = (
            limits.sample_period_seconds * limits.system_mva / (3600.0 * limits.energy_mwh)
        )

        variable_count = 2 * self.action_count
        hessian = sparse.block_diag(
            (
                sparse.csc_matrix(2.0 * self.quadratic),
                sparse.csc_matrix((self.action_count, self.action_count)),
            ),
            format="csc",
        )
        self._hessian = sparse.triu(hessian, format="csc")
        self._constraint_matrix = sparse.vstack(
            (
                sparse.csc_matrix(absolute_matrix),
                sparse.csc_matrix(self.ramp_augmented),
                sparse.csc_matrix(self.soc_augmented),
                sparse.eye(variable_count, format="csc"),
            ),
            format="csc",
        )
        self._constraint_count = int(self._constraint_matrix.shape[0])
        lower = np.concatenate(
            (
                np.zeros(2 * self.action_count),
                np.full(self.action_count, -limits.node_ramp),
                np.full(self.action_count, -np.inf),
                np.concatenate(
                    (
                        np.full(self.action_count, -limits.node_power),
                        np.zeros(self.action_count),
                    )
                ),
            )
        )
        upper = np.concatenate(
            (
                np.full(2 * self.action_count, np.inf),
                np.full(self.action_count, limits.node_ramp),
                np.full(self.action_count, np.inf),
                np.full(variable_count, limits.node_power),
            )
        )
        self._workspace = osqp.OSQP(algebra="builtin")
        self._workspace.setup(
            P=self._hessian,
            q=np.zeros(variable_count),
            A=self._constraint_matrix,
            l=lower,
            u=upper,
            verbose=False,
            solver_type="direct",
            max_iter=self.maximum_iterations,
            eps_abs=self.absolute_tolerance,
            eps_rel=self.relative_tolerance,
            polishing=False,
            warm_starting=True,
            adaptive_rho=True,
            adaptive_rho_interval=self.adaptive_rho_interval,
            scaled_termination=False,
            check_termination=25,
        )
        self._last_node_plan: np.ndarray | None = None

    @property
    def action_optimum_is_unique(self) -> bool:
        """Whether the objective is strictly convex in the executed actions."""

        return bool(self.minimum_action_hessian_eigenvalue > 0.0)

    def reset(self) -> None:
        """Reset all adaptive state at a case boundary."""

        self._last_node_plan = None
        self._workspace.warm_start(
            x=np.zeros(2 * self.action_count),
            y=np.zeros(self._constraint_count),
        )

    def _initial_node_sequence(self, previous: np.ndarray, *, warm_start: bool) -> np.ndarray:
        if not warm_start or self._last_node_plan is None:
            return _ramp_to_zero_initial_sequence(
                previous,
                horizon=self.horizon,
                ramp=self.limits.node_ramp,
            )
        shifted = np.empty_like(self._last_node_plan)
        shifted[:-1] = self._last_node_plan[1:]
        shifted[-1] = shifted[-2] + np.clip(
            -shifted[-2], -self.limits.node_ramp, self.limits.node_ramp
        )
        return shifted

    def solve(
        self,
        *,
        corrected_estimate: object,
        previous_node_action: object,
        soc: object,
        warm_start: bool = True,
    ) -> SparseConstrainedActionResult:
        """Solve one sample of the unchanged constrained-horizon program."""

        estimate = np.asarray(corrected_estimate, dtype=float)
        previous = np.asarray(previous_node_action, dtype=float)
        current_soc = np.asarray(soc, dtype=float)
        order = self.design.augmented_model.state_matrix.shape[0]
        if estimate.shape != (order,) or not np.all(np.isfinite(estimate)):
            raise ValueError("corrected_estimate has invalid shape or values")
        if previous.shape != (4,) or not np.all(np.isfinite(previous)):
            raise ValueError("previous_node_action must contain four finite values")
        if current_soc.shape != (4,) or not np.all(np.isfinite(current_soc)):
            raise ValueError("soc must contain four finite values")
        if np.any(np.abs(previous) > self.limits.node_power + self.feasibility_tolerance):
            raise ValueError("previous_node_action is outside the power limit")
        if np.any(current_soc < self.limits.minimum_soc) or np.any(
            current_soc > self.limits.maximum_soc
        ):
            raise ValueError("soc is outside the frozen bounds")

        free_output = self.free_output_map @ estimate
        linear = self.output_map.T @ free_output
        constant = float(free_output @ free_output)
        linear_cost = np.concatenate((2.0 * linear, np.zeros(self.action_count)))
        ramp_lower = np.tile(np.full(4, -self.limits.node_ramp), self.horizon)
        ramp_upper = np.tile(np.full(4, self.limits.node_ramp), self.horizon)
        ramp_lower[:4] += previous
        ramp_upper[:4] += previous
        discharge_capacity = (
            (current_soc - self.limits.minimum_soc)
            * self.limits.discharge_efficiency
            / self.soc_factor
        )
        charge_capacity = (self.limits.maximum_soc - current_soc) / (
            self.limits.charge_efficiency * self.soc_factor
        )
        cumulative_capacity = np.tile(np.minimum(discharge_capacity, charge_capacity), self.horizon)
        lower = np.concatenate(
            (
                np.zeros(2 * self.action_count),
                ramp_lower,
                np.full(self.action_count, -np.inf),
                np.concatenate(
                    (
                        np.full(self.action_count, -self.limits.node_power),
                        np.zeros(self.action_count),
                    )
                ),
            )
        )
        upper = np.concatenate(
            (
                np.full(2 * self.action_count, np.inf),
                ramp_upper,
                cumulative_capacity,
                np.full(2 * self.action_count, self.limits.node_power),
            )
        )
        initial_node = self._initial_node_sequence(previous, warm_start=warm_start).reshape(-1)
        initial = np.concatenate((initial_node, np.abs(initial_node)))
        self._workspace.update(q=linear_cost, l=lower, u=upper)
        self._workspace.warm_start(x=initial)
        raw = self._workspace.solve(raise_error=False)
        values = initial if raw.x is None else np.asarray(raw.x, dtype=float)

        node_actions = values[: self.action_count].reshape(self.horizon, 4)
        absolute_actions = values[self.action_count :].reshape(self.horizon, 4)
        coordinate_actions = (self.node_to_coordinate @ values[: self.action_count]).reshape(
            self.horizon, 4
        )
        ramp_deltas = np.vstack(
            (
                node_actions[:1] - previous.reshape(1, 4),
                np.diff(node_actions, axis=0),
            )
        )
        cumulative_absolute = np.cumsum(absolute_actions, axis=0)
        soc_lower = (
            current_soc - (self.soc_factor / self.limits.discharge_efficiency) * cumulative_absolute
        )
        soc_upper = (
            current_soc + (self.soc_factor * self.limits.charge_efficiency) * cumulative_absolute
        )
        explicit_residuals = np.array(
            [
                np.max(np.abs(node_actions) - self.limits.node_power),
                np.max(np.abs(ramp_deltas) - self.limits.node_ramp),
                np.max(np.abs(node_actions) - absolute_actions),
                np.max(-absolute_actions),
                np.max(self.limits.minimum_soc - soc_lower),
                np.max(soc_upper - self.limits.maximum_soc),
            ]
        )
        maximum_residual = float(max(0.0, np.max(explicit_residuals)))
        primal_residual = float(raw.info.prim_res)
        dual_residual = float(raw.info.dual_res)
        constraint_values = np.asarray(self._constraint_matrix @ values, dtype=float)
        projected = np.minimum(np.maximum(constraint_values, lower), upper)
        primal_tolerance = float(
            self.absolute_tolerance
            + self.relative_tolerance
            * max(
                float(np.linalg.norm(constraint_values, ord=np.inf)),
                float(np.linalg.norm(projected, ord=np.inf)),
            )
        )
        dual_values = np.asarray(raw.y, dtype=float)
        hessian_values = np.concatenate(
            (2.0 * self.quadratic @ values[: self.action_count], np.zeros(self.action_count))
        )
        transpose_dual = np.asarray(self._constraint_matrix.T @ dual_values, dtype=float)
        dual_tolerance = float(
            self.absolute_tolerance
            + self.relative_tolerance
            * max(
                float(np.linalg.norm(hessian_values, ord=np.inf)),
                float(np.linalg.norm(transpose_dual, ord=np.inf)),
                float(np.linalg.norm(linear_cost, ord=np.inf)),
            )
        )
        primal_ratio = float(primal_residual / primal_tolerance)
        dual_ratio = float(dual_residual / dual_tolerance)
        finite = bool(
            np.all(np.isfinite(values))
            and np.isfinite(raw.info.obj_val)
            and np.isfinite(primal_residual)
            and np.isfinite(dual_residual)
            and np.isfinite(primal_ratio)
            and np.isfinite(dual_ratio)
        )
        feasible = bool(
            raw.info.status_val == 1
            and finite
            and maximum_residual <= self.feasibility_tolerance
            and primal_ratio <= 1.0
            and dual_ratio <= 1.0
        )
        if feasible:
            self._last_node_plan = node_actions.copy()
        objective_value = float(
            values[: self.action_count] @ self.quadratic @ values[: self.action_count]
            + 2.0 * linear @ values[: self.action_count]
            + constant
        )
        predicted_outputs = (
            self.prediction_free @ estimate
            + self.prediction_forced @ coordinate_actions.reshape(-1)
        ).reshape(self.horizon, 4)
        solution = ConstrainedActionSolution(
            feasible=feasible,
            coordinate_action=coordinate_actions[0].copy(),
            node_action=node_actions[0].copy(),
            predicted_coordinate_actions=coordinate_actions,
            predicted_node_actions=node_actions,
            predicted_soc_lower_envelope=soc_lower,
            predicted_soc_upper_envelope=soc_upper,
            objective_value=objective_value,
            solver_iterations=int(raw.info.iter),
            maximum_constraint_residual=maximum_residual,
            message=str(raw.info.status),
        )
        return SparseConstrainedActionResult(
            solution=solution,
            predicted_outputs=predicted_outputs,
            primal_residual=primal_residual,
            dual_residual=dual_residual,
            primal_tolerance=primal_tolerance,
            dual_tolerance=dual_tolerance,
            primal_residual_ratio=primal_ratio,
            dual_residual_ratio=dual_ratio,
            duality_gap=float(raw.info.duality_gap),
            status_value=int(raw.info.status_val),
        )


def simulate_sparse_constrained_horizon_feedback(
    plant_realization: StateSpaceRealization,
    disturbance_sequence: object,
    *,
    design: ConstrainedHorizonDesign,
    initial_soc: float | Sequence[float],
    limits: FeedbackLimits = FeedbackLimits(),
    mismatch_transform: object | None = None,
) -> SparseConstrainedHorizonTrace:
    """Run the unchanged causal loop with one fresh sparse workspace."""

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

    solver = SparseConstrainedHorizonSolver(design, limits)
    if not solver.action_optimum_is_unique:
        raise ValueError("action Hessian is not strictly positive definite")
    solver.reset()
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
    step_results: list[SparseConstrainedActionResult] = []

    for step, disturbance in enumerate(disturbances):
        innovation = (
            previous_output - design.augmented_model.measurement_matrix @ estimate_prediction
        )
        corrected_estimate = estimate_prediction + design.filter_gain @ innovation
        result = solver.solve(
            corrected_estimate=corrected_estimate,
            previous_node_action=previous_node_action,
            soc=current_soc,
            warm_start=True,
        )
        solution = result.solution
        maximum_residual = max(maximum_residual, solution.maximum_constraint_residual)
        if not solution.feasible:
            raise ConstrainedHorizonInfeasible(
                f"step {step} finite-horizon solve failed: {solution.message}; "
                f"primal={result.primal_residual:.3e}; "
                f"dual={result.dual_residual:.3e}"
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
        step_results.append(result)

    ramp_deltas = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(~np.isfinite(estimates))
        or np.any(~np.isfinite(innovations))
        or np.any(np.abs(node_actions) > limits.node_power + solver.feasibility_tolerance)
        or np.any(np.abs(ramp_deltas) > limits.node_ramp + solver.feasibility_tolerance)
        or np.any(soc_history < limits.minimum_soc - solver.feasibility_tolerance)
        or np.any(soc_history > limits.maximum_soc + solver.feasibility_tolerance)
    )
    base = ConstrainedHorizonTrace(
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
    return SparseConstrainedHorizonTrace(base=base, steps=tuple(step_results))
