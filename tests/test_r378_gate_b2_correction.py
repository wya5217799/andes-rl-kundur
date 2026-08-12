from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r378_gate_b2_correction.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r378", RUNNER)
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


def test_rehearsal_requires_no_performance_parse_and_no_trajectory() -> None:
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
        "correction_valid": True,
        "capacity_ready": True,
        "competing_process_absence": True,
        "artifact_fit": True,
        "performance_fields_parsed": False,
        "physical_trajectory_executed": False,
    }
    assert runner._rehearsal_checks({"checks": checks}) is True
    checks["performance_fields_parsed"] = True
    assert runner._rehearsal_checks({"checks": checks}) is False


def test_contract_is_corrected_r377_contract() -> None:
    runner = _load_runner()
    corrected = runner.build_corrected_contract(runner.build_contract())
    assert runner._contract_is_closed(corrected) is True
    assert corrected["round"] == "R378"
    assert corrected["correction_scope"] == ["round", "settling_rule"]
    assert corrected["thresholds"] == runner.build_contract()["thresholds"]


def test_capacity_projection_scales_r377_anchor() -> None:
    runner = _load_runner()
    runtime = {"andes_version": "2.0.0", "case_sha256": "case"}
    payload = runner._build_capacity_payload(
        anchor_wall_seconds=449.2381028229138,
        projected_artifact_bytes=20_000_000,
        disk_free_bytes=3_000_000_000,
        logical_processors=32,
        physical_memory_bytes=33_500_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        runtime=runtime,
        sources={"runner": {"sha256": "ghi"}},
        parents={"r377_plan": {"sha256": "abc"}},
    )
    assert payload["readiness"] == "RUN-READY"
    assert payload["maximum_new_execution"]["record_count"] == 30
    assert payload["maximum_new_execution"][
        "point_estimate_wall_seconds"
    ] == pytest.approx(224.619, abs=0.01)
    assert payload["maximum_new_execution"][
        "wall_seconds_with_1p5_safety_factor"
    ] == pytest.approx(336.93, abs=0.02)
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["training_executed"] is False
