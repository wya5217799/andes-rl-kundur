"""Decision tests for the R328 retained-arm estimation diagnosis."""

from __future__ import annotations

from copy import deepcopy

from probes.r328_estimation_cause import analyse_r328_estimation_diagnosis


def _contract() -> dict[str, object]:
    return {
        "development_case_count": 1,
        "gates": {
            "development_mean_output_energy_ratio_maximum": 0.98,
            "development_worst_output_energy_ratio_maximum": 1.0,
        },
        "estimation_diagnosis": {
            "arm": "retained_cross",
            "maximum_constraint_residual": 1.0e-8,
            "maximum_normalized_residual_ratio": 1.0,
            "require_every_case_below_zero_control": True,
            "holdout_access": "forbidden",
            "cross_deleted_oracle": "forbidden-nonidentifiable-state-basis",
        },
    }


def _parent() -> dict[str, object]:
    return {
        "classification": "DEVELOPMENT-NO-GO",
        "combined_solver_repair_passed": True,
        "holdout_accessed": False,
        "arms": {
            "retained_cross": {
                "development": {
                    "valid": True,
                    "case_count": 1,
                    "mean_output_energy_ratio": 9.0,
                    "worst_output_energy_ratio": 9.0,
                }
            }
        },
    }


def _execution(ratio: float = 0.1) -> dict[str, object]:
    return {
        "sealed_source_identity": True,
        "parent_identity": True,
        "state_coordinate_identity": True,
        "deterministic_execution_replay": True,
        "holdout_accessed": False,
        "cross_deleted_oracle_accessed": False,
        "rows": [
            {
                "arm": "retained_cross",
                "case": "HS0/triangle/common/positive",
                "solver_failed": False,
                "execution_error": False,
                "constraint_violation_count": 0,
                "maximum_constraint_residual": 1.0e-10,
                "maximum_primal_residual_ratio": 0.5,
                "maximum_dual_residual_ratio": 0.6,
                "exact_state_construction_error": 0.0,
                "output_energy_ratio": ratio,
            }
        ],
    }


def test_exact_state_rescue_identifies_estimation_layer() -> None:
    result = analyse_r328_estimation_diagnosis(
        _execution(), _contract(), _parent(), analysis_replay=True
    )

    assert result["classification"] == "ESTIMATION-LAYER-CAUSE"
    assert result["exact_state"]["mean_output_energy_ratio"] == 0.1
    assert result["holdout_accessed"] is False


def test_valid_exact_state_failure_is_not_dominant() -> None:
    result = analyse_r328_estimation_diagnosis(
        _execution(1.1), _contract(), _parent(), analysis_replay=True
    )

    assert result["classification"] == "ESTIMATION-NOT-DOMINANT"


def test_cross_deleted_oracle_access_is_invalid() -> None:
    execution = _execution()
    execution["cross_deleted_oracle_accessed"] = True

    result = analyse_r328_estimation_diagnosis(
        execution, _contract(), _parent(), analysis_replay=True
    )

    assert result["classification"] == "INVALID-ESTIMATION-DIAGNOSIS"


def test_parent_must_be_valid_failed_output_feedback() -> None:
    parent = deepcopy(_parent())
    parent["arms"]["retained_cross"]["development"]["valid"] = False  # type: ignore[index]

    result = analyse_r328_estimation_diagnosis(
        _execution(), _contract(), parent, analysis_replay=True
    )

    assert result["classification"] == "INVALID-ESTIMATION-DIAGNOSIS"
