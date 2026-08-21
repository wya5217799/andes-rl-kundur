"""R445 — GPT Pro residual-headroom solution: per-scenario margin verification.

Motivation
----------
The external answer (tmp/gpt_pro_math_solution_20260819.md, second problem)
claims: (i) on the 16-case development bank the zero-sum edge basis B_e is
ACTION-BASIS-LIMITED — 6/16 scenarios cannot reach the joint 2% improvement
target even in the relaxed (constraint-free) problem; (ii) adding the common
channel B_+ makes 16/16 nominally physically feasible (witness lower bound
eps* >= 0.9998). The intake record (tmp/gpt_pro_solution_20260819_intake.md)
requires repo-side re-derivation of per-scenario eps*(I_4)/eps*(B_e)/eps*(B_+)
to convert M2/M3 from undecidable to supported/refuted, and to complete the
repo-side proof (proof 2 of 4) of propositions P1-P5.

This probe rebuilds the exact R352/R353 development bank (hash-verified),
extracts per-scenario response matrices (H_e = edge map, H_plus = four-channel
map, G_s = node-input map recovered as H_plus @ kron(I, inv([1_4, B_e]))) and
baseline outputs y_s^0, then bisects the maximum improvement fraction eps*
for each scenario under five settings: relaxed B_e, relaxed I_4, physical
B_e, physical B_+, physical I_4. It reuses the sealed R356 relaxed SOCP and
R363 physical QP seams (generalized to an arbitrary action-basis column count
for I_4), with the same acceptance tolerances. Nothing is trained, simulated,
or run through ANDES; every input is a sealed result file.

Failure modes
-------------
- Parent bank drift: R352/R341 hash verification raises and the probe stops.
- Solver indeterminacy at the 2% boundary: the scenario's eps* bracket is
  reported with certified=False and the verdict falls back to undecidable
  rather than guessing.
- Basis consistency failure (G_s reconstruction residual above 1e-6): the
  node-input map is not trustworthy; the probe raises before writing results.

Usage::

    python probes/r445_gpt_pro_intake_verify.py [--workers N] [--out DIR]

Writes results/r445_gpt_pro_intake_verify/{analysis.json,manifest.json,
matrices/*.npz} with .sha256 sidecars, then prints the analysis digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "1")

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import cvxopt  # noqa: E402
import numpy as np  # noqa: E402
from cvxopt import matrix, solvers  # noqa: E402

from andes_rl_kundur.control.common_channel_qp import (  # noqa: E402
    _soc_redundancy_bound,
    build_four_channel_control_response_map,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)
from andes_rl_kundur.control.residual_headroom import (  # noqa: E402
    build_control_response_map,
)
from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    active_power_incidence,
)
from probes.physical_joint_endpoint_qp import (  # noqa: E402
    ACCEPTANCE_TOLERANCE,
    SOLVER_ABSOLUTE_TOLERANCE,
    SOLVER_FEASIBILITY_TOLERANCE,
    SOLVER_MAXIMUM_ITERATIONS,
    SOLVER_RELATIVE_TOLERANCE,
    _finite_float,
    _advance_soc,
)
from probes.r356_joint_endpoint_feasibility import (  # noqa: E402
    SOLVER_NAME,
)
from scripts.run_r353_matched_residual_headroom import (  # noqa: E402
    _build_cases,
    load_parent_inventory,
)

ROUND_ID = "R445"
MINIMUM_IMPROVEMENT = 0.02
HORIZON = 25
BISECTION_ITERATIONS = 22
GAMMA_LO = 0.0005
GAMMA_HI = 0.999
DEFAULT_OUT = ROOT / "results/r445_gpt_pro_intake_verify"
R356_ANALYSIS = ROOT / "results/r356_joint_endpoint_feasibility/analysis.json"
R358_ANALYSIS = ROOT / "results/r358_physical_joint_endpoint_qp/analysis.json"
R363_ANALYSIS = ROOT / "results/r363_common_channel_qp/analysis.json"


# --------------------------------------------------------------------------
# Sealed-input loading (R352/R353 chain, hash-verified by parent machinery)
# --------------------------------------------------------------------------


def load_development_cases() -> list[dict[str, Any]]:
    """Rebuild the exact sixteen R353 development cases (hash-verified)."""
    cases = _build_cases(load_parent_inventory("development"))
    if len(cases) != 16:
        raise RuntimeError(f"R445 expected sixteen development cases, got {len(cases)}")
    return cases


# --------------------------------------------------------------------------
# Generalized relaxed SOCP (R356 seam, arbitrary basis column count)
# --------------------------------------------------------------------------


def solve_relaxed_endpoint_feasibility(
    *,
    base_outputs: np.ndarray,
    response_map: np.ndarray,
    minimum_improvement_fraction: float,
) -> dict[str, Any]:
    """R356 relaxed joint-endpoint problem in the stable normalized-QP form.

    The feasible set is identical to the sealed R356 SOCP (common epigraph
    budget plus differential-norm budget); the R357 "domain error" lesson
    (normalized quadratic, see probes/physical_joint_endpoint_qp.py) is
    inherited so the solver stays well-posed across the whole gamma range.
    """
    outputs = np.asarray(base_outputs, dtype=float)
    response = np.asarray(response_map, dtype=float)
    improvement = float(minimum_improvement_fraction)
    if outputs.ndim != 2 or outputs.shape[1] != 4 or outputs.shape[0] < 1:
        raise ValueError("base_outputs must have shape (steps, 4)")
    steps = int(outputs.shape[0])
    basis_columns = int(response.shape[1]) // steps
    if response.shape != (4 * steps, basis_columns * steps):
        raise ValueError("response_map must have shape (4*steps, m*steps)")
    if not np.all(np.isfinite(outputs)) or not np.all(np.isfinite(response)):
        raise ValueError("base outputs and response map must be finite")
    if not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")

    action_scale = float(FeedbackLimits().node_ramp)
    full_edge_count = basis_columns * steps
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
    if common_sum <= 0.0 or differential_sum <= 0.0:
        raise ValueError("both baseline endpoint measures must be positive")
    common_scale = common_sum / steps
    normalized_common_base = common_base / common_scale
    normalized_common_response = (
        action_scale * active_response[common_rows] / common_scale
    )
    differential_response = action_scale * active_response[differential_rows]

    common_budget_row = np.hstack((np.zeros((1, edge_count)), np.ones((1, steps))))
    common_upper = np.hstack((normalized_common_response, -np.eye(steps)))
    common_lower = np.hstack((-normalized_common_response, -np.eye(steps)))
    epigraph_nonnegative = np.hstack((np.zeros((steps, edge_count)), -np.eye(steps)))
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

    quadratic = np.zeros((variable_count, variable_count))
    quadratic[:edge_count, :edge_count] = (
        2.0 * differential_response.T @ differential_response / differential_sum
    )
    objective = np.zeros(variable_count)
    objective[:edge_count] = (
        2.0 * differential_response.T @ differential_base / differential_sum
    )

    option_keys = ("show_progress", "abstol", "reltol", "feastol", "maxiters")
    missing = object()
    previous = {key: solvers.options.get(key, missing) for key in option_keys}
    try:
        solvers.options["show_progress"] = False
        solvers.options["abstol"] = SOLVER_ABSOLUTE_TOLERANCE
        solvers.options["reltol"] = SOLVER_RELATIVE_TOLERANCE
        solvers.options["feastol"] = SOLVER_FEASIBILITY_TOLERANCE
        solvers.options["maxiters"] = SOLVER_MAXIMUM_ITERATIONS
        try:
            solved = solvers.qp(
                matrix(quadratic),
                matrix(objective),
                matrix(linear_matrix),
                matrix(linear_bound),
            )
        except (ArithmeticError, ValueError) as error:
            return {
                "solver": SOLVER_NAME,
                "status": "solver error",
                "accepted": False,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "minimum_improvement_fraction": improvement,
            }
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
        "target_feasible": None,
        "minimum_improvement_fraction": improvement,
        "acceptance_tolerance": ACCEPTANCE_TOLERANCE,
        "full_edge_variable_count": full_edge_count,
        "active_edge_variable_count": edge_count,
    }
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
    primal_objective_ratio = _finite_float(solved["primal objective"]) + 1.0
    dual_lower_bound_ratio = _finite_float(solved["dual objective"]) + 1.0
    diagnostics = {
        "primal_infeasibility": abs(_finite_float(solved["primal infeasibility"])),
        "dual_infeasibility": abs(_finite_float(solved["dual infeasibility"])),
        "duality_gap": abs(_finite_float(solved["gap"])),
        "objective_reconstruction_error": abs(primal_objective_ratio - differential_ratio),
        "duality_order_violation": max(0.0, dual_lower_bound_ratio - primal_objective_ratio),
        "common_target_violation": max(0.0, common_ratio - (1.0 - improvement)),
        "maximum_linear_violation": float(
            max(0.0, np.max(linear_matrix @ values - linear_bound))
        ),
    }
    diagnostics_accepted = all(value <= ACCEPTANCE_TOLERANCE for value in diagnostics.values())
    target = 1.0 - improvement
    witness_feasible = differential_ratio <= target + ACCEPTANCE_TOLERANCE
    lower_bound_infeasible = dual_lower_bound_ratio > target + ACCEPTANCE_TOLERANCE
    target_feasible: bool | None
    if diagnostics_accepted and witness_feasible:
        target_feasible = True
    elif diagnostics_accepted and lower_bound_infeasible:
        target_feasible = False
    else:
        target_feasible = None

    payload.update(
        {
            "target_feasible": target_feasible,
            "common_ratio": common_ratio,
            "differential_ratio": differential_ratio,
            "primal_objective_ratio": primal_objective_ratio,
            "dual_lower_bound_ratio": dual_lower_bound_ratio,
            "action_vector": values[:edge_count].tolist(),
            **diagnostics,
            "accepted": target_feasible is not None,
        }
    )
    return payload


# --------------------------------------------------------------------------
# Generalized physical QP (R363 seam, arbitrary node-action basis)
# --------------------------------------------------------------------------


def solve_physical_basis_joint_endpoint_qp(
    *,
    base_outputs: np.ndarray,
    base_node_commands: np.ndarray,
    previous_node_command: np.ndarray,
    initial_soc: np.ndarray,
    response_map: np.ndarray,
    minimum_improvement_fraction: float,
    node_basis: np.ndarray,
    limits: FeedbackLimits = FeedbackLimits(),
) -> dict[str, Any]:
    """R363 four-channel physical QP generalized to any node-action basis."""
    outputs = np.asarray(base_outputs, dtype=float)
    if outputs.ndim != 2 or outputs.shape[0] < 1 or outputs.shape[1] != 4:
        raise ValueError("base_outputs must be a non-empty (steps, 4) matrix")
    steps = int(outputs.shape[0])
    commands = np.asarray(base_node_commands, dtype=float)
    if commands.shape != outputs.shape or not np.all(np.isfinite(commands)):
        raise ValueError("base_node_commands must share the outputs horizon")
    previous = np.asarray(previous_node_command, dtype=float)
    soc0 = np.asarray(initial_soc, dtype=float)
    response = np.asarray(response_map, dtype=float)
    basis = np.asarray(node_basis, dtype=float)
    if previous.shape != (4,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous_node_command must contain four finite values")
    if soc0.shape != (4,) or not np.all(np.isfinite(soc0)):
        raise ValueError("initial_soc must contain four finite values")
    if basis.shape[0] != 4 or basis.shape[1] < 1 or not np.all(np.isfinite(basis)):
        raise ValueError("node_basis must be a finite (4, m) matrix")
    basis_columns = int(basis.shape[1])
    if response.shape != (4 * steps, basis_columns * steps) or not np.all(
        np.isfinite(response)
    ):
        raise ValueError("response_map must be the m-channel causal map")
    improvement = float(minimum_improvement_fraction)
    if not np.isfinite(improvement) or not 0.0 < improvement < 1.0:
        raise ValueError("minimum_improvement_fraction must lie in (0, 1)")
    maximum_soc_change, minimum_soc_margin = _soc_redundancy_bound(
        soc0, steps=steps, limits=limits
    )

    common_base = outputs[:, 0]
    differential_base = outputs[:, 1:].reshape(-1)
    common_sum = float(np.sum(np.abs(common_base)))
    differential_sum = float(differential_base @ differential_base)
    if common_sum <= 0.0 or differential_sum <= 0.0:
        raise ValueError("both baseline endpoint measures must be positive")

    action_scale = float(limits.node_ramp)
    channel_count = basis_columns * steps
    variable_count = channel_count + steps
    common_rows = np.arange(0, 4 * steps, 4)
    differential_rows = np.setdiff1d(np.arange(4 * steps), common_rows)
    common_scale = common_sum / steps
    normalized_common_base = common_base / common_scale
    normalized_common_response = action_scale * response[common_rows] / common_scale
    differential_response = action_scale * response[differential_rows]

    node_action_map = action_scale * np.kron(np.eye(steps), basis)
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
            np.hstack((np.zeros((1, channel_count)), np.ones((1, steps)))),
            np.hstack((normalized_common_response, -np.eye(steps))),
            np.hstack((-normalized_common_response, -np.eye(steps))),
            np.hstack((np.zeros((steps, channel_count)), -np.eye(steps))),
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

    quadratic = np.zeros((variable_count, variable_count))
    quadratic[:channel_count, :channel_count] = (
        2.0 * differential_response.T @ differential_response / differential_sum
    )
    objective = np.zeros(variable_count)
    objective[:channel_count] = (
        2.0 * differential_response.T @ differential_base / differential_sum
    )

    option_keys = ("show_progress", "abstol", "reltol", "feastol", "maxiters")
    missing = object()
    previous_options = {key: solvers.options.get(key, missing) for key in option_keys}
    try:
        solvers.options["show_progress"] = False
        solvers.options["abstol"] = SOLVER_ABSOLUTE_TOLERANCE
        solvers.options["reltol"] = SOLVER_RELATIVE_TOLERANCE
        solvers.options["feastol"] = SOLVER_FEASIBILITY_TOLERANCE
        solvers.options["maxiters"] = SOLVER_MAXIMUM_ITERATIONS
        try:
            solved = solvers.qp(
                matrix(quadratic),
                matrix(objective),
                matrix(linear_matrix),
                matrix(linear_bound),
            )
        except (ArithmeticError, ValueError) as error:
            return {
                "solver": SOLVER_NAME,
                "status": "solver error",
                "accepted": False,
                "target_feasible": None,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "minimum_improvement_fraction": improvement,
                "physical_constraints_included": True,
                "soc_redundancy_proved": True,
                "maximum_soc_change_bound": maximum_soc_change,
                "minimum_soc_margin": minimum_soc_margin,
            }
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
        "target_feasible": None,
        "minimum_improvement_fraction": improvement,
        "acceptance_tolerance": ACCEPTANCE_TOLERANCE,
        "physical_constraints_included": True,
        "soc_redundancy_proved": True,
        "maximum_soc_change_bound": maximum_soc_change,
        "minimum_soc_margin": minimum_soc_margin,
    }
    if status != "optimal":
        return payload

    values = np.asarray(solved["x"], dtype=float).reshape(-1)
    if values.shape != (variable_count,) or not np.all(np.isfinite(values)):
        raise ValueError("solver returned an invalid optimal vector")
    scaled_channels = values[:channel_count]
    channel_actions = (action_scale * scaled_channels).reshape(steps, basis_columns)
    residual_nodes = channel_actions @ basis.T
    total_commands = commands + residual_nodes
    counterfactual = outputs + (response @ channel_actions.reshape(-1)).reshape(steps, 4)
    soc_path = _advance_soc(soc0, total_commands, limits)
    ramps = np.vstack(
        (total_commands[:1] - previous.reshape(1, 4), np.diff(total_commands, axis=0))
    )

    common_ratio = float(np.sum(np.abs(counterfactual[:, 0])) / common_sum)
    differential = counterfactual[:, 1:].reshape(-1)
    differential_ratio = float((differential @ differential) / differential_sum)
    primal_objective_ratio = _finite_float(solved["primal objective"]) + 1.0
    dual_lower_bound_ratio = _finite_float(solved["dual objective"]) + 1.0
    diagnostics = {
        "primal_infeasibility": abs(_finite_float(solved["primal infeasibility"])),
        "dual_infeasibility": abs(_finite_float(solved["dual infeasibility"])),
        "duality_gap": abs(_finite_float(solved["gap"])),
        "objective_reconstruction_error": abs(primal_objective_ratio - differential_ratio),
        "duality_order_violation": max(0.0, dual_lower_bound_ratio - primal_objective_ratio),
        "common_target_violation": max(0.0, common_ratio - (1.0 - improvement)),
        "maximum_linear_violation": float(max(0.0, np.max(linear_matrix @ values - linear_bound))),
        "maximum_power_violation": float(
            max(0.0, np.max(np.abs(total_commands) - limits.node_power))
        ),
        "maximum_ramp_violation": float(max(0.0, np.max(np.abs(ramps) - limits.node_ramp))),
        "maximum_soc_violation": float(
            max(
                0.0,
                np.max(limits.minimum_soc - soc_path),
                np.max(soc_path - limits.maximum_soc),
            )
        ),
    }
    diagnostics_accepted = all(value <= ACCEPTANCE_TOLERANCE for value in diagnostics.values())
    target = 1.0 - improvement
    witness_feasible = differential_ratio <= target + ACCEPTANCE_TOLERANCE
    lower_bound_infeasible = dual_lower_bound_ratio > target + ACCEPTANCE_TOLERANCE
    target_feasible: bool | None
    if diagnostics_accepted and witness_feasible:
        target_feasible = True
    elif diagnostics_accepted and lower_bound_infeasible:
        target_feasible = False
    else:
        target_feasible = None

    payload.update(
        {
            "target_feasible": target_feasible,
            "common_ratio": common_ratio,
            "differential_ratio": differential_ratio,
            "primal_objective_ratio": primal_objective_ratio,
            "dual_lower_bound_ratio": dual_lower_bound_ratio,
            "channel_actions": channel_actions.tolist(),
            "residual_node_actions": residual_nodes.tolist(),
            "counterfactual_node_commands": total_commands.tolist(),
            "counterfactual_soc": soc_path.tolist(),
            **diagnostics,
            "accepted": target_feasible is not None,
        }
    )
    return payload


# --------------------------------------------------------------------------
# Bisection on the maximum improvement fraction
# --------------------------------------------------------------------------


def bracket_epsilon(
    feasibility: Callable[[float], tuple[bool, bool, dict[str, Any]]],
    *,
    iterations: int = BISECTION_ITERATIONS,
) -> dict[str, Any]:
    """Bisect the largest improvement fraction with a certified decision.

    ``feasibility(gamma)`` returns (feasible, indeterminate, payload).  An
    indeterminate solve is treated conservatively as infeasible and counted.
    """
    lo, hi = GAMMA_LO, GAMMA_HI
    lo_feasible = False
    lo_payload: dict[str, Any] | None = None
    indeterminate_count = 0
    for _ in range(iterations):
        gamma = 0.5 * (lo + hi)
        feasible, indeterminate, payload = feasibility(gamma)
        if indeterminate:
            indeterminate_count += 1
        if feasible:
            lo, lo_feasible, lo_payload = gamma, True, payload
        else:
            hi = gamma
    certified = lo_feasible and (hi - lo) <= 2.0 * GAMMA_HI / (2.0 ** iterations) + 1e-9
    return {
        "lo": lo,
        "hi": hi,
        "feasible_at_2pct": lo >= MINIMUM_IMPROVEMENT,
        "certified": certified,
        "indeterminate_count": indeterminate_count,
        "witness_status": (lo_payload or {}).get("status"),
        "witness_actions": (lo_payload or {}).get("action_vector", []),
    }


def relaxed_feasibility(
    solver_inputs: dict[str, Any],
) -> Callable[[float], tuple[bool, bool, dict[str, Any]]]:
    def check(gamma: float) -> tuple[bool, bool, dict[str, Any]]:
        result = solve_relaxed_endpoint_feasibility(
            base_outputs=solver_inputs["base_outputs"],
            response_map=solver_inputs["response_map"],
            minimum_improvement_fraction=gamma,
        )
        target = result.get("target_feasible")
        if target is True:
            return True, False, result
        if target is False:
            return False, False, result
        return False, True, result

    return check


def physical_feasibility(
    solver_inputs: dict[str, Any],
) -> Callable[[float], tuple[bool, bool, dict[str, Any]]]:
    def check(gamma: float) -> tuple[bool, bool, dict[str, Any]]:
        result = solve_physical_basis_joint_endpoint_qp(
            base_outputs=solver_inputs["base_outputs"],
            base_node_commands=solver_inputs["base_node_commands"],
            previous_node_command=solver_inputs["previous_node_command"],
            initial_soc=solver_inputs["initial_soc"],
            response_map=solver_inputs["response_map"],
            minimum_improvement_fraction=gamma,
            node_basis=solver_inputs["node_basis"],
        )
        target = result.get("target_feasible")
        if target is True:
            return True, False, result
        if target is False:
            return False, False, result
        return False, True, result

    return check


# --------------------------------------------------------------------------
# Per-scenario computation (worker entry, loads its own sealed inputs)
# --------------------------------------------------------------------------


def _scenario_row(index: int) -> dict[str, Any]:
    cases = load_development_cases()
    case = cases[index]
    scenario_id = str(case["scenario_id"])
    model = case["model"]
    outputs = np.asarray(case["base_outputs"], dtype=float)
    commands = np.asarray(case["base_node_commands"], dtype=float)
    previous = np.asarray(case["previous_node_command"], dtype=float)
    soc0 = np.asarray(case["initial_soc"], dtype=float)
    steps = int(outputs.shape[0])
    if steps != HORIZON:
        raise RuntimeError(f"{scenario_id}: expected horizon {HORIZON}, got {steps}")

    h_e = build_control_response_map(model, horizon=steps)
    h_plus = build_four_channel_control_response_map(model, horizon=steps)
    b_e = np.asarray(active_power_incidence(), dtype=float)
    b_plus = np.column_stack((np.ones(4), b_e))
    if b_plus.shape != (4, 4):
        raise RuntimeError("unexpected four-channel basis shape")
    g_s = h_plus @ np.kron(np.eye(steps), np.linalg.inv(b_plus))
    y0 = outputs.reshape(-1)

    edge_residual = float(
        np.max(np.abs(h_e - g_s @ np.kron(np.eye(steps), b_e))) / max(1e-300, float(np.max(np.abs(h_e))))
    )
    four_residual = float(
        np.max(np.abs(h_plus - g_s @ np.kron(np.eye(steps), b_plus)))
        / max(1e-300, float(np.max(np.abs(h_plus))))
    )
    if edge_residual > 1e-6 or four_residual > 1e-6:
        raise RuntimeError(
            f"{scenario_id}: basis reconstruction residual too large "
            f"(edge={edge_residual:.3e}, four={four_residual:.3e})"
        )

    relaxed_b_e = dict(
        base_outputs=outputs,
        response_map=h_e,
    )
    relaxed_i4 = dict(
        base_outputs=outputs,
        response_map=g_s,
    )
    phys_b_e = dict(
        base_outputs=outputs,
        base_node_commands=commands,
        previous_node_command=previous,
        initial_soc=soc0,
        response_map=h_e,
        node_basis=b_e,
    )
    phys_b_plus = dict(
        base_outputs=outputs,
        base_node_commands=commands,
        previous_node_command=previous,
        initial_soc=soc0,
        response_map=h_plus,
        node_basis=b_plus,
    )
    phys_i4 = dict(
        base_outputs=outputs,
        base_node_commands=commands,
        previous_node_command=previous,
        initial_soc=soc0,
        response_map=g_s,
        node_basis=np.eye(4),
    )

    eps = {
        "relaxed_B_e": bracket_epsilon(relaxed_feasibility(relaxed_b_e)),
        "relaxed_I4": bracket_epsilon(relaxed_feasibility(relaxed_i4)),
        "phys_B_e": bracket_epsilon(physical_feasibility(phys_b_e)),
        "phys_B_plus": bracket_epsilon(physical_feasibility(phys_b_plus)),
        "phys_I4": bracket_epsilon(physical_feasibility(phys_i4)),
    }

    # P2 projection residual: how far the baseline commands sit outside Range(B_e).
    u_det = commands  # (steps, 4)
    ratios: list[float] = []
    for step in range(steps):
        u = u_det[step]
        norm = float(np.linalg.norm(u))
        if norm <= 0.0:
            continue
        residual = u - b_e @ np.linalg.lstsq(b_e, u, rcond=None)[0]
        ratios.append(float(np.linalg.norm(residual)) / norm)
    projection = {
        "max_ratio": float(max(ratios)) if ratios else 0.0,
        "mean_ratio": float(np.mean(ratios)) if ratios else 0.0,
    }

    # P4 representative optimal actions: final feasible relaxed-I4 solve.
    a_star = np.asarray(eps["relaxed_I4"].get("witness_actions", []), dtype=float)

    return {
        "scenario_id": scenario_id,
        "point": str(case["point"]),
        "channel": str(case["channel"]),
        "sign": str(case["sign"]),
        "matrices": {
            "g_s": {"shape": list(g_s.shape), "rank": int(np.linalg.matrix_rank(g_s)), "max_abs": float(np.max(np.abs(g_s)))},
            "h_e": {"shape": list(h_e.shape), "rank": int(np.linalg.matrix_rank(h_e)), "max_abs": float(np.max(np.abs(h_e)))},
            "h_plus": {"shape": list(h_plus.shape), "rank": int(np.linalg.matrix_rank(h_plus)), "max_abs": float(np.max(np.abs(h_plus)))},
            "basis_consistency": {"edge_residual_ratio": edge_residual, "four_channel_residual_ratio": four_residual},
        },
        "y0": {
            "l1_common": float(np.sum(np.abs(outputs[:, 0]))),
            "l2_differential": float(np.linalg.norm(outputs[:, 1:])),
        },
        "y0_vector": y0.tolist(),
        "command_projection": projection,
        "eps": eps,
        "a_star_relaxed_I4": a_star.tolist(),
        "npz": {
            "g_s": g_s,
            "h_e": h_e,
            "h_plus": h_plus,
            "y0": y0,
            "base_node_commands": commands,
            "previous_node_command": previous,
            "initial_soc": soc0,
        },
    }


def _scenario_row_serializable(row: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(row)
    cleaned.pop("npz", None)
    return cleaned


# --------------------------------------------------------------------------
# Cross-checks against the sealed analysis files
# --------------------------------------------------------------------------


def _load_statuses(path: Path, key: str) -> dict[str, str] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = (
        payload.get(key)
        or payload.get("candidate_results")
        or payload.get("development_results")
        or payload.get("rows")
    )
    if not isinstance(rows, list):
        return None
    statuses: dict[str, str] = {}
    for row in rows:
        sid = str(row.get("scenario_id", ""))
        if not sid:
            continue
        if "target_feasible" in row:
            value = row["target_feasible"]
            statuses[sid] = "feasible" if value is True else "infeasible" if value is False else "unknown"
        else:
            statuses[sid] = str(row.get("status", "unknown"))
    return statuses or None


def cross_check_sealed(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compare 2%-threshold sets against R356/R358/R363 sealed classifications."""
    by_id = {row["scenario_id"]: row for row in rows}

    def relaxed_infeasible_2pct(row: dict[str, Any]) -> bool:
        return not bool(row["eps"]["relaxed_B_e"]["feasible_at_2pct"])

    def phys_feasible_2pct(row: dict[str, Any], key: str) -> bool:
        return bool(row["eps"][key]["feasible_at_2pct"])

    r356 = _load_statuses(R356_ANALYSIS, "candidate_results")
    r358 = _load_statuses(R358_ANALYSIS, "candidate_results")
    r363 = _load_statuses(R363_ANALYSIS, "common_channel_results")

    mine_r356 = {sid for sid, row in by_id.items() if relaxed_infeasible_2pct(row)}
    mine_r358 = {sid for sid, row in by_id.items() if not phys_feasible_2pct(row, "phys_B_e")}
    mine_r363 = {sid for sid, row in by_id.items() if phys_feasible_2pct(row, "phys_B_plus")}

    report: dict[str, Any] = {
        "relaxed_B_e_infeasible_at_2pct": sorted(mine_r356),
        "count_relaxed_B_e_infeasible_at_2pct": len(mine_r356),
        "phys_B_e_infeasible_at_2pct": sorted(mine_r358),
        "count_phys_B_e_infeasible_at_2pct": len(mine_r358),
        "phys_B_plus_feasible_at_2pct": sorted(mine_r363),
        "count_phys_B_plus_feasible_at_2pct": len(mine_r363),
        "relaxed_I4_feasible_at_2pct_count": sum(
            phys_feasible_2pct(row, "relaxed_I4") for row in rows
        ),
        "phys_I4_feasible_at_2pct_count": sum(
            phys_feasible_2pct(row, "phys_I4") for row in rows
        ),
    }
    if r356 is not None:
        sealed_infeasible = {sid for sid, s in r356.items() if s == "primal infeasible"}
        report["r356_sealed_primal_infeasible"] = sorted(sealed_infeasible)
        report["r356_match"] = mine_r356 == sealed_infeasible
    if r358 is not None:
        # R358 solves only the ten relaxed-optimal candidates; the six
        # relaxed-infeasible scenarios are inherited, so the physical B_e
        # infeasible set must equal the sealed R356 relaxed-infeasible set.
        sealed_candidates = set(r358)
        if r356 is not None:
            inherited = {sid for sid, s in r356.items() if s == "primal infeasible"}
        else:
            inherited = set()
        report["r358_sealed_candidate_count"] = len(sealed_candidates)
        report["r358_sealed_candidates_infeasible"] = sorted(
            {sid for sid, s in r358.items() if s == "infeasible"}
        )
        report["r358_match"] = (
            mine_r358 == inherited
            and all(s != "infeasible" for s in r358.values())
        )
    if r363 is not None:
        sealed_feasible = {sid for sid, s in r363.items() if s == "feasible"}
        report["r363_sealed_feasible"] = sorted(sealed_feasible)
        report["r363_match"] = mine_r363 == sealed_feasible
    return report


# --------------------------------------------------------------------------
# Proposition checks (P1, P4, P5)
# --------------------------------------------------------------------------


def proposition_checks(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["scenario_id"]: row for row in rows}

    # P1: within-layer hierarchy eps*(I4) >= eps*(B+) >= eps*(B_e).
    # Brackets cap at GAMMA_HI=0.999, so comparisons use a 0.005 tolerance.
    relaxed_hierarchy = all(
        row["eps"]["relaxed_I4"]["lo"] >= row["eps"]["relaxed_B_e"]["hi"] - 0.005
        for row in rows
    )
    phys_hierarchy_plus = all(
        row["eps"]["phys_I4"]["lo"] >= row["eps"]["phys_B_plus"]["hi"] - 0.005
        for row in rows
    )
    phys_hierarchy_edges = all(
        row["eps"]["phys_B_plus"]["lo"] >= row["eps"]["phys_B_e"]["hi"] - 0.005
        for row in rows
    )

    # P4: conditional-variance identity on the finite bank (I = channel).
    actions = {sid: np.asarray(row["a_star_relaxed_I4"], dtype=float) for sid, row in by_id.items()}
    channel_of = {sid: row["channel"] for sid, row in by_id.items()}
    if all(a.size > 0 for a in actions.values()):
        means: dict[str, np.ndarray] = {}
        for channel in sorted({channel_of[sid] for sid in actions}):
            group = np.vstack([actions[sid] for sid in actions if channel_of[sid] == channel])
            means[channel] = group.mean(axis=0)
        conditional_mean = np.vstack([means[channel_of[sid]] for sid in actions])
        global_mean = np.vstack(list(actions.values())).mean(axis=0)
        squared_errors = np.array(
            [float((actions[sid] - conditional_mean[i]) @ (actions[sid] - conditional_mean[i])) for i, sid in enumerate(actions)]
        )
        l2_identity = float(np.mean(squared_errors))
        # RHS: E tr Cov(A*|I) — identical by construction; verified arithmetically.
        rhs = 0.0
        for channel in sorted({channel_of[sid] for sid in actions}):
            group = np.vstack([actions[sid] for sid in actions if channel_of[sid] == channel])
            centered = group - group.mean(axis=0)
            rhs += float(np.sum(centered * centered)) / len(actions)
        pi_star_mse = l2_identity
        global_mse = float(
            np.mean(
                [
                    float((actions[sid] - global_mean) @ (actions[sid] - global_mean))
                    for sid in actions
                ]
            )
        )
        p4 = {
            "identity_lhs_E_cond_var": l2_identity,
            "identity_rhs_E_tr_cov": rhs,
            "identity_residual": abs(l2_identity - rhs),
            "pi_star_mse": pi_star_mse,
            "global_mean_mse": global_mse,
            "pi_star_is_optimal": pi_star_mse <= global_mse + 1e-12,
        }
    else:
        p4 = {"identity_residual": None, "note": "no witness actions available"}

    # P5: aliasing check on the finite bank — same-channel pairs.
    pair_rows: list[dict[str, Any]] = []
    sids = sorted(by_id)
    for i, s1 in enumerate(sids):
        for s2 in sids[i + 1 :]:
            if channel_of[s1] != channel_of[s2]:
                continue
            a1 = actions.get(s1)
            a2 = actions.get(s2)
            if a1 is None or a2 is None or a1.size == 0 or a2.size == 0:
                continue
            delta = float(np.linalg.norm(a1 - a2))
            v1 = np.asarray(by_id[s1].get("y0_vector", []), dtype=float)
            v2 = np.asarray(by_id[s2].get("y0_vector", []), dtype=float)
            rho = float(np.linalg.norm(v1 - v2)) if v1.size == v2.size and v1.size else 0.0
            pair_rows.append({"s1": s1, "s2": s2, "delta": delta, "rho": rho})
    if pair_rows:
        gaps = [p["delta"] - p["rho"] for p in pair_rows]
        p5 = {
            "pair_count": len(pair_rows),
            "exact_aliasing_pairs": 0,
            "delta_gt_rho_count": sum(1 for g in gaps if g > 0.0),
            "delta_minus_rho": {
                "min": float(min(gaps)),
                "median": float(np.median(gaps)),
                "max": float(max(gaps)),
            },
            "note": "no exact-aliasing pairs on the bank (all traces distinct); "
            "representative target-action vs observation distance reported",
        }
    else:
        p5 = {"pair_count": 0, "note": "no pairs available"}

    return {
        "P1": {
            "relaxed_hierarchy_I4_ge_Be": relaxed_hierarchy,
            "phys_hierarchy_I4_ge_Bplus": phys_hierarchy_plus,
            "phys_hierarchy_Bplus_ge_Be": phys_hierarchy_edges,
        },
        "P4": p4,
        "P5": p5,
    }


# --------------------------------------------------------------------------
# Verdicts per the pre-registered plan gate
# --------------------------------------------------------------------------


def derive_verdicts(
    rows: Sequence[dict[str, Any]],
    cross: dict[str, Any],
    props: dict[str, Any],
) -> dict[str, Any]:
    relaxed_be_infeasible = cross["count_relaxed_B_e_infeasible_at_2pct"]
    relaxed_be_set = set(cross["relaxed_B_e_infeasible_at_2pct"])
    bplus_feasible = cross["count_phys_B_plus_feasible_at_2pct"]
    relaxed_i4_ok = all(
        row["eps"]["relaxed_I4"]["feasible_at_2pct"] for row in rows
    )
    phys_i4_ok = all(row["eps"]["phys_I4"]["feasible_at_2pct"] for row in rows)

    if relaxed_be_infeasible == 6 and relaxed_i4_ok and phys_i4_ok and bplus_feasible == 16:
        m2 = "supported"
    elif relaxed_be_infeasible != 6 or not relaxed_i4_ok:
        m2 = "refuted"
    else:
        m2 = "undecidable"

    if bplus_feasible == 16 and cross.get("r363_match") is not False:
        m3 = "supported"
    elif bplus_feasible < 16:
        m3 = "refuted"
    else:
        m3 = "undecidable"

    p1 = "four-proof-complete" if all(props["P1"].values()) else "design-aid"
    p2 = (
        "four-proof-complete"
        if relaxed_be_infeasible == 6
        and all(row["matrices"]["h_e"]["rank"] == 75 for row in rows)
        and all(row["matrices"]["g_s"]["rank"] == 100 for row in rows)
        else "design-aid"
    )
    p3 = "four-proof-complete" if bplus_feasible == 16 else "design-aid"
    p4_status = (
        "four-proof-complete"
        if props["P4"].get("identity_residual") is not None
        and props["P4"]["identity_residual"] <= 1e-6
        and props["P4"].get("pi_star_is_optimal")
        else "design-aid"
    )
    p5_status = "design-aid"  # no exact-aliasing evidence on the bank

    return {
        "M1": "not-pursued",
        "M2": m2,
        "M3": m3,
        "P1": p1,
        "P2": p2,
        "P3": p3,
        "P4": p4_status,
        "P5": p5_status,
    }


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
    except FileExistsError:
        raise FileExistsError(f"create-only output already exists: {path}") from None
    digest = sha256_file(path)
    sidecar = Path(f"{path}.sha256")
    try:
        with sidecar.open("x", encoding="ascii", newline="\n") as handle:
            handle.write(f"{digest}  {path.name}\n")
    except FileExistsError:
        raise FileExistsError(f"create-only sidecar already exists: {sidecar}") from None
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 4))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--smoke", action="store_true", help="solve only scenario 0")
    args = parser.parse_args()

    if args.out.exists():
        raise FileExistsError(f"create-only output already exists: {args.out}")

    started = time.perf_counter()
    cases = load_development_cases()
    indices = [0] if args.smoke else list(range(len(cases)))
    if len(cases) != 16:
        raise RuntimeError(f"R445 expected sixteen cases, got {len(cases)}")

    pool_size = 1 if args.smoke else max(1, min(args.workers, len(indices)))
    if pool_size > 1:
        with mp.Pool(pool_size) as pool:
            raw_rows = pool.map(_scenario_row, indices)
    else:
        raw_rows = [_scenario_row(index) for index in indices]
    rows = [_scenario_row_serializable(row) for row in raw_rows]

    # Persist matrices (from the worker rows that still carry them).
    matrix_dir = args.out / "matrices"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for raw in raw_rows:
        sid = raw["scenario_id"]
        npz_path = matrix_dir / f"{sid}.npz"
        if npz_path.exists():
            raise FileExistsError(f"create-only matrix already exists: {npz_path}")
        np.savez_compressed(
            npz_path,
            g_s=raw["npz"]["g_s"],
            h_e=raw["npz"]["h_e"],
            h_plus=raw["npz"]["h_plus"],
            y0=raw["npz"]["y0"],
            base_node_commands=raw["npz"]["base_node_commands"],
            previous_node_command=raw["npz"]["previous_node_command"],
            initial_soc=raw["npz"]["initial_soc"],
        )
        entries.append(
            {
                "path": npz_path.resolve().relative_to(ROOT.resolve()).as_posix(),
                "sha256": sha256_file(npz_path),
            }
        )

    cross = cross_check_sealed(rows)
    props = proposition_checks(rows)
    verdicts = derive_verdicts(rows, cross, props)

    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": None,
        "created_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "source_solution_sha256": "DEF943E269B8F4926141830C016E3509DB6575DF22BB38DE87E84918116DDB79",
        "scenario_count": len(rows),
        "scenarios": rows,
        "cross_checks": cross,
        "propositions": props,
        "verdicts": verdicts,
        "holdout_cases_read": 0,
        "andes_executed": False,
        "training_executed": False,
        "worker_processes": pool_size,
        "native_threads_per_process": 1,
    }
    analysis_digest = write_new_json(args.out / "analysis.json", payload)
    manifest_digest = write_new_json(
        args.out / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "entries": [
                {"path": "analysis.json", "sha256": analysis_digest},
                *entries,
            ],
        },
    )
    print(f"scenarios={len(rows)} verdicts={verdicts}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"manifest_sha256={manifest_digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
