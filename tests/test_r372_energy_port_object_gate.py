from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r372_energy_port_object_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r372", RUNNER)
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
    runner._write_new_json(target, {"round": "R372"})
    with pytest.raises(FileExistsError):
        runner._write_new_json(target, {"round": "R372", "drift": True})


def test_rehearsal_accepts_explicit_no_physical_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "active_plan": True,
        "contract_closed": True,
        "capacity_anchor": True,
        "current_host": True,
        "competing_process_absence": True,
        "artifact_fit": True,
        "physical_trajectory_executed": False,
    }
    assert runner._rehearsal_checks({"checks": checks}) is True


def test_capacity_payload_binds_anchor_resources_and_serial_budget() -> None:
    runner = _load_runner()
    anchor = {
        "empirical_anchor": {
            "all_records_valid": True,
            "concurrent_workers": 1,
            "native_threads_per_worker": 1,
            "representative_steps": 5,
            "wall_seconds": 1.25,
        },
        "max_rss_kib": 159_000,
        "host": {
            "logical_processors": 32,
            "physical_memory_bytes": 33_500_000_000,
        },
        "installed_runtime": {"andes_version": "2.0.0"},
    }
    payload = runner._build_capacity_payload(
        anchor=anchor,
        anchor_path="memory/rounds/R365/capacity_evidence_v2.json",
        anchor_sha256="abc",
        projected_artifact_bytes=12_000,
        disk_free_bytes=2_000_000,
        logical_processors=32,
        physical_memory_bytes=33_500_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        runtime={"andes_version": "2.0.0"},
        sources={"runner": {"sha256": "def"}},
        parents={"route": {"sha256": "ghi"}},
    )
    assert payload["readiness"] == "RUN-READY"
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["wsl_python_processes"] == 1
    assert payload["native_threads_per_process"] == 1
    assert payload["other_reserved_processes"] == 0
    assert payload["projected_formal_wall_seconds"] == pytest.approx(12.5)
    assert payload["artifact_projection"]["projected_bytes"] == 12_000
    assert payload["empirical_anchor"]["path"].endswith(
        "capacity_evidence_v2.json"
    )
    assert payload["scientific_classification_inspected"] is False
    assert payload["formal_authority"] is False
    assert payload["training_executed"] is False
