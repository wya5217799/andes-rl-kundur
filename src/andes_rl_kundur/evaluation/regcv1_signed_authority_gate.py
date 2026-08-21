"""Prospective R387 signed per-device REGCV1 authority contract and classifier."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

ROUND_ID = "R387"
QUESTION_ID = "Q-0106"
EXPECTED_MAPPING = tuple(
    {"idx": f"REGCV1_{number}", "bus": number, "gen": number} for number in range(1, 5)
)
FORBIDDEN_MODELS = ("GENROU", "TGOV1", "EXDC2", "Toggler")
CHANNELS = (
    {"input": "pref", "output": "Pe", "cross_output": "Qe"},
    {"input": "qref", "output": "Qe", "cross_output": "Pe"},
)
TRACE_SIGNALS = ("Pe", "Qe", "Id", "Iq", "omega")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
NONFINITE_TOKENS = {"nan", "inf", "+inf", "-inf"}
SCIENTIFIC_ERRORS = {
    None,
    "PFlow.run returned a non-success value",
    "native TDS initialization guard failed",
    "TDS did not advance",
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
    for number in range(1, 5):
        idx = f"REGCV1_{number}"
        for channel in ("pref", "qref"):
            for sign in (-1, 1):
                arms.append(
                    {
                        "arm_id": f"regcv1_{number}_{channel}_{labels[sign]}",
                        "target_idx": idx,
                        "input_channel": channel,
                        "sign": sign,
                        "requested_delta": sign * 0.09,
                    }
                )
    return arms


def build_signed_authority_contract() -> dict[str, Any]:
    """Return the complete JSON-compatible R387 scientific contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "parent_round": "R386",
        "andes_version": "2.0.0",
        "expected_mapping": [dict(row) for row in EXPECTED_MAPPING],
        "forbidden_models": list(FORBIDDEN_MODELS),
        "network_inventory": {
            "bus_count": 10,
            "bus_indices": list(range(1, 11)),
            "line_count": 15,
            "pq_count": 2,
            "static_gen_count": 4,
            "static_generator_buses": [1, 2, 3, 4],
        },
        "parameter_card": {
            "fn": 60.0,
            "Tc": 0.01,
            "kw": 0.0,
            "kv": 0.01,
            "M": 10.0,
            "D": 0.0,
            "ra": 0.0,
            "xs": 0.2,
            "gammap": 1.0,
            "gammaq": 1.0,
        },
        "system_mva_base": 100.0,
        "device_rating_mva": 900.0,
        "step_abs_system_pu": 0.09,
        "channels": [dict(row) for row in CHANNELS],
        "arm_order": _arm_order(),
        "trajectory_count": 17,
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
            "omega_min_pu": 0.95,
            "omega_max_pu": 1.05,
        },
        "trace_signals": list(TRACE_SIGNALS),
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


def _setpoint_rows(system: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number in range(1, 5):
        idx = f"REGCV1_{number}"
        for channel in ("pref", "qref"):
            getter = getattr(system.RenGen, f"get_{channel}")
            rows.append({"idx": idx, "channel": channel, "value": float(getter(system, idx))})
    return rows


def apply_regcv1_setpoint_step(system: Any, arm: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one frozen R387 step and return all-eight-channel readback evidence."""

    pre = _setpoint_rows(system)
    target = arm["target_idx"]
    channel = arm["input_channel"]
    requested_absolute: float | None = None
    applied_readback: float | None = None
    if target is not None:
        matching = [row for row in pre if row["idx"] == target and row["channel"] == channel]
        if len(matching) != 1:
            raise RuntimeError("R387 target setpoint identity is not unique")
        requested_absolute = float(matching[0]["value"]) + float(arm["requested_delta"])
        setter = getattr(system.RenGen, f"set_{channel}")
        getter = getattr(system.RenGen, f"get_{channel}")
        setter(system, target, requested_absolute)
        applied_readback = float(getter(system, target))
    post = _setpoint_rows(system)
    return {
        "applied": target is not None,
        "pre_setpoints": pre,
        "post_setpoints": post,
        "requested_absolute": requested_absolute,
        "applied_readback": applied_readback,
    }


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _numeric_or_nonfinite_token(value: object) -> bool:
    return _finite(value) or (isinstance(value, str) and value.strip().lower() in NONFINITE_TOKENS)


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _close(left: object, right: object, tolerance: float) -> bool:
    return (
        _finite(left)
        and _finite(right)
        and math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    )


def _inventory_schema(inventory: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(inventory, Mapping):
            return False
        counts = inventory["forbidden_model_counts"]
        rows = inventory["regcv1"]
        normalized = [
            {"idx": str(row["idx"]), "bus": int(row["bus"]), "gen": int(row["gen"])} for row in rows
        ]
        return bool(
            inventory["network"] == contract["network_inventory"]
            and isinstance(counts, Mapping)
            and set(counts) == set(contract["forbidden_models"])
            and all(int(counts[name]) == 0 for name in contract["forbidden_models"])
            and inventory["forbidden_dae_names"] == []
            and normalized == contract["expected_mapping"]
            and len(rows) == 4
            and all(
                int(row["u"]) == 1 and _close(row["Sn"], contract["device_rating_mva"], 0.0)
                for row in rows
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _reference_schema(arm: Mapping[str, Any], contract: Mapping[str, Any]) -> bool:
    try:
        source = arm["reference_source"]
        refs = arm["references"]
        source_rows = source["rows"]
        ref_rows = refs["rows"]
        expected_idx = [row["idx"] for row in contract["expected_mapping"]]
        if not (
            source["captured"] is True
            and source["phase"] == "post_pflow_pre_tds_init"
            and source["pflow_converged_at_capture"] is True
            and source["tds_initialized_at_capture"] is False
            and _sequence(source_rows)
            and len(source_rows) == 4
            and [str(row["idx"]) for row in source_rows] == expected_idx
            and all(_finite(row["static_p"]) and _finite(row["static_q"]) for row in source_rows)
            and refs["checked"] is True
            and _close(refs["absolute_tolerance"], contract["reference_abs_tolerance"], 0.0)
            and _sequence(ref_rows)
            and len(ref_rows) == 4
            and [str(row["idx"]) for row in ref_rows] == expected_idx
        ):
            return False
        required = {
            "idx",
            "static_p",
            "static_q",
            "pref",
            "qref",
            "pref_match",
            "qref_match",
        }
        for source_row, ref_row in zip(source_rows, ref_rows, strict=True):
            if not (
                isinstance(ref_row, Mapping)
                and required.issubset(ref_row)
                and str(ref_row["idx"]) == str(source_row["idx"])
                and ref_row["static_p"] == source_row["static_p"]
                and ref_row["static_q"] == source_row["static_q"]
                and _finite(ref_row["pref"])
                and _finite(ref_row["qref"])
                and isinstance(ref_row["pref_match"], bool)
                and isinstance(ref_row["qref_match"], bool)
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _references_pass(arm: Mapping[str, Any], contract: Mapping[str, Any]) -> bool:
    tolerance = float(contract["reference_abs_tolerance"])
    source_rows = arm["reference_source"]["rows"]
    ref_rows = arm["references"]["rows"]
    for source, ref in zip(source_rows, ref_rows, strict=True):
        pref_match = _close(ref["pref"], source["static_p"], tolerance)
        qref_match = _close(ref["qref"], source["static_q"], tolerance)
        if not (
            ref["idx"] == source["idx"]
            and ref["static_p"] == source["static_p"]
            and ref["static_q"] == source["static_q"]
            and ref["pref_match"] is pref_match
            and ref["qref_match"] is qref_match
            and pref_match
            and qref_match
        ):
            return False
    return True


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
            elif not (isinstance(residual, str) and residual.strip().lower() in NONFINITE_TOKENS):
                return False
        if row_indices != normalized_indices:
            return False
        required_limit = {
            "model",
            "idx",
            "var",
            "limit_name",
            "limit_val",
            "unconstr",
        }
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
    if not _sequence(value) or len(value) != 8:
        return False
    expected = [
        (f"REGCV1_{number}", channel) for number in range(1, 5) for channel in ("pref", "qref")
    ]
    try:
        return [(str(row["idx"]), str(row["channel"])) for row in value] == expected and all(
            _finite(row["value"]) for row in value
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


def _trace_schema(value: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(value, Mapping) or value["captured"] is not True:
            return False
        time = value["time"]
        if not (
            _sequence(time)
            and len(time) >= 2
            and all(_finite(item) for item in time)
            and all(float(right) > float(left) for left, right in zip(time, time[1:]))
            and _close(time[0], 0.0, float(contract["tds_tolerance"]))
            and _close(
                time[-1],
                contract["tds_tf_seconds"],
                float(contract["tds_tolerance"]),
            )
            and _close(
                float(time[-1]) - float(time[0]),
                contract["tds_tf_seconds"],
                float(contract["tds_tolerance"]),
            )
            and isinstance(value["dae_finite"], bool)
            and isinstance(value["regcv1_finite"], bool)
        ):
            return False
        n_samples = len(time)
        bus_v = value["bus_v"]
        traces = value["regcv1"]
        idxes = [row["idx"] for row in contract["expected_mapping"]]
        if not (
            isinstance(bus_v, Mapping)
            and len(bus_v) == int(contract["network_inventory"]["bus_count"])
            and list(bus_v)
            == [str(value) for value in contract["network_inventory"]["bus_indices"]]
            and isinstance(traces, Mapping)
            and set(traces) == set(contract["trace_signals"])
        ):
            return False
        series = list(bus_v.values())
        for signal in contract["trace_signals"]:
            if not isinstance(traces[signal], Mapping) or list(traces[signal]) != idxes:
                return False
            series.extend(traces[signal].values())
        return all(
            _sequence(row)
            and len(row) == n_samples
            and all(_numeric_or_nonfinite_token(item) for item in row)
            for row in series
        )
    except (KeyError, TypeError, ValueError):
        return False


def _empty_reference_source(value: object) -> bool:
    return value == {
        "captured": False,
        "phase": None,
        "pflow_converged_at_capture": False,
        "tds_initialized_at_capture": False,
        "rows": [],
    }


def _empty_references(value: object) -> bool:
    return value == {"checked": False, "absolute_tolerance": None, "rows": []}


def _empty_action(value: object) -> bool:
    return value == {
        "applied": False,
        "pre_setpoints": [],
        "post_setpoints": [],
        "requested_absolute": None,
        "applied_readback": None,
    }


def _empty_trajectory(value: object) -> bool:
    return value == {
        "captured": False,
        "time": [],
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }


def _pre_trajectory_failure_sentinel(arm: Mapping[str, Any]) -> bool:
    return bool(
        _empty_action(arm["action"])
        and _empty_trajectory(arm["trajectory"])
        and arm["solver"]["tds_converged"] is False
        and arm["solver"]["terminal_time_seconds"] is None
    )


def _no_advance_sentinel(arm: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return bool(
        _action_schema(arm["action"], expected)
        and _empty_trajectory(arm["trajectory"])
        and arm["solver"]["pflow_converged"] is True
        and arm["solver"]["tds_initialized"] is True
        and arm["solver"]["tds_test_ok"] is True
        and isinstance(arm["solver"]["tds_converged"], bool)
        and _finite(arm["solver"]["terminal_time_seconds"])
    )


def _pflow_failure_sentinel(arm: Mapping[str, Any]) -> bool:
    return bool(
        _empty_reference_source(arm["reference_source"])
        and _empty_references(arm["references"])
        and _pre_trajectory_failure_sentinel(arm)
        and arm["solver"]["setup_completed"] is True
        and arm["solver"]["pflow_converged"] is False
        and arm["solver"]["tds_initialized"] is False
        and arm["solver"]["tds_test_ok"] is False
    )


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


def _arm_schema(arm: object, expected: Mapping[str, Any], contract: Mapping[str, Any]) -> bool:
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
            and _solver_schema(arm["solver"], allow_missing_terminal=scientific_error is not None)
        )
        if not common:
            return False
        if scientific_error == "PFlow.run returned a non-success value":
            return _pflow_failure_sentinel(arm)
        if scientific_error == "native TDS initialization guard failed":
            return bool(
                _reference_schema(arm, contract)
                and _pre_trajectory_failure_sentinel(arm)
                and arm["solver"]["pflow_converged"] is True
                and (
                    arm["solver"]["tds_initialized"] is False
                    or arm["solver"]["tds_test_ok"] is False
                )
            )
        if scientific_error == "TDS did not advance":
            return bool(
                _reference_schema(arm, contract)
                and _no_advance_sentinel(arm, expected)
                and _action_baseline_matches_references(arm, contract)
            )
        return bool(
            _reference_schema(arm, contract)
            and _action_schema(arm["action"], expected)
            and _trace_schema(arm["trajectory"], contract)
            and _action_baseline_matches_references(arm, contract)
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
                    "regcv1_source_sha256",
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
        pre = {(row["idx"], row["channel"]): float(row["value"]) for row in action["pre_setpoints"]}
        post = {
            (row["idx"], row["channel"]): float(row["value"]) for row in action["post_setpoints"]
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
    power_limit = float(contract["device_rating_mva"]) / float(contract["system_mva_base"])
    finite_ok = True
    electrical_ok = True
    for arm in arms:
        trajectory = arm["trajectory"]
        if trajectory["captured"] is not True:
            finite_ok = False
            electrical_ok = False
            continue
        traces = trajectory["regcv1"]
        if trajectory["dae_finite"] is not True or trajectory["regcv1_finite"] is not True:
            finite_ok = False
        series = list(trajectory["bus_v"].values())
        for signal in contract["trace_signals"]:
            series.extend(traces[signal].values())
        if not all(all(_finite(value) for value in row) for row in series):
            finite_ok = False
            electrical_ok = False
            continue
        for values in trajectory["bus_v"].values():
            if min(values) < limits["bus_v_min_pu"] or max(values) > limits["bus_v_max_pu"]:
                electrical_ok = False
        for idx in traces["Pe"]:
            for pe, qe, current_d, current_q, omega in zip(
                traces["Pe"][idx],
                traces["Qe"][idx],
                traces["Id"][idx],
                traces["Iq"][idx],
                traces["omega"][idx],
                strict=True,
            ):
                if (
                    math.hypot(float(current_d), float(current_q))
                    > limits["current_magnitude_max_pu"]
                ):
                    electrical_ok = False
                if math.hypot(float(pe), float(qe)) > power_limit:
                    electrical_ok = False
                if not limits["omega_min_pu"] <= float(omega) <= limits["omega_max_pu"]:
                    electrical_ok = False
    return finite_ok, electrical_ok


def _response_rows(
    arms: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    zero = arms[0]["trajectory"]["regcv1"]
    channel_map = {row["input"]: row for row in contract["channels"]}
    floor = float(contract["authority_abs_floor_system_pu"])
    responses: list[dict[str, Any]] = []
    for arm in arms[1:]:
        target = arm["target_idx"]
        mapping = channel_map[arm["input_channel"]]
        output = mapping["output"]
        cross_output = mapping["cross_output"]
        achieved = {
            idx: float(arm["trajectory"]["regcv1"][output][idx][-1]) - float(zero[output][idx][-1])
            for idx in zero[output]
        }
        target_response = achieved[target]
        non_target_max = max(abs(value) for idx, value in achieved.items() if idx != target)
        cross_response = float(arm["trajectory"]["regcv1"][cross_output][target][-1]) - float(
            zero[cross_output][target][-1]
        )
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

    lookup = {(row["target_idx"], row["input_channel"], row["sign"]): row for row in responses}
    paired: list[dict[str, Any]] = []
    pair_floor = float(contract["paired_separation_floor_system_pu"])
    for idx in [row["idx"] for row in contract["expected_mapping"]]:
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
        "claim_scope": "signed per-device REGCV1 Pref/Qref dynamic authority only",
        "next_gate": (
            "separately_registered_deterministic_pq_decoupling"
            if classification == "REGCV1-SIGNED-AUTHORITY-PASS"
            else None
        ),
        "retry_authorized": False,
        "training_authorized": False,
    }


def classify_regcv1_signed_authority_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one immutable R387 full-bank execution record fail-closed."""

    spec = build_signed_authority_contract() if contract is None else contract
    if spec != build_signed_authority_contract():
        return _analysis("ANALYSIS-INVALID", {"record_integrity": False})
    if not _record_integrity(record, spec):
        return _analysis("ANALYSIS-INVALID", {"record_integrity": False})

    arms = record["arms"]
    finite_ok, electrical_ok = _finite_and_electrical_checks(arms, spec)
    complete_trajectories = all(
        arm["scientific_error"] is None and arm["trajectory"]["captured"] is True for arm in arms
    )
    responses, paired = _response_rows(arms, spec) if complete_trajectories else ([], [])
    checks = {
        "record_integrity": True,
        "reference_preservation": all(
            arm["scientific_error"] != "PFlow.run returned a non-success value"
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
        "REGCV1-SIGNED-AUTHORITY-PASS" if all(checks.values()) else "STOP-REGCV1-SIGNED-AUTHORITY"
    )
    return _analysis(
        classification,
        checks,
        responses=responses,
        paired=paired,
    )


__all__ = [
    "apply_regcv1_setpoint_step",
    "build_signed_authority_contract",
    "classify_regcv1_signed_authority_record",
    "payload_sha256",
]
