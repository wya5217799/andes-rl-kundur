"""Classify the prospective PPVSM1 two-unit object/init/spectrum gate.

The module owns the immutable R393 contract and a fail-closed pure
classifier. It imports no ANDES runtime code so records replay on Windows.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

ROUND_ID = "R393"
QUESTION_ID = "Q-0110"

STATIC_MODELS = ("Bus", "PQ", "PV", "Slack", "Line", "Area")
FORBIDDEN_MODELS = (
    "REGCV1",
    "REGCV2",
    "REGF1",
    "REGF2",
    "REGF3",
    "GENROU",
    "TGOV1",
    "EXDC2",
    "Toggler",
    "Toggle",
    "PLL1",
    "PLL2",
)
EXPECTED_MAPPING = (
    {"idx": "PPVSM1_1", "bus": 1, "gen": 1},
    {"idx": "PPVSM1_2", "bus": 2, "gen": 2},
)
NETWORK_INVENTORY = {
    "bus_count": 10,
    "line_count": 15,
    "pq_count": 2,
    "static_gen_count": 4,
    "static_generator_buses": [1, 2, 3, 4],
    "ppvsm1_buses": [1, 2],
    "static_anchor_buses": [3, 4],
}
PPVSM1_PARAMETER_CARD = {
    "Sn": 900.0,
    "fn": 60.0,
    "mf": 0.15,
    "wdrp": 0.033,
    "Qdrp": 0.045,
    "krho": 20.0,
    "rho_rate_max": 10.0,
    "rho_rate_min": -10.0,
    "rf": 0.0,
    "xf": 0.2,
    "Rv": 0.05,
    "KPv": 3.0,
    "KIv": 10.0,
    "KPi": 0.5,
    "KIi": 20.0,
    "Te": 0.005,
    "Pmax": 1.0,
    "Pmin": -1.0,
    "Qmax": 1.0,
    "Qmin": -1.0,
    "dwmax": 75.0,
    "dwmin": -75.0,
}
PPVSM1_RUNTIME_PARAMETER_CARD = {
    **PPVSM1_PARAMETER_CARD,
    "xf": 0.2 * 100.0 / 900.0,
    "Pmax": 1.0 * 900.0 / 100.0,
    "Pmin": -1.0 * 900.0 / 100.0,
    "Qmax": 1.0 * 900.0 / 100.0,
    "Qmin": -1.0 * 900.0 / 100.0,
}
TRACE_SIGNALS = ("Pe", "Qe", "Id", "Iq", "virtual_frequency")
SCIENTIFIC_ERRORS = {
    None,
    "PFlow did not converge",
    "TDS initialization failed",
    "TDS did not converge",
    "TDS did not reach horizon",
    "EIG calculation failed",
}


def payload_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_ppvsm1_object_contract() -> dict[str, Any]:
    """Return a detached canonical R393 contract."""

    return deepcopy(
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "andes_version": "2.0.0",
            "static_models": list(STATIC_MODELS),
            "forbidden_models": list(FORBIDDEN_MODELS),
            "expected_mapping": list(EXPECTED_MAPPING),
            "network_inventory": NETWORK_INVENTORY,
            "parameter_card": PPVSM1_PARAMETER_CARD,
            "runtime_parameter_card": PPVSM1_RUNTIME_PARAMETER_CARD,
            "device_rating_mva": 900.0,
            "system_mva_base": 100.0,
            "xlsx_case_sha256": (
                "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8"
            ),
            "json_case_sha256": (
                "2b11fe7f69864aeea1158342a9116cc5d17868d0afd10fa1b9ca89ed094da423"
            ),
            "reference_abs_tolerance": 1.0e-12,
            "residual_abs_threshold": 1.0e-6,
            "tds_tf_seconds": 0.2,
            "tds_tolerance": 1.0e-4,
            "drift_abs_limit_system_pu": 2.0e-4,
            "positive_real_threshold": 1.0e-7,
            "neutral_abs_tolerance": 1.0e-6,
            "allowed_zero_modes": 1,
            "electrical_limits": {
                "bus_v_min": 0.8,
                "bus_v_max": 1.2,
                "device_current_max_pu": 2.0,
                "device_power_max_pu": 9.0,
                "dw_max": 75.0,
            },
        }
    )


def _finite_number(value: object) -> bool:
    return bool(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _trace_schema(record: Mapping[str, Any]) -> bool:
    try:
        trace = record["trace"]
        devices = trace["devices"]
        return bool(
            trace["checked"] is True
            and isinstance(trace["times"], list)
            and len(trace["times"]) >= 2
            and isinstance(devices, dict)
            and len(devices) == 2
            and all(
                isinstance(device_id, str) and device_id in ("PPVSM1_1", "PPVSM1_2")
                for device_id in devices
            )
            and all(
                all(
                    isinstance(values, list)
                    and len(values) == len(trace["times"])
                    and all(_finite_number(v) for v in values)
                    for values in signals.values()
                )
                for signals in devices.values()
            )
        )
    except (KeyError, TypeError):
        return False


def _spectrum_schema(record: Mapping[str, Any]) -> bool:
    try:
        spectrum = record["spectrum"]
        values = spectrum["eigenvalues"]
        return bool(
            spectrum["captured"] is True
            and _finite_number(spectrum.get("state_count"))
            and isinstance(values, list)
            and len(values) == int(spectrum["state_count"])
            and all(
                isinstance(row, Mapping)
                and _finite_number(row.get("real"))
                and _finite_number(row.get("imag"))
                for row in values
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def classify_ppvsm1_object_record(
    record: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the single-arm record and emit the frozen F0 verdict."""

    checks = {
        "schema": False,
        "inventory": False,
        "references": False,
        "diagnostics": False,
        "solver": False,
        "finite": False,
        "trace": False,
        "drift": False,
        "spectrum": False,
        "positive_real": False,
        "neutral": False,
    }
    invalid = lambda: {  # noqa: E731
        "classification": "ANALYSIS-INVALID",
        "checks": checks,
        "spectrum_summary": {},
    }
    try:
        checks["schema"] = bool(
            record["schema_version"] == 1
            and record["round"] == contract["round"]
            and record["question"] == QUESTION_ID
            and record["contract_sha256"] == payload_sha256(contract)
            and record.get("formal_input_complete") is True
            and record.get("execution_error") is None
            and record.get("training_executed") is False
            and record.get("post_init_action_executed") is False
            and record.get("trajectory_count") == 1
        )
        if not checks["schema"]:
            return invalid()
        inventory = record["inventory"]
        checks["inventory"] = bool(
            inventory["network"] == contract["network_inventory"]
            and inventory["ppvsm1_count"] == 2
            and inventory["ppvsm1_buses"] == [1, 2]
            and inventory["ppvsm1_mapping_ok"] is True
            and inventory["input_parameter_cards_match"] is True
            and inventory["runtime_parameter_cards_match"] is True
            and all(
                value == 0
                for value in inventory["forbidden_model_counts"].values()
            )
            and inventory["forbidden_dae_names"] == []
        )
        if not checks["inventory"]:
            return invalid()
        references = record["references"]
        checks["references"] = bool(
            references["checked"] is True
            and references["phase"] == "post_init"
            and all(row["abs_deviation"] <= contract["reference_abs_tolerance"]
                    for row in references["rows"])
        )
        if not checks["references"]:
            return invalid()
        diagnostics = record["initialization_diagnostics"]
        checks["diagnostics"] = bool(
            diagnostics["captured"] is True
            and diagnostics["residual_count"] == 0
            and diagnostics["clamped_limits"] == []
        )
        solver = record["solver"]
        finite = record["finite_guard"]
        checks["finite"] = bool(
            finite["checked"] is True
            and finite["dae_finite"] is True
            and finite["jacobian_finite"] is True
            and finite["state_matrix_finite"] is True
        )
        checks["solver"] = bool(
            solver["setup_completed"] is True
            and solver["pflow_converged"] is True
            and solver["tds_initialized"] is True
            and solver["tds_test_ok"] is True
            and solver["tds_converged"] is True
            and solver["terminal_time_seconds"] >= contract["tds_tf_seconds"]
            and checks["diagnostics"]
            and checks["finite"]
        )
        if not checks["solver"]:
            return {
                "classification": "STOP-PPVSM1-OBJECT-INIT",
                "checks": checks,
                "spectrum_summary": {},
            }
        if not (
            solver["eig_return"] is True
            and solver["time_before_eig"] == 0.0
            and solver["time_after_eig"] == 0.0
            and solver["state_max_abs_delta"] == 0.0
        ):
            return invalid()
        checks["trace"] = _trace_schema(record)
        if not checks["trace"]:
            return invalid()
        # zero-input drift: every sampled deviation from init within ceiling
        ceiling = contract["drift_abs_limit_system_pu"]
        try:
            devices = record["trace"]["devices"]
            bus_samples = record["trace"]["bus_v"]
            initial_bus = bus_samples[0]
            drift_ok = True
            for signals in devices.values():
                for values in signals.values():
                    if any(
                        abs(float(v) - float(values[0])) > ceiling
                        for v in values[1:]
                    ):
                        drift_ok = False
            for sample in bus_samples[1:]:
                for bus, value in sample.items():
                    if abs(float(value) - float(initial_bus[bus])) > ceiling:
                        drift_ok = False
            checks["drift"] = drift_ok
        except (KeyError, TypeError, ValueError):
            checks["drift"] = False
        if not checks["drift"]:
            return {
                "classification": "STOP-PPVSM1-OBJECT-INIT",
                "checks": checks,
                "spectrum_summary": {},
            }
        checks["spectrum"] = _spectrum_schema(record)
        if not checks["spectrum"]:
            return invalid()
        spectrum = record["spectrum"]
        threshold = contract["positive_real_threshold"]
        neutral = contract["neutral_abs_tolerance"]
        positive = [
            complex(float(row["real"]), float(row["imag"]))
            for row in spectrum["eigenvalues"]
            if float(row["real"]) > threshold
        ]
        near_zero = [
            complex(float(row["real"]), float(row["imag"]))
            for row in spectrum["eigenvalues"]
            if abs(complex(float(row["real"]), float(row["imag"]))) < neutral
        ]
        leading = max(
            (float(row["real"]) for row in spectrum["eigenvalues"]),
            default=0.0,
        )
        checks["positive_real"] = len(positive) == 0
        checks["neutral"] = len(near_zero) <= contract["allowed_zero_modes"]
        summary = {
            "leading_real": leading,
            "positive_real_count": len(positive),
            "near_zero_count": len(near_zero),
            "state_count": spectrum["state_count"],
        }
        if not checks["positive_real"]:
            return {
                "classification": "STOP-PPVSM1-POSITIVE-REAL",
                "checks": checks,
                "spectrum_summary": summary,
            }
        if not checks["neutral"]:
            return {
                "classification": "STOP-PPVSM1-NEUTRAL-DEGENERACY",
                "checks": checks,
                "spectrum_summary": summary,
            }
        return {
            "classification": "PPVSM1-OBJECT-PASS",
            "checks": checks,
            "spectrum_summary": summary,
        }
    except (KeyError, TypeError, ValueError):
        return invalid()


__all__ = [
    "build_ppvsm1_object_contract",
    "classify_ppvsm1_object_record",
    "payload_sha256",
]
