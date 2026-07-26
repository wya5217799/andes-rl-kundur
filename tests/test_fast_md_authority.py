import platform

import numpy as np
import pytest

from andes_rl_kundur.evaluation.fast_md_authority import (
    FAST_ENDPOINTS,
    FrozenCommonInertiaPulse,
    classify_fast_md_authority,
    frozen_fast_md_contract,
    run_fast_md_scenario,
    summarise_fast_md_trace,
)

IS_WSL = platform.system() == "Linux" and "microsoft" in platform.release().lower()


def test_frozen_common_inertia_pulse_has_exact_registered_schedule_and_budget():
    contract = frozen_fast_md_contract()
    controller = FrozenCommonInertiaPulse()
    obs = {index: np.zeros(1, dtype=np.float32) for index in range(4)}

    actions = [controller(step, obs, 4) for step in range(17)]

    for step in range(15):
        assert all(action[0] == pytest.approx(0.25) for action in actions[step].values())
        assert all(action[1] == pytest.approx(0.0) for action in actions[step].values())
    for step in (15, 16):
        assert all(np.array_equal(action, np.zeros(2)) for action in actions[step].values())

    assert contract["physical"]["pulse_m"] == pytest.approx(350.0)
    assert contract["budgets"]["action_l1_agent_s"] == pytest.approx(0.75)
    assert contract["budgets"]["in_trace_total_variation"] == pytest.approx(0.25)
    assert contract["budgets"]["boundary_aware_total_variation"] == pytest.approx(0.50)


def test_fast_md_summary_reports_inter_area_and_boundary_aware_action_endpoints():
    traces = []
    area_modes = [0.4, 0.2, 0.1, 0.0]
    for step, mode in enumerate(area_modes):
        common = 0.05
        left = common + mode / 2.0
        right = common - mode / 2.0
        action = 0.25 if step < 3 else 0.0
        traces.append(
            {
                "t": 0.2 * (step + 1),
                "delta_f_physical_hz": [left, left, right, right],
                "action_norm": [[action, 0.0]] * 4,
                "M_es": [200.0 + 600.0 * action] * 4,
                "D_es": [100.0] * 4,
                "bess_requested_power_system_pu": [0.0] * 4,
                "bess_commanded_power_system_pu": [0.0] * 4,
                "bess_actual_power_system_pu": [0.0] * 4,
                "bess_soc": [0.5] * 4,
                "bess_saturation_reasons": [[], [], [], []],
                "bess_charge_energy_mwh_total": [0.0] * 4,
                "bess_discharge_energy_mwh_total": [0.0] * 4,
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

    summary = summarise_fast_md_trace(
        record,
        final_window_steps=2,
        fast_window_steps=3,
    )

    assert summary["fast_inter_area_iae_hz_s"] == pytest.approx(0.14)
    assert summary["fast_inter_area_peak_abs_hz"] == pytest.approx(0.4)
    assert summary["action_l1_agent_s"] == pytest.approx(0.15)
    assert summary["action_total_variation"] == pytest.approx(0.25)
    assert summary["action_boundary_aware_total_variation"] == pytest.approx(0.50)
    assert summary["max_abs_action_slew_per_step"] == pytest.approx(0.25)
    assert summary["max_abs_m_action_norm"] == pytest.approx(0.25)
    assert summary["max_abs_d_action_norm"] == pytest.approx(0.0)
    assert summary["min_m"] == pytest.approx(200.0)
    assert summary["max_m"] == pytest.approx(350.0)
    assert summary["min_d"] == pytest.approx(100.0)
    assert summary["max_d"] == pytest.approx(100.0)


def _contrast(
    *,
    cleared: set[str],
    worsened: set[str] = frozenset(),
    slow_ok: bool = True,
):
    endpoints = {}
    for endpoint in FAST_ENDPOINTS:
        point = -3.0 if endpoint in cleared else 1.0
        upper = -0.5 if endpoint in cleared else 2.0
        if endpoint in worsened:
            point, upper = 6.0, 7.0
        endpoints[endpoint] = {
            "ratio_of_means_percent": {
                "point": point,
                "percentile_95_interval": [-4.0, upper],
            }
        }
    for endpoint in (
        "vsg_mean_iae_hz_s",
        "final_window_common_abs_mean_hz",
    ):
        point, upper = (-1.0, 1.0) if slow_ok else (3.0, 4.0)
        endpoints[endpoint] = {
            "ratio_of_means_percent": {
                "point": point,
                "percentile_95_interval": [-2.0, upper],
            }
        }
    return {"endpoints": endpoints}


def _summaries():
    return {
        "slow_droop_pi_fixed_md": {
            "complete_count": 24,
            "failure_count": 0,
            "constraint_violation_count": 0,
        },
        "slow_droop_pi_plus_common_m_pos": {
            "complete_count": 24,
            "failure_count": 0,
            "constraint_violation_count": 0,
        },
    }


def test_fast_md_gate_requires_common_and_differential_material_endpoints():
    decision = classify_fast_md_authority(
        controller_summaries=_summaries(),
        primary_contrast=_contrast(
            cleared={"max_abs_rocof_hz_s", "fast_inter_area_iae_hz_s"}
        ),
        total_scenarios=24,
        provenance_hashes_match=True,
        action_budget_pass=True,
        storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert decision["classification"] == "FAST-LAYER-POSITIVE"
    assert decision["cleared_fast_endpoint_count"] == 2


def test_fast_md_gate_is_partial_for_only_one_material_fast_endpoint():
    decision = classify_fast_md_authority(
        controller_summaries=_summaries(),
        primary_contrast=_contrast(cleared={"max_abs_rocof_hz_s"}),
        total_scenarios=24,
        provenance_hashes_match=True,
        action_budget_pass=True,
        storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert decision["classification"] == "FAST-LAYER-PARTIAL"


def test_fast_md_gate_rejects_a_material_gain_with_registered_harm():
    decision = classify_fast_md_authority(
        controller_summaries=_summaries(),
        primary_contrast=_contrast(
            cleared={"max_abs_rocof_hz_s"},
            worsened={"normalized_sync_loss_hz2"},
        ),
        total_scenarios=24,
        provenance_hashes_match=True,
        action_budget_pass=True,
        storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert decision["classification"] == "NO-INDEPENDENT-FAST-VALUE"


def test_fast_md_gate_is_invalid_when_action_contract_does_not_match():
    decision = classify_fast_md_authority(
        controller_summaries=_summaries(),
        primary_contrast=_contrast(
            cleared={"max_abs_rocof_hz_s", "fast_inter_area_iae_hz_s"}
        ),
        total_scenarios=24,
        provenance_hashes_match=True,
        action_budget_pass=False,
        storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert decision["classification"] == "INVALID"


@pytest.mark.skipif(not IS_WSL, reason="real ANDES integration runs only in WSL")
def test_fast_md_runner_produces_a_complete_auditable_smoke_trace():
    record = run_fast_md_scenario(
        "fast_md_smoke",
        {"PQ_Bus14": 1.0},
        seed=42,
        steps=20,
    )

    assert record["completed"] is True
    assert record["tds_failed"] is False
    assert record["n_steps"] == 20
    assert record["controller"] == "slow_droop_pi_plus_common_m_pos"
    assert record["traces"][0]["M_es"] == pytest.approx([350.0] * 4)
    assert record["traces"][15]["M_es"] == pytest.approx([200.0] * 4)
    summary = summarise_fast_md_trace(
        record,
        final_window_steps=5,
        fast_window_steps=15,
    )
    assert summary["bess_constraint_violation_count"] == 0
