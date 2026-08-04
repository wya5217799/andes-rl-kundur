"""Behavior tests for the sealed R330 holdout decision seam."""

from __future__ import annotations

from copy import deepcopy

import pytest
from probes.r330_estimator_holdout import _payload_sha256, analyse_r330_holdout


def _contract() -> dict[str, object]:
    return {
        "holdout_case_names": ["h0"],
        "mismatch_modes": ["nominal"],
        "holdout_case_count": 1,
        "gates": {
            "holdout_mean_output_energy_ratio_maximum": 0.98,
            "holdout_worst_output_energy_ratio_maximum": 1.0,
        },
        "solver": {
            "feasibility_tolerance": 1.0e-8,
            "maximum_iterations": 20_000,
        },
        "limits": {
            "node_power": 0.36,
            "node_ramp": 0.072,
            "minimum_soc": 0.2,
            "maximum_soc": 0.8,
        },
        "holdout": {"maximum_normalized_solver_residual_ratio": 1.0},
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R330",
        "question": "Q-0083",
        "created_utc": "2026-08-04T00:00:00+00:00",
        "seal_sha256": "a" * 64,
        "execution_sha256": "b" * 64,
        "contract_payload_sha256": _payload_sha256(_contract()),
        "sealed_source_identity": True,
        "parent_identity": True,
        "development_identity": True,
        "design_fingerprint_identity": True,
        "mismatch_identity": True,
        "holdout_case_identity": True,
        "limits_identity": True,
        "execution_receipt_identity": True,
        "runtime_dependency_identity": True,
        "estimator_information_boundary": True,
        "deterministic_execution_replay": True,
        "rows": [
            {
                "arm": "retained_cross",
                "phase": "holdout",
                "case": "h0",
                "mismatch": "nominal",
                "solver_failed": False,
                "execution_error": False,
                "native_thread_limit_valid": True,
                "constraint_violation_count": 0,
                "maximum_constraint_residual": 1.0e-10,
                "maximum_primal_residual_ratio": 0.5,
                "maximum_dual_residual_ratio": 0.6,
                "zero_output_energy": 2.0,
                "output_energy": 1.0,
                "output_energy_ratio": 0.5,
                "coordinate_action_energy": 0.1,
                "maximum_node_power": 0.2,
                "maximum_node_ramp": 0.05,
                "minimum_soc": 0.4,
                "maximum_soc": 0.5,
                "maximum_solver_iterations": 100,
            }
        ],
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
    }


def test_valid_holdout_passes_only_when_every_row_beats_zero_control() -> None:
    analysis = analyse_r330_holdout(_payload(), _contract(), analysis_replay=True)

    assert analysis["classification"] == "ESTIMATOR-HOLDOUT-PASS"
    assert analysis["holdout"]["case_count_below_zero_control"] == 1
    assert analysis["holdout"]["mean_output_energy_ratio"] == 0.5


def test_valid_holdout_that_misses_an_absolute_gate_is_no_go() -> None:
    payload = deepcopy(_payload())
    payload["rows"][0]["output_energy"] = 2.02
    payload["rows"][0]["output_energy_ratio"] = 1.01

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "ESTIMATOR-HOLDOUT-NO-GO"


def test_holdout_reports_each_registered_mismatch_without_changing_gate() -> None:
    contract = deepcopy(_contract())
    contract["mismatch_modes"] = ["nominal", "plus_scale"]
    contract["holdout_case_count"] = 2
    payload = deepcopy(_payload())
    payload["contract_payload_sha256"] = _payload_sha256(contract)
    second = deepcopy(payload["rows"][0])
    second["mismatch"] = "plus_scale"
    second["output_energy"] = 1.4
    second["output_energy_ratio"] = 0.7
    payload["rows"].append(second)

    analysis = analyse_r330_holdout(payload, contract, analysis_replay=True)

    assert analysis["classification"] == "ESTIMATOR-HOLDOUT-PASS"
    assert analysis["holdout"]["by_mismatch"]["nominal"]["mean_output_energy_ratio"] == 0.5
    assert analysis["holdout"]["by_mismatch"]["plus_scale"]["mean_output_energy_ratio"] == 0.7


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("estimator_information_boundary", False),
        ("design_fingerprint_identity", False),
        ("deterministic_execution_replay", False),
    ],
)
def test_identity_or_information_guard_failure_is_invalid(field: str, value: object) -> None:
    payload = deepcopy(_payload())
    payload[field] = value

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-ESTIMATOR-HOLDOUT"


def test_missing_registered_row_is_invalid_not_a_performance_no_go() -> None:
    payload = deepcopy(_payload())
    payload["rows"] = []

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-ESTIMATOR-HOLDOUT"


def test_reported_ratio_must_match_finite_nonnegative_energy_evidence() -> None:
    payload = deepcopy(_payload())
    payload["rows"][0]["output_energy_ratio"] = 0.4

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-ESTIMATOR-HOLDOUT"


def test_execution_must_identify_the_exact_sealed_contract() -> None:
    payload = deepcopy(_payload())
    payload["contract_payload_sha256"] = "0" * 64

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-ESTIMATOR-HOLDOUT"


def test_unknown_mismatch_is_invalid_instead_of_crashing() -> None:
    payload = deepcopy(_payload())
    payload["rows"][0]["mismatch"] = "unregistered"

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-ESTIMATOR-HOLDOUT"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("solver_failed", None),
        ("execution_error", None),
        ("maximum_node_power", 0.37),
        ("maximum_node_ramp", 0.08),
        ("minimum_soc", 0.19),
        ("maximum_soc", 0.81),
        ("maximum_solver_iterations", 20_001),
    ],
)
def test_missing_status_or_out_of_limit_trace_is_invalid(field: str, value: object) -> None:
    payload = deepcopy(_payload())
    if value is None:
        payload["rows"][0].pop(field)
    else:
        payload["rows"][0][field] = value

    analysis = analyse_r330_holdout(payload, _contract(), analysis_replay=True)

    assert analysis["classification"] == "INVALID-ESTIMATOR-HOLDOUT"
