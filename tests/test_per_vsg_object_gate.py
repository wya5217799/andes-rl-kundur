from __future__ import annotations

import copy

import numpy as np
import pytest

from andes_rl_kundur.evaluation.per_vsg_object_gate import (
    action_schedule,
    build_contract,
    classify_records,
    decode_action_matrix,
)


def _observation(
    *,
    agent: int,
    omega: np.ndarray,
    omega_dot: np.ndarray,
    power: np.ndarray,
    neighbours: dict[int, list[int]],
) -> list[float]:
    scale = 50.0 * 2.0 * np.pi
    row = [
        power[agent] / 2.0,
        (omega[agent] - 1.0) * scale / 3.0,
        omega_dot[agent] * scale / 5.0,
    ]
    row.extend((omega[index] - 1.0) * scale / 3.0 for index in neighbours[agent])
    row.extend(omega_dot[index] * scale / 5.0 for index in neighbours[agent])
    return np.asarray(row, dtype=np.float32).astype(float).tolist()


def _synthetic_records() -> list[dict[str, object]]:
    contract = build_contract()
    records: list[dict[str, object]] = []
    neighbours = {int(key): value for key, value in contract["comm_adj"].items()}
    for arm_id in contract["arm_ids"]:
        d0 = np.asarray(
            contract["mismatch_d0"]
            if arm_id == "mismatch"
            else contract["baseline_d0"],
            dtype=float,
        )
        steps: list[dict[str, object]] = []
        for step_index in range(contract["steps"]):
            action = action_schedule(arm_id, step_index, contract=contract)
            delta_m, delta_d, expected_m, expected_d = decode_action_matrix(
                action,
                m0=np.asarray(contract["baseline_m0"], dtype=float),
                d0=d0,
                contract=contract,
            )
            phase = 2.0 * np.pi * step_index / 9.0
            common_hz = 60.0 + 0.02 * np.sin(phase / 2.0)
            frequency_hz = np.full(4, common_hz)
            power = np.full(4, 0.5 + 0.01 * np.cos(phase / 2.0))
            if arm_id == "mismatch":
                frequency_hz += 0.01 * np.asarray(
                    [np.sin(phase), -np.sin(phase), np.cos(phase), -np.cos(phase)]
                )
                power += 0.02 * np.asarray(
                    [np.cos(phase), -np.cos(phase), np.sin(phase), -np.sin(phase)]
                )
            elif arm_id.startswith("single_"):
                target = int(arm_id.rsplit("_", 1)[1])
                frequency_hz[(target + 1) % 4] += 2.0e-4 * (target + 1)
                power[(target + 2) % 4] += 3.0e-4 * (target + 1)
            omega = frequency_hz / 60.0
            omega_dot = np.zeros(4)
            obs = [
                _observation(
                    agent=agent,
                    omega=omega,
                    omega_dot=omega_dot,
                    power=power,
                    neighbours=neighbours,
                )
                for agent in range(4)
            ]
            steps.append(
                {
                    "step_index": step_index,
                    "time": 0.7 + 0.2 * step_index,
                    "action_norm": action.tolist(),
                    "observation": obs,
                    "omega": omega.tolist(),
                    "omega_dot": omega_dot.tolist(),
                    "freq_hz_physical": frequency_hz.tolist(),
                    "P_es": power.tolist(),
                    "M_es": expected_m.tolist(),
                    "D_es": expected_d.tolist(),
                    "delta_M": delta_m.tolist(),
                    "delta_D": delta_d.tolist(),
                    "tds_failed": False,
                }
            )
        records.append(
            {
                "arm_id": arm_id,
                "identity": {
                    "n_agents": 4,
                    "vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
                    "vsg_buses": [12, 16, 14, 15],
                    "comm_adj": contract["comm_adj"],
                    "comm_eta": contract["comm_eta"],
                    "obs_dim": 7,
                    "observation_augmentations": {
                        "own_action": False,
                        "time": False,
                        "area_mean": False,
                    },
                    "baseline_m0": contract["baseline_m0"],
                    "baseline_d0": d0.tolist(),
                },
                "steps": steps,
                "completed_steps": contract["steps"],
                "tds_failed": False,
            }
        )
    return records


def _copy_dynamics(destination: dict[str, object], source: dict[str, object]) -> None:
    for key in (
        "observation",
        "omega",
        "omega_dot",
        "freq_hz_physical",
        "P_es",
    ):
        destination[key] = copy.deepcopy(source[key])


def test_contract_exposes_eight_arms_and_rank_eight_fingerprint() -> None:
    contract = build_contract()
    assert len(contract["arm_ids"]) == 8
    fingerprint = np.asarray(
        [
            action_schedule("fingerprint", index, contract=contract).reshape(-1)
            for index in range(8)
        ]
    )
    assert np.linalg.matrix_rank(fingerprint) == 8
    assert contract["training_authorized"] is False


def test_complete_synthetic_bank_passes() -> None:
    analysis = classify_records(_synthetic_records())
    assert analysis["classification"] == "PER-VSG-OBJECT-GATE-PASS"
    assert all(analysis["checks"].values())
    assert analysis["training_authorized"] is False


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("mapping", "STOP-OBJECT-MAPPING"),
        ("information", "STOP-INFORMATION-CONTRACT"),
        ("differential", "STOP-NO-DIFFERENTIAL-DYNAMICS"),
        ("authority", "STOP-NO-ACTION-AUTHORITY"),
        ("invalid", "ANALYSIS-INVALID"),
    ],
)
def test_classifier_returns_typed_stops(mutation: str, expected: str) -> None:
    records = _synthetic_records()
    if mutation == "mapping":
        fingerprint = next(row for row in records if row["arm_id"] == "fingerprint")
        fingerprint["steps"][0]["M_es"][1] += 1.0
    elif mutation == "information":
        for observation in records[0]["steps"][0]["observation"]:
            observation.append(99.0)
    elif mutation == "differential":
        mismatch = next(row for row in records if row["arm_id"] == "mismatch")
        zero = next(row for row in records if row["arm_id"] == "zero_a")
        for step, baseline in zip(mismatch["steps"], zero["steps"], strict=True):
            _copy_dynamics(step, baseline)
    elif mutation == "authority":
        zero = next(row for row in records if row["arm_id"] == "zero_a")
        for row in records:
                if row["arm_id"].startswith("single_"):
                    for step, baseline in zip(row["steps"], zero["steps"], strict=True):
                        _copy_dynamics(step, baseline)
    else:
        records[0]["steps"][0]["tds_failed"] = True
    assert classify_records(records)["classification"] == expected
