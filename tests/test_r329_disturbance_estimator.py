"""Formal decision tests for the prospective R329 estimator repair."""

from __future__ import annotations

from copy import deepcopy

from probes.r329_disturbance_estimator import analyse_r329_estimator


def _contract() -> dict[str, object]:
    return {
        "development_case_count": 1,
        "points": ["HS0"],
        "gates": {
            "development_mean_output_energy_ratio_maximum": 0.98,
            "development_worst_output_energy_ratio_maximum": 1.0,
        },
        "estimator": {
            "augmented_order": 8,
            "maximum_normalized_covariance_residual": 1.0e-8,
            "maximum_error_pole_radius": 1.0,
            "maximum_normalized_solver_residual_ratio": 1.0,
            "maximum_constraint_residual": 1.0e-8,
        },
    }


def _payload() -> dict[str, object]:
    return {
        "created_utc": "2026-08-04T00:00:00+00:00",
        "seal_sha256": "a" * 64,
        "execution_sha256": "b" * 64,
        "sealed_source_identity": True,
        "parent_identity": True,
        "oracle_identity": True,
        "estimator_information_boundary": True,
        "deterministic_execution_replay": True,
        "holdout_accessed": False,
        "parent_output_feedback_valid_failed": True,
        "designs": {
            "HS0": {
                "augmented_order": 8,
                "observability_rank": 8,
                "finite": True,
                "covariance_positive_semidefinite": True,
                "normalized_covariance_residual": 1.0e-10,
                "error_pole_radius": 0.9,
            }
        },
        "rows": [
            {
                "arm": "retained_cross",
                "phase": "development",
                "case": "c0",
                "solver_failed": False,
                "execution_error": False,
                "constraint_violation_count": 0,
                "maximum_constraint_residual": 1.0e-10,
                "maximum_primal_residual_ratio": 0.5,
                "maximum_dual_residual_ratio": 0.6,
                "output_energy_ratio": 0.5,
                "parent_output_identity": True,
                "state_estimation_squared_error": 0.1,
                "parent_state_estimation_squared_error": 1.0,
            }
        ],
    }


def test_r329_pass_requires_structure_error_improvement_and_absolute_control() -> None:
    analysis = analyse_r329_estimator(_payload(), _contract(), analysis_replay=True)

    assert analysis["classification"] == "AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS"
    assert analysis["state_estimation"]["improved"] is True
    assert analysis["controller"]["case_count_below_zero_control"] == 1
    assert analysis["holdout_accessed"] is False


def test_r329_valid_but_ineffective_estimator_is_no_go() -> None:
    payload = _payload()
    payload["rows"][0]["output_energy_ratio"] = 1.01

    analysis = analyse_r329_estimator(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "AUGMENTED-ESTIMATOR-NO-GO"


def test_r329_information_leak_is_invalid() -> None:
    payload = _payload()
    payload["estimator_information_boundary"] = False

    analysis = analyse_r329_estimator(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-AUGMENTED-ESTIMATOR"


def test_r329_state_error_must_improve_over_parent() -> None:
    payload = deepcopy(_payload())
    payload["rows"][0]["state_estimation_squared_error"] = 1.1

    analysis = analyse_r329_estimator(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "AUGMENTED-ESTIMATOR-NO-GO"
