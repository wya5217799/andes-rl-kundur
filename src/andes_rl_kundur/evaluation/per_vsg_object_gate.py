"""Pure contract and classifier for the R365 per-VSG object gate.

The module intentionally contains no ANDES import and no learning code.  It
turns a complete, prospectively frozen intervention bank into one typed gate
classification.  The WSL runner owns physical execution and provenance.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping, Sequence

import numpy as np


EXPECTED_VSG_IDS = ("VSG_1", "VSG_2", "VSG_3", "VSG_4")
EXPECTED_VSG_BUSES = (12, 16, 14, 15)
COMM_ADJ = {0: (1, 3), 1: (0, 2), 2: (1, 3), 3: (2, 0)}
ARM_IDS = (
    "zero_a",
    "zero_b",
    "single_0",
    "single_1",
    "single_2",
    "single_3",
    "fingerprint",
    "mismatch",
)


def build_contract() -> dict[str, Any]:
    """Return the immutable scientific contract as JSON-compatible data."""

    comm_adj = {str(key): list(value) for key, value in COMM_ADJ.items()}
    comm_eta = {
        f"{source}->{target}": 1
        for source, neighbours in COMM_ADJ.items()
        for target in neighbours
    }
    return {
        "schema_version": 1,
        "round": "R365",
        "question": "Q-0101",
        "arm_ids": list(ARM_IDS),
        "steps": 30,
        "dt_seconds": 0.2,
        "seed": 42,
        "vsg_ids": list(EXPECTED_VSG_IDS),
        "vsg_buses": list(EXPECTED_VSG_BUSES),
        "comm_adj": comm_adj,
        "comm_eta": comm_eta,
        "obs_dim": 7,
        "control_nominal_frequency_hz": 50.0,
        "physical_nominal_frequency_hz": 60.0,
        "baseline_m0": [200.0] * 4,
        "baseline_d0": [100.0] * 4,
        "mismatch_d0": [70.0, 90.0, 130.0, 150.0],
        "dm_min": -200.0,
        "dm_max": 600.0,
        "dd_min": -200.0,
        "dd_max": 600.0,
        "m_min_physical": 20.0,
        "d_min_physical": 10.0,
        "single_action": [0.25, -0.10],
        "fingerprint_amplitude": 0.25,
        "mapping_atol": 1.0e-9,
        "observation_atol": 2.0e-6,
        "frequency_noise_floor_hz": 1.0e-7,
        "power_noise_floor_pu": 1.0e-8,
        "noise_multiplier": 10.0,
        "direction_reversals_required": 2,
        "training_authorized": False,
    }


def action_schedule(
    arm_id: str,
    step_index: int,
    *,
    contract: Mapping[str, Any] | None = None,
) -> np.ndarray:
    """Return the frozen four-by-two normalized action for one decision."""

    spec = build_contract() if contract is None else contract
    if arm_id not in spec["arm_ids"]:
        raise ValueError(f"unknown arm_id: {arm_id}")
    if not 0 <= step_index < int(spec["steps"]):
        raise ValueError(f"step_index out of range: {step_index}")
    action = np.zeros((4, 2), dtype=float)
    if arm_id.startswith("single_"):
        actor = int(arm_id.rsplit("_", 1)[1])
        action[actor] = np.asarray(spec["single_action"], dtype=float)
    elif arm_id == "fingerprint" and step_index < 8:
        action.reshape(-1)[step_index] = float(spec["fingerprint_amplitude"])
    return action


def _decode_channel(value: np.ndarray, lower: float, upper: float) -> np.ndarray:
    return np.where(value >= 0.0, value * upper, value * (-lower))


def decode_action_matrix(
    action: Sequence[Sequence[float]] | np.ndarray,
    *,
    m0: Sequence[float] | np.ndarray,
    d0: Sequence[float] | np.ndarray,
    contract: Mapping[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply the V4 zero-centred decoder without importing the environment."""

    spec = build_contract() if contract is None else contract
    values = np.asarray(action, dtype=float)
    if values.shape != (4, 2):
        raise ValueError(f"action must have shape (4, 2), got {values.shape}")
    clipped = np.clip(values, -1.0, 1.0)
    delta_m = _decode_channel(
        clipped[:, 0], float(spec["dm_min"]), float(spec["dm_max"])
    )
    delta_d = _decode_channel(
        clipped[:, 1], float(spec["dd_min"]), float(spec["dd_max"])
    )
    expected_m = np.maximum(
        np.asarray(m0, dtype=float) + delta_m,
        float(spec["m_min_physical"]),
    )
    expected_d = np.maximum(
        np.asarray(d0, dtype=float) + delta_d,
        float(spec["d_min_physical"]),
    )
    return delta_m, delta_d, expected_m, expected_d


def _array(value: object, *, shape: tuple[int, ...] | None = None) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if shape is not None and array.shape != shape:
        raise ValueError(f"expected shape {shape}, got {array.shape}")
    return array


def _records_by_arm(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for record in records:
        arm_id = str(record.get("arm_id", ""))
        if arm_id in result:
            raise ValueError(f"duplicate arm: {arm_id}")
        result[arm_id] = record
    return result


def _identity_pass(records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> bool:
    for record in records:
        identity = record.get("identity")
        if not isinstance(identity, Mapping):
            return False
        if int(identity.get("n_agents", -1)) != 4:
            return False
        if list(identity.get("vsg_idx", [])) != list(spec["vsg_ids"]):
            return False
        if list(identity.get("vsg_buses", [])) != list(spec["vsg_buses"]):
            return False
        if identity.get("comm_adj") != spec["comm_adj"]:
            return False
        if identity.get("comm_eta") != spec["comm_eta"]:
            return False
        if int(identity.get("obs_dim", -1)) != int(spec["obs_dim"]):
            return False
        if identity.get("observation_augmentations") != {
            "own_action": False,
            "time": False,
            "area_mean": False,
        }:
            return False
    return True


def _validity_pass(records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> bool:
    if len(records) != len(spec["arm_ids"]):
        return False
    try:
        by_arm = _records_by_arm(records)
    except ValueError:
        return False
    if set(by_arm) != set(spec["arm_ids"]):
        return False
    for record in records:
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != int(spec["steps"]):
            return False
        if int(record.get("completed_steps", -1)) != int(spec["steps"]):
            return False
        if record.get("tds_failed") is not False:
            return False
        times: list[float] = []
        for index, step in enumerate(steps):
            if int(step.get("step_index", -1)) != index:
                return False
            if step.get("tds_failed") is not False:
                return False
            arrays = []
            try:
                arrays = [
                    _array(step["action_norm"], shape=(4, 2)),
                    _array(step["observation"]),
                    _array(step["omega"], shape=(4,)),
                    _array(step["omega_dot"], shape=(4,)),
                    _array(step["freq_hz_physical"], shape=(4,)),
                    _array(step["P_es"], shape=(4,)),
                    _array(step["M_es"], shape=(4,)),
                    _array(step["D_es"], shape=(4,)),
                    _array(step["delta_M"], shape=(4,)),
                    _array(step["delta_D"], shape=(4,)),
                ]
            except (KeyError, TypeError, ValueError):
                return False
            if not all(np.all(np.isfinite(array)) for array in arrays):
                return False
            if arrays[1].ndim != 2 or arrays[1].shape[0] != 4:
                return False
            action, _, omega, _, frequency, _, m_value, d_value, _, _ = arrays
            if np.max(np.abs(action)) > 1.0 + 1.0e-12:
                return False
            if np.min(m_value) < float(spec["m_min_physical"]) - 1.0e-12:
                return False
            if np.min(d_value) < float(spec["d_min_physical"]) - 1.0e-12:
                return False
            if not np.allclose(
                frequency,
                omega * float(spec["physical_nominal_frequency_hz"]),
                atol=1.0e-10,
                rtol=0.0,
            ):
                return False
            times.append(float(step["time"]))
        if len(times) > 1 and not np.allclose(
            np.diff(times), float(spec["dt_seconds"]), atol=1.0e-6, rtol=0.0
        ):
            return False
    return True


def _mapping_pass(records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> bool:
    atol = float(spec["mapping_atol"])
    by_arm = _records_by_arm(records)
    for arm_id, record in by_arm.items():
        identity = record["identity"]
        m0 = _array(identity["baseline_m0"], shape=(4,))
        d0 = _array(identity["baseline_d0"], shape=(4,))
        for step_index, step in enumerate(record["steps"]):
            action = _array(step["action_norm"], shape=(4, 2))
            frozen = action_schedule(arm_id, step_index, contract=spec)
            if not np.allclose(action, frozen, atol=0.0, rtol=0.0):
                return False
            delta_m, delta_d, expected_m, expected_d = decode_action_matrix(
                action, m0=m0, d0=d0, contract=spec
            )
            if not np.allclose(step["delta_M"], delta_m, atol=atol, rtol=0.0):
                return False
            if not np.allclose(step["delta_D"], delta_d, atol=atol, rtol=0.0):
                return False
            if not np.allclose(step["M_es"], expected_m, atol=atol, rtol=0.0):
                return False
            if not np.allclose(step["D_es"], expected_d, atol=atol, rtol=0.0):
                return False

    fingerprint = by_arm["fingerprint"]
    action_rows = []
    readback_rows = []
    m0 = _array(fingerprint["identity"]["baseline_m0"], shape=(4,))
    d0 = _array(fingerprint["identity"]["baseline_d0"], shape=(4,))
    for step in fingerprint["steps"][:8]:
        action_rows.append(_array(step["action_norm"], shape=(4, 2)).reshape(-1))
        readback = np.column_stack(
            (
                _array(step["M_es"], shape=(4,)) - m0,
                _array(step["D_es"], shape=(4,)) - d0,
            )
        )
        readback_rows.append(readback.reshape(-1))
    return bool(
        np.linalg.matrix_rank(np.asarray(action_rows)) == 8
        and np.linalg.matrix_rank(np.asarray(readback_rows)) == 8
    )


def _observation_pass(records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> bool:
    atol = float(spec["observation_atol"])
    scale = float(spec["control_nominal_frequency_hz"]) * 2.0 * np.pi
    for record in records:
        for step in record["steps"]:
            omega = _array(step["omega"], shape=(4,))
            omega_dot = _array(step["omega_dot"], shape=(4,))
            power = _array(step["P_es"], shape=(4,))
            try:
                observed = _array(step["observation"], shape=(4, 7))
            except (TypeError, ValueError):
                return False
            expected = np.zeros((4, 7), dtype=float)
            for agent, neighbours in COMM_ADJ.items():
                expected[agent, 0] = power[agent] / 2.0
                expected[agent, 1] = (omega[agent] - 1.0) * scale / 3.0
                expected[agent, 2] = omega_dot[agent] * scale / 5.0
                for offset, neighbour in enumerate(neighbours):
                    expected[agent, 3 + offset] = (
                        (omega[neighbour] - 1.0) * scale / 3.0
                    )
                    expected[agent, 5 + offset] = omega_dot[neighbour] * scale / 5.0
            if not np.allclose(observed, expected, atol=atol, rtol=0.0):
                return False
    return True


def _trace(record: Mapping[str, Any], key: str) -> np.ndarray:
    return np.asarray([step[key] for step in record["steps"]], dtype=float)


def _noise_floors(
    by_arm: Mapping[str, Mapping[str, Any]], spec: Mapping[str, Any]
) -> dict[str, float]:
    frequency_drift = float(
        np.max(np.abs(_trace(by_arm["zero_a"], "freq_hz_physical") - _trace(by_arm["zero_b"], "freq_hz_physical")))
    )
    power_drift = float(
        np.max(np.abs(_trace(by_arm["zero_a"], "P_es") - _trace(by_arm["zero_b"], "P_es")))
    )
    multiplier = float(spec["noise_multiplier"])
    return {
        "frequency_hz": max(
            float(spec["frequency_noise_floor_hz"]), multiplier * frequency_drift
        ),
        "power_pu": max(
            float(spec["power_noise_floor_pu"]), multiplier * power_drift
        ),
        "repeat_frequency_drift_hz": frequency_drift,
        "repeat_power_drift_pu": power_drift,
    }


def _authority_pass(
    by_arm: Mapping[str, Mapping[str, Any]], floors: Mapping[str, float]
) -> tuple[bool, dict[str, dict[str, float | bool]]]:
    baseline_f = _trace(by_arm["zero_a"], "freq_hz_physical")
    baseline_p = _trace(by_arm["zero_a"], "P_es")
    details: dict[str, dict[str, float | bool]] = {}
    all_pass = True
    for actor in range(4):
        arm_id = f"single_{actor}"
        other = [index for index in range(4) if index != actor]
        max_frequency = float(
            np.max(np.abs(_trace(by_arm[arm_id], "freq_hz_physical")[:, other] - baseline_f[:, other]))
        )
        max_power = float(
            np.max(np.abs(_trace(by_arm[arm_id], "P_es")[:, other] - baseline_p[:, other]))
        )
        passed = bool(
            max_frequency > float(floors["frequency_hz"])
            or max_power > float(floors["power_pu"])
        )
        details[arm_id] = {
            "max_off_target_frequency_effect_hz": max_frequency,
            "max_off_target_power_effect_pu": max_power,
            "passed": passed,
        }
        all_pass = all_pass and passed
    return all_pass, details


def _direction_reversals(series: np.ndarray, floor: float) -> int:
    differences = np.diff(np.asarray(series, dtype=float))
    signs = np.sign(differences[np.abs(differences) > floor])
    if signs.size < 2:
        return 0
    return int(np.sum(signs[1:] != signs[:-1]))


def _differential_pass(
    by_arm: Mapping[str, Mapping[str, Any]],
    floors: Mapping[str, float],
    spec: Mapping[str, Any],
) -> tuple[bool, dict[str, float | int | bool]]:
    mismatch_f = _trace(by_arm["mismatch"], "freq_hz_physical")
    mismatch_p = _trace(by_arm["mismatch"], "P_es")
    zero_a = _trace(by_arm["zero_a"], "freq_hz_physical")
    zero_b = _trace(by_arm["zero_b"], "freq_hz_physical")
    spread = float(np.max(np.ptp(mismatch_f, axis=1)))
    centered = mismatch_f - np.mean(mismatch_f, axis=1, keepdims=True)
    energy = float(np.sum(np.mean(centered**2, axis=1)) * float(spec["dt_seconds"]))
    repeat_energy = float(
        np.sum(np.mean((zero_a - zero_b) ** 2, axis=1))
        * float(spec["dt_seconds"])
    )
    energy_floor = max(
        10.0 * repeat_energy,
        float(floors["frequency_hz"]) ** 2 * float(spec["dt_seconds"]),
    )
    max_reversals = 0
    for source, target in combinations(range(4), 2):
        max_reversals = max(
            max_reversals,
            _direction_reversals(
                mismatch_f[:, source] - mismatch_f[:, target],
                float(floors["frequency_hz"]),
            ),
            _direction_reversals(
                mismatch_p[:, source] - mismatch_p[:, target],
                float(floors["power_pu"]),
            ),
        )
    passed = bool(
        spread > float(floors["frequency_hz"])
        and energy > energy_floor
        and max_reversals >= int(spec["direction_reversals_required"])
    )
    return passed, {
        "maximum_pairwise_frequency_spread_hz": spread,
        "differential_frequency_energy_hz2_s": energy,
        "differential_frequency_energy_floor_hz2_s": energy_floor,
        "maximum_direction_reversals": max_reversals,
        "passed": passed,
    }


def classify_records(
    records: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one complete R365 bank without inspecting rewards."""

    spec = build_contract() if contract is None else contract
    validity = _validity_pass(records, spec)
    if not validity:
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": {"validity": False},
            "training_authorized": False,
        }
    by_arm = _records_by_arm(records)
    identity = _identity_pass(records, spec)
    mapping = _mapping_pass(records, spec)
    information = _observation_pass(records, spec)
    floors = _noise_floors(by_arm, spec)
    differential, differential_details = _differential_pass(by_arm, floors, spec)
    authority, authority_details = _authority_pass(by_arm, floors)
    checks = {
        "validity": validity,
        "identity": identity,
        "independent_action_mapping": mapping,
        "same_instant_local_neighbour_information": information,
        "differential_dynamics": differential,
        "network_transmitted_action_authority": authority,
    }
    if not identity or not mapping:
        classification = "STOP-OBJECT-MAPPING"
    elif not information:
        classification = "STOP-INFORMATION-CONTRACT"
    elif not differential:
        classification = "STOP-NO-DIFFERENTIAL-DYNAMICS"
    elif not authority:
        classification = "STOP-NO-ACTION-AUTHORITY"
    else:
        classification = "PER-VSG-OBJECT-GATE-PASS"
    return {
        "schema_version": 1,
        "round": spec["round"],
        "question": spec["question"],
        "classification": classification,
        "checks": checks,
        "noise_floors": floors,
        "differential_dynamics": differential_details,
        "action_authority": authority_details,
        "training_authorized": False,
        "claim_scope": (
            "finite deterministic object/interface gate on the registered V4 plant"
        ),
    }


__all__ = [
    "action_schedule",
    "build_contract",
    "classify_records",
    "decode_action_matrix",
]
