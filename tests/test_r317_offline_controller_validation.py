"""Classification tests for the prospectively frozen R317 offline gate."""

from __future__ import annotations

from copy import deepcopy

from probes.r317_offline_controller_validation import evaluate_offline_controller


def _arm(ratio: float) -> dict[str, object]:
    return {
        "selection_feasible": True,
        "selected_scalar": 0.1,
        "candidate_count": 100,
        "development_case_count": 32,
        "maximum_pole_radius": 0.99,
        "examination": {
            "case_count": 80,
            "finite": True,
            "constraint_violation_count": 0,
            "energy_ratios_to_zero": [ratio] * 80,
        },
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R317",
        "question": "Q-0072",
        "validity_guards": {
            "sealed_source_identity": True,
            "matrix_contract": True,
            "deterministic_replay": True,
            "case_contract": True,
            "comparison_contract": True,
            "eval_not_run": True,
        },
        "arms": {
            "retained_cross": _arm(0.80),
            "cross_deleted": _arm(0.90),
        },
    }


def test_r317_pass_requires_absolute_and_matched_two_percent_improvement() -> None:
    analysis = evaluate_offline_controller(_payload())

    assert analysis["classification"] == "OFFLINE-CONTROLLER-PASS"
    assert analysis["controller_candidate_admitted"] is True
    assert analysis["physical_closed_loop_round_eligible"] is True
    assert analysis["distributed_agent_implementation_authorized"] is False
    assert analysis["training_authorized"] is False


def test_r317_no_go_when_any_retained_case_misses_absolute_floor() -> None:
    payload = _payload()
    payload["arms"]["retained_cross"]["examination"][  # type: ignore[index]
        "energy_ratios_to_zero"
    ][-1] = 0.99

    analysis = evaluate_offline_controller(payload)

    assert analysis["classification"] == "OFFLINE-CONTROLLER-NO-GO"
    assert analysis["gates"]["retained_every_case_absolute_improvement"] is False
    assert analysis["physical_closed_loop_round_eligible"] is False


def test_r317_invalidity_precedes_scientific_metrics() -> None:
    payload = deepcopy(_payload())
    payload["validity_guards"]["sealed_source_identity"] = False  # type: ignore[index]

    analysis = evaluate_offline_controller(payload)

    assert analysis["classification"] == "INVALID-OFFLINE-CONTROLLER"
    assert analysis["controller_candidate_admitted"] is False
    assert analysis["physical_closed_loop_round_eligible"] is False


def test_r317_no_feasible_scalar_is_a_scientific_no_go_not_invalid() -> None:
    payload = _payload()
    payload["arms"]["retained_cross"] = {  # type: ignore[index]
        "selection_feasible": False,
        "selected_scalar": None,
        "candidate_count": 100,
        "development_case_count": 32,
        "maximum_pole_radius": None,
        "examination": {
            "case_count": 0,
            "finite": True,
            "constraint_violation_count": 0,
            "energy_ratios_to_zero": [],
            "not_run_reason": "no-feasible-scalar",
        },
    }

    analysis = evaluate_offline_controller(payload)

    assert analysis["classification"] == "OFFLINE-CONTROLLER-NO-GO"
    assert analysis["gates"]["both_selections_feasible"] is False
