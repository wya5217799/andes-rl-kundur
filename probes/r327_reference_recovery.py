"""Pure admission logic for the R327 legacy-reference recovery amendment.

R327 does not rerun the candidate controller.  It replaces only the eight
failed legacy-prefix fields in an immutable R326 execution view, then delegates
the unchanged solver and controller gates to the sealed R326 decision logic.
This module performs no file I/O and starts no processes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

import numpy as np
from probes.r326_solver_adequacy import (
    analyse_r326_execution,
    solver_development_allows_holdout,
)

REFERENCE_FIELDS = (
    "reference_completed_steps",
    "reference_target_steps",
    "reference_failure_kind",
    "reference_failure_step",
    "reference_failure_message",
    "reference_status_matches_r325",
    "prefix_samples",
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


def _key(value: Mapping[str, object]) -> tuple[str, str, str] | None:
    parts = (value.get("arm"), value.get("case"), value.get("mismatch"))
    return parts if all(isinstance(item, str) and item for item in parts) else None  # type: ignore[return-value]


def _expected_keys(contract: Mapping[str, object]) -> tuple[tuple[str, str, str], ...]:
    recovery = _mapping(contract.get("reference_recovery")) or {}
    result: list[tuple[str, str, str]] = []
    for item in _sequence(recovery.get("expected_keys")):
        parts = _sequence(item)
        if len(parts) != 3 or not all(isinstance(part, str) and part for part in parts):
            return ()
        result.append((str(parts[0]), str(parts[1]), str(parts[2])))
    return tuple(result)


def _parent_rows(execution: Mapping[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    arms = _mapping(execution.get("arms")) or {}
    for arm in ("retained_cross", "cross_deleted"):
        arm_value = _mapping(arms.get(arm)) or {}
        phases = _mapping(arm_value.get("rows")) or {}
        for item in _sequence(phases.get("development")):
            if isinstance(item, dict):
                result.append(item)
    return result


def _recovery_summary(
    execution: Mapping[str, object], contract: Mapping[str, object]
) -> dict[str, object]:
    expected = _expected_keys(contract)
    rows = _sequence(execution.get("rows"))
    recovery = _mapping(contract.get("reference_recovery")) or {}
    action_tolerance = _finite(recovery.get("prefix_action_absolute_tolerance"))
    output_tolerance = _finite(recovery.get("prefix_output_absolute_tolerance"))
    inventory_valid = bool(expected and len(set(expected)) == len(expected))
    by_key: dict[tuple[str, str, str], Mapping[str, object]] = {}
    duplicate = False
    for item in rows:
        row = _mapping(item)
        key = None if row is None else _key(row)
        if row is None or key is None or key in by_key:
            duplicate = True
            continue
        by_key[key] = row
    exact_inventory = bool(inventory_valid and not duplicate and set(by_key) == set(expected))
    valid = bool(exact_inventory and action_tolerance is not None and output_tolerance is not None)
    sample_count = 0
    maximum_node_error = 0.0
    maximum_coordinate_error = 0.0
    maximum_output_error = 0.0
    incomplete_count = 0
    for key in expected:
        row = by_key.get(key)
        if row is None:
            continue
        target = row.get("reference_target_steps")
        completed = row.get("reference_completed_steps")
        samples = _sequence(row.get("prefix_samples"))
        complete = bool(
            isinstance(target, int)
            and not isinstance(target, bool)
            and target > 0
            and completed == target
            and len(samples) == target
            and row.get("reference_status_matches_r325") is True
            and row.get("reference_failure_kind") in (None, "")
            and row.get("reference_failure_step") is None
            and row.get("reference_failure_message") in (None, "")
        )
        if not complete:
            valid = False
            incomplete_count += 1
            continue
        sample_count += len(samples)
        for index, item in enumerate(samples):
            sample = _mapping(item)
            if sample is None or sample.get("step") != index:
                valid = False
                continue
            node = _finite(sample.get("node_action_max_abs_error"))
            coordinate = _finite(sample.get("coordinate_action_max_abs_error"))
            output = _finite(sample.get("predicted_output_max_abs_error"))
            if node is None or coordinate is None or output is None:
                valid = False
                continue
            maximum_node_error = max(maximum_node_error, node)
            maximum_coordinate_error = max(maximum_coordinate_error, coordinate)
            maximum_output_error = max(maximum_output_error, output)
            valid = bool(
                valid
                and node <= float(action_tolerance)
                and coordinate <= float(action_tolerance)
                and output <= float(output_tolerance)
            )
    return {
        "valid": valid,
        "exact_inventory": exact_inventory,
        "expected_case_count": len(expected),
        "recovered_case_count": len(by_key),
        "incomplete_count": incomplete_count,
        "sample_count": sample_count,
        "maximum_node_action_absolute_error": maximum_node_error,
        "maximum_coordinate_action_absolute_error": maximum_coordinate_error,
        "maximum_predicted_output_absolute_error": maximum_output_error,
    }


def _combined_execution(
    parent: Mapping[str, object],
    recovery_execution: Mapping[str, object],
    recovery_contract: Mapping[str, object],
) -> tuple[dict[str, object], bool]:
    combined = deepcopy(dict(parent))
    parent_rows = _parent_rows(combined)
    expected = set(_expected_keys(recovery_contract))
    original_missing = {
        key
        for row in parent_rows
        if (key := _key(row)) is not None and row.get("reference_status_matches_r325") is not True
    }
    recovery_rows = {
        key: row
        for item in _sequence(recovery_execution.get("rows"))
        if (row := _mapping(item)) is not None and (key := _key(row)) is not None
    }
    exact_parent_inventory = bool(original_missing == expected)
    for row in parent_rows:
        key = _key(row)
        replacement = None if key is None else recovery_rows.get(key)
        if replacement is None:
            continue
        for field in REFERENCE_FIELDS:
            row[field] = deepcopy(replacement.get(field))
    combined["holdout_accessed"] = False
    return combined, exact_parent_inventory


def analyse_r327_recovery(
    recovery_payload: object,
    recovery_contract: object,
    r326_payload: object,
    r326_contract: object,
    *,
    analysis_replay: bool,
) -> dict[str, object]:
    """Validate the amendment and reapply the immutable R326 gate ordering."""

    recovery_execution = _mapping(recovery_payload) or {}
    sealed_recovery = _mapping(recovery_contract) or {}
    parent_execution = _mapping(r326_payload) or {}
    sealed_parent = _mapping(r326_contract) or {}
    summary = _recovery_summary(recovery_execution, sealed_recovery)
    combined, exact_parent_inventory = _combined_execution(
        parent_execution, recovery_execution, sealed_recovery
    )
    combined_analysis = analyse_r326_execution(
        combined, sealed_parent, analysis_replay=analysis_replay
    )
    combined_guards = _mapping(combined_analysis.get("validity_guards")) or {}
    structural_guards = {
        "sealed_source_identity": recovery_execution.get("sealed_source_identity") is True,
        "parent_identity": recovery_execution.get("parent_identity") is True,
        "holdout_protected": recovery_execution.get("holdout_accessed") is False,
        "deterministic_reference_replay": (
            recovery_execution.get("deterministic_reference_replay") is True
        ),
        "exact_recovery_inventory": summary.get("exact_inventory") is True,
        "exact_parent_missing_inventory": exact_parent_inventory,
        "combined_r326_validity": bool(
            combined_guards and all(value is True for value in combined_guards.values())
        ),
        "deterministic_analysis_replay": analysis_replay,
    }
    reference_passed = bool(
        all(value is True for value in structural_guards.values()) and summary.get("valid") is True
    )
    combined_solver_passed = bool(
        reference_passed and combined_analysis.get("solver_repair_passed") is True
    )
    invalid = any(
        structural_guards[key] is not True
        for key in (
            "sealed_source_identity",
            "parent_identity",
            "holdout_protected",
            "deterministic_reference_replay",
            "exact_recovery_inventory",
            "exact_parent_missing_inventory",
            "combined_r326_validity",
            "deterministic_analysis_replay",
        )
    )
    if invalid:
        classification = "INVALID-REFERENCE-RECOVERY"
    elif not reference_passed or not combined_solver_passed:
        classification = "REFERENCE-RECOVERY-NO-GO"
    elif solver_development_allows_holdout(combined, sealed_parent):
        classification = "DEVELOPMENT-ADMISSION-PASS-HOLDOUT-SEALED"
    else:
        classification = "DEVELOPMENT-NO-GO"
    return {
        "schema_version": 1,
        "round": "R327",
        "question": "Q-0080",
        "created_utc": recovery_execution.get("created_utc"),
        "seal_sha256": recovery_execution.get("seal_sha256"),
        "execution_sha256": recovery_execution.get("execution_sha256"),
        "holdout_accessed": False,
        "reference_recovery": summary,
        "reference_recovery_passed": reference_passed,
        "combined_solver_repair": combined_analysis.get("solver_repair"),
        "combined_solver_repair_passed": combined_solver_passed,
        "arms": combined_analysis.get("arms") if combined_solver_passed else None,
        "validity_guards": structural_guards,
        "classification": classification,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
