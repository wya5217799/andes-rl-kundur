from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r384_regcv1_object_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r384", RUNNER)
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
    runner._write_new_json(target, {"round": "R384"})
    with pytest.raises(FileExistsError):
        runner._write_new_json(target, {"round": "R384", "drift": True})


def test_rehearsal_requires_explicit_absence_of_physical_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "question_in_flight": True,
        "active_plan": True,
        "no_competing_research_process": True,
        "physical_trajectory_executed": False,
    }
    assert runner._rehearsal_checks({"checks": checks}) is True
    checks["physical_trajectory_executed"] = True
    assert runner._rehearsal_checks({"checks": checks}) is False


def test_capacity_payload_records_one_job_stage_cap() -> None:
    runner = _load_runner()
    payload = runner._build_capacity_payload(
        logical_processors=32,
        physical_memory_bytes=34_000_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        disk_free_bytes=100_000_000_000,
        competing_processes=[],
    )
    assert payload["readiness"] == "RUN-READY"
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["wsl_python_processes"] == 1
    assert payload["native_threads_per_process"] == 1
    assert payload["stage_cap_reason"] == "one independent formal job"
    assert payload["physical_trajectory_executed"] is False


class _FakeRenGen:
    def __init__(self):
        self.values = {
            "pref": {f"REGCV1_{index}": 0.7 + index / 100.0 for index in range(1, 5)},
            "qref": {f"REGCV1_{index}": 0.08 + index / 1000.0 for index in range(1, 5)},
        }

    def get_pref(self, _system, idx):
        return self.values["pref"][idx]

    def set_pref(self, _system, idx, value):
        self.values["pref"][idx] = value

    def get_qref(self, _system, idx):
        return self.values["qref"][idx]

    def set_qref(self, _system, idx, value):
        self.values["qref"][idx] = value


def test_setpoint_probe_is_per_device_noninterfering_and_restoring() -> None:
    runner = _load_runner()
    system = SimpleNamespace(RenGen=_FakeRenGen())
    before = {
        channel: dict(values)
        for channel, values in system.RenGen.values.items()
    }

    result = runner._probe_setpoint_identity(
        system,
        [f"REGCV1_{index}" for index in range(1, 5)],
    )

    assert result["attempted"] is True
    assert result["completed"] is True
    assert all(row["non_target_unchanged"] for row in result["pref"])
    assert all(row["non_target_unchanged"] for row in result["qref"])
    assert system.RenGen.values == before
