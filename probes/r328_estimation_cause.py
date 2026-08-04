"""Pure classifier for the R328 retained-arm estimation intervention."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _exact_state_summary(
    execution: Mapping[str, object], contract: Mapping[str, object]
) -> dict[str, object]:
    expected = contract.get("development_case_count")
    diagnosis = _mapping(contract.get("estimation_diagnosis")) or {}
    maximum_constraint = _finite(diagnosis.get("maximum_constraint_residual"))
    maximum_normalized = _finite(diagnosis.get("maximum_normalized_residual_ratio"))
    rows = _sequence(execution.get("rows"))
    valid = bool(
        isinstance(expected, int)
        and not isinstance(expected, bool)
        and maximum_constraint is not None
        and maximum_normalized is not None
        and len(rows) == expected
    )
    ratios: list[float] = []
    cases: set[str] = set()
    solver_failure_count = 0
    execution_error_count = 0
    constraint_violation_count = 0
    maximum_constraint_residual = 0.0
    maximum_primal_ratio = 0.0
    maximum_dual_ratio = 0.0
    maximum_state_error = 0.0
    for item in rows:
        row = _mapping(item)
        if row is None:
            valid = False
            execution_error_count += 1
            continue
        case = row.get("case")
        if (
            row.get("arm") != "retained_cross"
            or not isinstance(case, str)
            or not case
            or case in cases
        ):
            valid = False
        else:
            cases.add(case)
        solver_failed = row.get("solver_failed") is True
        execution_error = row.get("execution_error") is True
        solver_failure_count += int(solver_failed)
        execution_error_count += int(execution_error)
        violations = row.get("constraint_violation_count")
        residual = _finite(row.get("maximum_constraint_residual"))
        primal = _finite(row.get("maximum_primal_residual_ratio"))
        dual = _finite(row.get("maximum_dual_residual_ratio"))
        state_error = _finite(row.get("exact_state_construction_error"))
        ratio = _finite(row.get("output_energy_ratio"))
        if any(value is None for value in (residual, primal, dual, state_error, ratio)):
            valid = False
            continue
        maximum_constraint_residual = max(maximum_constraint_residual, float(residual))
        maximum_primal_ratio = max(maximum_primal_ratio, float(primal))
        maximum_dual_ratio = max(maximum_dual_ratio, float(dual))
        maximum_state_error = max(maximum_state_error, float(state_error))
        ratios.append(float(ratio))
        valid = bool(
            valid
            and not solver_failed
            and not execution_error
            and isinstance(violations, int)
            and not isinstance(violations, bool)
            and violations == 0
            and float(residual) <= float(maximum_constraint)
            and float(primal) <= float(maximum_normalized)
            and float(dual) <= float(maximum_normalized)
            and float(state_error) == 0.0
        )
        if isinstance(violations, int) and not isinstance(violations, bool):
            constraint_violation_count += violations
    return {
        "valid": valid,
        "case_count": len(rows),
        "solver_failure_count": solver_failure_count,
        "execution_error_count": execution_error_count,
        "constraint_violation_count": constraint_violation_count,
        "mean_output_energy_ratio": float(np.mean(ratios)) if ratios else None,
        "worst_output_energy_ratio": max(ratios) if ratios else None,
        "case_count_below_zero_control": sum(value < 1.0 for value in ratios),
        "maximum_constraint_residual": maximum_constraint_residual,
        "maximum_primal_residual_ratio": maximum_primal_ratio,
        "maximum_dual_residual_ratio": maximum_dual_ratio,
        "maximum_exact_state_construction_error": maximum_state_error,
    }


def _parent_summary(
    parent: Mapping[str, object], contract: Mapping[str, object]
) -> tuple[dict[str, object], bool]:
    arms = _mapping(parent.get("arms")) or {}
    retained = _mapping(arms.get("retained_cross")) or {}
    development = _mapping(retained.get("development")) or {}
    gates = _mapping(contract.get("gates")) or {}
    mean = _finite(development.get("mean_output_energy_ratio"))
    worst = _finite(development.get("worst_output_energy_ratio"))
    mean_gate = _finite(gates.get("development_mean_output_energy_ratio_maximum"))
    worst_gate = _finite(gates.get("development_worst_output_energy_ratio_maximum"))
    valid = bool(
        parent.get("classification") == "DEVELOPMENT-NO-GO"
        and parent.get("combined_solver_repair_passed") is True
        and parent.get("holdout_accessed") is False
        and development.get("valid") is True
        and mean is not None
        and worst is not None
        and mean_gate is not None
        and worst_gate is not None
    )
    failed = bool(valid and (float(mean) > float(mean_gate) or float(worst) > float(worst_gate)))
    return {
        "valid": valid,
        "mean_output_energy_ratio": mean,
        "worst_output_energy_ratio": worst,
        "failed_absolute_gate": failed,
    }, failed


def analyse_r328_estimation_diagnosis(
    payload: object,
    contract: object,
    parent_analysis: object,
    *,
    analysis_replay: bool,
) -> dict[str, object]:
    """Classify whether exact retained state rescues the frozen controller."""

    execution = _mapping(payload) or {}
    sealed = _mapping(contract) or {}
    parent = _mapping(parent_analysis) or {}
    exact = _exact_state_summary(execution, sealed)
    parent_summary, parent_failed = _parent_summary(parent, sealed)
    guards = {
        "sealed_source_identity": execution.get("sealed_source_identity") is True,
        "parent_identity": execution.get("parent_identity") is True,
        "state_coordinate_identity": execution.get("state_coordinate_identity") is True,
        "deterministic_execution_replay": (execution.get("deterministic_execution_replay") is True),
        "holdout_protected": execution.get("holdout_accessed") is False,
        "cross_deleted_oracle_excluded": (execution.get("cross_deleted_oracle_accessed") is False),
        "parent_valid_failed_output_feedback": parent_summary.get("valid") is True
        and parent_failed,
        "exact_state_trace_valid": exact.get("valid") is True,
        "deterministic_analysis_replay": analysis_replay,
    }
    gates = _mapping(sealed.get("gates")) or {}
    mean_gate = _finite(gates.get("development_mean_output_energy_ratio_maximum"))
    worst_gate = _finite(gates.get("development_worst_output_energy_ratio_maximum"))
    mean = _finite(exact.get("mean_output_energy_ratio"))
    worst = _finite(exact.get("worst_output_energy_ratio"))
    expected = sealed.get("development_case_count")
    exact_rescues = bool(
        all(value is True for value in guards.values())
        and mean is not None
        and worst is not None
        and mean_gate is not None
        and worst_gate is not None
        and mean <= mean_gate
        and worst <= worst_gate
        and isinstance(expected, int)
        and exact.get("case_count_below_zero_control") == expected
    )
    if any(value is not True for value in guards.values()):
        classification = "INVALID-ESTIMATION-DIAGNOSIS"
    elif exact_rescues:
        classification = "ESTIMATION-LAYER-CAUSE"
    else:
        classification = "ESTIMATION-NOT-DOMINANT"
    return {
        "schema_version": 1,
        "round": "R328",
        "question": "Q-0081",
        "created_utc": execution.get("created_utc"),
        "seal_sha256": execution.get("seal_sha256"),
        "execution_sha256": execution.get("execution_sha256"),
        "holdout_accessed": False,
        "cross_deleted_oracle_accessed": False,
        "parent_output_feedback": parent_summary,
        "exact_state": exact,
        "exact_state_rescues": exact_rescues,
        "validity_guards": guards,
        "classification": classification,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
