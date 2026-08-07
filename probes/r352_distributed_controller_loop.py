"""Pure prospective selection and holdout classification for R352.

This module reads no repository artifact and executes no simulator. Callers
must supply the frozen scenarios, candidates, and thresholds from the sealed
execution contract.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


INVALID_CLASSIFICATION = "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION"
PHYSICAL_FAIL_CLASSIFICATION = "DISTRIBUTED-DETERMINISTIC-PHYSICAL-GUARD-FAIL"


def classify_stage_stop(records: list[dict[str, Any]]) -> str | None:
    """Return the prospective terminal stop classification for one arm stage."""

    if any(
        row.get("integrity_valid") is not True
        or row.get("information_action_contract_pass") is not True
        for row in records
    ):
        return INVALID_CLASSIFICATION
    if any(row.get("physical_guards_pass") is not True for row in records):
        return PHYSICAL_FAIL_CLASSIFICATION
    return None


def select_development_candidate(
    records: list[dict[str, Any]],
    *,
    scenarios: list[str],
    candidates: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Apply the prospective selection rule without accepting holdout rows."""

    if any(row.get("identity") != "DEVELOPMENT" for row in records):
        raise ValueError("development selection cannot inspect a holdout record")
    expected_count = len(scenarios) * (1 + len(candidates))
    if len(records) != expected_count:
        return {
            "classification": "INVALID-DEVELOPMENT-EXECUTION",
            "reason": "record-count",
            "selected": None,
            "holdout_records_inspected": False,
        }
    zero_by_scenario = {
        str(row["scenario_id"]): row for row in records if row.get("arm") == "zero_edge"
    }
    if set(zero_by_scenario) != set(scenarios):
        return {
            "classification": "INVALID-DEVELOPMENT-EXECUTION",
            "reason": "zero-inventory",
            "selected": None,
            "holdout_records_inspected": False,
        }

    survivors: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    imbalance_limit = thresholds[
        "requested_fleet_imbalance_absolute_maximum_system_pu"
    ]
    common_ratio_limit = 1.0 + thresholds[
        "maximum_single_scenario_common_worsening_fraction"
    ]
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        rows = {
            str(row["scenario_id"]): row
            for row in records
            if row.get("arm") == "local_candidate"
            and row.get("candidate_id") == candidate_id
        }
        if set(rows) != set(scenarios):
            rejected.append({"candidate_id": candidate_id, "reason": "inventory"})
            continue
        differential_ratios: list[float] = []
        common_ratios: list[float] = []
        valid = True
        for scenario_id in scenarios:
            zero = zero_by_scenario[scenario_id]
            row = rows[scenario_id]
            zero_metrics = zero["metrics"]
            metrics = row["metrics"]
            guards = (
                zero.get("integrity_valid") is True
                and zero.get("physical_guards_pass") is True
                and zero.get("information_action_contract_pass") is True
                and row.get("integrity_valid") is True
                and row.get("physical_guards_pass") is True
                and row.get("information_action_contract_pass") is True
                and metrics.get("controller_engaged") is True
                and float(metrics["maximum_requested_fleet_imbalance_system_pu"])
                <= imbalance_limit
            )
            if not guards:
                valid = False
                break
            differential_ratio = float(metrics["differential_coordinate_energy"]) / float(
                zero_metrics["differential_coordinate_energy"]
            )
            common_ratio = float(metrics["common_coordinate_iae"]) / float(
                zero_metrics["common_coordinate_iae"]
            )
            if not (
                math.isfinite(differential_ratio)
                and differential_ratio > 0.0
                and math.isfinite(common_ratio)
                and common_ratio > 0.0
                and common_ratio <= common_ratio_limit
            ):
                valid = False
                break
            differential_ratios.append(differential_ratio)
            common_ratios.append(common_ratio)
        if not valid:
            rejected.append({"candidate_id": candidate_id, "reason": "guard"})
            continue
        survivors.append(
            {
                **candidate,
                "geometric_mean_differential_ratio": float(
                    math.exp(np.mean(np.log(differential_ratios)))
                ),
                "maximum_common_ratio": float(max(common_ratios)),
            }
        )
    survivors.sort(
        key=lambda row: (
            float(row["geometric_mean_differential_ratio"]),
            float(row["frequency_difference_gain_per_hz"]),
            float(row["rocof_difference_gain_s_per_hz"]),
        )
    )
    return {
        "classification": (
            "DEVELOPMENT-CANDIDATE-SELECTED" if survivors else "NO-DEVELOPMENT-CANDIDATE"
        ),
        "selected": survivors[0] if survivors else None,
        "survivors": survivors,
        "rejected": rejected,
        "record_count": len(records),
        "holdout_records_inspected": False,
    }


def classify_formal_records(
    records: list[dict[str, Any]],
    *,
    expected_scenarios: set[str],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Apply the frozen local-over-zero holdout decision tree."""

    arms_by_scenario: dict[str, dict[str, dict[str, Any]]] = {}
    expected_count = len(expected_scenarios) * 3
    if len(records) != expected_count or any(
        row.get("identity") != "HOLDOUT" for row in records
    ):
        return {
            "classification": "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION",
            "local_gate": {"passed": False, "complete_paired_inventory": False},
            "training_authorized": False,
        }
    for row in records:
        scenario_id = str(row.get("scenario_id"))
        arm = str(row.get("arm"))
        if scenario_id not in expected_scenarios or arm not in {
            "zero_edge",
            "selected_local",
            "joint_upper",
        }:
            return {
                "classification": "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION",
                "local_gate": {"passed": False, "complete_paired_inventory": False},
                "training_authorized": False,
            }
        bucket = arms_by_scenario.setdefault(scenario_id, {})
        if arm in bucket:
            return {
                "classification": "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION",
                "local_gate": {"passed": False, "complete_paired_inventory": False},
                "training_authorized": False,
            }
        bucket[arm] = row
    complete = set(arms_by_scenario) == expected_scenarios and all(
        set(arms) == {"zero_edge", "selected_local", "joint_upper"}
        for arms in arms_by_scenario.values()
    )
    primary_records = [
        row for row in records if row.get("arm") in {"zero_edge", "selected_local"}
    ]
    integrity = complete and all(
        row.get("integrity_valid") is True
        and row.get("information_action_contract_pass") is True
        for row in primary_records
    )
    if not integrity:
        return {
            "classification": "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION",
            "local_gate": {"passed": False, "complete_paired_inventory": complete},
            "training_authorized": False,
        }
    if any(row.get("physical_guards_pass") is not True for row in primary_records):
        return {
            "classification": "DISTRIBUTED-DETERMINISTIC-PHYSICAL-GUARD-FAIL",
            "local_gate": {"passed": False, "complete_paired_inventory": True},
            "training_authorized": False,
        }

    differential_ratios: list[float] = []
    common_ratios: list[float] = []
    joint_differential_ratios: list[float] = []
    zero_differential: list[float] = []
    local_differential: list[float] = []
    valid_metrics = True
    local_engagement = True
    joint_engagement = True
    joint_valid = True
    imbalance_limit = thresholds[
        "requested_fleet_imbalance_absolute_maximum_system_pu"
    ]
    for arms in arms_by_scenario.values():
        zero = arms["zero_edge"]["metrics"]
        local = arms["selected_local"]["metrics"]
        joint = arms["joint_upper"]["metrics"]
        primary_values = [
            float(row[name])
            for row in (zero, local)
            for name in ("differential_coordinate_energy", "common_coordinate_iae")
        ]
        if not all(math.isfinite(value) and value >= 0.0 for value in primary_values):
            valid_metrics = False
            break
        zero_diff = float(zero["differential_coordinate_energy"])
        zero_common = float(zero["common_coordinate_iae"])
        if zero_diff <= 0.0 or zero_common <= 0.0:
            valid_metrics = False
            break
        zero_differential.append(zero_diff)
        local_differential.append(float(local["differential_coordinate_energy"]))
        differential_ratios.append(float(local["differential_coordinate_energy"]) / zero_diff)
        common_ratios.append(float(local["common_coordinate_iae"]) / zero_common)
        local_engagement = local_engagement and local.get("controller_engaged") is True
        joint_engagement = joint_engagement and joint.get("controller_engaged") is True
        if float(local["maximum_requested_fleet_imbalance_system_pu"]) > imbalance_limit:
            valid_metrics = False
        joint_valid = joint_valid and bool(
            joint.get("integrity_valid") is True
            and joint.get("information_action_contract_pass") is True
            and joint.get("physical_guards_pass") is True
            and float(joint["maximum_requested_fleet_imbalance_system_pu"])
            <= imbalance_limit
        )
        joint_values = [
            float(joint[name])
            for name in ("differential_coordinate_energy", "common_coordinate_iae")
        ]
        joint_metrics_valid = all(
            math.isfinite(value) and value >= 0.0 for value in joint_values
        )
        joint_valid = joint_valid and joint_metrics_valid
        if joint_metrics_valid:
            joint_differential_ratios.append(joint_values[0] / zero_diff)
    if not valid_metrics:
        return {
            "classification": "INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION",
            "local_gate": {"passed": False, "metric_integrity": False},
            "training_authorized": False,
        }
    mean_improvement = 1.0 - float(np.mean(differential_ratios))
    material = mean_improvement >= thresholds[
        "minimum_mean_differential_improvement_fraction"
    ]
    differential_no_harm = max(differential_ratios) <= 1.0 + thresholds[
        "maximum_single_scenario_differential_worsening_fraction"
    ]
    common_no_harm = max(common_ratios) <= 1.0 + thresholds[
        "maximum_single_scenario_common_worsening_fraction"
    ]
    passed = local_engagement and material and differential_no_harm and common_no_harm
    return {
        "classification": (
            "DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS"
            if passed
            else "DISTRIBUTED-DETERMINISTIC-NO-HOLDOUT-VALUE"
        ),
        "local_gate": {
            "passed": passed,
            "complete_paired_inventory": True,
            "controller_engagement": local_engagement,
            "paired_mean_differential_improvement_fraction": mean_improvement,
            "maximum_differential_ratio": float(max(differential_ratios)),
            "maximum_common_ratio": float(max(common_ratios)),
            "minimum_mean_improvement_pass": material,
            "differential_no_harm_pass": differential_no_harm,
            "common_no_harm_pass": common_no_harm,
        },
        "joint_upper": {
            "mean_differential_ratio_over_zero": (
                float(np.mean(joint_differential_ratios))
                if len(joint_differential_ratios) == len(expected_scenarios)
                else None
            ),
            "controller_engagement": joint_engagement,
            "valid": joint_valid,
            "diagnostic_only": True,
        },
        "joint_upper_is_diagnostic_only": True,
        "training_authorized": False,
    }
