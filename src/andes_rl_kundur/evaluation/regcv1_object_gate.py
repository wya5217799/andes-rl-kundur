"""Pure prospective contract and classifier for the R384 REGCV1 gate.

This module deliberately imports neither ANDES nor the experiment runner.  It
recomputes the scientific decision from one immutable execution record so an
incomplete record cannot be mistaken for a physical failure or a pass.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

EXPECTED_MAPPING = tuple(
    {"idx": f"REGCV1_{index}", "bus": index, "gen": index}
    for index in range(1, 5)
)
EXPECTED_CHAIN_MODELS = ("GENROU", "TGOV1", "EXDC2")
DRIFT_SIGNALS = ("Pe", "Qe", "dw", "omega", "v")


def build_contract() -> dict[str, Any]:
    """Return the complete JSON-compatible R384 scientific contract."""

    return {
        "schema_version": 1,
        "round": "R384",
        "question": "Q-0104",
        "case": "kundur/kundur_full.xlsx",
        "expected_mapping": [dict(row) for row in EXPECTED_MAPPING],
        "disabled_chain_models": list(EXPECTED_CHAIN_MODELS),
        "network_inventory": {
            "bus_count": 10,
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
        "tds_tf_seconds": 0.2,
        "drift_signals": list(DRIFT_SIGNALS),
        "retry_authorized": False,
        "training_authorized": False,
    }


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _record_integrity(record: Mapping[str, Any]) -> bool:
    """Check structure and formal completeness, not scientific success."""

    try:
        if (
            record["schema_version"] != 1
            or record["round"] != "R384"
            or record["question"] != "Q-0104"
            or not isinstance(record["contract_sha256"], str)
            or len(record["contract_sha256"]) != 64
            or record["formal_input_complete"] is not True
            or not isinstance(record["physical_trajectory_executed"], bool)
            or record["trajectory_count"] not in (0, 1)
            or record["trajectory_count"]
            != int(record["physical_trajectory_executed"])
            or record["training_executed"] is not False
            or record["execution_error"] is not None
        ):
            return False
        inventory = record["inventory"]
        interface = record["interface_identity"]
        solver = record["solver"]
        finite_guard = record["finite_guard"]
        drift = record["drift"]
        if not all(
            isinstance(value, Mapping)
            for value in (inventory, interface, solver, finite_guard, drift)
        ):
            return False
        if not isinstance(inventory["regcv1"], Sequence) or isinstance(
            inventory["regcv1"], (str, bytes)
        ):
            return False
        if not isinstance(inventory["disabled_dynamic_chain"], Sequence) or isinstance(
            inventory["disabled_dynamic_chain"], (str, bytes)
        ):
            return False
        if not isinstance(inventory["network"], Mapping):
            return False
        for channel in ("pref", "qref"):
            rows = interface[channel]
            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
                return False
        if not isinstance(drift["max_abs_by_signal"], Mapping):
            return False
        required_solver = {
            "setup_completed",
            "pflow_converged",
            "tds_initialized",
            "tds_test_ok",
            "tds_converged",
            "terminal_time_seconds",
            "tds_tolerance",
        }
        if not required_solver.issubset(solver):
            return False
        if not _is_finite_number(solver["terminal_time_seconds"]):
            return False
        if not _is_finite_number(solver["tds_tolerance"]):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _mapping_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    actual = record["inventory"]["regcv1"]
    if len(actual) != 4:
        return False
    try:
        normalized = [
            {
                "idx": str(row["idx"]),
                "bus": int(row["bus"]),
                "gen": int(row["gen"]),
            }
            for row in actual
        ]
        return bool(
            normalized == spec["expected_mapping"]
            and all(int(row["u"]) == 1 for row in actual)
            and all(_is_finite_number(row["Sn"]) and float(row["Sn"]) > 0 for row in actual)
            and record["inventory"]["network"] == spec["network_inventory"]
        )
    except (KeyError, TypeError, ValueError):
        return False


def _replacement_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    rows = record["inventory"]["disabled_dynamic_chain"]
    expected = {
        (model, index, index)
        for model in spec["disabled_chain_models"]
        for index in range(1, 5)
    }
    try:
        actual = {
            (str(row["model"]), int(row["idx"]), int(row["syn"]))
            for row in rows
            if int(row["u"]) == 0
        }
    except (KeyError, TypeError, ValueError):
        return False
    return actual == expected and len(rows) == len(expected)


def _interface_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    identity = record["interface_identity"]
    if identity.get("attempted") is not True or identity.get("completed") is not True:
        return False
    expected_ids = [row["idx"] for row in spec["expected_mapping"]]
    for channel in ("pref", "qref"):
        rows = identity[channel]
        if len(rows) != 4 or [str(row.get("idx")) for row in rows] != expected_ids:
            return False
        for row in rows:
            try:
                baseline = float(row["baseline"])
                probe = float(row["probe"])
                readback = float(row["readback"])
                restored = float(row["restored"])
            except (KeyError, TypeError, ValueError):
                return False
            if not all(math.isfinite(value) for value in (baseline, probe, readback, restored)):
                return False
            if (
                probe != math.nextafter(baseline, math.inf)
                or readback != probe
                or restored != baseline
                or row.get("non_target_unchanged") is not True
            ):
                return False
    return True


def _solver_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    solver = record["solver"]
    return bool(
        record["physical_trajectory_executed"] is True
        and record["trajectory_count"] == 1
        and all(
            solver.get(key) is True
            for key in (
                "setup_completed",
                "pflow_converged",
                "tds_initialized",
                "tds_test_ok",
                "tds_converged",
            )
        )
        and abs(float(solver["terminal_time_seconds"]) - float(spec["tds_tf_seconds"]))
        <= max(1.0e-12, float(solver["tds_tolerance"]))
        and float(solver["tds_tolerance"]) > 0.0
    )


def _finite_pass(record: Mapping[str, Any]) -> bool:
    guard = record["finite_guard"]
    return bool(
        guard.get("checked") is True
        and guard.get("dae_finite") is True
        and guard.get("regcv1_finite") is True
    )


def _drift_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    drift = record["drift"]
    values = drift["max_abs_by_signal"]
    tolerance = float(record["solver"]["tds_tolerance"])
    return bool(
        drift.get("checked") is True
        and set(values) == set(spec["drift_signals"])
        and all(
            _is_finite_number(values[name])
            and 0.0 <= float(values[name]) <= tolerance
            for name in spec["drift_signals"]
        )
    )


def classify_regcv1_object_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the registered typed decision for one immutable R384 record."""

    spec = build_contract() if contract is None else contract
    if not _record_integrity(record):
        return _analysis("ANALYSIS-INVALID", {"record_integrity": False})
    checks = {
        "record_integrity": True,
        "object_mapping": _mapping_pass(record, spec),
        "dynamic_chain_replacement": _replacement_pass(record, spec),
        "setpoint_interface_identity": _interface_pass(record, spec),
        "native_solver": _solver_pass(record, spec),
        "finite_values": _finite_pass(record),
        "zero_input_drift": _drift_pass(record, spec),
    }
    classification = (
        "REGCV1-OBJECT-INIT-PASS"
        if all(checks.values())
        else "STOP-REGCV1-OBJECT-INITIALIZATION"
    )
    return _analysis(classification, checks)


def _analysis(classification: str, checks: Mapping[str, bool]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": "R384",
        "question": "Q-0104",
        "classification": classification,
        "checks": dict(checks),
        "claim_scope": "four-REGCV1 object, interface identity, and zero-input initialization only",
        "next_gate": "signed_dynamic_pref_qref_authority",
        "retry_authorized": False,
        "training_authorized": False,
    }


__all__ = ["build_contract", "classify_regcv1_object_record"]
