from __future__ import annotations

from andes_rl_kundur.evaluation.vector_residual import _trace_row, audit_vector_action


def test_vector_action_audit_accepts_exact_frozen_contract() -> None:
    summary = {
        "r292_max_abs_edge": 0.125,
        "r292_max_abs_edge_slew": 0.125,
        "r292_max_abs_node_residual": 0.25,
        "r292_max_abs_node_slew": 0.25,
        "r292_max_abs_node_residual_sum": 0.0,
        "r292_max_abs_physical_m_residual_sum": 0.0,
        "r292_post_window_max_abs_edge": 0.0,
        "max_abs_d_action_norm": 0.0,
        "max_abs_m_action_norm": 0.5,
        "min_m": 200.0,
        "max_m": 500.0,
    }

    assert all(audit_vector_action(summary).values())


def test_vector_trace_row_preserves_requested_commanded_and_readback_chain() -> None:
    info = {
        "time": 0.2,
        "freq_hz_physical": [60.01, 60.0, 59.99, 60.0],
        "r292_executed_md_action_norm": [
            [0.125, 0.0],
            [0.5, 0.0],
            [0.0, 0.0],
            [0.375, 0.0],
        ],
        "M_es": [275.0, 500.0, 200.0, 425.0],
        "D_es": [100.0] * 4,
        "r292_raw_edge_action": [1.0, -1.0, 1.0],
        "r292_edge_flow_norm": [0.125, -0.125, 0.125],
        "r292_node_residual_norm": [-0.125, 0.25, -0.25, 0.125],
        "r292_physical_m_residual": [-75.0, 150.0, -150.0, 75.0],
        "r292_physical_m_residual_sum": 0.0,
        "vsg_common_m_model_units": [350.0] * 4,
        "vsg_requested_m_model_units": [275.0, 500.0, 200.0, 425.0],
        "vsg_commanded_m_model_units": [275.0, 500.0, 200.0, 425.0],
        "vsg_actual_m_model_units": [275.0, 500.0, 200.0, 425.0],
        "vsg_actual_d_model_units": [100.0] * 4,
        "bess_requested_power_system_pu": [0.0] * 4,
        "bess_commanded_power_system_pu": [0.0] * 4,
        "bess_actual_power_system_pu": [0.0] * 4,
        "bess_soc": [0.5] * 4,
        "bess_bus_voltage_pu": [1.0] * 4,
        "bess_saturation_reasons": [[], [], [], []],
        "bess_charge_energy_mwh_total": [0.0] * 4,
        "bess_discharge_energy_mwh_total": [0.0] * 4,
        "bess_constraint_violations": [],
    }

    row = _trace_row(0, info, 60.0)

    assert row["vsg_common_m_model_units"] == [350.0] * 4
    assert row["vsg_requested_m_model_units"] == [275.0, 500.0, 200.0, 425.0]
    assert row["vsg_commanded_m_model_units"] == [275.0, 500.0, 200.0, 425.0]
    assert row["vsg_actual_m_model_units"] == [275.0, 500.0, 200.0, 425.0]
    assert row["vsg_actual_d_model_units"] == [100.0] * 4
