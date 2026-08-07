"""Scale-stable feasibility relaxation for the R347 residual analysis."""

from __future__ import annotations

import numpy as np
from probes.r345_residual_headroom import ResidualSolveResult, endpoint_values
from scipy.optimize import minimize

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence


def _finite_matrix(values: object, *, name: str, columns: int) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if (
        matrix.ndim != 2
        or matrix.shape[0] < 1
        or matrix.shape[1] != columns
        or not np.all(np.isfinite(matrix))
    ):
        raise ValueError(f"{name} must be a non-empty finite matrix with {columns} columns")
    return matrix


def _advance_soc_path(
    initial_soc: np.ndarray,
    node_commands: np.ndarray,
    limits: FeedbackLimits,
) -> np.ndarray:
    factor = limits.sample_period_seconds * limits.system_mva / (3600.0 * limits.energy_mwh)
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


def solve_scale_stable_minimum_norm_edge_residual(
    *,
    base_outputs: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    response_map: object,
    limits: FeedbackLimits = FeedbackLimits(),
    minimum_improvement_fraction: float,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> ResidualSolveResult:
    """Solve the R345 problem with dimensionless relative feasibility slacks."""

    outputs = _finite_matrix(base_outputs, name="base_outputs", columns=4)
    commands = _finite_matrix(
        base_node_commands,
        name="base_node_commands",
        columns=4,
    )
    if commands.shape[0] != outputs.shape[0]:
        raise ValueError("base outputs and commands must share one horizon")
    previous = np.asarray(previous_node_command, dtype=float)
    soc0 = np.asarray(initial_soc, dtype=float)
    response = np.asarray(response_map, dtype=float)
    steps = outputs.shape[0]
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_node_command must contain four finite values")
    if soc0.shape != (4,) or not np.all(np.isfinite(soc0)):
        raise ValueError("initial_soc must contain four finite values")
    if response.shape != (4 * steps, 3 * steps) or not np.all(np.isfinite(response)):
        raise ValueError("response_map has incompatible shape or values")
    improvement = float(minimum_improvement_fraction)
    if not np.isfinite(improvement) or not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    iterations = int(maximum_iterations)
    ftol = float(function_tolerance)
    tolerance = float(feasibility_tolerance)
    if iterations < 1 or not np.isfinite(ftol) or ftol <= 0.0:
        raise ValueError("solver budget must be positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")

    base_endpoints = endpoint_values(
        outputs,
        sample_period_seconds=limits.sample_period_seconds,
    )
    if any(value <= 0.0 for value in base_endpoints.values()):
        raise ValueError("both base endpoints must be positive")
    baseline = np.asarray(
        [
            base_endpoints["common_coordinate_iae"],
            base_endpoints["differential_coordinate_energy"],
        ]
    )
    targets = (1.0 - improvement) * baseline
    incidence = np.asarray(active_power_incidence(), dtype=float)
    if incidence.shape != (4, 3):
        raise ValueError("active-power incidence must be four-by-three")

    def decode(
        values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        edges = values.reshape(steps, 3)
        residual_nodes = edges @ incidence.T
        total_commands = commands + residual_nodes
        counterfactual = outputs + (response @ values).reshape(steps, 4)
        soc_path = _advance_soc_path(soc0, total_commands, limits)
        return edges, residual_nodes, total_commands, counterfactual, soc_path

    def objective(values: np.ndarray) -> float:
        return float(values @ values)

    def gradient(values: np.ndarray) -> np.ndarray:
        return 2.0 * values

    def endpoint_constraints(values: np.ndarray) -> np.ndarray:
        *_unused, counterfactual, _soc = decode(values)
        endpoints = endpoint_values(
            counterfactual,
            sample_period_seconds=limits.sample_period_seconds,
        )
        return targets - np.asarray(
            [
                endpoints["common_coordinate_iae"],
                endpoints["differential_coordinate_energy"],
            ]
        )

    def physical_constraints(values: np.ndarray) -> np.ndarray:
        _edges, _residual, total, _counterfactual, soc_path = decode(values)
        ramps = np.vstack((total[:1] - previous.reshape(1, 4), np.diff(total, axis=0)))
        return np.concatenate(
            (
                (limits.node_power - np.abs(total)).reshape(-1),
                (limits.node_ramp - np.abs(ramps)).reshape(-1),
                (soc_path[1:] - limits.minimum_soc).reshape(-1),
                (limits.maximum_soc - soc_path[1:]).reshape(-1),
            )
        )

    edge_count = 3 * steps
    relaxed_initial = np.zeros(edge_count + 2)
    relaxed_initial[-2:] = improvement

    def relaxed_objective(values: np.ndarray) -> float:
        relative_slacks = values[edge_count:]
        return float(relative_slacks @ relative_slacks)

    def relaxed_gradient(values: np.ndarray) -> np.ndarray:
        gradient_values = np.zeros_like(values)
        gradient_values[edge_count:] = 2.0 * values[edge_count:]
        return gradient_values

    def relaxed_endpoint_constraints(values: np.ndarray) -> np.ndarray:
        return endpoint_constraints(values[:edge_count]) + (baseline * values[edge_count:])

    def relaxed_physical_constraints(values: np.ndarray) -> np.ndarray:
        return physical_constraints(values[:edge_count])

    relaxed_result = minimize(
        relaxed_objective,
        relaxed_initial,
        jac=relaxed_gradient,
        method="SLSQP",
        constraints=(
            {"type": "ineq", "fun": lambda values: values[edge_count:]},
            {"type": "ineq", "fun": relaxed_endpoint_constraints},
            {"type": "ineq", "fun": relaxed_physical_constraints},
        ),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )
    relaxed_values = np.asarray(relaxed_result.x, dtype=float)
    relaxed_edges = relaxed_values[:edge_count]
    relaxed_endpoint_slack = relaxed_endpoint_constraints(relaxed_values)
    relaxed_physical_slack = relaxed_physical_constraints(relaxed_values)
    relaxed_nonnegative_slack = relaxed_values[edge_count:]
    relaxed_constraint_residual = float(
        max(
            0.0,
            -float(np.min(relaxed_endpoint_slack)),
            -float(np.min(relaxed_physical_slack)),
            -float(np.min(relaxed_nonnegative_slack)),
        )
    )
    relaxed_valid = bool(
        relaxed_result.success
        and np.all(np.isfinite(relaxed_values))
        and np.isfinite(relaxed_result.fun)
        and relaxed_constraint_residual <= tolerance
    )
    target_slack = endpoint_constraints(relaxed_edges)
    maximum_target_shortfall = float(max(0.0, -float(np.min(target_slack))))
    target_feasible = bool(relaxed_valid and maximum_target_shortfall <= tolerance)
    if not target_feasible:
        edges, residual_nodes, total_commands, counterfactual, soc_path = decode(relaxed_edges)
        return ResidualSolveResult(
            feasible=False,
            optimizer_valid=relaxed_valid,
            target_feasible=False,
            edge_actions=edges,
            residual_node_actions=residual_nodes,
            counterfactual_node_commands=total_commands,
            counterfactual_outputs=counterfactual,
            counterfactual_soc=soc_path,
            objective_value=float(relaxed_edges @ relaxed_edges),
            solver_iterations=int(relaxed_result.nit),
            maximum_constraint_residual=relaxed_constraint_residual,
            maximum_target_shortfall=maximum_target_shortfall,
            message=f"relative feasibility relaxation: {relaxed_result.message}",
        )

    result = minimize(
        objective,
        relaxed_edges,
        jac=gradient,
        method="SLSQP",
        constraints=(
            {"type": "ineq", "fun": endpoint_constraints},
            {"type": "ineq", "fun": physical_constraints},
        ),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )
    values = np.asarray(result.x, dtype=float)
    edges, residual_nodes, total_commands, counterfactual, soc_path = decode(values)
    endpoint_slack = endpoint_constraints(values)
    physical_slack = physical_constraints(values)
    maximum_residual = float(
        max(
            0.0,
            -float(np.min(endpoint_slack)),
            -float(np.min(physical_slack)),
        )
    )
    optimizer_valid = bool(
        result.success
        and np.all(np.isfinite(values))
        and np.isfinite(result.fun)
        and maximum_residual <= tolerance
    )
    return ResidualSolveResult(
        feasible=optimizer_valid,
        optimizer_valid=optimizer_valid,
        target_feasible=True,
        edge_actions=edges,
        residual_node_actions=residual_nodes,
        counterfactual_node_commands=total_commands,
        counterfactual_outputs=counterfactual,
        counterfactual_soc=soc_path,
        objective_value=float(result.fun),
        solver_iterations=int(result.nit),
        maximum_constraint_residual=maximum_residual,
        maximum_target_shortfall=float(max(0.0, -float(np.min(endpoint_slack)))),
        message=(
            f"relative feasibility relaxation: {relaxed_result.message}; "
            f"minimum norm: {result.message}"
        ),
    )
