from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r452_m5_all_candidate_pareto_test",
    ROOT / "scripts/run_r452_m5_all_candidate_pareto.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _static() -> dict[str, float | bool]:
    return {
        "disturbance_differential_energy": 1.0,
        "off_diagonal_response_energy": 1.0,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
        "action_saturation_fraction": 0.0,
        "valid": True,
    }


def test_candidate_generator_matches_registered_sequence_and_duplicates() -> None:
    rows = MODULE.candidates()
    assert Counter(row["k"] for row in rows) == {2: 25, 3: 125, 5: 200}
    assert [row["global_index"] for row in rows] == list(range(350))
    assert len({row["candidate_id"] for row in rows}) == 350
    assert MODULE.candidate_sequence_sha256() == MODULE.EXPECTED_CANDIDATE_SHA256
    k5 = [
        tuple(tuple(pair) for pair in row["schedule"])
        for row in rows
        if row["k"] == 5
    ]
    assert len(set(k5)) == 192
    assert len(k5) - len(set(k5)) == 8


def test_candidate_sequence_matches_the_real_r439_generator_path() -> None:
    assert MODULE.capture_parent_candidate_sequence() == [
        row["schedule"] for row in MODULE.candidates()
    ]


def test_chunk_partition_and_shards_cover_every_registered_row_once() -> None:
    chunks = MODULE.candidate_chunks()
    assert len(chunks) == 16
    assert sorted(len(chunk) for chunk in chunks) == [21, 21] + [22] * 14
    assert [
        row["global_index"] for chunk in chunks for row in chunk
    ] == list(range(350))
    shard_ids = MODULE.expected_shard_ids()
    assert len(shard_ids) == 68
    assert len(set(shard_ids)) == 68
    assert sum(value.startswith("candidate|") for value in shard_ids) == 64
    assert sum(value.startswith("static|") for value in shard_ids) == 4


def test_joint_endpoint_and_no_harm_boundaries_are_inclusive() -> None:
    static = _static()
    candidate = {
        **static,
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "common_frequency_iae_hz_s": 1.03,
        "worst_unit_peak_hz": 1.03,
        "worst_rocof_hz_s": 1.03,
        "action_rms": 1.10,
        "action_total_variation": 1.10,
        "action_saturation_fraction": 0.05,
    }
    guard = MODULE.candidate_guard(candidate, static)
    assert guard["joint_endpoint_eligible"]
    assert guard["common_clean"]
    assert guard["action_clean"]
    assert guard["saturation_pass"]
    assert guard["joint_guard_feasible"]


def test_one_endpoint_or_one_guard_failure_blocks_joint_feasibility() -> None:
    static = _static()
    one_endpoint = {
        **static,
        "disturbance_differential_energy": 0.94,
        "off_diagonal_response_energy": 0.96,
    }
    assert not MODULE.candidate_guard(one_endpoint, static)[
        "joint_endpoint_eligible"
    ]
    excessive_action = {
        **static,
        "disturbance_differential_energy": 0.94,
        "off_diagonal_response_energy": 0.94,
        "action_rms": 1.100001,
    }
    guard = MODULE.candidate_guard(excessive_action, static)
    assert guard["joint_endpoint_eligible"]
    assert not guard["action_clean"]
    assert not guard["joint_guard_feasible"]


def test_pareto_retains_objective_ties_and_generated_ids() -> None:
    tied = [
        {"id": "a", "objectives": [1.0, 1.0, 1.0, 1.0]},
        {"id": "b", "objectives": [1.0, 1.0, 1.0, 1.0]},
    ]
    assert [row["id"] for row in MODULE.nondominated(tied)] == ["a", "b"]
    rows = tied + [
        {"id": "c", "objectives": [0.9, 1.0, 1.0, 1.0]},
        {"id": "d", "objectives": [0.8, 1.2, 0.8, 1.2]},
    ]
    assert [row["id"] for row in MODULE.nondominated(rows)] == ["c", "d"]


def test_schedule_label_is_syntactic_only() -> None:
    assert not MODULE.genuinely_varying([[3.0, 3.0], [3.0, 3.0]])
    assert MODULE.genuinely_varying([[3.0, 3.0], [2.0, 2.0]])


def test_anchor_comparison_pins_exact_schema_and_relative_tolerance() -> None:
    expected = {"valid": True, "value": 2.0, "nested": {"x": 3.0}}
    passing = {"valid": True, "value": 2.0 * (1 + 5e-7), "nested": {"x": 3.0}}
    failing = {"valid": True, "value": 2.0 * (1 + 2e-6), "nested": {"x": 3.0}}
    assert MODULE._anchor_compare(passing, expected)["passes"]
    assert not MODULE._anchor_compare(failing, expected)["passes"]
    assert not MODULE._anchor_compare({**expected, "extra": 1}, expected)["passes"]


def test_contract_pins_completion_and_reward_matched_static_reference() -> None:
    contract = MODULE.build_contract()["r452"]
    assert contract["execution_shards"] == 68
    assert contract["candidate_trajectories"] == 8_400
    assert contract["static_trajectories"] == 24
    assert contract["static_selected"] == MODULE.STATIC_SELECTED
    assert contract["thresholds"] == {
        "joint_endpoint_improvement_min": 0.05,
        "maximum_common_harm": 0.03,
        "maximum_action_stress_harm": 0.10,
        "maximum_action_saturation_fraction": 0.05,
        "anchor_relative_tolerance": 1e-6,
    }
