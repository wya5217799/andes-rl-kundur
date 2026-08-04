"""Classification tests for the prospectively frozen R318 diagnosis."""

from __future__ import annotations

from copy import deepcopy

from probes.r318_rejection_diagnosis import classify_rejection_diagnosis


def _arm(pole_feasible: int, fully_feasible: int = 0) -> dict[str, object]:
    return {
        "candidate_count": 100,
        "pole_feasible_count": pole_feasible,
        "governor_evaluated_count": pole_feasible,
        "fully_feasible_count": fully_feasible,
        "minimum_pole_radius": 1.01,
        "minimum_pole_scalar": 0.01,
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R318",
        "question": "Q-0073",
        "validity_guards": {
            "sealed_parent_identity": True,
            "gain_reconstruction_identity": True,
            "candidate_contract": True,
            "deterministic_replay": True,
            "no_examination_or_eval": True,
        },
        "arms": {
            "retained_cross": _arm(0),
            "cross_deleted": _arm(0),
        },
    }


def test_r318_classifies_all_pole_rejection_and_one_repair() -> None:
    analysis = classify_rejection_diagnosis(_payload())

    assert analysis["classification"] == "POLE-ONLY-REJECTION"
    assert analysis["repair"]["kind"] == "augmented-observer-quadratic-regulator"
    assert analysis["physical_closed_loop_round_eligible"] is False
    assert analysis["training_authorized"] is False


def test_r318_classifies_governor_only_rejection() -> None:
    payload = _payload()
    payload["arms"] = {  # type: ignore[assignment]
        "retained_cross": _arm(3),
        "cross_deleted": _arm(2),
    }

    analysis = classify_rejection_diagnosis(payload)

    assert analysis["classification"] == "GOVERNOR-ONLY-REJECTION"
    assert analysis["repair"]["kind"] == "constrained-receding-horizon"


def test_r318_conflict_precedes_cause_classification() -> None:
    payload = _payload()
    payload["arms"]["retained_cross"] = _arm(2, fully_feasible=1)  # type: ignore[index]

    analysis = classify_rejection_diagnosis(payload)

    assert analysis["classification"] == "DIAGNOSTIC-CONFLICT"
    assert analysis["repair"]["kind"] == "repair-r317-selection-implementation"


def test_r318_invalidity_precedes_candidate_counts() -> None:
    payload = deepcopy(_payload())
    payload["validity_guards"]["deterministic_replay"] = False  # type: ignore[index]

    analysis = classify_rejection_diagnosis(payload)

    assert analysis["classification"] == "INVALID-REJECTION-DIAGNOSIS"
    assert analysis["repair"] is None
