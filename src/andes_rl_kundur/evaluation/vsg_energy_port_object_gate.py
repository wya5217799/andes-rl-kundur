"""Pure contract and classifier for the R372 physical energy-port gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract

ARM_IDS = [
    "base_zero",
    "port_zero",
    *[
        f"actor_{actor}_{sign}"
        for actor in range(4)
        for sign in ("positive", "negative")
    ],
]


def build_contract() -> dict[str, Any]:
    """Return the prospective finite physical-object contract."""

    energy = r272_frozen_bess_contract()
    return {
        "schema_version": 1,
        "round": "R372",
        "arm_ids": ARM_IDS.copy(),
        "steps": 5,
        "seed": 42,
        "dt_seconds": 0.2,
        "request_magnitude_system_pu": 0.04,
        "numeric_atol": 1.0e-9,
        "timing_atol_seconds": 1.0e-6,
        "noise_multiplier": 10.0,
        "system_mva": energy.system_mva,
        "device_energy_mwh": energy.device_energy_mwh,
        "soc_initial": energy.soc_initial,
        "soc_min": energy.soc_min,
        "soc_max": energy.soc_max,
        "charge_efficiency": energy.charge_efficiency,
        "discharge_efficiency": energy.discharge_efficiency,
        "expected_vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
        "expected_vsg_buses": [12, 16, 14, 15],
        "training_authorized": False,
        "retry_authorized": False,
    }


def action_request(
    arm_id: str,
    *,
    contract: Mapping[str, Any] | None = None,
) -> np.ndarray:
    """Return one frozen four-device power request for an arm."""

    spec = build_contract() if contract is None else contract
    if arm_id not in spec["arm_ids"]:
        raise KeyError(f"unknown R372 arm: {arm_id}")
    request = np.zeros(4, dtype=float)
    if arm_id.startswith("actor_"):
        _, actor, sign = arm_id.split("_")
        direction = 1.0 if sign == "positive" else -1.0
        request[int(actor)] = direction * float(
            spec["request_magnitude_system_pu"]
        )
    return request


def classify_records(
    records: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one complete immutable physical-object bank."""

    spec = build_contract() if contract is None else contract
    validity = _validity_pass(records, spec)
    if not validity:
        return _analysis(
            spec,
            "ANALYSIS-INVALID",
            {"validity": False},
        )
    by_arm = {str(record["arm_id"]): record for record in records}
    zero_action = _zero_action_pass(by_arm, spec)
    routing = _routing_pass(by_arm, spec)
    torque_power = _torque_power_pass(by_arm, spec)
    electrical, response_details = _electrical_response_pass(by_arm, spec)
    energy = _energy_accounting_pass(by_arm, spec)
    checks = {
        "validity": True,
        "zero_action_equivalence": zero_action,
        "identity_and_routing": routing,
        "sign_timing_and_torque_power_semantics": torque_power,
        "target_electrical_response": electrical,
        "achieved_power_energy_accounting": energy,
    }
    if not zero_action:
        classification = "STOP-ZERO-ACTION-DRIFT"
    elif not routing:
        classification = "STOP-PORT-ROUTING"
    elif not torque_power:
        classification = "STOP-TORQUE-POWER-SEMANTICS"
    elif not electrical:
        classification = "STOP-NO-ELECTRICAL-RESPONSE"
    elif not energy:
        classification = "STOP-ENERGY-ACCOUNTING"
    else:
        classification = "PHYSICAL-ENERGY-PORT-OBJECT-PASS"
    return _analysis(
        spec,
        classification,
        checks,
        electrical_response=response_details,
    )


def _analysis(
    spec: Mapping[str, Any],
    classification: str,
    checks: Mapping[str, bool],
    **details: Any,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": spec["round"],
        "classification": classification,
        "checks": dict(checks),
        **details,
        "training_authorized": False,
        "claim_scope": "finite physical object/interface gate on one V4 plant",
        "next_gate": "bounded_actuator_authority_and_deterministic_design",
    }


def _array(value: object, *, shape: tuple[int, ...]) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"expected finite array with shape {shape}")
    return array


def _validity_pass(
    records: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> bool:
    try:
        arm_ids = [str(record["arm_id"]) for record in records]
        if arm_ids != list(spec["arm_ids"]) or len(set(arm_ids)) != len(arm_ids):
            return False
        for record in records:
            identity = record["identity"]
            if (
                identity["n_agents"] != 4
                or identity["vsg_idx"] != spec["expected_vsg_idx"]
                or identity["vsg_buses"] != spec["expected_vsg_buses"]
                or record["completed_steps"] != spec["steps"]
                or record["tds_failed"] is not False
                or record.get("failure") is not None
                or len(record["steps"]) != spec["steps"]
            ):
                return False
            times = []
            for step in record["steps"]:
                if step["tds_failed"] is not False:
                    return False
                times.append(float(step["time"]))
                if not np.isfinite(times[-1]):
                    return False
                for key in (
                    "requested_power_system_pu",
                    "commanded_power_system_pu",
                    "sampled_omega_pu",
                    "baseline_pref_system_pu",
                    "pref_written_system_pu",
                    "pref_readback_system_pu",
                    "torque_readback_system_pu",
                    "achieved_power_system_pu",
                    "soc",
                    "charged_energy_mwh",
                    "discharged_energy_mwh",
                    "total_charged_energy_mwh",
                    "total_discharged_energy_mwh",
                    "omega",
                    "freq_hz_physical",
                    "P_es",
                    "M_es",
                    "D_es",
                    "delta_M",
                    "delta_D",
                ):
                    _array(step[key], shape=(4,))
                md_action = _array(step["md_action_norm"], shape=(4, 2))
                if not np.allclose(md_action, 0.0, atol=0.0, rtol=0.0):
                    return False
                if not np.allclose(step["delta_M"], 0.0, atol=0.0, rtol=0.0):
                    return False
                if not np.allclose(step["delta_D"], 0.0, atol=0.0, rtol=0.0):
                    return False
                if not np.allclose(step["M_es"], 200.0, atol=spec["numeric_atol"], rtol=0.0):
                    return False
                if not np.allclose(step["D_es"], 100.0, atol=spec["numeric_atol"], rtol=0.0):
                    return False
                if np.any(_array(step["sampled_omega_pu"], shape=(4,)) <= 0.0):
                    return False
                soc = _array(step["soc"], shape=(4,))
                if np.any(soc < spec["soc_min"]) or np.any(soc > spec["soc_max"]):
                    return False
            if len(times) > 1 and not np.allclose(
                np.diff(times),
                spec["dt_seconds"],
                atol=spec["timing_atol_seconds"],
                rtol=0.0,
            ):
                return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _trace(record: Mapping[str, Any], key: str) -> np.ndarray:
    return np.asarray([step[key] for step in record["steps"]], dtype=float)


def _zero_action_pass(
    by_arm: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> bool:
    atol = float(spec["numeric_atol"])
    base = by_arm["base_zero"]
    port = by_arm["port_zero"]
    for key in ("time",):
        base_values = np.asarray([step[key] for step in base["steps"]], dtype=float)
        port_values = np.asarray([step[key] for step in port["steps"]], dtype=float)
        if not np.allclose(base_values, port_values, atol=atol, rtol=0.0):
            return False
    for key in ("omega", "P_es", "M_es", "D_es"):
        if not np.allclose(_trace(base, key), _trace(port, key), atol=atol, rtol=0.0):
            return False
    for key in (
        "requested_power_system_pu",
        "commanded_power_system_pu",
        "achieved_power_system_pu",
        "charged_energy_mwh",
        "discharged_energy_mwh",
        "total_charged_energy_mwh",
        "total_discharged_energy_mwh",
    ):
        if not np.allclose(_trace(port, key), 0.0, atol=atol, rtol=0.0):
            return False
    return bool(
        np.allclose(
            _trace(port, "soc"),
            spec["soc_initial"],
            atol=atol,
            rtol=0.0,
        )
    )


def _signed_arms(spec: Mapping[str, Any]) -> list[str]:
    return [arm for arm in spec["arm_ids"] if str(arm).startswith("actor_")]


def _target(arm_id: str) -> int:
    return int(arm_id.split("_")[1])


def _routing_pass(
    by_arm: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> bool:
    atol = float(spec["numeric_atol"])
    for arm_id in _signed_arms(spec):
        target = _target(arm_id)
        expected_request = action_request(arm_id, contract=spec)
        for step in by_arm[arm_id]["steps"]:
            request = _array(step["requested_power_system_pu"], shape=(4,))
            command = _array(step["commanded_power_system_pu"], shape=(4,))
            baseline = _array(step["baseline_pref_system_pu"], shape=(4,))
            pref = _array(step["pref_written_system_pu"], shape=(4,))
            torque = _array(step["torque_readback_system_pu"], shape=(4,))
            soc = _array(step["soc"], shape=(4,))
            other = [index for index in range(4) if index != target]
            if not np.allclose(request, expected_request, atol=0.0, rtol=0.0):
                return False
            if not np.allclose(command, expected_request, atol=atol, rtol=0.0):
                return False
            if not np.allclose(pref[other], baseline[other], atol=atol, rtol=0.0):
                return False
            if not np.allclose(torque[other], baseline[other], atol=atol, rtol=0.0):
                return False
            if not np.allclose(soc[other], spec["soc_initial"], atol=atol, rtol=0.0):
                return False
            if abs(pref[target] - baseline[target]) <= atol:
                return False
    return True


def _torque_power_pass(
    by_arm: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> bool:
    atol = float(spec["numeric_atol"])
    for arm_id in _signed_arms(spec):
        target = _target(arm_id)
        direction = 1.0 if arm_id.endswith("positive") else -1.0
        for step in by_arm[arm_id]["steps"]:
            command = _array(step["commanded_power_system_pu"], shape=(4,))
            sampled = _array(step["sampled_omega_pu"], shape=(4,))
            omega = _array(step["omega"], shape=(4,))
            baseline = _array(step["baseline_pref_system_pu"], shape=(4,))
            written = _array(step["pref_written_system_pu"], shape=(4,))
            readback = _array(step["pref_readback_system_pu"], shape=(4,))
            torque = _array(step["torque_readback_system_pu"], shape=(4,))
            achieved = _array(step["achieved_power_system_pu"], shape=(4,))
            expected_written = baseline + command / sampled
            expected_achieved = (torque - baseline) * 0.5 * (sampled + omega)
            if not np.allclose(written, expected_written, atol=atol, rtol=0.0):
                return False
            if not np.allclose(readback, written, atol=atol, rtol=0.0):
                return False
            if not np.allclose(torque, written, atol=atol, rtol=0.0):
                return False
            if not np.allclose(achieved, expected_achieved, atol=atol, rtol=0.0):
                return False
            if direction * achieved[target] <= atol:
                return False
    return True


def _electrical_response_pass(
    by_arm: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    base = _trace(by_arm["base_zero"], "P_es")
    port = _trace(by_arm["port_zero"], "P_es")
    zero_drift = float(np.max(np.abs(base - port)))
    floor = max(
        float(spec["numeric_atol"]),
        float(spec["noise_multiplier"]) * zero_drift,
    )
    details: dict[str, Any] = {
        "zero_action_electrical_drift_system_pu": zero_drift,
        "response_floor_system_pu": floor,
        "arms": {},
    }
    passed = True
    for arm_id in _signed_arms(spec):
        target = _target(arm_id)
        effect = float(
            np.max(np.abs(_trace(by_arm[arm_id], "P_es")[:, target] - port[:, target]))
        )
        arm_pass = effect > floor
        details["arms"][arm_id] = {
            "target_max_abs_effect_system_pu": effect,
            "passed": arm_pass,
        }
        passed = passed and arm_pass
    return passed, details


def _energy_accounting_pass(
    by_arm: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> bool:
    atol = float(spec["numeric_atol"])
    for arm_id in _signed_arms(spec):
        target = _target(arm_id)
        expected_soc = np.full(4, float(spec["soc_initial"]))
        expected_charged_total = np.zeros(4)
        expected_discharged_total = np.zeros(4)
        for step in by_arm[arm_id]["steps"]:
            achieved = _array(step["achieved_power_system_pu"], shape=(4,))
            grid_energy = (
                np.abs(achieved)
                * float(spec["system_mva"])
                * float(spec["dt_seconds"])
                / 3600.0
            )
            expected_charged = np.where(
                achieved < 0.0,
                grid_energy * float(spec["charge_efficiency"]),
                0.0,
            )
            expected_discharged = np.where(
                achieved > 0.0,
                grid_energy / float(spec["discharge_efficiency"]),
                0.0,
            )
            expected_soc += (
                expected_charged - expected_discharged
            ) / float(spec["device_energy_mwh"])
            expected_charged_total += expected_charged
            expected_discharged_total += expected_discharged
            comparisons = (
                (step["charged_energy_mwh"], expected_charged),
                (step["discharged_energy_mwh"], expected_discharged),
                (step["total_charged_energy_mwh"], expected_charged_total),
                (step["total_discharged_energy_mwh"], expected_discharged_total),
                (step["soc"], expected_soc),
            )
            if any(
                not np.allclose(actual, expected, atol=atol, rtol=0.0)
                for actual, expected in comparisons
            ):
                return False
        other = [index for index in range(4) if index != target]
        if not np.allclose(expected_soc[other], spec["soc_initial"], atol=atol, rtol=0.0):
            return False
        if arm_id.endswith("positive") and not expected_soc[target] < spec["soc_initial"]:
            return False
        if arm_id.endswith("negative") and not expected_soc[target] > spec["soc_initial"]:
            return False
    return True


__all__ = ["action_request", "build_contract", "classify_records"]
