"""Independent relaxed feasibility seam for the frozen R356 endpoint target.

The solver keeps only the common- and differential-coordinate endpoint
requirements.  It deliberately omits every physical and information
constraint, so accepted primal infeasibility is evidence against the original
problem while an optimal solution is not evidence for physical feasibility.

Usage::

    result = solve_joint_endpoint_feasibility(
        base_outputs=outputs,
        response_map=response,
        minimum_improvement_fraction=0.02,
    )

Malformed dimensions, non-finite inputs, non-positive baseline measures, or a
non-finite required solver diagnostic raise ``ValueError``.  Unsupported or
unaccepted solver exits fail closed in the sixteen-case classifier and never
authorize training.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from cvxopt import matrix, solvers

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

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


def _validate_inputs(
    base_outputs: np.ndarray,
    response_map: np.ndarray,
    minimum_improvement_fraction: float,
) -> tuple[np.ndarray, np.ndarray, int]:
    outputs = np.asarray(base_outputs, dtype=float)
    response = np.asarray(response_map, dtype=float)
    improvement = float(minimum_improvement_fraction)
    if outputs.ndim != 2 or outputs.shape[1] != 4 or outputs.shape[0] < 1:
        raise ValueError("base_outputs must have shape (steps, 4)")
    steps = int(outputs.shape[0])
    if response.shape != (4 * steps, 3 * steps):
        raise ValueError("response_map must have shape (4 * steps, 3 * steps)")
    if not np.all(np.isfinite(outputs)) or not np.all(np.isfinite(response)):
        raise ValueError("base outputs and response map must be finite")
    if not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    common_sum = float(np.sum(np.abs(outputs[:, 0])))
    differential = outputs[:, 1:].reshape(-1)
    differential_sum = float(differential @ differential)
    if common_sum <= 0.0 or differential_sum <= 0.0:
        raise ValueError("both baseline endpoint measures must be positive")
    return outputs, response, steps


def solve_joint_endpoint_feasibility(
    *,
    base_outputs: np.ndarray,
    response_map: np.ndarray,
    minimum_improvement_fraction: float,
) -> dict[str, Any]:
    """Solve the R356 relaxed joint endpoint target for one built case."""

    outputs, response, steps = _validate_inputs(
        base_outputs,
        response_map,
        minimum_improvement_fraction,
    )
    improvement = float(minimum_improvement_fraction)
    action_scale = float(FeedbackLimits().node_ramp)
    full_edge_count = 3 * steps
    active_columns = np.any(response != 0.0, axis=0)
    active_response = response[:, active_columns]
    edge_count = int(np.count_nonzero(active_columns))
    variable_count = edge_count + steps
    common_rows = np.arange(0, 4 * steps, 4)
    differential_rows = np.setdiff1d(np.arange(4 * steps), common_rows)

    common_base = outputs[:, 0]
    differential_base = outputs[:, 1:].reshape(-1)
    common_sum = float(np.sum(np.abs(common_base)))
    differential_sum = float(differential_base @ differential_base)
    common_scale = common_sum / steps
    normalized_common_base = common_base / common_scale
    normalized_common_response = (
        action_scale * active_response[common_rows] / common_scale
    )
    differential_response = action_scale * active_response[differential_rows]

    common_budget_row = np.hstack(
        (np.zeros((1, edge_count)), np.ones((1, steps)))
    )
    common_upper = np.hstack((normalized_common_response, -np.eye(steps)))
    common_lower = np.hstack((-normalized_common_response, -np.eye(steps)))
    epigraph_nonnegative = np.hstack(
        (np.zeros((steps, edge_count)), -np.eye(steps))
    )
    linear_matrix = np.vstack(
        (common_budget_row, common_upper, common_lower, epigraph_nonnegative)
    )
    linear_bound = np.concatenate(
        (
            np.asarray([(1.0 - improvement) * steps]),
            -normalized_common_base,
            normalized_common_base,
            np.zeros(steps),
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
    previous = {key: solvers.options.get(key, missing) for key in option_keys}
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
        for key, value in previous.items():
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
        "full_edge_variable_count": full_edge_count,
        "active_edge_variable_count": edge_count,
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
    edges = values[:edge_count]
    common = normalized_common_base + normalized_common_response @ edges
    differential = differential_base + differential_response @ edges
    common_ratio = float(np.sum(np.abs(common)) / steps)
    differential_ratio = float((differential @ differential) / differential_sum)
    maximum_linear_violation = float(
        max(0.0, np.max(linear_matrix @ values - linear_bound))
    )
    diagnostics = {
        "primal_infeasibility": _finite_float(solved["primal infeasibility"]),
        "dual_infeasibility": _finite_float(solved["dual infeasibility"]),
        "relative_gap": _finite_float(solved["relative gap"]),
        "common_target_violation": max(
            0.0, common_ratio - (1.0 - improvement)
        ),
        "differential_target_violation": max(
            0.0, differential_ratio - (1.0 - improvement)
        ),
        "maximum_linear_violation": maximum_linear_violation,
    }
    payload.update(
        {
            "common_ratio": common_ratio,
            "differential_ratio": differential_ratio,
            **diagnostics,
            "accepted": all(
                value <= ACCEPTANCE_TOLERANCE for value in diagnostics.values()
            ),
        }
    )
    return payload


def classify_joint_endpoint_feasibility(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify a complete feasibility bank without authorizing training."""

    if len(rows) != EXPECTED_CASE_COUNT or any(
        not bool(row.get("accepted", False)) for row in rows
    ):
        classification = "ANALYSIS-INVALID"
    else:
        statuses = [str(row.get("status", "")) for row in rows]
        if any(status == "primal infeasible" for status in statuses):
            classification = "NO-TRAINING"
        elif all(status == "optimal" for status in statuses):
            classification = "CLASSIFIER-REPAIR-ELIGIBLE"
        else:
            classification = "ANALYSIS-INVALID"
    return {
        "classification": classification,
        "training_authorized": False,
        "accepted_primal_infeasible_count": sum(
            bool(row.get("accepted", False))
            and row.get("status") == "primal infeasible"
            for row in rows
        ),
        "accepted_optimal_count": sum(
            bool(row.get("accepted", False)) and row.get("status") == "optimal"
            for row in rows
        ),
    }
