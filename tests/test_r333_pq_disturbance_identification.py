from __future__ import annotations

from copy import deepcopy

import numpy as np
from probes.r333_pq_disturbance_identification import (
    analyse_pq_disturbance_identification,
)

SEAL_SHA = "1" * 64
MODEL_SHA = "2" * 64


def _contract() -> dict[str, object]:
    return {
        "round": "R333",
        "question": "Q-0085",
        "operating_points": ["HS0", "HS1"],
        "operating_point_records": [
            {
                "name": "HS0",
                "vsg_m_device": 177.5,
                "vsg_d_device": 88.75,
                "tie_rx_scale": 1.10,
                "initial_soc": 0.41,
            },
            {
                "name": "HS1",
                "vsg_m_device": 202.5,
                "vsg_d_device": 101.25,
                "tie_rx_scale": 1.35,
                "initial_soc": 0.51,
            },
        ],
        "signs": ["zero", "positive", "negative"],
        "device_idx": "PQ_Bus14",
        "bus_idx": 14,
        "controlled_bus_order": [12, 16, 14, 15],
        "node_disturbance_map": [0.0, 0.0, -1.0, 0.0],
        "nominal_tie_lines": {
            "Line_4": {"r": 0.02201, "x": 0.22001},
            "Line_5": {"r": 0.02202, "x": 0.22002},
            "Line_6": {"r": 0.022, "x": 0.22},
        },
        "pre_event_active_load_system_pu": 2.48,
        "pre_event_reactive_load_system_pu": 0.0,
        "amplitude_system_pu": 0.05,
        "system_base_mva": 100.0,
        "vsg_device_base_mva": 200.0,
        "steps": 25,
        "active_steps": 5,
        "recovery_steps": 20,
        "control_period_seconds": 0.2,
        "event_times_seconds": {"apply": 0.5, "restore": 1.5},
        "physical_execution_planned": True,
        "physical_execution_performed": False,
        "thresholds": {
            "pq_readback_absolute_tolerance_system_pu": 1e-12,
            "zero_actuator_power_absolute_maximum_system_pu": 1e-6,
            "algebraic_residual_absolute_maximum": 1e-6,
            "signal_to_baseline_drift_energy_ratio_minimum": 10.0,
            "pair_midpoint_nonlinearity_ratio_maximum": 0.10,
            "reduced_physical_total_nrmse_maximum": 0.15,
            "reduced_physical_peak_vector_residual_maximum": 0.20,
        },
    }


def _receipt(
    *,
    idx: str,
    parameter: str,
    before: float,
    after: float,
    event_time: float,
    observation_time: float,
) -> dict[str, object]:
    return {
        "idx": idx,
        "mechanism": "Alter",
        "device_idx": "PQ_Bus14",
        "parameter": parameter,
        "method": "=",
        "scheduled_event_time_seconds": event_time,
        "observation_time_seconds": observation_time,
        "before_system_pu": before,
        "target_system_pu": after,
        "readback_system_pu": after,
        "system_base_mva": 100.0,
        "quantity": (
            "active-power consumption"
            if parameter == "Ppf"
            else "reactive-power consumption"
        ),
        "positive_sign": "increased consumption",
        "exact_event_row_semantics": "pre-event",
    }


def _expected_inputs() -> dict[str, dict[str, list[list[float]]]]:
    payload: dict[str, dict[str, list[list[float]]]] = {}
    for point in ("HS0", "HS1"):
        payload[point] = {}
        for sign, delta in (("zero", 0.0), ("positive", 0.05), ("negative", -0.05)):
            values = np.zeros((25, 4), dtype=float)
            values[:5, 2] = -delta
            payload[point][sign] = values.tolist()
    return payload


def _expected_predictions() -> dict[str, dict[str, list[list[float]]]]:
    payload: dict[str, dict[str, list[list[float]]]] = {}
    for point in ("HS0", "HS1"):
        payload[point] = {}
        for sign in ("zero", "positive", "negative"):
            payload[point][sign] = _response(sign).tolist()
    return payload


def _response(sign: str) -> np.ndarray:
    response = np.zeros((25, 4), dtype=float)
    if sign != "zero":
        direction = -1.0 if sign == "positive" else 1.0
        shape = direction * 1e-3 * np.exp(-0.08 * np.arange(25))
        response[:, 0] = shape
        response[:, 1] = 0.2 * shape
        response[:, 2] = -0.1 * shape
        response[:, 3] = 0.05 * shape
    return response


def _record(point: str, sign: str) -> dict[str, object]:
    steps = 25
    time = (0.7 + 0.2 * np.arange(steps)).tolist()
    delta = {"zero": 0.0, "positive": 0.05, "negative": -0.05}[sign]
    response = _response(sign)
    before = 2.48
    after = before + delta
    point_values = {
        "HS0": {
            "vsg_m_device": 177.5,
            "vsg_d_device": 88.75,
            "tie_rx_scale": 1.10,
            "initial_soc": 0.41,
        },
        "HS1": {
            "vsg_m_device": 202.5,
            "vsg_d_device": 101.25,
            "tie_rx_scale": 1.35,
            "initial_soc": 0.51,
        },
    }[point]

    def snapshot(*, p: float, t: float) -> dict[str, object]:
        return {
            "device_idx": "PQ_Bus14",
            "bus_idx": 14,
            "dae_time_seconds": t,
            "raw_active": True,
            "effective_active": True,
            "active": True,
            "Ppf_system_pu": p,
            "Qpf_system_pu": 0.0,
            "pq2z_config": 0,
            "vcmp_enable": 0,
            "constant_power_weights": {
                "p2p": 1.0,
                "p2i": 0.0,
                "p2z": 0.0,
                "q2q": 1.0,
                "q2i": 0.0,
                "q2z": 0.0,
            },
            "replacement_records": {"FLoad": [], "ZIP": []},
            "active_fload_replacements_for_device": 0,
            "active_zip_replacements_for_device": 0,
        }

    event_inventory = [
        {
            "idx": "R333_apply_p",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Ppf",
            "t": 0.5,
            "method": "=",
            "amount": after,
        },
        {
            "idx": "R333_apply_q",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Qpf",
            "t": 0.5,
            "method": "=",
            "amount": 0.0,
        },
        {
            "idx": "R333_restore_p",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Ppf",
            "t": 1.5,
            "method": "=",
            "amount": before,
        },
        {
            "idx": "R333_restore_q",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Qpf",
            "t": 1.5,
            "method": "=",
            "amount": 0.0,
        },
    ]
    grid = [0.4999, 0.5, 0.5001, 1.4999, 1.4999999999999998, 1.5, 1.5001]
    internal = {
        name: [0.0, 0.0, 0.0, 0.0]
        for name in ("Pext0", "Pext", "Pref", "Psum")
    }
    traces = [
        {
            "vsg_m_actual_system": [2.0 * point_values["vsg_m_device"]] * 4,
            "vsg_d_actual_system": [2.0 * point_values["vsg_d_device"]] * 4,
            "bess_soc": [point_values["initial_soc"]] * 4,
            "bess_internal": deepcopy(internal),
        }
        for _ in range(steps)
    ]
    return {
        "seal_sha256": SEAL_SHA,
        "dynamic_model_sha256": MODEL_SHA,
        "operating_point": point,
        "operating_point_configuration": {"name": point, **point_values},
        "tie_line_readback": {
            "Line_4": {
                "r": 0.02201 * point_values["tie_rx_scale"],
                "x": 0.22001 * point_values["tie_rx_scale"],
            },
            "Line_5": {
                "r": 0.02202 * point_values["tie_rx_scale"],
                "x": 0.22002 * point_values["tie_rx_scale"],
            },
            "Line_6": {
                "r": 0.022 * point_values["tie_rx_scale"],
                "x": 0.22 * point_values["tie_rx_scale"],
            },
        },
        "sign": sign,
        "device_idx": "PQ_Bus14",
        "delta_load_system_pu": delta,
        "completed": True,
        "tds_failed": False,
        "n_steps": steps,
        "requested_steps": steps,
        "time_seconds": time,
        "output_coordinates": response.tolist(),
        "predicted_output_coordinates": response.tolist(),
        "coordinate_input_sequence": _expected_inputs()[point][sign],
        "event_inventory": event_inventory,
        "event_receipts": [
            _receipt(
                idx="R333_apply_p",
                parameter="Ppf",
                before=before,
                after=after,
                event_time=0.5,
                observation_time=0.5,
            ),
            _receipt(
                idx="R333_apply_q",
                parameter="Qpf",
                before=0.0,
                after=0.0,
                event_time=0.5,
                observation_time=0.5,
            ),
            _receipt(
                idx="R333_restore_p",
                parameter="Ppf",
                before=after,
                after=before,
                event_time=1.5,
                observation_time=1.5,
            ),
            _receipt(
                idx="R333_restore_q",
                parameter="Qpf",
                before=0.0,
                after=0.0,
                event_time=1.5,
                observation_time=1.5,
            ),
        ],
        "pre_event_snapshot": snapshot(p=before, t=0.5),
        "post_apply_snapshot": snapshot(p=after, t=0.5),
        "pre_restore_snapshot": snapshot(p=after, t=1.5),
        "post_restore_snapshot": snapshot(p=before, t=1.5),
        "terminal_snapshot": snapshot(p=before, t=time[-1]),
        "event_callback_audit": [
            {
                "dae_time_seconds": 0.5,
                "event_ids": ["R333_apply_p", "R333_apply_q"],
                "before": snapshot(p=before, t=0.5),
                "after": snapshot(p=after, t=0.5),
                "callback_action": True,
            },
            {
                "dae_time_seconds": 1.5,
                "event_ids": ["R333_restore_p", "R333_restore_q"],
                "before": snapshot(p=after, t=1.5),
                "after": snapshot(p=before, t=1.5),
                "callback_action": True,
            },
        ],
        "event_fire_counts": {
            "R333_apply_p": 1,
            "R333_apply_q": 1,
            "R333_restore_p": 1,
            "R333_restore_q": 1,
        },
        "pq_active": True,
        "constant_power_weights": {
            "p2p": 1.0,
            "p2i": 0.0,
            "p2z": 0.0,
            "q2q": 1.0,
            "q2i": 0.0,
            "q2z": 0.0,
        },
        "active_fload_replacements_for_device": 0,
        "active_zip_replacements_for_device": 0,
        "alter_event_inventory_guard": True,
        "exact_event_sample_order_guard": True,
        "tds_time_grid_seconds": grid,
        "md_write_count_maximum": 0,
        "bess_requested_power_absolute_maximum_system_pu": 0.0,
        "bess_commanded_power_absolute_maximum_system_pu": 0.0,
        "bess_actual_power_absolute_maximum_system_pu": 0.0,
        "bess_internal_power_absolute_maximum_system_pu": 0.0,
        "internal_limiter_active": False,
        "external_saturation_active": False,
        "constraint_violation_count": 0,
        "line_8_all_in_service": True,
        "g4_all_in_service": True,
        "all_states_finite": True,
        "system_exit_code_maximum": 0,
        "algebraic_residual_absolute_maximum": 1e-9,
        "negative_load_crossing": False,
        "tds_grid_guard": True,
        "traces": traces,
    }


def _execution() -> dict[str, object]:
    return {
        "round": "R333",
        "question": "Q-0085",
        "seal_sha256": SEAL_SHA,
        "dynamic_model_sha256": MODEL_SHA,
        "records": [
            _record(point, sign)
            for point in ("HS0", "HS1")
            for sign in ("zero", "positive", "negative")
        ],
        "source_identity": True,
        "parent_identity": True,
        "runtime_identity": True,
        "physical_execution_performed": True,
        "controller_executed": False,
        "closed_loop_executed": False,
        "distributed_runtime_executed": False,
        "training_executed": False,
        "eval_executed": False,
    }


def _analyse(
    execution: dict[str, object],
    *,
    evidence_chain_valid: bool = True,
) -> dict[str, object]:
    return analyse_pq_disturbance_identification(
        execution,
        _contract(),
        expected_seal_sha256=SEAL_SHA,
        expected_dynamic_model_sha256=MODEL_SHA,
        expected_coordinate_inputs=_expected_inputs(),
        expected_predictions=_expected_predictions(),
        evidence_chain_valid=evidence_chain_valid,
    )


def test_valid_signed_bank_qualifies_only_one_physical_channel() -> None:
    analysis = _analyse(_execution())

    assert analysis["classification"] == "QUALIFY"
    assert all(analysis["validity_guards"].values())
    assert all(analysis["identification_guards"].values())
    assert analysis["scope"]["identified_physical_channel_count"] == 1
    assert analysis["scope"]["successor_package_required"] is True
    assert analysis["scope"]["controller_authorized"] is False
    assert analysis["scope"]["distributed_agent_authorized"] is False
    assert analysis["scope"]["training_authorized"] is False
    assert analysis["scope"]["eval_executed"] is False


def test_missing_or_duplicate_record_invalidates_the_bank() -> None:
    execution = _execution()
    execution["records"] = execution["records"][:-1]

    analysis = _analyse(execution)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["record_inventory"] is False


def test_extra_non_record_object_invalidates_without_blocking_reasons() -> None:
    execution = _execution()
    execution["records"].append("not-a-record")

    analysis = _analyse(execution)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["record_inventory"] is False
    assert analysis["identification_guards"]["all"] is None
    assert analysis["blocking_reasons"] == []


def test_nonzero_actuator_power_invalidates_instead_of_becoming_a_result() -> None:
    execution = _execution()
    execution["records"][1]["bess_actual_power_absolute_maximum_system_pu"] = 2e-6

    analysis = _analyse(execution)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["zero_actuator"] is False


def test_wrong_pq_readback_or_restoration_invalidates_the_bank() -> None:
    execution = _execution()
    execution["records"][1]["event_receipts"][2]["readback_system_pu"] = 2.47

    analysis = _analyse(execution)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["pq_write_and_restoration"] is False


def test_wrong_q_readback_or_pre_event_measurement_invalidates_the_bank() -> None:
    execution = _execution()
    execution["records"][1]["event_receipts"][1]["readback_system_pu"] = 0.01
    execution["records"][2]["pre_event_snapshot"]["Ppf_system_pu"] = 2.47

    analysis = _analyse(execution)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["pq_write_and_restoration"] is False


def test_replacement_or_wrong_event_order_invalidates_the_bank() -> None:
    for field, value in (
        ("active_fload_replacements_for_device", 1),
        ("exact_event_sample_order_guard", False),
    ):
        execution = _execution()
        execution["records"][1][field] = value

        analysis = _analyse(execution)

        assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
        assert analysis["validity_guards"]["pq_effective_and_event_timing"] is False


def test_disordered_tds_grid_invalidates_even_if_self_reported_guard_is_true() -> None:
    execution = _execution()
    execution["records"][1]["tds_time_grid_seconds"] = [
        0.5,
        0.4999,
        0.5001,
        1.4999,
        1.5,
        1.5001,
    ]

    analysis = _analyse(execution)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["pq_effective_and_event_timing"] is False


def test_wrong_callback_count_batch_time_or_action_invalidates() -> None:
    mutations = (
        lambda row: row["event_fire_counts"].update(R333_apply_p=2),
        lambda row: row["event_callback_audit"].pop(),
        lambda row: row["event_callback_audit"][0].update(dae_time_seconds=0.6),
        lambda row: row["event_callback_audit"][1].update(callback_action=False),
    )
    for mutate in mutations:
        execution = _execution()
        mutate(execution["records"][1])

        analysis = _analyse(execution)

        assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
        assert analysis["validity_guards"]["pq_effective_and_event_timing"] is False


def test_wrong_input_model_hash_or_prediction_binding_invalidates() -> None:
    mutations = (
        lambda row: row.update(dynamic_model_sha256="3" * 64),
        lambda row: row["coordinate_input_sequence"][0].__setitem__(0, 0.01),
        lambda row: row["predicted_output_coordinates"][0].__setitem__(0, 0.01),
    )
    for mutate in mutations:
        execution = _execution()
        mutate(execution["records"][1])

        analysis = _analyse(execution)

        assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
        assert analysis["validity_guards"]["model_and_input_binding"] is False


def test_wrong_operating_point_or_internal_power_invalidates() -> None:
    for mutate in (
        lambda row: row["operating_point_configuration"].update(tie_rx_scale=1.2),
        lambda row: row["tie_line_readback"]["Line_4"].update(r=0.0),
        lambda row: row.update(bess_internal_power_absolute_maximum_system_pu=2e-6),
        lambda row: row["traces"][0]["bess_internal"]["Psum"].__setitem__(0, 2e-6),
    ):
        execution = _execution()
        mutate(execution["records"][1])

        analysis = _analyse(execution)

        assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"


def test_unverified_attempt_or_provenance_chain_invalidates() -> None:
    analysis = _analyse(_execution(), evidence_chain_valid=False)

    assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
    assert analysis["validity_guards"]["identity"] is False


def test_valid_execution_blocks_when_frozen_channel_prediction_is_wrong() -> None:
    execution = _execution()
    for record in execution["records"]:
        if record["sign"] != "zero":
            record["predicted_output_coordinates"] = np.zeros((25, 4)).tolist()

    expected = _expected_predictions()
    for point in ("HS0", "HS1"):
        for sign in ("positive", "negative"):
            expected[point][sign] = np.zeros((25, 4)).tolist()

    analysis = analyse_pq_disturbance_identification(
        execution,
        _contract(),
        expected_seal_sha256=SEAL_SHA,
        expected_dynamic_model_sha256=MODEL_SHA,
        expected_coordinate_inputs=_expected_inputs(),
        expected_predictions=expected,
        evidence_chain_valid=True,
    )

    assert analysis["classification"] == "BLOCK"
    assert analysis["validity_guards"]["all"] is True
    assert analysis["identification_guards"]["frozen_channel_equivalence"] is False


def test_valid_execution_blocks_on_signed_pair_nonlinearity() -> None:
    execution = _execution()
    positive = next(
        row
        for row in execution["records"]
        if row["operating_point"] == "HS0" and row["sign"] == "positive"
    )
    negative = next(
        row
        for row in execution["records"]
        if row["operating_point"] == "HS0" and row["sign"] == "negative"
    )
    negative["output_coordinates"] = deepcopy(positive["output_coordinates"])

    analysis = _analyse(execution)

    assert analysis["classification"] == "BLOCK"
    assert analysis["identification_guards"]["paired_local_linearity"] is False


def test_forbidden_learning_or_controller_flag_invalidates_scope() -> None:
    for field in (
        "controller_executed",
        "closed_loop_executed",
        "distributed_runtime_executed",
        "training_executed",
        "eval_executed",
    ):
        execution = _execution()
        execution[field] = True

        analysis = _analyse(execution)

        assert analysis["classification"] == "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
        assert analysis["validity_guards"]["scope_exclusions"] is False
