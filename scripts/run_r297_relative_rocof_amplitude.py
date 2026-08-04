#!/usr/bin/env python3
"""Run R297's final full-anchor relative-RoCoF amplitude check."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_r296_relative_rocof_probe as prior  # noqa: E402
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R297"
QUESTION_ID = "Q-0054"
STAGE = "relative_rocof_full_amplitude"
SHARD_COUNT = 3
FULL_GAIN = 1.0 / prior.FILTER_MAGNITUDE_PER_S
DEFAULT_SEAL = ROOT / "memory/rounds/R297/relative_rocof_amplitude_seal.json"
DEFAULT_OUT = ROOT / "results/r297_relative_rocof_amplitude"
R296_SUMMARY = ROOT / "results/r296_relative_rocof_probe/development_summary.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"create-only artifact exists: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("x", encoding="ascii") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing artifact or sidecar: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = sha256_file(path)
    if expected != observed:
        raise RuntimeError(f"hash mismatch for {path}: {expected} != {observed}")
    return observed


def _source_entry(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def scenario_bank() -> list[dict[str, Any]]:
    return prior.scenario_bank()


def arm_bank() -> list[dict[str, Any]]:
    return [
        {
            "name": "relative_rocof_local__kv0",
            "architecture": "distributed_dapi",
            "execution": "explicit_local_agents",
            "sync_gain": 1.0,
            "consensus_gain": 1.0,
            "relative_rocof_gain": 0.0,
            "target_static_sync_fraction": 0.0,
        },
        {
            "name": "relative_rocof_local__kv100pct",
            "architecture": "distributed_dapi",
            "execution": "explicit_local_agents",
            "sync_gain": 1.0,
            "consensus_gain": 1.0,
            "relative_rocof_gain": FULL_GAIN,
            "target_static_sync_fraction": 1.0,
        },
    ]


def job_bank() -> list[dict[str, Any]]:
    jobs = []
    for scenario in scenario_bank():
        for arm in arm_bank():
            jobs.append(
                {
                    "order": len(jobs),
                    "name": f"{scenario['name']}__{arm['name']}",
                    "scenario": scenario,
                    "arm": arm,
                }
            )
    return jobs


def formal_return_bank() -> list[dict[str, Any]]:
    rows = []
    for tie_k in (1.25, 1.75):
        for location in ("PQ_0", "PQ_1", "PQ_Bus15"):
            for delta_u in (-1.0, 1.0):
                rows.append(
                    {
                        "name": (
                            f"k{tie_k:g}__{location.lower()}__"
                            f"{'pos' if delta_u > 0 else 'neg'}"
                        ),
                        "tie_k": tie_k,
                        "location": location,
                        "delta_u": delta_u,
                    }
                )
    return rows


def _seal_payload() -> dict[str, Any]:
    _verify_sidecar(R296_SUMMARY)
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "final_gain_revision": True,
        "steps": prior.development.STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "filter_time_constant_s": prior.FILTER_TAU_S,
        "filter_magnitude_per_s": prior.FILTER_MAGNITUDE_PER_S,
        "full_anchor_gain_system_pu_s_per_hz": FULL_GAIN,
        "thresholds": prior.THRESHOLDS,
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "predeclared_formal_return_bank": formal_return_bank(),
        "estimand": (
            "development-only matched-case effect of the final full-anchor "
            "relative-RoCoF residual versus fresh zero-residual DAPI"
        ),
        "claim_boundary": (
            "final fixed-plant development revision only; pass authorizes a new "
            "held-out evaluation but is not itself efficacy evidence"
        ),
        "prior_evidence": {"r296_summary": _source_entry(R296_SUMMARY)},
        "sources": {
            "runner": _source_entry(Path(__file__).resolve()),
            "r296_runner": _source_entry(Path(prior.__file__).resolve()),
            "controller": _source_entry(prior.CONTROLLER_SOURCE),
            "fast_endpoints": _source_entry(prior.FAST_ENDPOINT_SOURCE),
        },
    }


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    original = (prior.ROUND_ID, prior.QUESTION_ID, prior.STAGE)
    try:
        prior.ROUND_ID = ROUND_ID
        prior.QUESTION_ID = QUESTION_ID
        prior.STAGE = STAGE
        return prior._run_job(job, seal_hash)
    finally:
        prior.ROUND_ID, prior.QUESTION_ID, prior.STAGE = original


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(f"scenarios=4 arms=2 jobs={len(payload['jobs'])}")


def _verify_seal(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _verify_sidecar(path)
    if observed != expected_sha256:
        raise RuntimeError(f"seal hash mismatch: {expected_sha256} != {observed}")
    seal = json.loads(path.read_text(encoding="utf-8"))
    for group in ("sources", "prior_evidence"):
        for name, entry in seal[group].items():
            if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
                raise RuntimeError(f"sealed source drift for {group}.{name}")
    return seal


def smoke(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    job = next(item for item in seal["jobs"] if item["arm"]["relative_rocof_gain"] > 0)
    path = out_dir / "smoke" / f"{job['name']}.json"
    if path.exists():
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
    trace = record.get("mechanism_trace", [])
    if record["guards"]["completed"] is not True or len(trace) != prior.development.STEPS:
        raise RuntimeError(f"retained smoke failed: {path}")
    if max(abs(row["residual_sum_system_pu"]) for row in trace) > prior.THRESHOLDS[
        "residual_sum_abs_max_system_pu"
    ]:
        raise RuntimeError("retained smoke violates zero-sum contract")
    print(f"smoke_pass=True steps={record['n_steps']} wall={record['runtime']['wall_clock_seconds']:.2f}s")


def run_shard(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    if shard_count != int(seal["shard_count"]):
        raise RuntimeError("runtime shard count differs from seal")
    jobs = [job for job in seal["jobs"] if int(job["order"]) % shard_count == shard_index]
    for position, job in enumerate(jobs, start=1):
        path = out_dir / "records" / f"{job['name']}.json"
        if path.exists():
            _verify_sidecar(path)
            print(f"[{position}/{len(jobs)}] verified_existing={job['name']}", flush=True)
            continue
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
        print(
            f"[{position}/{len(jobs)}] job={job['name']} "
            f"completed={record['guards']['completed']} "
            f"wall={record['runtime']['wall_clock_seconds']:.2f}s",
            flush=True,
        )


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    by_arm: dict[str, dict[str, dict[str, float]]] = {}
    mechanism: dict[str, dict[str, dict[str, float]]] = {}
    invalid: list[str] = []
    for job in seal["jobs"]:
        path = out_dir / "records" / f"{job['name']}.json"
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        trace = record.get("mechanism_trace", [])
        zero_sum = (
            max(abs(row["residual_sum_system_pu"]) for row in trace)
            if trace
            else float("inf")
        )
        if not (
            record.get("seal_sha256") == expected_sha256
            and record["guards"]["completed"] is True
            and len(trace) == prior.development.STEPS
            and zero_sum <= prior.THRESHOLDS["residual_sum_abs_max_system_pu"]
        ):
            invalid.append(job["name"])
            continue
        metrics = summarise_fast_md_trace(
            record,
            final_window_steps=prior.development.FINAL_WINDOW_STEPS,
            fast_window_steps=prior.development.FAST_WINDOW_STEPS,
        )
        arm = job["arm"]["name"]
        scenario = job["scenario"]["name"]
        by_arm.setdefault(arm, {})[scenario] = {
            endpoint: float(metrics[endpoint])
            for endpoint in (*prior.COMMON_ENDPOINTS, *prior.DIFFERENTIAL_ENDPOINTS)
        }
        mechanism.setdefault(arm, {})[scenario] = {
            "residual_request_rms_system_pu": float(
                np.mean([row["residual_request_rms_system_pu"] for row in trace])
            ),
            "total_request_differential_rms_system_pu": float(
                np.mean([row["total_request_differential_rms_system_pu"] for row in trace])
            ),
            "residual_sum_abs_max_system_pu": zero_sum,
        }
    expected = {item["name"] for item in seal["scenarios"]}
    baseline = by_arm.get("relative_rocof_local__kv0", {})
    candidate = by_arm.get("relative_rocof_local__kv100pct", {})
    complete = not invalid and set(baseline) == expected and set(candidate) == expected
    result: dict[str, Any] = {}
    if complete:
        residual_rms = float(
            np.mean(
                [
                    row["residual_request_rms_system_pu"]
                    for row in mechanism["relative_rocof_local__kv100pct"].values()
                ]
            )
        )
        result = prior.evaluate_candidate(
            candidate,
            baseline,
            residual_rms=residual_rms,
        )
        result["relative_rocof_gain_system_pu_s_per_hz"] = FULL_GAIN
    if not complete:
        classification = "INVALID-RELATIVE-ROCOF-AMPLITUDE"
    elif result["passed"]:
        classification = "RELATIVE-ROCOF-FULL-AMPLITUDE-CANDIDATE-IDENTIFIED"
    else:
        classification = "RELATIVE-ROCOF-AMPLITUDE-NO-GO"
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "seal_sha256": expected_sha256,
        "classification": classification,
        "candidate": result,
        "invalid_jobs": invalid,
        "record_count": sum(len(rows) for rows in by_arm.values()),
        "expected_record_count": len(seal["jobs"]),
        "arm_endpoint_means": {
            arm: {
                endpoint: float(np.mean([row[endpoint] for row in rows.values()]))
                for endpoint in (*prior.COMMON_ENDPOINTS, *prior.DIFFERENTIAL_ENDPOINTS)
            }
            for arm, rows in by_arm.items()
        },
        "mechanism_diagnostic_means": {
            arm: {
                field: (
                    float(max(row[field] for row in rows.values()))
                    if field == "residual_sum_abs_max_system_pu"
                    else float(np.mean([row[field] for row in rows.values()]))
                )
                for field in next(iter(rows.values()))
            }
            for arm, rows in mechanism.items()
        },
        "predeclared_formal_return_bank": seal["predeclared_formal_return_bank"],
        "claim_boundary": seal["claim_boundary"],
        "next_step": (
            "open a new sealed full evaluation using the predeclared bank"
            if classification == "RELATIVE-ROCOF-FULL-AMPLITUDE-CANDIDATE-IDENTIFIED"
            else "end relative-RoCoF gain revision"
            if classification == "RELATIVE-ROCOF-AMPLITUDE-NO-GO"
            else "diagnose validity only"
        ),
    }
    path = out_dir / "development_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={classification}")
    print(f"summary_sha256={digest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "smoke", "run", "analyse"))
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-seal-sha256")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.seal, args.out)
        return
    if not args.expected_seal_sha256:
        parser.error("--expected-seal-sha256 is required after prepare")
    if args.command == "smoke":
        smoke(args.seal, args.expected_seal_sha256, args.out)
    elif args.command == "run":
        run_shard(
            args.seal,
            args.expected_seal_sha256,
            args.out,
            args.shard_index,
            args.shard_count,
        )
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out)


if __name__ == "__main__":
    main()
