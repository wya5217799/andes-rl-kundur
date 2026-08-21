"""Prospective contract and pure classifier for the R385 clean-object gate."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

EXPECTED_MAPPING = tuple(
    {"idx": f"REGCV1_{index}", "bus": index, "gen": index}
    for index in range(1, 5)
)
STATIC_MODELS = ("Bus", "PQ", "PV", "Slack", "Line", "Area")
FORBIDDEN_MODELS = ("GENROU", "TGOV1", "EXDC2", "Toggler")
DRIFT_SIGNALS = ("Pe", "Qe", "dw", "omega", "v")
SCIENTIFIC_ERRORS = {
    None,
    "PFlow.run returned a non-success value",
    "native TDS initialization guard failed",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def build_clean_contract() -> dict[str, Any]:
    """Return the complete JSON-compatible R385 scientific contract."""

    return {
        "schema_version": 1,
        "round": "R385",
        "question": "Q-0105",
        "static_models": list(STATIC_MODELS),
        "forbidden_models": list(FORBIDDEN_MODELS),
        "expected_mapping": [dict(row) for row in EXPECTED_MAPPING],
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
        "reference_abs_tolerance": 1.0e-12,
        "drift_signals": list(DRIFT_SIGNALS),
        "retry_authorized": False,
        "training_authorized": False,
    }


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _is_row_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _diagnostics_pass(record: Mapping[str, Any]) -> bool:
    try:
        diagnostics = record["initialization_diagnostics"]
        residuals = diagnostics["residuals"]
        bad_indices = diagnostics["bad_combined_indices"]
        clamped = diagnostics["clamped_limits"]
        equation_count = int(diagnostics["equation_count"])
        residual_count = int(diagnostics["residual_count"])
        tolerance = float(record["solver"]["tds_tolerance"])
        if (
            diagnostics["captured"] is not True
            or equation_count < 0
            or residual_count < 0
            or not _finite(tolerance)
            or tolerance <= 0
            or not _is_row_sequence(residuals)
            or not _is_row_sequence(bad_indices)
            or not _is_row_sequence(clamped)
            or residual_count != len(residuals)
            or residual_count != len(bad_indices)
        ):
            return False

        normalized_indices = [int(value) for value in bad_indices]
        if (
            len(set(normalized_indices)) != len(normalized_indices)
            or any(value < 0 or value >= equation_count for value in normalized_indices)
        ):
            return False

        row_indices: list[int] = []
        required_residual = {
            "combined_index",
            "name",
            "residual",
            "equation",
            "model",
            "idx",
        }
        nonfinite_tokens = {"nan", "inf", "+inf", "-inf"}
        for row in residuals:
            if not isinstance(row, Mapping) or not required_residual.issubset(row):
                return False
            combined_index = int(row["combined_index"])
            row_indices.append(combined_index)
            if (
                not isinstance(row["name"], str)
                or not row["name"]
                or not isinstance(row["equation"], str)
                or not isinstance(row["model"], str)
            ):
                return False
            residual = row["residual"]
            if _finite(residual):
                if abs(float(residual)) < tolerance:
                    return False
            elif not (
                isinstance(residual, str)
                and residual.strip().lower() in nonfinite_tokens
            ):
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


def _mapping_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        rows = record["inventory"]["regcv1"]
        normalized = [
            {"idx": str(row["idx"]), "bus": int(row["bus"]), "gen": int(row["gen"])}
            for row in rows
        ]
        return bool(
            normalized == spec["expected_mapping"]
            and len(rows) == 4
            and all(int(row["u"]) == 1 for row in rows)
            and all(_finite(row["Sn"]) and float(row["Sn"]) > 0 for row in rows)
            and record["inventory"]["network"] == spec["network_inventory"]
        )
    except (KeyError, TypeError, ValueError):
        return False


def _structural_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        counts = record["inventory"]["forbidden_model_counts"]
        return bool(
            set(counts) == set(spec["forbidden_models"])
            and all(int(counts[name]) == 0 for name in spec["forbidden_models"])
            and record["inventory"]["forbidden_dae_names"] == []
        )
    except (KeyError, TypeError, ValueError):
        return False


def _integrity_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        source = record["source"]
        if (
            record["schema_version"] != 1
            or record["round"] != "R385"
            or record["question"] != "Q-0105"
            or record["contract_sha256"] != _payload_sha256(spec)
            or record["formal_input_complete"] is not True
            or record["execution_error"] is not None
            or record["scientific_error"] not in SCIENTIFIC_ERRORS
            or record["training_executed"] is not False
            or not isinstance(record["trajectory_attempted"], bool)
            or not isinstance(record["physical_trajectory_executed"], bool)
            or isinstance(record["trajectory_count"], bool)
            or record["trajectory_count"] not in (0, 1)
            or record["trajectory_count"] != int(record["physical_trajectory_executed"])
            or (
                record["physical_trajectory_executed"] is True
                and record["trajectory_attempted"] is not True
            )
            or source["xlsx_json_static_equal"] is not True
            or source["derived_case_deterministic"] is not True
            or not all(
                _valid_sha256(source[key])
                for key in (
                    "xlsx_case_sha256",
                    "json_case_sha256",
                    "derived_case_sha256",
                )
            )
            or not _diagnostics_pass(record)
        ):
            return False
        return _mapping_pass(record, spec) and _structural_pass(record, spec)
    except (KeyError, TypeError, ValueError):
        return False


def _references_pass(record: Mapping[str, Any]) -> bool:
    try:
        refs = record["references"]
        rows = refs["rows"]
        return bool(
            refs["checked"] is True
            and len(rows) == 4
            and [str(row["idx"]) for row in rows]
            == [f"REGCV1_{index}" for index in range(1, 5)]
            and all(
                row["pref_match"] is True
                and row["qref_match"] is True
                and all(
                    _finite(row[key])
                    for key in ("static_p", "static_q", "pref", "qref")
                )
                for row in rows
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _solver_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        solver = record["solver"]
        return bool(
            record["physical_trajectory_executed"] is True
            and record["trajectory_count"] == 1
            and all(
                solver[key] is True
                for key in (
                    "setup_completed",
                    "pflow_converged",
                    "tds_initialized",
                    "tds_test_ok",
                    "tds_converged",
                )
            )
            and _finite(solver["tds_tolerance"])
            and float(solver["tds_tolerance"]) > 0
            and _finite(solver["terminal_time_seconds"])
            and abs(
                float(solver["terminal_time_seconds"])
                - float(spec["tds_tf_seconds"])
            )
            <= max(1.0e-12, float(solver["tds_tolerance"]))
        )
    except (KeyError, TypeError, ValueError):
        return False


def _finite_pass(record: Mapping[str, Any]) -> bool:
    try:
        guard = record["finite_guard"]
        return bool(
            guard["checked"] is True
            and guard["dae_finite"] is True
            and guard["regcv1_finite"] is True
        )
    except (KeyError, TypeError):
        return False


def _drift_pass(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        drift = record["drift"]
        values = drift["max_abs_by_signal"]
        tol = float(record["solver"]["tds_tolerance"])
        return bool(
            drift["checked"] is True
            and set(values) == set(spec["drift_signals"])
            and all(_finite(values[name]) and 0 <= float(values[name]) <= tol for name in values)
        )
    except (KeyError, TypeError, ValueError):
        return False


def classify_regcv1_clean_init_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the typed R385 decision for one immutable execution record."""

    spec = build_clean_contract() if contract is None else contract
    if not _integrity_pass(record, spec):
        return _analysis("ANALYSIS-INVALID", {"record_integrity": False})

    checks = {
        "record_integrity": True,
        "source_integrity": True,
        "structural_absence": True,
        "object_mapping": True,
        "initialization_residuals_zero": record["initialization_diagnostics"][
            "residual_count"
        ]
        == 0,
        "post_init_references": _references_pass(record),
        "native_solver": _solver_pass(record, spec),
        "finite_values": _finite_pass(record),
        "zero_input_drift": _drift_pass(record, spec),
    }
    classification = (
        "REGCV1-CLEAN-INIT-PASS"
        if all(checks.values())
        else "STOP-REGCV1-CLEAN-INITIALIZATION"
    )
    return _analysis(classification, checks)


def _analysis(classification: str, checks: Mapping[str, bool]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": "R385",
        "question": "Q-0105",
        "classification": classification,
        "checks": dict(checks),
        "claim_scope": "structurally clean four-REGCV1 initialization and zero-input validity only",
        "next_gate": (
            "signed_dynamic_pref_qref_authority"
            if classification == "REGCV1-CLEAN-INIT-PASS"
            else None
        ),
        "retry_authorized": False,
        "training_authorized": False,
    }


__all__ = ["build_clean_contract", "classify_regcv1_clean_init_record"]
