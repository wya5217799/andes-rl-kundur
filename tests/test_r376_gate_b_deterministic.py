from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r376_gate_b_deterministic.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r376", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_exposes_only_rehearsal_seal_and_formal_execution() -> None:
    runner = _load_runner()
    parser = runner.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert set(subparsers.choices) == {"rehearse", "prepare", "execute"}
    assert runner._contract_is_closed(runner.build_contract()) is True


def test_rehearsal_requires_explicit_no_physical_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "parent_sidecars": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "active_plan": True,
        "contract_closed": True,
        "capacity_ready": True,
        "competing_process_absence": True,
        "artifact_fit": True,
        "physical_trajectory_executed": False,
    }
    assert runner._rehearsal_checks({"checks": checks}) is True
    checks["physical_trajectory_executed"] = True
    assert runner._rehearsal_checks({"checks": checks}) is False


def test_capacity_projection_scales_the_measured_r374_anchor() -> None:
    runner = _load_runner()
    runtime = {"andes_version": "2.0.0", "case_sha256": "case"}
    anchor_execution = {
        "record_count": 60,
        "wall_seconds": 300.0,
        "records": [{"tds_failed": False}] * 60,
    }
    anchor_capacity = {
        "installed_runtime": runtime,
        "host": {
            "logical_processors": 32,
            "physical_memory_bytes": 33_500_000_000,
        },
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "empirical_anchor": {"record_count": 60},
        "checks": {"memory_fit": True},
        "wsl": {"memory_available_bytes": 16_000_000_000},
    }
    parents = {
        "r374_development": {"path": "development.json", "sha256": "abc"},
        "r375_seal": {"path": "seal.json", "sha256": "def"},
    }

    payload = runner._build_capacity_payload(
        anchor_execution=anchor_execution,
        anchor_capacity=anchor_capacity,
        projected_artifact_bytes=10_000_000,
        disk_free_bytes=2_000_000_000,
        logical_processors=32,
        physical_memory_bytes=33_500_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        runtime=runtime,
        sources={"runner": {"sha256": "ghi"}},
        parents=parents,
    )

    assert payload["readiness"] == "RUN-READY"
    assert payload["formal_projection"]["record_count"] == 90
    assert payload["formal_projection"]["environment_steps"] == 4500
    assert payload["formal_projection"][
        "wall_seconds_with_1p5_safety_factor"
    ] == pytest.approx(675.0)
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["training_executed"] is False


def test_contract_freezes_probe_and_clip_values() -> None:
    runner = _load_runner()
    contract = runner.build_contract()
    assert contract["probe_component_action"] == 0.25
    assert contract["controller_action_clip"] == 0.70
    assert contract["round"] == "R376"
