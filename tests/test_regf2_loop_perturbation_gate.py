"""Unit tests for the R392 REGF2 loop-perturbation classifier.

Pure synthetic records; no ANDES runtime import. These tests lock the frozen
bank, prediction table, movement thresholds, and every classification branch.
"""

from __future__ import annotations

import pytest

from andes_rl_kundur.evaluation.regf2_loop_perturbation_gate import (
    ARMS,
    CARD_DEFAULTS,
    build_regf2_loop_perturbation_contract,
    classify_regf2_loop_perturbation_record,
    expected_perturbation_value,
    payload_sha256,
)

LEADING = 46.41533383454654
SECOND = 4.606789511264594


def _eigenvalues(leading: float, second: float, count: int = 64) -> list[dict]:
    values = [
        {"real": leading, "imag": 0.0},
        {"real": second, "imag": 0.0},
    ]
    values += [
        {"real": -1.0 - 0.01 * index, "imag": 0.5}
        for index in range(count - 2)
    ]
    return values


def _arm(
    name: str,
    leading: float,
    second: float,
    *,
    init_stop: str | None = None,
    bad_readback: bool = False,
    bad_guard: bool = False,
) -> dict:
    spec = next(arm for arm in ARMS if arm["name"] == name)
    perturbation_spec = spec["perturbation"]
    if perturbation_spec is None:
        perturbation = {
            "param": None,
            "factor": None,
            "expected_value": None,
            "readback": [],
            "applied": False,
        }
    else:
        expected = expected_perturbation_value(perturbation_spec, CARD_DEFAULTS)
        readback = (
            [expected + 1.0] * 4 if bad_readback else [expected] * 4
        )
        perturbation = {
            "param": perturbation_spec["param"],
            "factor": perturbation_spec.get("factor"),
            "expected_value": expected,
            "readback": readback,
            "applied": True,
        }
    return {
        "name": name,
        "tds_tolerance": 1.0e-4,
        "execution_error": None,
        "scientific_error": init_stop,
        "trajectory_attempted": False,
        "physical_trajectory_executed": False,
        "trajectory_count": 0,
        "perturbation": perturbation,
        "solver": {
            "setup_completed": True,
            "pflow_converged": True,
            "tds_initialized": True,
            "tds_test_ok": True,
            "eig_return": True,
            "system_exit_code": 0,
            "actual_tds_tolerance": 1.0e-4,
            "time_before_eig": 0.0,
            "time_after_eig": 0.0,
            "state_max_abs_delta": 0.0,
        },
        "finite_guard": {
            "checked": True,
            "dae_finite": not bad_guard,
            "jacobian_finite": True,
            "state_matrix_finite": True,
        },
        "equilibrium_snapshot": {
            "captured": True,
            "before": {"time": 0.0},
            "after": {"time": 0.0},
        },
        "initialization_diagnostics": {
            "captured": True,
            "residual_count": 0,
            "clamped_limits": [],
        },
        "matrix": {
            "captured": True,
            "state_names": [f"state_{index}" for index in range(64)],
            "andes_eigenvalues": _eigenvalues(leading, second),
        },
    }


def _record(contract: dict, arms: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "round": "R392",
        "question": "Q-0109",
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "post_init_action_executed": False,
        "trajectory_count": 0,
        "arms": arms,
    }


def _full_bank(
    *,
    mf1: float = LEADING,
    mf2: float = LEADING,
    tpm: float = LEADING,
    tr: float = LEADING,
    kiv1: float = LEADING,
    kiv2: float = LEADING,
    sn: float = LEADING,
    s_mf1: float = SECOND,
    s_mf2: float = SECOND,
    s_tpm: float = SECOND,
    s_tr: float = SECOND,
    s_kiv1: float = SECOND,
    s_kiv2: float = SECOND,
    s_sn: float = SECOND,
) -> list[dict]:
    return [
        _arm("A0_reference", LEADING, SECOND),
        _arm("H1a_mf_x4", mf1, s_mf1),
        _arm("H1b_mf_div4", mf2, s_mf2),
        _arm("H2a_Tpm_x10", tpm, s_tpm),
        _arm("H2b_Tr_x10", tr, s_tr),
        _arm("H3a_KIv_x4", kiv1, s_kiv1),
        _arm("H3b_KIv_div4", kiv2, s_kiv2),
        _arm("H4_Sn_100", sn, s_sn),
    ]


def test_contract_freezes_bank_thresholds_and_parents() -> None:
    contract = build_regf2_loop_perturbation_contract()
    assert contract["round"] == "R392"
    assert contract["question"] == "Q-0109"
    assert contract["parent_round"] == "R391"
    assert [arm["name"] for arm in contract["arms"]] == [
        arm["name"] for arm in ARMS
    ]
    assert contract["card_defaults"]["mf"] == 0.15
    assert contract["card_defaults"]["KIv"] == 10.0
    assert contract["card_defaults"]["Sn"] == 900.0
    assert contract["thresholds"]["movement_relative_threshold"] == 0.10
    assert contract["thresholds"]["reduced_state_count"] == 64
    assert contract["r391_reference_roots"]["leading"]["real"] == LEADING
    assert "object_contract" in contract
    assert "registered_state_variables" in contract
    assert "sparse_adapter_runtime" in contract


def test_expected_perturbation_value_factor_and_absolute() -> None:
    assert expected_perturbation_value(
        {"param": "mf", "factor": 4.0}, CARD_DEFAULTS
    ) == 0.6
    assert expected_perturbation_value(
        {"param": "KIv", "factor": 0.25}, CARD_DEFAULTS
    ) == 2.5
    assert expected_perturbation_value(
        {"param": "Sn", "value": 100.0}, CARD_DEFAULTS
    ) == 100.0
    assert expected_perturbation_value(None, CARD_DEFAULTS) is None
    with pytest.raises(ValueError):
        expected_perturbation_value(
            {"param": "not_a_param", "factor": 2.0}, CARD_DEFAULTS
        )


def test_all_predictions_match_yields_mechanism_mixed() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank(
        mf1=20.0, mf2=35.0, tpm=10.0, tr=12.0,
        kiv1=LEADING, kiv2=LEADING,
        s_kiv1=1.0, s_kiv2=1.5,
        sn=5.0, s_sn=0.5,
    )
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "MECHANISM-MIXED"
    assert result["checks"]["reference_reproduction"] is True
    assert all(
        result["attribution"][family]["supported"]
        for family in result["attribution"]
    )


def test_only_vsm_inertia_moves_yields_mechanism_vsm_inertia() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank(mf1=20.0, mf2=35.0)
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "MECHANISM-VSM-INERTIA"
    assert result["attribution"]["VSM-INERTIA"]["lambda1_moved"] is True
    assert result["attribution"]["VOLTAGE-OUTER-PI"]["lambda2_moved"] is False


def test_no_movement_yields_mechanism_none_isolated() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank()
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "MECHANISM-NONE-ISOLATED"


def test_unpredicted_movement_yields_mechanism_unpredicted() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank(kiv1=20.0, kiv2=25.0)
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "MECHANISM-UNPREDICTED"


def test_reference_root_mismatch_yields_platform_stop() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank()
    arms[0] = _arm("A0_reference", 30.0, SECOND)
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "STOP-REGF2-PERTURBATION-PLATFORM"
    assert result["checks"]["reference_reproduction"] is False


def test_reference_guard_failure_yields_platform_stop() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank()
    arms[0] = _arm("A0_reference", LEADING, SECOND, bad_guard=True)
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "STOP-REGF2-PERTURBATION-PLATFORM"


def test_perturbation_readback_mismatch_yields_analysis_invalid() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank()
    arms[1] = _arm("H1a_mf_x4", LEADING, SECOND, bad_readback=True)
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "ANALYSIS-INVALID"


def test_typed_arm_stop_contributes_no_attribution() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank()
    arms[1] = _arm("H1a_mf_x4", LEADING, SECOND, init_stop="TDS initialization failed")
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "MECHANISM-NONE-ISOLATED"
    assert result["arm_outcomes"][1]["arm_stop"] == "TDS initialization failed"
    assert result["attribution"]["VSM-INERTIA"]["supported"] is False
    assert result["attribution"]["VSM-INERTIA"]["note"] is not None


def test_reference_typed_stop_yields_platform_stop() -> None:
    contract = build_regf2_loop_perturbation_contract()
    arms = _full_bank()
    arms[0] = _arm("A0_reference", LEADING, SECOND, init_stop="PFlow did not converge")
    result = classify_regf2_loop_perturbation_record(_record(contract, arms), contract)
    assert result["classification"] == "STOP-REGF2-PERTURBATION-PLATFORM"


def test_unknown_schema_is_analysis_invalid() -> None:
    contract = build_regf2_loop_perturbation_contract()
    record = _record(contract, _full_bank())
    record["arms"] = record["arms"][:-1]
    result = classify_regf2_loop_perturbation_record(record, contract)
    assert result["classification"] == "ANALYSIS-INVALID"
