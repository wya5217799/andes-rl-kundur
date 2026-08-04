#!/usr/bin/env python3
"""Audit an interrupted R292 v3 formal matrix before process-level resume.

Usage
-----
Run once after a host interruption and before relaunching formal shards::

    python scripts/audit_r292_formal_v3_resume.py

The audit verifies the existing seal and all present trace JSON/sidecar pairs,
but deliberately does not compute or inspect performance endpoints.  It writes
a new immutable resume-audit record and refuses any unexpected, failed,
incomplete, provenance-mismatched, or hash-mismatched trajectory.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL_ADAPTER = ROOT / "scripts/run_r292_formal_v3.py"
AMENDMENT = ROOT / "memory/rounds/R292/execution_resume_20260731.json"
RUN_DIR = ROOT / "results/r292_recovery_v3_unattended"
STATUS_DIR = RUN_DIR / "status"
DEFAULT_AUDIT = RUN_DIR / "reboot_resume_1_audit.json"


def _load_formal():
    spec = importlib.util.spec_from_file_location(
        "r292_formal_v3_resume_audit", FORMAL_ADAPTER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load R292 v3 formal adapter: {FORMAL_ADAPTER}")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    return adapter.FORMAL


def _status_text(name: str) -> str | None:
    path = STATUS_DIR / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def audit(output: Path = DEFAULT_AUDIT) -> dict[str, object]:
    if output.exists() or Path(f"{output}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite resume audit: {output}")
    if _status_text("phase") != "FORMAL_V3_RUNNING_THREE_SHARDS":
        raise ValueError("resume audit requires the interrupted formal-running phase")
    if _status_text("failed") is not None or _status_text("complete") is not None:
        raise ValueError("failed or completed execution is not eligible for reboot resume")

    formal = _load_formal()
    seal = formal.DEFAULT_SEAL
    fields = Path(f"{seal}.sha256").read_text(encoding="ascii").split()
    if len(fields) != 2 or fields[1] != seal.name:
        raise ValueError("invalid R292 v3 formal seal sidecar")
    seal_hash = fields[0]
    if formal.sha256_file(seal) != seal_hash:
        raise ValueError("R292 v3 formal seal hash mismatch")
    manifest = formal._verify(seal, seal_hash)
    execution = manifest["execution"]
    if execution.get("resume_completed") is not True:
        raise ValueError("formal manifest does not authorize completed-trace resume")
    if execution.get("overwrite") is not False:
        raise ValueError("formal manifest permits overwrite")
    if execution.get("retry_failed_trajectory") is not False:
        raise ValueError("formal manifest permits failed-trajectory retry")

    bank, _ = formal.load_scenario_bank(
        formal.FORMAL_BANK,
        expected_sha256=manifest["formal_bank"]["sha256"],
    )
    tasks = [
        (scenario, arm)
        for scenario in bank["scenarios"]
        for arm in formal.ARMS
    ]
    expected = {
        formal._trace_path(formal.DEFAULT_OUT, scenario["name"], arm): (
            scenario,
            arm,
            index % execution["shard_count"],
        )
        for index, (scenario, arm) in enumerate(tasks)
    }
    trace_dir = formal.DEFAULT_OUT / "traces"
    actual = set(trace_dir.glob("*.json")) if trace_dir.exists() else set()
    unexpected = sorted(str(path.relative_to(ROOT)) for path in actual - set(expected))
    if unexpected:
        raise ValueError(f"unexpected formal traces: {unexpected}")
    if not actual:
        raise ValueError("no completed formal trace exists to resume")

    completed_by_shard: Counter[int] = Counter()
    trace_hashes: dict[str, str] = {}
    for path in sorted(actual):
        sidecar = Path(f"{path}.sha256")
        if not sidecar.is_file():
            raise ValueError(f"missing formal trace sidecar: {path}")
        side_fields = sidecar.read_text(encoding="ascii").split()
        if len(side_fields) != 2 or side_fields[1] != path.name:
            raise ValueError(f"invalid formal trace sidecar: {sidecar}")
        digest = formal.sha256_file(path)
        if digest != side_fields[0]:
            raise ValueError(f"formal trace hash mismatch: {path}")
        scenario, arm, shard = expected[path]
        record = formal._validate_trace(path, scenario, arm, manifest, seal_hash)
        if record.get("completed") is not True or record.get("tds_failed") is not False:
            raise ValueError(f"retained failed formal trace forbids resume: {path}")
        if record.get("n_steps") != record.get("requested_steps") != 300:
            raise ValueError(f"formal trace step-count mismatch: {path}")
        if record.get("n_steps") != 300 or len(record.get("traces", [])) != 300:
            raise ValueError(f"incomplete formal trace forbids resume: {path}")
        completed_by_shard[shard] += 1
        trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest

    shard_count = int(execution["shard_count"])
    tasks_per_shard = Counter(index % shard_count for index in range(len(tasks)))
    payload: dict[str, object] = {
        "schema_version": 1,
        "round": "R292",
        "event": "host-reboot-formal-resume-audit",
        "classification": "RESUME_SAFE",
        "execution_resume_record": {
            "path": str(AMENDMENT.relative_to(ROOT)).replace("\\", "/"),
            "sha256": formal.sha256_file(AMENDMENT),
        },
        "formal_seal_sha256": seal_hash,
        "formal_bank_sha256": manifest["formal_bank"]["sha256"],
        "expected_trajectory_count": len(tasks),
        "validated_completed_trajectory_count": len(actual),
        "remaining_trajectory_count": len(tasks) - len(actual),
        "completed_by_shard": {
            str(index): completed_by_shard[index] for index in range(shard_count)
        },
        "remaining_by_shard": {
            str(index): tasks_per_shard[index] - completed_by_shard[index]
            for index in range(shard_count)
        },
        "trace_hashes": dict(sorted(trace_hashes.items())),
        "performance_endpoints_inspected": False,
        "screen_or_formal_prepare_repeated": False,
        "overwrite": False,
        "retry_failed_trajectory": False,
    }
    digest = formal._write_new(output, payload)
    print(
        f"[resume-audit] classification=RESUME_SAFE "
        f"completed={len(actual)} remaining={len(tasks) - len(actual)} "
        f"sha256={digest}",
        flush=True,
    )
    return payload


if __name__ == "__main__":
    audit()
