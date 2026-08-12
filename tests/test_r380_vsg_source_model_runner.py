from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r380_vsg_source_model_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r380", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_closes_the_registered_two_point_source_model_gate() -> None:
    runner = _load_runner()
    contract = runner.build_contract()

    assert contract["round"] == "R380"
    assert contract["points"] == {
        "P0": {"pq_bus15_p0_system_pu": 0.0},
        "P1": {"pq_bus15_p0_system_pu": 0.05},
    }
    assert contract["control_inputs"] == ["VSG_1", "VSG_2", "VSG_3", "VSG_4"]
    assert contract["disturbance_inputs"] == ["PQ_0", "PQ_1", "PQ_Bus14"]
    assert contract["sample_period_seconds"] == 0.2
    assert contract["validation"]["record_count"] == 36
    assert contract["validation"]["steps_per_record"] == 125
    assert contract["validation"]["pulse_steps"] == [5, 9]
    assert contract["thresholds"] == {
        "adjacent_derivative_relative_difference_max": 1.0e-5,
        "midpoint_ratio_max": 1.0e-6,
        "algebraic_reciprocal_condition_min": 1.0e-12,
        "eig_relative_frobenius_error_max": 1.0e-8,
        "eig_maximum_absolute_error_max": 1.0e-9,
        "control_markov_rank": 4,
        "nrmse_max": 0.15,
        "peak_vector_residual_max": 0.20,
        "zero_repeatability_hz_max": 1.0e-9,
    }
    assert runner._contract_is_closed(contract) is True


def test_runner_exposes_only_canary_readiness_and_formal_execution() -> None:
    runner = _load_runner()
    parser = runner.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert set(subparsers.choices) == {"canary", "rehearse", "prepare", "execute"}
    with pytest.raises(SystemExit):
        parser.parse_args(["execute"])


def test_create_only_json_refuses_overwrite(tmp_path: Path) -> None:
    runner = _load_runner()
    target = tmp_path / "artifact.json"
    runner._write_new_json(target, {"round": "R380"})
    with pytest.raises(FileExistsError):
        runner._write_new_json(target, {"round": "R380", "drift": True})


def test_rehearsal_requires_no_seal_attempt_model_or_trajectory() -> None:
    runner = _load_runner()
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "active_plan": True,
        "contract_closed": True,
        "capacity_ready": True,
        "output_absence": True,
        "competing_process_absence": True,
        "seal_created": False,
        "formal_attempt_created": False,
        "source_model_created": False,
        "physical_trajectory_executed": False,
    }
    assert runner._rehearsal_checks({"checks": checks}) is True
    checks["source_model_created"] = True
    assert runner._rehearsal_checks({"checks": checks}) is False


def test_capacity_payload_reuses_only_the_serial_r379_host_budget() -> None:
    runner = _load_runner()
    anchor = {
        "readiness": "RUN-READY",
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "host": {
            "logical_processors": 32,
            "physical_memory_bytes": 33_500_000_000,
        },
        "wsl": {"memory_available_bytes": 16_000_000_000},
        "installed_runtime": {"andes_version": "2.0.0", "case_sha256": "case"},
        "checks": {"artifact_fit": True, "memory_fit": True},
    }
    payload = runner._build_capacity_payload(
        anchor=anchor,
        anchor_sha256="abc",
        runtime={"andes_version": "2.0.0", "case_sha256": "case"},
        logical_processors=32,
        physical_memory_bytes=33_500_000_000,
        wsl_memory_available_bytes=15_000_000_000,
        projected_artifact_bytes=2_000_000,
        disk_free_bytes=5_000_000_000,
        other_processes=(),
    )

    assert payload["readiness"] == "RUN-READY"
    assert payload["host_process_budget"] == 1
    assert payload["wsl_python_processes"] == 1
    assert payload["native_threads_per_process"] == 1
    assert payload["other_reserved_processes"] == 0
    assert payload["formal_projection"] == {
        "record_count": 36,
        "environment_steps": 4500,
    }
    assert payload["scientific_classification_inspected"] is False
    assert payload["training_executed"] is False


def test_record_guards_bind_point_runtime_and_exact_input_profile() -> None:
    runner = _load_runner()
    spec = next(
        row
        for row in runner.record_specs()
        if row["record_id"] == "P1_combined_plus"
    )
    inputs = runner.input_sequence(spec)
    baseline_pref = np.full(4, 0.5)
    load_baseline = np.asarray([11.59, 15.75, 2.48])
    rows = []
    for step_index, values in enumerate(inputs):
        control = values[:4]
        disturbance = values[4:]
        rows.append(
            {
                "step_index": step_index,
                "time": 0.7 + 0.2 * step_index,
                "control_system_pu": control.tolist(),
                "disturbance_system_pu": disturbance.tolist(),
                "requested_power_system_pu": control.tolist(),
                "commanded_power_system_pu": control.tolist(),
                "sampled_omega_pu": np.ones(4).tolist(),
                "baseline_pref_system_pu": baseline_pref.tolist(),
                "pref_written_system_pu": (baseline_pref + control).tolist(),
                "pref_readback_system_pu": (baseline_pref + control).tolist(),
                "torque_readback_system_pu": (baseline_pref + control).tolist(),
                "achieved_power_system_pu": control.tolist(),
                "load_readback_system_pu": (load_baseline + disturbance).tolist(),
                "saturation_reasons": [[], [], [], []],
                "omega": np.ones(4).tolist(),
                "freq_hz_physical": np.full(4, 60.0).tolist(),
                "P_es": np.zeros(4).tolist(),
                "delta_M": np.zeros(4).tolist(),
                "delta_D": np.zeros(4).tolist(),
                "md_action_norm": np.zeros((4, 2)).tolist(),
                "tds_failed": False,
            }
        )
    identity = {
        "point": "P1",
        "vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
        "vsg_buses": [12, 16, 14, 15],
        "pq_load_ids": ["PQ_0", "PQ_1", "PQ_Bus14"],
        "pq_bus15_p0_system_pu": 0.05,
        "pflow_converged": True,
        "tds_test_ok": True,
        "exit_code": 0,
        "seal_sha256": "a" * 64,
        "case_sha256": "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8",
        "andes_version": "2.0.0",
    }
    runtime = {
        "andes_version": "2.0.0",
        "case_sha256": "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8",
    }

    guards = runner.record_guards(
        rows=rows,
        expected_inputs=inputs,
        point="P1",
        identity=identity,
        load_baseline=load_baseline,
        seal_sha256="a" * 64,
        runtime=runtime,
        failure=None,
        contract=runner.build_contract(),
    )
    assert all(guards.values())

    identity["pq_bus15_p0_system_pu"] = 0.0
    guards = runner.record_guards(
        rows=rows,
        expected_inputs=inputs,
        point="P1",
        identity=identity,
        load_baseline=load_baseline,
        seal_sha256="a" * 64,
        runtime=runtime,
        failure=None,
        contract=runner.build_contract(),
    )
    assert guards["identity_and_units"] is False


def test_source_construction_stops_at_the_first_failed_point(monkeypatch) -> None:
    runner = _load_runner()
    calls: list[str] = []

    def fail_first(point: str, *, source_fingerprint: str):
        calls.append(point)
        assert source_fingerprint
        return (
            {
                "point": point,
                "object_valid": True,
                "construction_pass": False,
                "error": "registered failure",
                "sampled_model": None,
            },
            None,
        )

    monkeypatch.setattr(runner, "_construct_point_model", fail_first)
    constructions, models, object_valid = runner._construct_models_first_failure(
        seal_sha256="a" * 64,
        runtime={"andes_version": "2.0.0"},
    )

    assert calls == ["P0"]
    assert list(constructions) == ["P0"]
    assert models == {}
    assert object_valid is True


def test_validation_execution_stops_at_the_first_invalid_record(monkeypatch) -> None:
    runner = _load_runner()
    calls: list[str] = []

    def invalid_first(spec, *, seal_sha256: str, runtime):
        calls.append(str(spec["record_id"]))
        assert seal_sha256 and runtime
        return {
            "record_id": spec["record_id"],
            "guards": {"record_complete": False},
        }

    monkeypatch.setattr(runner, "_run_record", invalid_first)
    records = runner._run_validation_records_first_failure(
        specs=runner.record_specs(),
        seal_sha256="a" * 64,
        runtime={"andes_version": "2.0.0"},
    )

    assert calls == ["P0_zero_0"]
    assert len(records) == 1
