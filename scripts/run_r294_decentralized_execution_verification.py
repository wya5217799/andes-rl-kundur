#!/usr/bin/env python3
"""Verify explicit local-agent DAPI against sealed R294 Stage-D traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_r294_compact_controller_validation as formal  # noqa: E402
import run_r294_fast_controller_development as development  # noqa: E402
from andes_rl_kundur.control.decentralized_dapi import (  # noqa: E402
    DecentralizedDAPIExecution,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R294"
QUESTION_ID = "Q-0051"
STAGE = "stage_e_explicit_decentralized_execution"
SHARD_COUNT = 3
TRACE_ATOL = 1e-10
ENDPOINT_ATOL = 1e-12
DEFAULT_SEAL = ROOT / "memory/rounds/R294/stage_e_decentralized_execution_seal.json"
DEFAULT_OUT = ROOT / "results/r294_model_validation/stage_e_decentralized_execution"
PROTOCOL = ROOT / "memory/rounds/R294/stage_e_decentralized_execution_protocol.md"
LOCAL_SOURCE = ROOT / "src/andes_rl_kundur/control/decentralized_dapi.py"
SPARSE_SOURCE = ROOT / "src/andes_rl_kundur/control/coupling_aware_power.py"
DEVELOPMENT_RUNNER = ROOT / "scripts/run_r294_fast_controller_development.py"
FORMAL_SEAL = ROOT / "memory/rounds/R294/stage_d_compact_controller_validation_seal.json"
FORMAL_SUMMARY = ROOT / "results/r294_model_validation/stage_d_compact_controller_validation/formal_summary.json"
FORMAL_RECORDS = ROOT / "results/r294_model_validation/stage_d_compact_controller_validation/records"
TRACE_FIELDS = (
    "bess_requested_power_system_pu",
    "bess_commanded_power_system_pu",
    "delta_f_physical_hz",
    "bess_soc",
)
ENDPOINTS = (*development.COMMON_ENDPOINTS, *development.DIFFERENTIAL_ENDPOINTS)


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
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty artifact: {path}")
    if not sidecar.is_file() or sidecar.stat().st_size == 0:
        raise RuntimeError(f"missing or empty sidecar: {sidecar}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = sha256_file(path)
    if expected != observed:
        raise RuntimeError(f"hash mismatch for {path}: {expected} != {observed}")
    return observed


def _source_entry(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def arm() -> dict[str, Any]:
    return {
        "name": "distributed_dapi_local_agents__ks1",
        "architecture": "distributed_dapi_local_agents",
        "sync_gain": 1.0,
    }


def job_bank() -> list[dict[str, Any]]:
    return [
        {
            "order": order,
            "name": f"{scenario['name']}__{arm()['name']}",
            "scenario": scenario,
            "arm": arm(),
        }
        for order, scenario in enumerate(formal.scenario_bank())
    ]


def _seal_payload() -> dict[str, Any]:
    _verify_sidecar(FORMAL_SEAL)
    _verify_sidecar(FORMAL_SUMMARY)
    summary = json.loads(FORMAL_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("classification") != "VALID-BOTH-VECTOR-CONTROLLERS-PASS":
        raise RuntimeError("Stage-D classification does not permit equivalence verification")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "purpose": "post-formal explicit local-agent execution equivalence",
        "steps": development.STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "trace_atol": TRACE_ATOL,
        "endpoint_atol": ENDPOINT_ATOL,
        "trace_fields": list(TRACE_FIELDS),
        "endpoints": list(ENDPOINTS),
        "formal_summary_sha256": sha256_file(FORMAL_SUMMARY),
        "jobs": job_bank(),
        "claim_boundary": (
            "implementation equivalence in one deterministic single-process ANDES "
            "simulation only; no performance selection, communication robustness, "
            "hardware decentralization, MARL, or deployment claim"
        ),
        "sources": {
            "protocol": _source_entry(PROTOCOL),
            "runner": _source_entry(Path(__file__).resolve()),
            "local_controller": _source_entry(LOCAL_SOURCE),
            "sparse_vector_controller": _source_entry(SPARSE_SOURCE),
            "development_runner": _source_entry(DEVELOPMENT_RUNNER),
            "formal_seal": _source_entry(FORMAL_SEAL),
            "formal_summary": _source_entry(FORMAL_SUMMARY),
        },
    }


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(f"jobs={len(payload['jobs'])}")


def _verify_seal(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _verify_sidecar(path)
    if observed != expected_sha256:
        raise RuntimeError(f"seal hash mismatch: {expected_sha256} != {observed}")
    seal = json.loads(path.read_text(encoding="utf-8"))
    for name, entry in seal["sources"].items():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    return seal


def _local_controller(arm_config: dict[str, Any], *, device_count: int, nominal_hz: float):
    if arm_config["architecture"] != "distributed_dapi_local_agents":
        raise ValueError("Stage E accepts only explicit local-agent DAPI")
    return DecentralizedDAPIExecution(
        adjacency=development.COMM_ADJ,
        device_count=device_count,
        nominal_frequency_hz=nominal_hz,
        kp_system_pu_per_hz_per_device=development.KP,
        ki_system_pu_per_hz_s_per_device=development.KI,
        sync_gain_system_pu_per_hz=float(arm_config["sync_gain"]),
        consensus_gain_per_s=development.CONSENSUS_GAIN,
    )


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    original_factory = development._controller
    original_stage = development.STAGE
    try:
        development._controller = _local_controller
        development.STAGE = STAGE
        return development._run_job(job, seal_hash)
    finally:
        development._controller = original_factory
        development.STAGE = original_stage


def smoke(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    job = seal["jobs"][0]
    path = out_dir / "smoke" / f"{job['name']}.json"
    if path.exists():
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
    if record["guards"]["completed"] is not True:
        raise RuntimeError(f"retained smoke failed: {path}")
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
    comparisons = []
    invalid = []
    for job in seal["jobs"]:
        local_path = out_dir / "records" / f"{job['name']}.json"
        formal_name = f"{job['scenario']['name']}__distributed_dapi__ks1.json"
        formal_path = FORMAL_RECORDS / formal_name
        _verify_sidecar(local_path)
        _verify_sidecar(formal_path)
        local = json.loads(local_path.read_text(encoding="utf-8"))
        reference = json.loads(formal_path.read_text(encoding="utf-8"))
        if local["guards"]["completed"] is not True or reference["guards"]["completed"] is not True:
            invalid.append(job["name"])
            continue
        trace_differences = {}
        for field in TRACE_FIELDS:
            local_value = np.asarray([row[field] for row in local["traces"]], dtype=float)
            reference_value = np.asarray(
                [row[field] for row in reference["traces"]], dtype=float
            )
            trace_differences[field] = float(np.max(np.abs(local_value - reference_value)))
        local_metrics = summarise_fast_md_trace(
            local,
            final_window_steps=development.FINAL_WINDOW_STEPS,
            fast_window_steps=development.FAST_WINDOW_STEPS,
        )
        reference_metrics = summarise_fast_md_trace(
            reference,
            final_window_steps=development.FINAL_WINDOW_STEPS,
            fast_window_steps=development.FAST_WINDOW_STEPS,
        )
        endpoint_differences = {
            endpoint: abs(float(local_metrics[endpoint]) - float(reference_metrics[endpoint]))
            for endpoint in ENDPOINTS
        }
        comparisons.append(
            {
                "scenario": job["scenario"]["name"],
                "local_record": local_path.relative_to(ROOT).as_posix(),
                "formal_record": formal_path.relative_to(ROOT).as_posix(),
                "trace_max_abs_differences": trace_differences,
                "endpoint_abs_differences": endpoint_differences,
                "trace_equivalent": all(value <= TRACE_ATOL for value in trace_differences.values()),
                "endpoint_equivalent": all(
                    value <= ENDPOINT_ATOL for value in endpoint_differences.values()
                ),
            }
        )
    passed = bool(
        not invalid
        and len(comparisons) == len(seal["jobs"])
        and all(row["trace_equivalent"] and row["endpoint_equivalent"] for row in comparisons)
    )
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": expected_sha256,
        "classification": (
            "DECENTRALIZED-EXECUTION-EQUIVALENT" if passed else "DECENTRALIZED-EXECUTION-NOT-EQUIVALENT"
        ),
        "guards": {
            "all_local_records_valid": not invalid and len(comparisons) == len(seal["jobs"]),
            "all_trace_fields_equivalent": all(row["trace_equivalent"] for row in comparisons),
            "all_endpoints_equivalent": all(row["endpoint_equivalent"] for row in comparisons),
            "invalid_jobs": invalid,
            "record_count": len(comparisons),
            "expected_record_count": len(seal["jobs"]),
        },
        "max_trace_abs_difference": max(
            value
            for row in comparisons
            for value in row["trace_max_abs_differences"].values()
        ),
        "max_endpoint_abs_difference": max(
            value
            for row in comparisons
            for value in row["endpoint_abs_differences"].values()
        ),
        "comparisons": comparisons,
        "claim_boundary": seal["claim_boundary"],
    }
    path = out_dir / "execution_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={summary['classification']}")
    print(f"max_trace_abs_difference={summary['max_trace_abs_difference']}")
    print(f"max_endpoint_abs_difference={summary['max_endpoint_abs_difference']}")
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
