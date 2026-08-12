from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.deterministic_headroom import (
    build_contract,
    classify_summaries,
    summarise_record,
)


def _summary(
    scenario_id: str,
    arm_id: str,
    *,
    primary: float,
    secondary: float = 1.0,
    common: float = 1.0,
    variation: float = 0.1,
    saturation: float = 0.0,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "arm_id": arm_id,
        "completed": True,
        "tds_failed": False,
        "differential_frequency_energy_hz2_s": primary,
        "differential_power_energy_pu2_s": secondary,
        "common_frequency_iae_hz_s": common,
        "action_boundary_aware_total_variation": variation,
        "action_saturation_fraction": saturation,
        "action_bound_violation": False,
        "action_slew_violation": False,
        "maximum_action_row_dispersion": 0.05,
        "actuator_mapping_pass": True,
    }


def _passing_bank() -> list[dict[str, object]]:
    contract = build_contract()
    scenarios = [row["scenario_id"] for row in contract["scenarios"]]
    candidates = list(contract["candidate_arm_ids"])
    rows: list[dict[str, object]] = []
    for index, scenario in enumerate(scenarios):
        rows.append(_summary(scenario, "zero", primary=100.0, variation=0.0))
        for candidate_index, arm_id in enumerate(candidates):
            primary = 95.0 + candidate_index
            secondary = 2.0
            if candidate_index == 0:
                primary = 80.0
                secondary = 1.0
            elif candidate_index == 1:
                primary = 60.0 if index < 4 else 100.0
            elif candidate_index == 2:
                primary = 100.0 if index < 4 else 60.0
            rows.append(
                _summary(
                    scenario,
                    arm_id,
                    primary=primary,
                    secondary=secondary,
                )
            )
    return rows


def test_contract_has_balanced_strong_bank_and_exact_r366_family() -> None:
    contract = build_contract()

    assert contract["steps"] == 30
    assert contract["dt_seconds"] == 0.2
    assert contract["baseline_d0"] == [70.0, 90.0, 130.0, 150.0]
    assert len(contract["scenarios"]) == 8
    assert len(contract["candidate_arm_ids"]) == 9
    assert contract["arm_ids"] == ["zero", *contract["candidate_arm_ids"]]
    assert {
        (row["location"], row["sign"])
        for row in contract["scenarios"]
    } == {
        (location, sign)
        for location in ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
        for sign in ("negative", "positive")
    }
    assert contract["thresholds"] == {
        "deterministic_minimum_improvement": 0.10,
        "oracle_minimum_headroom": 0.05,
        "maximum_common_frequency_harm": 0.05,
        "maximum_action_saturation_fraction": 0.05,
        "nonconstant_action_variation_floor": 1e-6,
        "minimum_distinct_oracle_candidates": 2,
    }
    assert contract["training_authorized"] is False


def test_trace_summary_uses_physical_differential_and_absolute_action_metrics() -> None:
    contract = build_contract()
    record = {
        "scenario_id": "demo",
        "arm_id": "demo_arm",
        "completed": True,
        "tds_failed": False,
        "identity": {
            "baseline_m0": [200.0, 200.0, 200.0, 200.0],
            "baseline_d0": [70.0, 90.0, 130.0, 150.0],
        },
        "steps": [
            {
                "freq_hz_physical": [59.0, 61.0, 60.0, 60.0],
                "P_es": [-1.0, 1.0, 0.0, 0.0],
                "action_norm": [[0.1, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
                "delta_M": [60.0, 0.0, 0.0, 0.0],
                "delta_D": [0.0, 0.0, 0.0, 0.0],
                "M_es": [260.0, 200.0, 200.0, 200.0],
                "D_es": [70.0, 90.0, 130.0, 150.0],
            },
            {
                "freq_hz_physical": [58.0, 62.0, 60.0, 60.0],
                "P_es": [-2.0, 2.0, 0.0, 0.0],
                "action_norm": [[0.2, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
                "delta_M": [120.0, 0.0, 0.0, 0.0],
                "delta_D": [0.0, 0.0, 0.0, 0.0],
                "M_es": [320.0, 200.0, 200.0, 200.0],
                "D_es": [70.0, 90.0, 130.0, 150.0],
            },
        ],
    }

    summary = summarise_record(record, contract=contract, expected_steps=2)

    assert np.isclose(summary["differential_frequency_energy_hz2_s"], 0.5)
    assert np.isclose(summary["differential_power_energy_pu2_s"], 0.5)
    assert summary["common_frequency_iae_hz_s"] == 0.0
    assert np.isclose(summary["action_boundary_aware_total_variation"], 0.025)
    assert summary["action_saturation_fraction"] == 0.0
    assert summary["action_bound_violation"] is False
    assert summary["action_slew_violation"] is False
    assert summary["actuator_mapping_pass"] is True


def test_classifier_selects_one_global_controller_and_non_deployable_oracle() -> None:
    contract = build_contract()

    analysis = classify_summaries(_passing_bank(), contract=contract)

    assert analysis["classification"] == "DETERMINISTIC-AND-HEADROOM-PASS"
    assert analysis["deterministic_gate"]["passed"] is True
    assert np.isclose(
        analysis["deterministic_gate"]["aggregate_improvement_fraction"],
        0.20,
    )
    assert analysis["selected_deterministic_arm"] == contract["candidate_arm_ids"][0]
    assert analysis["oracle_gate"]["passed"] is True
    assert np.isclose(analysis["oracle_gate"]["headroom_fraction"], 0.25)
    assert analysis["oracle_gate"]["distinct_selected_candidates"] == 2
    assert analysis["oracle_gate"]["role"] == "non_deployable_outcome_selector"
    assert analysis["training_authorized"] is False


def test_classifier_rejects_common_harm_or_actuator_stress_before_selection() -> None:
    contract = build_contract()
    rows = _passing_bank()
    for row in rows:
        if row["arm_id"] == contract["candidate_arm_ids"][0]:
            row["common_frequency_iae_hz_s"] = 1.06
        elif row["arm_id"] in contract["candidate_arm_ids"][1:]:
            row["action_saturation_fraction"] = 0.06

    analysis = classify_summaries(rows, contract=contract)

    assert analysis["classification"] == "STOP-DETERMINISTIC-NO-EFFICACY"
    assert analysis["deterministic_gate"]["passed"] is False
    assert analysis["selected_deterministic_arm"] is None


def test_classifier_stops_when_oracle_is_static_or_has_no_incremental_headroom() -> None:
    contract = build_contract()
    rows = _passing_bank()
    for row in rows:
        if row["arm_id"] != "zero":
            row["differential_frequency_energy_hz2_s"] = 80.0
            row["action_boundary_aware_total_variation"] = 0.0

    analysis = classify_summaries(rows, contract=contract)

    assert analysis["classification"] == "STOP-NO-CONDITIONAL-HEADROOM"
    assert analysis["deterministic_gate"]["passed"] is True
    assert analysis["oracle_gate"]["headroom_pass"] is False
    assert analysis["oracle_gate"]["nonconstant_action_pass"] is False
    assert analysis["oracle_gate"]["distinct_candidate_pass"] is False


def test_classifier_fails_closed_on_missing_scenario_arm_pair() -> None:
    rows = _passing_bank()
    rows.pop()

    analysis = classify_summaries(rows, contract=build_contract())

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["complete_bank"] is False
    assert analysis["training_authorized"] is False


def test_classifier_fails_closed_on_actuator_mapping_mismatch() -> None:
    rows = _passing_bank()
    rows[1]["actuator_mapping_pass"] = False

    analysis = classify_summaries(rows, contract=build_contract())

    assert analysis["classification"] == "ANALYSIS-INVALID"
    assert analysis["checks"]["all_rows_valid"] is False
