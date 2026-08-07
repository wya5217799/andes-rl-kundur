"""Public contract tests for the R344 deterministic bridge adapter."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import scripts.run_r344_deterministic_bridge as adapter


def test_adapter_bootstraps_repository_imports_from_isolated_cwd(
    tmp_path: Path,
) -> None:
    probe = f"""
import importlib
import importlib.util

spec = importlib.util.spec_from_file_location(
    "isolated_r344_adapter",
    {str(Path(adapter.__file__).resolve())!r},
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parent = importlib.import_module("scripts.run_r334_pq_disturbance_identification")
print(parent.__name__)
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "scripts.run_r334_pq_disturbance_identification"


def test_contract_freezes_small_staged_inventory_and_learning_exclusions() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R344"
    assert contract["question"] == "Q-0090"
    assert contract["controller"]["information_pattern"] == "full-output-centralized"
    assert contract["controller"]["horizon_steps"] == 25
    assert contract["capacity"]["job_count"] == 32
    assert contract["capacity"]["worker_rungs"] == [16, 24, 32]
    assert contract["canaries"]["zero_action_job_count"] == 2
    assert contract["canaries"]["signed_authority_job_count"] == 16
    assert contract["formal"]["scenario_count"] == 16
    assert contract["formal"]["trajectory_count"] == 32
    assert contract["formal"]["amplitude_by_device_system_pu"] == {
        "PQ_0": 0.03,
        "PQ_1": 0.03,
        "PQ_Bus14": 0.03,
        "PQ_Bus15": 0.02,
    }
    assert contract["training_executed"] is False
    assert contract["distributed_runtime_executed"] is False
    assert contract["eval_executed"] is False


def test_prepare_is_create_only_and_binds_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seal = tmp_path / "formal_seal.json"
    launch = {
        "worker_processes": 24,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "installed_andes": {
            "version": "2.0.0",
            "sources": {"andes": "frozen"},
            "case": {"sha256": "a" * 64},
        },
        "rehearsal": {"path": "memory/rounds/R344/rehearsal.json", "sha256": "b" * 64},
        "capacity": {"path": "memory/rounds/R344/capacity_ladder.json", "sha256": "c" * 64},
        "host_capacity": {"path": "memory/rounds/R344/host_capacity.json", "sha256": "d" * 64},
    }
    monkeypatch.setattr(adapter, "_verified_launch_prerequisites", lambda: launch)
    monkeypatch.setattr(
        adapter, "_installed_andes_identity", lambda: launch["installed_andes"]
    )
    monkeypatch.setattr(
        adapter,
        "_formal_output_paths",
        lambda out_dir=adapter.DEFAULT_OUT: [seal],
    )
    monkeypatch.setattr(adapter, "DEFAULT_OUT", tmp_path / "formal_output")

    digest = adapter.prepare(seal)
    payload, verified = adapter.load_seal(seal, digest)

    assert digest == verified
    assert payload["round"] == "R344"
    assert payload["contract"] == adapter.build_contract()
    assert payload["launch"] == launch
    assert payload["formal_trace_count_at_freeze"] == 0
    with pytest.raises(FileExistsError):
        adapter.prepare(seal)


def test_parser_exposes_no_training_or_eval_command() -> None:
    parser = adapter.build_parser()
    subparsers = next(
        action for action in parser._actions if action.dest == "command"
    )
    commands = set(subparsers.choices)

    assert {
        "prepare",
        "rehearse",
        "capacity-ladder",
        "execute-canaries",
        "execute-formal",
        "analyse",
    } <= commands
    assert not {"train", "training", "eval", "distributed"} & commands
    assert not hasattr(parser.parse_args(["rehearse"]), "expected_sha256")
    assert not hasattr(parser.parse_args(["capacity-ladder"]), "expected_sha256")
    assert parser.parse_args(
        ["execute-canaries", "--expected-sha256", "0" * 64]
    ).expected_sha256 == "0" * 64


def test_capacity_cli_forwards_create_only_recovery_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "capacity_attempt_2"
    record_path = tmp_path / "capacity_ladder_attempt_2.json"
    captured: dict[str, Path] = {}

    def fake_capacity_ladder(*, out_dir: Path, record_path: Path) -> str:
        captured.update(out_dir=out_dir, record_path=record_path)
        return "a" * 64

    monkeypatch.setattr(adapter, "run_capacity_ladder", fake_capacity_ladder)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_r344_deterministic_bridge.py",
            "capacity-ladder",
            "--out",
            str(out_dir),
            "--record",
            str(record_path),
        ],
    )

    assert adapter.main() == 0
    assert captured == {"out_dir": out_dir, "record_path": record_path}


def test_controller_loader_binds_each_exact_r341_point() -> None:
    for point in ("FV0", "FV1"):
        controller, identity = adapter.build_point_controller(point)

        assert identity["point"] == point
        assert identity["order12_canonical_sha256"] == (
            adapter.POINT_MODEL_DIGESTS[point]
        )
        assert controller.identity.output_scales == tuple(adapter.OUTPUT_SCALES[point])
        assert controller.estimator.observability_rank == 16
        assert controller.estimator.error_pole_radius < 1.0


def test_capacity_selection_uses_throughput_only_among_valid_rungs() -> None:
    selected = adapter.select_capacity_rung(
        [
            {"worker_processes": 16, "valid": True, "throughput_jobs_per_second": 3.1},
            {"worker_processes": 24, "valid": True, "throughput_jobs_per_second": 4.7},
            {"worker_processes": 32, "valid": False, "throughput_jobs_per_second": 5.4},
        ]
    )

    assert selected["worker_processes"] == 24
    with pytest.raises(ValueError, match="no valid capacity rung"):
        adapter.select_capacity_rung(
            [{"worker_processes": 32, "valid": False, "throughput_jobs_per_second": 9.0}]
        )


def _formal_record(
    *,
    point: str,
    scenario: str,
    arm: str,
    common: float,
    differential: float,
) -> dict[str, object]:
    return {
        "point": point,
        "scenario_id": scenario,
        "arm": arm,
        "integrity_valid": True,
        "physical_guards_pass": True,
        "fallback_count": 0,
        "controller_engaged": arm == "frozen_controller",
        "metrics": {
            "common_coordinate_iae": common,
            "differential_coordinate_energy": differential,
        },
    }


def test_formal_classifier_requires_material_paired_benefit_at_both_points() -> None:
    records: list[dict[str, object]] = []
    for point in ("FV0", "FV1"):
        for index in range(8):
            scenario = f"{point}_{index}"
            records.extend(
                [
                    _formal_record(
                        point=point,
                        scenario=scenario,
                        arm="zero_control",
                        common=10.0,
                        differential=5.0,
                    ),
                    _formal_record(
                        point=point,
                        scenario=scenario,
                        arm="frozen_controller",
                        common=9.0,
                        differential=4.5,
                    ),
                ]
            )

    passed = adapter.classify_formal_records(records)
    assert passed["classification"] == "DETERMINISTIC-BRIDGE-PASS"
    assert passed["paired_mean_improvement_fraction"] == {
        "common_coordinate_iae": pytest.approx(0.1),
        "differential_coordinate_energy": pytest.approx(0.1),
    }

    records[-1]["metrics"] = {
        "common_coordinate_iae": 10.6,
        "differential_coordinate_energy": 4.5,
    }
    no_benefit = adapter.classify_formal_records(records)
    assert no_benefit["classification"] == "VALID-NO-DETERMINISTIC-BENEFIT"
    assert not no_benefit["guards"]["maximum_scenario_worsening"]


def test_formal_classifier_separates_integrity_and_physical_failures() -> None:
    record = _formal_record(
        point="FV0",
        scenario="bad",
        arm="zero_control",
        common=1.0,
        differential=1.0,
    )
    record["integrity_valid"] = False
    assert adapter.classify_formal_records([record])["classification"] == (
        "INVALID-DETERMINISTIC-BRIDGE"
    )

    record["integrity_valid"] = True
    record["physical_guards_pass"] = False
    assert adapter.classify_formal_records([record])["classification"] == (
        "DETERMINISTIC-PHYSICAL-GUARD-FAIL"
    )


def test_signed_coordinate_inventory_maps_common_and_edges() -> None:
    basis = adapter.control_coordinate_basis()

    np.testing.assert_allclose(basis[:, 0], np.ones(4))
    np.testing.assert_allclose(np.sum(basis[:, 1:], axis=0), np.zeros(3))
    assert np.linalg.matrix_rank(basis) == 4


def test_rehearsal_is_create_only_and_has_no_physical_or_formal_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installed = {
        "version": "2.0.0",
        "sources": {"andes": "frozen"},
        "case": {"path": "/installed/kundur_full.xlsx", "sha256": "a" * 64},
    }
    monkeypatch.setattr(adapter, "_installed_andes_identity", lambda: installed)
    monkeypatch.setattr(adapter, "_r344_python_process_count", lambda: 1)
    record = tmp_path / "round" / "rehearsal.json"
    scratch = tmp_path / "scratch"
    scratch.mkdir()

    digest = adapter.rehearse(
        record_path=record,
        output_paths=[tmp_path / "formal_attempt.json"],
        cwd=scratch,
        scratch_root=tmp_path,
    )
    payload = adapter._read_hashed_json(record)

    assert adapter._sha256_file(record) == digest
    assert payload["installed_andes"] == installed
    assert payload["manifest_roundtrip"] is True
    assert payload["scratch_isolation"] is True
    assert payload["physical_trajectory_executed"] is False
    assert payload["formal_attempt_created"] is False
    assert payload["formal_seal_created"] is False
    with pytest.raises(FileExistsError):
        adapter.rehearse(
            record_path=record,
            output_paths=[tmp_path / "formal_attempt.json"],
            cwd=scratch,
            scratch_root=tmp_path,
        )


def test_rehearsal_rejects_repository_cwd_and_preexisting_formal_asset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        adapter,
        "_installed_andes_identity",
        lambda: {
            "version": "2.0.0",
            "sources": {"andes": "frozen"},
            "case": {"path": "/installed/kundur_full.xlsx", "sha256": "a" * 64},
        },
    )
    monkeypatch.setattr(adapter, "_r344_python_process_count", lambda: 1)

    with pytest.raises(RuntimeError, match="scratch isolation"):
        adapter.pre_attempt_checks(
            output_paths=[],
            cwd=adapter.ROOT,
            scratch_root=adapter.ROOT / "tmp" / "andes",
        )

    existing = tmp_path / "formal_attempt.json"
    existing.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="pre-existing R344 formal asset"):
        adapter.pre_attempt_checks(
            output_paths=[existing],
            cwd=tmp_path,
            scratch_root=tmp_path.parent,
        )

    monkeypatch.setattr(adapter, "_formal_output_paths", lambda: [existing])
    for name in adapter.THREAD_ENVIRONMENT:
        monkeypatch.setenv(name, "1")
    result = adapter.pre_attempt_checks(
        output_paths=[],
        cwd=tmp_path,
        scratch_root=tmp_path.parent,
    )
    assert result["checks"]["output_absence"] is True


def test_canary_classifier_stops_between_zero_and_signed_stages() -> None:
    zero = [
        {
            "mode": "zero_canary",
            "point": point,
            "integrity_valid": True,
            "physical_guards_pass": True,
        }
        for point in ("FV0", "FV1")
    ]
    signed = [
        {
            "mode": "signed_canary",
            "integrity_valid": True,
            "physical_guards_pass": True,
        }
        for _ in range(16)
    ]

    assert adapter.classify_canary_stage(zero, mode="zero_canary", count=2) == (
        "CANARY-STAGE-PASS"
    )
    assert adapter.classify_canary_stage(
        signed, mode="signed_canary", count=16
    ) == "CANARY-STAGE-PASS"
    zero[0]["physical_guards_pass"] = False
    assert adapter.classify_canary_stage(zero, mode="zero_canary", count=2) == (
        "DETERMINISTIC-PHYSICAL-GUARD-FAIL"
    )
    zero[0]["integrity_valid"] = False
    assert adapter.classify_canary_stage(zero, mode="zero_canary", count=2) == (
        "INVALID-DETERMINISTIC-BRIDGE"
    )


def test_zero_and_signed_spec_inventory_is_fixed() -> None:
    zero = adapter.build_zero_canary_specs()
    signed = adapter.build_signed_canary_specs()
    formal = adapter.build_formal_specs()

    assert len(zero) == 2
    assert len(signed) == 16
    assert len(formal) == 32
    assert {row["arm"] for row in formal} == {
        "zero_control",
        "frozen_controller",
    }
    assert all(row["total_steps"] == 25 for row in signed + formal)
