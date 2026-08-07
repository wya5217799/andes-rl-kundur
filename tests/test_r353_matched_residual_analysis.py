"""Contract tests for the create-only R353 execution adapter."""

from __future__ import annotations

import json

import pytest
from scripts import run_r353_matched_residual_headroom as r353


def test_contract_freezes_matched_local_information_and_blocks_training() -> None:
    contract = r353.build_contract()

    assert contract["round"] == "R353"
    assert contract["inventory"] == {
        "development_pairs": 16,
        "holdout_pairs": 16,
        "primary_records_per_bank": 32,
        "samples_per_trace": 25,
        "joint_arm_included": False,
    }
    assert contract["residual"]["edge_coordinates"] == 3
    assert contract["local_information"]["feature_count_per_edge"] == 13
    assert contract["local_information"]["unrecoverable_startup_samples"] == 2
    assert contract["authorizations"] == {
        "simulation_authorized": False,
        "training_authorized": False,
        "distributed_runtime_authorized": False,
        "eval_authorized": False,
    }


def test_parent_loader_admits_exact_zero_and_selected_local_pairs() -> None:
    development = r353.load_parent_inventory("development")
    holdout = r353.load_parent_inventory("holdout")

    assert len(development) == 16
    assert len(holdout) == 16
    assert all(set(case["arms"]) == {"zero_edge", "selected_local"} for case in development)
    assert all(set(case["arms"]) == {"zero_edge", "selected_local"} for case in holdout)
    assert all(
        case["arms"]["selected_local"]["record"]["candidate_id"] == "kf500_kr0"
        for case in development + holdout
    )
    assert all(
        len(arm["trace"]["rows"]) == 25
        for case in development + holdout
        for arm in case["arms"].values()
    )


def test_adapter_exposes_only_create_only_analysis_commands() -> None:
    parser = r353.build_parser()

    assert parser.parse_args(["rehearsal"]).command == "rehearsal"
    assert parser.parse_args(["prepare"]).command == "prepare"
    assert parser.parse_args(["analyse", "--expected-seal-sha256", "a" * 64]).command == "analyse"
    with pytest.raises(SystemExit):
        parser.parse_args(["train"])


def test_source_and_parent_closure_bind_every_primary_trace_without_joint_data() -> None:
    sources = r353.source_paths(include_rehearsal=False)
    parents = r353.parent_paths()

    assert {
        "plan",
        "adapter",
        "probe",
        "probe_tests",
        "adapter_tests",
    } <= set(sources)
    package_sources = {
        path.relative_to(r353.ROOT / "src/andes_rl_kundur").as_posix()
        for name, path in sources.items()
        if name.startswith("package_")
    }
    assert package_sources == {
        path.relative_to(r353.ROOT / "src/andes_rl_kundur").as_posix()
        for path in (r353.ROOT / "src/andes_rl_kundur").rglob("*.py")
    }
    assert "control/residual_headroom.py" in package_sources
    assert len([name for name in parents if name.startswith("development_trace_")]) == 32
    assert len([name for name in parents if name.startswith("holdout_trace_")]) == 32
    assert all(path.is_file() for path in sources.values())
    assert all(path.is_file() for path in parents.values())
    assert not any("joint" in path.as_posix() for path in parents.values())


def test_rehearsal_and_prepare_are_create_only_and_bind_both_closures(tmp_path) -> None:
    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"
    formal_out = tmp_path / "formal"

    r353.rehearsal(rehearsal_path, out_dir=formal_out)
    rehearsal = json.loads(rehearsal_path.read_text(encoding="utf-8"))
    assert rehearsal["development_pair_count"] == 16
    assert rehearsal["holdout_pair_count"] == 16
    assert rehearsal["formal_output_absent"]
    assert not formal_out.exists()

    seal_digest = r353.prepare(
        seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert seal["sources"]["rehearsal"]["sha256"]
    assert len(seal["parents"]) >= 75
    loaded, loaded_digest = r353.load_seal(
        seal_path,
        seal_digest,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    assert loaded == seal
    assert loaded_digest == seal_digest
    with pytest.raises(FileExistsError, match="create-only"):
        r353.prepare(seal_path, rehearsal_path=rehearsal_path, out_dir=formal_out)
