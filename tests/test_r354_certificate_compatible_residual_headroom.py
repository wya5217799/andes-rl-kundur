"""Regression tests for the R354 certificate-compatible recovery seam."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib import import_module

import numpy as np
import pytest
from scripts import run_r353_matched_residual_headroom as r353
from scripts import run_r354_certificate_compatible_residual_headroom as r354

from andes_rl_kundur.control.minimum_norm_certificate import MinimumNormCertificate
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import SeparateInputRealization


def test_current_minimum_norm_certificate_serializes_without_legacy_fields() -> None:
    """The recovery serializer must expose the actual sealed certificate schema."""

    recovery = import_module("probes.r354_certificate_compatible_residual_headroom")
    certificate = MinimumNormCertificate(
        valid=True,
        feasible=True,
        reason="certified",
        active_constraint_count=2,
        maximum_constraint_violation=1.0e-12,
        stationarity_residual=2.0e-7,
        complementarity_residual=3.0e-8,
        optimality_tolerance=1.0e-4,
        multipliers=np.asarray([0.25, 0.75]),
    )

    assert recovery.certificate_payload(certificate) == {
        "valid": True,
        "feasible": True,
        "reason": "certified",
        "active_constraint_count": 2,
        "maximum_constraint_violation": 1.0e-12,
        "stationarity_residual": 2.0e-7,
        "complementarity_residual": 3.0e-8,
        "optimality_tolerance": 1.0e-4,
        "multipliers": [0.25, 0.75],
    }


def test_oracle_case_uses_certificate_compatible_serializer_at_real_seam() -> None:
    """The R354 oracle seam must no longer call the frozen legacy serializer."""

    recovery = import_module("probes.r354_certificate_compatible_residual_headroom")
    direct = np.zeros((4, 4))
    direct[:, 1] = np.asarray([-1.0, -1.0, 0.0, 0.0])
    model = SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=direct,
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    case = {
        "scenario_id": "regression",
        "model": model,
        "base_outputs": np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        "zero_outputs": np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        "base_node_commands": np.zeros((1, 4)),
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "mismatch_envelope": np.zeros(4),
    }

    row = recovery.solve_oracle_case(
        case,
        minimum_improvement_fraction=0.02,
        maximum_iterations=20_000,
        function_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )

    assert row["feasible"] is True
    assert row["certificate"]["valid"] is True
    assert row["certificate"]["reason"] == "certified"
    assert "message" not in row["certificate"]
    assert FeedbackLimits().sample_period_seconds == 0.2


def test_recovery_contract_changes_only_identity_and_serializer_metadata() -> None:
    """Every scientific and execution field inherited from R353 stays identical."""

    parent_contract = r353.build_contract()
    recovery_contract = r354.build_contract()

    for key in (
        "inventory",
        "residual",
        "local_information",
        "statistics",
        "execution",
        "decision",
        "authorizations",
    ):
        assert recovery_contract[key] == parent_contract[key]
    assert recovery_contract["round"] == "R354"
    assert recovery_contract["question"] == parent_contract["question"]
    assert recovery_contract["recovery"]["parent_round"] == "R353"
    assert recovery_contract["recovery"]["authorized_change"] == (
        "minimum-norm-certificate-serialization-only"
    )
    assert recovery_contract["resource_budget"] == {
        "host_process_budget": 1,
        "analysis_processes": 1,
        "wsl_python_processes": 0,
        "native_threads_per_process": 1,
        "other_reserved_processes_at_plan": 0,
        "retry_authorized": False,
    }


def test_recovery_closure_binds_parent_failure_and_all_primary_traces() -> None:
    """The successor must bind both the invalid attempt and the original evidence."""

    sources = r354.source_paths(include_rehearsal=False)
    parents = r354.parent_paths()

    assert {
        "plan",
        "adapter",
        "probe",
        "recovery_tests",
        "r353_adapter",
        "r353_probe",
        "r353_probe_tests",
        "r353_adapter_tests",
    } <= set(sources)
    assert {"r353_seal", "r353_attempt", "r353_failure"} <= set(parents)
    assert len([name for name in parents if name.startswith("development_trace_")]) == 32
    assert len([name for name in parents if name.startswith("holdout_trace_")]) == 32
    assert all(path.is_file() for path in sources.values())
    assert all(path.is_file() for path in parents.values())


def test_formal_preflight_executes_corrected_serializer_smoke_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every formal entry must exercise, not merely inspect, the repaired seam."""

    def fail_if_called(_certificate: MinimumNormCertificate) -> dict[str, object]:
        raise RuntimeError("serializer smoke sentinel")

    monkeypatch.setattr(r354.recovery, "certificate_payload", fail_if_called)

    with pytest.raises(RuntimeError, match="serializer smoke sentinel"):
        r354._verify_recovery_inputs()


def test_adapter_caps_native_thread_pools_before_importing_numpy() -> None:
    """A fresh formal process must realize the preregistered one-thread cap."""

    code = """
import json
from threadpoolctl import threadpool_info
import scripts.run_r354_certificate_compatible_residual_headroom
print(json.dumps(threadpool_info()))
"""
    environment = os.environ.copy()
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        environment[variable] = "24"
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=r354.ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    pools = json.loads(completed.stdout)

    assert pools
    assert all(pool["num_threads"] == 1 for pool in pools)


def test_rehearsal_and_prepare_are_create_only_for_recovery(tmp_path) -> None:
    """The formal pre-attempt path must bind the repair without creating a result."""

    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"
    formal_out = tmp_path / "formal"

    r354.rehearsal(rehearsal_path, out_dir=formal_out)
    rehearsal = json.loads(rehearsal_path.read_text(encoding="utf-8"))
    assert rehearsal["development_pair_count"] == 16
    assert rehearsal["holdout_pair_count"] == 16
    assert rehearsal["attempt_created"] is False
    assert rehearsal["andes_executed"] is False
    assert not formal_out.exists()
    assert r353.ROUND_ID == "R353"
    assert r353.DEFAULT_OUT.name == "r353_matched_residual_headroom"
    assert r353.build_contract()["round"] == "R353"

    seal_digest = r354.prepare(
        seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert seal["contract"]["recovery"]["parent_round"] == "R353"
    assert seal["parents"]["r353_failure"]["sha256"] == (
        "09e2c55e7c6d7db532135c18333ef7a9ebae349fa6a933384e1a312e2b79b33d"
    )
    loaded, loaded_digest = r354.load_seal(
        seal_path,
        seal_digest,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    assert loaded == seal
    assert loaded_digest == seal_digest
    assert r353.ROUND_ID == "R353"
    assert r353.build_contract()["round"] == "R353"
    with pytest.raises(FileExistsError, match="create-only"):
        r354.prepare(seal_path, rehearsal_path=rehearsal_path, out_dir=formal_out)


def test_recovery_adapter_exposes_no_simulator_or_training_command() -> None:
    parser = r354.build_parser()

    assert parser.parse_args(["rehearsal"]).command == "rehearsal"
    assert parser.parse_args(["prepare"]).command == "prepare"
    assert parser.parse_args(
        ["analyse", "--expected-seal-sha256", "a" * 64]
    ).command == "analyse"
    with pytest.raises(SystemExit):
        parser.parse_args(["train"])
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["analyse", "--expected-seal-sha256", "a" * 64, "--out", "alternate"]
        )
