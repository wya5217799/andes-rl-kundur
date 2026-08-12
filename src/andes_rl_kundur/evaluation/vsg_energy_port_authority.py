"""Prospective bounded-authority classifier for the four VSG energy ports.

The gate uses duplicated zero arms and paired signed interventions in a fixed
common/differential basis.  It asks whether the already object-gated ports have
bounded, energy-consistent authority on the corresponding physical modes.  It
does not score a controller, choose an action from outcomes, or authorize
learning.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract

MODE_VECTORS: dict[str, tuple[float, float, float, float]] = {
    "common": (1.0, 1.0, 1.0, 1.0),
    "inter_area": (1.0, 1.0, -1.0, -1.0),
    "local_area_1": (1.0, -1.0, 0.0, 0.0),
    "local_area_2": (0.0, 0.0, 1.0, -1.0),
}


def build_contract() -> dict[str, Any]:
    """Return the complete outcome-blind R373 scientific contract."""

    energy = r272_frozen_bess_contract()
    modes = {name: list(vector) for name, vector in MODE_VECTORS.items()}
    arm_ids = ["zero_a", "zero_b"]
    for mode in modes:
        arm_ids.extend((f"{mode}_positive", f"{mode}_negative"))
    conditions = [
        {"condition_id": "nominal", "delta_u": {}},
        {
            "condition_id": "load_bus14_plus_0p5",
            "delta_u": {"PQ_Bus14": 0.5},
        },
        {
            "condition_id": "load_bus15_plus_0p5",
            "delta_u": {"PQ_Bus15": 0.5},
        },
    ]
    return {
        "schema_version": 1,
        "round": "R373",
        "seed": 42,
        "steps": 40,
        "dt_seconds": 0.2,
        "conditions": conditions,
        "condition_ids": [item["condition_id"] for item in conditions],
        "modes": modes,
        "mode_ids": list(modes),
        "arm_ids": arm_ids,
        "record_count": len(conditions) * len(arm_ids),
        "request_component_magnitude_system_pu": 0.04,
        "minimum_projected_achieved_power_system_pu": 0.035,
        "minimum_frequency_response_rms_hz": 1.0e-6,
        "minimum_electrical_response_rms_system_pu": 1.0e-6,
        "initial_direction_window_steps": 5,
        "noise_multiplier": 10.0,
        "numeric_atol": 1.0e-9,
        "timing_atol_seconds": 1.0e-6,
        "expected_vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
        "expected_vsg_buses": [12, 16, 14, 15],
        "system_mva": energy.system_mva,
        "device_energy_mwh": energy.device_energy_mwh,
        "device_power_limit_system_pu": energy.device_power_limit_system_pu,
        "device_ramp_limit_system_pu_per_s": (
            energy.device_ramp_limit_system_pu_per_s
        ),
        "soc_initial": energy.soc_initial,
        "soc_min": energy.soc_min,
        "soc_max": energy.soc_max,
        "charge_efficiency": energy.charge_efficiency,
        "discharge_efficiency": energy.discharge_efficiency,
        "reward_used_for_gate": False,
        "retry_authorized": False,
        "training_authorized": False,
    }


def action_request(
    arm_id: str,
    *,
    contract: Mapping[str, Any] | None = None,
) -> np.ndarray:
    """Return one frozen four-device request for an R373 arm."""

    frozen = dict(contract or build_contract())
    if arm_id in {"zero_a", "zero_b"}:
        return np.zeros(4, dtype=float)
    for suffix, sign in (("_positive", 1.0), ("_negative", -1.0)):
        if arm_id.endswith(suffix):
            mode_id = arm_id[: -len(suffix)]
            if mode_id not in frozen["modes"]:
                break
            basis = np.asarray(frozen["modes"][mode_id], dtype=float)
            magnitude = float(
                frozen["request_component_magnitude_system_pu"]
            )
            return sign * magnitude * basis
    raise ValueError(f"unknown R373 arm: {arm_id}")


def _array(value: object, *, shape: tuple[int, ...]) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"expected finite array with shape {shape}")
    return array


def _project(values: np.ndarray, basis: np.ndarray) -> np.ndarray:
    denominator = float(np.dot(basis, basis))
    if denominator <= 0.0:
        raise ValueError("mode basis must be nonzero")
    return np.asarray(values @ basis / denominator, dtype=float)


def _execution_is_valid(
    records: list[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected_keys = {
        (str(condition["condition_id"]), str(arm_id))
        for condition in contract["conditions"]
        for arm_id in contract["arm_ids"]
    }
    actual_keys = [
        (str(record.get("condition_id")), str(record.get("arm_id")))
        for record in records
    ]
    if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != expected_keys:
        errors.append("condition/arm records do not match the frozen bank")
        return False, errors

    condition_payloads = {
        str(item["condition_id"]): dict(item["delta_u"])
        for item in contract["conditions"]
    }
    expected_identity = {
        "n_agents": 4,
        "vsg_idx": list(contract["expected_vsg_idx"]),
        "vsg_buses": list(contract["expected_vsg_buses"]),
    }
    steps_expected = int(contract["steps"])
    dt = float(contract["dt_seconds"])
    timing_atol = float(contract["timing_atol_seconds"])
    numeric_atol = float(contract["numeric_atol"])

    for record in records:
        condition_id = str(record["condition_id"])
        arm_id = str(record["arm_id"])
        if dict(record.get("delta_u", {})) != condition_payloads[condition_id]:
            errors.append(f"{condition_id}/{arm_id}: disturbance drift")
        if dict(record.get("identity", {})) != expected_identity:
            errors.append(f"{condition_id}/{arm_id}: identity drift")
        rows = list(record.get("steps", []))
        if (
            bool(record.get("tds_failed"))
            or record.get("failure") is not None
            or int(record.get("completed_steps", -1)) != steps_expected
            or len(rows) != steps_expected
        ):
            errors.append(f"{condition_id}/{arm_id}: incomplete execution")
            continue
        expected_request = action_request(arm_id, contract=contract)
        times: list[float] = []
        for step_index, row in enumerate(rows):
            try:
                if int(row["step_index"]) != step_index or bool(
                    row.get("tds_failed")
                ):
                    raise ValueError("step index or TDS status drift")
                times.append(float(row["time"]))
                request = _array(
                    row["requested_power_system_pu"], shape=(4,)
                )
                if not np.allclose(
                    request, expected_request, atol=numeric_atol, rtol=0.0
                ):
                    raise ValueError("request schedule drift")
                for key in (
                    "commanded_power_system_pu",
                    "achieved_power_system_pu",
                    "soc",
                    "charged_energy_mwh",
                    "discharged_energy_mwh",
                    "total_charged_energy_mwh",
                    "total_discharged_energy_mwh",
                    "freq_hz_physical",
                    "P_es",
                    "M_es",
                    "D_es",
                    "delta_M",
                    "delta_D",
                ):
                    _array(row[key], shape=(4,))
                md = _array(row["md_action_norm"], shape=(4, 2))
                if not np.allclose(md, 0.0, atol=numeric_atol, rtol=0.0):
                    raise ValueError("legacy M/D action is nonzero")
                if not np.allclose(
                    _array(row["delta_M"], shape=(4,)),
                    0.0,
                    atol=numeric_atol,
                    rtol=0.0,
                ) or not np.allclose(
                    _array(row["delta_D"], shape=(4,)),
                    0.0,
                    atol=numeric_atol,
                    rtol=0.0,
                ):
                    raise ValueError("legacy M/D state changed")
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"{condition_id}/{arm_id}/{step_index}: {exc}")
                break
        if len(times) == steps_expected:
            intervals = np.diff(np.asarray(times, dtype=float))
            if not np.allclose(intervals, dt, atol=timing_atol, rtol=0.0):
                errors.append(f"{condition_id}/{arm_id}: timing drift")
    return not errors, errors


def _by_key(
    records: list[Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(record["condition_id"]), str(record["arm_id"])): record
        for record in records
    }


def _trajectory(record: Mapping[str, Any], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in record["steps"]], dtype=float)


def _zero_repeatability(
    by_key: Mapping[tuple[str, str], Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    maxima = {
        "time_s": 0.0,
        "frequency_hz": 0.0,
        "electrical_power_system_pu": 0.0,
        "command_system_pu": 0.0,
        "achieved_power_system_pu": 0.0,
        "soc": 0.0,
    }
    fields = {
        "frequency_hz": "freq_hz_physical",
        "electrical_power_system_pu": "P_es",
        "command_system_pu": "commanded_power_system_pu",
        "achieved_power_system_pu": "achieved_power_system_pu",
        "soc": "soc",
    }
    for condition_id in contract["condition_ids"]:
        first = by_key[(str(condition_id), "zero_a")]
        second = by_key[(str(condition_id), "zero_b")]
        condition = {
            "time_s": float(
                np.max(
                    np.abs(
                        _trajectory(first, "time")
                        - _trajectory(second, "time")
                    )
                )
            )
        }
        for output_name, field in fields.items():
            condition[output_name] = float(
                np.max(
                    np.abs(
                        _trajectory(first, field) - _trajectory(second, field)
                    )
                )
            )
        rows[str(condition_id)] = condition
        for name, value in condition.items():
            maxima[name] = max(maxima[name], float(value))
    tolerance = float(contract["numeric_atol"])
    return {
        "pass": all(value <= tolerance for value in maxima.values()),
        "tolerance": tolerance,
        "maxima": maxima,
        "conditions": rows,
    }


def _bounded_energy_audit(
    records: list[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    atol = float(contract["numeric_atol"])
    dt = float(contract["dt_seconds"])
    system_mva = float(contract["system_mva"])
    energy_mwh = float(contract["device_energy_mwh"])
    eta_c = float(contract["charge_efficiency"])
    eta_d = float(contract["discharge_efficiency"])
    power_limit = float(contract["device_power_limit_system_pu"])
    ramp_limit = float(contract["device_ramp_limit_system_pu_per_s"])
    soc_min = float(contract["soc_min"])
    soc_max = float(contract["soc_max"])

    max_abs_command = 0.0
    max_abs_slew = 0.0
    max_energy_error = 0.0
    max_soc_error = 0.0
    min_soc = float("inf")
    max_soc = float("-inf")
    saturation_count = 0
    command_l1_device_s = 0.0
    command_total_variation = 0.0
    total_charged_mwh = 0.0
    total_discharged_mwh = 0.0

    for record in records:
        previous_command = np.zeros(4, dtype=float)
        expected_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
        expected_charged_total = np.zeros(4, dtype=float)
        expected_discharged_total = np.zeros(4, dtype=float)
        for row in record["steps"]:
            command = _array(row["commanded_power_system_pu"], shape=(4,))
            achieved = _array(row["achieved_power_system_pu"], shape=(4,))
            observed_soc = _array(row["soc"], shape=(4,))
            observed_charged = _array(row["charged_energy_mwh"], shape=(4,))
            observed_discharged = _array(
                row["discharged_energy_mwh"], shape=(4,)
            )
            observed_charged_total = _array(
                row["total_charged_energy_mwh"], shape=(4,)
            )
            observed_discharged_total = _array(
                row["total_discharged_energy_mwh"], shape=(4,)
            )
            grid_energy = np.abs(achieved) * system_mva * dt / 3600.0
            charged = np.where(achieved < 0.0, grid_energy * eta_c, 0.0)
            discharged = np.where(achieved > 0.0, grid_energy / eta_d, 0.0)
            expected_soc = expected_soc + (charged - discharged) / energy_mwh
            expected_charged_total += charged
            expected_discharged_total += discharged
            max_energy_error = max(
                max_energy_error,
                float(np.max(np.abs(observed_charged - charged))),
                float(np.max(np.abs(observed_discharged - discharged))),
                float(
                    np.max(
                        np.abs(observed_charged_total - expected_charged_total)
                    )
                ),
                float(
                    np.max(
                        np.abs(
                            observed_discharged_total
                            - expected_discharged_total
                        )
                    )
                ),
            )
            max_soc_error = max(
                max_soc_error,
                float(np.max(np.abs(observed_soc - expected_soc))),
            )
            slew = np.abs(command - previous_command) / dt
            max_abs_slew = max(max_abs_slew, float(np.max(slew)))
            command_total_variation += float(np.sum(np.abs(command - previous_command)))
            command_l1_device_s += float(np.sum(np.abs(command)) * dt)
            max_abs_command = max(max_abs_command, float(np.max(np.abs(command))))
            min_soc = min(min_soc, float(np.min(observed_soc)))
            max_soc = max(max_soc, float(np.max(observed_soc)))
            saturation_count += sum(bool(reasons) for reasons in row["saturation_reasons"])
            previous_command = command
        total_charged_mwh += float(np.sum(expected_charged_total))
        total_discharged_mwh += float(np.sum(expected_discharged_total))

    guards = {
        "command_within_power_limit": max_abs_command <= power_limit + atol,
        "slew_within_ramp_limit": max_abs_slew <= ramp_limit + atol,
        "zero_saturation": saturation_count == 0,
        "soc_within_bounds": min_soc >= soc_min - atol and max_soc <= soc_max + atol,
        "energy_ledger_matches": max_energy_error <= atol,
        "soc_ledger_matches": max_soc_error <= atol,
    }
    return {
        "pass": all(guards.values()),
        "guards": guards,
        "max_abs_command_system_pu": max_abs_command,
        "max_abs_slew_system_pu_per_s": max_abs_slew,
        "max_energy_ledger_error_mwh": max_energy_error,
        "max_soc_ledger_error": max_soc_error,
        "min_soc": min_soc,
        "max_soc": max_soc,
        "saturation_count": saturation_count,
        "command_l1_device_s": command_l1_device_s,
        "command_total_variation_system_pu": command_total_variation,
        "total_charged_energy_mwh": total_charged_mwh,
        "total_discharged_energy_mwh": total_discharged_mwh,
    }


def _mode_authority(
    by_key: Mapping[tuple[str, str], Mapping[str, Any]],
    contract: Mapping[str, Any],
    zero: Mapping[str, Any],
) -> dict[str, Any]:
    modes = {
        str(name): np.asarray(vector, dtype=float)
        for name, vector in contract["modes"].items()
    }
    frequency_floor = max(
        float(contract["minimum_frequency_response_rms_hz"]),
        float(contract["noise_multiplier"])
        * float(zero["maxima"]["frequency_hz"]),
    )
    electrical_floor = max(
        float(contract["minimum_electrical_response_rms_system_pu"]),
        float(contract["noise_multiplier"])
        * float(zero["maxima"]["electrical_power_system_pu"]),
    )
    achieved_floor = float(
        contract["minimum_projected_achieved_power_system_pu"]
    )
    initial_steps = int(contract["initial_direction_window_steps"])
    rows: dict[str, Any] = {}
    achieved_pass = True
    electrical_pass = True
    frequency_pass = True

    for condition_id in contract["condition_ids"]:
        condition_rows: dict[str, Any] = {}
        for input_mode, input_basis in modes.items():
            positive = by_key[(str(condition_id), f"{input_mode}_positive")]
            negative = by_key[(str(condition_id), f"{input_mode}_negative")]
            achieved_positive = _project(
                _trajectory(positive, "achieved_power_system_pu"),
                input_basis,
            )
            achieved_negative = _project(
                _trajectory(negative, "achieved_power_system_pu"),
                input_basis,
            )
            minimum_signed_achieved = min(
                float(np.min(achieved_positive)),
                float(np.min(-achieved_negative)),
            )
            achieved_ok = minimum_signed_achieved >= achieved_floor
            achieved_pass = achieved_pass and achieved_ok

            frequency_matrix: dict[str, float] = {}
            electrical_matrix: dict[str, float] = {}
            diagonal_frequency: np.ndarray | None = None
            diagonal_electrical: np.ndarray | None = None
            for output_mode, output_basis in modes.items():
                frequency_response = 0.5 * (
                    _project(
                        _trajectory(positive, "freq_hz_physical"), output_basis
                    )
                    - _project(
                        _trajectory(negative, "freq_hz_physical"), output_basis
                    )
                )
                electrical_response = 0.5 * (
                    _project(_trajectory(positive, "P_es"), output_basis)
                    - _project(_trajectory(negative, "P_es"), output_basis)
                )
                frequency_matrix[output_mode] = float(
                    np.sqrt(np.mean(np.square(frequency_response)))
                )
                electrical_matrix[output_mode] = float(
                    np.sqrt(np.mean(np.square(electrical_response)))
                )
                if output_mode == input_mode:
                    diagonal_frequency = frequency_response
                    diagonal_electrical = electrical_response
            assert diagonal_frequency is not None and diagonal_electrical is not None
            frequency_rms = frequency_matrix[input_mode]
            electrical_rms = electrical_matrix[input_mode]
            initial_signed_mean = float(np.mean(diagonal_frequency[:initial_steps]))
            frequency_ok = (
                frequency_rms > frequency_floor
                and initial_signed_mean > frequency_floor
            )
            electrical_ok = electrical_rms > electrical_floor
            frequency_pass = frequency_pass and frequency_ok
            electrical_pass = electrical_pass and electrical_ok
            condition_rows[input_mode] = {
                "minimum_signed_projected_achieved_power_system_pu": (
                    minimum_signed_achieved
                ),
                "achieved_power_pass": achieved_ok,
                "frequency_response_rms_hz": frequency_rms,
                "frequency_initial_signed_mean_hz": initial_signed_mean,
                "frequency_pass": frequency_ok,
                "electrical_response_rms_system_pu": electrical_rms,
                "electrical_pass": electrical_ok,
                "frequency_rms_matrix_row_hz": frequency_matrix,
                "electrical_rms_matrix_row_system_pu": electrical_matrix,
            }
        rows[str(condition_id)] = condition_rows
    return {
        "achieved_power_pass": achieved_pass,
        "electrical_mode_pass": electrical_pass,
        "frequency_mode_pass": frequency_pass,
        "frequency_floor_hz": frequency_floor,
        "electrical_floor_system_pu": electrical_floor,
        "achieved_power_floor_system_pu": achieved_floor,
        "conditions": rows,
    }


def classify_records(
    records: list[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one complete R373 bank with typed, prospective stop reasons."""

    frozen = dict(contract or build_contract())
    valid, errors = _execution_is_valid(records, frozen)
    if not valid:
        return {
            "schema_version": 1,
            "round": "R373",
            "classification": "ANALYSIS-INVALID",
            "checks": {
                "execution_validity": False,
                "zero_repeatability": False,
                "bounded_energy_safe": False,
                "achieved_power_authority": False,
                "electrical_mode_authority": False,
                "frequency_mode_authority": False,
            },
            "execution_errors": errors,
            "record_count": len(records),
            "training_authorized": False,
            "next_gate": None,
        }

    by_key = _by_key(records)
    zero = _zero_repeatability(by_key, frozen)
    energy = _bounded_energy_audit(records, frozen)
    authority = _mode_authority(by_key, frozen, zero)
    checks = {
        "execution_validity": True,
        "zero_repeatability": bool(zero["pass"]),
        "bounded_energy_safe": bool(energy["pass"]),
        "achieved_power_authority": bool(authority["achieved_power_pass"]),
        "electrical_mode_authority": bool(authority["electrical_mode_pass"]),
        "frequency_mode_authority": bool(authority["frequency_mode_pass"]),
    }
    if not checks["zero_repeatability"]:
        classification = "STOP-AUTHORITY-NOISE"
    elif not checks["bounded_energy_safe"]:
        classification = "STOP-UNSAFE-ACTUATION"
    elif not checks["achieved_power_authority"]:
        classification = "STOP-NO-ACHIEVED-POWER-AUTHORITY"
    elif not checks["electrical_mode_authority"]:
        classification = "STOP-NO-ELECTRICAL-AUTHORITY"
    elif not checks["frequency_mode_authority"]:
        classification = "STOP-NO-RELEVANT-DYNAMIC-AUTHORITY"
    else:
        classification = "BOUNDED-ENERGY-PORT-AUTHORITY-PASS"
    return {
        "schema_version": 1,
        "round": "R373",
        "classification": classification,
        "checks": checks,
        "execution_errors": [],
        "record_count": len(records),
        "zero_repeatability": zero,
        "bounded_energy_audit": energy,
        "mode_authority": authority,
        "reward_used_for_gate": False,
        "training_authorized": False,
        "next_gate": (
            "permission_matched_deterministic_coordinator_design"
            if classification == "BOUNDED-ENERGY-PORT-AUTHORITY-PASS"
            else None
        ),
    }
