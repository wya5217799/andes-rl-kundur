from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import run_r337_icems_comparison as adapter


def test_contract_freezes_genuine_matched_comparison_and_excludes_r293_outcomes() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R337"
    assert contract["question"] == "Q-0088"
    assert contract["title"] == (
        "Decoupling-Oriented Coordination of Paralleled VSGs With "
        "Multi-Agent Reinforcement Learning"
    )
    assert contract["title_changed"] is False
    assert contract["seeds"] == [421, 463, 509, 557, 601]
    assert contract["distributed_execution"] == {
        "information": "two_endpoints_per_edge",
        "outputs": 3,
        "runtime_central_aggregation": False,
        "training_only_central_critic": True,
    }
    assert contract["single_actor_execution"] == {
        "information": "joint_20d",
        "outputs": 3,
    }
    assert contract["matched"]["actor_parameter_relative_difference"] < 0.01
    assert contract["excluded_r293_assets"] == [
        "checkpoints",
        "replay_buffers",
        "training_diagnostics",
        "candidate_bank",
        "screen_records",
        "formal_traces",
        "formal_outcomes",
    ]
    assert contract["formal_launch"]["wsl_python_processes"] == 3
    assert contract["formal_launch"]["native_threads_per_process"] == 1


def test_training_seal_uses_r337_identity_new_seeds_and_only_viewed_parent(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "training_seal.json"
    out_root = tmp_path / "training"

    adapter.prepare_training_seal(manifest, out_root)
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert payload["round"] == "R337"
    assert payload["question"] == "Q-0088"
    assert payload["seeds"] == [421, 463, 509, 557, 601]
    assert payload["training"]["checkpoint_count"] == 10
    assert payload["training"]["total_real_andes_steps"] == 45_000
    assert payload["classical_guard"]["classification"] == "CLASSICAL-GUARD-PASS"
    assert payload["sources"]["plan"]["path"] == "memory/rounds/R337/plan.md"
    assert payload["sources"]["r337_adapter"]["path"] == (
        "scripts/run_r337_icems_comparison.py"
    )
    source_paths = {row["path"] for row in payload["sources"].values()}
    assert not any("r293_prior_residual_training" in path for path in source_paths)
    assert not any("r293_fresh_bank" in path for path in source_paths)
    assert not any("r293_formal_evaluation" in path for path in source_paths)


def test_same_path_pre_attempt_checks_cover_sources_parents_runtime_and_absence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed = {
        "version": "2.0.0",
        "sources": {"andes/core/tds.py": "a" * 64},
        "case": {"path": "/installed/kundur_full.xlsx", "sha256": "b" * 64},
    }
    outputs = [tmp_path / "training", tmp_path / "formal_seal.json"]
    monkeypatch.setattr(adapter, "_installed_andes_identity", lambda: installed)
    monkeypatch.setattr(adapter, "_r337_python_process_count", lambda: 2)

    checks = adapter.pre_attempt_checks(output_paths=outputs)

    assert checks["checks"] == {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
    }
    assert checks["installed_andes"] == installed
    assert checks["wsl_python_processes"] == 2
    assert checks["native_threads_per_process"] == 1
    assert "r293_classical_guard_summary" in checks["parent_hashes"]
    assert "r337_adapter" in checks["source_hashes"]

    outputs[0].mkdir()
    with pytest.raises(FileExistsError, match="pre-existing R337 formal asset"):
        adapter.pre_attempt_checks(output_paths=outputs)


def test_rehearsal_is_create_only_and_execute_precheck_rejects_runtime_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed = {
        "version": "2.0.0",
        "sources": {"andes/core/tds.py": "a" * 64},
        "case": {"path": "/installed/kundur_full.xlsx", "sha256": "b" * 64},
    }
    record = tmp_path / "rehearsal.json"
    outputs = [tmp_path / "attempt.json", tmp_path / "formal"]
    monkeypatch.setattr(adapter, "_installed_andes_identity", lambda: installed)
    monkeypatch.setattr(adapter, "_r337_python_process_count", lambda: 2)

    digest = adapter.rehearse(record_path=record, output_paths=outputs)

    assert record.is_file()
    assert record.with_name("rehearsal.json.sha256").read_text(
        encoding="utf-8"
    ).split()[0] == digest
    assert not any(path.exists() for path in outputs)
    adapter.verify_rehearsal(record_path=record, output_paths=outputs)

    drifted = {**installed, "version": "2.0.1"}
    monkeypatch.setattr(adapter, "_installed_andes_identity", lambda: drifted)
    with pytest.raises(ValueError, match="rehearsal drift: installed_andes"):
        adapter.verify_rehearsal(record_path=record, output_paths=outputs)


def test_stage_contract_routes_every_new_learned_and_formal_asset_to_r337() -> None:
    stages = adapter.build_stage_contract()

    assert stages["training"] == {
        "seal": "memory/rounds/R337/training_seal.json",
        "out": "results/r337_prior_residual_training",
        "run_count": 10,
    }
    assert stages["fresh_bank"] == {
        "seal": "memory/rounds/R337/fresh_bank_screen_seal.json",
        "out": "results/r337_fresh_bank",
        "candidate_seed": 2026080401,
        "scenario_count": 24,
    }
    assert stages["formal"] == {
        "seal": "memory/rounds/R337/formal_seal.json",
        "out": "results/r337_formal_evaluation",
        "arm_count": 12,
        "matrix_count": 288,
        "bootstrap_seed": 2026080402,
    }
    assert stages["viewed_parent_only"] == {
        "classical_guard_summary": (
            "results/r293_classical_guard/classical_guard_summary.json"
        ),
        "classical_guard_provenance": (
            "results/r293_classical_guard/provenance.json"
        ),
    }
    assert stages["execution"] == {
        "serial_in_one_formal_child": True,
        "maximum_r337_wsl_python_processes": 3,
        "native_threads_per_process": 1,
        "automatic_retry": False,
    }


def test_formal_cli_bootstraps_outside_repo_and_exposes_only_frozen_commands(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(adapter.__file__).resolve()), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "rehearse" in completed.stdout
    assert "execute" in completed.stdout
    assert "resume" not in completed.stdout
