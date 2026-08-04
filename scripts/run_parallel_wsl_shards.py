"""Launch independent ANDES shards concurrently from the Windows host.

Motivation
----------
An ANDES shard must use one WSL Python process.  Launching shards through a
Python orchestrator inside WSL consumes an extra process and can accidentally
serialize a nominally sharded study.  This host-side launcher starts every
declared shard before waiting, enforces the repository's three-process cap,
and reports progress against the global task count.

Usage
-----
Dry-run a three-shard plan::

    python scripts/run_parallel_wsl_shards.py --worker-script scripts/run.py \
      --shard-count 3 --global-task-count 264 --log-dir tmp/run --dry-run -- \
      run --expected-manifest-sha256 <sha256>

Remove ``--dry-run`` to execute the workers.  The worker entrypoint must
accept ``--shard-index`` and ``--shard-count``.

Failure modes
-------------
Invalid counts exit 2 before launch.  A failed worker terminates the remaining
host-side WSL clients and exits 1.  If ``--trace-dir`` is supplied, successful
workers with an incomplete global JSON count exit 3.  Logs are preserved and
never overwritten silently by this launcher.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WSL_PYTHON = "/home/wya/andes_venv/bin/python"
SCRATCH_LAUNCHER = "scripts/andes_scratch.py"
MAX_WSL_PYTHON_PROCESSES = 3


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved.as_posix()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", maxsplit=1)[1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _worker_script(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return _wsl_path(path)
    return path.as_posix()


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    if not 1 <= args.shard_count <= MAX_WSL_PYTHON_PROCESSES:
        raise ValueError(
            f"shard_count must be 1..{MAX_WSL_PYTHON_PROCESSES}"
        )
    if args.global_task_count < 1:
        raise ValueError("global_task_count must be positive")
    worker_args = list(args.worker_args)
    if worker_args[:1] == ["--"]:
        worker_args = worker_args[1:]
    wsl_root = _wsl_path(ROOT)
    workers = []
    for shard_index in range(args.shard_count):
        command = [
            "wsl.exe",
            "--cd",
            wsl_root,
            WSL_PYTHON,
            SCRATCH_LAUNCHER,
            _worker_script(args.worker_script),
            *worker_args,
            "--shard-index",
            str(shard_index),
            "--shard-count",
            str(args.shard_count),
        ]
        workers.append(
            {
                "shard_index": shard_index,
                "command": command,
                "log": str((args.log_dir / f"shard_{shard_index}.log").resolve()),
            }
        )
    return {
        "schema_version": 1,
        "worker_count": args.shard_count,
        "wsl_python_process_budget": MAX_WSL_PYTHON_PROCESSES,
        "global_task_count": args.global_task_count,
        "trace_dir": str(args.trace_dir.resolve()) if args.trace_dir else None,
        "workers": workers,
    }


def _completed_count(trace_dir: Path | None) -> int:
    if trace_dir is None or not trace_dir.is_dir():
        return 0
    return sum(1 for _path in trace_dir.glob("*.json"))


def execute(plan: dict[str, Any], *, poll_seconds: float) -> int:
    log_handles = []
    processes: list[tuple[dict[str, Any], subprocess.Popen[bytes]]] = []
    try:
        for worker in plan["workers"]:
            log_path = Path(worker["log"])
            log_path.parent.mkdir(parents=True, exist_ok=True)
            if log_path.exists():
                raise FileExistsError(f"refusing to overwrite log: {log_path}")
            handle = log_path.open("xb")
            log_handles.append(handle)
            process = subprocess.Popen(
                worker["command"],
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
            processes.append((worker, process))

        trace_dir = Path(plan["trace_dir"]) if plan["trace_dir"] else None
        last_completed = -1
        while True:
            completed = _completed_count(trace_dir)
            if completed != last_completed:
                print(
                    f"[global {completed}/{plan['global_task_count']}]",
                    flush=True,
                )
                last_completed = completed
            running = [item for item in processes if item[1].poll() is None]
            failed = [item for item in processes if item[1].poll() not in (None, 0)]
            if failed:
                for _worker, process in running:
                    process.terminate()
                for _worker, process in running:
                    process.wait(timeout=10)
                return 1
            if not running:
                break
            time.sleep(poll_seconds)

        if trace_dir is not None:
            completed = _completed_count(trace_dir)
            if completed != plan["global_task_count"]:
                print(
                    f"ERROR: global trace count {completed} != "
                    f"{plan['global_task_count']}",
                    file=sys.stderr,
                )
                return 3
        return 0
    finally:
        for handle in log_handles:
            handle.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-script", required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    parser.add_argument("--global-task-count", type=int, required=True)
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--trace-dir", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("worker_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = build_plan(args)
        if args.dry_run:
            print(json.dumps(plan, ensure_ascii=True, indent=2))
            return 0
        return execute(plan, poll_seconds=args.poll_seconds)
    except (ValueError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
