"""Formal admission and classification for the R326 solver-only repair.

The adapter supplies raw case rows, numerical-prefix comparisons, design
curvature, and dependency identity.  This probe recomputes every
conclusion-affecting gate and delegates the unchanged controller-performance
tree to the frozen R325 classifier.  It performs no file I/O and runs no
controller.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from probes.r325_constrained_horizon_validation import (
    analyse_r325_execution,
    development_allows_holdout,
)


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _phase_rows(execution: Mapping[str, object], arm: str, phase: str) -> Sequence[object]:
    arms = _mapping(execution.get("arms"))
    arm_value = None if arms is None else _mapping(arms.get(arm))
    phases = None if arm_value is None else _mapping(arm_value.get("rows"))
    return () if phases is None else _sequence(phases.get(phase))


def _solver_phase_summary(
    execution: Mapping[str, object],
    contract: Mapping[str, object],
    *,
    arm: str,
    phase: str,
    require_reference: bool,
) -> dict[str, object]:
    rows = _phase_rows(execution, arm, phase)
    expected_key = "development_case_count" if phase == "development" else "holdout_case_count"
    expected = contract.get(expected_key)
    solver = _mapping(contract.get("solver"))
    repair = _mapping(contract.get("solver_repair"))
    feasibility_tolerance = None if solver is None else _finite(solver.get("feasibility_tolerance"))
    normalized_limit = (
        None if repair is None else _finite(repair.get("maximum_normalized_residual_ratio"))
    )
    prefix_action_tolerance = (
        None if repair is None else _finite(repair.get("prefix_action_absolute_tolerance"))
    )
    prefix_output_tolerance = (
        None if repair is None else _finite(repair.get("prefix_output_absolute_tolerance"))
    )
    valid = bool(
        isinstance(expected, int)
        and not isinstance(expected, bool)
        and feasibility_tolerance is not None
        and normalized_limit is not None
        and (
            not require_reference
            or (prefix_action_tolerance is not None and prefix_output_tolerance is not None)
        )
        and len(rows) == expected
    )
    maximum_constraint_residual = 0.0
    maximum_primal_ratio = 0.0
    maximum_dual_ratio = 0.0
    maximum_prefix_error = 0.0
    compared_sample_count = 0
    solver_failure_count = 0
    execution_error_count = 0
    reference_mismatch_count = 0
    for item in rows:
        row = _mapping(item)
        if row is None:
            valid = False
            execution_error_count += 1
            continue
        solver_failed = row.get("solver_failed") is True
        execution_error = row.get("execution_error") is True
        solver_failure_count += int(solver_failed)
        execution_error_count += int(execution_error)
        residual = _finite(row.get("maximum_constraint_residual"))
        primal_ratio = _finite(row.get("maximum_primal_residual_ratio"))
        dual_ratio = _finite(row.get("maximum_dual_residual_ratio"))
        violations = row.get("constraint_violation_count")
        if residual is None or primal_ratio is None or dual_ratio is None:
            valid = False
        else:
            maximum_constraint_residual = max(maximum_constraint_residual, residual)
            maximum_primal_ratio = max(maximum_primal_ratio, primal_ratio)
            maximum_dual_ratio = max(maximum_dual_ratio, dual_ratio)
            valid = bool(
                valid
                and residual <= float(feasibility_tolerance)
                and primal_ratio <= float(normalized_limit)
                and dual_ratio <= float(normalized_limit)
            )
        valid = bool(
            valid
            and not solver_failed
            and not execution_error
            and isinstance(violations, int)
            and not isinstance(violations, bool)
            and violations == 0
        )
        if not require_reference:
            continue
        completed = row.get("reference_completed_steps")
        samples = _sequence(row.get("prefix_samples"))
        status_matches = row.get("reference_status_matches_r325") is True
        if (
            not isinstance(completed, int)
            or isinstance(completed, bool)
            or completed < 0
            or len(samples) != completed
            or not status_matches
        ):
            valid = False
            reference_mismatch_count += 1
            continue
        compared_sample_count += completed
        for index, sample_value in enumerate(samples):
            sample = _mapping(sample_value)
            if sample is None or sample.get("step") != index:
                valid = False
                continue
            for key in (
                "node_action_max_abs_error",
                "coordinate_action_max_abs_error",
                "predicted_output_max_abs_error",
            ):
                error = _finite(sample.get(key))
                if error is None:
                    valid = False
                else:
                    maximum_prefix_error = max(maximum_prefix_error, error)
                    tolerance = (
                        prefix_output_tolerance
                        if key == "predicted_output_max_abs_error"
                        else prefix_action_tolerance
                    )
                    valid = bool(valid and error <= float(tolerance))
    return {
        "valid": valid,
        "case_count": len(rows),
        "solver_failure_count": solver_failure_count,
        "execution_error_count": execution_error_count,
        "reference_mismatch_count": reference_mismatch_count,
        "compared_sample_count": compared_sample_count,
        "maximum_constraint_residual": maximum_constraint_residual,
        "maximum_primal_residual_ratio": maximum_primal_ratio,
        "maximum_dual_residual_ratio": maximum_dual_ratio,
        "maximum_prefix_absolute_error": maximum_prefix_error,
    }


def _design_summary(
    execution: Mapping[str, object], contract: Mapping[str, object]
) -> dict[str, object]:
    repair = _mapping(contract.get("solver_repair"))
    minimum = None if repair is None else _finite(repair.get("minimum_action_hessian_eigenvalue"))
    designs = _mapping(execution.get("designs"))
    values: list[float] = []
    valid = minimum is not None and designs is not None
    for arm in ("retained_cross", "cross_deleted"):
        arm_designs = None if designs is None else _mapping(designs.get(arm))
        if arm_designs is None or not arm_designs:
            valid = False
            continue
        for item in arm_designs.values():
            design = _mapping(item)
            eigenvalue = (
                None if design is None else _finite(design.get("minimum_action_hessian_eigenvalue"))
            )
            if eigenvalue is None:
                valid = False
            else:
                values.append(eigenvalue)
                valid = bool(valid and eigenvalue > float(minimum))
    return {
        "valid": valid,
        "design_count": len(values),
        "minimum_action_hessian_eigenvalue": min(values) if values else None,
    }


def _solver_repair_view(
    execution: Mapping[str, object], contract: Mapping[str, object]
) -> dict[str, object]:
    repair = _mapping(contract.get("solver_repair")) or {}
    development = {
        arm: _solver_phase_summary(
            execution,
            contract,
            arm=arm,
            phase="development",
            require_reference=True,
        )
        for arm in ("retained_cross", "cross_deleted")
    }
    holdout = None
    if execution.get("holdout_accessed") is True:
        holdout = {
            arm: _solver_phase_summary(
                execution,
                contract,
                arm=arm,
                phase="holdout",
                require_reference=False,
            )
            for arm in ("retained_cross", "cross_deleted")
        }
    design = _design_summary(execution, contract)
    identity = {
        "r325_contract_unchanged": bool(
            execution.get("r325_contract_payload_sha256")
            == repair.get("r325_contract_payload_sha256")
        ),
        "dependency_fingerprint": bool(
            execution.get("dependency_fingerprint") == repair.get("dependency_fingerprint")
        ),
        "solver_settings": bool(execution.get("solver_settings") == contract.get("solver")),
    }
    development_valid = bool(
        design["valid"] is True
        and all(summary["valid"] is True for summary in development.values())
    )
    holdout_valid = bool(
        holdout is not None and all(summary["valid"] is True for summary in holdout.values())
    )
    return {
        "identity": identity,
        "designs": design,
        "development": development,
        "development_valid": development_valid,
        "holdout": holdout,
        "holdout_valid": holdout_valid,
    }


def solver_development_allows_holdout(payload: object, contract: object) -> bool:
    """Require numerical equivalence and the unchanged development gates."""

    execution = _mapping(payload)
    sealed = _mapping(contract)
    if execution is None or sealed is None:
        return False
    repair = _solver_repair_view(execution, sealed)
    identity = _mapping(repair.get("identity")) or {}
    return bool(
        execution.get("sealed_source_identity") is True
        and execution.get("deterministic_execution_replay") is True
        and identity
        and all(value is True for value in identity.values())
        and repair.get("development_valid") is True
        and development_allows_holdout(execution, sealed)
    )


def classify_r326(payload: object, contract: object) -> str:
    """Apply the preregistered R326 classification tree."""

    analysis = _mapping(payload)
    sealed = _mapping(contract)
    if analysis is None or sealed is None:
        return "INVALID-SOLVER-REPAIR"
    guards = _mapping(analysis.get("validity_guards"))
    if guards is None or not guards or any(value is not True for value in guards.values()):
        return "INVALID-SOLVER-REPAIR"
    if analysis.get("solver_repair_passed") is not True:
        return "SOLVER-REPAIR-NO-GO"
    if (
        analysis.get("holdout_accessed") is True
        and analysis.get("holdout_solver_valid") is not True
    ):
        return "FRESH-HOLDOUT-NO-GO"
    controller = analysis.get("controller_classification")
    mapping = {
        "FORMULATION-INFEASIBLE": "SOLVER-REPAIR-NO-GO",
        "DEVELOPMENT-NO-GO": "DEVELOPMENT-NO-GO",
        "FRESH-HOLDOUT-NO-GO": "FRESH-HOLDOUT-NO-GO",
        "RETAINED-BLOCK-NO-VALUE": "RETAINED-BLOCK-NO-VALUE",
        "CONSTRAINED-HORIZON-PASS": "CONSTRAINED-HORIZON-PASS",
    }
    return mapping.get(controller, "INVALID-SOLVER-REPAIR")


def analyse_r326_execution(
    payload: object,
    contract: object,
    *,
    analysis_replay: bool,
) -> dict[str, object]:
    """Build formal R326 analysis from raw execution measurements."""

    execution = _mapping(payload) or {}
    sealed = _mapping(contract) or {}
    base = analyse_r325_execution(execution, sealed, analysis_replay=analysis_replay)
    repair = _solver_repair_view(execution, sealed)
    identity = _mapping(repair.get("identity")) or {}
    base_guards = _mapping(base.get("validity_guards")) or {}
    validity_guards = {
        "sealed_source_identity": base_guards.get("sealed_source_identity") is True,
        "no_r321_outcome_access": base_guards.get("no_r321_outcome_access") is True,
        "comparison_contract": base_guards.get("comparison_contract") is True,
        "case_contract": base_guards.get("case_contract") is True,
        "trace_integrity": base_guards.get("trace_integrity") is True,
        "deterministic_execution_replay": (
            base_guards.get("deterministic_execution_replay") is True
        ),
        "deterministic_analysis_replay": analysis_replay,
        "r325_contract_unchanged": identity.get("r325_contract_unchanged") is True,
        "dependency_fingerprint": identity.get("dependency_fingerprint") is True,
        "solver_settings": identity.get("solver_settings") is True,
    }
    analysis: dict[str, object] = {
        "schema_version": 1,
        "round": "R326",
        "question": "Q-0080",
        "created_utc": execution.get("created_utc"),
        "seal_sha256": execution.get("seal_sha256"),
        "execution_sha256": execution.get("execution_sha256"),
        "holdout_accessed": execution.get("holdout_accessed") is True,
        "arms": base.get("arms"),
        "solver_repair": repair,
        "solver_repair_passed": bool(
            repair.get("development_valid") is True
            and identity
            and all(value is True for value in identity.values())
        ),
        "holdout_solver_valid": repair.get("holdout_valid") is True,
        "controller_classification": base.get("classification"),
        "validity_guards": validity_guards,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    analysis["classification"] = classify_r326(analysis, sealed)
    return analysis
