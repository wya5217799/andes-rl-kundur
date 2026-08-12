from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r365_per_vsg_object_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r365", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_exposes_no_training_or_tuning_command() -> None:
    runner = _load_runner()
    parser = runner.build_parser()
    subparsers = next(
        action for action in parser._actions if action.__class__.__name__ == "_SubParsersAction"
    )
    assert set(subparsers.choices) == {
        "rehearse",
        "measure-capacity",
        "prepare",
        "execute",
    }


def test_create_only_json_refuses_overwrite(tmp_path: Path) -> None:
    runner = _load_runner()
    target = tmp_path / "artifact.json"
    runner._write_new_json(target, {"round": "R365"})
    with pytest.raises(FileExistsError):
        runner._write_new_json(target, {"round": "R365", "drift": True})


def test_rehearsal_accepts_explicit_no_physical_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "active_plan": True,
        "in_flight_question": True,
        "contract_closed": True,
        "physical_trajectory_executed": False,
    }
    assert runner._rehearsal_checks({"checks": checks}) is True


def test_capacity_payload_matches_project_preflight_schema() -> None:
    runner = _load_runner()
    payload = runner._build_capacity_payload(
        representative_valid=True,
        representative_wall_seconds=2.0,
        max_rss_kib=1000,
        disk_free_bytes=2000,
        logical_processors=8,
        physical_memory_bytes=16_000,
        wsl_memory_available_bytes=8_000,
        runtime={"andes_version": "test"},
        sources={"runner": {"sha256": "abc"}},
        parents={"route": {"sha256": "def"}},
    )
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["host"] == {
        "logical_processors": 8,
        "physical_memory_bytes": 16_000,
    }
    assert payload["wsl"]["memory_available_bytes"] == 8_000
    assert payload["empirical_anchor"]["all_records_valid"] is True
    assert payload["empirical_anchor"]["concurrent_workers"] == 1
    assert payload["empirical_anchor"]["native_threads_per_worker"] == 1
