"""Formal classification tests for the R325 constrained controller."""

from __future__ import annotations

from probes.r325_constrained_horizon_validation import (
    analyse_r325_execution,
    classify_r325,
    development_allows_holdout,
)


def _contract() -> dict[str, object]:
    return {
        "gates": {
            "development_mean_output_energy_ratio_maximum": 0.98,
            "development_worst_output_energy_ratio_maximum": 1.0,
            "holdout_mean_output_energy_ratio_maximum": 0.98,
            "holdout_worst_output_energy_ratio_maximum": 1.0,
            "retained_to_deleted_mean_ratio_maximum": 0.98,
        }
    }


def _passing_payload() -> dict[str, object]:
    return {
        "validity_guards": {
            "sealed_source_identity": True,
            "no_r321_outcome_access": True,
            "comparison_contract": True,
            "case_contract": True,
            "deterministic_replay": True,
        },
        "holdout_accessed": True,
        "arms": {
            "retained_cross": {
                "formulation_feasible": True,
                "development": {
                    "valid": True,
                    "mean_output_energy_ratio": 0.90,
                    "worst_output_energy_ratio": 0.99,
                },
                "holdout": {
                    "valid": True,
                    "mean_output_energy_ratio": 0.90,
                    "worst_output_energy_ratio": 0.98,
                },
            },
            "cross_deleted": {
                "formulation_feasible": True,
                "development": {
                    "valid": True,
                    "mean_output_energy_ratio": 0.95,
                    "worst_output_energy_ratio": 0.99,
                },
                "holdout": {
                    "valid": True,
                    "mean_output_energy_ratio": 0.94,
                    "worst_output_energy_ratio": 0.99,
                },
            },
        },
    }


def test_r325_pass_requires_absolute_and_retained_block_value_gates() -> None:
    assert (
        classify_r325(_passing_payload(), _contract())
        == "CONSTRAINED-HORIZON-PASS"
    )


def test_r325_integrity_failure_has_precedence() -> None:
    payload = _passing_payload()
    payload["validity_guards"]["no_r321_outcome_access"] = False  # type: ignore[index]

    assert classify_r325(payload, _contract()) == "INVALID-CONSTRAINED-HORIZON"


def test_r325_development_no_go_stops_before_holdout() -> None:
    payload = _passing_payload()
    payload["holdout_accessed"] = False
    retained = payload["arms"]["retained_cross"]  # type: ignore[index]
    retained["development"]["worst_output_energy_ratio"] = 1.01  # type: ignore[index]
    retained.pop("holdout")
    payload["arms"]["cross_deleted"].pop("holdout")  # type: ignore[index]

    assert classify_r325(payload, _contract()) == "DEVELOPMENT-NO-GO"


def test_r325_retained_block_no_value_preserves_controller_success() -> None:
    payload = _passing_payload()
    retained = payload["arms"]["retained_cross"]["holdout"]  # type: ignore[index]
    retained["mean_output_energy_ratio"] = 0.93  # type: ignore[index]

    assert classify_r325(payload, _contract()) == "RETAINED-BLOCK-NO-VALUE"


def test_r325_development_solver_failure_is_formulation_infeasible() -> None:
    contract = {
        **_contract(),
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "tuning_candidate_count": 0,
        "development_case_count": 1,
        "holdout_case_count": 1,
        "solver": {"feasibility_tolerance": 1.0e-8},
        "comparison_identifiability": {"decision": "ALLOW"},
    }
    success = {
        "solver_failed": False,
        "execution_error": False,
        "constraint_violation_count": 0,
        "maximum_constraint_residual": 0.0,
        "maximum_solver_iterations": 3,
        "output_energy_ratio": 0.9,
    }
    failed = {
        "solver_failed": True,
        "execution_error": False,
        "error": "iteration budget exhausted",
    }
    execution = {
        "created_utc": "2026-08-03T00:00:00+00:00",
        "seal_sha256": "a" * 64,
        "sealed_source_identity": True,
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "holdout_accessed": False,
        "deterministic_execution_replay": True,
        "arms": {
            "retained_cross": {
                "observer_synthesis_succeeded": True,
                "rows": {"development": [failed]},
            },
            "cross_deleted": {
                "observer_synthesis_succeeded": True,
                "rows": {"development": [success]},
            },
        },
    }

    assert development_allows_holdout(execution, contract) is False
    analysis = analyse_r325_execution(execution, contract, analysis_replay=True)
    assert analysis["classification"] == "FORMULATION-INFEASIBLE"
