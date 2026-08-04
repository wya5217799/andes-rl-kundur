from __future__ import annotations

from copy import deepcopy

from andes_rl_kundur.evaluation.r292_screen import (
    audit_r292_q0_screen_record,
)


def _valid_q0_record() -> dict:
    traces = []
    for step in range(300):
        active = step < 15
        common = 0.25 if active else 0.0
        m_value = 350.0 if active else 200.0
        power = 0.05 if step < 150 else -0.05
        traces.append(
            {
                "step": step,
                "t": 0.2 * (step + 1),
                "freq_hz_physical": [60.0, 60.0, 60.0, 60.0],
                "delta_f_physical_hz": [0.0, 0.0, 0.0, 0.0],
                "action_norm": [[common, 0.0]] * 4,
                "M_es": [m_value] * 4,
                "D_es": [100.0] * 4,
                "r292_edge_flow_norm": [0.0, 0.0, 0.0],
                "r292_node_residual_norm": [0.0, 0.0, 0.0, 0.0],
                "r292_physical_m_residual_sum": 0.0,
                "bess_requested_power_system_pu": [power] * 4,
                "bess_commanded_power_system_pu": [power] * 4,
                "bess_actual_power_system_pu": [power] * 4,
                "bess_soc": [0.49] * 4,
                "bess_bus_voltage_pu": [1.0] * 4,
                "bess_saturation_reasons": [[], [], [], []],
                "bess_constraint_violations": [],
            }
        )
    return {
        "controller": "q0",
        "scenario": "worked_q0",
        "delta_u": {"PQ_0": 1.0},
        "completed": True,
        "tds_failed": False,
        "requested_steps": 300,
        "n_steps": 300,
        "traces": traces,
    }


def test_r292_q0_audit_accepts_frozen_common_pulse_and_slow_bess() -> None:
    result = audit_r292_q0_screen_record(
        _valid_q0_record(),
        trace_sha256="a" * 64,
    )

    assert result["physical_valid"] is True
    assert all(result["checks"].values())
    assert result["m_unique"] == [200.0, 350.0]
    assert result["max_abs_commanded_power"] == 0.05


def test_r292_q0_audit_rejects_nonzero_edge_residual() -> None:
    record = deepcopy(_valid_q0_record())
    record["traces"][0]["r292_edge_flow_norm"][0] = 0.01

    result = audit_r292_q0_screen_record(record, trace_sha256="b" * 64)

    assert result["physical_valid"] is False
    assert result["checks"]["zero_edge_residual"] is False
