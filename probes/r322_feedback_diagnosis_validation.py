"""Formal classifier for the R322 development-only feedback diagnosis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


EXPECTED_VALIDITY_GUARDS = {
    "sealed_source_identity",
    "parent_hash_only",
    "exact_design_contract",
    "matrix_contract",
    "development_only_contract",
    "decomposition_identity",
    "deterministic_replay",
    "case_contract",
    "common_scale_contract",
    "comparison_contract",
    "eval_not_run",
    "no_physical_execution",
}
EXPECTED_ARMS = {"retained_cross", "cross_deleted"}
EXPECTED_POINTS = {"HS0", "HS1"}
EXPECTED_CASE_COUNT = 32
ABSOLUTE_FLOOR = 0.98
OBSERVER_RESCUE_FRACTION = 0.50
AUTHORITY_OVERDRIVE = 2.0
MAXIMUM_ERROR_COMMAND_FRACTION = 0.50
MAXIMUM_POLE_RADIUS = 0.995
MINIMUM_IMPROVEMENT = 0.02


def _invalid(payload: Mapping[str, object], reason: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": payload.get("round"),
        "question": payload.get("question"),
        "classification": "INVALID-DEVELOPMENT-DIAGNOSIS",
        "invalid_reason": reason,
        "fresh_holdout_eligible": False,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
    }


def _finite_nonnegative(values: object, count: int, *, name: str) -> np.ndarray:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} is missing")
    array = np.asarray(values, dtype=float)
    if array.shape != (count,) or not np.all(np.isfinite(array)) or np.any(array < 0):
        raise ValueError(f"{name} violates the case contract")
    return array


def _original_arm(value: Mapping[str, object], *, name: str) -> dict[str, Any]:
    if int(value.get("case_count", -1)) != EXPECTED_CASE_COUNT:
        raise ValueError(f"{name} original case count drift")
    if value.get("finite") is not True:
        raise ValueError(f"{name} original diagnosis is non-finite")
    if int(value.get("constraint_violation_count", -1)) != 0:
        raise ValueError(f"{name} original diagnosis has a constraint violation")
    return {
        "case_count": EXPECTED_CASE_COUNT,
        "finite": True,
        "constraint_violation_count": 0,
        "observer_energy_ratios_to_zero": _finite_nonnegative(
            value.get("observer_energy_ratios_to_zero"),
            EXPECTED_CASE_COUNT,
            name=f"{name} observer energy",
        ).tolist(),
        "exact_state_energy_ratios_to_zero": _finite_nonnegative(
            value.get("exact_state_energy_ratios_to_zero"),
            EXPECTED_CASE_COUNT,
            name=f"{name} exact-state energy",
        ).tolist(),
        "true_state_overdrive_ratios": _finite_nonnegative(
            value.get("true_state_overdrive_ratios"),
            EXPECTED_CASE_COUNT,
            name=f"{name} true-state overdrive",
        ).tolist(),
        "estimation_error_command_norm_ratios": _finite_nonnegative(
            value.get("estimation_error_command_norm_ratios"),
            EXPECTED_CASE_COUNT,
            name=f"{name} estimation-error command",
        ).tolist(),
    }


def identify_mechanism(original_arms: Mapping[str, Mapping[str, object]]) -> str:
    """Apply the prospective dominance signatures to normalized arm summaries."""

    observer_signatures: list[bool] = []
    authority_signatures: list[bool] = []
    for arm in EXPECTED_ARMS:
        value = original_arms[arm]
        observer = np.asarray(value["observer_energy_ratios_to_zero"], dtype=float)
        exact = np.asarray(value["exact_state_energy_ratios_to_zero"], dtype=float)
        overdrive = np.asarray(value["true_state_overdrive_ratios"], dtype=float)
        error_fraction = np.asarray(
            value["estimation_error_command_norm_ratios"], dtype=float
        )
        rescue = 1.0 - float(np.mean(exact)) / max(
            float(np.mean(observer)), np.finfo(float).tiny
        )
        observer_signatures.append(
            bool(np.max(exact) <= ABSOLUTE_FLOOR and rescue >= OBSERVER_RESCUE_FRACTION)
        )
        authority_signatures.append(
            bool(
                np.min(exact) > ABSOLUTE_FLOOR
                and np.min(overdrive) >= AUTHORITY_OVERDRIVE
                and float(np.median(error_fraction))
                <= MAXIMUM_ERROR_COMMAND_FRACTION
            )
        )
    observer_dominant = all(observer_signatures)
    authority_dominant = all(authority_signatures)
    if observer_dominant and not authority_dominant:
        return "OBSERVER-TRANSIENT-DOMINANT"
    if authority_dominant and not observer_dominant:
        return "GAIN-AUTHORITY-DOMINANT"
    return "MIXED-MECHANISM"


def _repair_arm(value: Mapping[str, object], *, name: str) -> dict[str, Any]:
    if int(value.get("case_count", -1)) != EXPECTED_CASE_COUNT:
        raise ValueError(f"{name} repair case count drift")
    points = value.get("point_designs")
    if not isinstance(points, Mapping) or set(points) != EXPECTED_POINTS:
        raise ValueError(f"{name} repair point-design contract mismatch")
    designs: dict[str, dict[str, float]] = {}
    for point, row in points.items():
        if not isinstance(row, Mapping):
            raise ValueError(f"{name} repair point design is not an object")
        controller = float(row.get("controller_pole_radius", float("nan")))
        observer = float(row.get("observer_pole_radius", float("nan")))
        if not np.isfinite(controller) or not np.isfinite(observer):
            raise ValueError(f"{name} repair pole metric is non-finite")
        designs[str(point)] = {
            "controller_pole_radius": controller,
            "observer_pole_radius": observer,
        }
    ratios = _finite_nonnegative(
        value.get("energy_ratios_to_zero"),
        EXPECTED_CASE_COUNT,
        name=f"{name} repair energy",
    )
    return {
        "case_count": EXPECTED_CASE_COUNT,
        "finite": value.get("finite") is True,
        "constraint_violation_count": int(
            value.get("constraint_violation_count", -1)
        ),
        "point_designs": designs,
        "maximum_controller_pole_radius": max(
            row["controller_pole_radius"] for row in designs.values()
        ),
        "maximum_observer_pole_radius": max(
            row["observer_pole_radius"] for row in designs.values()
        ),
        "energy_ratios_to_zero": ratios.tolist(),
    }


def evaluate_feedback_diagnosis(payload: object) -> dict[str, Any]:
    """Classify one immutable R322 development-only diagnosis and repair."""

    if not isinstance(payload, Mapping):
        return _invalid({}, "payload is not an object")
    if payload.get("round") != "R322" or payload.get("question") != "Q-0077":
        return _invalid(payload, "round or question identity mismatch")
    validity = payload.get("validity_guards")
    if not isinstance(validity, Mapping) or set(validity) != EXPECTED_VALIDITY_GUARDS:
        return _invalid(payload, "validity guard contract mismatch")
    if not all(value is True for value in validity.values()):
        return _invalid(payload, "one or more validity guards failed")
    originals = payload.get("original_arms")
    if not isinstance(originals, Mapping) or set(originals) != EXPECTED_ARMS:
        return _invalid(payload, "original arm contract mismatch")
    try:
        normalized_originals = {
            arm: _original_arm(originals[arm], name=arm)  # type: ignore[arg-type]
            for arm in EXPECTED_ARMS
        }
    except (TypeError, ValueError) as exc:
        return _invalid(payload, str(exc))
    mechanism = identify_mechanism(normalized_originals)
    if payload.get("mechanism_signature") != mechanism:
        return _invalid(payload, "mechanism signature mismatch")

    if mechanism == "MIXED-MECHANISM":
        if payload.get("common_authority_scale") is not None or payload.get(
            "repair_arms"
        ) != {}:
            return _invalid(payload, "mixed mechanism must not execute a repair")
        return {
            "schema_version": 1,
            "round": "R322",
            "question": "Q-0077",
            "classification": "MECHANISM-NOT-IDENTIFIED",
            "validity_guards": dict(validity),
            "mechanism_signature": mechanism,
            "original_arms": normalized_originals,
            "common_authority_scale": None,
            "repair_arms": {},
            "gates": {"dominance_signature_identified": False},
            "fresh_holdout_eligible": False,
            "physical_closed_loop_round_eligible": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
            "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
            "claim_ceiling": "development-only mechanism not identified",
        }

    scale = float(payload.get("common_authority_scale", float("nan")))
    repairs = payload.get("repair_arms")
    if (
        not np.isfinite(scale)
        or scale <= 0.0
        or scale > 1.0
        or not isinstance(repairs, Mapping)
        or set(repairs) != EXPECTED_ARMS
    ):
        return _invalid(payload, "common repair scale or arm contract mismatch")
    try:
        normalized_repairs = {
            arm: _repair_arm(repairs[arm], name=arm)  # type: ignore[arg-type]
            for arm in EXPECTED_ARMS
        }
    except (TypeError, ValueError) as exc:
        return _invalid(payload, str(exc))

    retained = normalized_repairs["retained_cross"]
    deleted = normalized_repairs["cross_deleted"]
    retained_ratios = np.asarray(retained["energy_ratios_to_zero"], dtype=float)
    deleted_ratios = np.asarray(deleted["energy_ratios_to_zero"], dtype=float)
    mean_reduction = 1.0 - float(np.mean(retained_ratios)) / max(
        float(np.mean(deleted_ratios)), np.finfo(float).tiny
    )
    worst_reduction = 1.0 - float(np.max(retained_ratios)) / max(
        float(np.max(deleted_ratios)), np.finfo(float).tiny
    )
    gates = {
        "dominance_signature_identified": True,
        "both_nominal_controller_poles": bool(
            retained["maximum_controller_pole_radius"] <= MAXIMUM_POLE_RADIUS
            and deleted["maximum_controller_pole_radius"] <= MAXIMUM_POLE_RADIUS
        ),
        "both_nominal_observer_poles": bool(
            retained["maximum_observer_pole_radius"] <= MAXIMUM_POLE_RADIUS
            and deleted["maximum_observer_pole_radius"] <= MAXIMUM_POLE_RADIUS
        ),
        "all_repair_values_finite": bool(retained["finite"] and deleted["finite"]),
        "zero_repair_constraint_violations": bool(
            retained["constraint_violation_count"] == 0
            and deleted["constraint_violation_count"] == 0
        ),
        "retained_every_case_absolute_improvement": bool(
            np.max(retained_ratios) <= ABSOLUTE_FLOOR + 1.0e-12
        ),
        "retained_mean_matched_improvement": bool(
            mean_reduction >= MINIMUM_IMPROVEMENT - 1.0e-12
        ),
        "retained_worst_matched_improvement": bool(
            worst_reduction >= MINIMUM_IMPROVEMENT - 1.0e-12
        ),
    }
    passed = all(gates.values())
    return {
        "schema_version": 1,
        "round": "R322",
        "question": "Q-0077",
        "classification": (
            "ACTUATOR-NORMALIZED-REPAIR-ELIGIBLE"
            if passed
            else "ACTUATOR-NORMALIZED-REPAIR-NO-GO"
        ),
        "validity_guards": dict(validity),
        "mechanism_signature": mechanism,
        "original_arms": normalized_originals,
        "common_authority_scale": scale,
        "repair_arms": normalized_repairs,
        "comparison": {
            "decision": "QUALIFY-DEVELOPMENT-ONLY",
            "mean_energy_reduction_vs_cross_deleted": mean_reduction,
            "worst_energy_reduction_vs_cross_deleted": worst_reduction,
        },
        "gates": gates,
        "fresh_holdout_eligible": passed,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "claim_ceiling": (
            "development-only diagnosis and one common actuator-normalized "
            "feedback candidate"
        ),
    }
