"""Four-channel (common plus three-edge) physical response and QP primitives.

The module extends the R358 three-edge zero-common physical analysis with the
frozen common residual-power channel: it builds the full four-channel causal
response map from the R341 separate-input model and solves the same physical
joint-endpoint QP over the extended action basis ``[ones(4), incidence]``.
It owns no simulator, training process, repository artifact, or scientific
classification; every parameter is frozen and tuning-free.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import SeparateInputRealization
from andes_rl_kundur.control.residual_headroom import finite_matrix
from andes_rl_kundur.env.andes.model_first_contract import active_power_incidence

FOUR_CHANNEL_COLUMNS = 4


def build_four_channel_control_response_map(
    model: SeparateInputRealization,
    *,
    horizon: int,
) -> np.ndarray:
    """Return the causal output map for four control inputs (common plus edges)."""

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
        or control.shape != (order, FOUR_CHANNEL_COLUMNS)
        or output.shape != (4, order)
        or direct.shape != (4, FOUR_CHANNEL_COLUMNS)
        or not all(np.all(np.isfinite(item)) for item in (state, control, output, direct))
    ):
        raise ValueError("model must be a finite four-coordinate realization")

    response = np.zeros((4 * steps, FOUR_CHANNEL_COLUMNS * steps))
    powers = [np.eye(order)]
    for _ in range(max(0, steps - 1)):
        powers.append(powers[-1] @ state)
    for output_step in range(steps):
        row = slice(4 * output_step, 4 * (output_step + 1))
        for action_step in range(output_step + 1):
            column = slice(
                FOUR_CHANNEL_COLUMNS * action_step,
                FOUR_CHANNEL_COLUMNS * (action_step + 1),
            )
            lag = output_step - action_step
            response[row, column] = (
                direct if lag == 0 else output @ powers[lag - 1] @ control
            )
    if response.shape != (4 * steps, FOUR_CHANNEL_COLUMNS * steps):
        raise ValueError("four-channel response has the wrong shape")
    if not np.all(np.isfinite(response)):
        raise ValueError("four-channel response contains non-finite values")
    return response


def _soc_redundancy_bound(
    soc0: np.ndarray,
    *,
    steps: int,
    limits: FeedbackLimits,
) -> tuple[float, float]:
    """Return the frozen SOC slack and margin used by the R358 solver."""
    from probes.physical_joint_endpoint_qp import _soc_redundancy_bound as parent

    return parent(soc0, steps=steps, limits=limits)


def solve_common_channel_joint_endpoint_qp(
    *,
    base_outputs: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    response_map: object,
    minimum_improvement_fraction: float,
    limits: FeedbackLimits = FeedbackLimits(),
) -> dict[str, Any]:
    """Solve the R358 joint-endpoint QP over the four-channel action basis.

    Variables are ``4 * steps`` action coordinates (common plus three edge
    flows per sample) plus ``steps`` differential epigraph slacks.  The common
    channel is the fleet-equal net power injection ``ones(4)``; the three edge
    channels are the frozen zero-sum tree edges.  The common-coordinate
    endpoint must improve by the registered fraction while the differential
    endpoint is minimized under the exact physical limits.
    """

    from cvxopt import matrix, solvers

    from probes.physical_joint_endpoint_qp import (
        ACCEPTANCE_TOLERANCE,
        SOLVER_ABSOLUTE_TOLERANCE,
        SOLVER_MAXIMUM_ITERATIONS,
        SOLVER_NAME,
        SOLVER_RELATIVE_TOLERANCE,
        SOLVER_FEASIBILITY_TOLERANCE,
        _finite_float,
        _advance_soc,
    )

    outputs = finite_matrix(base_outputs, name="base_outputs", columns=4)
    commands = finite_matrix(
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
    if soc0.shape != (4,) or not np.all(np.isfinite(soc0)):
        raise ValueError("initial_soc must contain four finite values")
    if response.shape != (4 * steps, FOUR_CHANNEL_COLUMNS * steps) or not np.all(
        np.isfinite(response)
    ):
        raise ValueError("response_map must be the four-channel causal map")
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
    channel_count = FOUR_CHANNEL_COLUMNS * steps
    variable_count = channel_count + steps
    common_rows = np.arange(0, 4 * steps, 4)
    differential_rows = np.setdiff1d(np.arange(4 * steps), common_rows)
    common_scale = common_sum / steps
    normalized_common_base = common_base / common_scale
    normalized_common_response = action_scale * response[common_rows] / common_scale
    differential_response = action_scale * response[differential_rows]

    node_action_map = (
        action_scale
        * np.kron(
            np.eye(steps),
            np.column_stack((np.ones(4), active_power_incidence())),
        )
    )
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
    channel_actions = (action_scale * scaled_channels).reshape(steps, FOUR_CHANNEL_COLUMNS)
    residual_nodes = channel_actions @ np.column_stack(
        (np.ones(4), active_power_incidence())
    ).T
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
