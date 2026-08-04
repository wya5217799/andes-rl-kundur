"""Pure decision seam for the R330 untouched holdout."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

import numpy as np


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def analyse_r330_holdout(
    payload: object,
    contract: object,
    *,
    analysis_replay: bool,
) -> dict[str, object]:
    """Validate and classify one fixed estimator holdout execution."""

    execution = _mapping(payload) or {}
    sealed = _mapping(contract) or {}
    rows = _sequence(execution.get("rows"))
    expected_cases = _sequence(sealed.get("holdout_case_names"))
    expected_modes = _sequence(sealed.get("mismatch_modes"))
    expected_count = sealed.get("holdout_case_count")
    solver = _mapping(sealed.get("solver")) or {}
    limits = _mapping(sealed.get("limits")) or {}
    holdout_contract = _mapping(sealed.get("holdout")) or {}
    feasibility = _finite(solver.get("feasibility_tolerance"))
    maximum_solver_iterations = solver.get("maximum_iterations")
    node_power_limit = _finite(limits.get("node_power"))
    node_ramp_limit = _finite(limits.get("node_ramp"))
    minimum_soc_limit = _finite(limits.get("minimum_soc"))
    maximum_soc_limit = _finite(limits.get("maximum_soc"))
    normalized_limit = _finite(holdout_contract.get("maximum_normalized_solver_residual_ratio"))
    expected_inventory = {
        (str(case), str(mode)) for case in expected_cases for mode in expected_modes
    }
    inventory: set[tuple[str, str]] = set()
    ratios: list[float] = []
    ratios_by_mode: dict[str, list[float]] = {str(mode): [] for mode in expected_modes}
    valid_rows = bool(
        isinstance(expected_count, int)
        and not isinstance(expected_count, bool)
        and len(rows) == expected_count
        and len(expected_inventory) == expected_count
        and feasibility is not None
        and normalized_limit is not None
        and isinstance(maximum_solver_iterations, int)
        and not isinstance(maximum_solver_iterations, bool)
        and maximum_solver_iterations > 0
        and node_power_limit is not None
        and node_ramp_limit is not None
        and minimum_soc_limit is not None
        and maximum_soc_limit is not None
    )
    solver_failures = 0
    execution_errors = 0
    violations = 0
    maximum_constraint = 0.0
    maximum_primal = 0.0
    maximum_dual = 0.0
    for item in rows:
        row = _mapping(item)
        if row is None:
            valid_rows = False
            execution_errors += 1
            continue
        key = (str(row.get("case")), str(row.get("mismatch")))
        if (
            row.get("arm") != "retained_cross"
            or row.get("phase") != "holdout"
            or key not in expected_inventory
            or key in inventory
        ):
            valid_rows = False
        inventory.add(key)
        solver_status = row.get("solver_failed")
        error_status = row.get("execution_error")
        solver_failed = solver_status is True
        execution_error = error_status is True
        count = row.get("constraint_violation_count")
        constraint = _finite(row.get("maximum_constraint_residual"))
        primal = _finite(row.get("maximum_primal_residual_ratio"))
        dual = _finite(row.get("maximum_dual_residual_ratio"))
        zero_energy = _finite(row.get("zero_output_energy"))
        output_energy = _finite(row.get("output_energy"))
        ratio = _finite(row.get("output_energy_ratio"))
        action_energy = _finite(row.get("coordinate_action_energy"))
        maximum_node_power = _finite(row.get("maximum_node_power"))
        maximum_node_ramp = _finite(row.get("maximum_node_ramp"))
        minimum_soc = _finite(row.get("minimum_soc"))
        maximum_soc = _finite(row.get("maximum_soc"))
        row_solver_iterations = row.get("maximum_solver_iterations")
        solver_failures += int(solver_failed)
        execution_errors += int(execution_error)
        if any(
            value is None
            for value in (
                constraint,
                primal,
                dual,
                zero_energy,
                output_energy,
                ratio,
                action_energy,
                maximum_node_power,
                maximum_node_ramp,
                minimum_soc,
                maximum_soc,
            )
        ):
            valid_rows = False
            continue
        valid_rows = bool(
            valid_rows
            and solver_status is False
            and error_status is False
            and row.get("native_thread_limit_valid") is True
            and isinstance(count, int)
            and not isinstance(count, bool)
            and count == 0
            and constraint >= 0.0
            and constraint <= feasibility
            and primal >= 0.0
            and primal <= normalized_limit
            and dual >= 0.0
            and dual <= normalized_limit
            and zero_energy > np.finfo(float).tiny
            and output_energy >= 0.0
            and ratio >= 0.0
            and action_energy >= 0.0
            and maximum_node_power >= 0.0
            and maximum_node_power <= node_power_limit + feasibility
            and maximum_node_ramp >= 0.0
            and maximum_node_ramp <= node_ramp_limit + feasibility
            and minimum_soc >= minimum_soc_limit - feasibility
            and maximum_soc <= maximum_soc_limit + feasibility
            and minimum_soc <= maximum_soc
            and isinstance(row_solver_iterations, int)
            and not isinstance(row_solver_iterations, bool)
            and 0 <= row_solver_iterations <= maximum_solver_iterations
            and np.isclose(
                ratio,
                output_energy / zero_energy,
                rtol=1.0e-12,
                atol=1.0e-15,
            )
        )
        if isinstance(count, int) and not isinstance(count, bool):
            violations += count
        ratios.append(ratio)
        if key[1] in ratios_by_mode:
            ratios_by_mode[key[1]].append(ratio)
        maximum_constraint = max(maximum_constraint, constraint)
        maximum_primal = max(maximum_primal, primal)
        maximum_dual = max(maximum_dual, dual)
    valid_rows = valid_rows and inventory == expected_inventory
    guards = {
        "execution_contract_identity": (
            execution.get("round") == "R330"
            and execution.get("question") == "Q-0083"
            and execution.get("contract_payload_sha256") == _payload_sha256(sealed)
        ),
        "execution_receipt_identity": (execution.get("execution_receipt_identity") is True),
        "sealed_source_identity": execution.get("sealed_source_identity") is True,
        "parent_identity": execution.get("parent_identity") is True,
        "development_identity": execution.get("development_identity") is True,
        "design_fingerprint_identity": (execution.get("design_fingerprint_identity") is True),
        "mismatch_identity": execution.get("mismatch_identity") is True,
        "holdout_case_identity": execution.get("holdout_case_identity") is True,
        "limits_identity": execution.get("limits_identity") is True,
        "runtime_dependency_identity": (execution.get("runtime_dependency_identity") is True),
        "estimator_information_boundary": (execution.get("estimator_information_boundary") is True),
        "deterministic_execution_replay": (execution.get("deterministic_execution_replay") is True),
        "holdout_rows_valid": valid_rows,
        "physical_path_excluded": (execution.get("physical_execution_authorized") is False),
        "distributed_path_excluded": (
            execution.get("distributed_agent_implementation_authorized") is False
        ),
        "training_path_excluded": execution.get("training_authorized") is False,
        "eval_path_excluded": (execution.get("eval") == "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY"),
        "deterministic_analysis_replay": analysis_replay,
    }
    gates = _mapping(sealed.get("gates")) or {}
    mean_gate = _finite(gates.get("holdout_mean_output_energy_ratio_maximum"))
    worst_gate = _finite(gates.get("holdout_worst_output_energy_ratio_maximum"))
    mean = float(np.mean(ratios)) if ratios else None
    worst = max(ratios) if ratios else None
    passes = bool(
        all(value is True for value in guards.values())
        and mean is not None
        and worst is not None
        and mean_gate is not None
        and worst_gate is not None
        and mean <= mean_gate
        and worst <= worst_gate
        and sum(value < 1.0 for value in ratios) == expected_count
    )
    if any(value is not True for value in guards.values()):
        classification = "INVALID-ESTIMATOR-HOLDOUT"
    elif passes:
        classification = "ESTIMATOR-HOLDOUT-PASS"
    else:
        classification = "ESTIMATOR-HOLDOUT-NO-GO"
    return {
        "schema_version": 1,
        "round": "R330",
        "question": "Q-0083",
        "created_utc": execution.get("created_utc"),
        "seal_sha256": execution.get("seal_sha256"),
        "execution_sha256": execution.get("execution_sha256"),
        "holdout": {
            "valid": valid_rows,
            "case_count": len(rows),
            "mean_output_energy_ratio": mean,
            "worst_output_energy_ratio": worst,
            "case_count_below_zero_control": sum(value < 1.0 for value in ratios),
            "solver_failure_count": solver_failures,
            "execution_error_count": execution_errors,
            "constraint_violation_count": violations,
            "maximum_constraint_residual": maximum_constraint,
            "maximum_primal_residual_ratio": maximum_primal,
            "maximum_dual_residual_ratio": maximum_dual,
            "by_mismatch": {
                mode: {
                    "case_count": len(values),
                    "mean_output_energy_ratio": (float(np.mean(values)) if values else None),
                    "worst_output_energy_ratio": max(values) if values else None,
                    "case_count_below_zero_control": sum(value < 1.0 for value in values),
                }
                for mode, values in ratios_by_mode.items()
            },
        },
        "validity_guards": guards,
        "classification": classification,
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
