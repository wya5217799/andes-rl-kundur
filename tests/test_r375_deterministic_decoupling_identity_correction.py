from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r375_deterministic_decoupling_identity_correction.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r375", RUNNER)
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


def test_rehearsal_is_result_blind_and_runs_no_physical_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "parent_sidecars": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "active_plan": True,
        "contract_single_diff": True,
        "identity_alignment": True,
        "capacity_ready": True,
        "competing_process_absence": True,
        "artifact_fit": True,
        "performance_fields_parsed": False,
        "physical_trajectory_executed": False,
    }

    assert runner._rehearsal_checks({"checks": checks}) is True
    checks["performance_fields_parsed"] = True
    assert runner._rehearsal_checks({"checks": checks}) is False


def test_capacity_projects_only_conditional_held_out_work() -> None:
    runner = _load_runner()
    payload = runner._build_capacity_payload(
        anchor_wall_seconds=447.5055512560066,
        projected_artifact_bytes=10_000_000,
        disk_free_bytes=2_000_000_000,
        logical_processors=32,
        physical_memory_bytes=33_500_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        runtime={"andes_version": "2.0.0", "case_sha256": "case"},
        sources={"runner": {"sha256": "abc"}},
        parents={"development_execution": {"sha256": "def"}},
    )

    assert payload["readiness"] == "RUN-READY"
    assert payload["reused_development"]["record_count"] == 60
    assert payload["maximum_new_execution"]["record_count"] == 30
    assert payload["maximum_new_execution"]["environment_steps"] == 1500
    assert payload["maximum_new_execution"][
        "wall_seconds_with_1p5_safety_factor"
    ] == pytest.approx(335.6291634420049)
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["training_executed"] is False
