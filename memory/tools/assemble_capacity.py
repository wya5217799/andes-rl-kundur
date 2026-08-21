"""Assemble a round's capacity_evidence.json from a measured shard ladder.

Motivation:
    Round runners measure raw ladder rungs (throughput vs workers) but leave
    worker selection to a governed assembly step: replay the 5% marginal-gain
    rule, cap workers at the shard count, apply the memory rule, and freeze
    the honest concurrent-load declarations before ``prepare`` seals the
    launch budget.  Same pattern as the R436/R438 assembly scripts; this is
    the codified generic tool (CLAUDE.md maintainability rule).

Usage:
    # in WSL (memory rule reads /proc/meminfo):
    python memory/tools/assemble_capacity.py --round R439 \\
        --cap-workers 4 --other-reserved 14 --rss-floor-bytes 943718400

    # dry-run print only:
    python memory/tools/assemble_capacity.py --round R439 --cap-workers 4 \\
        --other-reserved 14 --dry-run

Failure modes:
    Missing rung file (ladder not finished) exits 2.  A ladder with any
    failed task exits 3 (never select a rung from broken measurements).
    Non-Linux hosts skip the memory rule and mark it ``unchecked``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MARGINAL_GAIN_MIN = 1.05
OS_FLOOR_BYTES = 3 * 1024**3
DEFAULT_RSS_FLOOR_BYTES = 943_718_400  # 900 MiB per live worker (owner rule)


def _memory_resources() -> tuple[int, int | None, int | None]:
    logical = None
    physical = None
    mem_total = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "MemTotal":
                mem_total = int(value.strip().split()[0]) * 1024
                break
    except OSError:
        pass
    try:
        import os

        logical = os.cpu_count()
    except Exception:
        pass
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):  # type: ignore[misc]
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            physical = int(status.ullTotalPhys)
    except Exception:
        pass
    return logical, physical, mem_total


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assemble(
    round_id: str,
    *,
    cap_workers: int,
    other_reserved: int,
    rss_floor_bytes: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    capacity_path = ROOT / "memory" / "rounds" / round_id / "capacity_evidence.json"
    if not capacity_path.is_file():
        raise SystemExit(
            f"2 capacity evidence missing (ladder not finished?): {capacity_path}"
        )
    payload = json.loads(capacity_path.read_text(encoding="utf-8"))
    rungs = payload.get("rungs")
    if not isinstance(rungs, list) or not rungs:
        raise SystemExit(f"2 no ladder rungs in {capacity_path}")
    if not all(r.get("all_ok", True) for r in rungs):
        raise SystemExit(f"3 ladder has failed tasks in {capacity_path}")
    best = max(rungs, key=lambda r: r["throughput_jobs_per_second"])
    ladder_selected = int(best["workers"])
    selected = min(ladder_selected, cap_workers)
    decisions = []
    previous = None
    for rung in rungs:
        throughput = float(rung["throughput_jobs_per_second"])
        marginal = throughput / previous if previous else None
        decisions.append(
            {
                "workers": int(rung["workers"]),
                "throughput_jobs_per_second": throughput,
                "marginal_gain": round(marginal, 4) if marginal else None,
                "accepted": bool(marginal is None or marginal >= MARGINAL_GAIN_MIN),
            }
        )
        previous = throughput
    logical, physical, mem_total = _memory_resources()
    memory_safe = None
    if mem_total:
        projected = selected * rss_floor_bytes
        memory_safe = bool(projected + OS_FLOOR_BYTES <= mem_total)
        memory_rule = (
            f"selected workers x {rss_floor_bytes} B RSS floor + 3 GiB OS "
            f"floor <= WSL MemTotal {mem_total} B"
        )
    else:
        memory_rule = "memory rule unchecked (no /proc/meminfo)"
    payload["selected_workers"] = selected
    payload["selected_throughput_jobs_per_second"] = float(best["throughput_jobs_per_second"])
    payload["ladder_selected_workers"] = ladder_selected
    payload["cap_workers"] = cap_workers
    payload["readiness"] = (
        "RUN-READY"
        if memory_safe
        else ("MEMORY-BLOCKED" if memory_safe is False else "MEMORY-UNCHECKED")
    )
    payload["rung_decisions"] = decisions
    payload["memory_rule"] = memory_rule
    payload["training_worker_rss_anchor"] = rss_floor_bytes
    payload["os_floor_bytes"] = OS_FLOOR_BYTES
    payload["host_process_budget"] = selected + 1
    payload["wsl_python_processes"] = selected + 1
    payload["other_reserved_processes"] = other_reserved
    payload["native_threads_per_process"] = 1
    payload["host"] = {
        "logical_processors": logical,
        "physical_memory_bytes": physical,
    }
    payload["assembled_utc"] = None
    if not dry_run:
        from datetime import UTC, datetime

        payload["assembled_utc"] = datetime.now(UTC).isoformat()
        capacity_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        digest = _sha256_file(capacity_path)
        Path(f"{capacity_path}.sha256").write_text(
            f"{digest}  {capacity_path.name}\n", encoding="ascii"
        )
        payload["_sha256"] = digest
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True, help="round id, e.g. R439")
    parser.add_argument(
        "--cap-workers", required=True, type=int, help="shard-count worker ceiling"
    )
    parser.add_argument(
        "--other-reserved",
        required=True,
        type=int,
        help="concurrent in-flight python processes to freeze into the budget",
    )
    parser.add_argument(
        "--rss-floor-bytes",
        type=int,
        default=DEFAULT_RSS_FLOOR_BYTES,
        help="per-worker RSS floor for the memory rule",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    payload = assemble(
        args.round,
        cap_workers=args.cap_workers,
        other_reserved=args.other_reserved,
        rss_floor_bytes=args.rss_floor_bytes,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            {
                "round": args.round,
                "selected_workers": payload["selected_workers"],
                "ladder_selected_workers": payload.get("ladder_selected_workers"),
                "readiness": payload["readiness"],
                "other_reserved_processes": payload["other_reserved_processes"],
                "sha256": payload.get("_sha256"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
