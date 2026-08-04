"""Behavior tests for the prospectively frozen R320 pole diagnosis."""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from probes.r320_pole_cause_diagnosis import (
    controllability_matrix,
    evaluate_pole_cause,
    normalized_pbh_margin,
    observability_matrix,
)


def test_rank_and_pbh_helpers_distinguish_reachable_from_structural_modes() -> None:
    state = np.diag([0.8, 0.9])
    full_input = np.eye(2)
    full_output = np.eye(2)

    assert np.linalg.matrix_rank(controllability_matrix(state, full_input)) == 2
    assert np.linalg.matrix_rank(observability_matrix(state, full_output)) == 2
    assert normalized_pbh_margin(state, full_input, 0.9, kind="control") > 0.0
    assert normalized_pbh_margin(state, full_output, 0.9, kind="observe") > 0.0

    first_only = np.array([[1.0], [0.0]])
    assert np.linalg.matrix_rank(controllability_matrix(state, first_only)) == 1
    assert normalized_pbh_margin(state, first_only, 0.9, kind="control") == 0.0


def _model() -> dict[str, object]:
    return {
        "state_dimension": 14,
        "stored_controller_pole_radius": 0.999,
        "recomputed_controller_pole_radius": 0.999,
        "stored_observer_pole_radius": 0.998,
        "recomputed_observer_pole_radius": 0.998,
        "failed_controller_mode_count": 1,
        "failed_observer_mode_count": 1,
        "controllability_rank": 14,
        "observability_rank": 14,
        "minimum_failed_controller_pbh_margin": 1.0e-4,
        "minimum_failed_observer_pbh_margin": 2.0e-4,
        "placement": {
            "attempted": True,
            "finite": True,
            "controller_target_max_abs_error": 1.0e-10,
            "observer_target_max_abs_error": 1.0e-10,
            "controller_maximum_radius": 0.98,
            "observer_maximum_radius": 0.94,
        },
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R320",
        "question": "Q-0075",
        "validity_guards": {
            "sealed_parent_identity": True,
            "matrix_gain_contract": True,
            "deterministic_replay": True,
            "failed_mode_contract": True,
            "no_performance_access": True,
            "placement_contract": True,
            "eval_not_run": True,
        },
        "models": {
            "retained_cross/HS0": _model(),
            "retained_cross/HS1": _model(),
            "cross_deleted/HS0": _model(),
            "cross_deleted/HS1": _model(),
        },
    }


def test_r320_admits_one_fixed_template_when_all_failed_modes_are_placeable() -> None:
    analysis = evaluate_pole_cause(_payload())

    assert analysis["classification"] == "POLE-TARGET-ELIGIBLE"
    assert analysis["fixed_template_repair_eligible"] is True
    assert analysis["physical_closed_loop_round_eligible"] is False
    assert analysis["training_authorized"] is False


def test_r320_stops_on_structurally_uncontrollable_failed_mode() -> None:
    payload = _payload()
    model = payload["models"]["retained_cross/HS0"]  # type: ignore[index]
    model["controllability_rank"] = 13
    for value in payload["models"].values():  # type: ignore[union-attr]
        value["placement"] = {
            "attempted": False,
            "not_run_reason": "structural-failure",
        }

    analysis = evaluate_pole_cause(payload)

    assert analysis["classification"] == "STRUCTURAL-POLE-NO-GO"
    assert analysis["fixed_template_repair_eligible"] is False


def test_r320_stops_when_the_single_fixed_template_cannot_be_placed() -> None:
    payload = _payload()
    payload["models"]["cross_deleted/HS1"]["placement"][  # type: ignore[index]
        "controller_target_max_abs_error"
    ] = 1.0e-4

    analysis = evaluate_pole_cause(payload)

    assert analysis["classification"] == "TARGET-PLACEMENT-NO-GO"


def test_r320_reports_conflict_before_structural_interpretation() -> None:
    payload = _payload()
    payload["models"]["retained_cross/HS0"][  # type: ignore[index]
        "recomputed_controller_pole_radius"
    ] = 0.997

    analysis = evaluate_pole_cause(payload)

    assert analysis["classification"] == "DIAGNOSTIC-CONFLICT"
    assert analysis["fixed_template_repair_eligible"] is False


def test_r320_invalidity_precedes_nominal_metrics() -> None:
    payload = deepcopy(_payload())
    payload["validity_guards"]["no_performance_access"] = False  # type: ignore[index]

    analysis = evaluate_pole_cause(payload)

    assert analysis["classification"] == "INVALID-POLE-CAUSE-DIAGNOSIS"
