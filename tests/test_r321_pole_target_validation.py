"""Classification tests for the prospectively frozen R321 examination."""

from __future__ import annotations

from copy import deepcopy

from probes.r321_pole_target_validation import evaluate_pole_target_examination


def _arm(ratio: float) -> dict[str, object]:
    return {
        "synthesis_feasible": True,
        "point_designs": {
            point: {
                "controller_pole_radius": 0.98,
                "observer_pole_radius": 0.94,
                "controller_target_max_abs_error": 1.0e-10,
                "observer_target_max_abs_error": 1.0e-10,
                "controller_gain_frobenius_norm": 10.0,
                "observer_gain_frobenius_norm": 12.0,
            }
            for point in ("HS0", "HS1")
        },
        "development": {
            "case_count": 32,
            "finite": True,
            "constraint_violation_count": 0,
            "innovation_energy_ratios": [0.5] * 32,
            "energy_ratios_to_zero": [0.9] * 32,
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
        "round": "R321",
        "question": "Q-0076",
        "validity_guards": {
            "sealed_source_identity": True,
            "parent_authority": True,
            "matrix_contract": True,
            "sealed_scale_contract": True,
            "fixed_template_contract": True,
            "deterministic_replay": True,
            "case_contract": True,
            "comparison_contract": True,
            "cross_deletion_contract": True,
            "conditional_examination_contract": True,
            "eval_not_run": True,
            "no_physical_execution": True,
        },
        "arms": {
            "retained_cross": _arm(0.80),
            "cross_deleted": _arm(0.90),
        },
    }


def test_r321_pass_requires_exact_poles_finite_traces_and_all_improvements() -> None:
    analysis = evaluate_pole_target_examination(_payload())

    assert analysis["classification"] == "POLE-TARGET-PASS"
    assert analysis["controller_candidate_admitted"] is True
    assert analysis["physical_closed_loop_round_eligible"] is True
    assert analysis["distributed_agent_implementation_authorized"] is False
    assert analysis["training_authorized"] is False


def test_r321_no_go_when_any_retained_case_misses_the_absolute_floor() -> None:
    payload = _payload()
    payload["arms"]["retained_cross"]["examination"][  # type: ignore[index]
        "energy_ratios_to_zero"
    ][-1] = 0.99

    analysis = evaluate_pole_target_examination(payload)

    assert analysis["classification"] == "POLE-TARGET-NO-GO"
    assert analysis["gates"]["retained_every_case_absolute_improvement"] is False
    assert analysis["physical_closed_loop_round_eligible"] is False


def test_r321_nominal_target_failure_blocks_examination_without_invalidating() -> None:
    payload = _payload()
    payload["arms"]["cross_deleted"]["point_designs"]["HS1"][  # type: ignore[index]
        "observer_target_max_abs_error"
    ] = 1.0e-4
    for arm in payload["arms"].values():  # type: ignore[union-attr]
        arm["examination"] = {
            "case_count": 0,
            "finite": True,
            "constraint_violation_count": 0,
            "innovation_energy_ratios": [],
            "energy_ratios_to_zero": [],
            "not_run_reason": "development-gate-failed",
        }

    analysis = evaluate_pole_target_examination(payload)

    assert analysis["classification"] == "POLE-TARGET-NO-GO"
    assert analysis["gates"]["both_exact_observer_targets"] is False
    assert analysis["gates"]["examination_executed"] is False


def test_r321_invalidity_precedes_scientific_metrics() -> None:
    payload = deepcopy(_payload())
    payload["validity_guards"]["sealed_scale_contract"] = False  # type: ignore[index]

    analysis = evaluate_pole_target_examination(payload)

    assert analysis["classification"] == "INVALID-POLE-TARGET-EXAMINATION"
    assert analysis["controller_candidate_admitted"] is False
