from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.icems_residual import (
    audit_icems_policy_action,
    physical_zero_sum_tolerance,
    summarise_icems_policy_trace,
)


def _synthetic_record() -> dict:
    traces = []
    charge = np.zeros(4, dtype=float)
    discharge = np.zeros(4, dtype=float)
    for step in range(20):
        active = step < 15
        q = 0.1 if active else 0.0
        residual = q * np.asarray([1.0, 1.0, -1.0, -1.0])
        common = 0.25 if active else 0.0
        action = np.stack(
            [common + residual, np.zeros(4)],
            axis=1,
        )
        delta_f = np.asarray(
            [0.01, 0.008, -0.006, -0.004],
            dtype=float,
        ) * np.exp(-step / 10.0)
        traces.append(
            {
                "step": step,
                "t": (step + 1) * 0.2,
                "delta_f_physical_hz": delta_f.tolist(),
                "action_norm": action.tolist(),
                "M_es": (200.0 + 600.0 * action[:, 0]).tolist(),
                "D_es": np.full(4, 100.0).tolist(),
                "r278_q": q,
                "r278_residual_action_norm": residual.tolist(),
                "r278_physical_m_residual_sum": 0.0,
                "bess_commanded_power_system_pu": np.zeros(4).tolist(),
                "bess_soc": np.full(4, 0.5).tolist(),
                "bess_saturation_reasons": [[], [], [], []],
                "bess_constraint_violations": [],
                "bess_charge_energy_mwh_total": charge.tolist(),
                "bess_discharge_energy_mwh_total": discharge.tolist(),
            }
        )
    return {
        "completed": True,
        "tds_failed": False,
        "frequency_reporting_basis": "legacy_control_hz",
        "andes_nominal_frequency_hz": 60.0,
        "n_steps": len(traces),
        "traces": traces,
    }


def test_icems_summary_and_action_audit_accept_valid_trace() -> None:
    summary = summarise_icems_policy_trace(
        _synthetic_record(),
        final_window_steps=5,
        fast_window_steps=15,
    )
    audit = audit_icems_policy_action(summary)
    assert summary["r278_max_abs_q"] == 0.1
    assert summary["r278_post_window_max_abs_q"] == 0.0
    assert all(audit.values())


def test_icems_action_audit_rejects_post_window_action() -> None:
    record = _synthetic_record()
    record["traces"][-1]["r278_q"] = 0.01
    summary = summarise_icems_policy_trace(
        record,
        final_window_steps=5,
        fast_window_steps=15,
    )
    audit = audit_icems_policy_action(summary)
    assert audit["post_window_zero"] is False


def test_physical_zero_sum_audit_uses_float32_representation_bound() -> None:
    record = _synthetic_record()
    record["traces"][0]["r278_physical_m_residual_sum"] = 3.0517578125e-5
    summary = summarise_icems_policy_trace(
        record,
        final_window_steps=5,
        fast_window_steps=15,
    )
    assert physical_zero_sum_tolerance() >= 3.0517578125e-5
    assert audit_icems_policy_action(summary)["physical_zero_sum"] is True

    record["traces"][0]["r278_physical_m_residual_sum"] = 1e-3
    summary = summarise_icems_policy_trace(
        record,
        final_window_steps=5,
        fast_window_steps=15,
    )
    assert audit_icems_policy_action(summary)["physical_zero_sum"] is False
