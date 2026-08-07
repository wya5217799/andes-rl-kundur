from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from scripts import run_r342_limited_reverse_residual as adapter
from scripts import train_r293_prior_residual as training


def test_training_contract_round_trip_preserves_reverse_limit() -> None:
    restored = training._contract_from_telemetry(
        {
            "family": "full",
            "gain": 1.0,
            "residual_scale": 0.5,
            "reverse_limit": 0.1,
        }
    )

    assert restored.family == "full"
    assert restored.gain == 1.0
    assert restored.residual_scale == 0.5
    assert restored.reverse_limit == 0.1
    assert restored.name == "classical_edge_full_k1_b0p1"


def test_training_contract_round_trip_keeps_legacy_default() -> None:
    restored = training._contract_from_telemetry(
        {"family": "full", "gain": 1.0, "residual_scale": 0.5}
    )

    assert restored.reverse_limit == 0.0
    assert restored.name == "classical_edge_full_k1"


def test_single_architecture_matrix_budget_is_derived_not_hard_coded(
    monkeypatch,
) -> None:
    monkeypatch.setattr(training, "ARCHITECTURES", ("distributed_prior",))
    monkeypatch.setattr(training, "SEEDS", (421, 463, 509, 557, 601))

    budget = training._training_budget()

    assert budget["checkpoint_count"] == 5
    assert budget["steps_per_checkpoint"] == 4_500
    assert budget["total_real_andes_steps"] == 22_500
    assert training._expected_actor_counts() == {"distributed_prior": 4_929}


def test_r342_contract_changes_only_reverse_limit() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R342"
    assert contract["title_changed"] is False
    assert contract["beta_zero"] == 0.0
    assert contract["beta_candidate"] == 0.1
    assert contract["residual_scale"] == 0.5
    assert contract["seeds"] == [421, 463, 509, 557, 601]
    assert contract["new_training_steps"] == 22_500


def test_r342_training_seal_has_five_beta_point_one_checkpoints(
    tmp_path: Path,
) -> None:
    seal = tmp_path / "training_seal.json"
    out_root = tmp_path / "training"

    adapter.prepare_training_seal(seal, out_root)
    payload = json.loads(seal.read_text(encoding="utf-8"))

    assert payload["round"] == "R342"
    assert payload["architectures"] == ["distributed_prior"]
    assert payload["seeds"] == [421, 463, 509, 557, 601]
    assert payload["training"]["checkpoint_count"] == 5
    assert payload["training"]["total_real_andes_steps"] == 22_500
    action = payload["action_and_reward"]
    assert action["residual_scale"] == 0.5
    assert action["reverse_limit"] == 0.1
    assert action["classical_prior"]["name"] == "classical_edge_full_k1_b0p1"


def test_r342_training_jobs_are_exactly_one_per_seed() -> None:
    jobs = adapter.training_jobs()

    assert len(jobs) == 5
    assert {job["seed"] for job in jobs} == {421, 463, 509, 557, 601}
    assert {job["architecture"] for job in jobs} == {"distributed_prior"}
    assert all(job["native_threads"] == 1 for job in jobs)


def _mock_rehearsal_inputs(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("source\n", encoding="utf-8")
    parent = tmp_path / "parent.json"
    parent.write_text("{}\n", encoding="utf-8")
    digest = hashlib.sha256(parent.read_bytes()).hexdigest()
    parent.with_name(parent.name + ".sha256").write_text(
        f"{digest}  {parent.name}\n", encoding="utf-8"
    )
    monkeypatch.setattr(adapter, "_source_paths", lambda: {"source": source})
    monkeypatch.setattr(adapter, "_parent_paths", lambda: {"parent": parent})
    monkeypatch.setattr(
        adapter,
        "_installed_andes_identity",
        lambda: {
            "version": "test",
            "sources": {"package": "abc"},
            "case": {"sha256": "def"},
        },
    )
    monkeypatch.setattr(adapter, "_r342_python_process_count", lambda: 1)
    for name in adapter.THREAD_ENVIRONMENT:
        monkeypatch.setenv(name, "1")


def test_rehearsal_uses_same_checks_without_creating_outputs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _mock_rehearsal_inputs(monkeypatch, tmp_path)
    record = tmp_path / "rehearsal.json"
    formal_output = tmp_path / "formal-output"

    adapter.rehearse(record_path=record, output_paths=[formal_output])
    payload = json.loads(record.read_text(encoding="utf-8"))

    assert payload["round"] == "R342"
    assert all(payload["checks"].values())
    assert payload["formal_attempt_created"] is False
    assert payload["formal_outputs_created"] is False
    assert not formal_output.exists()
    current = adapter.verify_rehearsal(
        record_path=record,
        output_paths=[formal_output],
    )
    assert current["checks"] == payload["checks"]


def test_rehearsal_blocks_any_preexisting_output(monkeypatch, tmp_path: Path) -> None:
    _mock_rehearsal_inputs(monkeypatch, tmp_path)
    existing = tmp_path / "training"
    existing.mkdir()

    with pytest.raises(FileExistsError, match="pre-existing R342"):
        adapter.pre_attempt_checks(output_paths=[existing])


def test_rehearsal_source_set_does_not_hash_its_own_future_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.py"
    source.write_text("source\n", encoding="utf-8")
    rehearsal = tmp_path / "rehearsal.json"
    rehearsal.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        adapter,
        "_training_source_paths",
        lambda: {"source": source, "rehearsal_record": rehearsal},
    )

    assert "rehearsal_record" not in adapter._source_paths()


def _write_hashed_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )


def test_training_worker_mapping_is_exact_and_rejects_wrong_shard_count() -> None:
    assert [adapter.training_job_for_shard(index, 5)["seed"] for index in range(5)] == [
        421,
        463,
        509,
        557,
        601,
    ]
    with pytest.raises(ValueError, match="exactly five"):
        adapter.training_job_for_shard(0, 4)


def test_training_smoke_gate_requires_five_valid_overlapping_receipts(
    tmp_path: Path,
) -> None:
    out_root = tmp_path / "training"
    for index, seed in enumerate((421, 463, 509, 557, 601)):
        _write_hashed_json(
            out_root / "smoke_receipts" / f"worker_{index}.json",
            {
                "round": "R342",
                "seed": seed,
                "shard_index": index,
                "shard_count": 5,
                "smoke_episodes": 1,
                "started_ns": index,
                "finished_ns": 10 + index,
                "return_code": 0,
            },
        )
        _write_hashed_json(
            out_root
            / "smoke"
            / f"distributed_prior_s{seed}_e1"
            / "training_summary.json",
            {
                "round": "R342",
                "architecture": "distributed_prior",
                "seed": seed,
                "episodes_completed": 1,
                "total_steps": 15,
                "smoke": True,
                "failed": False,
                "all_completed": True,
            },
        )

    digest = adapter.verify_training_smoke(out_root)
    gate = json.loads((out_root / "smoke_gate.json").read_text(encoding="utf-8"))

    assert len(digest) == 64
    assert gate["classification"] == "PASS"
    assert gate["worker_count"] == 5
    assert gate["all_workers_overlapped"] is True
    assert gate["performance_use"] == "forbidden"
    assert gate["timing"]["maximum_worker_seconds"] > 0
    assert gate["timing"]["observed_parallel_wall_seconds"] > 0
    assert gate["timing"]["estimated_full_training_wall_seconds"] > 0


def test_fresh_bank_contract_is_new_single_draw_and_sixteen_shards() -> None:
    contract = adapter.build_fresh_bank_contract()

    assert contract["round"] == "R342"
    assert contract["candidate_seed"] == 2026080601
    assert contract["scenario_count"] == 24
    assert contract["shard_count"] == 16
    assert contract["redraw_after_failure"] is False
    assert contract["controller"] == "q0"


def test_fresh_bank_training_gate_requires_exactly_five_new_checkpoints() -> None:
    valid = {
        "round": "R342",
        "all_completed": True,
        "expected_run_count": 5,
        "observed_run_count": 5,
        "seed_selection_performed": False,
        "artifact_hashes": {},
    }

    adapter._verify_r342_training(valid)
    invalid = {**valid, "observed_run_count": 4}
    with pytest.raises(ValueError, match="five completed"):
        adapter._verify_r342_training(invalid)


def test_fresh_bank_configuration_routes_only_r342_outputs() -> None:
    with adapter._configured_fresh() as fresh:
        assert fresh.ROUND_ID == "R342"
        assert fresh.CANDIDATE_SEED == 2026080601
        assert fresh.SHARD_COUNT == 16
        assert fresh.DEFAULT_SEAL == adapter.FRESH_SEAL
        assert fresh.DEFAULT_OUT == adapter.FRESH_OUT
        assert fresh.FORMAL_TRACE_DIR == adapter.FORMAL_OUT / "traces"


def test_formal_contract_has_twelve_causal_arms_and_264_new_traces() -> None:
    contract = adapter.build_formal_contract()
    arms = contract["arms"]

    assert arms[:2] == ["q0", "classical_edge"]
    assert arms[2:7] == [f"beta0_s{seed}" for seed in (421, 463, 509, 557, 601)]
    assert arms[7:] == [f"beta0p1_s{seed}" for seed in (421, 463, 509, 557, 601)]
    assert contract["arm_count"] == 12
    assert contract["new_controller_trajectory_budget"] == 264
    assert contract["reused_q0_trajectory_count"] == 24
    assert contract["shard_count"] == 16
    assert contract["bootstrap_seed"] == 2026080602


def test_formal_checkpoint_routes_beta_zero_to_parent_and_candidate_to_r342() -> None:
    assert adapter._formal_checkpoint_path("beta0", 421) == (
        adapter.ROOT
        / "results/r337_prior_residual_training/distributed_prior_s421/final.pt"
    )
    assert adapter._formal_checkpoint_path("beta0p1", 421) == (
        adapter.TRAINING_OUT / "distributed_prior_s421/final.pt"
    )
    with pytest.raises(ValueError, match="unknown learned family"):
        adapter._formal_checkpoint_path("other", 421)


def test_formal_configuration_routes_new_bank_and_custom_arm_loader() -> None:
    with adapter._configured_formal() as formal:
        assert formal.ROUND_ID == "R342"
        assert formal.ARMS == tuple(adapter.formal_arms())
        assert formal.NEW_TRACE_ARMS == tuple(adapter.formal_arms()[1:])
        assert formal.SHARD_COUNT == 16
        assert formal.FORMAL_BANK == adapter.FRESH_OUT / "formal_bank.json"
        assert formal.DEFAULT_SEAL == adapter.FORMAL_SEAL
        assert formal.DEFAULT_OUT == adapter.FORMAL_OUT
        assert formal._make_controller is adapter._make_r342_controller
        assert formal.PHASE == "fresh-bank-limited-reversal-formal"
        assert formal.EXPERIMENT == "r342_limited_reverse_residual"
        assert formal.ALLOW_EXISTING_TRACE_RESUME is False


def test_mechanism_engagement_counts_only_beta_point_one_reverse_steps() -> None:
    records = {
        "beta0_s421": [
            {"traces": [{"residual_composition": {"reverse_count": 0}}]}
        ],
        "beta0p1_s421": [
            {
                "traces": [
                    {
                        "residual_composition": {
                            "reverse_count": 2,
                            "reverse_limit": 0.1,
                        }
                    },
                    {
                        "residual_composition": {
                            "reverse_count": 0,
                            "reverse_limit": 0.1,
                        }
                    },
                ]
            }
        ],
    }

    engagement = adapter._mechanism_engagement(records)

    assert engagement["reverse_command_count"] == 2
    assert engagement["steps_with_reverse"] == 1
    assert engagement["engaged"] is True


def test_seed_directionality_counts_both_comparisons_on_both_endpoints() -> None:
    bank_names = ["case_a", "case_b"]
    grid: dict[str, dict[str, dict[str, float]]] = {}
    for name in bank_names:
        grid[name] = {
            "classical_edge": {
                "normalized_sync_loss_hz2": 10.0,
                "fast_inter_area_iae_hz_s": 10.0,
            }
        }
        for seed in (421, 463, 509, 557, 601):
            grid[name][f"beta0_s{seed}"] = {
                "normalized_sync_loss_hz2": 9.0,
                "fast_inter_area_iae_hz_s": 9.0,
            }
            grid[name][f"beta0p1_s{seed}"] = {
                "normalized_sync_loss_hz2": 8.0,
                "fast_inter_area_iae_hz_s": 8.0,
            }

    classical_count, beta0_count, rows = adapter._seed_directionality(
        grid,
        bank_names,
    )

    assert classical_count == 5
    assert beta0_count == 5
    assert len(rows) == 5


def test_physical_canary_contract_uses_all_sixteen_budgeted_workers() -> None:
    contract = adapter.build_physical_canary_contract()

    assert contract["worker_count"] == 16
    assert contract["steps_per_worker"] == 15
    assert contract["task_count"] == 16
    assert len({(row["scenario_index"], row["arm"]) for row in contract["tasks"]}) == 16
    assert contract["performance_use"] == "forbidden"
    assert contract["automatic_formal_release"] is False


def test_formal_release_requires_hashed_matching_canary_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate = tmp_path / "canary_gate.json"
    _write_hashed_json(
        gate,
        {
            "round": "R342",
            "classification": "PASS",
            "formal_seal_sha256": "seal123",
            "worker_count": 16,
            "automatic_formal_release": False,
        },
    )
    monkeypatch.setattr(adapter, "CANARY_GATE", gate)

    adapter._require_canary_pass("seal123")
    with pytest.raises(ValueError, match="different formal seal"):
        adapter._require_canary_pass("other")


def test_execution_stage_plan_is_small_step_and_uses_frozen_parallelism() -> None:
    plan = adapter.build_execution_stage_plan()

    assert [stage["name"] for stage in plan["stages"]] == [
        "training-smoke",
        "full-training",
        "fresh-bank-screen",
        "physical-canary",
    ]
    assert [stage["workers"] for stage in plan["stages"]] == [5, 5, 16, 16]
    assert plan["release_points"] == ["training-smoke", "physical-canary"]
    assert plan["initial_stop_after"] == "training-smoke"
    assert plan["automatic_formal_release"] is False
    assert plan["automatic_full_training_release"] is False
    assert plan["full_formal_workers_after_release"] == 16


def test_cli_exposes_each_manual_release_boundary() -> None:
    parser = adapter._parser()

    assert parser.parse_args(["execute"]).command == "execute"
    assert (
        parser.parse_args(["continue-through-canary"]).command
        == "continue-through-canary"
    )
    assert parser.parse_args(["execute-formal"]).command == "execute-formal"
    assert parser.parse_args(["verify-rehearsal"]).command == "verify-rehearsal"
    assert parser.parse_args(["verify-training"]).command == "verify-training"
