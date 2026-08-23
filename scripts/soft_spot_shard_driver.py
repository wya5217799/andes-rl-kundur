"""Shared eval-shard driver for the soft-spot program (R411+).

Motivation:
    The soft-spot experiment program
    (paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md)
    requires one parameterized eval-shard driver reused unchanged by items
    A1/A2/A3/A4 instead of per-item orchestration code.  Each round's sealed
    runner owns the scientific content and exposes a ``shard <shard_id>``
    subcommand with create-only hashed outputs; this driver only schedules.

    The driver process is the budget's launcher: with ``workers`` concurrent
    shards the WSL python process count is ``workers + 1``, matching the
    sealed ``wsl_python_processes`` budget of the round.

Usage (WSL only, always through the scratch launcher):
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r411_probe_amplitude_ladder.py \
        --shards tmp/andes/r411_shards.json --workers 8 --round R411 \
        [--only id,id,...] [--resume]

Failure modes:
    Any nonzero shard exit marks the shard failed and the driver exits 1.
    Re-running failed shards requires ``--only <ids> --resume`` so the
    runner skips already-written hashed profile files; a first attempt
    refuses to overwrite (create-only).  Per-shard logs and the driver
    result are orchestration traces under tmp/andes and never evidence.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

ROOT = Path(__file__).resolve().parents[1]

SHARD_COMMAND = "shard"
_LAUNCHER = "scripts/andes_scratch.py"


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


def waves(shards: Sequence[str], workers: int) -> list[list[str]]:
    """Partition shard ids into sequential waves of at most ``workers``."""
    if workers < 1:
        raise ValueError("workers must be positive")
    return [
        list(shards[index : index + workers])
        for index in range(0, len(shards), workers)
    ]


def _log_name(shard_id: str) -> str:
    """Portable per-shard log filename (shard ids may contain '|')."""
    return shard_id.replace("|", "_") + ".log"


def drive(
    runner: Path,
    shards: Sequence[str],
    *,
    workers: int,
    round_id: str,
    log_dir: Path,
    resume: bool,
) -> dict[str, Any]:
    """Run every shard through the scratch launcher, wave by wave."""
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    started_utc = datetime.now(UTC).isoformat()
    results: dict[str, Any] = {}
    failed: list[str] = []
    for index, wave in enumerate(waves(shards, workers)):
        processes: dict[str, subprocess.Popen[bytes]] = {}
        for shard_id in wave:
            log_path = log_dir / _log_name(shard_id)
            processes[shard_id] = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / _LAUNCHER),
                    str(runner),
                    SHARD_COMMAND,
                    shard_id,
                    *(["--resume"] if resume else []),
                ],
                stdout=log_path.open("wb"),
                stderr=subprocess.STDOUT,
            )
        for shard_id, process in processes.items():
            code = int(process.wait())
            results[shard_id] = {
                "exit_code": code,
                "log": str(log_dir / _log_name(shard_id)),
            }
            if code != 0:
                failed.append(shard_id)
        safe_emit(
            f"[{round_id}] wave {index + 1}: "
            + ", ".join(
                f"{shard_id}->{results[shard_id]['exit_code']}" for shard_id in wave
            )
        )
    wall = time.monotonic() - started
    return {
        "round": round_id,
        "runner": str(runner),
        "runner_sha256": _sha256_file(runner),
        "workers": workers,
        "resume": resume,
        "shard_count": len(shards),
        "started_utc": started_utc,
        "finished_utc": datetime.now(UTC).isoformat(),
        "wall_seconds": round(wall, 3),
        "results": results,
        "failed": failed,
    }


def _log_root(value: str | None) -> Path:
    """Resolve the orchestration log root like --shards/--runner: relative
    values anchor to the repository root, absolute values pass through.

    The driver runs with a scratch working directory (andes_scratch
    launcher), while detached pipelines look up driver_result.json from the
    repository root; an unanchored relative --log-dir writes logs under the
    scratch tree and pipelines then exit missing the result (R476 failure).
    """
    if value is None:
        return ROOT / "tmp" / "andes"
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--shards", required=True, type=Path)
    parser.add_argument("--workers", required=True, type=int)
    parser.add_argument("--round", required=True)
    parser.add_argument(
        "--only",
        default=None,
        help="comma-separated shard ids to run instead of the full list",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--log-dir",
        default=None,
        help="optional explicit orchestration log directory (default tmp/andes)",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    runner = args.runner if args.runner.is_absolute() else ROOT / args.runner
    runner = runner.resolve()
    shards_path = (
        args.shards if args.shards.is_absolute() else ROOT / args.shards
    ).resolve()
    shard_ids = json.loads(shards_path.read_text(encoding="utf-8"))
    if not isinstance(shard_ids, list) or not all(
        isinstance(item, str) for item in shard_ids
    ):
        raise SystemExit("shards JSON must be a list of shard id strings")
    if args.only is not None:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        unknown = wanted - set(shard_ids)
        if unknown:
            raise SystemExit(f"unknown shard ids in --only: {sorted(unknown)}")
        shard_ids = [item for item in shard_ids if item in wanted]
    log_root = _log_root(args.log_dir)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    log_dir = log_root / f"{args.round}_shard_logs_{stamp}"
    payload = drive(
        runner,
        shard_ids,
        workers=args.workers,
        round_id=args.round,
        log_dir=log_dir,
        resume=args.resume,
    )
    result_path = log_dir / "driver_result.json"
    result_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not payload["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
