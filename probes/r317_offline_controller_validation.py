"""Formal classifier for the prospectively frozen R317 offline controller gate.

The probe consumes only model-calculation summaries.  It runs no controller,
optimizer, simulator, or EVAL profile and therefore cannot repair an execution
or change a registered threshold after outcomes are visible.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


EXPECTED_VALIDITY_GUARDS = {
    "sealed_source_identity",
    "matrix_contract",
    "deterministic_replay",
    "case_contract",
    "comparison_contract",
    "eval_not_run",
}
EXPECTED_CANDIDATE_COUNT = 100
EXPECTED_DEVELOPMENT_CASE_COUNT = 32
EXPECTED_EXAMINATION_CASE_COUNT = 80
MAXIMUM_POLE_RADIUS = 0.995
MINIMUM_IMPROVEMENT = 0.02


def _invalid_analysis(payload: Mapping[str, object], reason: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": payload.get("round"),
        "question": payload.get("question"),
        "classification": "INVALID-OFFLINE-CONTROLLER",
        "invalid_reason": reason,
        "controller_candidate_admitted": False,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
    }


def _arm_summary(arm: Mapping[str, object], *, name: str) -> dict[str, object]:
    examination = arm.get("examination")
    if not isinstance(examination, Mapping):
        raise ValueError(f"{name} examination is missing")
    feasible = arm.get("selection_feasible") is True
    candidate_count = int(arm.get("candidate_count", -1))
    development_case_count = int(arm.get("development_case_count", -1))
    if not feasible:
        if (
            arm.get("selected_scalar") is not None
            or arm.get("maximum_pole_radius") is not None
            or examination.get("case_count") != 0
            or examination.get("energy_ratios_to_zero") != []
            or examination.get("not_run_reason") != "no-feasible-scalar"
        ):
            raise ValueError(f"{name} infeasible-selection contract mismatch")
        return {
            "selection_feasible": False,
            "selected_scalar": None,
            "candidate_count": candidate_count,
            "development_case_count": development_case_count,
            "maximum_pole_radius": None,
            "examination_case_count": 0,
            "finite": examination.get("finite") is True,
            "constraint_violation_count": int(
                examination.get("constraint_violation_count", -1)
            ),
            "mean_output_energy_ratio": None,
            "worst_output_energy_ratio": None,
            "best_output_energy_ratio": None,
            "energy_ratios_to_zero": [],
            "not_run_reason": "no-feasible-scalar",
        }
    ratios_value = examination.get("energy_ratios_to_zero")
    if not isinstance(ratios_value, Sequence) or isinstance(ratios_value, (str, bytes)):
        raise ValueError(f"{name} energy ratios are missing")
    ratios = np.asarray(ratios_value, dtype=float)
    if (
        ratios.shape != (EXPECTED_EXAMINATION_CASE_COUNT,)
        or not np.all(np.isfinite(ratios))
        or np.any(ratios < 0.0)
    ):
        raise ValueError(f"{name} energy ratios violate the case contract")
    selected_scalar = float(arm.get("selected_scalar", float("nan")))
    pole_radius = float(arm.get("maximum_pole_radius", float("nan")))
    if not np.isfinite(selected_scalar) or selected_scalar <= 0.0:
        raise ValueError(f"{name} selected scalar is invalid")
    if not np.isfinite(pole_radius) or pole_radius < 0.0:
        raise ValueError(f"{name} pole radius is invalid")
    return {
        "selection_feasible": True,
        "selected_scalar": selected_scalar,
        "candidate_count": candidate_count,
        "development_case_count": development_case_count,
        "maximum_pole_radius": pole_radius,
        "examination_case_count": int(examination.get("case_count", -1)),
        "finite": examination.get("finite") is True,
        "constraint_violation_count": int(
            examination.get("constraint_violation_count", -1)
        ),
        "mean_output_energy_ratio": float(np.mean(ratios)),
        "worst_output_energy_ratio": float(np.max(ratios)),
        "best_output_energy_ratio": float(np.min(ratios)),
        "energy_ratios_to_zero": ratios.tolist(),
    }


def evaluate_offline_controller(payload: object) -> dict[str, Any]:
    """Classify one immutable R317 model-only controller result."""

    if not isinstance(payload, Mapping):
        return _invalid_analysis({}, "payload is not an object")
    if payload.get("round") != "R317" or payload.get("question") != "Q-0072":
        return _invalid_analysis(payload, "round or question identity mismatch")
    validity = payload.get("validity_guards")
    if not isinstance(validity, Mapping) or set(validity) != EXPECTED_VALIDITY_GUARDS:
        return _invalid_analysis(payload, "validity guard contract mismatch")
    if not all(value is True for value in validity.values()):
        return _invalid_analysis(payload, "one or more validity guards failed")
    arms = payload.get("arms")
    if not isinstance(arms, Mapping) or set(arms) != {
        "retained_cross",
        "cross_deleted",
    }:
        return _invalid_analysis(payload, "comparison arm contract mismatch")
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
        return _invalid_analysis(payload, str(exc))

    contract_fields = (
        retained["candidate_count"] == EXPECTED_CANDIDATE_COUNT,
        deleted["candidate_count"] == EXPECTED_CANDIDATE_COUNT,
        retained["development_case_count"] == EXPECTED_DEVELOPMENT_CASE_COUNT,
        deleted["development_case_count"] == EXPECTED_DEVELOPMENT_CASE_COUNT,
        retained["examination_case_count"]
        == (
            EXPECTED_EXAMINATION_CASE_COUNT
            if retained["selection_feasible"]
            else 0
        ),
        deleted["examination_case_count"]
        == (
            EXPECTED_EXAMINATION_CASE_COUNT
            if deleted["selection_feasible"]
            else 0
        ),
    )
    if not all(contract_fields):
        return _invalid_analysis(payload, "tuning or case count drift")

    if not retained["selection_feasible"] or not deleted["selection_feasible"]:
        gates = {
            "both_selections_feasible": False,
            "both_nominal_pole_radii": False,
            "all_examination_outputs_finite": bool(
                retained["finite"] and deleted["finite"]
            ),
            "zero_constraint_violations": bool(
                retained["constraint_violation_count"] == 0
                and deleted["constraint_violation_count"] == 0
            ),
            "retained_every_case_absolute_improvement": False,
            "retained_mean_matched_improvement": False,
            "retained_worst_matched_improvement": False,
        }
        return {
            "schema_version": 1,
            "round": "R317",
            "question": "Q-0072",
            "classification": "OFFLINE-CONTROLLER-NO-GO",
            "validity_guards": dict(validity),
            "arms": {
                "retained_cross": retained,
                "cross_deleted": deleted,
            },
            "comparison": {
                "decision": "ALLOW-DESIGN-NOT-EXECUTED",
                "mean_energy_reduction_vs_cross_deleted": None,
                "worst_energy_reduction_vs_cross_deleted": None,
                "stay_out": [
                    "all efficacy and architecture claims because one arm had no feasible scalar"
                ],
            },
            "gates": gates,
            "controller_candidate_admitted": False,
            "physical_closed_loop_round_eligible": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
            "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
            "claim_ceiling": "frozen static law rejected before examination",
        }

    retained_mean = float(retained["mean_output_energy_ratio"])
    deleted_mean = float(deleted["mean_output_energy_ratio"])
    retained_worst = float(retained["worst_output_energy_ratio"])
    deleted_worst = float(deleted["worst_output_energy_ratio"])
    mean_reduction = 1.0 - retained_mean / max(deleted_mean, np.finfo(float).tiny)
    worst_reduction = 1.0 - retained_worst / max(
        deleted_worst, np.finfo(float).tiny
    )
    gates = {
        "both_selections_feasible": bool(
            retained["selection_feasible"] and deleted["selection_feasible"]
        ),
        "both_nominal_pole_radii": bool(
            float(retained["maximum_pole_radius"]) <= MAXIMUM_POLE_RADIUS
            and float(deleted["maximum_pole_radius"]) <= MAXIMUM_POLE_RADIUS
        ),
        "all_examination_outputs_finite": bool(
            retained["finite"] and deleted["finite"]
        ),
        "zero_constraint_violations": bool(
            retained["constraint_violation_count"] == 0
            and deleted["constraint_violation_count"] == 0
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
    passed = all(gates.values())
    return {
        "schema_version": 1,
        "round": "R317",
        "question": "Q-0072",
        "classification": (
            "OFFLINE-CONTROLLER-PASS" if passed else "OFFLINE-CONTROLLER-NO-GO"
        ),
        "validity_guards": dict(validity),
        "arms": {
            "retained_cross": retained,
            "cross_deleted": deleted,
        },
        "comparison": {
            "decision": "ALLOW",
            "executed_comparison": (
                "retained versus deleted common/differential feedback blocks "
                "in one frozen delayed DC-inverse law"
            ),
            "identified_estimand": (
                "finite-bank normalized output-energy value of the retained "
                "feedback blocks under matched model, governor, timing, budget, "
                "disturbance, and mismatch conditions"
            ),
            "mean_energy_reduction_vs_cross_deleted": mean_reduction,
            "worst_energy_reduction_vs_cross_deleted": worst_reduction,
            "stay_out": [
                "controller-family superiority",
                "robust MPC or DAPI value",
                "physical closed-loop efficacy or recursive feasibility",
                "voltage or current safety",
                "distributed execution or communication value",
                "agent or MARL value",
                "topology generalization",
                "robust-stability certification",
                "deployment",
            ],
        },
        "gates": gates,
        "controller_candidate_admitted": passed,
        "physical_closed_loop_round_eligible": passed,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "claim_ceiling": (
            "two-point finite-bank model-only value of one frozen delayed "
            "cross-feedback construction"
        ),
    }
