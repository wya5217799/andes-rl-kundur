"""Capacity-amendment ladder for R402 (rungs 1/2/4/8, user-authorized).

R402 launched under the R401-sealed five-process budget.  The repository
owner authorized a capacity expansion, so this runner re-measures the
representative ladder at rungs 1/2/4/8 and freezes a new whole-host budget
for the remaining training runs.  The scientific contract (arms, seeds,
interaction budget, rewards, decision tree) is untouched.  This is an
operational amendment recorded inside the active R402 round; no new round
is opened.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r401_cd_matd3_canary_contract as r401  # noqa: E402

ROUND_ID = "R402"
EVIDENCE = ROOT / "memory/rounds/R402/capacity_evidence_v2.json"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_json(path: Path, payload: dict[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _live_training_workers() -> list[dict[str, Any]]:
    """Return the live R402 training processes with RSS in bytes."""

    matches: list[dict[str, Any]] = []
    for path in Path("/proc").glob("[0-9]*/status"):
        try:
            pid = int(path.parent.name)
            cmdline_path = path.parent / "cmdline"
            command = cmdline_path.read_bytes().replace(b"\x00", b" ").decode(
                "utf-8", errors="replace"
            )
        except (OSError, ValueError):
            continue
        if "run_r402_cd_matd3_canary.py" not in command or "train" not in command:
            continue
        rss_kib = 0
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    rss_kib = int(line.split()[1])
                    break
        except OSError:
            continue
        matches.append({"pid": pid, "rss_kib": rss_kib, "command": command.strip()})
    return matches


def _memory_totals() -> dict[str, int]:
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition(":")
        if separator:
            meminfo[name] = int(value.strip().split()[0]) * 1024
    return {
        "total": int(meminfo.get("MemTotal", 0)),
        "available": int(meminfo.get("MemAvailable", 0)),
    }


def _select_with_training_memory_rule(
    rungs: list[dict[str, Any]],
    *,
    training_worker_rss_bytes: int,
    wsl_total_bytes: int,
) -> dict[str, Any]:
    """Select the highest rung whose 5-percent marginal gain holds and whose
    projected concurrent training-worker memory stays within half of WSL.
    """

    selected = None
    decisions = []
    for rung in rungs:
        workers = int(rung["workers"])
        throughput = float(rung["throughput_jobs_per_second"])
        projected = training_worker_rss_bytes * workers
        memory_safe = projected <= wsl_total_bytes / 2
        valid = bool(rung["all_records_valid"])
        if not valid:
            accepted = False
            reason = "invalid_representative_records"
        elif not memory_safe:
            accepted = False
            reason = "training_memory_reserve_guard"
        elif selected is None:
            accepted = True
            reason = "first_safe_rung"
        elif throughput < 1.05 * float(selected["throughput_jobs_per_second"]):
            accepted = False
            reason = "insufficient_throughput_gain"
        else:
            accepted = True
            reason = "safe_throughput_gain"
        decisions.append(
            {
                "workers": workers,
                "accepted": accepted,
                "reason": reason,
                "projected_training_worker_memory_bytes": projected,
                "memory_safe": memory_safe,
            }
        )
        if accepted:
            selected = rung
    if selected is None:
        return {"readiness": "HOLD", "selected_workers": None, "rung_decisions": decisions}
    workers = int(selected["workers"])
    return {
        "readiness": "RUN-READY",
        "selected_workers": workers,
        "host_process_budget": workers + 1,
        "wsl_python_processes": workers + 1,
        "selected_throughput_jobs_per_second": float(
            selected["throughput_jobs_per_second"]
        ),
        "rung_decisions": decisions,
    }


def measure() -> str:
    """Run the 1/2/4/8 ladder and freeze the amendment evidence."""

    r401._assert_wsl_scratch()
    if EVIDENCE.exists():
        raise FileExistsError("R402 capacity amendment evidence exists")
    live = _live_training_workers()
    training_rss = max((worker["rss_kib"] for worker in live), default=0) * 1024
    if len(live) != 4 or training_rss <= 0:
        raise RuntimeError(
            "expected four live training workers for the amendment ladder: "
            + str(live),
        )
    totals = _memory_totals()
    contract = r401.build_contract()
    base_jobs = r401._capacity_jobs(contract)
    jobs = list(base_jobs) * 4
    rungs = [r401._measure_rung(jobs, workers) for workers in (1, 2, 4, 8)]
    selection = _select_with_training_memory_rule(
        rungs,
        training_worker_rss_bytes=training_rss,
        wsl_total_bytes=totals["total"],
    )
    workers = int(selection["selected_workers"] or 0)
    host = r401._memory_resources()
    throughput = selection.get("selected_throughput_jobs_per_second")
    projected = None
    if throughput is not None:
        remaining = 5 * r401.TOTAL_INTERACTION_STEPS + r401.evaluation_record_count() * 30
        projected = float(remaining) / (30.0 * float(throughput))
    return _write_new_json(
        EVIDENCE,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "capacity_amendment_ladder_rungs_1_2_4_8",
            "authorization": (
                "repository owner authorized the capacity expansion in-session; "
                "scientific contract unchanged"
            ),
            "contract_sha256": r401.contract_sha256(contract),
            "supersedes": {
                "path": "memory/rounds/R401/capacity_evidence.json",
                "reason": (
                    "user-authorized expansion beyond the R401-sealed "
                    "five-process budget for the remaining R402 runs"
                ),
            },
            "live_training_workers": live,
            "training_worker_rss_bytes": training_rss,
            "wsl_memory": totals,
            "host": {
                "logical_processors": host[0],
                "physical_memory_bytes": host[1],
            },
            "wsl": {"memory_available_bytes": host[2]},
            "disk_free_bytes": int(shutil.disk_usage(ROOT).free),
            "rungs": rungs,
            **selection,
            "whole_host_python_process_budget": int(
                selection["host_process_budget"]
            ),
            "empirical_anchor": {
                "all_records_valid": True,
                "concurrent_workers": workers + 1,
                "simulator_workers": workers,
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "projected_remaining_wall_seconds": projected,
            "memory_rule": (
                "projected concurrent training-worker RSS must not exceed "
                "half of WSL total memory"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "formal_authority": False,
            "training_executed": False,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["measure"])
    args = parser.parse_args()
    print(f"R402 capacity amendment evidence: {measure()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

