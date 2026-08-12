"""Pure R367 deterministic-efficacy and conditional-headroom gate.

The module contains no ANDES import and no learning code.  It freezes the
finite development contract, summarises already executed physical traces, and
classifies only a complete scenario-by-arm bank.  The formal WSL runner owns
simulation and provenance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.per_vsg_md import local_neighbour_md_candidates


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "scenario_id": "strong_pq_0_negative",
        "location": "PQ_0",
        "sign": "negative",
        "delta_u": {"PQ_0": -1.0088},
    },
    {
        "scenario_id": "strong_pq_0_positive",
        "location": "PQ_0",
        "sign": "positive",
        "delta_u": {"PQ_0": 1.0901},
    },
    {
        "scenario_id": "strong_pq_1_negative",
        "location": "PQ_1",
        "sign": "negative",
        "delta_u": {"PQ_1": -1.0533},
    },
    {
        "scenario_id": "strong_pq_1_positive",
        "location": "PQ_1",
        "sign": "positive",
        "delta_u": {"PQ_1": 1.1468},
    },
    {
        "scenario_id": "strong_pq_bus14_negative",
        "location": "PQ_Bus14",
        "sign": "negative",
        "delta_u": {"PQ_Bus14": -1.1266},
    },
    {
        "scenario_id": "strong_pq_bus14_positive",
        "location": "PQ_Bus14",
        "sign": "positive",
        "delta_u": {"PQ_Bus14": 1.0622},
    },
    {
        "scenario_id": "strong_pq_bus15_negative",
        "location": "PQ_Bus15",
        "sign": "negative",
        "delta_u": {"PQ_Bus15": -1.0191},
    },
    {
        "scenario_id": "strong_pq_bus15_positive",
        "location": "PQ_Bus15",
        "sign": "positive",
        "delta_u": {"PQ_Bus15": 1.0497},
    },
)


def build_contract() -> dict[str, Any]:
    """Return the immutable JSON-compatible R367 scientific contract."""

    candidate_ids = [row.name for row in local_neighbour_md_candidates()]
    return {
        "schema_version": 1,
        "round": "R367",
        "question": "Q-0103",
        "steps": 30,
        "dt_seconds": 0.2,
        "seed": 42,
        "physical_nominal_frequency_hz": 60.0,
        "control_nominal_frequency_hz": 50.0,
        "baseline_m0": [200.0] * 4,
        "baseline_d0": [70.0, 90.0, 130.0, 150.0],
        "action_bounds": [-1.0, 1.0],
        "action_slew_limit": 0.25,
        "decoder": {
            "delta_m_negative": -200.0,
            "delta_m_positive": 600.0,
            "delta_d_negative": -200.0,
            "delta_d_positive": 600.0,
            "m_lower_clamp": 20.0,
            "d_lower_clamp": 10.0,
            "mapping_atol": 1.0e-5,
        },
        "scenarios": [dict(row) for row in SCENARIOS],
        "candidate_arm_ids": candidate_ids,
        "arm_ids": ["zero", *candidate_ids],
        "thresholds": {
            "deterministic_minimum_improvement": 0.10,
            "oracle_minimum_headroom": 0.05,
            "maximum_common_frequency_harm": 0.05,
            "maximum_action_saturation_fraction": 0.05,
            "nonconstant_action_variation_floor": 1.0e-6,
            "minimum_distinct_oracle_candidates": 2,
        },
        "scenario_source": {
            "role": "read_only_design_input_only",
            "path": "results/r274_prospective_active_power_authority/formal_bank.json",
            "selection": "all_and_only_severity_strong_four_locations_cross_two_signs",
            "source_sha256": (
                "9d028e8a0e990fbea6585c674b471dba4d41ea27c1e0b7ecb5d8389092b31f44"
            ),
            "old_measurements_reused": False,
        },
        "oracle_role": "non_deployable_outcome_selector",
        "reward_used_for_gate": False,
        "training_authorized": False,
    }


def _finite_array(value: object, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite with shape {shape}")
    return array


def summarise_record(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any] | None = None,
    expected_steps: int | None = None,
) -> dict[str, Any]:
    """Summarise one completed physical trajectory using frozen endpoints."""

    spec = build_contract() if contract is None else contract
    steps = record.get("steps")
    required_steps = int(spec["steps"] if expected_steps is None else expected_steps)
    if not isinstance(steps, list) or len(steps) != required_steps:
        raise ValueError("record must contain the expected number of steps")

    frequencies = np.stack(
        [
            _finite_array(row.get("freq_hz_physical"), (4,), "frequency")
            for row in steps
        ]
    )
    powers = np.stack(
        [_finite_array(row.get("P_es"), (4,), "active power") for row in steps]
    )
    actions = np.stack(
        [_finite_array(row.get("action_norm"), (4, 2), "action") for row in steps]
    )
    delta_m = np.stack(
        [_finite_array(row.get("delta_M"), (4,), "delta M") for row in steps]
    )
    delta_d = np.stack(
        [_finite_array(row.get("delta_D"), (4,), "delta D") for row in steps]
    )
    actual_m = np.stack(
        [_finite_array(row.get("M_es"), (4,), "executed M") for row in steps]
    )
    actual_d = np.stack(
        [_finite_array(row.get("D_es"), (4,), "executed D") for row in steps]
    )
    identity = record.get("identity")
    if not isinstance(identity, Mapping):
        raise ValueError("record must contain actuator identity")
    baseline_m = _finite_array(identity.get("baseline_m0"), (4,), "baseline M")
    baseline_d = _finite_array(identity.get("baseline_d0"), (4,), "baseline D")
    decoder = spec["decoder"]
    expected_delta_m = np.where(
        actions[:, :, 0] >= 0.0,
        actions[:, :, 0] * float(decoder["delta_m_positive"]),
        actions[:, :, 0] * -float(decoder["delta_m_negative"]),
    )
    expected_delta_d = np.where(
        actions[:, :, 1] >= 0.0,
        actions[:, :, 1] * float(decoder["delta_d_positive"]),
        actions[:, :, 1] * -float(decoder["delta_d_negative"]),
    )
    expected_m = np.maximum(
        baseline_m[None, :] + expected_delta_m,
        float(decoder["m_lower_clamp"]),
    )
    expected_d = np.maximum(
        baseline_d[None, :] + expected_delta_d,
        float(decoder["d_lower_clamp"]),
    )
    mapping_atol = float(decoder["mapping_atol"])
    mapping_pass = bool(
        np.allclose(delta_m, expected_delta_m, rtol=0.0, atol=mapping_atol)
        and np.allclose(delta_d, expected_delta_d, rtol=0.0, atol=mapping_atol)
        and np.allclose(actual_m, expected_m, rtol=0.0, atol=mapping_atol)
        and np.allclose(actual_d, expected_d, rtol=0.0, atol=mapping_atol)
    )
    dt = float(spec["dt_seconds"])
    frequency_centered = frequencies - np.mean(frequencies, axis=1, keepdims=True)
    power_centered = powers - np.mean(powers, axis=1, keepdims=True)
    common_error = np.abs(
        np.mean(frequencies, axis=1)
        - float(spec["physical_nominal_frequency_hz"])
    )
    boundary_differences = np.diff(
        np.concatenate([np.zeros((1, 4, 2)), actions], axis=0),
        axis=0,
    )
    lower, upper = (float(value) for value in spec["action_bounds"])
    tolerance = 1.0e-9
    saturation = np.logical_or(
        actions <= lower + tolerance,
        actions >= upper - tolerance,
    )
    return {
        "scenario_id": str(record.get("scenario_id", "")),
        "arm_id": str(record.get("arm_id", "")),
        "completed": bool(record.get("completed") is True and len(steps) == required_steps),
        "tds_failed": bool(record.get("tds_failed", False)),
        "differential_frequency_energy_hz2_s": float(
            np.sum(np.mean(frequency_centered**2, axis=1)) * dt
        ),
        "differential_power_energy_pu2_s": float(
            np.sum(np.mean(power_centered**2, axis=1)) * dt
        ),
        "common_frequency_iae_hz_s": float(np.sum(common_error) * dt),
        "action_boundary_aware_total_variation": float(
            np.sum(np.mean(np.abs(boundary_differences), axis=(1, 2)))
        ),
        "action_saturation_fraction": float(np.mean(saturation)),
        "action_bound_violation": bool(
            np.any(actions < lower - tolerance) or np.any(actions > upper + tolerance)
        ),
        "action_slew_violation": bool(
            np.any(
                np.abs(boundary_differences)
                > float(spec["action_slew_limit"]) + tolerance
            )
        ),
        "maximum_action_row_dispersion": float(
            np.max(np.ptp(actions, axis=1))
        ),
        "actuator_mapping_pass": mapping_pass,
    }


def _summary_is_valid(row: Mapping[str, Any]) -> bool:
    numeric = (
        "differential_frequency_energy_hz2_s",
        "differential_power_energy_pu2_s",
        "common_frequency_iae_hz_s",
        "action_boundary_aware_total_variation",
        "action_saturation_fraction",
        "maximum_action_row_dispersion",
    )
    try:
        values = np.asarray([float(row[key]) for key in numeric], dtype=float)
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        row.get("completed") is True
        and row.get("tds_failed") is False
        and row.get("actuator_mapping_pass") is True
        and np.all(np.isfinite(values))
        and np.all(values >= 0.0)
        and 0.0 <= float(row["action_saturation_fraction"]) <= 1.0
    )


def _arm_guard(
    arm_rows: Sequence[Mapping[str, Any]],
    zero_by_scenario: Mapping[str, Mapping[str, Any]],
    *,
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    common = sum(float(row["common_frequency_iae_hz_s"]) for row in arm_rows)
    zero_common = sum(
        float(zero_by_scenario[str(row["scenario_id"])]["common_frequency_iae_hz_s"])
        for row in arm_rows
    )
    common_limit = (1.0 + float(thresholds["maximum_common_frequency_harm"])) * zero_common
    checks = {
        "complete_and_no_failure": all(_summary_is_valid(row) for row in arm_rows),
        "common_frequency_no_harm": common <= common_limit + 1.0e-15,
        "saturation_budget": all(
            float(row["action_saturation_fraction"])
            <= float(thresholds["maximum_action_saturation_fraction"]) + 1.0e-15
            for row in arm_rows
        ),
        "zero_bound_violations": not any(
            bool(row.get("action_bound_violation", True)) for row in arm_rows
        ),
        "zero_slew_violations": not any(
            bool(row.get("action_slew_violation", True)) for row in arm_rows
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "aggregate_primary": sum(
            float(row["differential_frequency_energy_hz2_s"])
            for row in arm_rows
        ),
        "aggregate_secondary": sum(
            float(row["differential_power_energy_pu2_s"]) for row in arm_rows
        ),
        "aggregate_common_frequency_iae_hz_s": common,
        "aggregate_common_frequency_limit_hz_s": common_limit,
    }


def classify_summaries(
    summaries: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the prospective R367 deterministic and oracle decision tree."""

    spec = build_contract() if contract is None else contract
    expected_scenarios = [str(row["scenario_id"]) for row in spec["scenarios"]]
    expected_arms = [str(value) for value in spec["arm_ids"]]
    by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicates = False
    for row in summaries:
        key = (str(row.get("scenario_id", "")), str(row.get("arm_id", "")))
        if key in by_key:
            duplicates = True
        by_key[key] = row
    expected_keys = {
        (scenario_id, arm_id)
        for scenario_id in expected_scenarios
        for arm_id in expected_arms
    }
    complete_bank = not duplicates and set(by_key) == expected_keys
    valid_rows = complete_bank and all(_summary_is_valid(row) for row in by_key.values())
    checks = {
        "complete_bank": complete_bank,
        "all_rows_valid": bool(valid_rows),
        "reward_unused": spec.get("reward_used_for_gate") is False,
        "training_forbidden": spec.get("training_authorized") is False,
    }
    if not all(checks.values()):
        return {
            "schema_version": 1,
            "round": spec["round"],
            "question": spec["question"],
            "classification": "ANALYSIS-INVALID",
            "checks": checks,
            "selected_deterministic_arm": None,
            "training_authorized": False,
        }

    zero_by_scenario = {
        scenario_id: by_key[(scenario_id, "zero")]
        for scenario_id in expected_scenarios
    }
    zero_primary = sum(
        float(row["differential_frequency_energy_hz2_s"])
        for row in zero_by_scenario.values()
    )
    if zero_primary <= 0.0:
        checks["positive_zero_primary"] = False
        return {
            "schema_version": 1,
            "round": spec["round"],
            "question": spec["question"],
            "classification": "ANALYSIS-INVALID",
            "checks": checks,
            "selected_deterministic_arm": None,
            "training_authorized": False,
        }
    checks["positive_zero_primary"] = True

    thresholds = spec["thresholds"]
    arm_guards: dict[str, dict[str, Any]] = {}
    for arm_id in spec["candidate_arm_ids"]:
        rows = [by_key[(scenario_id, str(arm_id))] for scenario_id in expected_scenarios]
        arm_guards[str(arm_id)] = _arm_guard(
            rows,
            zero_by_scenario,
            thresholds=thresholds,
        )
    eligible = [
        (details["aggregate_primary"], details["aggregate_secondary"], arm_id)
        for arm_id, details in arm_guards.items()
        if details["passed"]
    ]
    eligible.sort()
    selected_arm = eligible[0][2] if eligible else None
    selected_primary = float(eligible[0][0]) if eligible else float("nan")
    improvement = (
        (zero_primary - selected_primary) / zero_primary if eligible else float("nan")
    )
    deterministic_pass = bool(
        eligible
        and improvement
        >= float(thresholds["deterministic_minimum_improvement"]) - 1.0e-15
    )
    deterministic_gate = {
        "passed": deterministic_pass,
        "zero_aggregate_primary": zero_primary,
        "selected_aggregate_primary": selected_primary if eligible else None,
        "aggregate_improvement_fraction": improvement if eligible else None,
        "minimum_improvement_fraction": float(
            thresholds["deterministic_minimum_improvement"]
        ),
        "candidate_guards": arm_guards,
    }
    if not deterministic_pass:
        return {
            "schema_version": 1,
            "round": spec["round"],
            "question": spec["question"],
            "classification": "STOP-DETERMINISTIC-NO-EFFICACY",
            "checks": checks,
            "selected_deterministic_arm": None,
            "deterministic_gate": deterministic_gate,
            "training_authorized": False,
            "claim_scope": "finite development bank only",
        }

    selected_rows: list[dict[str, Any]] = []
    for scenario_id in expected_scenarios:
        zero_row = zero_by_scenario[scenario_id]
        scenario_eligible: list[tuple[float, float, str, Mapping[str, Any]]] = []
        for arm_id in spec["candidate_arm_ids"]:
            row = by_key[(scenario_id, str(arm_id))]
            common_limit = (
                1.0 + float(thresholds["maximum_common_frequency_harm"])
            ) * float(zero_row["common_frequency_iae_hz_s"])
            valid = bool(
                _summary_is_valid(row)
                and float(row["common_frequency_iae_hz_s"])
                <= common_limit + 1.0e-15
                and float(row["action_saturation_fraction"])
                <= float(thresholds["maximum_action_saturation_fraction"])
                + 1.0e-15
                and row.get("action_bound_violation") is False
                and row.get("action_slew_violation") is False
            )
            if valid:
                scenario_eligible.append(
                    (
                        float(row["differential_frequency_energy_hz2_s"]),
                        float(row["differential_power_energy_pu2_s"]),
                        str(arm_id),
                        row,
                    )
                )
        if not scenario_eligible:
            return {
                "schema_version": 1,
                "round": spec["round"],
                "question": spec["question"],
                "classification": "ANALYSIS-INVALID",
                "checks": {**checks, "oracle_candidate_each_scenario": False},
                "selected_deterministic_arm": selected_arm,
                "deterministic_gate": deterministic_gate,
                "training_authorized": False,
            }
        scenario_eligible.sort(key=lambda value: value[:3])
        primary, secondary, arm_id, row = scenario_eligible[0]
        selected_rows.append(
            {
                "scenario_id": scenario_id,
                "arm_id": arm_id,
                "primary": primary,
                "secondary": secondary,
                "action_boundary_aware_total_variation": float(
                    row["action_boundary_aware_total_variation"]
                ),
            }
        )

    oracle_primary = sum(float(row["primary"]) for row in selected_rows)
    headroom = (selected_primary - oracle_primary) / selected_primary
    distinct_count = len({str(row["arm_id"]) for row in selected_rows})
    headroom_pass = headroom >= float(thresholds["oracle_minimum_headroom"]) - 1.0e-15
    nonconstant_pass = all(
        float(row["action_boundary_aware_total_variation"])
        > float(thresholds["nonconstant_action_variation_floor"])
        for row in selected_rows
    )
    distinct_pass = distinct_count >= int(
        thresholds["minimum_distinct_oracle_candidates"]
    )
    oracle_pass = bool(headroom_pass and nonconstant_pass and distinct_pass)
    oracle_gate = {
        "passed": oracle_pass,
        "role": str(spec["oracle_role"]),
        "selected_rows": selected_rows,
        "aggregate_primary": oracle_primary,
        "headroom_fraction": headroom,
        "minimum_headroom_fraction": float(thresholds["oracle_minimum_headroom"]),
        "headroom_pass": bool(headroom_pass),
        "nonconstant_action_pass": bool(nonconstant_pass),
        "distinct_selected_candidates": distinct_count,
        "distinct_candidate_pass": bool(distinct_pass),
    }
    return {
        "schema_version": 1,
        "round": spec["round"],
        "question": spec["question"],
        "classification": (
            "DETERMINISTIC-AND-HEADROOM-PASS"
            if oracle_pass
            else "STOP-NO-CONDITIONAL-HEADROOM"
        ),
        "checks": checks,
        "selected_deterministic_arm": selected_arm,
        "deterministic_gate": deterministic_gate,
        "oracle_gate": oracle_gate,
        "oracle_deployable": False,
        "training_authorized": False,
        "claim_scope": "finite deterministic development bank only",
    }


__all__ = ["build_contract", "classify_summaries", "summarise_record"]
