"""Decision tests for the sealed R327 legacy-reference amendment."""

from __future__ import annotations

from copy import deepcopy

from probes.r327_reference_recovery import analyse_r327_recovery


def _r326_contract() -> dict[str, object]:
    return {
        "round": "R326",
        "question": "Q-0080",
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "tuning_candidate_count": 0,
        "development_case_count": 1,
        "holdout_case_count": 1,
        "solver": {"name": "osqp", "feasibility_tolerance": 1.0e-8},
        "solver_repair": {
            "prefix_action_absolute_tolerance": 2.0e-5,
            "prefix_output_absolute_tolerance": 1.0e-6,
            "maximum_normalized_residual_ratio": 1.0,
            "minimum_action_hessian_eigenvalue": 0.0,
            "r325_contract_payload_sha256": "c" * 64,
            "dependency_fingerprint": {"osqp": "1.1.3"},
        },
        "comparison_identifiability": {"decision": "ALLOW"},
        "gates": {
            "development_mean_output_energy_ratio_maximum": 0.98,
            "development_worst_output_energy_ratio_maximum": 1.0,
            "holdout_mean_output_energy_ratio_maximum": 0.98,
            "holdout_worst_output_energy_ratio_maximum": 1.0,
            "retained_to_deleted_mean_ratio_maximum": 0.98,
        },
    }


def _row(*, arm: str, case: str, ratio: float, reference_ok: bool) -> dict[str, object]:
    return {
        "arm": arm,
        "phase": "development",
        "case": case,
        "mismatch": "nominal",
        "solver_failed": False,
        "execution_error": False,
        "constraint_violation_count": 0,
        "maximum_constraint_residual": 1.0e-10,
        "maximum_primal_residual_ratio": 0.5,
        "maximum_dual_residual_ratio": 0.6,
        "maximum_solver_iterations": 100,
        "output_energy_ratio": ratio,
        "reference_target_steps": 1,
        "reference_completed_steps": 1 if reference_ok else 0,
        "reference_status_matches_r325": reference_ok,
        "prefix_samples": (
            [
                {
                    "step": 0,
                    "node_action_max_abs_error": 1.0e-8,
                    "coordinate_action_max_abs_error": 1.0e-8,
                    "predicted_output_max_abs_error": 1.0e-8,
                }
            ]
            if reference_ok
            else []
        ),
    }


def _r326_execution() -> dict[str, object]:
    return {
        "created_utc": "2026-08-04T00:00:00+00:00",
        "seal_sha256": "a" * 64,
        "sealed_source_identity": True,
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "r325_contract_payload_sha256": "c" * 64,
        "dependency_fingerprint": {"osqp": "1.1.3"},
        "solver_settings": {"name": "osqp", "feasibility_tolerance": 1.0e-8},
        "deterministic_execution_replay": True,
        "designs": {
            "retained_cross": {"HS0": {"minimum_action_hessian_eigenvalue": 0.1}},
            "cross_deleted": {"HS0": {"minimum_action_hessian_eigenvalue": 0.1}},
        },
        "holdout_accessed": False,
        "arms": {
            "retained_cross": {
                "observer_synthesis_succeeded": True,
                "rows": {
                    "development": [
                        _row(
                            arm="retained_cross",
                            case="HS0/triangle/common/positive",
                            ratio=1.01,
                            reference_ok=False,
                        )
                    ]
                },
            },
            "cross_deleted": {
                "observer_synthesis_succeeded": True,
                "rows": {
                    "development": [
                        _row(
                            arm="cross_deleted",
                            case="HS0/impulse/common/positive",
                            ratio=0.95,
                            reference_ok=True,
                        )
                    ]
                },
            },
        },
    }


def _recovery_contract() -> dict[str, object]:
    return {
        "reference_recovery": {
            "expected_keys": [["retained_cross", "HS0/triangle/common/positive", "nominal"]],
            "prefix_action_absolute_tolerance": 2.0e-5,
            "prefix_output_absolute_tolerance": 1.0e-6,
        }
    }


def _recovery_execution() -> dict[str, object]:
    row = _row(
        arm="retained_cross",
        case="HS0/triangle/common/positive",
        ratio=0.0,
        reference_ok=True,
    )
    return {
        "sealed_source_identity": True,
        "parent_identity": True,
        "holdout_accessed": False,
        "deterministic_reference_replay": True,
        "rows": [row],
    }


def test_complete_recovery_reaches_unchanged_development_no_go() -> None:
    result = analyse_r327_recovery(
        _recovery_execution(),
        _recovery_contract(),
        _r326_execution(),
        _r326_contract(),
        analysis_replay=True,
    )

    assert result["reference_recovery_passed"] is True
    assert result["combined_solver_repair_passed"] is True
    assert result["classification"] == "DEVELOPMENT-NO-GO"
    assert result["holdout_accessed"] is False


def test_missing_recovery_key_is_invalid() -> None:
    execution = _recovery_execution()
    execution["rows"] = []

    result = analyse_r327_recovery(
        execution,
        _recovery_contract(),
        _r326_execution(),
        _r326_contract(),
        analysis_replay=True,
    )

    assert result["classification"] == "INVALID-REFERENCE-RECOVERY"


def test_recovered_prefix_threshold_failure_is_no_go() -> None:
    execution = _recovery_execution()
    execution["rows"][0]["prefix_samples"][0][  # type: ignore[index]
        "node_action_max_abs_error"
    ] = 3.0e-5

    result = analyse_r327_recovery(
        execution,
        _recovery_contract(),
        _r326_execution(),
        _r326_contract(),
        analysis_replay=True,
    )

    assert result["classification"] == "REFERENCE-RECOVERY-NO-GO"


def test_development_pass_keeps_holdout_sealed() -> None:
    parent = deepcopy(_r326_execution())
    parent["arms"]["retained_cross"]["rows"]["development"][0][  # type: ignore[index]
        "output_energy_ratio"
    ] = 0.90

    result = analyse_r327_recovery(
        _recovery_execution(),
        _recovery_contract(),
        parent,
        _r326_contract(),
        analysis_replay=True,
    )

    assert result["classification"] == "DEVELOPMENT-ADMISSION-PASS-HOLDOUT-SEALED"
    assert result["holdout_accessed"] is False
