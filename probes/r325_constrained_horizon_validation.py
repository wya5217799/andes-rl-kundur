"""Formal analysis and classifier for the frozen R325 controller contract.

Usage: pass raw adapter measurements plus the sealed contract to
``development_allows_holdout`` or ``analyse_r325_execution``. This probe owns
all conclusion-affecting screening, admission, and classification logic; it
performs no file I/O and runs no controller.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _rows(arm: Mapping[str, object], phase: str) -> Sequence[object]:
    phases = _mapping(arm.get("rows"))
    value = None if phases is None else phases.get(phase)
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _expected_count(contract: Mapping[str, object], phase: str) -> int | None:
    key = "development_case_count" if phase == "development" else "holdout_case_count"
    value = contract.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _phase_summary(
    arm: Mapping[str, object],
    phase: str,
    contract: Mapping[str, object],
) -> dict[str, object]:
    values = _rows(arm, phase)
    expected = _expected_count(contract, phase)
    solver = _mapping(contract.get("solver"))
    tolerance = None if solver is None else _finite(solver.get("feasibility_tolerance"))
    ratios: list[float] = []
    valid = expected is not None and tolerance is not None and len(values) == expected
    solver_failure_count = 0
    execution_error_count = 0
    constraint_violation_count = 0
    maximum_residual = 0.0
    maximum_iterations = 0
    for item in values:
        row = _mapping(item)
        if row is None:
            valid = False
            execution_error_count += 1
            continue
        solver_failed = row.get("solver_failed") is True
        execution_error = row.get("execution_error") is True
        solver_failure_count += int(solver_failed)
        execution_error_count += int(execution_error)
        violations = row.get("constraint_violation_count")
        if not isinstance(violations, int) or isinstance(violations, bool):
            valid = False
        else:
            constraint_violation_count += violations
            valid = valid and violations == 0
        residual = _finite(row.get("maximum_constraint_residual"))
        ratio = _finite(row.get("output_energy_ratio"))
        iterations = row.get("maximum_solver_iterations")
        if residual is None or ratio is None:
            valid = False
        else:
            maximum_residual = max(maximum_residual, residual)
            ratios.append(ratio)
            valid = valid and residual <= tolerance
        if not isinstance(iterations, int) or isinstance(iterations, bool):
            valid = False
        else:
            maximum_iterations = max(maximum_iterations, iterations)
        valid = valid and not solver_failed and not execution_error
    return {
        "valid": bool(valid and len(ratios) == len(values)),
        "case_count": len(values),
        "mean_output_energy_ratio": float(np.mean(ratios)) if ratios else None,
        "worst_output_energy_ratio": float(np.max(ratios)) if ratios else None,
        "solver_failure_count": solver_failure_count,
        "execution_error_count": execution_error_count,
        "constraint_violation_count": constraint_violation_count,
        "maximum_constraint_residual": maximum_residual,
        "maximum_solver_iterations": maximum_iterations,
    }


def _arms_view(
    execution: Mapping[str, object],
    contract: Mapping[str, object],
) -> dict[str, dict[str, object]] | None:
    raw_arms = _mapping(execution.get("arms"))
    if raw_arms is None:
        return None
    result: dict[str, dict[str, object]] = {}
    for name in ("retained_cross", "cross_deleted"):
        raw_arm = _mapping(raw_arms.get(name))
        if raw_arm is None:
            return None
        development = _phase_summary(raw_arm, "development", contract)
        formulation_feasible = bool(
            raw_arm.get("observer_synthesis_succeeded") is True
            and development["case_count"] == contract.get("development_case_count")
            and development["solver_failure_count"] == 0
        )
        arm: dict[str, object] = {
            "formulation_feasible": formulation_feasible,
            "observer_synthesis_error": raw_arm.get("observer_synthesis_error"),
            "development": development,
        }
        if execution.get("holdout_accessed") is True:
            arm["holdout"] = _phase_summary(raw_arm, "holdout", contract)
        result[name] = arm
    return result


def _gates(contract: Mapping[str, object]) -> Mapping[str, object] | None:
    gates = _mapping(contract.get("gates"))
    required = {
        "development_mean_output_energy_ratio_maximum",
        "development_worst_output_energy_ratio_maximum",
        "holdout_mean_output_energy_ratio_maximum",
        "holdout_worst_output_energy_ratio_maximum",
        "retained_to_deleted_mean_ratio_maximum",
    }
    if gates is None or any(_finite(gates.get(name)) is None for name in required):
        return None
    return gates


def development_allows_holdout(payload: object, contract: object) -> bool:
    """Return the frozen development admission decision from raw rows."""

    execution = _mapping(payload)
    sealed = _mapping(contract)
    if execution is None or sealed is None:
        return False
    arms = _arms_view(execution, sealed)
    gates = _gates(sealed)
    comparison = _mapping(sealed.get("comparison_identifiability"))
    if arms is None or gates is None or comparison is None:
        return False
    retained = arms["retained_cross"]
    deleted = arms["cross_deleted"]
    retained_development = _mapping(retained.get("development"))
    deleted_development = _mapping(deleted.get("development"))
    if retained_development is None or deleted_development is None:
        return False
    mean = _finite(retained_development.get("mean_output_energy_ratio"))
    worst = _finite(retained_development.get("worst_output_energy_ratio"))
    return bool(
        execution.get("r321_analysis_access") == "HASH-ONLY-NO-PARSE"
        and comparison.get("decision") == "ALLOW"
        and sealed.get("tuning_candidate_count") == 0
        and retained.get("formulation_feasible") is True
        and deleted.get("formulation_feasible") is True
        and retained_development.get("valid") is True
        and deleted_development.get("valid") is True
        and mean is not None
        and worst is not None
        and mean <= float(gates["development_mean_output_energy_ratio_maximum"])
        and worst <= float(gates["development_worst_output_energy_ratio_maximum"])
    )


def classify_r325(payload: object, contract: object) -> str:
    """Apply the preregistered R325 classification tree."""

    root = _mapping(payload)
    sealed = _mapping(contract)
    if root is None or sealed is None or _gates(sealed) is None:
        return "INVALID-CONSTRAINED-HORIZON"
    guards = _mapping(root.get("validity_guards"))
    arms = _mapping(root.get("arms"))
    if (
        guards is None
        or not guards
        or any(value is not True for value in guards.values())
        or arms is None
    ):
        return "INVALID-CONSTRAINED-HORIZON"
    retained = _mapping(arms.get("retained_cross"))
    deleted = _mapping(arms.get("cross_deleted"))
    if retained is None or deleted is None:
        return "INVALID-CONSTRAINED-HORIZON"
    if (
        retained.get("formulation_feasible") is not True
        or deleted.get("formulation_feasible") is not True
    ):
        return "FORMULATION-INFEASIBLE"

    retained_development = _mapping(retained.get("development"))
    deleted_development = _mapping(deleted.get("development"))
    gates = _gates(sealed)
    assert gates is not None
    if retained_development is None or deleted_development is None:
        return "INVALID-CONSTRAINED-HORIZON"
    development_mean = _finite(retained_development.get("mean_output_energy_ratio"))
    development_worst = _finite(retained_development.get("worst_output_energy_ratio"))
    if (
        retained_development.get("valid") is not True
        or deleted_development.get("valid") is not True
        or development_mean is None
        or development_worst is None
        or development_mean
        > float(gates["development_mean_output_energy_ratio_maximum"])
        or development_worst
        > float(gates["development_worst_output_energy_ratio_maximum"])
    ):
        return "DEVELOPMENT-NO-GO"

    if root.get("holdout_accessed") is not True:
        return "INVALID-CONSTRAINED-HORIZON"
    retained_holdout = _mapping(retained.get("holdout"))
    deleted_holdout = _mapping(deleted.get("holdout"))
    if retained_holdout is None or deleted_holdout is None:
        return "INVALID-CONSTRAINED-HORIZON"
    retained_mean = _finite(retained_holdout.get("mean_output_energy_ratio"))
    retained_worst = _finite(retained_holdout.get("worst_output_energy_ratio"))
    deleted_mean = _finite(deleted_holdout.get("mean_output_energy_ratio"))
    deleted_worst = _finite(deleted_holdout.get("worst_output_energy_ratio"))
    if (
        retained_holdout.get("valid") is not True
        or deleted_holdout.get("valid") is not True
        or retained_mean is None
        or retained_worst is None
        or deleted_mean is None
        or deleted_worst is None
        or retained_mean > float(gates["holdout_mean_output_energy_ratio_maximum"])
        or retained_worst > float(gates["holdout_worst_output_energy_ratio_maximum"])
    ):
        return "FRESH-HOLDOUT-NO-GO"
    if (
        retained_mean
        > float(gates["retained_to_deleted_mean_ratio_maximum"]) * deleted_mean
        or retained_worst > deleted_worst
    ):
        return "RETAINED-BLOCK-NO-VALUE"
    return "CONSTRAINED-HORIZON-PASS"


def analyse_r325_execution(
    payload: object,
    contract: object,
    *,
    analysis_replay: bool,
) -> dict[str, object]:
    """Build the formal analysis from raw execution measurements."""

    execution = _mapping(payload)
    sealed = _mapping(contract)
    if execution is None or sealed is None:
        execution = {}
        sealed = {}
    arms = _arms_view(execution, sealed)
    raw_arms = _mapping(execution.get("arms"))
    comparison = _mapping(sealed.get("comparison_identifiability"))
    holdout_accessed = execution.get("holdout_accessed") is True
    case_contract = arms is not None and raw_arms is not None
    trace_integrity = arms is not None and raw_arms is not None
    if arms is not None and raw_arms is not None:
        for name in ("retained_cross", "cross_deleted"):
            raw_arm = _mapping(raw_arms.get(name))
            if raw_arm is None:
                case_contract = False
                trace_integrity = False
                continue
            development = _rows(raw_arm, "development")
            case_contract = case_contract and len(development) == sealed.get(
                "development_case_count"
            )
            trace_integrity = trace_integrity and all(
                _mapping(row) is not None
                and _mapping(row).get("execution_error") is not True  # type: ignore[union-attr]
                for row in development
            )
            holdout = _rows(raw_arm, "holdout")
            if holdout_accessed:
                case_contract = case_contract and len(holdout) == sealed.get(
                    "holdout_case_count"
                )
                trace_integrity = trace_integrity and all(
                    _mapping(row) is not None
                    and _mapping(row).get("execution_error") is not True  # type: ignore[union-attr]
                    for row in holdout
                )
            else:
                case_contract = case_contract and len(holdout) == 0
    analysis: dict[str, object] = {
        "schema_version": 1,
        "round": "R325",
        "question": "Q-0078",
        "created_utc": execution.get("created_utc"),
        "seal_sha256": execution.get("seal_sha256"),
        "execution_sha256": execution.get("execution_sha256"),
        "holdout_accessed": holdout_accessed,
        "arms": arms,
        "validity_guards": {
            "sealed_source_identity": bool(
                execution.get("sealed_source_identity") is True
            ),
            "no_r321_outcome_access": bool(
                execution.get("r321_analysis_access") == "HASH-ONLY-NO-PARSE"
                and sealed.get("r321_analysis_access") == "HASH-ONLY-NO-PARSE"
            ),
            "comparison_contract": bool(
                comparison is not None
                and comparison.get("decision") == "ALLOW"
                and sealed.get("tuning_candidate_count") == 0
            ),
            "case_contract": bool(case_contract),
            "trace_integrity": bool(trace_integrity),
            "deterministic_execution_replay": bool(
                execution.get("deterministic_execution_replay") is True
            ),
            "deterministic_analysis_replay": bool(analysis_replay),
        },
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    analysis["classification"] = classify_r325(analysis, sealed)
    return analysis
