"""Integrity-corrected R388 classifier for the frozen R387 authority bank."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from andes_rl_kundur.evaluation import regcv1_signed_authority_gate as parent

ROUND_ID = "R388"
QUESTION_ID = "Q-0106"
PARTIAL_ERROR = "TDS terminated before horizon"
SCIENTIFIC_ERRORS = parent.SCIENTIFIC_ERRORS | {PARTIAL_ERROR}


def build_signed_authority_correction_contract() -> dict[str, Any]:
    """Return R387's science unchanged plus the sealed R388 evidence schema."""

    parent_contract = parent.build_signed_authority_contract()
    contract = copy.deepcopy(parent_contract)
    contract.update(
        {
            "schema_version": 2,
            "round": ROUND_ID,
            "parent_round": "R387",
            "correction_of_contract_sha256": parent.payload_sha256(parent_contract),
            "trajectory_evidence": {
                "start_time_seconds": 0.0,
                "max_first_sample_time_seconds": 1.0 / 30.0
                + float(parent_contract["tds_tolerance"]),
                "bus_identity_order_independent": True,
                "initial_snapshot_required": True,
                "advanced_partial_error": PARTIAL_ERROR,
            },
        }
    )
    return contract


def _empty_initial() -> dict[str, Any]:
    return {
        "captured": False,
        "time_seconds": None,
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }


def _empty_trajectory(value: object) -> bool:
    return value == {
        "captured": False,
        "start_time_seconds": None,
        "initial": _empty_initial(),
        "time": [],
        "dae_finite": False,
        "regcv1_finite": False,
        "bus_v": {},
        "regcv1": {},
    }


def _identity_sets(
    bus_values: object,
    trace_values: object,
    contract: Mapping[str, Any],
) -> bool:
    if not isinstance(bus_values, Mapping) or not isinstance(trace_values, Mapping):
        return False
    expected_buses = {
        str(value) for value in contract["network_inventory"]["bus_indices"]
    }
    expected_idxes = {str(row["idx"]) for row in contract["expected_mapping"]}
    return bool(
        set(bus_values) == expected_buses
        and set(trace_values) == set(contract["trace_signals"])
        and all(
            isinstance(trace_values[signal], Mapping)
            and set(trace_values[signal]) == expected_idxes
            for signal in contract["trace_signals"]
        )
    )


def _initial_schema(value: object, contract: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(value, Mapping):
            return False
        if not (
            value["captured"] is True
            and parent._close(
                value["time_seconds"],
                contract["trajectory_evidence"]["start_time_seconds"],
                0.0,
            )
            and isinstance(value["dae_finite"], bool)
            and isinstance(value["regcv1_finite"], bool)
            and _identity_sets(value["bus_v"], value["regcv1"], contract)
        ):
            return False
        values = list(value["bus_v"].values())
        for signal in contract["trace_signals"]:
            values.extend(value["regcv1"][signal].values())
        return all(parent._numeric_or_nonfinite_token(item) for item in values)
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
        tolerance = float(contract["tds_tolerance"])
        start = float(contract["trajectory_evidence"]["start_time_seconds"])
        time = value["time"]
        if not (
            parent._close(value["start_time_seconds"], start, 0.0)
            and _initial_schema(value["initial"], contract)
            and parent._sequence(time)
            and len(time) >= 2
            and all(parent._finite(item) for item in time)
            and all(float(right) > float(left) for left, right in zip(time, time[1:]))
            and float(time[0]) > start
            and float(time[0])
            <= float(contract["trajectory_evidence"]["max_first_sample_time_seconds"])
            and parent._close(time[-1], terminal_time, tolerance)
            and isinstance(value["dae_finite"], bool)
            and isinstance(value["regcv1_finite"], bool)
            and _identity_sets(value["bus_v"], value["regcv1"], contract)
        ):
            return False
        horizon = float(contract["tds_tf_seconds"])
        if partial:
            if not (float(terminal_time) > start and float(terminal_time) < horizon - tolerance):
                return False
        elif not parent._close(terminal_time, horizon, tolerance):
            return False
        n_samples = len(time)
        series = list(value["bus_v"].values())
        for signal in contract["trace_signals"]:
            series.extend(value["regcv1"][signal].values())
        return all(
            parent._sequence(row)
            and len(row) == n_samples
            and all(parent._numeric_or_nonfinite_token(item) for item in row)
            for row in series
        )
    except (KeyError, TypeError, ValueError):
        return False


def _initial_only_no_advance(
    value: object,
    contract: Mapping[str, Any],
) -> bool:
    try:
        return bool(
            isinstance(value, Mapping)
            and value["captured"] is False
            and parent._close(
                value["start_time_seconds"],
                contract["trajectory_evidence"]["start_time_seconds"],
                0.0,
            )
            and _initial_schema(value["initial"], contract)
            and value["time"] == []
            and value["dae_finite"] is False
            and value["regcv1_finite"] is False
            and value["bus_v"] == {}
            and value["regcv1"] == {}
        )
    except (KeyError, TypeError):
        return False


def _pre_trajectory_failure_sentinel(arm: Mapping[str, Any]) -> bool:
    return bool(
        parent._empty_action(arm["action"])
        and _empty_trajectory(arm["trajectory"])
        and arm["solver"]["tds_converged"] is False
        and arm["solver"]["terminal_time_seconds"] is None
    )


def _pflow_failure_sentinel(arm: Mapping[str, Any]) -> bool:
    return bool(
        parent._empty_reference_source(arm["reference_source"])
        and parent._empty_references(arm["references"])
        and _pre_trajectory_failure_sentinel(arm)
        and arm["solver"]["setup_completed"] is True
        and arm["solver"]["pflow_converged"] is False
        and arm["solver"]["tds_initialized"] is False
        and arm["solver"]["tds_test_ok"] is False
    )


def _no_advance_sentinel(
    arm: Mapping[str, Any],
    expected: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> bool:
    return bool(
        parent._action_schema(arm["action"], expected)
        and _initial_only_no_advance(arm["trajectory"], contract)
        and arm["solver"]["pflow_converged"] is True
        and arm["solver"]["tds_initialized"] is True
        and arm["solver"]["tds_test_ok"] is True
        and arm["solver"]["tds_converged"] is False
        and parent._close(
            arm["solver"]["terminal_time_seconds"],
            contract["trajectory_evidence"]["start_time_seconds"],
            float(contract["tds_tolerance"]),
        )
    )


def _arm_schema(
    arm: object,
    expected: Mapping[str, Any],
    contract: Mapping[str, Any],
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
            and parent._inventory_schema(arm["inventory"], contract)
            and parent._diagnostics_schema(
                arm["initialization_diagnostics"],
                float(contract["tds_tolerance"]),
            )
            and parent._solver_schema(
                arm["solver"],
                allow_missing_terminal=scientific_error is not None,
            )
        )
        if not common:
            return False
        if scientific_error == "PFlow.run returned a non-success value":
            return _pflow_failure_sentinel(arm)
        if scientific_error == "native TDS initialization guard failed":
            return bool(
                parent._reference_schema(arm, contract)
                and _pre_trajectory_failure_sentinel(arm)
                and arm["solver"]["pflow_converged"] is True
                and (
                    arm["solver"]["tds_initialized"] is False
                    or arm["solver"]["tds_test_ok"] is False
                )
            )
        if scientific_error == "TDS did not advance":
            return bool(
                parent._reference_schema(arm, contract)
                and _no_advance_sentinel(arm, expected, contract)
                and parent._action_baseline_matches_references(arm, contract)
            )
        if scientific_error == PARTIAL_ERROR:
            return bool(
                parent._reference_schema(arm, contract)
                and parent._action_schema(arm["action"], expected)
                and parent._action_baseline_matches_references(arm, contract)
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
            parent._reference_schema(arm, contract)
            and parent._action_schema(arm["action"], expected)
            and parent._action_baseline_matches_references(arm, contract)
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
            record["schema_version"] == 2
            and record["round"] == ROUND_ID
            and record["question"] == QUESTION_ID
            and record["contract_sha256"] == parent.payload_sha256(contract)
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
                parent._valid_sha256(source[key])
                for key in (
                    "xlsx_case_sha256",
                    "json_case_sha256",
                    "derived_case_sha256",
                    "regcv1_source_sha256",
                )
            )
            and parent._sequence(arms)
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


def _finite_and_electrical_checks(
    arms: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[bool, bool]:
    finite_ok, electrical_ok = parent._finite_and_electrical_checks(arms, contract)
    limits = contract["electrical_limits"]
    power_limit = float(contract["device_rating_mva"]) / float(contract["system_mva_base"])
    for arm in arms:
        initial = arm["trajectory"]["initial"]
        if initial["captured"] is not True:
            finite_ok = False
            electrical_ok = False
            continue
        traces = initial["regcv1"]
        values = list(initial["bus_v"].values())
        for signal in contract["trace_signals"]:
            values.extend(traces[signal].values())
        if (
            initial["dae_finite"] is not True
            or initial["regcv1_finite"] is not True
            or not all(parent._finite(value) for value in values)
        ):
            finite_ok = False
            electrical_ok = False
            continue
        if any(
            not limits["bus_v_min_pu"] <= float(value) <= limits["bus_v_max_pu"]
            for value in initial["bus_v"].values()
        ):
            electrical_ok = False
        for idx in traces["Pe"]:
            if math.hypot(float(traces["Id"][idx]), float(traces["Iq"][idx])) > limits[
                "current_magnitude_max_pu"
            ]:
                electrical_ok = False
            if math.hypot(float(traces["Pe"][idx]), float(traces["Qe"][idx])) > power_limit:
                electrical_ok = False
            if not limits["omega_min_pu"] <= float(traces["omega"][idx]) <= limits[
                "omega_max_pu"
            ]:
                electrical_ok = False
    return finite_ok, electrical_ok


def _analysis(
    classification: str,
    checks: Mapping[str, bool],
    *,
    responses: Sequence[Mapping[str, Any]] = (),
    paired: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "schema_version": 2,
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


def classify_regcv1_signed_authority_correction_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one immutable R388 record while preserving R387's science."""

    canonical = build_signed_authority_correction_contract()
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
        parent._response_rows(arms, spec) if complete_trajectories else ([], [])
    )
    checks = {
        "record_integrity": True,
        "reference_preservation": all(
            arm["scientific_error"] != "PFlow.run returned a non-success value"
            and parent._references_pass(arm, spec)
            for arm in arms
        ),
        "initialization_diagnostics_zero": parent._initialization_pass(arms),
        "native_solver": parent._solver_pass(arms, spec),
        "finite_values": finite_ok,
        "electrical_envelope": electrical_ok,
        "action_identity": parent._action_identity_pass(arms, spec),
        "signed_self_response": complete_trajectories
        and all(row["signed_pass"] for row in responses),
        "target_attribution": complete_trajectories
        and all(row["attribution_pass"] for row in responses),
        "paired_separation": complete_trajectories and all(row["pass"] for row in paired),
    }
    classification = (
        "REGCV1-SIGNED-AUTHORITY-PASS"
        if all(checks.values())
        else "STOP-REGCV1-SIGNED-AUTHORITY"
    )
    return _analysis(classification, checks, responses=responses, paired=paired)


__all__ = [
    "build_signed_authority_correction_contract",
    "classify_regcv1_signed_authority_correction_record",
]
