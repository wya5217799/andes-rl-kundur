from __future__ import annotations

import copy

import numpy as np
import pytest

from andes_rl_kundur.evaluation.vsg_energy_port_object_gate import (
    action_request,
    build_contract,
    classify_records,
)


def _synthetic_records() -> list[dict[str, object]]:
    contract = build_contract()
    records: list[dict[str, object]] = []
    for arm_id in contract["arm_ids"]:
        request = action_request(arm_id, contract=contract)
        soc = np.full(4, 0.5)
        charged_total = np.zeros(4)
        discharged_total = np.zeros(4)
        steps: list[dict[str, object]] = []
        for step_index in range(contract["steps"]):
            achieved = request.copy()
            grid_energy = np.abs(achieved) * 100.0 * 0.2 / 3600.0
            charged = np.where(achieved < 0.0, grid_energy * 0.9848857802, 0.0)
            discharged = np.where(
                achieved > 0.0,
                grid_energy / 0.9848857802,
                0.0,
            )
            soc = soc + (charged - discharged) / 28.0
            charged_total += charged
            discharged_total += discharged
            electrical_power = np.full(4, 0.5) + achieved
            steps.append(
                {
                    "step_index": step_index,
                    "time": 0.7 + 0.2 * step_index,
                    "requested_power_system_pu": request.tolist(),
                    "commanded_power_system_pu": request.tolist(),
                    "sampled_omega_pu": np.ones(4).tolist(),
                    "baseline_pref_system_pu": np.full(4, 0.5).tolist(),
                    "pref_written_system_pu": (np.full(4, 0.5) + request).tolist(),
                    "pref_readback_system_pu": (np.full(4, 0.5) + request).tolist(),
                    "torque_readback_system_pu": (np.full(4, 0.5) + request).tolist(),
                    "achieved_power_system_pu": achieved.tolist(),
                    "soc": soc.tolist(),
                    "charged_energy_mwh": charged.tolist(),
                    "discharged_energy_mwh": discharged.tolist(),
                    "total_charged_energy_mwh": charged_total.tolist(),
                    "total_discharged_energy_mwh": discharged_total.tolist(),
                    "saturation_reasons": [[], [], [], []],
                    "omega": np.ones(4).tolist(),
                    "freq_hz_physical": np.full(4, 60.0).tolist(),
                    "P_es": electrical_power.tolist(),
                    "M_es": np.full(4, 200.0).tolist(),
                    "D_es": np.full(4, 100.0).tolist(),
                    "delta_M": np.zeros(4).tolist(),
                    "delta_D": np.zeros(4).tolist(),
                    "md_action_norm": np.zeros((4, 2)).tolist(),
                    "tds_failed": False,
                }
            )
        records.append(
            {
                "arm_id": arm_id,
                "identity": {
                    "n_agents": 4,
                    "vsg_idx": contract["expected_vsg_idx"],
                    "vsg_buses": contract["expected_vsg_buses"],
                },
                "steps": steps,
                "completed_steps": contract["steps"],
                "tds_failed": False,
                "failure": None,
            }
        )
    return records


def test_contract_freezes_two_zero_arms_and_signed_single_actor_arms() -> None:
    contract = build_contract()

    assert contract["arm_ids"] == [
        "base_zero",
        "port_zero",
        "actor_0_positive",
        "actor_0_negative",
        "actor_1_positive",
        "actor_1_negative",
        "actor_2_positive",
        "actor_2_negative",
        "actor_3_positive",
        "actor_3_negative",
    ]
    assert contract["steps"] == 5
    assert contract["dt_seconds"] == 0.2
    assert contract["request_magnitude_system_pu"] == 0.04
    assert np.array_equal(action_request("port_zero", contract=contract), np.zeros(4))
    assert np.array_equal(
        action_request("actor_2_negative", contract=contract),
        np.asarray([0.0, 0.0, -0.04, 0.0]),
    )
    assert contract["training_authorized"] is False


def test_complete_object_matched_bank_passes_without_authorizing_training() -> None:
    analysis = classify_records(_synthetic_records())

    assert analysis["classification"] == "PHYSICAL-ENERGY-PORT-OBJECT-PASS"
    assert all(analysis["checks"].values())
    assert analysis["training_authorized"] is False
    assert analysis["next_gate"] == "bounded_actuator_authority_and_deterministic_design"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("invalid", "ANALYSIS-INVALID"),
        ("zero", "STOP-ZERO-ACTION-DRIFT"),
        ("routing", "STOP-PORT-ROUTING"),
        ("torque", "STOP-TORQUE-POWER-SEMANTICS"),
        ("electrical", "STOP-NO-ELECTRICAL-RESPONSE"),
        ("energy", "STOP-ENERGY-ACCOUNTING"),
    ],
)
def test_classifier_returns_typed_stop_for_each_physical_failure(
    mutation: str,
    expected: str,
) -> None:
    records = _synthetic_records()
    by_arm = {record["arm_id"]: record for record in records}
    if mutation == "invalid":
        records[0]["steps"][0]["tds_failed"] = True
    elif mutation == "zero":
        by_arm["port_zero"]["steps"][0]["omega"][0] += 1.0e-4
    elif mutation == "routing":
        by_arm["actor_0_positive"]["steps"][0]["torque_readback_system_pu"][1] += 0.01
    elif mutation == "torque":
        by_arm["actor_0_positive"]["steps"][0]["achieved_power_system_pu"][0] += 0.01
    elif mutation == "electrical":
        zero_steps = by_arm["port_zero"]["steps"]
        for arm_id, record in by_arm.items():
            if str(arm_id).startswith("actor_"):
                for step, zero_step in zip(record["steps"], zero_steps, strict=True):
                    step["P_es"] = copy.deepcopy(zero_step["P_es"])
    else:
        by_arm["actor_0_positive"]["steps"][0]["soc"][0] -= 0.01

    analysis = classify_records(records)

    assert analysis["classification"] == expected
    assert analysis["training_authorized"] is False
