"""Classification tests for the prospective R322 development diagnosis."""

from __future__ import annotations

from copy import deepcopy

from probes.r322_feedback_diagnosis_validation import evaluate_feedback_diagnosis


def _original_arm() -> dict[str, object]:
    return {
        "case_count": 32,
        "finite": True,
        "constraint_violation_count": 0,
        "observer_energy_ratios_to_zero": [4.0] * 32,
        "exact_state_energy_ratios_to_zero": [3.0] * 32,
        "true_state_overdrive_ratios": [3.0] * 32,
        "estimation_error_command_norm_ratios": [0.2] * 32,
    }


def _repair_arm(ratio: float) -> dict[str, object]:
    return {
        "case_count": 32,
        "finite": True,
        "constraint_violation_count": 0,
        "point_designs": {
            "HS0": {"controller_pole_radius": 0.99, "observer_pole_radius": 0.94},
            "HS1": {"controller_pole_radius": 0.99, "observer_pole_radius": 0.94},
        },
        "energy_ratios_to_zero": [ratio] * 32,
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R322",
        "question": "Q-0077",
        "validity_guards": {
            "sealed_source_identity": True,
            "parent_hash_only": True,
            "exact_design_contract": True,
            "matrix_contract": True,
            "development_only_contract": True,
            "decomposition_identity": True,
            "deterministic_replay": True,
            "case_contract": True,
            "common_scale_contract": True,
            "comparison_contract": True,
            "eval_not_run": True,
            "no_physical_execution": True,
        },
        "original_arms": {
            "retained_cross": _original_arm(),
            "cross_deleted": _original_arm(),
        },
        "mechanism_signature": "GAIN-AUTHORITY-DOMINANT",
        "common_authority_scale": 0.01,
        "repair_arms": {
            "retained_cross": _repair_arm(0.80),
            "cross_deleted": _repair_arm(0.90),
        },
    }


def test_r322_admits_one_common_scaled_repair_after_gain_authority_signature() -> None:
    analysis = evaluate_feedback_diagnosis(_payload())

    assert analysis["classification"] == "ACTUATOR-NORMALIZED-REPAIR-ELIGIBLE"
    assert analysis["mechanism_signature"] == "GAIN-AUTHORITY-DOMINANT"
    assert analysis["fresh_holdout_eligible"] is True
    assert analysis["physical_closed_loop_round_eligible"] is False
    assert analysis["training_authorized"] is False


def test_r322_stops_without_repair_when_no_dominance_signature_is_identified() -> None:
    payload = _payload()
    for arm in payload["original_arms"].values():  # type: ignore[union-attr]
        arm["true_state_overdrive_ratios"] = [1.2] * 32
        arm["estimation_error_command_norm_ratios"] = [0.8] * 32
    payload["mechanism_signature"] = "MIXED-MECHANISM"
    payload["common_authority_scale"] = None
    payload["repair_arms"] = {}

    analysis = evaluate_feedback_diagnosis(payload)

    assert analysis["classification"] == "MECHANISM-NOT-IDENTIFIED"
    assert analysis["fresh_holdout_eligible"] is False


def test_r322_rejects_common_scaled_repair_when_absolute_floor_still_fails() -> None:
    payload = _payload()
    payload["repair_arms"]["retained_cross"][  # type: ignore[index]
        "energy_ratios_to_zero"
    ][-1] = 1.01

    analysis = evaluate_feedback_diagnosis(payload)

    assert analysis["classification"] == "ACTUATOR-NORMALIZED-REPAIR-NO-GO"
    assert analysis["gates"]["retained_every_case_absolute_improvement"] is False


def test_r322_invalidity_precedes_mechanism_or_repair_metrics() -> None:
    payload = deepcopy(_payload())
    payload["validity_guards"]["development_only_contract"] = False  # type: ignore[index]

    analysis = evaluate_feedback_diagnosis(payload)

    assert analysis["classification"] == "INVALID-DEVELOPMENT-DIAGNOSIS"
    assert analysis["fresh_holdout_eligible"] is False
