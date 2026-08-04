"""Formal classifier for the prospectively frozen R321 model-only gate.

The probe consumes immutable calculation summaries. It runs no synthesis,
controller, simulator, optimizer, or EVAL profile and cannot change a target or
threshold after an outcome is visible.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


EXPECTED_VALIDITY_GUARDS = {
    "sealed_source_identity",
    "parent_authority",
    "matrix_contract",
    "sealed_scale_contract",
    "fixed_template_contract",
    "deterministic_replay",
    "case_contract",
    "comparison_contract",
    "cross_deletion_contract",
    "conditional_examination_contract",
    "eval_not_run",
    "no_physical_execution",
}
EXPECTED_POINTS = {"HS0", "HS1"}
EXPECTED_DEVELOPMENT_CASE_COUNT = 32
EXPECTED_EXAMINATION_CASE_COUNT = 80
CONTROLLER_TARGET_RADIUS = 0.98
OBSERVER_TARGET_RADIUS = 0.94
TARGET_TOLERANCE = 1.0e-8
MINIMUM_IMPROVEMENT = 0.02


def _invalid(payload: Mapping[str, object], reason: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": payload.get("round"),
        "question": payload.get("question"),
        "classification": "INVALID-POLE-TARGET-EXAMINATION",
        "invalid_reason": reason,
        "controller_candidate_admitted": False,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
    }


def _finite_ratios(values: object, count: int, *, name: str) -> np.ndarray:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} ratios are missing")
    ratios = np.asarray(values, dtype=float)
    if ratios.shape != (count,) or not np.all(np.isfinite(ratios)) or np.any(
        ratios < 0.0
    ):
        raise ValueError(f"{name} ratios violate the case contract")
    return ratios


def _point_designs(values: Mapping[object, object], *, name: str) -> dict[str, Any]:
    if set(values) != EXPECTED_POINTS:
        raise ValueError(f"{name} point-design contract mismatch")
    normalized: dict[str, dict[str, float]] = {}
    fields = (
        "controller_pole_radius",
        "observer_pole_radius",
        "controller_target_max_abs_error",
        "observer_target_max_abs_error",
        "controller_gain_frobenius_norm",
        "observer_gain_frobenius_norm",
    )
    for point, value in values.items():
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} point design is not an object")
        row = {field: float(value.get(field, float("nan"))) for field in fields}
        if not all(np.isfinite(number) and number >= 0.0 for number in row.values()):
            raise ValueError(f"{name} point design has a non-finite metric")
        normalized[str(point)] = row
    return normalized


def _not_run_contract(summary: Mapping[str, object], *, reason: str, name: str) -> None:
    if (
        int(summary.get("case_count", -1)) != 0
        or summary.get("not_run_reason") != reason
        or summary.get("innovation_energy_ratios") != []
        or summary.get("energy_ratios_to_zero") != []
    ):
        raise ValueError(f"{name} not-run contract mismatch")


def _arm_summary(arm: Mapping[str, object], *, name: str) -> dict[str, Any]:
    synthesis = arm.get("synthesis_feasible") is True
    point_designs = arm.get("point_designs")
    development = arm.get("development")
    examination = arm.get("examination")
    if not isinstance(point_designs, Mapping):
        raise ValueError(f"{name} point designs are missing")
    if not isinstance(development, Mapping) or not isinstance(examination, Mapping):
        raise ValueError(f"{name} development or examination is missing")

    if not synthesis:
        if set(point_designs):
            raise ValueError(f"{name} infeasible synthesis has point designs")
        _not_run_contract(development, reason="synthesis-failed", name=name)
        _not_run_contract(examination, reason="development-gate-failed", name=name)
        return {
            "synthesis_feasible": False,
            "point_designs": {},
            "maximum_controller_pole_radius": None,
            "maximum_observer_pole_radius": None,
            "maximum_controller_target_error": None,
            "maximum_observer_target_error": None,
            "development_case_count": 0,
            "development_finite": True,
            "development_constraint_violation_count": 0,
            "development_innovation_energy_ratios": [],
            "development_energy_ratios_to_zero": [],
            "examination_case_count": 0,
            "examination_finite": True,
            "examination_constraint_violation_count": 0,
            "examination_innovation_energy_ratios": [],
            "energy_ratios_to_zero": [],
        }

    designs = _point_designs(point_designs, name=name)
    development_count = int(development.get("case_count", -1))
    if development_count != EXPECTED_DEVELOPMENT_CASE_COUNT:
        raise ValueError(f"{name} development case count drift")
    development_innovations = _finite_ratios(
        development.get("innovation_energy_ratios"),
        EXPECTED_DEVELOPMENT_CASE_COUNT,
        name=f"{name} development innovation",
    )
    development_ratios = _finite_ratios(
        development.get("energy_ratios_to_zero"),
        EXPECTED_DEVELOPMENT_CASE_COUNT,
        name=f"{name} development energy",
    )

    examination_count = int(examination.get("case_count", -1))
    if examination_count == 0:
        _not_run_contract(
            examination, reason="development-gate-failed", name=f"{name} examination"
        )
        examination_innovations = np.asarray([], dtype=float)
        examination_ratios = np.asarray([], dtype=float)
    elif examination_count == EXPECTED_EXAMINATION_CASE_COUNT:
        examination_innovations = _finite_ratios(
            examination.get("innovation_energy_ratios"),
            EXPECTED_EXAMINATION_CASE_COUNT,
            name=f"{name} examination innovation",
        )
        examination_ratios = _finite_ratios(
            examination.get("energy_ratios_to_zero"),
            EXPECTED_EXAMINATION_CASE_COUNT,
            name=f"{name} examination energy",
        )
    else:
        raise ValueError(f"{name} examination case count drift")

    return {
        "synthesis_feasible": True,
        "point_designs": designs,
        "maximum_controller_pole_radius": max(
            row["controller_pole_radius"] for row in designs.values()
        ),
        "maximum_observer_pole_radius": max(
            row["observer_pole_radius"] for row in designs.values()
        ),
        "maximum_controller_target_error": max(
            row["controller_target_max_abs_error"] for row in designs.values()
        ),
        "maximum_observer_target_error": max(
            row["observer_target_max_abs_error"] for row in designs.values()
        ),
        "development_case_count": development_count,
        "development_finite": development.get("finite") is True,
        "development_constraint_violation_count": int(
            development.get("constraint_violation_count", -1)
        ),
        "development_innovation_energy_ratios": development_innovations.tolist(),
        "development_energy_ratios_to_zero": development_ratios.tolist(),
        "examination_case_count": examination_count,
        "examination_finite": examination.get("finite") is True,
        "examination_constraint_violation_count": int(
            examination.get("constraint_violation_count", -1)
        ),
        "examination_innovation_energy_ratios": examination_innovations.tolist(),
        "energy_ratios_to_zero": examination_ratios.tolist(),
    }


def evaluate_pole_target_examination(payload: object) -> dict[str, Any]:
    """Classify one immutable R321 fixed pole-target examination result."""

    if not isinstance(payload, Mapping):
        return _invalid({}, "payload is not an object")
    if payload.get("round") != "R321" or payload.get("question") != "Q-0076":
        return _invalid(payload, "round or question identity mismatch")
    validity = payload.get("validity_guards")
    if not isinstance(validity, Mapping) or set(validity) != EXPECTED_VALIDITY_GUARDS:
        return _invalid(payload, "validity guard contract mismatch")
    if not all(value is True for value in validity.values()):
        return _invalid(payload, "one or more validity guards failed")
    arms = payload.get("arms")
    if not isinstance(arms, Mapping) or set(arms) != {
        "retained_cross",
        "cross_deleted",
    }:
        return _invalid(payload, "comparison arm contract mismatch")
    try:
        retained_value = arms["retained_cross"]
        deleted_value = arms["cross_deleted"]
        if not isinstance(retained_value, Mapping) or not isinstance(
            deleted_value, Mapping
        ):
            raise ValueError("arm is not an object")
        retained = _arm_summary(retained_value, name="retained_cross")
        deleted = _arm_summary(deleted_value, name="cross_deleted")
    except (TypeError, ValueError) as exc:
        return _invalid(payload, str(exc))

    gates: dict[str, bool] = {
        "both_syntheses_feasible": bool(
            retained["synthesis_feasible"] and deleted["synthesis_feasible"]
        ),
        "both_exact_controller_targets": bool(
            retained["synthesis_feasible"]
            and deleted["synthesis_feasible"]
            and retained["maximum_controller_target_error"] <= TARGET_TOLERANCE
            and deleted["maximum_controller_target_error"] <= TARGET_TOLERANCE
            and retained["maximum_controller_pole_radius"]
            <= CONTROLLER_TARGET_RADIUS + TARGET_TOLERANCE
            and deleted["maximum_controller_pole_radius"]
            <= CONTROLLER_TARGET_RADIUS + TARGET_TOLERANCE
        ),
        "both_exact_observer_targets": bool(
            retained["synthesis_feasible"]
            and deleted["synthesis_feasible"]
            and retained["maximum_observer_target_error"] <= TARGET_TOLERANCE
            and deleted["maximum_observer_target_error"] <= TARGET_TOLERANCE
            and retained["maximum_observer_pole_radius"]
            <= OBSERVER_TARGET_RADIUS + TARGET_TOLERANCE
            and deleted["maximum_observer_pole_radius"]
            <= OBSERVER_TARGET_RADIUS + TARGET_TOLERANCE
        ),
        "all_development_values_finite": bool(
            retained["development_finite"] and deleted["development_finite"]
        ),
        "zero_development_constraint_violations": bool(
            retained["development_constraint_violation_count"] == 0
            and deleted["development_constraint_violation_count"] == 0
        ),
    }
    development_passed = all(gates.values())
    examination_executed = bool(
        retained["examination_case_count"] == EXPECTED_EXAMINATION_CASE_COUNT
        and deleted["examination_case_count"] == EXPECTED_EXAMINATION_CASE_COUNT
    )
    if examination_executed != development_passed:
        return _invalid(payload, "conditional examination contract mismatch")
    gates["examination_executed"] = examination_executed

    if not development_passed:
        gates.update(
            {
                "all_examination_values_finite": False,
                "zero_examination_constraint_violations": False,
                "retained_every_case_absolute_improvement": False,
                "retained_mean_matched_improvement": False,
                "retained_worst_matched_improvement": False,
            }
        )
        return {
            "schema_version": 1,
            "round": "R321",
            "question": "Q-0076",
            "classification": "POLE-TARGET-NO-GO",
            "validity_guards": dict(validity),
            "arms": {"retained_cross": retained, "cross_deleted": deleted},
            "comparison": {
                "decision": "ALLOW-DESIGN-NOT-EXECUTED",
                "mean_energy_reduction_vs_cross_deleted": None,
                "worst_energy_reduction_vs_cross_deleted": None,
                "stay_out": ["all efficacy and architecture claims"],
            },
            "gates": gates,
            "controller_candidate_admitted": False,
            "physical_closed_loop_round_eligible": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
            "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
            "claim_ceiling": "exact fixed pole target rejected before examination",
        }

    retained_ratios = np.asarray(retained["energy_ratios_to_zero"], dtype=float)
    deleted_ratios = np.asarray(deleted["energy_ratios_to_zero"], dtype=float)
    retained_mean = float(np.mean(retained_ratios))
    deleted_mean = float(np.mean(deleted_ratios))
    retained_worst = float(np.max(retained_ratios))
    deleted_worst = float(np.max(deleted_ratios))
    mean_reduction = 1.0 - retained_mean / max(deleted_mean, np.finfo(float).tiny)
    worst_reduction = 1.0 - retained_worst / max(
        deleted_worst, np.finfo(float).tiny
    )
    gates.update(
        {
            "all_examination_values_finite": bool(
                retained["examination_finite"] and deleted["examination_finite"]
            ),
            "zero_examination_constraint_violations": bool(
                retained["examination_constraint_violation_count"] == 0
                and deleted["examination_constraint_violation_count"] == 0
            ),
            "retained_every_case_absolute_improvement": bool(
                retained_worst <= 1.0 - MINIMUM_IMPROVEMENT + 1.0e-12
            ),
            "retained_mean_matched_improvement": bool(
                mean_reduction >= MINIMUM_IMPROVEMENT - 1.0e-12
            ),
            "retained_worst_matched_improvement": bool(
                worst_reduction >= MINIMUM_IMPROVEMENT - 1.0e-12
            ),
        }
    )
    passed = all(gates.values())
    return {
        "schema_version": 1,
        "round": "R321",
        "question": "Q-0076",
        "classification": "POLE-TARGET-PASS" if passed else "POLE-TARGET-NO-GO",
        "validity_guards": dict(validity),
        "arms": {"retained_cross": retained, "cross_deleted": deleted},
        "comparison": {
            "decision": "ALLOW",
            "executed_comparison": (
                "retained versus deleted common/differential transfer blocks in "
                "one exact fixed pole-targeted observer-feedback construction"
            ),
            "identified_estimand": (
                "finite-bank normalized output-energy value of the retained "
                "transfer blocks under matched model, information, action, "
                "governor, placement budget, cases, and mismatch conditions"
            ),
            "mean_energy_reduction_vs_cross_deleted": mean_reduction,
            "worst_energy_reduction_vs_cross_deleted": worst_reduction,
            "stay_out": [
                "controller-family or decoupling-class superiority",
                "physical closed-loop efficacy or robust stability",
                "voltage or current safety",
                "distributed execution or communication value",
                "agent or MARL value",
                "topology generalization, HIL, or deployment",
            ],
        },
        "gates": gates,
        "controller_candidate_admitted": passed,
        "physical_closed_loop_round_eligible": passed,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "claim_ceiling": (
            "two-point finite-bank model-only value of one exact fixed pole-"
            "targeted observer-feedback construction"
        ),
    }
