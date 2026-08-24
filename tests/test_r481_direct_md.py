"""Targeted tests for the R481 fresh-holdout direct-M/D successor round."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.r481_fresh_profiles import (
    GENERATOR_SEED,
    VIEWED_ROWS,
    build_contract,
    build_fresh_rows,
    phase1a_gate,
)

# ruff: noqa: E402
import importlib.util

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "r481_runner", _ROOT / "scripts" / "run_r481_direct_md.py"
)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def test_fresh_rows_shape_and_split() -> None:
    rows = build_fresh_rows()
    assert len(rows) == 6
    for row in rows:
        assert len(row["baseline_m0"]) == 4
        assert len(row["baseline_d0"]) == 4
        assert len(set(row["baseline_m0"])) == 4
        assert len(set(row["baseline_d0"])) == 4
        assert 0.0 < row["load14"] <= 3.0
        assert 0.0 <= row["load15"] <= 1.0
        assert row["location"] in {"PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"}


def test_fresh_rows_exclude_every_viewed_row() -> None:
    rows = build_fresh_rows()
    viewed = [
        {
            "baseline_m0": tuple(row["baseline_m0"]),
            "baseline_d0": tuple(row["baseline_d0"]),
            "load14": float(row["load14"]),
            "load15": float(row["load15"]),
            "probe": float(row["probe"]),
            "location": str(row["location"]),
            "localized": float(row["localized"]),
        }
        for row in VIEWED_ROWS
    ]
    for row in rows:
        for old in viewed:
            assert (
                tuple(row["baseline_m0"]),
                tuple(row["baseline_d0"]),
                row["load14"],
                row["load15"],
                row["probe"],
                row["location"],
                row["localized"],
            ) != (
                old["baseline_m0"],
                old["baseline_d0"],
                old["load14"],
                old["load15"],
                old["probe"],
                old["location"],
                old["localized"],
            ), f"fresh row collides with a viewed row: {row}"
            assert (row["probe"], row["location"], row["localized"]) != (
                old["probe"],
                old["location"],
                old["localized"],
            ), f"fresh scenario triple collides with a viewed row: {row}"


def test_fresh_rows_deterministic_and_distinct() -> None:
    first = build_fresh_rows(seed=GENERATOR_SEED)
    second = build_fresh_rows(seed=GENERATOR_SEED)
    assert first == second
    tuples = [json.dumps(row, sort_keys=True) for row in first]
    assert len(set(tuples)) == 6


def test_contract_shape_matches_r399_family() -> None:
    contract = build_contract()
    assert contract["round"] == "R481"
    assert contract["steps"] == 30
    assert contract["dt_seconds"] == 0.2
    assert len(contract["profiles"]) == 6
    assert sum(row["split"] == "development" for row in contract["profiles"]) == 2
    assert sum(row["split"] == "evaluation" for row in contract["profiles"]) == 4
    assert all(len(row["scenarios"]) == 6 for row in contract["profiles"])
    assert len(contract["arm_ids"]) == 10
    assert contract["arm_ids"][0] == "zero"
    assert contract["reward_used_for_gate"] is False
    assert contract["training_authorized"] is False
    job_count = sum(
        len(row["scenarios"]) for row in contract["profiles"]
    ) * len(contract["arm_ids"])
    assert job_count == 360


def test_classify_bank_accepts_fresh_contract() -> None:
    from andes_rl_kundur.evaluation.md_decoupling_headroom import classify_bank

    contract = build_contract()
    result = classify_bank([], contract=contract)
    assert result["classification"] == "ANALYSIS-INVALID"
    assert result["checks"]["complete_bank"] is False


def _summary(passed: bool) -> dict:
    return {
        "valid": passed,
        "actuator_mapping_pass": passed,
        "action_bound_violation": not passed,
        "action_slew_violation": not passed,
        "off_diagonal_response_energy": 0.4,
        "disturbance_differential_energy": 0.3,
        "common_frequency_iae_hz_s": 0.5,
        "worst_unit_peak_hz": 0.05,
        "worst_rocof_hz_s": 0.2,
        "action_saturation_fraction": 0.01 if passed else 0.5,
        "minimum_record_total_variation": 1e-3 if passed else 0.0,
        "minimum_record_action_row_dispersion": 1e-3 if passed else 0.0,
    }


def _zero_summary() -> dict:
    return {
        "valid": True,
        "actuator_mapping_pass": True,
        "action_bound_violation": False,
        "action_slew_violation": False,
        "off_diagonal_response_energy": 1.0,
        "disturbance_differential_energy": 1.0,
        "common_frequency_iae_hz_s": 0.5,
        "worst_unit_peak_hz": 0.05,
        "worst_rocof_hz_s": 0.2,
        "action_saturation_fraction": 0.0,
        "minimum_record_total_variation": 1e-3,
        "minimum_record_action_row_dispersion": 1e-3,
    }


def test_phase1a_gate_requires_four_of_four() -> None:
    contract = build_contract()
    eval_ids = [
        row["profile_id"] for row in contract["profiles"] if row["split"] == "evaluation"
    ]
    summaries = []
    for profile_id in eval_ids:
        summaries.append(
            {
                "profile_id": profile_id,
                "arm_id": "local_neighbour_md_km2_kd2",
                **_summary(passed=True),
            }
        )
        summaries.append(
            {"profile_id": profile_id, "arm_id": "zero", **_zero_summary()}
        )
    gate = phase1a_gate(
        summaries,
        contract=contract,
        selected_arm="local_neighbour_md_km2_kd2",
    )
    assert gate["passed_4_of_4"] is True
    assert gate["passed_count"] == 4

    summaries = []
    for index, profile_id in enumerate(eval_ids):
        passed = index != 0
        summaries.append(
            {
                "profile_id": profile_id,
                "arm_id": "local_neighbour_md_km2_kd2",
                **_summary(passed=passed),
            }
        )
        summaries.append(
            {"profile_id": profile_id, "arm_id": "zero", **_zero_summary()}
        )
    gate = phase1a_gate(
        summaries,
        contract=contract,
        selected_arm="local_neighbour_md_km2_kd2",
    )
    assert gate["passed_4_of_4"] is False
    assert gate["passed_count"] == 3
    assert gate["one_to_three_cannot_open"] is True


def test_runner_job_shapes() -> None:
    contract = build_contract()
    assert len(runner._formal_jobs(contract)) == 360
    assert len(runner._capacity_jobs(contract)) == 8
    rehearsal = runner._rehearsal_jobs(contract)
    assert len(rehearsal) == 6
    assert all(job["arm_id"] == "zero" for job in rehearsal)
