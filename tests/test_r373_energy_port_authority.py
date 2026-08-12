from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r373_energy_port_authority.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r373", RUNNER)
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


def test_create_only_json_refuses_overwrite(tmp_path: Path) -> None:
    runner = _load_runner()
    target = tmp_path / "artifact.json"
    runner._write_new_json(target, {"round": "R373"})
    with pytest.raises(FileExistsError):
        runner._write_new_json(target, {"round": "R373", "drift": True})


def test_rehearsal_requires_explicit_no_physical_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
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


def test_capacity_payload_scales_the_measured_r372_anchor() -> None:
    runner = _load_runner()
    runtime = {"andes_version": "2.0.0", "case_sha256": "case"}
    anchor_execution = {
        "record_count": 10,
        "wall_seconds": 5.0,
        "records": [{"tds_failed": False}] * 10,
    }
    anchor_capacity = {
        "installed_runtime": runtime,
        "host": {
            "logical_processors": 32,
            "physical_memory_bytes": 33_500_000_000,
        },
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "empirical_anchor": {"max_rss_kib": 160_000},
    }
    parents = {
        "object_execution": {"path": "execution.json", "sha256": "abc"},
        "object_capacity": {"path": "capacity.json", "sha256": "def"},
    }
    payload = runner._build_capacity_payload(
        anchor_execution=anchor_execution,
        anchor_capacity=anchor_capacity,
        projected_artifact_bytes=1_000_000,
        disk_free_bytes=1_000_000_000,
        logical_processors=32,
        physical_memory_bytes=33_500_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        runtime=runtime,
        sources={"runner": {"sha256": "ghi"}},
        parents=parents,
    )

    assert payload["readiness"] == "RUN-READY"
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["wsl_python_processes"] == 1
    assert payload["native_threads_per_process"] == 1
    assert payload["formal_projection"]["environment_steps"] == 1200
    assert payload["formal_projection"][
        "wall_seconds_with_1p5_safety_factor"
    ] == pytest.approx(180.0)
    assert payload["scientific_classification_inspected"] is False
    assert payload["formal_authority"] is False
    assert payload["training_executed"] is False
