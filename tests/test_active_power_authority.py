import platform

import pytest

from andes_rl_kundur.evaluation.active_power_authority import (
    classify_active_power_authority,
    run_active_power_scenario,
    summarise_active_power_trace,
)

IS_WSL = platform.system() == "Linux" and "microsoft" in platform.release().lower()


def test_active_power_summary_uses_registered_final_window_and_energy_fields():
    common_delta_hz = [1.0, 0.5, 0.2, 0.1]
    commands = [0.0, 0.1, 0.1, 0.0]
    soc = [0.50, 0.4999, 0.4998, 0.4998]
    traces = []
    for index, (delta_hz, command, step_soc) in enumerate(
        zip(common_delta_hz, commands, soc, strict=True)
    ):
        traces.append(
            {
                "t": 0.2 * (index + 1),
                "delta_f_physical_hz": [delta_hz, delta_hz],
                "action_norm": [[0.0, 0.0], [0.0, 0.0]],
                "bess_requested_power_system_pu": [command, command],
                "bess_commanded_power_system_pu": [command, command],
                "bess_actual_power_system_pu": [command, command],
                "bess_soc": [step_soc, step_soc],
                "bess_saturation_reasons": [[], []],
                "bess_charge_energy_mwh_total": [0.0, 0.0],
                "bess_discharge_energy_mwh_total": [0.1 * index, 0.1 * index],
                "bess_constraint_violations": [],
            }
        )
    record = {
        "tds_failed": False,
        "completed": True,
        "frequency_reporting_basis": "legacy_control_hz",
        "andes_nominal_frequency_hz": 60.0,
        "n_steps": 4,
        "traces": traces,
    }

    summary = summarise_active_power_trace(record, final_window_steps=2)

    assert summary["vsg_mean_iae_hz_s"] == pytest.approx(0.36)
    assert summary["final_window_common_abs_mean_hz"] == pytest.approx(0.15)
    assert summary["terminal_common_abs_hz"] == pytest.approx(0.1)
    assert summary["bess_command_l1_device_s"] == pytest.approx(0.04)
    assert summary["bess_command_total_variation"] == pytest.approx(0.2)
    assert summary["bess_min_soc"] == pytest.approx(0.4998)
    assert summary["bess_discharge_energy_mwh_total"] == pytest.approx(0.6)
    assert summary["bess_constraint_violation_count"] == 0


@pytest.mark.skipif(not IS_WSL, reason="real ANDES integration runs only in WSL")
def test_active_power_runner_produces_a_complete_auditable_pi_smoke_trace():
    record = run_active_power_scenario(
        "pi_smoke",
        {"PQ_Bus14": 1.5},
        controller_name="droop_pi",
        seed=42,
        steps=10,
    )

    assert record["completed"] is True
    assert record["tds_failed"] is False
    assert record["n_steps"] == 10
    assert record["controller"] == "droop_pi"
    assert any(
        power > 0.0
        for power in record["traces"][-1]["bess_commanded_power_system_pu"]
    )
    summary = summarise_active_power_trace(record, final_window_steps=5)
    assert summary["bess_constraint_violation_count"] == 0


def test_authority_gate_requires_joint_materiality_uncertainty_and_guards():
    controller_summaries = {
        "zero_support": {
            "complete_count": 20,
            "failure_count": 0,
            "constraint_violation_count": 0,
            "means": {
                "normalized_sync_loss_hz2": 1.0,
                "worst_bus_peak_abs_hz": 1.0,
                "max_abs_rocof_hz_s": 1.0,
            },
        },
        "droop_pi": {
            "complete_count": 20,
            "failure_count": 0,
            "constraint_violation_count": 0,
            "means": {
                "normalized_sync_loss_hz2": 1.03,
                "worst_bus_peak_abs_hz": 1.04,
                "max_abs_rocof_hz_s": 1.02,
            },
        },
    }
    primary_contrast = {
        "endpoints": {
            "vsg_mean_iae_hz_s": {
                "ratio_of_means_percent": {
                    "point": -3.0,
                    "percentile_95_interval": [-4.0, -1.0],
                }
            },
            "final_window_common_abs_mean_hz": {
                "ratio_of_means_percent": {
                    "point": -2.5,
                    "percentile_95_interval": [-3.5, -0.5],
                }
            },
        }
    }

    decision = classify_active_power_authority(
        controller_summaries=controller_summaries,
        primary_contrast=primary_contrast,
        total_scenarios=20,
        provenance_hashes_match=True,
    )

    assert decision["classification"] == "AUTHORITY-POSITIVE"
    assert all(decision["guards"].values())


def test_authority_gate_is_invalid_when_the_matched_baseline_cannot_complete():
    controller_summaries = {
        "zero_support": {
            "complete_count": 19,
            "failure_count": 1,
            "constraint_violation_count": 0,
            "means": {
                "normalized_sync_loss_hz2": 1.0,
                "worst_bus_peak_abs_hz": 1.0,
                "max_abs_rocof_hz_s": 1.0,
            },
        },
        "droop_pi": {
            "complete_count": 19,
            "failure_count": 1,
            "constraint_violation_count": 0,
            "means": {
                "normalized_sync_loss_hz2": 1.0,
                "worst_bus_peak_abs_hz": 1.0,
                "max_abs_rocof_hz_s": 1.0,
            },
        },
    }

    decision = classify_active_power_authority(
        controller_summaries=controller_summaries,
        primary_contrast=None,
        total_scenarios=20,
        provenance_hashes_match=True,
    )

    assert decision["classification"] == "INVALID"
    assert decision["guards"]["complete_primary_pairs"] is False
