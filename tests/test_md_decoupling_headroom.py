from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.md_decoupling_headroom import (
    build_contract,
    classify_bank,
    summarise_profile,
)


def test_contract_freezes_disjoint_six_scenario_profile_banks() -> None:
    contract = build_contract()

    profiles = contract["profiles"]
    assert [profile["profile_id"] for profile in profiles] == [
        "dev_a",
        "dev_b",
        "eval_a",
        "eval_b",
        "eval_c",
        "eval_d",
    ]
    assert [profile["split"] for profile in profiles] == [
        "development",
        "development",
        "evaluation",
        "evaluation",
        "evaluation",
        "evaluation",
    ]
    assert all(len(profile["scenarios"]) == 6 for profile in profiles)
    scenario_ids = [
        scenario["scenario_id"]
        for profile in profiles
        for scenario in profile["scenarios"]
    ]
    assert len(scenario_ids) == len(set(scenario_ids)) == 36
    assert contract["steps"] == 30
    assert contract["dt_seconds"] == 0.2
    assert contract["seed"] == 399
    assert contract["thresholds"] == {
        "minimum_joint_improvement": 0.05,
        "maximum_common_harm": 0.03,
        "maximum_action_stress_harm": 0.10,
        "maximum_action_saturation_fraction": 0.05,
        "nonconstant_action_variation_floor": 1.0e-6,
        "independent_action_dispersion_floor": 1.0e-6,
    }
    assert np.allclose(
        contract["differential_transform"],
        [
            [0.5, 0.5, -0.5, -0.5],
            [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0, 0.0],
            [0.0, 0.0, 1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)],
        ],
    )
    assert contract["reward_used_for_gate"] is False
    assert contract["training_authorized"] is False


def _physical_record(
    *,
    scenario: dict[str, object],
    arm_id: str,
    deviations: np.ndarray,
) -> dict[str, object]:
    baseline_m = np.asarray([200.0, 200.0, 200.0, 200.0])
    baseline_d = np.asarray([100.0, 100.0, 100.0, 100.0])
    actions = np.zeros((deviations.shape[0], 4, 2), dtype=float)
    steps = []
    for index, deviation in enumerate(deviations):
        steps.append(
            {
                "step_index": index,
                "time": (index + 1) * 0.2,
                "freq_hz_physical": (60.0 + deviation).tolist(),
                "action_norm": actions[index].tolist(),
                "delta_M": [0.0] * 4,
                "delta_D": [0.0] * 4,
                "M_es": baseline_m.tolist(),
                "D_es": baseline_d.tolist(),
                "tds_failed": False,
            }
        )
    return {
        "profile_id": scenario["profile_id"],
        "scenario_id": scenario["scenario_id"],
        "pair_kind": scenario["pair_kind"],
        "sign": scenario["sign"],
        "magnitude": scenario["magnitude"],
        "arm_id": arm_id,
        "identity": {
            "baseline_m0": baseline_m.tolist(),
            "baseline_d0": baseline_d.tolist(),
        },
        "initial_freq_hz_physical": [60.0] * 4,
        "steps": steps,
        "completed": True,
        "tds_failed": False,
    }


def test_summarise_profile_uses_signed_odd_physical_responses() -> None:
    contract = build_contract()
    contract["steps"] = 2
    profile = dict(contract["profiles"][0])
    for scenario in profile["scenarios"]:
        scenario["magnitude"] = 1.0

    positive = {
        "common": np.asarray([[1.0, 1.0, -1.0, -1.0]] * 2),
        "differential": np.asarray([[1.5, -0.5, 1.5, -0.5]] * 2),
        "localized": np.asarray([[1.0, 0.0, 0.0, 0.0]] * 2),
    }
    records = []
    for scenario in profile["scenarios"]:
        response = positive[str(scenario["pair_kind"])]
        if scenario["sign"] == "negative":
            response = -response
        records.append(
            _physical_record(
                scenario=scenario,
                arm_id="zero",
                deviations=response,
            )
        )

    summary = summarise_profile(records, contract=contract)

    assert summary["valid"] is True
    assert np.isclose(summary["off_diagonal_response_energy"], 19.0 / 30.0)
    assert np.isclose(summary["disturbance_differential_energy"], 7.0 / 6.0)
    assert np.isclose(summary["common_frequency_iae_hz_s"], 0.6)
    assert np.isclose(summary["worst_unit_peak_hz"], 1.5)
    assert np.isclose(summary["worst_rocof_hz_s"], 7.5)
    assert summary["action_rms"] == 0.0
    assert summary["action_total_variation"] == 0.0
    assert summary["actuator_mapping_pass"] is True


def _summary(
    *,
    profile_id: str,
    split: str,
    arm_id: str,
    off_diagonal: float,
    differential: float,
    common: float = 1.0,
    peak: float = 1.0,
    rocof: float = 1.0,
    action_rms: float = 0.5,
    action_variation: float = 1.0,
) -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "split": split,
        "arm_id": arm_id,
        "valid": True,
        "record_count": 6,
        "off_diagonal_response_energy": off_diagonal,
        "disturbance_differential_energy": differential,
        "common_frequency_iae_hz_s": common,
        "worst_unit_peak_hz": peak,
        "worst_rocof_hz_s": rocof,
        "differential_settling_seconds": {
            "common": 6.0,
            "differential": 6.0,
            "localized": 6.0,
        },
        "action_rms": action_rms,
        "action_total_variation": action_variation,
        "minimum_record_total_variation": action_variation / 6.0,
        "maximum_action_row_dispersion": 0.1,
        "minimum_record_action_row_dispersion": 0.01,
        "action_saturation_fraction": 0.0,
        "action_bound_violation": False,
        "action_slew_violation": False,
        "actuator_mapping_pass": True,
    }


def _passing_summary_bank() -> list[dict[str, object]]:
    contract = build_contract()
    selected = "local_neighbour_md_km1_kd1"
    oracle = "local_neighbour_md_km2_kd2"
    rows: list[dict[str, object]] = []
    for profile in contract["profiles"]:
        profile_id = str(profile["profile_id"])
        split = str(profile["split"])
        for arm_id in contract["arm_ids"]:
            if split == "development":
                off_diagonal = 10.0 if arm_id == "zero" else 8.0
                differential = 10.0 if arm_id == "zero" else 8.0
                if arm_id == selected:
                    off_diagonal = differential = 6.0
                elif arm_id == oracle:
                    off_diagonal = differential = 7.0
                common = 1.0 if arm_id == "zero" else 1.01
            else:
                off_diagonal = differential = 12.0 if arm_id == "zero" else 10.5
                common = 1.0
                if arm_id == selected:
                    off_diagonal = differential = 10.0
                elif arm_id == oracle:
                    off_diagonal = differential = 9.0
                    common = 1.01
            rows.append(
                _summary(
                    profile_id=profile_id,
                    split=split,
                    arm_id=str(arm_id),
                    off_diagonal=off_diagonal,
                    differential=differential,
                    common=common,
                )
            )
    return rows


def test_classify_bank_selects_development_baseline_and_passes_joint_headroom() -> None:
    decision = classify_bank(_passing_summary_bank(), contract=build_contract())

    assert decision["classification"] == "HEADROOM-PASS"
    assert decision["selected_deterministic_arm"] == "local_neighbour_md_km1_kd1"
    assert np.isclose(decision["oracle_gate"]["off_diagonal_improvement"], 0.10)
    assert np.isclose(decision["oracle_gate"]["differential_improvement"], 0.10)
    assert {
        row["arm_id"] for row in decision["oracle_gate"]["selected_profiles"]
    } == {"local_neighbour_md_km2_kd2"}
    assert decision["training_authorized"] is False


def test_classify_bank_stops_when_either_joint_metric_misses_five_percent() -> None:
    rows = _passing_summary_bank()
    for row in rows:
        if (
            row["split"] == "evaluation"
            and row["arm_id"] == "local_neighbour_md_km2_kd2"
        ):
            row["disturbance_differential_energy"] = 9.6

    decision = classify_bank(rows, contract=build_contract())

    assert decision["classification"] == "STOP-NO-JOINT-HEADROOM"
    assert decision["oracle_gate"]["off_diagonal_pass"] is True
    assert decision["oracle_gate"]["differential_pass"] is False


def test_classify_bank_rejects_incomplete_profile_arm_matrix() -> None:
    rows = _passing_summary_bank()
    rows.pop()

    decision = classify_bank(rows, contract=build_contract())

    assert decision["classification"] == "ANALYSIS-INVALID"
    assert decision["checks"]["complete_bank"] is False
