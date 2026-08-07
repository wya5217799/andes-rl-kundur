from __future__ import annotations

import copy

import numpy as np
import pytest
from scripts import run_r339_input_bridge_diagnosis as r339


def test_contract_freezes_sixteen_whole_host_jobs_and_no_fresh_trajectory() -> None:
    contract = r339.build_contract()

    assert contract["round"] == "R339"
    assert contract["question"] == "Q-0087"
    assert contract["whole_host_python_processes"] == 16
    assert contract["native_threads_per_process"] == 1
    assert len(contract["job_specs"]) == 16
    assert contract["job_specs"][0] == {
        "point": "HS0",
        "input_family": "control",
        "channel": 0,
    }
    assert contract["job_specs"][-1] == {
        "point": "HS1",
        "input_family": "load",
        "channel": 3,
    }
    assert contract["finite_difference_steps_system_pu"] == [1e-4, 1e-5, 1e-6]
    assert contract["fresh_nonlinear_trajectory_executed"] is False
    assert contract["controller_executed"] is False
    assert contract["training_executed"] is False


def test_parallel_schedule_uses_parent_plus_fifteen_children() -> None:
    schedule = r339.parallel_schedule()

    assert schedule["parent_job"] == {
        "point": "HS0",
        "input_family": "control",
        "channel": 0,
    }
    assert len(schedule["child_jobs"]) == 15
    assert schedule["total_python_processes"] == 16


def _column_job(channel: int, *, digest: str = "same") -> dict[str, object]:
    return {
        "point": "HS0",
        "input_family": "control",
        "channel": channel,
        "base_snapshot_sha256": digest,
        "base_snapshot": {"point": "HS0"},
        "channel_ids": ["a", "b", "c", "d"],
        "equilibrium_input_system_pu": [0.0, 0.0, 0.0, 0.0],
        "steps": [
            {
                "step_system_pu": step,
                "f_input_column": [[channel + step], [channel + step + 1.0]],
                "g_input_column": [[channel + step + 2.0]],
                "midpoint_ratio": step,
                "branch_reference_sha256": "branch",
                "all_branch_snapshots_match": True,
            }
            for step in (1.0e-4, 1.0e-5, 1.0e-6)
        ],
        "restored_exactly": True,
        "job_metadata": {"pid": 10 + channel},
    }


def test_family_combination_requires_four_identical_column_jobs() -> None:
    combined = r339.combine_family_jobs([_column_job(index) for index in range(4)])

    assert combined["channel_ids"] == ["a", "b", "c", "d"]
    assert combined["restored_exactly"] is True
    np.testing.assert_allclose(
        combined["steps"][0]["f_input"],
        [
            [0.0001, 1.0001, 2.0001, 3.0001],
            [1.0001, 2.0001, 3.0001, 4.0001],
        ],
    )
    assert combined["steps"][0]["midpoint_ratios"] == [
        1.0e-4,
        1.0e-4,
        1.0e-4,
        1.0e-4,
    ]

    with pytest.raises(RuntimeError, match="base snapshot"):
        r339.combine_family_jobs(
            [_column_job(index, digest="drift" if index == 3 else "same") for index in range(4)]
        )


def test_point_combination_requires_identical_independent_base_snapshot() -> None:
    control = {
        "point": "HS0",
        "input_family": "control",
        "base_snapshot_sha256": "same",
        "input_derivatives": {"family": "control"},
    }
    load = {
        "point": "HS0",
        "input_family": "load",
        "base_snapshot_sha256": "same",
        "input_derivatives": {"family": "load"},
    }

    combined = r339.combine_point_jobs(control, load)

    assert combined["point"] == "HS0"
    assert combined["base_snapshot_sha256"] == "same"
    assert combined["control_input_derivatives"] == {"family": "control"}
    assert combined["load_input_derivatives"] == {"family": "load"}

    drifted = copy.deepcopy(load)
    drifted["base_snapshot_sha256"] = "different"
    with pytest.raises(RuntimeError, match="base snapshot"):
        r339.combine_point_jobs(control, drifted)


def test_source_closure_contains_runner_math_and_public_tests() -> None:
    paths = {path.as_posix() for path in r339._source_paths().values()}

    assert any(path.endswith("scripts/run_r339_input_bridge_diagnosis.py") for path in paths)
    assert any(path.endswith("model_first_input_bridge.py") for path in paths)
    assert any(path.endswith("tests/test_r339_input_bridge_diagnosis.py") for path in paths)
    assert any(path.endswith("tests/test_model_first_input_bridge.py") for path in paths)
    assert any(path.endswith("probes/r339_input_bridge_diagnosis.py") for path in paths)
    assert any(path.endswith("tests/test_r339_input_bridge_probe.py") for path in paths)
