"""Classify the prospective stock-REGF2 Kundur object/init gate.

The module owns the immutable scientific contract and, after the execution
record seam is implemented, its fail-closed pure classifier.  It imports no
ANDES runtime code so records remain replayable on Windows.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


STATIC_MODELS = ("Bus", "PQ", "PV", "Slack", "Line", "Area")
FORBIDDEN_MODELS = (
    "REGCV1",
    "REGCV2",
    "REGF1",
    "REGF3",
    "GENROU",
    "TGOV1",
    "EXDC2",
    "Toggler",
    "Toggle",
)
EXPECTED_MAPPING = tuple(
    {"idx": f"REGF2_{index}", "bus": index, "gen": index}
    for index in range(1, 5)
)
NETWORK_INVENTORY = {
    "bus_count": 10,
    "line_count": 15,
    "pq_count": 2,
    "static_gen_count": 4,
    "static_generator_buses": [1, 2, 3, 4],
}
REGF2_PARAMETER_CARD = {
    "rf": 0.0,
    "xf": 0.2,
    "Vdip": 0.8,
    "Tfrz": 0.0,
    "PQFLAG": 1.0,
    "fn": 60.0,
    "dwmax": 75.0,
    "dwmin": -75.0,
    "wdrp": 0.033,
    "Qdrp": 0.045,
    "Tr": 0.005,
    "Te": 0.005,
    "KPi": 0.5,
    "KIi": 20.0,
    "KPv": 3.0,
    "KIv": 10.0,
    "Pmax": 1.0,
    "Pmin": -1.0,
    "KPplim": 5.0,
    "KIplim": 30.0,
    "Qmax": 1.0,
    "Qmin": -1.0,
    "KPqlim": 0.1,
    "KIqlim": 1.5,
    "Tpm": 0.025,
    "gammap": 1.0,
    "gammaq": 1.0,
    "mf": 0.15,
    "dd": 0.11,
    "pll": None,
}
REGF2_RUNTIME_PARAMETER_CARD = {
    **REGF2_PARAMETER_CARD,
    # ANDES stores these converted from the 900-MVA device base to the
    # 100-MVA system base after setup.
    "xf": 0.2 * 100.0 / 900.0,
    "Pmax": 1.0 * 900.0 / 100.0,
    "Pmin": -1.0 * 900.0 / 100.0,
    "Qmax": 1.0 * 900.0 / 100.0,
    "Qmin": -1.0 * 900.0 / 100.0,
}
SCIENTIFIC_ERRORS = {
    None,
    "PFlow did not converge",
    "TDS initialization failed",
    "TDS did not converge",
    "TDS did not reach horizon",
}
TRACE_SIGNALS = ("Pe", "Qe", "Id", "Iq", "virtual_frequency")


def build_regf2_object_init_contract() -> dict[str, Any]:
    """Return a detached canonical R389 contract."""

    return deepcopy(
        {
            "schema_version": 1,
            "round": "R389",
            "question": "Q-0107",
            "andes_version": "2.0.0",
            "static_models": list(STATIC_MODELS),
            "forbidden_models": list(FORBIDDEN_MODELS),
            "expected_mapping": list(EXPECTED_MAPPING),
            "network_inventory": NETWORK_INVENTORY,
            "parameter_card": REGF2_PARAMETER_CARD,
            "runtime_parameter_card": REGF2_RUNTIME_PARAMETER_CARD,
            "device_rating_mva": 900.0,
            "system_mva_base": 100.0,
            "xlsx_case_sha256": (
                "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
            ),
            "json_case_sha256": (
                "2b11fe7f69864aeea1158342a9116cc5d17868d0afd10fa1b9ca89ed094da423"
            ),
            "derived_case_sha256": (
                "b33a134a368ee8e5829a956c35355370b2af66eb52bab5974ac83a965309e983"
            ),
            "regf1_source_sha256": (
                "b3346a41dc302dfba314ac61fabff5920828fce963823a4d6761045e0d22323f"
            ),
            "regf2_source_sha256": (
                "1109842ea912e27f8d750be525c26e4dfc41c40b3b6b692a333959aa8d635a53"
            ),
            "reference_abs_tolerance": 1.0e-12,
            "residual_abs_threshold": 1.0e-6,
            "tds_tf_seconds": 0.2,
            "tds_tolerance": 1.0e-4,
            "drift_abs_limit_system_pu": 2.0e-4,
            "electrical_limits": {
                "bus_v_min_pu": 0.9,
                "bus_v_max_pu": 1.1,
                "current_magnitude_max_pu": 10.0,
                "apparent_power_max_system_pu": 9.0,
                "virtual_frequency_min_pu": 0.95,
                "virtual_frequency_max_pu": 1.05,
            },
            "post_init_actions_authorized": False,
            "retry_authorized": False,
            "training_authorized": False,
            "trajectory_count": 1,
        }
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


def _finite(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _diagnostics_schema(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        diagnostics = record["initialization_diagnostics"]
        if diagnostics["captured"] is not True:
            return False
        equation_count = diagnostics["equation_count"]
        bad_indices = diagnostics["bad_combined_indices"]
        residual_count = diagnostics["residual_count"]
        residuals = diagnostics["residuals"]
        clamped = diagnostics["clamped_limits"]
        if (
            isinstance(equation_count, bool)
            or not isinstance(equation_count, int)
            or equation_count <= 0
            or not isinstance(bad_indices, Sequence)
            or isinstance(bad_indices, (str, bytes))
            or not isinstance(residual_count, int)
            or isinstance(residual_count, bool)
            or not isinstance(residuals, Sequence)
            or isinstance(residuals, (str, bytes))
            or not isinstance(clamped, Sequence)
            or isinstance(clamped, (str, bytes))
            or residual_count != len(residuals)
        ):
            return False
        normalized_indices = [int(value) for value in bad_indices]
        if (
            len(normalized_indices) != len(set(normalized_indices))
            or any(value < 0 or value >= equation_count for value in normalized_indices)
        ):
            return False

        threshold = float(spec["residual_abs_threshold"])
        row_indices: list[int] = []
        nonfinite_tokens = {"nan", "+nan", "-nan", "inf", "+inf", "-inf"}
        required_residual = {
            "combined_index",
            "name",
            "residual",
            "equation",
            "model",
            "idx",
        }
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
                if abs(float(residual)) < threshold:
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


def _source_schema(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        source = record["source"]
        return bool(
            source["andes_version"] == spec["andes_version"]
            and source["xlsx_json_static_equal"] is True
            and source["derived_case_deterministic"] is True
            and source["xlsx_case_sha256"] == spec["xlsx_case_sha256"]
            and source["json_case_sha256"] == spec["json_case_sha256"]
            and source["derived_case_sha256"] == spec["derived_case_sha256"]
            and source["regf1_source_sha256"] == spec["regf1_source_sha256"]
            and source["regf2_source_sha256"] == spec["regf2_source_sha256"]
        )
    except (KeyError, TypeError):
        return False


def _inventory_schema(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        inventory = record["inventory"]
        if inventory["network"] != spec["network_inventory"]:
            return False
        counts = inventory["forbidden_model_counts"]
        if (
            set(counts) != set(spec["forbidden_models"])
            or any(isinstance(counts[name], bool) or int(counts[name]) != 0 for name in counts)
            or inventory["forbidden_dae_names"] != []
        ):
            return False

        regf2 = inventory["regf2"]
        pll2 = inventory["pll2"]
        if (
            not isinstance(regf2, list)
            or not isinstance(pll2, list)
            or len(regf2) != 4
            or len(pll2) != 4
        ):
            return False
        normalized = [
            {"idx": str(row["idx"]), "bus": int(row["bus"]), "gen": int(row["gen"])}
            for row in regf2
        ]
        if normalized != spec["expected_mapping"]:
            return False
        if any(
            int(row["u"]) != 1
            or not _finite(row["Sn"])
            or float(row["Sn"]) != float(spec["device_rating_mva"])
            or row["input_parameter_card"] != spec["parameter_card"]
            or row["runtime_parameter_card"] != spec["runtime_parameter_card"]
            or not isinstance(row["pll"], str)
            or not row["pll"]
            for row in regf2
        ):
            return False

        pll_ids = [str(row["idx"]) for row in pll2]
        pll_buses = [int(row["bus"]) for row in pll2]
        if (
            len(set(pll_ids)) != 4
            or pll_buses != [1, 2, 3, 4]
            or any(int(row["u"]) != 1 for row in pll2)
            or [str(row["pll"]) for row in regf2] != pll_ids
        ):
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _references_schema(record: Mapping[str, Any], spec: Mapping[str, Any]) -> tuple[bool, bool]:
    try:
        references = record["references"]
        rows = references["rows"]
        tolerance = float(spec["reference_abs_tolerance"])
        if (
            references["phase"] != "post-pflow-pre-init-to-post-init"
            or references["checked"] is not True
            or not _finite(references["absolute_tolerance"])
            or float(references["absolute_tolerance"]) != tolerance
            or not isinstance(rows, list)
            or len(rows) != 4
            or [str(row["idx"]) for row in rows]
            != [row["idx"] for row in spec["expected_mapping"]]
        ):
            return False, False
        matches: list[bool] = []
        for row in rows:
            if not all(_finite(row[key]) for key in ("static_p", "static_q", "pref", "qref")):
                return False, False
            pref_match = math.isclose(
                float(row["pref"]), float(row["static_p"]), rel_tol=0.0, abs_tol=tolerance
            )
            qref_match = math.isclose(
                float(row["qref"]), float(row["static_q"]), rel_tol=0.0, abs_tol=tolerance
            )
            if row["pref_match"] is not pref_match or row["qref_match"] is not qref_match:
                return False, False
            matches.extend((pref_match, qref_match))
        return True, all(matches)
    except (KeyError, TypeError, ValueError):
        return False, False


def _empty_references(references: object, spec: Mapping[str, Any]) -> bool:
    return isinstance(references, Mapping) and references == {
        "phase": None,
        "checked": False,
        "absolute_tolerance": spec["reference_abs_tolerance"],
        "rows": [],
    }


def _empty_trace(trace: object) -> bool:
    return isinstance(trace, Mapping) and trace == {
        "checked": False,
        "times": [],
        "bus_v": [],
        "devices": {},
    }


def _trace_schema(
    record: Mapping[str, Any],
    spec: Mapping[str, Any],
    *,
    require_horizon: bool,
) -> bool:
    try:
        trace = record["trace"]
        times = trace["times"]
        bus_v = trace["bus_v"]
        devices = trace["devices"]
        if (
            trace["checked"] is not True
            or not isinstance(times, list)
            or len(times) < 2
            or not all(_finite(value) for value in times)
            or float(times[0]) != 0.0
            or any(float(right) <= float(left) for left, right in zip(times, times[1:]))
            or not isinstance(bus_v, list)
            or len(bus_v) != len(times)
        ):
            return False
        terminal = float(record["solver"]["terminal_time_seconds"])
        tolerance = max(1.0e-12, float(spec["tds_tolerance"]))
        if abs(float(times[-1]) - terminal) > tolerance:
            return False
        horizon = float(spec["tds_tf_seconds"])
        if require_horizon:
            if abs(float(times[-1]) - horizon) > tolerance:
                return False
        elif not 0.0 < float(times[-1]) < horizon - tolerance:
            return False
        expected_bus_keys = {str(bus) for bus in range(1, 11)}
        for sample in bus_v:
            if not isinstance(sample, Mapping) or set(sample) != expected_bus_keys:
                return False
            if not all(_finite(value) for value in sample.values()):
                return False

        expected_devices = {row["idx"] for row in spec["expected_mapping"]}
        if not isinstance(devices, Mapping) or set(devices) != expected_devices:
            return False
        for signals in devices.values():
            if not isinstance(signals, Mapping) or set(signals) != set(TRACE_SIGNALS):
                return False
            if any(
                not isinstance(values, list)
                or len(values) != len(times)
                or not all(_finite(value) for value in values)
                for values in signals.values()
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _solver_and_attempt_schema(record: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    try:
        solver = record["solver"]
        error = record["scientific_error"]
        if error not in SCIENTIFIC_ERRORS:
            return False
        if any(not isinstance(solver[key], bool) for key in (
            "setup_completed",
            "pflow_converged",
            "tds_initialized",
            "tds_test_ok",
            "tds_converged",
        )):
            return False
        if not _finite(solver["terminal_time_seconds"]) or not _finite(solver["tds_tolerance"]):
            return False
        if float(solver["tds_tolerance"]) != float(spec["tds_tolerance"]):
            return False
        attempted = record["trajectory_attempted"]
        executed = record["physical_trajectory_executed"]
        count = record["trajectory_count"]
        if (
            not isinstance(attempted, bool)
            or not isinstance(executed, bool)
            or isinstance(count, bool)
            or count not in (0, 1)
            or count != int(executed)
            or (executed and not attempted)
        ):
            return False

        if error is None:
            return bool(
                attempted
                and executed
                and all(solver[key] is True for key in (
                    "setup_completed",
                    "pflow_converged",
                    "tds_initialized",
                    "tds_test_ok",
                    "tds_converged",
                ))
                and _trace_schema(record, spec, require_horizon=True)
            )
        if error == "PFlow did not converge":
            return bool(
                solver["setup_completed"]
                and not solver["pflow_converged"]
                and not solver["tds_initialized"]
                and not solver["tds_test_ok"]
                and not solver["tds_converged"]
                and not attempted
                and not executed
                and count == 0
                and float(solver["terminal_time_seconds"]) == 0.0
                and _empty_trace(record["trace"])
            )
        if error == "TDS initialization failed":
            return bool(
                solver["setup_completed"]
                and solver["pflow_converged"]
                and not (
                    solver["tds_initialized"]
                    and solver["tds_test_ok"]
                )
                and not solver["tds_converged"]
                and not attempted
                and not executed
                and count == 0
                and float(solver["terminal_time_seconds"]) == 0.0
                and _empty_trace(record["trace"])
            )
        if error == "TDS did not reach horizon":
            common = bool(
                solver["setup_completed"]
                and solver["pflow_converged"]
                and solver["tds_initialized"]
                and solver["tds_test_ok"]
                and not solver["tds_converged"]
                and attempted
            )
            if not common:
                return False
            if executed:
                return bool(
                    count == 1
                    and _trace_schema(record, spec, require_horizon=False)
                )
            return bool(
                count == 0
                and float(solver["terminal_time_seconds"]) == 0.0
                and _empty_trace(record["trace"])
            )
        if error == "TDS did not converge":
            return bool(
                solver["setup_completed"]
                and solver["pflow_converged"]
                and solver["tds_initialized"]
                and solver["tds_test_ok"]
                and not solver["tds_converged"]
                and attempted
                and executed
                and count == 1
                and _trace_schema(record, spec, require_horizon=True)
            )
        return False
    except (KeyError, TypeError, ValueError):
        return False


def _finite_guard_schema(record: Mapping[str, Any]) -> bool:
    try:
        guard = record["finite_guard"]
        return guard["checked"] is True and all(
            isinstance(guard[key], bool)
            for key in ("dae_finite", "regf2_finite")
        )
    except (KeyError, TypeError):
        return False


def _record_integrity(record: Mapping[str, Any], spec: Mapping[str, Any]) -> tuple[bool, bool]:
    try:
        if record["scientific_error"] == "PFlow did not converge":
            references_schema = _empty_references(record["references"], spec)
            references_pass = False
        else:
            references_schema, references_pass = _references_schema(record, spec)
        if (
            record["schema_version"] != 1
            or record["round"] != "R389"
            or record["question"] != "Q-0107"
            or record["contract_sha256"] != _payload_sha256(spec)
            or record["formal_input_complete"] is not True
            or record["execution_error"] is not None
            or record["training_executed"] is not False
            or record["post_init_action_executed"] is not False
            or not _source_schema(record, spec)
            or not _inventory_schema(record, spec)
            or not references_schema
            or not _diagnostics_schema(record, spec)
            or not _solver_and_attempt_schema(record, spec)
            or not _finite_guard_schema(record)
        ):
            return False, False
        return True, references_pass
    except (KeyError, TypeError, ValueError):
        return False, False


def _trace_checks(record: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, bool]:
    error = record["scientific_error"]
    if error is not None:
        return {
            "native_solver": False,
            "finite_values": False,
            "electrical_guards": False,
            "zero_input_drift": False,
        }
    trace = record["trace"]
    limits = spec["electrical_limits"]
    bus_values = [float(value) for sample in trace["bus_v"] for value in sample.values()]
    device_samples = trace["devices"].values()
    electrical = all(
        float(limits["bus_v_min_pu"]) <= value <= float(limits["bus_v_max_pu"])
        for value in bus_values
    )
    for signals in device_samples:
        for pe, qe, i_d, i_q, frequency in zip(
            signals["Pe"],
            signals["Qe"],
            signals["Id"],
            signals["Iq"],
            signals["virtual_frequency"],
            strict=True,
        ):
            electrical = electrical and bool(
                math.hypot(float(i_d), float(i_q))
                <= float(limits["current_magnitude_max_pu"])
                and math.hypot(float(pe), float(qe))
                <= float(limits["apparent_power_max_system_pu"])
                and float(limits["virtual_frequency_min_pu"])
                <= float(frequency)
                <= float(limits["virtual_frequency_max_pu"])
            )
    drift_limit = float(spec["drift_abs_limit_system_pu"])
    drift_values = [
        max(abs(float(value) - float(values[0])) for value in values)
        for signals in trace["devices"].values()
        for name, values in signals.items()
        if name in {"Pe", "Qe"}
    ]
    for bus in range(1, 11):
        values = [float(sample[str(bus)]) for sample in trace["bus_v"]]
        drift_values.append(max(abs(value - values[0]) for value in values))
    finite_guard = record["finite_guard"]
    solver = record["solver"]
    return {
        "native_solver": bool(
            solver["tds_converged"]
            and abs(float(solver["terminal_time_seconds"]) - float(spec["tds_tf_seconds"]))
            <= max(1.0e-12, float(spec["tds_tolerance"]))
        ),
        "finite_values": bool(
            finite_guard["checked"]
            and finite_guard["dae_finite"]
            and finite_guard["regf2_finite"]
        ),
        "electrical_guards": electrical,
        "zero_input_drift": all(value <= drift_limit for value in drift_values),
    }


def _analysis(classification: str, checks: Mapping[str, bool]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": "R389",
        "question": "Q-0107",
        "classification": classification,
        "checks": dict(checks),
        "claim_scope": "stock four-REGF2 object, initialization, and zero-input short-trajectory validity only",
        "next_gate": (
            "regf2_dynamic_signal_authority"
            if classification == "REGF2-OBJECT-INIT-PASS"
            else None
        ),
        "post_init_actions_authorized": False,
        "retry_authorized": False,
        "training_authorized": False,
    }


def classify_regf2_object_init_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the fail-closed R389 classification for one immutable record."""

    expected = build_regf2_object_init_contract()
    if contract is not None and contract != expected:
        return _analysis("ANALYSIS-INVALID", {"canonical_contract": False})
    spec = expected
    integrity, references_pass = _record_integrity(record, spec)
    if not integrity:
        return _analysis("ANALYSIS-INVALID", {"record_integrity": False})

    checks = {
        "record_integrity": True,
        "source_integrity": True,
        "structural_absence": True,
        "object_mapping_and_card": True,
        "pll_inventory": True,
        "post_init_references": references_pass,
        "initialization_residuals_zero": record["initialization_diagnostics"]["residual_count"] == 0,
        "initialization_limits_unclamped": len(record["initialization_diagnostics"]["clamped_limits"]) == 0,
        **_trace_checks(record, spec),
    }
    classification = (
        "REGF2-OBJECT-INIT-PASS"
        if all(checks.values())
        else "STOP-REGF2-OBJECT-INITIALIZATION"
    )
    return _analysis(classification, checks)


__all__ = [
    "EXPECTED_MAPPING",
    "FORBIDDEN_MODELS",
    "NETWORK_INVENTORY",
    "REGF2_PARAMETER_CARD",
    "REGF2_RUNTIME_PARAMETER_CARD",
    "STATIC_MODELS",
    "build_regf2_object_init_contract",
    "classify_regf2_object_init_record",
]
