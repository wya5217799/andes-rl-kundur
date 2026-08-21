"""Unit tests for the R393 PPVSM1 object gate classifier.

Pure synthetic records; no ANDES runtime import.
"""

from __future__ import annotations

import pytest

from andes_rl_kundur.evaluation.ppvsm1_object_gate import (
    PPVSM1_PARAMETER_CARD,
    build_ppvsm1_object_contract,
    classify_ppvsm1_object_record,
    payload_sha256,
)


def _eigenvalues(rows):
    return [{"real": r, "imag": i} for r, i in rows]


def _record(contract, *, spectrum=None, drift_ok=True, init_fail=False,
            eig_fail=False, extra_neutral=False, positive_real=False,
            bad_readback=False):
    eigenvalues = spectrum
    if eigenvalues is None:
        if positive_real:
            rows = [(1.0, 0.0)] + [(-1.0 - 0.1 * k, 0.3) for k in range(17)]
        elif extra_neutral:
            rows = [(0.0, 0.0), (0.0, 0.0)] + [(-1.0 - 0.1 * k, 0.3) for k in range(16)]
        else:
            rows = [(0.0, 0.0)] + [(-1.0 - 0.1 * k, 0.3) for k in range(17)]
        eigenvalues = [{"real": r, "imag": i} for r, i in rows]
    n = len(eigenvalues)
    drift = 0.0 if drift_ok else 1e-3
    init = [1.0] + [1.0 + drift] * 6
    record = {
        "schema_version": 1,
        "round": "R393",
        "question": "Q-0110",
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "scientific_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_attempted": True,
        "physical_trajectory_executed": True,
        "trajectory_count": 1,
        "source": {"andes_version": "2.0.0", "xlsx_case_sha256": "x",
                   "json_case_sha256": "j", "derived_case_sha256": "d",
                   "ppvsm1_model_sha256": "m", "eig_source_sha256": "e"},
        "inventory": {
            "network": contract["network_inventory"],
            "forbidden_model_counts": {"GENROU": 0, "REGF2": 0,
                                     "PLL2": 0},
            "forbidden_dae_names": [],
            "ppvsm1_count": 2,
            "ppvsm1_buses": [1, 2],
            "ppvsm1_mapping_ok": True,
            "input_parameter_cards_match": not bad_readback,
            "runtime_parameter_cards_match": True,
        },
        "references": {
            "checked": True,
            "phase": "post_init",
            "rows": [{"abs_deviation": 0.0}, {"abs_deviation": 0.0}],
        },
        "initialization_diagnostics": {
            "captured": True, "equation_count": 75, "bad_combined_indices": [],
            "residual_count": 0, "residuals": [], "clamped_limits": [],
        },
        "solver": {
            "setup_completed": True, "pflow_converged": True,
            "tds_initialized": not init_fail, "tds_test_ok": not init_fail,
            "eig_return": not eig_fail, "tds_converged": True,
            "terminal_time_seconds": 0.2, "tds_tolerance": 1e-4,
            "time_before_eig": 0.0, "time_after_eig": 0.0,
            "state_max_abs_delta": 0.0,
        },
        "finite_guard": {"checked": True, "dae_finite": True,
                         "jacobian_finite": True, "state_matrix_finite": True},
        "trace": {
            "checked": True,
            "times": [0.0, 1 / 30, 2 / 30, 3 / 30, 4 / 30, 5 / 30, 6 / 30],
            "bus_v": [{"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 1.0,
                       "6": 1.0, "7": 1.0, "8": 1.0, "9": 1.0, "10": 1.0}]
            + [{"1": 1.0, "2": 1.0, "3": 1.0, "4": 1.0, "5": 1.0,
                "6": 1.0, "7": 1.0, "8": 1.0, "9": 1.0, "10": 1.0}] * 6,
            "devices": {
                "PPVSM1_1": {
                    "Pe": init, "Qe": init, "Id": init, "Iq": init,
                    "virtual_frequency": init,
                },
                "PPVSM1_2": {
                    "Pe": init, "Qe": init, "Id": init, "Iq": init,
                    "virtual_frequency": init,
                },
            },
        },
        "spectrum": {
            "captured": True,
            "state_count": n,
            "eigenvalues": eigenvalues,
        },
    }
    return record


def test_contract_freezes_two_unit_object() -> None:
    contract = build_ppvsm1_object_contract()
    assert contract["round"] == "R393"
    assert contract["expected_mapping"] == [
        {"idx": "PPVSM1_1", "bus": 1, "gen": 1},
        {"idx": "PPVSM1_2", "bus": 2, "gen": 2},
    ]
    assert contract["parameter_card"]["mf"] == 0.15
    assert contract["parameter_card"]["Rv"] == 0.05
    assert contract["runtime_parameter_card"]["Pmax"] == 9.0
    assert contract["drift_abs_limit_system_pu"] == 2e-4
    assert contract["allowed_zero_modes"] == 1


def test_clean_pass_yields_object_pass() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(_record(contract), contract)
    assert result["classification"] == "PPVSM1-OBJECT-PASS"
    assert result["checks"]["drift"] is True
    assert result["checks"]["positive_real"] is True
    assert result["checks"]["neutral"] is True


def test_init_failure_yields_object_init_stop() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(
        _record(contract, init_fail=True), contract
    )
    assert result["classification"] == "STOP-PPVSM1-OBJECT-INIT"


def test_eig_failure_is_invalid() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(
        _record(contract, eig_fail=True), contract
    )
    assert result["classification"] == "ANALYSIS-INVALID"


def test_drift_breach_yields_object_init_stop() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(
        _record(contract, drift_ok=False), contract
    )
    assert result["classification"] == "STOP-PPVSM1-OBJECT-INIT"
    assert result["checks"]["drift"] is False


def test_positive_real_root_yields_positive_real_stop() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(
        _record(contract, positive_real=True), contract
    )
    assert result["classification"] == "STOP-PPVSM1-POSITIVE-REAL"
    assert result["spectrum_summary"]["positive_real_count"] == 1


def test_extra_neutral_mode_yields_neutral_stop() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(
        _record(contract, extra_neutral=True), contract
    )
    assert result["classification"] == "STOP-PPVSM1-NEUTRAL-DEGENERACY"
    assert result["spectrum_summary"]["near_zero_count"] == 2


def test_bad_card_readback_is_invalid() -> None:
    contract = build_ppvsm1_object_contract()
    result = classify_ppvsm1_object_record(
        _record(contract, bad_readback=True), contract
    )
    assert result["classification"] == "ANALYSIS-INVALID"


def test_schema_mismatch_is_invalid() -> None:
    contract = build_ppvsm1_object_contract()
    record = _record(contract)
    record["arms"] = None
    record["trajectory_count"] = 0
    result = classify_ppvsm1_object_record(record, contract)
    assert result["classification"] == "ANALYSIS-INVALID"
