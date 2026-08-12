from __future__ import annotations

import copy

import numpy as np
import pytest

from andes_rl_kundur.evaluation.vsg_energy_port_authority import (
    action_request,
    build_contract,
    classify_records,
)


def _synthetic_records() -> list[dict[str, object]]:
    contract = build_contract()
    records: list[dict[str, object]] = []
    for condition in contract["conditions"]:
        condition_id = str(condition["condition_id"])
        delta_u = dict(condition["delta_u"])
        condition_shift = 0.0 if condition_id == "nominal" else -0.01
        for arm_id in contract["arm_ids"]:
            request = action_request(str(arm_id), contract=contract)
            soc = np.full(4, 0.5)
            charged_total = np.zeros(4)
            discharged_total = np.zeros(4)
            rows: list[dict[str, object]] = []
            for step_index in range(contract["steps"]):
                achieved = request.copy()
                grid_energy = np.abs(achieved) * 100.0 * 0.2 / 3600.0
                charged = np.where(
                    achieved < 0.0,
                    grid_energy * 0.9848857802,
                    0.0,
                )
                discharged = np.where(
                    achieved > 0.0,
                    grid_energy / 0.9848857802,
                    0.0,
                )
                soc = soc + (charged - discharged) / 28.0
                charged_total += charged
                discharged_total += discharged
                dynamic_scale = 0.1 * (step_index + 1)
                rows.append(
                    {
                        "step_index": step_index,
                        "time": 0.7 + 0.2 * step_index,
                        "requested_power_system_pu": request.tolist(),
                        "commanded_power_system_pu": request.tolist(),
                        "sampled_omega_pu": np.ones(4).tolist(),
                        "baseline_pref_system_pu": np.full(4, 0.5).tolist(),
                        "pref_written_system_pu": (
                            np.full(4, 0.5) + request
                        ).tolist(),
                        "pref_readback_system_pu": (
                            np.full(4, 0.5) + request
                        ).tolist(),
                        "torque_readback_system_pu": (
                            np.full(4, 0.5) + request
                        ).tolist(),
                        "achieved_power_system_pu": achieved.tolist(),
                        "soc": soc.tolist(),
                        "charged_energy_mwh": charged.tolist(),
                        "discharged_energy_mwh": discharged.tolist(),
                        "total_charged_energy_mwh": charged_total.tolist(),
                        "total_discharged_energy_mwh": discharged_total.tolist(),
                        "saturation_reasons": [[], [], [], []],
                        "omega": np.ones(4).tolist(),
                        "freq_hz_physical": (
                            np.full(4, 60.0 + condition_shift)
                            + dynamic_scale * request
                        ).tolist(),
                        "P_es": (np.full(4, 0.5) + request).tolist(),
                        "M_es": np.full(4, 200.0).tolist(),
                        "D_es": np.full(4, 100.0).tolist(),
                        "delta_M": np.zeros(4).tolist(),
                        "delta_D": np.zeros(4).tolist(),
                        "md_action_norm": np.zeros((4, 2)).tolist(),
                        "tds_failed": False,
                        "done": step_index == contract["steps"] - 1,
                    }
                )
            records.append(
                {
                    "condition_id": condition_id,
                    "delta_u": delta_u,
                    "arm_id": str(arm_id),
                    "identity": {
                        "n_agents": 4,
                        "vsg_idx": contract["expected_vsg_idx"],
                        "vsg_buses": contract["expected_vsg_buses"],
                    },
                    "steps": rows,
                    "completed_steps": contract["steps"],
                    "tds_failed": False,
                    "failure": None,
                    "reward_used_for_gate": False,
                    "training_executed": False,
                }
            )
    return records


def _record(
    records: list[dict[str, object]],
    condition_id: str,
    arm_id: str,
) -> dict[str, object]:
    return next(
        record
        for record in records
        if record["condition_id"] == condition_id and record["arm_id"] == arm_id
    )


def _zero_achieved_and_energy(record: dict[str, object]) -> None:
    for row in record["steps"]:
        row["achieved_power_system_pu"] = [0.0] * 4
        row["soc"] = [0.5] * 4
        row["charged_energy_mwh"] = [0.0] * 4
        row["discharged_energy_mwh"] = [0.0] * 4
        row["total_charged_energy_mwh"] = [0.0] * 4
        row["total_discharged_energy_mwh"] = [0.0] * 4


def test_contract_freezes_three_conditions_and_four_physical_modes() -> None:
    contract = build_contract()

    assert contract["condition_ids"] == [
        "nominal",
        "load_bus14_plus_0p5",
        "load_bus15_plus_0p5",
    ]
    assert contract["mode_ids"] == [
        "common",
        "inter_area",
        "local_area_1",
        "local_area_2",
    ]
    assert contract["arm_ids"][:2] == ["zero_a", "zero_b"]
    assert contract["record_count"] == 30
    assert contract["steps"] == 40
    assert contract["training_authorized"] is False
    assert np.array_equal(
        action_request("inter_area_negative", contract=contract),
        np.asarray([-0.04, -0.04, 0.04, 0.04]),
    )


def test_complete_linear_mode_bank_passes_without_authorizing_training() -> None:
    analysis = classify_records(_synthetic_records())

    assert analysis["classification"] == "BOUNDED-ENERGY-PORT-AUTHORITY-PASS"
    assert all(analysis["checks"].values())
    assert analysis["training_authorized"] is False
    assert analysis["next_gate"] == (
        "permission_matched_deterministic_coordinator_design"
    )
    assert analysis["mode_authority"]["frequency_floor_hz"] == 1.0e-6


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("invalid", "ANALYSIS-INVALID"),
        ("noise", "STOP-AUTHORITY-NOISE"),
        ("unsafe", "STOP-UNSAFE-ACTUATION"),
        ("achieved", "STOP-NO-ACHIEVED-POWER-AUTHORITY"),
        ("electrical", "STOP-NO-ELECTRICAL-AUTHORITY"),
        ("frequency", "STOP-NO-RELEVANT-DYNAMIC-AUTHORITY"),
    ],
)
def test_classifier_returns_typed_stop_for_each_registered_failure(
    mutation: str,
    expected: str,
) -> None:
    records = _synthetic_records()
    nominal_zero_b = _record(records, "nominal", "zero_b")
    nominal_common_positive = _record(records, "nominal", "common_positive")
    nominal_common_negative = _record(records, "nominal", "common_negative")
    if mutation == "invalid":
        nominal_zero_b["tds_failed"] = True
    elif mutation == "noise":
        nominal_zero_b["steps"][0]["freq_hz_physical"][0] += 1.0e-4
    elif mutation == "unsafe":
        nominal_common_positive["steps"][0]["saturation_reasons"][0] = [
            "ramp"
        ]
    elif mutation == "achieved":
        _zero_achieved_and_energy(nominal_common_positive)
    elif mutation == "electrical":
        zero = _record(records, "nominal", "zero_a")
        for positive_row, negative_row, zero_row in zip(
            nominal_common_positive["steps"],
            nominal_common_negative["steps"],
            zero["steps"],
            strict=True,
        ):
            positive_row["P_es"] = copy.deepcopy(zero_row["P_es"])
            negative_row["P_es"] = copy.deepcopy(zero_row["P_es"])
    else:
        zero = _record(records, "nominal", "zero_a")
        for positive_row, negative_row, zero_row in zip(
            nominal_common_positive["steps"],
            nominal_common_negative["steps"],
            zero["steps"],
            strict=True,
        ):
            positive_row["freq_hz_physical"] = copy.deepcopy(
                zero_row["freq_hz_physical"]
            )
            negative_row["freq_hz_physical"] = copy.deepcopy(
                zero_row["freq_hz_physical"]
            )

    analysis = classify_records(records)

    assert analysis["classification"] == expected
    assert analysis["training_authorized"] is False
