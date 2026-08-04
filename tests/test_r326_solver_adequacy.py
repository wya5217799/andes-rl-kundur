"""Formal classification tests for the prospective R326 solver repair."""

from __future__ import annotations

from copy import deepcopy

from probes.r326_solver_adequacy import (
    analyse_r326_execution,
    classify_r326,
    solver_development_allows_holdout,
)


def _contract() -> dict[str, object]:
    return {
        "round": "R326",
        "question": "Q-0080",
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "tuning_candidate_count": 0,
        "development_case_count": 1,
        "holdout_case_count": 1,
        "solver": {
            "name": "osqp",
            "feasibility_tolerance": 1.0e-8,
        },
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


def _row(*, ratio: float, reference: bool) -> dict[str, object]:
    row: dict[str, object] = {
        "solver_failed": False,
        "execution_error": False,
        "constraint_violation_count": 0,
        "maximum_constraint_residual": 1.0e-10,
        "maximum_primal_residual_ratio": 0.5,
        "maximum_dual_residual_ratio": 0.6,
        "maximum_solver_iterations": 100,
        "output_energy_ratio": ratio,
    }
    if reference:
        row.update(
            {
                "reference_completed_steps": 1,
                "reference_status_matches_r325": True,
                "prefix_samples": [
                    {
                        "step": 0,
                        "node_action_max_abs_error": 1.0e-8,
                        "coordinate_action_max_abs_error": 1.0e-8,
                        "predicted_output_max_abs_error": 1.0e-8,
                    }
                ],
            }
        )
    return row


def _payload() -> dict[str, object]:
    return {
        "created_utc": "2026-08-04T00:00:00+00:00",
        "seal_sha256": "a" * 64,
        "execution_sha256": "b" * 64,
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
        "holdout_accessed": True,
        "arms": {
            "retained_cross": {
                "observer_synthesis_succeeded": True,
                "rows": {
                    "development": [_row(ratio=0.90, reference=True)],
                    "holdout": [_row(ratio=0.90, reference=False)],
                },
            },
            "cross_deleted": {
                "observer_synthesis_succeeded": True,
                "rows": {
                    "development": [_row(ratio=0.95, reference=True)],
                    "holdout": [_row(ratio=0.94, reference=False)],
                },
            },
        },
    }


def test_r326_pass_requires_solver_repair_and_unchanged_controller_gates() -> None:
    payload = _payload()
    contract = _contract()

    assert solver_development_allows_holdout(payload, contract)
    analysis = analyse_r326_execution(payload, contract, analysis_replay=True)
    assert analysis["solver_repair_passed"] is True
    assert classify_r326(analysis, contract) == "CONSTRAINED-HORIZON-PASS"


def test_r326_prefix_disagreement_blocks_holdout() -> None:
    payload = _payload()
    payload["holdout_accessed"] = False
    for arm in payload["arms"].values():  # type: ignore[union-attr]
        arm["rows"].pop("holdout")
    sample = payload["arms"]["retained_cross"]["rows"]["development"][0][  # type: ignore[index]
        "prefix_samples"
    ][0]
    sample["node_action_max_abs_error"] = 3.0e-5

    assert solver_development_allows_holdout(payload, _contract()) is False
    analysis = analyse_r326_execution(payload, _contract(), analysis_replay=True)
    assert classify_r326(analysis, _contract()) == "SOLVER-REPAIR-NO-GO"


def test_r326_controller_development_failure_is_not_solver_failure() -> None:
    payload = _payload()
    payload["holdout_accessed"] = False
    for arm in payload["arms"].values():  # type: ignore[union-attr]
        arm["rows"].pop("holdout")
    payload["arms"]["retained_cross"]["rows"]["development"][0][  # type: ignore[index]
        "output_energy_ratio"
    ] = 1.01

    analysis = analyse_r326_execution(payload, _contract(), analysis_replay=True)
    assert analysis["solver_repair_passed"] is True
    assert classify_r326(analysis, _contract()) == "DEVELOPMENT-NO-GO"


def test_r326_holdout_residual_failure_is_fresh_holdout_no_go() -> None:
    payload = deepcopy(_payload())
    payload["arms"]["retained_cross"]["rows"]["holdout"][0][  # type: ignore[index]
        "maximum_dual_residual_ratio"
    ] = 1.01

    analysis = analyse_r326_execution(payload, _contract(), analysis_replay=True)
    assert classify_r326(analysis, _contract()) == "FRESH-HOLDOUT-NO-GO"
