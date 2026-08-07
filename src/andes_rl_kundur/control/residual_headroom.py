"""Reusable numerical primitives for model-first residual-headroom analysis.

The module owns artifact-independent response maps, endpoint metrics,
standardized affine fitting, paired statistics, physical projection, and the
fixed three-start convex solve.  Callers supply finite arrays and explicit
solver budgets.  Invalid shapes, non-finite values, infeasible physical paths,
or uncertified solves are returned or raised explicitly; no simulator,
training process, repository artifact, or scientific classification is owned
here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import t as student_t

from andes_rl_kundur.control.convex_residual_solver import (
    ConvexResidualSolveResult,
    solve_convex_minimum_norm_edge_residual,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import SeparateInputRealization
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence


@dataclass(frozen=True)
class StandardizedAffineModel:
    """Train-fold standardization and affine least-squares coefficients."""

    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray


@dataclass(frozen=True)
class ResidualProjectionResult:
    """Closest physically feasible edge sequence to a proposal."""

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
class NormalizedWarmStart:
    """Dimensionless warm start used by the fixed three-start solver."""

    edge_actions: np.ndarray
    optimizer_valid: bool


@dataclass(frozen=True)
class ResidualStartResult:
    """One named independently certified convex solve."""

    name: str
    result: ConvexResidualSolveResult


@dataclass(frozen=True)
class ThreeStartResidualResult:
    """Fixed starts and the deterministic certified selection."""

    starts: tuple[ResidualStartResult, ...]
    selected: ConvexResidualSolveResult | None
    selected_start: str | None
    certified_start_count: int
    normalized_warm_start_valid: bool


def finite_matrix(values: object, *, name: str, columns: int) -> np.ndarray:
    """Return a finite non-empty matrix with the required column count."""

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
    """Compute common-coordinate IAE and differential-coordinate energy."""

    outputs = finite_matrix(coordinate_outputs, name="coordinate_outputs", columns=4)
    sample_period = float(sample_period_seconds)
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")
    return {
        "common_coordinate_iae": float(sample_period * np.sum(np.abs(outputs[:, 0]))),
        "differential_coordinate_energy": float(sample_period * np.sum(np.square(outputs[:, 1:]))),
    }


def fit_standardized_affine(features: object, targets: object) -> StandardizedAffineModel:
    """Fit one deterministic affine least-squares map without tuning."""

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
    return StandardizedAffineModel(
        mean=mean,
        scale=scale,
        coefficients=np.asarray(coefficients, dtype=float),
    )


def apply_standardized_affine(
    model: StandardizedAffineModel,
    features: object,
) -> np.ndarray:
    """Apply a train-fold standardized affine least-squares map."""

    inputs = np.asarray(features, dtype=float)
    if (
        inputs.ndim != 2
        or inputs.shape[1] != model.mean.shape[0]
        or not np.all(np.isfinite(inputs))
    ):
        raise ValueError("features are incompatible with the affine model")
    standardized = (inputs - model.mean) / model.scale
    prediction = np.column_stack((np.ones(inputs.shape[0]), standardized)) @ model.coefficients
    if not np.all(np.isfinite(prediction)):
        raise ValueError("affine prediction is non-finite")
    return np.asarray(prediction, dtype=float)


def paired_endpoint_gate(
    signed_relative_changes: object,
    *,
    groups: Mapping[str, Sequence[str]],
    minimum_improvement_fraction: float,
    confidence_level: float,
) -> dict[str, object]:
    """Apply mean, one-sided paired-bound, and subgroup-direction gates."""

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
    upper = float(mean + student_t.ppf(confidence, df=changes.size - 1) * standard_error)
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
    return {
        "pass": bool(mean_improvement >= minimum and upper < 0.0 and subgroup_directional),
        "count": int(changes.size),
        "mean_signed_relative_change": mean,
        "mean_improvement_fraction": float(mean_improvement),
        "one_sided_upper_bound": upper,
        "confidence_level": confidence,
        "minimum_improvement_fraction": minimum,
        "subgroup_directional": bool(subgroup_directional),
        "subgroups": subgroup_results,
    }


def _advance_soc(
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


def solve_normalized_warm_start(
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
) -> NormalizedWarmStart:
    """Solve the residual problem in dimensionless coordinates for a warm start."""

    outputs = finite_matrix(base_outputs, name="base_outputs", columns=4)
    commands = finite_matrix(base_node_commands, name="base_node_commands", columns=4)
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
    iterations = int(maximum_iterations)
    ftol = float(function_tolerance)
    tolerance = float(feasibility_tolerance)
    if not np.isfinite(improvement) or not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    if iterations < 1 or not np.isfinite(ftol) or ftol <= 0.0:
        raise ValueError("solver budget must be positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")

    action_scale = float(limits.node_ramp)
    soc_scale = float(limits.maximum_soc - limits.minimum_soc)
    if action_scale <= 0.0 or soc_scale <= 0.0:
        raise ValueError("frozen physical normalization scales must be positive")
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

    def decode_scaled(
        scaled_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        edges = (action_scale * scaled_values).reshape(steps, 3)
        residual_nodes = edges @ incidence.T
        total_commands = commands + residual_nodes
        counterfactual = outputs + (response @ edges.reshape(-1)).reshape(steps, 4)
        soc_path = _advance_soc(soc0, total_commands, limits)
        return edges, residual_nodes, total_commands, counterfactual, soc_path

    def endpoint_constraints_original(scaled_values: np.ndarray) -> np.ndarray:
        *_unused, counterfactual, _soc = decode_scaled(scaled_values)
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

    def endpoint_constraints_scaled(scaled_values: np.ndarray) -> np.ndarray:
        return endpoint_constraints_original(scaled_values) / baseline

    def physical_constraint_blocks(
        scaled_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        _edges, _residual, total, _counterfactual, soc_path = decode_scaled(scaled_values)
        ramps = np.vstack((total[:1] - previous.reshape(1, 4), np.diff(total, axis=0)))
        return (
            (limits.node_power - np.abs(total)).reshape(-1),
            (limits.node_ramp - np.abs(ramps)).reshape(-1),
            (soc_path[1:] - limits.minimum_soc).reshape(-1),
            (limits.maximum_soc - soc_path[1:]).reshape(-1),
        )

    def physical_constraints_original(scaled_values: np.ndarray) -> np.ndarray:
        return np.concatenate(physical_constraint_blocks(scaled_values))

    def physical_constraints_scaled(scaled_values: np.ndarray) -> np.ndarray:
        power, ramp, soc_lower, soc_upper = physical_constraint_blocks(scaled_values)
        return np.concatenate(
            (
                power / limits.node_power,
                ramp / limits.node_ramp,
                soc_lower / soc_scale,
                soc_upper / soc_scale,
            )
        )

    edge_count = 3 * steps
    relaxed_initial = np.zeros(edge_count + 2)
    relaxed_initial[-2:] = improvement

    def relaxed_objective(values: np.ndarray) -> float:
        slacks = values[edge_count:]
        return float(slacks @ slacks)

    def relaxed_gradient(values: np.ndarray) -> np.ndarray:
        gradient_values = np.zeros_like(values)
        gradient_values[edge_count:] = 2.0 * values[edge_count:]
        return gradient_values

    def relaxed_endpoint_constraints_scaled(values: np.ndarray) -> np.ndarray:
        return endpoint_constraints_scaled(values[:edge_count]) + values[edge_count:]

    def relaxed_physical_constraints_scaled(values: np.ndarray) -> np.ndarray:
        return physical_constraints_scaled(values[:edge_count])

    relaxed_result = minimize(
        relaxed_objective,
        relaxed_initial,
        jac=relaxed_gradient,
        method="SLSQP",
        constraints=(
            {"type": "ineq", "fun": lambda values: values[edge_count:]},
            {"type": "ineq", "fun": relaxed_endpoint_constraints_scaled},
            {"type": "ineq", "fun": relaxed_physical_constraints_scaled},
        ),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )
    relaxed_values = np.asarray(relaxed_result.x, dtype=float)
    relaxed_scaled_edges = relaxed_values[:edge_count]
    relaxed_relative_slacks = relaxed_values[edge_count:]
    relaxed_endpoint_original = (
        endpoint_constraints_original(relaxed_scaled_edges) + baseline * relaxed_relative_slacks
    )
    relaxed_physical_original = physical_constraints_original(relaxed_scaled_edges)
    relaxed_constraint_residual = float(
        max(
            0.0,
            -float(np.min(relaxed_endpoint_original)),
            -float(np.min(relaxed_physical_original)),
            -float(np.min(relaxed_relative_slacks)),
        )
    )
    relaxed_valid = bool(
        relaxed_result.success
        and np.all(np.isfinite(relaxed_values))
        and np.isfinite(relaxed_result.fun)
        and relaxed_constraint_residual <= tolerance
    )
    target_shortfall = float(
        max(0.0, -float(np.min(endpoint_constraints_original(relaxed_scaled_edges))))
    )
    if not (relaxed_valid and target_shortfall <= tolerance):
        edges, *_unused = decode_scaled(relaxed_scaled_edges)
        return NormalizedWarmStart(edge_actions=edges, optimizer_valid=relaxed_valid)

    result = minimize(
        lambda values: float(values @ values),
        relaxed_scaled_edges,
        jac=lambda values: 2.0 * values,
        method="SLSQP",
        constraints=(
            {"type": "ineq", "fun": endpoint_constraints_scaled},
            {"type": "ineq", "fun": physical_constraints_scaled},
        ),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )
    scaled_values = np.asarray(result.x, dtype=float)
    edges, *_unused = decode_scaled(scaled_values)
    maximum_residual = float(
        max(
            0.0,
            -float(np.min(endpoint_constraints_original(scaled_values))),
            -float(np.min(physical_constraints_original(scaled_values))),
        )
    )
    valid = bool(
        result.success
        and np.all(np.isfinite(scaled_values))
        and np.isfinite(result.fun)
        and maximum_residual <= tolerance
    )
    return NormalizedWarmStart(edge_actions=edges, optimizer_valid=valid)


def solve_three_start_edge_residual(
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
) -> ThreeStartResidualResult:
    """Run fixed feasibility, zero, and normalized-warm starts once."""

    inputs = {
        "base_outputs": base_outputs,
        "base_node_commands": base_node_commands,
        "previous_node_command": previous_node_command,
        "initial_soc": initial_soc,
        "response_map": response_map,
        "limits": limits,
        "minimum_improvement_fraction": minimum_improvement_fraction,
        "maximum_iterations": maximum_iterations,
        "function_tolerance": function_tolerance,
        "feasibility_tolerance": feasibility_tolerance,
    }
    warm = solve_normalized_warm_start(**inputs)
    starts = (
        ResidualStartResult(
            name="feasibility",
            result=solve_convex_minimum_norm_edge_residual(**inputs),
        ),
        ResidualStartResult(
            name="zero",
            result=solve_convex_minimum_norm_edge_residual(
                **inputs,
                use_feasibility_start=False,
            ),
        ),
        ResidualStartResult(
            name="r348",
            result=solve_convex_minimum_norm_edge_residual(
                **inputs,
                initial_edge_actions=warm.edge_actions,
                use_feasibility_start=False,
            ),
        ),
    )
    certified = [(index, start) for index, start in enumerate(starts) if start.result.feasible]
    if certified:
        _index, chosen = min(
            certified,
            key=lambda item: (item[1].result.objective_value, item[0]),
        )
        selected = chosen.result
        selected_start = chosen.name
    else:
        selected = None
        selected_start = None
    return ThreeStartResidualResult(
        starts=starts,
        selected=selected,
        selected_start=selected_start,
        certified_start_count=len(certified),
        normalized_warm_start_valid=bool(warm.optimizer_valid),
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

    proposed = finite_matrix(
        proposed_edge_actions,
        name="proposed_edge_actions",
        columns=3,
    )
    commands = finite_matrix(
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
        soc_path = _advance_soc(soc0, total, limits)
        return edges, residual_nodes, total, soc_path

    target = proposed.reshape(-1)

    def objective(values: np.ndarray) -> float:
        delta = values - target
        return float(delta @ delta)

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

    result = minimize(
        objective,
        np.zeros(3 * steps),
        jac=lambda values: 2.0 * (values - target),
        method="SLSQP",
        constraints=({"type": "ineq", "fun": physical_constraints},),
        options={"maxiter": iterations, "ftol": ftol, "disp": False},
    )
    values = np.asarray(result.x, dtype=float)
    edges, residual_nodes, total, soc_path = decode(values)
    maximum_residual = float(max(0.0, -float(np.min(physical_constraints(values)))))
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
