"""Continuously refill a bounded shard pool for future adaptive rounds.

Motivation:
    ``soft_spot_shard_driver.py`` intentionally launches fixed waves and waits
    for the whole wave.  Adaptive training creates heterogeneous runtimes, so a
    fixed-wave barrier wastes capacity.  This successor driver keeps every
    authorized worker slot occupied by launching the next unique shard as soon
    as one finishes.  It is a new adapter and is not referenced by the active
    R482 seal.

Usage (WSL, through the scratch launcher):
    python scripts/andes_scratch.py scripts/adaptive_shard_driver.py \
        --runner scripts/run_adaptive_u2_successor.py \
        --runner-arg=--config --runner-arg=memory/rounds/RXXX/adaptive_config.json \
        --shards tmp/andes/jobs.json \
        --workers 16 --round RXXX --log-dir tmp/andes/rXXX_dynamic_logs

Failure modes:
    Duplicate shard ids, invalid worker counts, or a nonzero shard exit fail
    closed.  After a failure no new shard is launched; already-running shards
    are allowed to finish and are inventoried.  Logs and the driver result are
    orchestration traces, not scientific evidence.  Formal recovery remains a
    round-owned prospective decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[1]
_LAUNCHER = "scripts/andes_scratch.py"
MAX_REHEARSED_WORKERS = 16


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _log_name(shard_id: str) -> str:
    return shard_id.replace("|", "_") + ".log"


def drive_dynamic(
    runner: Path,
    shards: Sequence[str],
    *,
    runner_args: Sequence[str] = (),
    workers: int,
    round_id: str,
    log_dir: Path,
    resume: bool = False,
    poll_seconds: float = 0.1,
    state_path: Path | None = None,
) -> dict[str, Any]:
    """Run unique shards with immediate refill and fail-closed admission."""

    if workers < 1:
        raise ValueError("workers must be positive")
    if workers > MAX_REHEARSED_WORKERS:
        raise ValueError(f"workers exceeds rehearsed cap {MAX_REHEARSED_WORKERS}: {workers}")
    if poll_seconds <= 0.0:
        raise ValueError("poll_seconds must be positive")
    if len(set(shards)) != len(shards):
        raise ValueError("shard ids must be unique")

    log_dir.mkdir(parents=True, exist_ok=True)
    pending = list(shards)
    active: dict[str, tuple[subprocess.Popen[bytes], TextIO, float]] = {}
    results: dict[str, Any] = {}
    failed: list[str] = []
    launch_order: list[str] = []
    completion_order: list[str] = []
    max_active = 0
    halt_admission = False
    started = time.monotonic()
    started_utc = datetime.now(UTC).isoformat()

    def persist_state() -> None:
        if state_path is None:
            return
        payload = {
            "schema_version": 1,
            "round": round_id,
            "runner": str(runner),
            "runner_args": list(runner_args),
            "workers": workers,
            "pending": pending,
            "active": {
                shard_id: {"pid": process.pid}
                for shard_id, (process, _handle, _started) in active.items()
            },
            "results": results,
            "failed": failed,
            "launch_order": launch_order,
            "completion_order": completion_order,
            "admission_halted": halt_admission,
            "updated_utc": datetime.now(UTC).isoformat(),
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_suffix(state_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(state_path)

    def launch(shard_id: str) -> None:
        nonlocal max_active
        log_path = log_dir / _log_name(shard_id)
        handle = log_path.open("wb")
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / _LAUNCHER),
                str(runner),
                *runner_args,
                "shard",
                shard_id,
                *(["--resume"] if resume else []),
            ],
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        active[shard_id] = (process, handle, time.monotonic())
        launch_order.append(shard_id)
        max_active = max(max_active, len(active))

    while pending and len(active) < workers:
        launch(pending.pop(0))
    persist_state()

    while active:
        completed = [
            shard_id
            for shard_id, (process, _handle, _started) in active.items()
            if process.poll() is not None
        ]
        if not completed:
            time.sleep(poll_seconds)
            continue
        for shard_id in completed:
            process, handle, shard_started = active.pop(shard_id)
            handle.close()
            code = int(process.returncode)
            completion_order.append(shard_id)
            results[shard_id] = {
                "exit_code": code,
                "log": str(log_dir / _log_name(shard_id)),
                "wall_seconds": round(time.monotonic() - shard_started, 3),
            }
            if code != 0:
                failed.append(shard_id)
                halt_admission = True
        if not halt_admission:
            while pending and len(active) < workers:
                launch(pending.pop(0))
        persist_state()

    wall = time.monotonic() - started
    payload = {
        "schema_version": 1,
        "round": round_id,
        "runner": str(runner),
        "runner_args": list(runner_args),
        "runner_sha256": _sha256_file(runner),
        "workers": workers,
        "resume": resume,
        "shard_count": len(shards),
        "started_utc": started_utc,
        "finished_utc": datetime.now(UTC).isoformat(),
        "wall_seconds": round(wall, 3),
        "max_active_observed": max_active,
        "launch_order": launch_order,
        "completion_order": completion_order,
        "results": results,
        "failed": failed,
        "not_launched": pending,
        "admission_halted": halt_admission,
    }
    persist_state()
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--shards", required=True, type=Path)
    parser.add_argument("--workers", required=True, type=int)
    parser.add_argument("--round", required=True)
    parser.add_argument("--runner-arg", action="append", default=[])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--log-dir", type=Path, default=Path("tmp/andes"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    runner = args.runner if args.runner.is_absolute() else ROOT / args.runner
    shards_path = args.shards if args.shards.is_absolute() else ROOT / args.shards
    log_root = args.log_dir if args.log_dir.is_absolute() else ROOT / args.log_dir
    shard_ids = json.loads(shards_path.read_text(encoding="utf-8"))
    if not isinstance(shard_ids, list) or not all(isinstance(item, str) for item in shard_ids):
        raise SystemExit("shards JSON must be a list of shard id strings")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = log_root / f"{args.round}_dynamic_logs_{stamp}"
    payload = drive_dynamic(
        runner.resolve(),
        shard_ids,
        runner_args=args.runner_arg,
        workers=args.workers,
        round_id=args.round,
        log_dir=run_dir,
        resume=args.resume,
        state_path=run_dir / "queue_state.json",
    )
    result_path = run_dir / "driver_result.json"
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not payload["failed"] and not payload["not_launched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
