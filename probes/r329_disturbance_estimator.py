"""Pure classifier for the R329 fixed disturbance-aware estimator."""

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


def _design_summary(
    payload: Mapping[str, object], contract: Mapping[str, object]
) -> tuple[dict[str, object], bool]:
    records = _mapping(payload.get("designs")) or {}
    expected_points = _sequence(contract.get("points"))
    estimator = _mapping(contract.get("estimator")) or {}
    expected_order = estimator.get("augmented_order")
    maximum_residual = _finite(estimator.get("maximum_normalized_covariance_residual"))
    maximum_radius = _finite(estimator.get("maximum_error_pole_radius"))
    valid = bool(
        expected_points
        and set(records) == set(expected_points)
        and isinstance(expected_order, int)
        and not isinstance(expected_order, bool)
        and maximum_residual is not None
        and maximum_radius is not None
    )
    worst_residual = 0.0
    worst_radius = 0.0
    minimum_rank: int | None = None
    for point in expected_points:
        record = _mapping(records.get(point)) or {}
        order = record.get("augmented_order")
        rank = record.get("observability_rank")
        residual = _finite(record.get("normalized_covariance_residual"))
        radius = _finite(record.get("error_pole_radius"))
        point_valid = bool(
            order == expected_order
            and rank == expected_order
            and record.get("finite") is True
            and record.get("covariance_positive_semidefinite") is True
            and residual is not None
            and radius is not None
            and residual <= maximum_residual
            and radius < maximum_radius
        )
        valid = valid and point_valid
        if residual is not None:
            worst_residual = max(worst_residual, residual)
        if radius is not None:
            worst_radius = max(worst_radius, radius)
        if isinstance(rank, int) and not isinstance(rank, bool):
            minimum_rank = rank if minimum_rank is None else min(minimum_rank, rank)
    return {
        "valid": bool(valid),
        "point_count": len(records),
        "minimum_observability_rank": minimum_rank,
        "maximum_normalized_covariance_residual": worst_residual,
        "maximum_error_pole_radius": worst_radius,
    }, bool(valid)


def _row_summary(
    payload: Mapping[str, object], contract: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, object], bool]:
    rows = _sequence(payload.get("rows"))
    expected = contract.get("development_case_count")
    estimator = _mapping(contract.get("estimator")) or {}
    maximum_constraint = _finite(estimator.get("maximum_constraint_residual"))
    maximum_normalized = _finite(estimator.get("maximum_normalized_solver_residual_ratio"))
    valid = bool(
        isinstance(expected, int)
        and not isinstance(expected, bool)
        and len(rows) == expected
        and maximum_constraint is not None
        and maximum_normalized is not None
    )
    cases: set[str] = set()
    ratios: list[float] = []
    estimator_error = 0.0
    parent_error = 0.0
    solver_failures = 0
    execution_errors = 0
    violations = 0
    maximum_constraint_seen = 0.0
    maximum_primal_ratio = 0.0
    maximum_dual_ratio = 0.0
    for item in rows:
        row = _mapping(item)
        if row is None:
            valid = False
            execution_errors += 1
            continue
        case = row.get("case")
        if (
            row.get("arm") != "retained_cross"
            or row.get("phase") != "development"
            or not isinstance(case, str)
            or not case
            or case in cases
        ):
            valid = False
        else:
            cases.add(case)
        solver_failed = row.get("solver_failed") is True
        execution_error = row.get("execution_error") is True
        solver_failures += int(solver_failed)
        execution_errors += int(execution_error)
        count = row.get("constraint_violation_count")
        constraint = _finite(row.get("maximum_constraint_residual"))
        primal = _finite(row.get("maximum_primal_residual_ratio"))
        dual = _finite(row.get("maximum_dual_residual_ratio"))
        ratio = _finite(row.get("output_energy_ratio"))
        estimate_error = _finite(row.get("state_estimation_squared_error"))
        old_error = _finite(row.get("parent_state_estimation_squared_error"))
        if any(
            value is None for value in (constraint, primal, dual, ratio, estimate_error, old_error)
        ):
            valid = False
            continue
        valid = bool(
            valid
            and not solver_failed
            and not execution_error
            and isinstance(count, int)
            and not isinstance(count, bool)
            and count == 0
            and row.get("parent_output_identity") is True
            and constraint <= maximum_constraint
            and primal <= maximum_normalized
            and dual <= maximum_normalized
            and estimate_error >= 0.0
            and old_error >= 0.0
        )
        ratios.append(ratio)
        estimator_error += estimate_error
        parent_error += old_error
        maximum_constraint_seen = max(maximum_constraint_seen, constraint)
        maximum_primal_ratio = max(maximum_primal_ratio, primal)
        maximum_dual_ratio = max(maximum_dual_ratio, dual)
        if isinstance(count, int) and not isinstance(count, bool):
            violations += count
    improved = bool(valid and estimator_error < parent_error)
    controller = {
        "valid": bool(valid),
        "case_count": len(rows),
        "mean_output_energy_ratio": float(np.mean(ratios)) if ratios else None,
        "worst_output_energy_ratio": max(ratios) if ratios else None,
        "case_count_below_zero_control": sum(value < 1.0 for value in ratios),
        "solver_failure_count": solver_failures,
        "execution_error_count": execution_errors,
        "constraint_violation_count": violations,
        "maximum_constraint_residual": maximum_constraint_seen,
        "maximum_primal_residual_ratio": maximum_primal_ratio,
        "maximum_dual_residual_ratio": maximum_dual_ratio,
    }
    state_estimation = {
        "new_total_squared_error": estimator_error,
        "parent_total_squared_error": parent_error,
        "new_to_parent_squared_error_ratio": (
            estimator_error / parent_error if parent_error > 0.0 else None
        ),
        "improved": improved,
    }
    return controller, state_estimation, bool(valid)


def analyse_r329_estimator(
    payload: object,
    contract: object,
    *,
    analysis_replay: bool,
) -> dict[str, object]:
    """Classify the fixed estimator's structural and development admission."""

    execution = _mapping(payload) or {}
    sealed = _mapping(contract) or {}
    designs, designs_valid = _design_summary(execution, sealed)
    controller, state_estimation, rows_valid = _row_summary(execution, sealed)
    guards = {
        "sealed_source_identity": execution.get("sealed_source_identity") is True,
        "parent_identity": execution.get("parent_identity") is True,
        "oracle_identity": execution.get("oracle_identity") is True,
        "estimator_information_boundary": (execution.get("estimator_information_boundary") is True),
        "deterministic_execution_replay": (execution.get("deterministic_execution_replay") is True),
        "holdout_protected": execution.get("holdout_accessed") is False,
        "parent_output_feedback_valid_failed": (
            execution.get("parent_output_feedback_valid_failed") is True
        ),
        "estimator_designs_valid": designs_valid,
        "development_rows_valid": rows_valid,
        "deterministic_analysis_replay": analysis_replay,
    }
    gates = _mapping(sealed.get("gates")) or {}
    mean_gate = _finite(gates.get("development_mean_output_energy_ratio_maximum"))
    worst_gate = _finite(gates.get("development_worst_output_energy_ratio_maximum"))
    mean = _finite(controller.get("mean_output_energy_ratio"))
    worst = _finite(controller.get("worst_output_energy_ratio"))
    expected = sealed.get("development_case_count")
    passes = bool(
        all(value is True for value in guards.values())
        and state_estimation.get("improved") is True
        and mean is not None
        and worst is not None
        and mean_gate is not None
        and worst_gate is not None
        and mean <= mean_gate
        and worst <= worst_gate
        and isinstance(expected, int)
        and controller.get("case_count_below_zero_control") == expected
    )
    if any(value is not True for value in guards.values()):
        classification = "INVALID-AUGMENTED-ESTIMATOR"
    elif passes:
        classification = "AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS"
    else:
        classification = "AUGMENTED-ESTIMATOR-NO-GO"
    return {
        "schema_version": 1,
        "round": "R329",
        "question": "Q-0082",
        "created_utc": execution.get("created_utc"),
        "seal_sha256": execution.get("seal_sha256"),
        "execution_sha256": execution.get("execution_sha256"),
        "holdout_accessed": False,
        "designs": designs,
        "controller": controller,
        "state_estimation": state_estimation,
        "validity_guards": guards,
        "classification": classification,
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
