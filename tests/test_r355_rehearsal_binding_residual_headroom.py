"""Regression tests for the R355 inherited rehearsal-path binding."""

from __future__ import annotations

import json

import pytest
from scripts import run_r354_certificate_compatible_residual_headroom as r354
from scripts import run_r355_rehearsal_binding_residual_headroom as r355


def test_contract_changes_only_identity_and_invocation_recovery_metadata() -> None:
    """R355 must preserve every scientific and execution field from R354."""

    inherited = r354.build_contract()
    recovery = r355.build_contract()

    for key in (
        "inventory",
        "residual",
        "local_information",
        "statistics",
        "execution",
        "decision",
        "authorizations",
        "resource_budget",
    ):
        assert recovery[key] == inherited[key]
    assert recovery["round"] == "R355"
    assert recovery["question"] == inherited["question"]
    assert recovery["recovery"]["parent_round"] == "R354"
    assert recovery["recovery"]["authorized_change"] == (
        "load-seal-rehearsal-path-binding-only"
    )
    assert recovery["recovery"]["inherited_certificate_recovery"] == (
        inherited["recovery"]
    )


def test_predecessor_closure_binds_sealed_pre_attempt_failure() -> None:
    """R355 must fail closed if any R354 predecessor identity changes."""

    r355._verify_predecessor_inputs()
    assert not r355.R354_OUT.exists()
    assert {"r354_rehearsal", "r354_seal"} <= set(r355.parent_paths())
    assert {
        "plan",
        "adapter",
        "invocation_tests",
        "r354_closed_plan",
        "r354_adapter",
        "r354_probe",
        "r354_tests",
    } <= set(r355.source_paths(include_rehearsal=False))


def test_implicit_inherited_seal_load_uses_current_rehearsal(tmp_path) -> None:
    """Exercise the exact seam that rejected R354 before an attempt existed."""

    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"
    formal_out = tmp_path / "formal"

    r355.rehearsal(rehearsal_path, out_dir=formal_out)
    seal_digest = r355.prepare(
        seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    with r355._predecessor_runtime(
        seal_path=seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    ):
        with r354._parent_runtime():
            loaded, loaded_digest = r355.parent.load_seal(
                seal_path,
                seal_digest,
                out_dir=formal_out,
            )

    assert loaded["round"] == "R355"
    assert loaded["sources"]["rehearsal"]["path"].endswith("rehearsal.json")
    assert loaded_digest == seal_digest
    assert not formal_out.exists()
    assert r354.ROUND_ID == "R354"
    assert r355.parent.load_seal is r355._PARENT_LOAD_SEAL


def test_formal_rehearsal_command_exercises_implicit_loader_seam(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The official rehearsal itself must call the seam that rejected R354."""

    calls: list[object] = []
    inherited = r355._PARENT_LOAD_SEAL

    def recording_loader(*args, **kwargs):
        calls.append(kwargs.get("rehearsal_path"))
        return inherited(*args, **kwargs)

    monkeypatch.setattr(r355, "_PARENT_LOAD_SEAL", recording_loader)
    record_path = tmp_path / "rehearsal.json"
    formal_out = tmp_path / "formal"

    r355.rehearsal(record_path, out_dir=formal_out)

    assert calls == [record_path]
    assert not formal_out.exists()


def test_rehearsal_prepare_and_loader_are_create_only(tmp_path) -> None:
    """No corrected pre-attempt operation may create or overwrite a result."""

    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"
    formal_out = tmp_path / "formal"

    r355.rehearsal(rehearsal_path, out_dir=formal_out)
    rehearsal = json.loads(rehearsal_path.read_text(encoding="utf-8"))
    assert rehearsal["development_pair_count"] == 16
    assert rehearsal["holdout_pair_count"] == 16
    assert rehearsal["attempt_created"] is False
    assert rehearsal["andes_executed"] is False
    assert rehearsal["training_executed"] is False
    seal_digest = r355.prepare(
        seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    loaded, loaded_digest = r355.load_seal(
        seal_path,
        seal_digest,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    assert loaded["contract"]["resource_budget"]["native_threads_per_process"] == 1
    assert loaded_digest == seal_digest
    assert not formal_out.exists()
    with pytest.raises(FileExistsError, match="create-only"):
        r355.prepare(
            seal_path,
            rehearsal_path=rehearsal_path,
            out_dir=formal_out,
        )


def test_cli_exposes_no_training_simulation_or_alternate_output() -> None:
    """Only the canonical create-only analysis entry is exposed."""

    parser = r355.build_parser()
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
