from __future__ import annotations

from andes_rl_kundur.evaluation.gate_b4_deterministic import (
    CANDIDATE_ARM,
    build_contract,
    controller_spec,
    phase_jobs,
    select_development_candidate,
)


def test_gate_b4_contract_freezes_one_second_order_candidate() -> None:
    contract = build_contract()
    assert contract["round"] == "R381"
    assert contract["filter_order"] == 2
    assert contract["corner_hz"] == 0.05
    assert contract["highpass_alpha"] == 0.9391013674242926
    assert contract["development"]["record_count"] == 30
    assert contract["evaluation"]["record_count"] == 30
    assert [item["arm_id"] for item in contract["distributed_candidates"]] == [
        CANDIDATE_ARM
    ]
    assert len(phase_jobs("development", contract=contract)) == 30

    spec = controller_spec(CANDIDATE_ARM, contract=contract)
    assert spec == {
        "architecture": "distributed_cascaded_hp_damping",
        "kp_n_per_hz": 4.0,
        "ki_n_per_hz_s": 0.8,
        "sync_gain_per_hz": 1.0,
        "consensus_gain_per_s": 0.5,
        "highpass_alpha": 0.9391013674242926,
        "filter_order": 2,
    }


def _summary(*, diff_energy: float, settling: float) -> dict:
    return {
        "guards_pass": True,
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
                    "common_frequency_iae_hz_s": 1.0,
                    "worst_device_peak_abs_hz": 1.0,
                    "max_rocof_hz_per_s": 1.0,
                }
            },
        },
    }


def test_gate_b4_selection_can_select_only_the_registered_candidate() -> None:
    result = select_development_candidate(
        {
            "zero_feedback": _summary(diff_energy=1.2, settling=2.4),
            "local_feasibility_native": _summary(diff_energy=1.0, settling=1.8),
            CANDIDATE_ARM: _summary(diff_energy=0.9, settling=1.4),
        },
        contract=build_contract(),
    )
    assert result["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED"
    assert result["selected_arm_id"] == CANDIDATE_ARM
    assert result["training_authorized"] is False
