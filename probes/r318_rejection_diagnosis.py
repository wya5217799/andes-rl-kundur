"""Pure classifier for the frozen R318 scalar-grid rejection diagnosis."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

EXPECTED_VALIDITY_GUARDS = {
    "sealed_parent_identity",
    "gain_reconstruction_identity",
    "candidate_contract",
    "deterministic_replay",
    "no_examination_or_eval",
}
EXPECTED_ARMS = {"retained_cross", "cross_deleted"}
EXPECTED_CANDIDATE_COUNT = 100


def _invalid(payload: Mapping[str, object], reason: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": payload.get("round"),
        "question": payload.get("question"),
        "classification": "INVALID-REJECTION-DIAGNOSIS",
        "invalid_reason": reason,
        "repair": None,
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
    }


def _arm_summary(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} arm is not an object")
    counts = {
        key: int(value.get(key, -1))
        for key in (
            "candidate_count",
            "pole_feasible_count",
            "governor_evaluated_count",
            "fully_feasible_count",
        )
    }
    if (
        counts["candidate_count"] != EXPECTED_CANDIDATE_COUNT
        or not 0
        <= counts["fully_feasible_count"]
        <= counts["governor_evaluated_count"]
        <= counts["pole_feasible_count"]
        <= counts["candidate_count"]
    ):
        raise ValueError(f"{name} candidate counts violate the frozen contract")
    minimum_radius = float(value.get("minimum_pole_radius", float("nan")))
    minimum_scalar = float(value.get("minimum_pole_scalar", float("nan")))
    if (
        not np.isfinite(minimum_radius)
        or minimum_radius < 0.0
        or not np.isfinite(minimum_scalar)
        or minimum_scalar <= 0.0
    ):
        raise ValueError(f"{name} minimum pole diagnostic is invalid")
    return {
        **counts,
        "minimum_pole_radius": minimum_radius,
        "minimum_pole_scalar": minimum_scalar,
        "maximum_governor_intervention_count": int(
            value.get("maximum_governor_intervention_count", 0)
        ),
        "constraint_violation_types": list(
            value.get("constraint_violation_types", [])
        ),
    }


def classify_rejection_diagnosis(payload: object) -> dict[str, Any]:
    """Return one frozen cause classification and its sole eligible repair."""

    if not isinstance(payload, Mapping):
        return _invalid({}, "payload is not an object")
    if payload.get("round") != "R318" or payload.get("question") != "Q-0073":
        return _invalid(payload, "round or question identity mismatch")
    guards = payload.get("validity_guards")
    if not isinstance(guards, Mapping) or set(guards) != EXPECTED_VALIDITY_GUARDS:
        return _invalid(payload, "validity guard contract mismatch")
    if not all(value is True for value in guards.values()):
        return _invalid(payload, "one or more validity guards failed")
    arms_value = payload.get("arms")
    if not isinstance(arms_value, Mapping) or set(arms_value) != EXPECTED_ARMS:
        return _invalid(payload, "arm identity mismatch")
    try:
        arms = {
            name: _arm_summary(arms_value[name], name=name) for name in EXPECTED_ARMS
        }
    except (TypeError, ValueError) as exc:
        return _invalid(payload, str(exc))

    fully_feasible = sum(int(arm["fully_feasible_count"]) for arm in arms.values())
    pole_counts = [int(arm["pole_feasible_count"]) for arm in arms.values()]
    if fully_feasible:
        classification = "DIAGNOSTIC-CONFLICT"
        repair = {
            "kind": "repair-r317-selection-implementation",
            "reason": "at least one replayed frozen candidate passed both gates",
        }
    elif all(count == 0 for count in pole_counts):
        classification = "POLE-ONLY-REJECTION"
        repair = {
            "kind": "augmented-observer-quadratic-regulator",
            "reason": (
                "synthesize directly on the one-sample-delay-augmented model "
                "instead of inverting zero-frequency gain"
            ),
        }
    elif all(count > 0 for count in pole_counts):
        classification = "GOVERNOR-ONLY-REJECTION"
        repair = {
            "kind": "constrained-receding-horizon",
            "reason": (
                "preserve the delayed model and unchanged limits while making "
                "constraint feasibility part of synthesis"
            ),
        }
    else:
        classification = "MIXED-REJECTION"
        repair = {
            "kind": "augmented-observer-quadratic-regulator",
            "reason": (
                "repair nominal delayed poles before any constraint-directed change"
            ),
        }
    return {
        "schema_version": 1,
        "round": "R318",
        "question": "Q-0073",
        "classification": classification,
        "validity_guards": dict(guards),
        "arms": arms,
        "repair": repair,
        "comparison_identifiability": {
            "decision": "QUALIFY",
            "allowed_claim": (
                "candidate-level rejection cause for the already rejected "
                "R317 laws only"
            ),
            "stay_out": [
                "retained-cross efficacy",
                "controller-family value",
                "physical stability or safety",
                "distributed-agent or MARL value",
            ],
        },
        "physical_closed_loop_round_eligible": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "claim_ceiling": (
            "cause classification and one future offline controller-form repair only"
        ),
    }
