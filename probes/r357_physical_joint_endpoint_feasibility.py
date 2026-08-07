"""Certified physical feasibility for the frozen R357 joint endpoint target.

The public seam solves one linear-response case with the registered three edge
actions, common and differential endpoint targets, node-power limits, and
node-ramp limits.  State of charge is omitted from the cone only after a
worst-path analytic bound proves it redundant, then reconstructed exactly for
every accepted witness.  Solver status alone never implies acceptance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from cvxopt import matrix, solvers

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence


SOLVER_NAME = "cvxopt-socp"
SOLVER_ABSOLUTE_TOLERANCE = 1.0e-10
SOLVER_RELATIVE_TOLERANCE = 1.0e-10
SOLVER_FEASIBILITY_TOLERANCE = 1.0e-10
SOLVER_MAXIMUM_ITERATIONS = 100
ACCEPTANCE_TOLERANCE = 1.0e-8
EXPECTED_CASE_COUNT = 16


def _finite_float(value: Any) -> float:
    converted = float(value)
    if not np.isfinite(converted):
        raise ValueError("solver returned a non-finite diagnostic")
    return converted


def _finite_matrix(values: object, *, name: str, columns: int) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if (
        result.ndim != 2
        or result.shape[0] < 1
        or result.shape[1] != columns
        or not np.all(np.isfinite(result))
    ):
        raise ValueError(f"{name} must be a non-empty finite matrix with {columns} columns")
    return result


def _soc_redundancy_bound(
    initial_soc: np.ndarray,
    *,
    steps: int,
    limits: FeedbackLimits,
) -> tuple[float, float]:
    if initial_soc.shape != (4,) or not np.all(np.isfinite(initial_soc)):
        raise ValueError("initial_soc must contain four finite values")
    minimum_margin = float(
        min(
            np.min(initial_soc - limits.minimum_soc),
            np.min(limits.maximum_soc - initial_soc),
        )
    )
    efficiency_factor = max(
        float(limits.charge_efficiency),
        1.0 / float(limits.discharge_efficiency),
    )
    maximum_change = float(
        steps
        * limits.sample_period_seconds
        * limits.system_mva
        * limits.node_power
        * efficiency_factor
        / (3600.0 * limits.energy_mwh)
    )
    if minimum_margin + ACCEPTANCE_TOLERANCE < maximum_change:
        raise ValueError("state-of-charge redundancy is not established")
    return maximum_change, minimum_margin


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


def solve_physical_joint_endpoint_feasibility(
    *,
    base_outputs: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    response_map: object,
    minimum_improvement_fraction: float,
    limits: FeedbackLimits = FeedbackLimits(),
) -> dict[str, Any]:
    """Solve and independently reconstruct one exact R357 physical case."""

    outputs = _finite_matrix(base_outputs, name="base_outputs", columns=4)
    commands = _finite_matrix(
        base_node_commands,
        name="base_node_commands",
        columns=4,
    )
    if commands.shape[0] != outputs.shape[0]:
        raise ValueError("base outputs and node commands must share one horizon")
    steps = int(outputs.shape[0])
    previous = np.asarray(previous_node_command, dtype=float)
    soc0 = np.asarray(initial_soc, dtype=float)
    response = np.asarray(response_map, dtype=float)
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_node_command must contain four finite values")
    if response.shape != (4 * steps, 3 * steps) or not np.all(np.isfinite(response)):
        raise ValueError("response_map has incompatible shape or values")
    improvement = float(minimum_improvement_fraction)
    if not np.isfinite(improvement) or not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    maximum_soc_change, minimum_soc_margin = _soc_redundancy_bound(
        soc0,
        steps=steps,
        limits=limits,
    )

    common_base = outputs[:, 0]
    differential_base = outputs[:, 1:].reshape(-1)
    common_sum = float(np.sum(np.abs(common_base)))
    differential_sum = float(differential_base @ differential_base)
    if common_sum <= 0.0 or differential_sum <= 0.0:
        raise ValueError("both baseline endpoint measures must be positive")

    action_scale = float(limits.node_ramp)
    edge_count = 3 * steps
    variable_count = edge_count + steps
    common_rows = np.arange(0, 4 * steps, 4)
    differential_rows = np.setdiff1d(np.arange(4 * steps), common_rows)
    common_scale = common_sum / steps
    normalized_common_base = common_base / common_scale
    normalized_common_response = action_scale * response[common_rows] / common_scale
    differential_response = action_scale * response[differential_rows]

    incidence = np.asarray(active_power_incidence(), dtype=float)
    node_action_map = action_scale * np.kron(np.eye(steps), incidence)
    zero_epigraph = np.zeros((4 * steps, steps))
    command_vector = commands.reshape(-1)

    difference = np.zeros((4 * steps, 4 * steps))
    for step in range(steps):
        row = slice(4 * step, 4 * (step + 1))
        difference[row, row] = np.eye(4)
        if step > 0:
            previous_column = slice(4 * (step - 1), 4 * step)
            difference[row, previous_column] = -np.eye(4)
    base_ramps = difference @ command_vector
    base_ramps[:4] -= previous
    ramp_action_map = difference @ node_action_map

    linear_matrix = np.vstack(
        (
            np.hstack((np.zeros((1, edge_count)), np.ones((1, steps)))),
            np.hstack((normalized_common_response, -np.eye(steps))),
            np.hstack((-normalized_common_response, -np.eye(steps))),
            np.hstack((np.zeros((steps, edge_count)), -np.eye(steps))),
            np.hstack((node_action_map, zero_epigraph)),
            np.hstack((-node_action_map, zero_epigraph)),
            np.hstack((ramp_action_map, zero_epigraph)),
            np.hstack((-ramp_action_map, zero_epigraph)),
        )
    )
    linear_bound = np.concatenate(
        (
            np.asarray([(1.0 - improvement) * steps]),
            -normalized_common_base,
            normalized_common_base,
            np.zeros(steps),
            np.full(4 * steps, limits.node_power) - command_vector,
            np.full(4 * steps, limits.node_power) + command_vector,
            np.full(4 * steps, limits.node_ramp) - base_ramps,
            np.full(4 * steps, limits.node_ramp) + base_ramps,
        )
    )

    cone_matrix = np.zeros((1 + differential_base.size, variable_count))
    cone_matrix[1:, :edge_count] = -differential_response
    cone_bound = np.concatenate(
        (
            np.asarray([np.sqrt((1.0 - improvement) * differential_sum)]),
            differential_base,
        )
    )
    objective = np.concatenate((np.zeros(edge_count), np.ones(steps)))

    option_keys = ("show_progress", "abstol", "reltol", "feastol", "maxiters")
    missing = object()
    previous_options = {key: solvers.options.get(key, missing) for key in option_keys}
    try:
        solvers.options["show_progress"] = False
        solvers.options["abstol"] = SOLVER_ABSOLUTE_TOLERANCE
        solvers.options["reltol"] = SOLVER_RELATIVE_TOLERANCE
        solvers.options["feastol"] = SOLVER_FEASIBILITY_TOLERANCE
        solvers.options["maxiters"] = SOLVER_MAXIMUM_ITERATIONS
        solved = solvers.socp(
            matrix(objective),
            Gl=matrix(linear_matrix),
            hl=matrix(linear_bound),
            Gq=[matrix(cone_matrix)],
            hq=[matrix(cone_bound)],
        )
    finally:
        for key, value in previous_options.items():
            if value is missing:
                solvers.options.pop(key, None)
            else:
                solvers.options[key] = value

    status = str(solved["status"])
    payload: dict[str, Any] = {
        "solver": SOLVER_NAME,
        "status": status,
        "accepted": False,
        "minimum_improvement_fraction": improvement,
        "acceptance_tolerance": ACCEPTANCE_TOLERANCE,
        "physical_constraints_included": True,
        "soc_redundancy_proved": True,
        "maximum_soc_change_bound": maximum_soc_change,
        "minimum_soc_margin": minimum_soc_margin,
    }
    if status == "primal infeasible":
        residual = _finite_float(
            solved["residual as primal infeasibility certificate"]
        )
        payload["residual_as_primal_infeasibility_certificate"] = residual
        payload["accepted"] = residual <= ACCEPTANCE_TOLERANCE
        return payload
    if status != "optimal":
        return payload

    values = np.asarray(solved["x"], dtype=float).reshape(-1)
    if values.shape != (variable_count,) or not np.all(np.isfinite(values)):
        raise ValueError("solver returned an invalid optimal vector")
    scaled_edges = values[:edge_count]
    edge_actions = (action_scale * scaled_edges).reshape(steps, 3)
    residual_nodes = edge_actions @ incidence.T
    total_commands = commands + residual_nodes
    counterfactual = outputs + (response @ edge_actions.reshape(-1)).reshape(steps, 4)
    soc_path = _advance_soc(soc0, total_commands, limits)
    ramps = np.vstack(
        (total_commands[:1] - previous.reshape(1, 4), np.diff(total_commands, axis=0))
    )
    common_ratio = float(np.sum(np.abs(counterfactual[:, 0])) / common_sum)
    differential = counterfactual[:, 1:].reshape(-1)
    differential_ratio = float((differential @ differential) / differential_sum)
    maximum_linear_violation = float(
        max(0.0, np.max(linear_matrix @ values - linear_bound))
    )
    maximum_cone_violation = float(
        max(0.0, np.linalg.norm(differential) - cone_bound[0])
    )
    maximum_power_violation = float(
        max(0.0, np.max(np.abs(total_commands) - limits.node_power))
    )
    maximum_ramp_violation = float(
        max(0.0, np.max(np.abs(ramps) - limits.node_ramp))
    )
    maximum_soc_violation = float(
        max(
            0.0,
            np.max(limits.minimum_soc - soc_path),
            np.max(soc_path - limits.maximum_soc),
        )
    )
    diagnostics = {
        "primal_infeasibility": abs(_finite_float(solved["primal infeasibility"])),
        "dual_infeasibility": abs(_finite_float(solved["dual infeasibility"])),
        "relative_gap": abs(_finite_float(solved["relative gap"])),
        "common_target_violation": max(0.0, common_ratio - (1.0 - improvement)),
        "differential_target_violation": max(
            0.0, differential_ratio - (1.0 - improvement)
        ),
        "maximum_linear_violation": maximum_linear_violation,
        "maximum_cone_violation": maximum_cone_violation,
        "maximum_power_violation": maximum_power_violation,
        "maximum_ramp_violation": maximum_ramp_violation,
        "maximum_soc_violation": maximum_soc_violation,
    }
    payload.update(
        {
            "common_ratio": common_ratio,
            "differential_ratio": differential_ratio,
            "edge_actions": edge_actions.tolist(),
            "residual_node_actions": residual_nodes.tolist(),
            "counterfactual_node_commands": total_commands.tolist(),
            "counterfactual_soc": soc_path.tolist(),
            **diagnostics,
            "accepted": all(
                value <= ACCEPTANCE_TOLERANCE for value in diagnostics.values()
            ),
        }
    )
    return payload


def classify_physical_joint_endpoint_feasibility(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify a complete accepted bank without authorizing later gates."""

    accepted = len(rows) == EXPECTED_CASE_COUNT and all(
        bool(row.get("accepted", False)) for row in rows
    )
    statuses = [str(row.get("status", "")) for row in rows]
    if not accepted or any(
        status not in {"optimal", "primal infeasible"} for status in statuses
    ):
        classification = "ANALYSIS-INVALID"
    elif any(status == "optimal" for status in statuses):
        classification = "PHYSICAL-HEADROOM-FOUND"
    else:
        classification = "NO-PHYSICAL-HEADROOM"
    return {
        "classification": classification,
        "accepted_optimal_count": sum(status == "optimal" for status in statuses),
        "accepted_primal_infeasible_count": sum(
            status == "primal infeasible" for status in statuses
        ),
        "training_authorized": False,
        "simulation_authorized": False,
        "holdout_authorized": False,
    }

