"""Windows-safe tests for successor config and completed-cell recovery."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from andes_rl_kundur.training.adaptive_stop import AdaptiveStopConfig
from andes_rl_kundur.training.adaptive_u2 import config_sha256, sha256_file

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "_test_adaptive_successor", ROOT / "scripts/run_adaptive_u2_successor.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import adaptive successor runner")
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _write_artifact(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def test_load_config_rejects_duplicate_cells(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr(
        runner,
        "_repo_path",
        lambda value: Path(value) if Path(value).is_absolute() else ROOT / Path(value),
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "round": "R483",
                "source_round": "R482",
                "out": "tmp/andes/r999_out",
                "source_out": "results/research_loop/r482_u2_confirmatory",
                "seal": "memory/rounds/R999/formal_seal.json",
                "power": "memory/rounds/R999/power.json",
                "probe_bank": "memory/rounds/R999/probe.npz",
                "probe_bank_sha256": "x",
                "stop_config": {},
                "recovery_policy": runner.RECOVERY_POLICY,
                "execution": {
                    "workers": 16,
                    "train_log_dir": "tmp/andes/r483_train_logs",
                    "eval_log_dir": "tmp/andes/r483_eval_logs",
                },
                "authority": {
                    "plan": "memory/rounds/R483/plan.md",
                    "owner_approval": "memory/rounds/R483/OWNER_APPROVED.json",
                    "routing_gate": "memory/rounds/R483/routing_gate.json",
                    "rehearsal": "memory/rounds/R483/rehearsal.json",
                    "capacity": "memory/rounds/R483/capacity.json",
                    "review_a": "memory/rounds/R483/review_a.json",
                    "review_b": "memory/rounds/R483/review_b.json",
                    "train_shard_list": "tmp/andes/r999_train_shards.json",
                    "eval_shard_list": "tmp/andes/r999_eval_shards.json",
                },
                "cells": [
                    {"arm_id": "an_cn_r1", "seed": 7},
                    {"arm_id": "an_cn_r1", "seed": 7},
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        runner.load_config(config)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate adaptive cells should fail closed")


def test_load_config_rejects_unbalanced_arm_seed_roster(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(
        runner,
        "_repo_path",
        lambda value: Path(value) if Path(value).is_absolute() else ROOT / Path(value),
    )
    base = {
        "schema_version": 2,
        "round": "R483",
        "source_round": "R482",
        "out": "tmp/andes/r999_out",
        "source_out": "results/research_loop/r482_u2_confirmatory",
        "seal": "memory/rounds/R999/formal_seal.json",
        "power": "memory/rounds/R999/power.json",
        "probe_bank": "memory/rounds/R999/probe.npz",
        "probe_bank_sha256": "x",
        "stop_config": {},
        "recovery_policy": runner.RECOVERY_POLICY,
        "execution": {
            "workers": 16,
            "train_log_dir": "tmp/andes/r483_train_logs",
            "eval_log_dir": "tmp/andes/r483_eval_logs",
        },
        "authority": {
            "plan": "memory/rounds/R483/plan.md",
            "owner_approval": "memory/rounds/R483/OWNER_APPROVED.json",
            "routing_gate": "memory/rounds/R483/routing_gate.json",
            "rehearsal": "memory/rounds/R483/rehearsal.json",
            "capacity": "memory/rounds/R483/capacity.json",
            "review_a": "memory/rounds/R483/review_a.json",
            "review_b": "memory/rounds/R483/review_b.json",
            "train_shard_list": "tmp/andes/r999_train_shards.json",
            "eval_shard_list": "tmp/andes/r999_eval_shards.json",
        },
        "cells": [
            {"arm_id": "an_cn_r0", "seed": 1},
            {"arm_id": "an_cn_r0", "seed": 2},
            {"arm_id": "an_cn_r1", "seed": 1},
        ],
    }
    path = tmp_path / "unbalanced.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    try:
        runner.load_config(path)
    except ValueError as exc:
        assert "balanced" in str(exc)
    else:
        raise AssertionError("unbalanced adaptive roster should fail closed")


def test_r483_config_rejects_changed_stop_policy(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(
        runner,
        "_repo_path",
        lambda value: Path(value) if Path(value).is_absolute() else ROOT / Path(value),
    )
    payload = {
        "schema_version": 2,
        "round": "R483",
        "source_round": "R482",
        "out": "results/research_loop/r483_adaptive_u2",
        "source_out": "results/research_loop/r482_u2_confirmatory",
        "seal": "memory/rounds/R483/formal_seal.json",
        "power": "paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json",
        "probe_bank": "memory/rounds/R483/probe_bank.npz",
        "probe_bank_sha256": "probe",
        "stop_config": {"max_steps": 40_000},
        "recovery_policy": runner.RECOVERY_POLICY,
        "execution": {
            "workers": 16,
            "train_log_dir": "tmp/andes/r483_train_logs",
            "eval_log_dir": "tmp/andes/r483_eval_logs",
        },
        "authority": {
            "plan": "memory/rounds/R483/plan.md",
            "owner_approval": "memory/rounds/R483/OWNER_APPROVED.json",
            "routing_gate": "memory/rounds/R483/routing_gate.json",
            "rehearsal": "memory/rounds/R483/rehearsal.json",
            "capacity": "memory/rounds/R483/capacity.json",
            "review_a": "memory/rounds/R483/review_a.json",
            "review_b": "memory/rounds/R483/review_b.json",
            "train_shard_list": "tmp/andes/r483_train_shards.json",
            "eval_shard_list": "tmp/andes/r483_eval_shards.json",
        },
        "cells": [
            {"arm_id": arm, "seed": seed}
            for arm in runner.FACTORIAL_ARMS
            for seed in runner.SEEDS
        ],
    }
    path = tmp_path / "changed-policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        runner.load_config(path)
    except ValueError as exc:
        assert "frozen R483 policy" in str(exc)
    else:
        raise AssertionError("changed R483 stop policy must fail closed")


def test_resume_accepts_only_a_complete_hash_valid_cell(tmp_path: Path) -> None:
    stop = AdaptiveStopConfig()
    config = {
        "round": "R999",
        "_out": tmp_path / "out",
        "probe_bank_sha256": "probe-sha",
        "_stop": stop,
    }
    folder = tmp_path / "out/train/an_cn_r1/seed7"
    hashes = {
        "half_checkpoint_sha256": _write_artifact(folder / "half.pt", "half"),
        "final_checkpoint_sha256": _write_artifact(folder / "final.pt", "final"),
        "full_curves_sha256": _write_artifact(folder / "full_curves.npz", "curves"),
        "adaptive_trace_sha256": _write_artifact(folder / "adaptive_trace.json", "trace"),
    }
    manifest = folder / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "round": "R999",
                "source_round": "R482",
                "arm_id": "an_cn_r1",
                "training_seed": 7,
                "training_mode": "adaptive_stop_v1",
                "valid": True,
                "stop_config_sha256": config_sha256(stop),
                "probe_bank_sha256": "probe-sha",
                "interaction_steps": 34_000,
                "stop_reason": "converged",
                "converged": True,
                **hashes,
            }
        ),
        encoding="utf-8",
    )
    digest = sha256_file(manifest)
    Path(f"{manifest}.sha256").write_text(f"{digest}  manifest.json\n", encoding="ascii")
    assert runner._validate_completed(config, "an_cn_r1", 7) == digest

    (folder / "final.pt").write_text("damaged", encoding="utf-8")
    try:
        runner._validate_completed(config, "an_cn_r1", 7)
    except RuntimeError as exc:
        assert "artifact mismatch" in str(exc)
    else:
        raise AssertionError("resume must reject a damaged completed cell")


def test_seal_inputs_cannot_self_declare_formal_authority(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(runner, "_source_base_inventory", lambda config: {})
    monkeypatch.setattr(runner, "_preseal_authority", lambda config: {})
    config_file = tmp_path / "config.json"
    config_file.write_text("{}", encoding="utf-8")
    config = {
        "round": "R999",
        "probe_bank_sha256": "probe-sha",
        "_path": config_file,
        "_stop": AdaptiveStopConfig(),
        "_cells": (("an_cn_r1", 7),),
    }
    fragment = runner.seal_inputs(config)
    assert fragment["seal_fragment_only"] is True
    assert "formal_authority" not in fragment


def test_nonterminal_or_malformed_r482_blocks_successor_preseal_setup(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        runner,
        "_round_state",
        lambda path: "active" if path == runner.SOURCE_PLAN else "completed",
    )
    config = {"authority": {"plan": Path("unused"), "owner_approval": Path("unused")}}
    try:
        runner._preseal_authority(config)
    except RuntimeError as exc:
        assert "not in a recognized terminal state" in str(exc)
    else:
        raise AssertionError("active source round must block successor setup")

    monkeypatch.setattr(runner, "_round_state", lambda path: None)
    try:
        runner._preseal_authority(config)
    except RuntimeError as exc:
        assert "None" in str(exc)
    else:
        raise AssertionError("malformed source round state must fail closed")


def test_source_base_must_match_r482_frozen_audit() -> None:
    audit = {
        "bases": {
            "7": {
                "path": "results/source/seed7/base.pt",
                "sha256": "frozen-sha",
            }
        }
    }
    runner._verify_base_audit_entry(
        audit,
        seed=7,
        base_path="results/source/seed7/base.pt",
        base_sha256="frozen-sha",
    )
    try:
        runner._verify_base_audit_entry(
            audit,
            seed=7,
            base_path="results/source/seed7/base.pt",
            base_sha256="substituted-sha",
        )
    except RuntimeError as exc:
        assert "contradicts" in str(exc)
    else:
        raise AssertionError("pre-seal base substitution must fail closed")


def test_source_audit_must_match_r482_formal_seal() -> None:
    runner._verify_source_audit_anchor(
        {"round": "R482", "formal_authority": True, "base_audit_sha256": "frozen"},
        "frozen",
    )
    try:
        runner._verify_source_audit_anchor(
            {
                "round": "R482",
                "formal_authority": True,
                "base_audit_sha256": "original",
            },
            "substituted",
        )
    except RuntimeError as exc:
        assert "not anchored" in str(exc)
    else:
        raise AssertionError("replaced audit must contradict the R482 formal seal")


def test_runtime_contract_uses_successor_roster_and_power() -> None:
    runtime = runner._load_runtime()
    config = {
        "round": "R999",
        "_out": ROOT / "tmp/andes/r999_out",
        "_power": ROOT / "paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json",
        "_cells": (("an_cn_r1", 507),),
        "_stop": AdaptiveStopConfig(),
        "probe_bank_sha256": "probe-sha",
        "recovery_policy": runner.RECOVERY_POLICY,
    }
    runner.bind_runtime(runtime, config)
    contract = runtime.build_contract()["adaptive_u2"]
    assert contract["retrain_cells"] == ["train|an_cn_r1|507"]
    assert contract["fresh_seed_roster"] == [507]
    assert contract["power_plan_sha256"] == sha256_file(config["_power"])
    assert contract["fixed_budget_cells_pooled_as_adaptive"] is False


def test_train_and_evaluation_shards_cover_balanced_roster() -> None:
    config = {
        "_cells": (
            ("an_cn_r0", 1),
            ("an_cn_r0", 2),
            ("an_cn_r1", 1),
            ("an_cn_r1", 2),
        )
    }
    assert runner.train_shard_ids(config) == [
        "train|an_cn_r0|1",
        "train|an_cn_r0|2",
        "train|an_cn_r1|1",
        "train|an_cn_r1|2",
    ]
    assert runner.evaluation_shard_ids(config) == [
        "eval|an_cn_r0|half",
        "eval|an_cn_r1|half",
        "eval|an_cn_r0|final",
        "eval|an_cn_r1|final",
    ]


def test_resume_allows_abrupt_partial_but_blocks_retained_failure(
    tmp_path: Path,
) -> None:
    config = {"_out": tmp_path / "out"}
    attempt = config["_out"] / "recovery_attempts/an_cn_r1/seed7/attempt1"
    attempt.mkdir(parents=True)
    (attempt / "half.pt").write_text("abrupt power loss", encoding="utf-8")
    try:
        runner._assert_recoverable_attempts(config, "an_cn_r1", 7, resume=False)
    except RuntimeError as exc:
        assert "authorized resume" in str(exc)
    else:
        raise AssertionError("partial attempt must not be silently ignored")
    runner._assert_recoverable_attempts(config, "an_cn_r1", 7, resume=True)

    (attempt / "initialization_failure.json").write_text("{}", encoding="utf-8")
    try:
        runner._assert_recoverable_attempts(config, "an_cn_r1", 7, resume=True)
    except RuntimeError as exc:
        assert "forbids retry" in str(exc)
    else:
        raise AssertionError("retained scientific/code failure must not be retried")


def test_evaluation_resume_allows_only_abrupt_partial(tmp_path: Path) -> None:
    config = {"_out": tmp_path / "out"}
    attempt = config["_out"] / "evaluation_attempts/final/an_cn_r0/attempt1"
    (attempt / "payload/seed501").mkdir(parents=True)
    (attempt / "payload/seed501/partial.json").write_text("{}", encoding="utf-8")
    try:
        runner._assert_evaluation_recoverable(
            config, "an_cn_r0", "final", resume=False
        )
    except RuntimeError as exc:
        assert "require resume" in str(exc)
    else:
        raise AssertionError("evaluation partial must require explicit resume")
    runner._assert_evaluation_recoverable(config, "an_cn_r0", "final", resume=True)
    (attempt / "evaluation_failure.json").write_text("{}", encoding="utf-8")
    try:
        runner._assert_evaluation_recoverable(
            config, "an_cn_r0", "final", resume=True
        )
    except RuntimeError as exc:
        assert "forbids retry" in str(exc)
    else:
        raise AssertionError("retained evaluation failure must block retry")
