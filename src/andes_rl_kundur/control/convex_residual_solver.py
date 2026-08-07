"""Smooth convex solver for minimum-action residual headroom.

The regulated common-coordinate absolute-value constraint is represented with
epigraph variables, while the differential-coordinate constraint keeps its
exact convex quadratic form.  Physical limits are checked after solving this
endpoint-only superset: a globally optimal superset point that also satisfies
those limits is globally optimal for the original feasible set.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from andes_rl_kundur.control.convex_first_order_certificate import (
    certify_smooth_convex_first_order,
)
from andes_rl_kundur.control.minimum_norm_certificate import MinimumNormCertificate
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence


@dataclass(frozen=True)
class ConvexResidualSolveResult:
    """One independently certified minimum-norm edge-residual result."""

    feasible: bool
    optimizer_status_success: bool
    target_feasible: bool
    edge_actions: np.ndarray
    residual_node_actions: np.ndarray
    counterfactual_node_commands: np.ndarray
    counterfactual_outputs: np.ndarray
    counterfactual_soc: np.ndarray
    objective_value: float
    solver_iterations: int
    maximum_constraint_residual: float
    maximum_target_shortfall: float
    certificate: MinimumNormCertificate
    message: str


def _matrix(values: object, *, name: str, columns: int) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if (
        result.ndim != 2
        or result.shape[0] < 1
        or result.shape[1] != columns
        or not np.all(np.isfinite(result))
    ):
        raise ValueError(f"{name} must be a non-empty finite matrix with {columns} columns")
    return result


def _advance_soc(
    initial_soc: np.ndarray,
    node_commands: np.ndarray,
    limits: FeedbackLimits,
) -> np.ndarray:
    factor = limits.sample_period_seconds * limits.system_mva / (
        3600.0 * limits.energy_mwh
    )
    path = np.empty((node_commands.shape[0] + 1, 4))
    path[0] = initial_soc
    for step, command in enumerate(node_commands):
        delta = np.where(
            command >= 0.0,
            -factor * command / limits.discharge_efficiency,
            -factor * command * limits.charge_efficiency,
        )
        path[step + 1] = path[step] + delta
    return path


def solve_convex_minimum_norm_edge_residual(
    *,
    base_outputs: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    response_map: object,
    initial_edge_actions: object | None = None,
    use_feasibility_start: bool = True,
    limits: FeedbackLimits = FeedbackLimits(),
    minimum_improvement_fraction: float,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> ConvexResidualSolveResult:
    """Solve and independently certify the convex minimum-action problem."""

    outputs = _matrix(base_outputs, name="base_outputs", columns=4)
    commands = _matrix(base_node_commands, name="base_node_commands", columns=4)
    if commands.shape[0] != outputs.shape[0]:
        raise ValueError("base outputs and commands must share one horizon")
    previous = np.asarray(previous_node_command, dtype=float)
    soc0 = np.asarray(initial_soc, dtype=float)
    steps = outputs.shape[0]
    response = np.asarray(response_map, dtype=float)
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_node_command must contain four finite values")
    if soc0.shape != (4,) or not np.all(np.isfinite(soc0)):
        raise ValueError("initial_soc must contain four finite values")
    if response.shape != (4 * steps, 3 * steps) or not np.all(np.isfinite(response)):
        raise ValueError("response_map has incompatible shape or values")
    warm_edges = None
    if initial_edge_actions is not None:
        warm_edges = np.asarray(initial_edge_actions, dtype=float)
        if warm_edges.shape != (steps, 3) or not np.all(np.isfinite(warm_edges)):
            raise ValueError("initial_edge_actions must be a finite horizon-by-three matrix")
    if not isinstance(use_feasibility_start, bool):
        raise ValueError("use_feasibility_start must be boolean")
    improvement = float(minimum_improvement_fraction)
    iterations = int(maximum_iterations)
    function_tol = float(function_tolerance)
    feasibility_tol = float(feasibility_tolerance)
    if not np.isfinite(improvement) or not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    if iterations < 1 or not np.isfinite(function_tol) or function_tol <= 0.0:
        raise ValueError("solver budget must be positive")
    if not np.isfinite(feasibility_tol) or feasibility_tol <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")

    sample_period = float(limits.sample_period_seconds)
    action_scale = float(limits.node_ramp)
    incidence = np.asarray(active_power_incidence(), dtype=float)
    edge_count = 3 * steps
    common_rows = np.arange(0, 4 * steps, 4)
    differential_rows = np.setdiff1d(np.arange(4 * steps), common_rows)
    common_base = outputs[:, 0]
    differential_base = outputs[:, 1:].reshape(-1)
    common_response = action_scale * response[common_rows]
    differential_response = action_scale * response[differential_rows]
    common_sum = float(np.sum(np.abs(common_base)))
    differential_sum = float(differential_base @ differential_base)
    if common_sum <= 0.0 or differential_sum <= 0.0:
        raise ValueError("both base endpoints must be positive")
    common_scale = common_sum / steps
    normalized_common_base = common_base / common_scale
    normalized_common_response = common_response / common_scale

    common_budget = (1.0 - improvement) * common_sum / common_scale
    objective_scale = float(np.sqrt(feasibility_tol))

    def objective(values: np.ndarray) -> float:
        edges = values[:edge_count]
        return float(edges @ edges / objective_scale)

    def objective_jacobian(values: np.ndarray) -> np.ndarray:
        result = np.zeros_like(values)
        result[:edge_count] = 2.0 * values[:edge_count] / objective_scale
        return result

    def smooth_constraints(values: np.ndarray) -> np.ndarray:
        edges = values[:edge_count]
        epigraph = values[edge_count:]
        common = normalized_common_base + normalized_common_response @ edges
        differential = differential_base + differential_response @ edges
        return np.concatenate(
            (
                np.asarray([(common_budget - np.sum(epigraph)) / steps]),
                epigraph - common,
                epigraph + common,
                np.asarray(
                    [
                        1.0
                        - improvement
                        - float(differential @ differential) / differential_sum
                    ]
                ),
            )
        )

    def smooth_constraint_jacobian(values: np.ndarray) -> np.ndarray:
        edges = values[:edge_count]
        differential = differential_base + differential_response @ edges
        return np.vstack(
            (
                np.hstack(
                    (
                        np.zeros((1, edge_count)),
                        -np.ones((1, steps)) / steps,
                    )
                ),
                np.hstack((-normalized_common_response, np.eye(steps))),
                np.hstack((normalized_common_response, np.eye(steps))),
                np.hstack(
                    (
                        (
                            -2.0
                            * differential.reshape(1, -1)
                            @ differential_response
                            / differential_sum
                        ),
                        np.zeros((1, steps)),
                    )
                ),
            )
        )

    initial = np.concatenate((np.zeros(edge_count), np.abs(normalized_common_base)))
    zero_initial = initial.copy()
    differential_constraint_index = 1 + 2 * steps

    def relaxed_objective(values: np.ndarray) -> float:
        slacks = values[-2:]
        return float(slacks @ slacks)

    def relaxed_objective_jacobian(values: np.ndarray) -> np.ndarray:
        result = np.zeros_like(values)
        result[-2:] = 2.0 * values[-2:]
        return result

    def relaxed_constraints(values: np.ndarray) -> np.ndarray:
        result = smooth_constraints(values[:-2])
        result[0] += values[-2]
        result[differential_constraint_index] += values[-1]
        return result

    def relaxed_constraint_jacobian(values: np.ndarray) -> np.ndarray:
        base = smooth_constraint_jacobian(values[:-2])
        result = np.hstack((base, np.zeros((base.shape[0], 2))))
        result[0, -2] = 1.0
        result[differential_constraint_index, -1] = 1.0
        return result

    relaxed_initial = np.concatenate((initial, np.asarray([improvement, improvement])))
    relaxed = minimize(
        relaxed_objective,
        relaxed_initial,
        jac=relaxed_objective_jacobian,
        method="SLSQP",
        bounds=[(None, None)] * edge_count
        + [(0.0, None)] * steps
        + [(0.0, None)] * 2,
        constraints=(
            {
                "type": "ineq",
                "fun": relaxed_constraints,
                "jac": relaxed_constraint_jacobian,
            },
        ),
        options={"maxiter": iterations, "ftol": function_tol, "disp": False},
    )
    relaxed_edges = np.asarray(relaxed.x[:edge_count], dtype=float)
    relaxed_common = normalized_common_base + normalized_common_response @ relaxed_edges
    if use_feasibility_start:
        initial = np.concatenate((relaxed_edges, np.abs(relaxed_common)))
    else:
        initial = zero_initial
    if warm_edges is not None:
        warm_scaled_edges = warm_edges.reshape(-1) / action_scale
        warm_common = normalized_common_base + (
            normalized_common_response @ warm_scaled_edges
        )
        initial = np.concatenate((warm_scaled_edges, np.abs(warm_common)))
    optimized = minimize(
        objective,
        initial,
        jac=objective_jacobian,
        method="SLSQP",
        bounds=[(None, None)] * edge_count + [(0.0, None)] * steps,
        constraints=(
            {
                "type": "ineq",
                "fun": smooth_constraints,
                "jac": smooth_constraint_jacobian,
            },
        ),
        options={"maxiter": iterations, "ftol": function_tol, "disp": False},
    )
    scaled_edges = np.asarray(optimized.x[:edge_count], dtype=float)
    edges = (action_scale * scaled_edges).reshape(steps, 3)
    residual_nodes = edges @ incidence.T
    total_commands = commands + residual_nodes
    counterfactual = outputs + (response @ edges.reshape(-1)).reshape(steps, 4)
    soc_path = _advance_soc(soc0, total_commands, limits)
    common_value = sample_period * float(np.sum(np.abs(counterfactual[:, 0])))
    differential_value = sample_period * float(
        np.sum(np.square(counterfactual[:, 1:]))
    )
    common_baseline = sample_period * common_sum
    differential_baseline = sample_period * differential_sum
    endpoint_slacks = np.asarray(
        (
            (1.0 - improvement) * common_baseline - common_value,
            (1.0 - improvement) * differential_baseline - differential_value,
        )
    )
    ramps = np.vstack(
        (total_commands[:1] - previous.reshape(1, 4), np.diff(total_commands, axis=0))
    )
    physical_slacks = np.concatenate(
        (
            (limits.node_power - np.abs(total_commands)).reshape(-1),
            (limits.node_ramp - np.abs(ramps)).reshape(-1),
            (soc_path[1:] - limits.minimum_soc).reshape(-1),
            (limits.maximum_soc - soc_path[1:]).reshape(-1),
        )
    )
    original_slacks = np.concatenate((endpoint_slacks, physical_slacks))
    maximum_residual = float(max(0.0, -float(np.min(original_slacks))))
    maximum_target_shortfall = float(max(0.0, -float(np.min(endpoint_slacks))))

    certificate_common = (
        normalized_common_base + normalized_common_response @ scaled_edges
    )
    certificate_point = np.concatenate((scaled_edges, np.abs(certificate_common)))
    certificate = certify_smooth_convex_first_order(
        point=certificate_point,
        objective_gradient=lambda values: np.concatenate(
            (2.0 * values[:edge_count], np.zeros(steps))
        ),
        constraint_function=smooth_constraints,
        constraint_jacobian=smooth_constraint_jacobian,
        feasibility_tolerance=feasibility_tol,
    )
    finite = bool(
        np.all(np.isfinite(optimized.x))
        and np.isfinite(optimized.fun)
        and np.all(np.isfinite(original_slacks))
    )
    target_feasible = bool(maximum_target_shortfall <= feasibility_tol)
    feasible = bool(
        finite
        and target_feasible
        and maximum_residual <= feasibility_tol
        and certificate.valid
    )
    return ConvexResidualSolveResult(
        feasible=feasible,
        optimizer_status_success=bool(optimized.success),
        target_feasible=target_feasible,
        edge_actions=edges,
        residual_node_actions=residual_nodes,
        counterfactual_node_commands=total_commands,
        counterfactual_outputs=counterfactual,
        counterfactual_soc=soc_path,
        objective_value=float(edges.reshape(-1) @ edges.reshape(-1)),
        solver_iterations=int(optimized.nit),
        maximum_constraint_residual=maximum_residual,
        maximum_target_shortfall=maximum_target_shortfall,
        certificate=certificate,
        message=f"{optimized.message}; independent certificate: {certificate.reason}",
    )
