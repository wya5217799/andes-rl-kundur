from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


def _recovery_adapter():
    try:
        return importlib.import_module("scripts.run_r343_limited_reverse_recovery")
    except ModuleNotFoundError:
        pytest.fail("R343 recovery adapter is not implemented")


def test_prepared_recovery_seal_is_accepted_by_exact_worker_verifier(
    tmp_path: Path,
) -> None:
    recovery = _recovery_adapter()
    seal = tmp_path / "formal_seal.json"
    out_dir = tmp_path / "formal"

    digest = recovery.prepare_formal_seal(seal, out_dir)
    payload = json.loads(seal.read_text(encoding="utf-8"))
    verified = recovery.verify_formal_seal(seal, digest)

    assert digest == hashlib.sha256(seal.read_bytes()).hexdigest()
    assert payload["round"] == "R343"
    assert payload["training_summary_sha256"] == (
        "47d6d41b4829efe8193e5671902da488a17834f5e7c8900313c08d1157c1f329"
    )
    assert payload["formal_trace_count_at_freeze"] == 0
    assert verified == payload


def _write_hashed_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )


def test_recovery_canary_contract_uses_sixteen_unique_non_scientific_tasks() -> None:
    recovery = _recovery_adapter()

    contract = recovery.build_canary_contract()

    assert contract["round"] == "R343"
    assert contract["worker_count"] == 16
    assert contract["steps_per_worker"] == 15
    assert len(contract["tasks"]) == 16
    assert len({(row["scenario_index"], row["arm"]) for row in contract["tasks"]}) == 16
    assert contract["performance_use"] == "forbidden"
    assert contract["automatic_formal_release"] is False


def test_recovery_canary_gate_requires_complete_overlap_and_isolation(
    tmp_path: Path,
) -> None:
    recovery = _recovery_adapter()
    seal = tmp_path / "formal_seal.json"
    recovery.prepare_formal_seal(seal, tmp_path / "formal")
    seal_digest = hashlib.sha256(seal.read_bytes()).hexdigest()
    manifest = json.loads(seal.read_text(encoding="utf-8"))
    trace_dir = tmp_path / "canary" / "traces"
    log_dir = tmp_path / "canary" / "logs"
    gate_path = tmp_path / "canary" / "gate.json"
    log_dir.mkdir(parents=True)

    for task in recovery.build_canary_contract()["tasks"]:
        index = task["shard_index"]
        _write_hashed_json(
            trace_dir / f"canary_{index}.json",
            {
                "round": "R343",
                "phase": "r343-sixteen-worker-physical-canary",
                "controller": task["arm"],
                "formal_seal_sha256": seal_digest,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "execution_shard_index": index,
                "execution_shard_count": 16,
                "observed_concurrent_workers": 16,
                "performance_use": "forbidden",
                "completed": True,
                "tds_failed": False,
                "simulation_started_ns": index,
                "simulation_finished_ns": 100 + index,
                "scratch_working_directory": f"/tmp/r343-{index}",
            },
        )
        (log_dir / f"shard_{index}.log").write_text("complete\n", encoding="utf-8")

    digest = recovery.verify_canary(
        seal,
        seal_digest,
        trace_dir=trace_dir,
        log_dir=log_dir,
        gate_path=gate_path,
    )
    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    assert digest == hashlib.sha256(gate_path.read_bytes()).hexdigest()
    assert gate["classification"] == "PASS"
    assert gate["worker_count"] == 16
    assert gate["unique_scratch_directory_count"] == 16
    assert gate["all_workers_overlapped"] is True
    assert gate["automatic_formal_release"] is False


def test_rehearsal_proves_manifest_roundtrip_without_formal_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    recovery = _recovery_adapter()
    source = recovery.ROOT / "tests/test_r343_limited_reverse_recovery.py"
    parent = tmp_path / "parent.json"
    _write_hashed_json(parent, {"parent": True})
    record = tmp_path / "rehearsal.json"
    formal_output = tmp_path / "formal-output"
    monkeypatch.setattr(recovery, "_source_paths", lambda: {"source": source})
    monkeypatch.setattr(recovery, "_parent_paths", lambda: {"parent": parent})
    monkeypatch.setattr(
        recovery,
        "_installed_andes_identity",
        lambda: {
            "version": "test",
            "sources": {"package": "abc"},
            "case": {"sha256": "def"},
        },
    )
    monkeypatch.setattr(recovery, "_r343_process_count", lambda: 1)
    for name in recovery.THREAD_ENVIRONMENT:
        monkeypatch.setenv(name, "1")

    digest = recovery.rehearse(
        record_path=record,
        output_paths=[formal_output],
    )
    payload = json.loads(record.read_text(encoding="utf-8"))

    assert digest == hashlib.sha256(record.read_bytes()).hexdigest()
    assert payload["checks"]["manifest_roundtrip"] is True
    assert payload["formal_attempt_created"] is False
    assert payload["formal_outputs_created"] is False
    assert not formal_output.exists()
    recovery.verify_rehearsal(
        record_path=record,
        output_paths=[formal_output],
    )


def test_recovery_cli_exposes_manual_canary_and_formal_release_boundaries() -> None:
    recovery = _recovery_adapter()
    parser = recovery._parser()

    assert parser.parse_args(["rehearse"]).command == "rehearse"
    verifier = parser.parse_args(
        ["verify-formal", "--expected-manifest-sha256", "abc"]
    )
    assert verifier.command == "verify-formal"
    assert parser.parse_args(["execute-canary"]).command == "execute-canary"
    assert parser.parse_args(["execute-formal"]).command == "execute-formal"
    worker = parser.parse_args(
        [
            "canary-worker",
            "--expected-manifest-sha256",
            "abc",
            "--shard-index",
            "0",
            "--shard-count",
            "16",
        ]
    )
    assert worker.shard_count == 16


def test_canary_worker_rejects_any_non_sixteen_shard_budget(tmp_path: Path) -> None:
    recovery = _recovery_adapter()

    with pytest.raises(ValueError, match="exactly sixteen"):
        recovery.run_canary_worker(
            tmp_path / "unused.json",
            "unused",
            shard_index=0,
            shard_count=15,
        )


def test_formal_release_gate_is_bound_to_current_seal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    recovery = _recovery_adapter()
    gate = tmp_path / "canary_gate.json"
    _write_hashed_json(
        gate,
        {
            "round": "R343",
            "classification": "PASS",
            "formal_seal_sha256": "seal123",
            "worker_count": 16,
            "automatic_formal_release": False,
        },
    )
    monkeypatch.setattr(recovery, "CANARY_GATE", gate)

    recovery._require_canary_pass("seal123")
    with pytest.raises(ValueError, match="different formal seal"):
        recovery._require_canary_pass("other")
