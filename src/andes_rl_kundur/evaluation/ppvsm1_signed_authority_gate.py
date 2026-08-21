"""Classify the prospective R397 PPVSM1 two-unit signed P/Q authority bank.

The module owns the frozen R397 contract and a fail-closed pure classifier
for the nine-arm bank (zero arm plus two devices times two channels times two
signs). It imports no ANDES runtime code so records replay on Windows. The
schema embeds the R388-corrected evidence discipline (explicit initial
snapshot, order-independent bus identity, typed advanced-partial
termination) and the R393-R396 PPVSM1 lessons (signal-major initial rows,
device-major traces, global-address reads, round==contract round check).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from andes_rl_kundur.evaluation.ppvsm1_object_gate import (
    FORBIDDEN_MODELS,
    NETWORK_INVENTORY,
    PPVSM1_PARAMETER_CARD,
    PPVSM1_RUNTIME_PARAMETER_CARD,
)

ROUND_ID = "R397"
QUESTION_ID = "Q-0111"
PARTIAL_ERROR = "TDS terminated before horizon"
EXPECTED_MAPPING = (
    {"idx": "PPVSM1_1", "bus": 1, "gen": 1},
    {"idx": "PPVSM1_2", "bus": 2, "gen": 2},
)
CHANNELS = (
    {"input": "pref", "output": "Pe", "cross_output": "Qe"},
    {"input": "qref", "output": "Qe", "cross_output": "Pe"},
)
TRACE_SIGNALS = ("Pe", "Qe", "Id", "Iq", "virtual_frequency")
SETPOINT_CHANNELS = ("pref", "qref")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
NONFINITE_TOKENS = {"nan", "inf", "+inf", "-inf"}
SCIENTIFIC_ERRORS = {
    None,
    "PFlow did not converge",
    "TDS initialization failed",
    "TDS did not advance",
    PARTIAL_ERROR,
}


def _arm_order() -> list[dict[str, Any]]:
    arms: list[dict[str, Any]] = [
        {
            "arm_id": "zero",
            "target_idx": None,
            "input_channel": None,
            "sign": 0,
            "requested_delta": 0.0,
        }
    ]
    labels = {-1: "negative", 1: "positive"}
    for number in (1, 2):
        idx = f"PPVSM1_{number}"
        for channel in ("pref", "qref"):
            for sign in (-1, 1):
                arms.append(
                    {
                        "arm_id": f"ppvsm1_{number}_{channel}_{labels[sign]}",
                        "target_idx": idx,
                        "input_channel": channel,
                        "sign": sign,
                        "requested_delta": sign * 0.09,
                    }
                )
    return arms


def build_ppvsm1_signed_authority_contract() -> dict[str, Any]:
    """Return the complete JSON-compatible R397 scientific contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "parent_round": "R396",
        "andes_version": "2.0.0",
        "expected_mapping": [dict(row) for row in EXPECTED_MAPPING],
        "forbidden_models": list(FORBIDDEN_MODELS),
        "network_inventory": dict(NETWORK_INVENTORY),
        "bus_indices": list(range(1, 11)),
        "parameter_card": dict(PPVSM1_PARAMETER_CARD),
        "runtime_parameter_card": dict(PPVSM1_RUNTIME_PARAMETER_CARD),
        "system_mva_base": 100.0,
        "device_rating_mva": 900.0,
        "step_abs_system_pu": 0.09,
        "channels": [dict(row) for row in CHANNELS],
        "arm_order": _arm_order(),
        "trajectory_count": 9,
        "tds_tf_seconds": 2.0,
        "tds_tolerance": 1.0e-4,
        "reference_abs_tolerance": 1.0e-12,
        "setpoint_abs_tolerance": 1.0e-12,
        "authority_abs_floor_system_pu": 2.0e-4,
        "paired_separation_floor_system_pu": 4.0e-4,
        "electrical_limits": {
            "bus_v_min_pu": 0.9,
            "bus_v_max_pu": 1.1,
            "current_magnitude_max_pu": 10.0,
            "apparent_power_max_system_pu": 9.0,
            "omega_min_pu": 0.95,
            "omega_max_pu": 1.05,
        },
        "trace_signals": list(TRACE_SIGNALS),
        "trajectory_evidence": {
            "start_time_seconds": 0.0,
            "max_first_sample_time_seconds": 1.0 / 30.0 + 1.0e-4,
            "bus_identity_order_independent": True,
            "initial_snapshot_required": True,
            "advanced_partial_error": PARTIAL_ERROR,
        },
        "retry_authorized": False,
        "training_authorized": False,
    }


def payload_sha256(payload: object) -> str:
    """Return the canonical SHA-256 digest for a JSON-compatible payload."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _finite(value: object) -> bool:
    return bool(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _numeric_or_nonfinite_token(value: object) -> bool:
    return _finite(value) or (
        isinstance(value, str) and value.strip().lower() in NONFINITE_TOKENS
    )


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _close(left: object, right: object, tolerance: float) -> bool:
    return bool(
        _finite(left)
        and _finite(right)
        and math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    )


def _identity_sets(bus_values: object, devices: object, contract: Mapping[str, Any]) -> bool:
    if not isinstance(bus_values, Mapping) or not isinstance(devices, Mapping):
        return False
    expected_buses = {str(value) for value in contract["bus_indices"]}
    expected_idxes = {str(row["idx"]) for row in contract["expected_mapping"]}
    return bool(
        set(bus_values) == expected_buses
        and set(devices) == set(contract["trace_signals"])
        and all(
            isinstance(devices[signal], Mapping)
            and set(devices[signal]) == expected_idxes
            for signal in contract["trace_signals"]
        )
    )


def _inventory_schema(inventory: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(inventory, Mapping):
            return False
        counts = inventory["forbidden_model_counts"]
        return bool(
            inventory["network"] == contract["network_inventory"]
            and isinstance(counts, Mapping)
            and set(counts) == set(contract["forbidden_models"])
            and all(int(counts[name]) == 0 for name in contract["forbidden_models"])
            and inventory["forbidden_dae_names"] == []
            and int(inventory["ppvsm1_count"]) == 2
            and inventory["ppvsm1_buses"] == [1, 2]
            and inventory["ppvsm1_mapping_ok"] is True
            and inventory["input_parameter_cards_match"] is True
            and inventory["runtime_parameter_cards_match"] is True
        )
    except (KeyError, TypeError, ValueError):
        return False


def _reference_source_schema(value: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        rows = value["rows"]
        expected_idx = [row["idx"] for row in contract["expected_mapping"]]
        return bool(
            value["captured"] is True
            and value["phase"] == "post_pflow_pre_tds_init"
            and _sequence(rows)
            and len(rows) == 2
            and [str(row["idx"]) for row in rows] == expected_idx
            and all(
                isinstance(row, Mapping)
                and _finite(row["static_p"])
                and _finite(row["static_q"])
                for row in rows
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _references_schema(value: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        rows = value["rows"]
        expected_idx = [row["idx"] for row in contract["expected_mapping"]]
        if not (
            value["checked"] is True
            and value["phase"] == "post_init"
            and _close(
                value["absolute_tolerance"],
                contract["reference_abs_tolerance"],
                0.0,
            )
            and _sequence(rows)
            and len(rows) == 2
            and [str(row["idx"]) for row in rows] == expected_idx
        ):
            return False
        return all(
            isinstance(row, Mapping)
            and _finite(row["static_p"])
            and _finite(row["static_q"])
            and _finite(row["pref"])
            and _finite(row["qref"])
            and _finite(row["abs_deviation"])
            and _close(
                row["abs_deviation"],
                max(
                    abs(float(row["pref"]) - float(row["static_p"])),
                    abs(float(row["qref"]) - float(row["static_q"])),
                ),
                0.0,
            )
            for row in rows
        )
    except (KeyError, TypeError, ValueError):
        return False


def _references_pass(arm: Mapping[str, Any], contract: Mapping[str, Any]) -> bool:
    try:
        tolerance = float(contract["reference_abs_tolerance"])
        source_rows = arm["reference_source"]["rows"]
        ref_rows = arm["references"]["rows"]
        for source, ref in zip(source_rows, ref_rows, strict=True):
            if not (
                ref["idx"] == source["idx"]
                and ref["static_p"] == source["static_p"]
                and ref["static_q"] == source["static_q"]
                and _close(ref["pref"], source["static_p"], tolerance)
                and _close(ref["qref"], source["static_q"], tolerance)
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _diagnostics_schema(value: object, tolerance: float) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        equation_count = int(value["equation_count"])
        residual_count = int(value["residual_count"])
        residuals = value["residuals"]
        indices = value["bad_combined_indices"]
        clamped = value["clamped_limits"]
        if not (
            value["captured"] is True
            and equation_count > 0
            and residual_count >= 0
            and _sequence(residuals)
            and _sequence(indices)
            and _sequence(clamped)
            and residual_count == len(residuals) == len(indices)
        ):
            return False
        normalized_indices = [int(item) for item in indices]
        if len(set(normalized_indices)) != len(normalized_indices) or any(
            item < 0 or item >= equation_count for item in normalized_indices
        ):
            return False
        required_residual = {
            "combined_index",
            "name",
            "residual",
            "equation",
            "model",
            "idx",
        }
        row_indices: list[int] = []
        for row in residuals:
            if not isinstance(row, Mapping) or not required_residual.issubset(row):
                return False
            row_indices.append(int(row["combined_index"]))
            if any(
                not isinstance(row[key], str) or not row[key]
                for key in ("name", "equation", "model")
            ):
                return False
            residual = row["residual"]
            if _finite(residual):
                if abs(float(residual)) < tolerance:
                    return False
            elif not (
                isinstance(residual, str)
                and residual.strip().lower() in NONFINITE_TOKENS
            ):
                return False
        if row_indices != normalized_indices:
            return False
        required_limit = {"model", "idx", "var", "limit_name", "limit_val", "unconstr"}
        for row in clamped:
            if not isinstance(row, Mapping) or not required_limit.issubset(row):
                return False
            if any(
                not isinstance(row[key], str) or not row[key]
                for key in ("model", "var", "limit_name")
            ):
                return False
            if not _finite(row["limit_val"]) or not _finite(row["unconstr"]):
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _solver_schema(value: object, *, allow_missing_terminal: bool = False) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        return bool(
            all(
                isinstance(value[key], bool)
                for key in (
                    "setup_completed",
                    "pflow_converged",
                    "tds_initialized",
                    "tds_test_ok",
                    "tds_converged",
                )
            )
            and _finite(value["tds_tolerance"])
            and (
                _finite(value["terminal_time_seconds"])
                or (allow_missing_terminal and value["terminal_time_seconds"] is None)
            )
        )
    except (KeyError, TypeError):
        return False


def _setpoint_schema(value: object) -> bool:
    if not _sequence(value) or len(value) != 4:
        return False
    expected = [
        (f"PPVSM1_{number}", channel)
        for number in (1, 2)
        for channel in ("pref", "qref")
    ]
    try:
        return bool(
            [(str(row["idx"]), str(row["channel"])) for row in value] == expected
            and all(_finite(row["value"]) for row in value)
        )
    except (KeyError, TypeError):
        return False


def _action_schema(value: object, expected: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        if not _setpoint_schema(value["pre_setpoints"]) or not _setpoint_schema(
            value["post_setpoints"]
        ):
            return False
        if expected["target_idx"] is None:
            return bool(
                value["applied"] is False
                and value["requested_absolute"] is None
                and value["applied_readback"] is None
            )
        return bool(
            value["applied"] is True
            and _finite(value["requested_absolute"])
            and _finite(value["applied_readback"])
        )
    except (KeyError, TypeError):
        return False


def _action_baseline_matches_references(
    arm: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    try:
        tolerance = float(contract["setpoint_abs_tolerance"])
        expected: dict[tuple[str, str], float] = {}
        for row in arm["references"]["rows"]:
            expected[(str(row["idx"]), "pref")] = float(row["pref"])
            expected[(str(row["idx"]), "qref")] = float(row["qref"])
        observed = {
            (str(row["idx"]), str(row["channel"])): float(row["value"])
            for row in arm["action"]["pre_setpoints"]
        }
        return bool(
            set(observed) == set(expected)
            and all(_close(observed[key], value, tolerance) for key, value in expected.items())
        )
    except (KeyError, TypeError, ValueError):
        return False


def _bus_identity(value: object, contract: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping):
        return False
    expected_buses = {str(number) for number in contract["bus_indices"]}
    return set(value) == expected_buses


def _trace_device_identity(value: object, contract: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping):
        return False
    expected_idxes = {str(row["idx"]) for row in contract["expected_mapping"]}
    return bool(
        set(value) == expected_idxes
        and all(
            isinstance(value[device_id], Mapping)
            and set(value[device_id]) == set(contract["trace_signals"])
            for device_id in expected_idxes
        )
    )


def _initial_schema(value: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        if not (
            value["captured"] is True
            and _close(
                value["time_seconds"],
                contract["trajectory_evidence"]["start_time_seconds"],
                0.0,
            )
            and isinstance(value["dae_finite"], bool)
            and isinstance(value["ppvsm1_finite"], bool)
            and _identity_sets(value["bus_v"], value["devices"], contract)
        ):
            return False
        values = list(value["bus_v"].values())
        for signal in contract["trace_signals"]:
            values.extend(value["devices"][signal].values())
        return all(_numeric_or_nonfinite_token(item) for item in values)
    except (KeyError, TypeError, ValueError):
        return False


def _trace_schema(
    value: object,
    contract: Mapping[str, Any],
    *,
    terminal_time: object,
    partial: bool,
) -> bool:
    try:
        if not isinstance(value, Mapping) or value["captured"] is not True:
            return False
        evidence = contract["trajectory_evidence"]
        tolerance = float(contract["tds_tolerance"])
        start = float(evidence["start_time_seconds"])
        time = value["time"]
        if not (
            _close(value["start_time_seconds"], start, 0.0)
            and _initial_schema(value["initial"], contract)
            and _sequence(time)
            and len(time) >= 2
            and all(_finite(item) for item in time)
            and all(float(right) > float(left) for left, right in zip(time, time[1:]))
            and float(time[0]) > start
            and float(time[0]) <= float(evidence["max_first_sample_time_seconds"])
            and _close(time[-1], terminal_time, tolerance)
            and isinstance(value["dae_finite"], bool)
            and isinstance(value["ppvsm1_finite"], bool)
            and _bus_identity(value["bus_v"], contract)
            and _trace_device_identity(value["devices"], contract)
        ):
            return False
        horizon = float(contract["tds_tf_seconds"])
        if partial:
            if not (float(terminal_time) > start and float(terminal_time) < horizon - tolerance):
                return False
        elif not _close(terminal_time, horizon, tolerance):
            return False
        n_samples = len(time)
        expected_idx = [str(row["idx"]) for row in contract["expected_mapping"]]
        if not all(
            _sequence(row) and len(row) == n_samples for row in value["bus_v"].values()
        ):
            return False
        for device_id in expected_idx:
            signals = value["devices"][device_id]
            if set(signals) != set(contract["trace_signals"]):
                return False
            if not all(
                _sequence(row) and len(row) == n_samples for row in signals.values()
            ):
                return False
        series = list(value["bus_v"].values())
        for device_id in expected_idx:
            for signal in contract["trace_signals"]:
                series.append(value["devices"][device_id][signal])
        return all(
            all(_numeric_or_nonfinite_token(item) for item in row) for row in series
        )
    except (KeyError, TypeError, ValueError):
        return False


def _empty_reference_source() -> dict[str, Any]:
    return {"captured": False, "phase": None, "rows": []}


def _empty_references() -> dict[str, Any]:
    return {"checked": False, "absolute_tolerance": None, "phase": None, "rows": []}


def _empty_action() -> dict[str, Any]:
    return {
        "applied": False,
        "pre_setpoints": [],
        "post_setpoints": [],
        "requested_absolute": None,
        "applied_readback": None,
    }


def _empty_initial() -> dict[str, Any]:
    return {
        "captured": False,
        "time_seconds": None,
        "dae_finite": False,
        "ppvsm1_finite": False,
        "bus_v": {},
        "devices": {},
    }


def _empty_trajectory() -> dict[str, Any]:
    return {
        "captured": False,
        "start_time_seconds": None,
        "initial": _empty_initial(),
        "time": [],
        "dae_finite": False,
        "ppvsm1_finite": False,
        "bus_v": {},
        "devices": {},
    }


def _empty_action_arm(arm: Mapping[str, Any]) -> bool:
    return arm["action"] == _empty_action()


def _pre_trajectory_failure_sentinel(arm: Mapping[str, Any]) -> bool:
    return bool(
        _empty_action_arm(arm)
        and arm["trajectory"] == _empty_trajectory()
        and arm["solver"]["tds_converged"] is False
        and arm["solver"]["terminal_time_seconds"] is None
    )


def _pflow_failure_sentinel(arm: Mapping[str, Any]) -> bool:
    return bool(
        arm["reference_source"] == _empty_reference_source()
        and arm["references"] == _empty_references()
        and _pre_trajectory_failure_sentinel(arm)
        and arm["solver"]["setup_completed"] is True
        and arm["solver"]["pflow_converged"] is False
        and arm["solver"]["tds_initialized"] is False
        and arm["solver"]["tds_test_ok"] is False
    )


def _initial_only_no_advance(
    value: object, contract: Mapping[str, Any]
) -> bool:
    try:
        return bool(
            isinstance(value, Mapping)
            and value["captured"] is False
            and _close(
                value["start_time_seconds"],
                contract["trajectory_evidence"]["start_time_seconds"],
                0.0,
            )
            and _initial_schema(value["initial"], contract)
            and value["time"] == []
            and value["dae_finite"] is False
            and value["ppvsm1_finite"] is False
            and value["bus_v"] == {}
            and value["devices"] == {}
        )
    except (KeyError, TypeError):
        return False


def _no_advance_sentinel(
    arm: Mapping[str, Any], expected: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    return bool(
        _action_schema(arm["action"], expected)
        and _initial_only_no_advance(arm["trajectory"], contract)
        and arm["solver"]["pflow_converged"] is True
        and arm["solver"]["tds_initialized"] is True
        and arm["solver"]["tds_test_ok"] is True
        and arm["solver"]["tds_converged"] is False
        and _close(
            arm["solver"]["terminal_time_seconds"],
            contract["trajectory_evidence"]["start_time_seconds"],
            float(contract["tds_tolerance"]),
        )
    )


def _arm_schema(
    arm: object, expected: Mapping[str, Any], contract: Mapping[str, Any]
) -> bool:
    try:
        if not isinstance(arm, Mapping):
            return False
        metadata = {
            key: arm[key]
            for key in (
                "arm_id",
                "target_idx",
                "input_channel",
                "sign",
                "requested_delta",
            )
        }
        scientific_error = arm["scientific_error"]
        if scientific_error not in SCIENTIFIC_ERRORS:
            return False
        common = bool(
            metadata == expected
            and _inventory_schema(arm["inventory"], contract)
            and _diagnostics_schema(
                arm["initialization_diagnostics"],
                float(contract["tds_tolerance"]),
            )
            and _solver_schema(
                arm["solver"], allow_missing_terminal=scientific_error is not None
            )
        )
        if not common:
            return False
        if scientific_error == "PFlow did not converge":
            return _pflow_failure_sentinel(arm)
        if scientific_error == "TDS initialization failed":
            return bool(
                _reference_source_schema(arm["reference_source"], contract)
                and _references_schema(arm["references"], contract)
                and _pre_trajectory_failure_sentinel(arm)
                and arm["solver"]["pflow_converged"] is True
                and (
                    arm["solver"]["tds_initialized"] is False
                    or arm["solver"]["tds_test_ok"] is False
                )
            )
        if scientific_error == "TDS did not advance":
            return bool(
                _reference_source_schema(arm["reference_source"], contract)
                and _references_schema(arm["references"], contract)
                and _no_advance_sentinel(arm, expected, contract)
                and _action_baseline_matches_references(arm, contract)
            )
        if scientific_error == PARTIAL_ERROR:
            return bool(
                _reference_source_schema(arm["reference_source"], contract)
                and _references_schema(arm["references"], contract)
                and _action_schema(arm["action"], expected)
                and _action_baseline_matches_references(arm, contract)
                and arm["solver"]["pflow_converged"] is True
                and arm["solver"]["tds_initialized"] is True
                and arm["solver"]["tds_test_ok"] is True
                and arm["solver"]["tds_converged"] is False
                and _trace_schema(
                    arm["trajectory"],
                    contract,
                    terminal_time=arm["solver"]["terminal_time_seconds"],
                    partial=True,
                )
            )
        return bool(
            _reference_source_schema(arm["reference_source"], contract)
            and _references_schema(arm["references"], contract)
            and _action_schema(arm["action"], expected)
            and _action_baseline_matches_references(arm, contract)
            and _trace_schema(
                arm["trajectory"],
                contract,
                terminal_time=arm["solver"]["terminal_time_seconds"],
                partial=False,
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _record_integrity(record: Mapping[str, Any], contract: Mapping[str, Any]) -> bool:
    try:
        source = record["source"]
        arms = record["arms"]
        expected = contract["arm_order"]
        if not (
            record["schema_version"] == 1
            and record["round"] == ROUND_ID
            and record["question"] == QUESTION_ID
            and record["contract_sha256"] == payload_sha256(contract)
            and record["formal_input_complete"] is True
            and record["execution_error"] is None
            and record["training_executed"] is False
            and isinstance(record["trajectory_attempted_count"], int)
            and not isinstance(record["trajectory_attempted_count"], bool)
            and record["trajectory_attempted_count"] == contract["trajectory_count"]
            and isinstance(record["trajectory_executed_count"], int)
            and not isinstance(record["trajectory_executed_count"], bool)
            and 0 <= record["trajectory_executed_count"] <= contract["trajectory_count"]
            and source["andes_version"] == contract["andes_version"]
            and source["xlsx_json_static_equal"] is True
            and source["derived_case_deterministic"] is True
            and all(
                _valid_sha256(source[key])
                for key in (
                    "xlsx_case_sha256",
                    "json_case_sha256",
                    "derived_case_sha256",
                    "ppvsm1_model_sha256",
                )
            )
            and _sequence(arms)
            and len(arms) == contract["trajectory_count"]
        ):
            return False
        if not all(
            _arm_schema(arm, expected_arm, contract)
            for arm, expected_arm in zip(arms, expected, strict=True)
        ):
            return False
        return record["trajectory_executed_count"] == sum(
            int(arm["trajectory"]["captured"] is True) for arm in arms
        )
    except (KeyError, TypeError, ValueError):
        return False


def _initialization_pass(arms: Sequence[Mapping[str, Any]]) -> bool:
    return all(
        arm["initialization_diagnostics"]["residual_count"] == 0
        and arm["initialization_diagnostics"]["residuals"] == []
        and arm["initialization_diagnostics"]["bad_combined_indices"] == []
        and arm["initialization_diagnostics"]["clamped_limits"] == []
        for arm in arms
    )


def _solver_pass(arms: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> bool:
    tolerance = float(contract["tds_tolerance"])
    terminal = float(contract["tds_tf_seconds"])
    return all(
        all(
            arm["solver"][key] is True
            for key in (
                "setup_completed",
                "pflow_converged",
                "tds_initialized",
                "tds_test_ok",
                "tds_converged",
            )
        )
        and _close(arm["solver"]["tds_tolerance"], tolerance, 0.0)
        and _close(arm["solver"]["terminal_time_seconds"], terminal, tolerance)
        and _close(arm["trajectory"]["time"][-1], terminal, tolerance)
        for arm in arms
    )


def _action_identity_pass(arms: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> bool:
    tolerance = float(contract["setpoint_abs_tolerance"])
    for arm in arms:
        if arm["scientific_error"] is not None:
            return False
        action = arm["action"]
        pre = {
            (row["idx"], row["channel"]): float(row["value"])
            for row in action["pre_setpoints"]
        }
        post = {
            (row["idx"], row["channel"]): float(row["value"])
            for row in action["post_setpoints"]
        }
        target = arm["target_idx"]
        if target is None:
            if any(not _close(post[key], value, tolerance) for key, value in pre.items()):
                return False
            continue
        key = (target, arm["input_channel"])
        requested = pre[key] + float(arm["requested_delta"])
        if not (
            _close(action["requested_absolute"], requested, tolerance)
            and _close(action["applied_readback"], requested, tolerance)
            and _close(post[key], requested, tolerance)
        ):
            return False
        if any(
            other != key and not _close(post[other], value, tolerance)
            for other, value in pre.items()
        ):
            return False
    return True


def _finite_and_electrical_checks(
    arms: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> tuple[bool, bool]:
    limits = contract["electrical_limits"]
    finite_ok = True
    electrical_ok = True
    for arm in arms:
        trajectory = arm["trajectory"]
        if trajectory["captured"] is not True:
            finite_ok = False
            electrical_ok = False
            continue
        if (
            trajectory["dae_finite"] is not True
            or trajectory["ppvsm1_finite"] is not True
        ):
            finite_ok = False
        series = list(trajectory["bus_v"].values())
        for device_id in (row["idx"] for row in contract["expected_mapping"]):
            for signal in contract["trace_signals"]:
                series.append(trajectory["devices"][device_id][signal])
        if not all(all(_finite(value) for value in row) for row in series):
            finite_ok = False
            electrical_ok = False
            continue
        initial = trajectory["initial"]
        if not (
            initial["dae_finite"] is True and initial["ppvsm1_finite"] is True
        ):
            finite_ok = False
        initial_values = list(initial["bus_v"].values())
        for signal in contract["trace_signals"]:
            initial_values.extend(initial["devices"][signal].values())
        if not all(_finite(value) for value in initial_values):
            finite_ok = False
            electrical_ok = False
            continue
        for values in trajectory["bus_v"].values():
            if min(values) < limits["bus_v_min_pu"] or max(values) > limits["bus_v_max_pu"]:
                electrical_ok = False
        if any(
            value < limits["bus_v_min_pu"] or value > limits["bus_v_max_pu"]
            for value in initial["bus_v"].values()
        ):
            electrical_ok = False
        for device_id in (row["idx"] for row in contract["expected_mapping"]):
            signals = trajectory["devices"][device_id]
            for pe, qe, current_d, current_q, omega in zip(
                signals["Pe"],
                signals["Qe"],
                signals["Id"],
                signals["Iq"],
                signals["virtual_frequency"],
                strict=True,
            ):
                if (
                    math.hypot(float(current_d), float(current_q))
                    > limits["current_magnitude_max_pu"]
                ):
                    electrical_ok = False
                if math.hypot(float(pe), float(qe)) > limits[
                    "apparent_power_max_system_pu"
                ]:
                    electrical_ok = False
                if not limits["omega_min_pu"] <= float(omega) <= limits["omega_max_pu"]:
                    electrical_ok = False
            init = initial["devices"]
            if (
                math.hypot(float(init["Id"][device_id]), float(init["Iq"][device_id]))
                > limits["current_magnitude_max_pu"]
            ):
                electrical_ok = False
            if math.hypot(
                float(init["Pe"][device_id]), float(init["Qe"][device_id])
            ) > limits["apparent_power_max_system_pu"]:
                electrical_ok = False
            if not limits["omega_min_pu"] <= float(init["virtual_frequency"][device_id]) <= limits[
                "omega_max_pu"
            ]:
                electrical_ok = False
    return finite_ok, electrical_ok


def _response_rows(
    arms: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    zero = arms[0]["trajectory"]["devices"]
    channel_map = {row["input"]: row for row in contract["channels"]}
    floor = float(contract["authority_abs_floor_system_pu"])
    responses: list[dict[str, Any]] = []
    for arm in arms[1:]:
        target = arm["target_idx"]
        mapping = channel_map[arm["input_channel"]]
        output = mapping["output"]
        cross_output = mapping["cross_output"]
        achieved = {
            idx: float(arm["trajectory"]["devices"][idx][output][-1])
            - float(zero[idx][output][-1])
            for idx in zero
        }
        target_response = achieved[target]
        non_target_max = max(
            abs(value) for idx, value in achieved.items() if idx != target
        )
        cross_response = float(
            arm["trajectory"]["devices"][target][cross_output][-1]
        ) - float(zero[target][cross_output][-1])
        responses.append(
            {
                "arm_id": arm["arm_id"],
                "target_idx": target,
                "input_channel": arm["input_channel"],
                "output_signal": output,
                "sign": arm["sign"],
                "target_response": target_response,
                "non_target_responses": {
                    idx: value for idx, value in achieved.items() if idx != target
                },
                "max_abs_non_target_response": non_target_max,
                "target_attribution_margin": abs(target_response) - non_target_max,
                "target_cross_channel_response": cross_response,
                "signed_pass": int(arm["sign"]) * target_response >= floor,
                "attribution_pass": abs(target_response) - non_target_max >= floor,
            }
        )

    lookup = {
        (row["target_idx"], row["input_channel"], row["sign"]): row
        for row in responses
    }
    paired: list[dict[str, Any]] = []
    pair_floor = float(contract["paired_separation_floor_system_pu"])
    for idx in (row["idx"] for row in contract["expected_mapping"]):
        for channel in ("pref", "qref"):
            negative = lookup[(idx, channel, -1)]["target_response"]
            positive = lookup[(idx, channel, 1)]["target_response"]
            separation = positive - negative
            paired.append(
                {
                    "target_idx": idx,
                    "input_channel": channel,
                    "negative_response": negative,
                    "positive_response": positive,
                    "separation": separation,
                    "pass": separation >= pair_floor,
                }
            )
    return responses, paired


def _analysis(
    classification: str,
    checks: Mapping[str, bool],
    *,
    responses: Sequence[Mapping[str, Any]] = (),
    paired: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "classification": classification,
        "checks": dict(checks),
        "responses": [dict(row) for row in responses],
        "paired_separations": [dict(row) for row in paired],
        "claim_scope": "signed per-device PPVSM1 Pref/Qref dynamic authority on the frozen two-unit cell only",
        "next_gate": (
            "separately_registered_droop_slope_matching_verification"
            if classification == "PPVSM1-SIGNED-AUTHORITY-PASS"
            else None
        ),
        "retry_authorized": False,
        "training_authorized": False,
    }


def classify_ppvsm1_signed_authority_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one immutable R397 full-bank execution record fail-closed."""

    canonical = build_ppvsm1_signed_authority_contract()
    spec = canonical if contract is None else contract
    if spec != canonical or not _record_integrity(record, spec):
        return _analysis("ANALYSIS-INVALID", {"record_integrity": False})

    arms = record["arms"]
    finite_ok, electrical_ok = _finite_and_electrical_checks(arms, spec)
    complete_trajectories = all(
        arm["scientific_error"] is None and arm["trajectory"]["captured"] is True
        for arm in arms
    )
    responses, paired = (
        _response_rows(arms, spec) if complete_trajectories else ([], [])
    )
    checks = {
        "record_integrity": True,
        "reference_preservation": all(
            arm["scientific_error"] != "PFlow did not converge"
            and _references_pass(arm, spec)
            for arm in arms
        ),
        "initialization_diagnostics_zero": _initialization_pass(arms),
        "native_solver": _solver_pass(arms, spec),
        "finite_values": finite_ok,
        "electrical_envelope": electrical_ok,
        "action_identity": _action_identity_pass(arms, spec),
        "signed_self_response": complete_trajectories
        and all(row["signed_pass"] for row in responses),
        "target_attribution": complete_trajectories
        and all(row["attribution_pass"] for row in responses),
        "paired_separation": complete_trajectories and all(row["pass"] for row in paired),
    }
    classification = (
        "PPVSM1-SIGNED-AUTHORITY-PASS"
        if all(checks.values())
        else "STOP-PPVSM1-SIGNED-AUTHORITY"
    )
    return _analysis(
        classification,
        checks,
        responses=responses,
        paired=paired,
    )


__all__ = [
    "build_ppvsm1_signed_authority_contract",
    "classify_ppvsm1_signed_authority_record",
    "payload_sha256",
]
