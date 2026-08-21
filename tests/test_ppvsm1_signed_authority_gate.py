"""Unit tests for the pure R397 PPVSM1 signed-authority classifier."""

from __future__ import annotations

import copy
import json
from typing import Any

from andes_rl_kundur.evaluation.ppvsm1_object_gate import (
    PPVSM1_PARAMETER_CARD,
    PPVSM1_RUNTIME_PARAMETER_CARD,
)
from andes_rl_kundur.evaluation.ppvsm1_signed_authority_gate import (
    PARTIAL_ERROR,
    build_ppvsm1_signed_authority_contract,
    classify_ppvsm1_signed_authority_record,
    payload_sha256,
)

SHA = "0" * 64
SHA2 = "1" * 64


def _canonical_json(record: object) -> object:
    return json.loads(
        json.dumps(record, sort_keys=True, allow_nan=False)
    )


def _static_rows() -> list[dict[str, Any]]:
    return [
        {"idx": "PPVSM1_1", "static_p": 0.5, "static_q": 0.1},
        {"idx": "PPVSM1_2", "static_p": 0.4, "static_q": 0.08},
    ]


def _pre_setpoints() -> list[dict[str, Any]]:
    return [
        {"idx": "PPVSM1_1", "channel": "pref", "value": 0.5},
        {"idx": "PPVSM1_1", "channel": "qref", "value": 0.1},
        {"idx": "PPVSM1_2", "channel": "pref", "value": 0.4},
        {"idx": "PPVSM1_2", "channel": "qref", "value": 0.08},
    ]


def _inventory(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "network": copy.deepcopy(contract["network_inventory"]),
        "forbidden_model_counts": {
            name: 0 for name in contract["forbidden_models"]
        },
        "forbidden_dae_names": [],
        "ppvsm1": [
            {"idx": "PPVSM1_1", "bus": 1, "gen": 1},
            {"idx": "PPVSM1_2", "bus": 2, "gen": 2},
        ],
        "ppvsm1_count": 2,
        "ppvsm1_buses": [1, 2],
        "ppvsm1_mapping_ok": True,
        "input_parameter_cards_match": True,
        "runtime_parameter_cards_match": True,
    }


def _diagnostics() -> dict[str, Any]:
    return {
        "captured": True,
        "equation_count": 30,
        "bad_combined_indices": [],
        "residual_count": 0,
        "residuals": [],
        "clamped_limits": [],
    }


def _initial_bus_v() -> dict[str, float]:
    return {str(number): 1.0 for number in range(1, 11)}


def _initial_devices() -> dict[str, dict[str, float]]:
    return {
        "Pe": {"PPVSM1_1": 0.5, "PPVSM1_2": 0.4},
        "Qe": {"PPVSM1_1": 0.1, "PPVSM1_2": 0.08},
        "Id": {"PPVSM1_1": 0.5, "PPVSM1_2": 0.4},
        "Iq": {"PPVSM1_1": -0.1, "PPVSM1_2": -0.08},
        "virtual_frequency": {"PPVSM1_1": 1.0, "PPVSM1_2": 1.0},
    }


def _arm(contract: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    target = expected["target_idx"]
    channel = expected["input_channel"]
    delta = float(expected["requested_delta"])
    pre = _pre_setpoints()
    post = copy.deepcopy(pre)
    applied = False
    requested_absolute = None
    applied_readback = None
    if target is not None:
        for row in post:
            if row["idx"] == target and row["channel"] == channel:
                row["value"] = row["value"] + delta
        requested_absolute = float(
            next(
                row["value"]
                for row in pre
                if row["idx"] == target and row["channel"] == channel
            )
            + delta
        )
        applied_readback = requested_absolute
        applied = True

    devices = _initial_devices()
    if target is not None:
        output = "Pe" if channel == "pref" else "Qe"
        response = (1 if delta > 0 else -1) * 0.001
        devices = {
            signal: dict(values) for signal, values in devices.items()
        }
        for device_id in devices[output]:
            if device_id == target:
                devices[output][device_id] = (
                    devices[output][device_id] + response
                )

    initial_devices = _initial_devices()
    trace_devices = {
        device_id: {
            signal: [
                initial_devices[signal][device_id]
                if signal not in devices or device_id not in devices[signal]
                else 0.0,
            ]
            for signal in contract["trace_signals"]
        }
        for device_id in ("PPVSM1_1", "PPVSM1_2")
    }
    for device_id in ("PPVSM1_1", "PPVSM1_2"):
        for signal in contract["trace_signals"]:
            start_value = initial_devices[signal][device_id]
            end_value = start_value
            if target is not None and device_id == target:
                output = "Pe" if channel == "pref" else "Qe"
                if signal == output:
                    end_value = devices[signal][device_id]
            trace_devices[device_id][signal] = [start_value, start_value, end_value]

    static_rows = _static_rows()
    return {
        "arm_id": expected["arm_id"],
        "target_idx": target,
        "input_channel": channel,
        "sign": expected["sign"],
        "requested_delta": delta,
        "scientific_error": None,
        "inventory": _inventory(contract),
        "reference_source": {
            "captured": True,
            "phase": "post_pflow_pre_tds_init",
            "rows": [
                {"idx": row["idx"], "static_p": row["static_p"], "static_q": row["static_q"]}
                for row in static_rows
            ],
        },
        "references": {
            "checked": True,
            "absolute_tolerance": 1.0e-12,
            "phase": "post_init",
            "rows": [
                {
                    "idx": row["idx"],
                    "static_p": row["static_p"],
                    "static_q": row["static_q"],
                    "pref": row["static_p"],
                    "qref": row["static_q"],
                    "abs_deviation": 0.0,
                }
                for row in static_rows
            ],
        },
        "initialization_diagnostics": _diagnostics(),
        "action": {
            "applied": applied,
            "pre_setpoints": pre,
            "post_setpoints": post,
            "requested_absolute": requested_absolute,
            "applied_readback": applied_readback,
        },
        "trajectory": {
            "captured": True,
            "start_time_seconds": 0.0,
            "initial": {
                "captured": True,
                "time_seconds": 0.0,
                "dae_finite": True,
                "ppvsm1_finite": True,
                "bus_v": _initial_bus_v(),
                "devices": _initial_devices(),
            },
            "time": [1.0 / 30.0, 1.0, 2.0],
            "dae_finite": True,
            "ppvsm1_finite": True,
            "bus_v": {
                str(number): [1.0, 1.0, 1.0] for number in range(1, 11)
            },
            "devices": trace_devices,
        },
        "solver": {
            "setup_completed": True,
            "pflow_converged": True,
            "tds_initialized": True,
            "tds_test_ok": True,
            "tds_converged": True,
            "tds_tolerance": 1.0e-4,
            "terminal_time_seconds": 2.0,
        },
    }


def passing_record() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = build_ppvsm1_signed_authority_contract()
    record: dict[str, Any] = {
        "schema_version": 1,
        "round": "R397",
        "question": "Q-0111",
        "contract_sha256": payload_sha256(contract),
        "formal_input_complete": True,
        "execution_error": None,
        "training_executed": False,
        "trajectory_attempted_count": 9,
        "trajectory_executed_count": 9,
        "source": {
            "andes_version": "2.0.0",
            "xlsx_json_static_equal": True,
            "derived_case_deterministic": True,
            "xlsx_case_sha256": SHA,
            "json_case_sha256": SHA,
            "derived_case_sha256": SHA,
            "ppvsm1_model_sha256": SHA,
        },
        "arms": [_arm(contract, expected) for expected in contract["arm_order"]],
    }
    return contract, record


def _rehash(record: dict[str, Any], contract: dict[str, Any]) -> None:
    record["contract_sha256"] = payload_sha256(contract)


def test_contract_is_canonical_and_carries_the_frozen_bank() -> None:
    contract = build_ppvsm1_signed_authority_contract()

    assert contract["round"] == "R397"
    assert contract["question"] == "Q-0111"
    assert contract["parent_round"] == "R396"
    assert contract["trajectory_count"] == 9
    assert len(contract["arm_order"]) == 9
    assert contract["arm_order"][0]["arm_id"] == "zero"
    assert [row["arm_id"] for row in contract["arm_order"][1:5]] == [
        "ppvsm1_1_pref_negative",
        "ppvsm1_1_pref_positive",
        "ppvsm1_1_qref_negative",
        "ppvsm1_1_qref_positive",
    ]
    assert contract["parameter_card"] == PPVSM1_PARAMETER_CARD
    assert contract["runtime_parameter_card"] == PPVSM1_RUNTIME_PARAMETER_CARD
    assert contract["step_abs_system_pu"] == 0.09
    assert contract["tds_tf_seconds"] == 2.0
    assert contract["tds_tolerance"] == 1.0e-4
    assert contract["authority_abs_floor_system_pu"] == 2.0e-4
    assert contract["paired_separation_floor_system_pu"] == 4.0e-4
    assert contract["electrical_limits"] == {
        "bus_v_min_pu": 0.9,
        "bus_v_max_pu": 1.1,
        "current_magnitude_max_pu": 10.0,
        "apparent_power_max_system_pu": 9.0,
        "omega_min_pu": 0.95,
        "omega_max_pu": 1.05,
    }
    assert contract["bus_indices"] == list(range(1, 11))
    assert "bus_indices" not in contract["network_inventory"]
    assert contract["trajectory_evidence"]["advanced_partial_error"] == PARTIAL_ERROR
    assert contract["retry_authorized"] is False
    assert contract["training_authorized"] is False
    assert build_ppvsm1_signed_authority_contract() == contract


def test_payload_sha256_is_canonical_json_digest() -> None:
    contract = build_ppvsm1_signed_authority_contract()
    assert payload_sha256(contract) == payload_sha256(
        copy.deepcopy(contract)
    )
    assert payload_sha256(contract) != payload_sha256(
        {**contract, "round": "R396"}
    )


def test_passing_record_classifies_pass_with_all_checks() -> None:
    contract, record = passing_record()

    analysis = classify_ppvsm1_signed_authority_record(
        _canonical_json(record), contract=contract
    )

    assert analysis["classification"] == "PPVSM1-SIGNED-AUTHORITY-PASS"
    assert all(analysis["checks"].values())
    assert len(analysis["responses"]) == 8
    assert len(analysis["paired_separations"]) == 4
    assert all(row["signed_pass"] for row in analysis["responses"])
    assert all(row["attribution_pass"] for row in analysis["responses"])
    assert all(row["pass"] for row in analysis["paired_separations"])
    assert analysis["next_gate"] == (
        "separately_registered_droop_slope_matching_verification"
    )
    assert analysis["retry_authorized"] is False


def test_round_mismatch_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["round"] = "R396"

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["record_integrity"] is False


def test_contract_substitution_is_analysis_invalid() -> None:
    contract, record = passing_record()
    other = {**contract, "round": "R396"}

    analysis = classify_ppvsm1_signed_authority_record(
        record, contract=other
    )

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_wrong_arm_count_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"] = record["arms"][:8]
    record["trajectory_executed_count"] = 8

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_execution_error_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["execution_error"] = "RuntimeError: boom"

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_signed_response_failure_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][1]
    arm["trajectory"]["devices"]["PPVSM1_1"]["Pe"] = [0.5, 0.5, 0.5 + 0.001]

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True
    assert analysis["checks"]["signed_self_response"] is False
    assert analysis["responses"][0]["signed_pass"] is False


def test_target_attribution_failure_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][1]
    arm["trajectory"]["devices"]["PPVSM1_2"]["Pe"] = [0.4, 0.4, 0.4 + 0.0009]

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["target_attribution"] is False


def test_bus_voltage_out_of_envelope_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][0]
    arm["trajectory"]["bus_v"]["7"] = [1.0, 1.0, 1.2]

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["electrical_envelope"] is False


def test_nonfinite_trace_value_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][0]
    arm["trajectory"]["devices"]["PPVSM1_1"]["Iq"] = [0.0, 0.0, "nan"]

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["finite_values"] is False


def test_action_identity_leakage_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][1]
    for row in arm["action"]["post_setpoints"]:
        if row["idx"] == "PPVSM1_2" and row["channel"] == "pref":
            row["value"] += 0.001

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["action_identity"] is False


def test_reference_deviation_is_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][0]
    drifted = 0.5 + 1.0e-6
    arm["references"]["rows"][0]["pref"] = drifted
    arm["references"]["rows"][0]["abs_deviation"] = max(
        abs(drifted - 0.5), 0.0
    )
    for row in arm["action"]["pre_setpoints"]:
        if row["idx"] == "PPVSM1_1" and row["channel"] == "pref":
            row["value"] = drifted
    for row in arm["action"]["post_setpoints"]:
        if row["idx"] == "PPVSM1_1" and row["channel"] == "pref":
            row["value"] = drifted

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["reference_preservation"] is False


def test_pflow_failure_sentinel_is_valid_and_stops() -> None:
    contract, record = passing_record()
    arm = record["arms"][0]
    arm["scientific_error"] = "PFlow did not converge"
    arm["reference_source"] = {"captured": False, "phase": None, "rows": []}
    arm["references"] = {
        "checked": False,
        "absolute_tolerance": None,
        "phase": None,
        "rows": [],
    }
    arm["action"] = {
        "applied": False,
        "pre_setpoints": [],
        "post_setpoints": [],
        "requested_absolute": None,
        "applied_readback": None,
    }
    arm["trajectory"] = {
        "captured": False,
        "start_time_seconds": None,
        "initial": {
            "captured": False,
            "time_seconds": None,
            "dae_finite": False,
            "ppvsm1_finite": False,
            "bus_v": {},
            "devices": {},
        },
        "time": [],
        "dae_finite": False,
        "ppvsm1_finite": False,
        "bus_v": {},
        "devices": {},
    }
    arm["solver"].update(
        {
            "pflow_converged": False,
            "tds_initialized": False,
            "tds_test_ok": False,
            "tds_converged": False,
            "terminal_time_seconds": None,
        }
    )
    record["trajectory_executed_count"] = 8

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True
    assert analysis["checks"]["native_solver"] is False
    assert analysis["checks"]["reference_preservation"] is False


def test_advanced_partial_trace_is_typed_scientific_stop() -> None:
    contract, record = passing_record()
    arm = record["arms"][4]
    arm["scientific_error"] = PARTIAL_ERROR
    arm["solver"]["terminal_time_seconds"] = 1.0
    arm["solver"]["tds_converged"] = False
    for values in arm["trajectory"]["bus_v"].values():
        del values[2:]
    for device_id in arm["trajectory"]["devices"]:
        for signal in arm["trajectory"]["devices"][device_id]:
            del arm["trajectory"]["devices"][device_id][signal][2:]
    arm["trajectory"]["time"] = arm["trajectory"]["time"][:2]

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True
    assert analysis["checks"]["native_solver"] is False
    assert analysis["responses"] == []


def test_short_trace_without_typed_error_is_analysis_invalid() -> None:
    contract, record = passing_record()
    arm = record["arms"][4]
    arm["solver"]["terminal_time_seconds"] = 1.0
    arm["solver"]["tds_converged"] = False
    for values in arm["trajectory"]["bus_v"].values():
        del values[2:]
    for device_id in arm["trajectory"]["devices"]:
        for signal in arm["trajectory"]["devices"][device_id]:
            del arm["trajectory"]["devices"][device_id][signal][2:]
    arm["trajectory"]["time"] = arm["trajectory"]["time"][:2]

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_missing_initial_snapshot_is_analysis_invalid() -> None:
    contract, record = passing_record()
    record["arms"][1]["trajectory"]["initial"]["captured"] = False

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_device_major_initial_row_is_analysis_invalid() -> None:
    contract, record = passing_record()
    initial = record["arms"][1]["trajectory"]["initial"]
    initial["devices"] = {
        "PPVSM1_1": {
            signal: values["PPVSM1_1"] for signal, values in initial["devices"].items()
        },
        "PPVSM1_2": {
            signal: values["PPVSM1_2"] for signal, values in initial["devices"].items()
        },
    }

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_duplicated_bus_identity_is_analysis_invalid() -> None:
    contract, record = passing_record()
    initial = record["arms"][0]["trajectory"]["initial"]
    initial["bus_v"] = {**initial["bus_v"], "extra": 1.0}

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_no_advance_sentinel_is_valid_and_stops() -> None:
    contract, record = passing_record()
    arm = record["arms"][2]
    arm["scientific_error"] = "TDS did not advance"
    arm["solver"]["tds_converged"] = False
    arm["solver"]["terminal_time_seconds"] = 0.0
    arm["trajectory"] = {
        "captured": False,
        "start_time_seconds": 0.0,
        "initial": arm["trajectory"]["initial"],
        "time": [],
        "dae_finite": False,
        "ppvsm1_finite": False,
        "bus_v": {},
        "devices": {},
    }
    record["trajectory_executed_count"] = 8

    analysis = classify_ppvsm1_signed_authority_record(record, contract=contract)

    assert analysis["classification"] == "STOP-PPVSM1-SIGNED-AUTHORITY"
    assert analysis["checks"]["record_integrity"] is True
