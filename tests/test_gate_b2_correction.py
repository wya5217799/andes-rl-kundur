from __future__ import annotations

from andes_rl_kundur.evaluation.gate_b2_correction import (
    build_corrected_contract,
    corrected_settling_pass,
    select_development_candidate,
    validate_correction,
)
from andes_rl_kundur.evaluation.gate_b2_deterministic import build_contract


def test_corrected_contract_differs_only_in_round_id() -> None:
    parent = build_contract()
    corrected = build_corrected_contract(parent)
    assert validate_correction(parent, corrected) is True
    assert corrected["round"] == "R378"
    assert corrected["correction_scope"] == ["round", "settling_rule"]
    assert corrected["steps"] == parent["steps"]
    assert corrected["thresholds"] == parent["thresholds"]
    assert corrected["development"] == parent["development"]
    assert corrected["evaluation"] == parent["evaluation"]


def test_validate_rejects_other_differences() -> None:
    parent = build_contract()
    corrected = build_corrected_contract(parent)
    corrected["steps"] = 100
    assert validate_correction(parent, corrected) is False


def test_corrected_settling_pass_allows_equal_settling() -> None:
    assert corrected_settling_pass(1.2, 1.2) is True
    assert corrected_settling_pass(1.4, 1.2) is False
    assert corrected_settling_pass(1.0, 1.2) is True


def _summary_placeholder(
    guards_pass: bool,
    *,
    diff_energy: float = 1.0,
    settling: float = 2.0,
    common_iae: float = 1.0,
) -> dict:
    return {
        "guards_pass": guards_pass,
        "probe": {
            "diagonal_response_energy_hz2_s": 1.0,
            "off_diagonal_response_energy_hz2_s": 1.0,
            "off_diagonal_to_diagonal_energy_ratio": 1.0,
        },
        "disturbance": {
            "mean_differential_frequency_energy_hz2_s": diff_energy,
            "mean_differential_settling_seconds": settling,
            "conditions": {
                "c1": {
                    "differential_frequency_energy_hz2_s": diff_energy,
                    "common_frequency_iae_hz_s": common_iae,
                    "worst_device_peak_abs_hz": 1.0,
                    "max_rocof_hz_per_s": 1.0,
                }
            },
        },
    }


def test_corrected_selection_accepts_equal_settling_candidate() -> None:
    contract = build_corrected_contract(build_contract())
    local = _summary_placeholder(True, diff_energy=1.0, settling=1.2)
    candidate = _summary_placeholder(True, diff_energy=0.96, settling=1.2)
    summaries = {
        "local_feasibility_native": local,
        "zero_feedback": _summary_placeholder(True, diff_energy=1.2, settling=1.7),
        "distributed_hp_damping_ks0p5_kc0p5_alpha0p6": candidate,
        "distributed_hp_damping_ks0p5_kc1_alpha0p6": candidate,
        "distributed_hp_damping_ks1_kc0p5_alpha0p6": candidate,
        "distributed_hp_damping_ks1_kc1_alpha0p6": candidate,
    }
    result = select_development_candidate(summaries, contract=contract)
    assert result["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED"
    assert result["selected_arm_id"] == "distributed_hp_damping_ks0p5_kc0p5_alpha0p6"
    assert result["training_authorized"] is False


def test_corrected_selection_rejects_worse_settling() -> None:
    contract = build_corrected_contract(build_contract())
    local = _summary_placeholder(True, diff_energy=1.0, settling=1.2)
    candidate = _summary_placeholder(True, diff_energy=0.96, settling=1.4)
    summaries = {
        "local_feasibility_native": local,
        "zero_feedback": _summary_placeholder(True),
        "distributed_hp_damping_ks0p5_kc0p5_alpha0p6": candidate,
        "distributed_hp_damping_ks0p5_kc1_alpha0p6": candidate,
        "distributed_hp_damping_ks1_kc0p5_alpha0p6": candidate,
        "distributed_hp_damping_ks1_kc1_alpha0p6": candidate,
    }
    result = select_development_candidate(summaries, contract=contract)
    assert result["classification"] == "STOP-DEVELOPMENT-NO-CANDIDATE"


def test_corrected_selection_requires_guards() -> None:
    contract = build_corrected_contract(build_contract())
    summaries = {
        "local_feasibility_native": _summary_placeholder(False),
    }
    result = select_development_candidate(summaries, contract=contract)
    assert result["classification"] == "ANALYSIS-INVALID"
