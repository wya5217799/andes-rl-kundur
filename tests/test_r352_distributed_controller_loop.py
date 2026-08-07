from __future__ import annotations

import numpy as np
import pytest

from scripts import run_r352_distributed_controller_loop as r352


def test_contract_freezes_disjoint_development_and_holdout_banks() -> None:
    contract = r352.build_contract()

    assert len(contract["candidate_gains"]) == 9
    assert len(contract["development_scenarios"]) == 16
    assert len(contract["holdout_scenarios"]) == 16
    assert {row["waveform"] for row in contract["development_scenarios"]} == {
        "ramp_hold_unit"
    }
    assert {row["waveform"] for row in contract["holdout_scenarios"]} == {
        "staggered_rise_unit"
    }
    assert contract["action_edges"] == [[0, 1], [1, 2], [2, 3]]
    assert contract["training_executed"] is False


def test_development_selection_uses_only_complete_registered_records() -> None:
    records = []
    for scenario in r352.development_scenarios():
        records.append(
            {
                "identity": "DEVELOPMENT",
                "scenario_id": scenario["scenario_id"],
                "arm": "zero_edge",
                "integrity_valid": True,
                "physical_guards_pass": True,
                "information_action_contract_pass": True,
                "metrics": {
                    "differential_coordinate_energy": 10.0,
                    "common_coordinate_iae": 4.0,
                    "controller_engaged": False,
                    "maximum_requested_fleet_imbalance_system_pu": 0.0,
                },
            }
        )
        for candidate in r352.candidate_grid():
            candidate_id = candidate["candidate_id"]
            ratio = 0.5 if candidate_id == "kf200_kr25" else 0.8
            records.append(
                {
                    "identity": "DEVELOPMENT",
                    "scenario_id": scenario["scenario_id"],
                    "arm": "local_candidate",
                    "candidate_id": candidate_id,
                    "integrity_valid": True,
                    "physical_guards_pass": True,
                    "information_action_contract_pass": True,
                    "metrics": {
                        "differential_coordinate_energy": 10.0 * ratio,
                        "common_coordinate_iae": 4.0,
                        "controller_engaged": True,
                        "maximum_requested_fleet_imbalance_system_pu": 0.0,
                    },
                }
            )

    selection = r352.select_development_candidate(records)

    assert selection["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED"
    assert selection["selected"]["candidate_id"] == "kf200_kr25"
    assert selection["holdout_records_inspected"] is False


def test_formal_classifier_uses_local_over_zero_and_keeps_joint_diagnostic() -> None:
    records = []
    for scenario in r352.holdout_scenarios():
        for arm, differential, common, engaged in (
            ("zero_edge", 10.0, 4.0, False),
            ("selected_local", 9.0, 4.1, True),
            ("joint_upper", 8.0, 4.0, True),
        ):
            records.append(
                {
                    "identity": "HOLDOUT",
                    "scenario_id": scenario["scenario_id"],
                    "arm": arm,
                    "integrity_valid": True,
                    "physical_guards_pass": True,
                    "information_action_contract_pass": True,
                    "metrics": {
                        "differential_coordinate_energy": differential,
                        "common_coordinate_iae": common,
                        "controller_engaged": engaged,
                        "maximum_requested_fleet_imbalance_system_pu": 0.0,
                    },
                }
            )

    analysis = r352.classify_formal_records(records)

    assert analysis["classification"] == "DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS"
    assert analysis["local_gate"]["passed"] is True
    assert analysis["joint_upper_is_diagnostic_only"] is True
    assert analysis["training_authorized"] is False


def test_formal_classifier_averages_paired_ratios_not_ratio_of_means() -> None:
    records = []
    scenarios = r352.holdout_scenarios()
    for index, scenario in enumerate(scenarios):
        zero = 100.0 if index == 0 else 1.0
        local = 90.0 if index == 0 else 1.1
        for arm, differential, engaged in (
            ("zero_edge", zero, False),
            ("selected_local", local, True),
            ("joint_upper", local, True),
        ):
            records.append(
                {
                    "identity": "HOLDOUT",
                    "scenario_id": scenario["scenario_id"],
                    "arm": arm,
                    "integrity_valid": True,
                    "physical_guards_pass": True,
                    "information_action_contract_pass": True,
                    "metrics": {
                        "differential_coordinate_energy": differential,
                        "common_coordinate_iae": 1.0,
                        "controller_engaged": engaged,
                        "maximum_requested_fleet_imbalance_system_pu": 0.0,
                    },
                }
            )

    analysis = r352.classify_formal_records(records)

    expected = 1.0 - np.mean([0.9] + [1.1] * 15)
    assert analysis["local_gate"]["paired_mean_differential_improvement_fraction"] == pytest.approx(expected)
    assert analysis["classification"] == "DISTRIBUTED-DETERMINISTIC-NO-HOLDOUT-VALUE"


def test_joint_diagnostic_engagement_cannot_change_local_gate() -> None:
    records = []
    for scenario in r352.holdout_scenarios():
        for arm, differential, engaged in (
            ("zero_edge", 10.0, False),
            ("selected_local", 9.0, True),
            ("joint_upper", 10.0, False),
        ):
            records.append(
                {
                    "identity": "HOLDOUT",
                    "scenario_id": scenario["scenario_id"],
                    "arm": arm,
                    "integrity_valid": True,
                    "physical_guards_pass": True,
                    "information_action_contract_pass": True,
                    "metrics": {
                        "differential_coordinate_energy": differential,
                        "common_coordinate_iae": 1.0,
                        "controller_engaged": engaged,
                        "maximum_requested_fleet_imbalance_system_pu": 0.0,
                    },
                }
            )

    analysis = r352.classify_formal_records(records)

    assert analysis["classification"] == "DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS"
    assert analysis["local_gate"]["passed"] is True
    assert analysis["joint_upper"]["controller_engagement"] is False


def test_joint_diagnostic_guard_failure_cannot_change_local_gate() -> None:
    records = []
    for scenario in r352.holdout_scenarios():
        for arm, differential, physical_pass in (
            ("zero_edge", 10.0, True),
            ("selected_local", 9.0, True),
            ("joint_upper", 10.0, False),
        ):
            records.append(
                {
                    "identity": "HOLDOUT",
                    "scenario_id": scenario["scenario_id"],
                    "arm": arm,
                    "integrity_valid": True,
                    "physical_guards_pass": physical_pass,
                    "information_action_contract_pass": True,
                    "metrics": {
                        "differential_coordinate_energy": differential,
                        "common_coordinate_iae": 1.0,
                        "controller_engaged": arm != "zero_edge",
                        "maximum_requested_fleet_imbalance_system_pu": 0.0,
                    },
                }
            )

    analysis = r352.classify_formal_records(records)

    assert analysis["classification"] == "DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS"
    assert analysis["local_gate"]["passed"] is True
    assert analysis["joint_upper"]["valid"] is False


def test_stage_stop_distinguishes_integrity_from_physical_failure() -> None:
    valid = {
        "integrity_valid": True,
        "information_action_contract_pass": True,
        "physical_guards_pass": True,
    }

    assert r352.classify_stage_stop([valid]) is None
    assert (
        r352.classify_stage_stop([{**valid, "integrity_valid": False}])
        == "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION"
    )
    assert (
        r352.classify_stage_stop([{**valid, "physical_guards_pass": False}])
        == "DISTRIBUTED-DETERMINISTIC-PHYSICAL-GUARD-FAIL"
    )


def test_parser_exposes_only_staged_nontraining_commands() -> None:
    parser = r352.build_parser()
    subparsers = next(
        action for action in parser._actions if action.dest == "command"  # noqa: SLF001
    )

    assert set(subparsers.choices) == {
        "rehearse-development",
        "measure-capacity",
        "execute-development",
        "rehearse-formal",
        "prepare-formal",
        "execute-formal",
    }
    assert all("train" not in name for name in subparsers.choices)
