"""Classification tests for the prospectively frozen R319 offline gate."""

from __future__ import annotations

from copy import deepcopy

from probes.r319_observer_lqr_validation import evaluate_observer_lqr


def _arm(ratio: float) -> dict[str, object]:
    return {
        "synthesis_feasible": True,
        "point_designs": {
            "HS0": {"controller_pole_radius": 0.98, "observer_pole_radius": 0.97},
            "HS1": {"controller_pole_radius": 0.98, "observer_pole_radius": 0.97},
        },
        "development": {
            "case_count": 32,
            "finite": True,
            "constraint_violation_count": 0,
            "innovation_energy_ratios": [0.5] * 32,
        },
        "examination": {
            "case_count": 80,
            "finite": True,
            "constraint_violation_count": 0,
            "innovation_energy_ratios": [0.5] * 80,
            "energy_ratios_to_zero": [ratio] * 80,
        },
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R319",
        "question": "Q-0074",
        "validity_guards": {
            "sealed_source_identity": True,
            "matrix_contract": True,
            "deterministic_replay": True,
            "case_contract": True,
            "comparison_contract": True,
            "cross_deletion_contract": True,
            "no_examination_on_development_failure": True,
            "eval_not_run": True,
        },
        "arms": {
            "retained_cross": _arm(0.80),
            "cross_deleted": _arm(0.90),
        },
    }


def test_r319_pass_requires_poles_estimation_constraints_and_improvement() -> None:
    analysis = evaluate_observer_lqr(_payload())

    assert analysis["classification"] == "OBSERVER-LQR-PASS"
    assert analysis["controller_candidate_admitted"] is True
    assert analysis["physical_closed_loop_round_eligible"] is True
    assert analysis["distributed_agent_implementation_authorized"] is False
    assert analysis["training_authorized"] is False


def test_r319_no_go_when_any_retained_case_misses_absolute_floor() -> None:
    payload = _payload()
    payload["arms"]["retained_cross"]["examination"][  # type: ignore[index]
        "energy_ratios_to_zero"
    ][-1] = 0.99

    analysis = evaluate_observer_lqr(payload)

    assert analysis["classification"] == "OBSERVER-LQR-NO-GO"
    assert analysis["gates"]["retained_every_case_absolute_improvement"] is False
    assert analysis["physical_closed_loop_round_eligible"] is False


def test_r319_development_failure_blocks_examination_without_invalidating() -> None:
    payload = _payload()
    payload["arms"]["retained_cross"]["point_designs"]["HS1"][  # type: ignore[index]
        "observer_pole_radius"
    ] = 0.999
    for arm in payload["arms"].values():  # type: ignore[union-attr]
        arm["examination"] = {
            "case_count": 0,
            "finite": True,
            "constraint_violation_count": 0,
            "innovation_energy_ratios": [],
            "energy_ratios_to_zero": [],
            "not_run_reason": "development-gate-failed",
        }

    analysis = evaluate_observer_lqr(payload)

    assert analysis["classification"] == "OBSERVER-LQR-NO-GO"
    assert analysis["gates"]["both_nominal_observer_poles"] is False
    assert analysis["gates"]["examination_executed"] is False


def test_r319_invalidity_precedes_scientific_metrics() -> None:
    payload = deepcopy(_payload())
    payload["validity_guards"]["comparison_contract"] = False  # type: ignore[index]

    analysis = evaluate_observer_lqr(payload)

    assert analysis["classification"] == "INVALID-OBSERVER-LQR"
    assert analysis["controller_candidate_admitted"] is False
