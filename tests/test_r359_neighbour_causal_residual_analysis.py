"""Contract tests for the create-only R359 execution adapter."""

from __future__ import annotations

import json

import pytest
from scripts import run_r359_neighbour_causal_residual as r359


def test_contract_freezes_exact_information_and_blocks_learning() -> None:
    contract = r359.build_contract()

    assert contract["round"] == "R359"
    assert contract["information"] == {
        "edge_actor_count": 3,
        "continuous_fields_per_actor": 15,
        "startup_zero_steps": 2,
        "forbidden_fields": [
            "achieved_power",
            "operating_point",
            "disturbance_channel",
            "disturbance_sign",
            "scenario_identity",
            "other_edge_observations",
            "future_values",
            "realized_endpoints",
            "oracle_values",
        ],
    }
    assert contract["authorizations"] == {
        "simulation_authorized": False,
        "training_authorized": False,
        "distributed_runtime_authorized": False,
        "eval_authorized": False,
    }


def test_adapter_exposes_only_staged_create_only_commands() -> None:
    parser = r359.build_parser()

    assert parser.parse_args(["rehearsal"]).command == "rehearsal"
    assert parser.parse_args(["prepare"]).command == "prepare"
    assert parser.parse_args(["analyse", "--expected-seal-sha256", "a" * 64]).command == "analyse"
    with pytest.raises(SystemExit):
        parser.parse_args(["train"])


def test_source_and_parent_closure_bind_exact_r352_r358_inputs() -> None:
    sources = r359.source_paths(include_rehearsal=False)
    parents = r359.parent_paths()

    assert {
        "plan",
        "question",
        "capacity",
        "adapter",
        "probe",
        "probe_tests",
        "adapter_tests",
    } <= set(sources)
    assert {"r358_analysis", "r358_manifest", "r358_seal", "r358_claim"} <= set(parents)
    assert len([name for name in parents if name.startswith("development_trace_")]) == 32
    assert len([name for name in parents if name.startswith("holdout_trace_")]) == 32
    assert all(path.is_file() for path in sources.values())
    assert all(path.is_file() for path in parents.values())


def test_rehearsal_and_prepare_are_create_only_and_do_not_read_holdout_labels(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"
    formal_out = tmp_path / "formal"
    active_plan = tmp_path / "plan.md"
    active_question = tmp_path / "question.md"
    active_plan.write_text("---\nstate: active\n---\n", encoding="utf-8")
    active_question.write_text(
        "---\nstatus: in-flight\n---\nR359:\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(r359, "PLAN", active_plan)
    monkeypatch.setattr(r359, "QUESTION", active_question)

    r359.rehearsal(rehearsal_path, out_dir=formal_out)
    rehearsal = json.loads(rehearsal_path.read_text(encoding="utf-8"))
    assert rehearsal["development_pair_count"] == 16
    assert rehearsal["holdout_pair_count"] == 16
    assert rehearsal["development_target_partition"] == {"positive": 10, "zero": 6}
    assert rehearsal["holdout_residual_labels_read"] == 0
    assert rehearsal["formal_output_absent"] is True
    assert not formal_out.exists()

    digest = r359.prepare(
        seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert seal["sources"]["rehearsal"]["sha256"]
    assert seal["retry_authorized"] is False
    loaded, loaded_digest = r359.load_seal(
        seal_path,
        digest,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    assert loaded == seal
    assert loaded_digest == digest
