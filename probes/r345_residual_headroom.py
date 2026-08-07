"""Create-only residual-headroom primitives for R345.

The module operates on already recorded coordinate traces and the frozen R341
separate-input realization.  It reads no repository artifact, runs no physical
simulator, and exposes no training or evaluation entry point.  Scientific
classification remains in the R345 execution adapter.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.stats import t as student_t

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputRealization,
)
from andes_rl_kundur.env.andes.model_first_contract import (
    active_power_incidence,
    weighted_common_differential_transform,
)


@dataclass(frozen=True)
class ResidualSolveResult:
    """One minimum-norm outcome-seeing edge-residual feasibility result."""

    feasible: bool
    optimizer_valid: bool
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
    message: str


@dataclass(frozen=True)
class ResidualProjectionResult:
    """One neighbour-local edge sequence projected to physical headroom."""

    feasible: bool
    edge_actions: np.ndarray
    residual_node_actions: np.ndarray
    counterfactual_node_commands: np.ndarray
    counterfactual_soc: np.ndarray
    objective_value: float
    solver_iterations: int
    maximum_constraint_residual: float
    message: str


@dataclass(frozen=True)
class StandardizedOlsModel:
    """Deterministic affine least-squares map with train-fold scaling only."""

    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray


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


def build_control_response_map(
    model: SeparateInputRealization,
    *,
    horizon: int,
) -> np.ndarray:
    """Return the causal output map for three zero-common edge inputs."""

    steps = int(horizon)
    if steps < 1:
        raise ValueError("horizon must be positive")
    state = np.asarray(model.state_matrix, dtype=float)
    control = np.asarray(model.control_input_matrix, dtype=float)
    output = np.asarray(model.output_matrix, dtype=float)
    direct = np.asarray(model.control_feedthrough_matrix, dtype=float)
    order = state.shape[0]
    if (
        state.shape != (order, order)
        or control.shape != (order, 4)
        or output.shape != (4, order)
        or direct.shape != (4, 4)
        or not all(np.all(np.isfinite(item)) for item in (state, control, output, direct))
    ):
        raise ValueError("model must be a finite four-coordinate realization")

    edge_control = control[:, 1:]
    edge_direct = direct[:, 1:]
    response = np.zeros((4 * steps, 3 * steps))
    powers = [np.eye(order)]
    for _ in range(max(0, steps - 1)):
        powers.append(powers[-1] @ state)
    for output_step in range(steps):
        row = slice(4 * output_step, 4 * (output_step + 1))
        for action_step in range(output_step + 1):
            column = slice(3 * action_step, 3 * (action_step + 1))
            lag = output_step - action_step
            response[row, column] = (
                edge_direct if lag == 0 else output @ powers[lag - 1] @ edge_control
            )
    return response


def endpoint_values(
    coordinate_outputs: object,
    *,
    sample_period_seconds: float,
) -> dict[str, float]:
    """Compute the two frozen R344 primary coordinate endpoints."""

    outputs = _finite_matrix(coordinate_outputs, name="coordinate_outputs", columns=4)
    sample_period = float(sample_period_seconds)
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")
    return {
        "common_coordinate_iae": float(sample_period * np.sum(np.abs(outputs[:, 0]))),
        "differential_coordinate_energy": float(sample_period * np.sum(np.square(outputs[:, 1:]))),
    }


def physical_frequency_from_coordinates(
    coordinate_outputs: object,
    *,
    reference_frequency_hz: object,
    inertia_system: object,
    physical_nominal_frequency_hz: float = 60.0,
) -> np.ndarray:
    """Recover the four causal device-frequency values from logged coordinates."""

    coordinates = _finite_matrix(
        coordinate_outputs,
        name="coordinate_outputs",
        columns=4,
    )
    reference = np.asarray(reference_frequency_hz, dtype=float)
    nominal = float(physical_nominal_frequency_hz)
    if reference.shape != (4,) or not np.all(np.isfinite(reference)):
        raise ValueError("reference_frequency_hz must contain four finite values")
    if not np.isfinite(nominal) or nominal <= 0.0:
        raise ValueError("physical_nominal_frequency_hz must be positive and finite")
    transform = weighted_common_differential_transform(inertia_system)
    if transform.inverse.shape != (4, 4):
        raise ValueError("inertia_system must define exactly four coordinates")
    deviations = (transform.inverse @ coordinates.T).T
    return reference.reshape(1, 4) + nominal * deviations


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


def solve_minimum_norm_edge_residual(
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
    """Find the minimum-L2 edge residual meeting both endpoint targets."""

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
    target_common = (1.0 - improvement) * base_endpoints["common_coordinate_iae"]
    target_differential = (1.0 - improvement) * base_endpoints["differential_coordinate_energy"]
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
        return np.asarray(
            [
                target_common - endpoints["common_coordinate_iae"],
                target_differential - endpoints["differential_coordinate_energy"],
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
    relaxed_initial[-2:] = np.asarray(
        [
            base_endpoints["common_coordinate_iae"] - target_common,
            base_endpoints["differential_coordinate_energy"] - target_differential,
        ]
    )
    relaxed_scales = np.asarray(
        [
            base_endpoints["common_coordinate_iae"],
            base_endpoints["differential_coordinate_energy"],
        ]
    )

    def relaxed_objective(values: np.ndarray) -> float:
        slacks = values[edge_count:]
        normalized = slacks / relaxed_scales
        return float(normalized @ normalized)

    def relaxed_gradient(values: np.ndarray) -> np.ndarray:
        gradient_values = np.empty_like(values)
        gradient_values[:edge_count] = 0.0
        gradient_values[edge_count:] = (
            2.0 * values[edge_count:] / np.square(relaxed_scales)
        )
        return gradient_values

    def relaxed_endpoint_constraints(values: np.ndarray) -> np.ndarray:
        return endpoint_constraints(values[:edge_count]) + values[edge_count:]

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
            message=f"feasibility relaxation: {relaxed_result.message}",
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
            f"feasibility relaxation: {relaxed_result.message}; minimum norm: {result.message}"
        ),
    )


def project_edge_sequence_to_headroom(
    *,
    proposed_edge_actions: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    limits: FeedbackLimits = FeedbackLimits(),
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> ResidualProjectionResult:
    """Return the closest fleet-neutral edge sequence satisfying headroom."""

    proposed = _finite_matrix(
        proposed_edge_actions,
        name="proposed_edge_actions",
        columns=3,
    )
    commands = _finite_matrix(
        base_node_commands,
        name="base_node_commands",
        columns=4,
    )
    if proposed.shape[0] != commands.shape[0]:
        raise ValueError("proposed actions and base commands must share one horizon")
    previous = np.asarray(previous_node_command, dtype=float)
    soc0 = np.asarray(initial_soc, dtype=float)
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_node_command must contain four finite values")
    if soc0.shape != (4,) or not np.all(np.isfinite(soc0)):
        raise ValueError("initial_soc must contain four finite values")
    iterations = int(maximum_iterations)
    ftol = float(function_tolerance)
    tolerance = float(feasibility_tolerance)
    if iterations < 1 or not np.isfinite(ftol) or ftol <= 0.0:
        raise ValueError("solver budget must be positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")

    steps = proposed.shape[0]
    incidence = np.asarray(active_power_incidence(), dtype=float)

    def decode(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        edges = values.reshape(steps, 3)
        residual_nodes = edges @ incidence.T
        total = commands + residual_nodes
        soc_path = _advance_soc_path(soc0, total, limits)
        return edges, residual_nodes, total, soc_path

    target = proposed.reshape(-1)

    def objective(values: np.ndarray) -> float:
        delta = values - target
        return float(delta @ delta)

    def gradient(values: np.ndarray) -> np.ndarray:
        return 2.0 * (values - target)

    def physical_constraints(values: np.ndarray) -> np.ndarray:
        _edges, _residual, total, soc_path = decode(values)
        ramps = np.vstack((total[:1] - previous.reshape(1, 4), np.diff(total, axis=0)))
        return np.concatenate(
            (
                (limits.node_power - np.abs(total)).reshape(-1),
                (limits.node_ramp - np.abs(ramps)).reshape(-1),
                (soc_path[1:] - limits.minimum_soc).reshape(-1),
                (limits.maximum_soc - soc_path[1:]).reshape(-1),
            )
        )

    initial = np.zeros(3 * steps)
    result = minimize(
        objective,
        initial,
        jac=gradient,
        method="SLSQP",
        constraints=({"type": "ineq", "fun": physical_constraints},),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )
    values = np.asarray(result.x, dtype=float)
    edges, residual_nodes, total, soc_path = decode(values)
    physical_slack = physical_constraints(values)
    maximum_residual = float(max(0.0, -float(np.min(physical_slack))))
    feasible = bool(
        result.success
        and np.all(np.isfinite(values))
        and np.isfinite(result.fun)
        and maximum_residual <= tolerance
    )
    return ResidualProjectionResult(
        feasible=feasible,
        edge_actions=edges,
        residual_node_actions=residual_nodes,
        counterfactual_node_commands=total,
        counterfactual_soc=soc_path,
        objective_value=float(result.fun),
        solver_iterations=int(result.nit),
        maximum_constraint_residual=maximum_residual,
        message=str(result.message),
    )


def causal_edge_features(
    *,
    frequency_hz_before_action: object,
    achieved_node_power_before_action: object,
    commanded_node_power_before_action: object,
    edge: tuple[int, int],
    nominal_frequency_hz: float,
) -> np.ndarray:
    """Return only the two action-edge endpoints' causal physical values."""

    frequency = _finite_matrix(
        frequency_hz_before_action,
        name="frequency_hz_before_action",
        columns=4,
    )
    achieved = _finite_matrix(
        achieved_node_power_before_action,
        name="achieved_node_power_before_action",
        columns=4,
    )
    commanded = _finite_matrix(
        commanded_node_power_before_action,
        name="commanded_node_power_before_action",
        columns=4,
    )
    if not (frequency.shape == achieved.shape == commanded.shape):
        raise ValueError("causal feature arrays must share one shape")
    source, target = (int(edge[0]), int(edge[1]))
    if source == target or min(source, target) < 0 or max(source, target) >= 4:
        raise ValueError("edge endpoints must be two distinct device indices")
    nominal = float(nominal_frequency_hz)
    if not np.isfinite(nominal) or nominal <= 0.0:
        raise ValueError("nominal_frequency_hz must be positive and finite")
    return np.column_stack(
        (
            frequency[:, source] - nominal,
            frequency[:, target] - nominal,
            achieved[:, source],
            achieved[:, target],
            commanded[:, source],
            commanded[:, target],
        )
    )


def fit_standardized_ols(features: object, targets: object) -> StandardizedOlsModel:
    """Fit one deterministic affine OLS map without a tuning parameter."""

    inputs = np.asarray(features, dtype=float)
    outputs = np.asarray(targets, dtype=float)
    if inputs.ndim != 2 or inputs.shape[0] < 2 or not np.all(np.isfinite(inputs)):
        raise ValueError("features must be a finite matrix with at least two rows")
    if outputs.ndim not in (1, 2) or outputs.shape[0] != inputs.shape[0]:
        raise ValueError("targets must align with feature rows")
    if not np.all(np.isfinite(outputs)):
        raise ValueError("targets must be finite")
    mean = np.mean(inputs, axis=0)
    raw_scale = np.std(inputs, axis=0, ddof=0)
    scale = np.where(raw_scale > 0.0, raw_scale, 1.0)
    standardized = (inputs - mean) / scale
    design = np.column_stack((np.ones(inputs.shape[0]), standardized))
    coefficients, *_ = np.linalg.lstsq(design, outputs, rcond=None)
    return StandardizedOlsModel(
        mean=mean,
        scale=scale,
        coefficients=np.asarray(coefficients, dtype=float),
    )


def apply_standardized_ols(model: StandardizedOlsModel, features: object) -> np.ndarray:
    """Apply a train-fold standardized affine OLS map."""

    inputs = np.asarray(features, dtype=float)
    if (
        inputs.ndim != 2
        or inputs.shape[1] != model.mean.shape[0]
        or not np.all(np.isfinite(inputs))
    ):
        raise ValueError("features are incompatible with the OLS model")
    standardized = (inputs - model.mean) / model.scale
    design = np.column_stack((np.ones(inputs.shape[0]), standardized))
    prediction = design @ model.coefficients
    if not np.all(np.isfinite(prediction)):
        raise ValueError("OLS prediction is non-finite")
    return np.asarray(prediction, dtype=float)


def paired_endpoint_gate(
    signed_relative_changes: object,
    *,
    groups: Mapping[str, Sequence[str]],
    minimum_improvement_fraction: float,
    confidence_level: float,
) -> dict[str, Any]:
    """Apply the frozen mean, one-sided paired bound, and subgroup gates."""

    changes = np.asarray(signed_relative_changes, dtype=float)
    if changes.ndim != 1 or changes.size < 2 or not np.all(np.isfinite(changes)):
        raise ValueError("signed_relative_changes must contain at least two finite values")
    minimum = float(minimum_improvement_fraction)
    confidence = float(confidence_level)
    if not np.isfinite(minimum) or not 0.0 < minimum < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    if not np.isfinite(confidence) or not 0.5 < confidence < 1.0:
        raise ValueError("confidence_level must lie in (0.5, 1)")
    mean = float(np.mean(changes))
    standard_error = float(np.std(changes, ddof=1) / np.sqrt(changes.size))
    critical = float(student_t.ppf(confidence, df=changes.size - 1))
    upper = float(mean + critical * standard_error)
    subgroup_results: dict[str, dict[str, float]] = {}
    subgroup_directional = True
    for family, labels in groups.items():
        if len(labels) != changes.size:
            raise ValueError(f"group family {family} does not align with changes")
        family_results: dict[str, float] = {}
        for label in sorted(set(labels)):
            mask = np.asarray([item == label for item in labels], dtype=bool)
            value = float(np.mean(changes[mask]))
            family_results[str(label)] = value
            subgroup_directional &= value < 0.0
        subgroup_results[str(family)] = family_results
    mean_improvement = -mean
    passed = bool(mean_improvement >= minimum and upper < 0.0 and subgroup_directional)
    return {
        "pass": passed,
        "count": int(changes.size),
        "mean_signed_relative_change": mean,
        "mean_improvement_fraction": float(mean_improvement),
        "one_sided_upper_bound": upper,
        "confidence_level": confidence,
        "minimum_improvement_fraction": minimum,
        "subgroup_directional": bool(subgroup_directional),
        "subgroups": subgroup_results,
    }
