#!/usr/bin/env python3
"""Run R294's frozen held-out compact controller comparison."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_r294_fast_controller_development as development  # noqa: E402
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R294"
QUESTION_ID = "Q-0051"
STAGE = "stage_d_compact_controller_validation"
SHARD_COUNT = 3
BOOTSTRAP_REPS = 20_000
BOOTSTRAP_SEED = 294_004
DEFAULT_SEAL = ROOT / "memory/rounds/R294/stage_d_compact_controller_validation_seal.json"
DEFAULT_OUT = ROOT / "results/r294_model_validation/stage_d_compact_controller_validation"
PROTOCOL = ROOT / "memory/rounds/R294/stage_d_compact_controller_validation_protocol.md"
DEVELOPMENT_RUNNER = ROOT / "scripts/run_r294_fast_controller_development.py"
DEVELOPMENT_SUMMARY = (
    ROOT
    / "results/r294_model_validation/stage_c_fast_controller_development_v1/development_summary.json"
)
CONTROLLER_SOURCE = ROOT / "src/andes_rl_kundur/control/coupling_aware_power.py"
FAST_ENDPOINT_SOURCE = ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
COMMON_ENDPOINTS = development.COMMON_ENDPOINTS
DIFFERENTIAL_ENDPOINTS = development.DIFFERENTIAL_ENDPOINTS
THRESHOLDS = {
    "common_ratio_interval_upper_max": 1.05,
    "common_worst_individual_ratio_max": 1.10,
    "differential_point_ratio_max": 0.98,
    "differential_ratio_interval_upper_max_exclusive": 1.0,
}


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


def scenario_bank() -> list[dict[str, Any]]:
    development_names = {item["name"] for item in development.scenario_bank()}
    rows = []
    for tie_k, location, delta_u in itertools.product(
        (1.0, 2.0),
        ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"),
        (-1.0, 1.0),
    ):
        name = (
            f"k{tie_k:g}__{location.lower()}__"
            f"{'pos' if delta_u > 0 else 'neg'}"
        )
        if name not in development_names:
            rows.append(
                {
                    "name": name,
                    "tie_k": tie_k,
                    "location": location,
                    "delta_u": delta_u,
                }
            )
    if len(rows) != 12:
        raise RuntimeError("held-out complement must contain exactly 12 scenarios")
    return rows


def arm_bank() -> list[dict[str, Any]]:
    return [
        {
            "name": "equal_sharing_pi",
            "architecture": "scalar_equal_sharing",
            "sync_gain": None,
        },
        {
            "name": "central_vector__ks1",
            "architecture": "central_vector",
            "sync_gain": 1.0,
        },
        {
            "name": "distributed_dapi__ks1",
            "architecture": "distributed_dapi",
            "sync_gain": 1.0,
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


def _development_selection() -> dict[str, Any]:
    _verify_sidecar(DEVELOPMENT_SUMMARY)
    summary = json.loads(DEVELOPMENT_SUMMARY.read_text(encoding="utf-8"))
    expected = {
        "central_vector": "central_vector__ks1",
        "distributed_dapi": "distributed_dapi__ks1",
    }
    if summary.get("classification") != "FAST-DEVELOPMENT-CANDIDATES-IDENTIFIED":
        raise RuntimeError("development classification does not authorize freeze")
    if summary.get("selected_candidates") != expected:
        raise RuntimeError("formal arms differ from development selection")
    return {
        "summary_sha256": sha256_file(DEVELOPMENT_SUMMARY),
        "selected_candidates": expected,
    }


def _seal_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "plant": "AndesMultiVSGEnvV4Storage full nonlinear DAE",
        "steps": development.STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "bootstrap": {
            "resamples": BOOTSTRAP_REPS,
            "seed": BOOTSTRAP_SEED,
            "unit": "matched scenario",
            "interval_percent": [2.5, 97.5],
        },
        "thresholds": THRESHOLDS,
        "development_selection": _development_selection(),
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "estimand": (
            "paired held-out performance of each fixed coupling-aware vector law "
            "against scalar equal-sharing PI; central-versus-distributed is the "
            "secondary executed-formulation contrast"
        ),
        "claim_boundary": (
            "one modified Kundur plant and the named deterministic laws only; no pure "
            "architecture, MARL, neural, MPC, topology-generalization, stability, or "
            "deployment claim"
        ),
        "sources": {
            "protocol": _source_entry(PROTOCOL),
            "runner": _source_entry(Path(__file__).resolve()),
            "development_runner": _source_entry(DEVELOPMENT_RUNNER),
            "development_summary": _source_entry(DEVELOPMENT_SUMMARY),
            "controller": _source_entry(CONTROLLER_SOURCE),
            "fast_endpoints": _source_entry(FAST_ENDPOINT_SOURCE),
        },
    }


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(
        f"scenarios={len(payload['scenarios'])} arms={len(payload['arms'])} "
        f"jobs={len(payload['jobs'])}"
    )


def _verify_seal(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _verify_sidecar(path)
    if observed != expected_sha256:
        raise RuntimeError(f"seal hash mismatch: {expected_sha256} != {observed}")
    seal = json.loads(path.read_text(encoding="utf-8"))
    for name, entry in seal["sources"].items():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    return seal


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    development.STAGE = STAGE
    return development._run_job(job, seal_hash)


def smoke(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    job = next(
        item for item in seal["jobs"] if item["arm"]["architecture"] == "distributed_dapi"
    )
    path = out_dir / "smoke" / f"{job['name']}.json"
    if path.exists():
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
    if record["guards"]["completed"] is not True:
        raise RuntimeError(f"retained smoke failed: {path}")
    print(
        f"smoke_pass=True controller={record['controller']} "
        f"steps={record['n_steps']} wall={record['runtime']['wall_clock_seconds']:.2f}s"
    )


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


def paired_ratio_interval(
    candidate: np.ndarray,
    baseline: np.ndarray,
    *,
    seed: int,
    resamples: int = BOOTSTRAP_REPS,
) -> dict[str, Any]:
    candidate = np.asarray(candidate, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    if candidate.shape != baseline.shape or candidate.ndim != 1 or candidate.size < 2:
        raise ValueError("paired endpoint vectors must be equal one-dimensional arrays")
    if not np.all(np.isfinite(candidate)) or not np.all(np.isfinite(baseline)):
        raise ValueError("paired endpoints must be finite")
    reference = float(np.mean(baseline))
    if math.isclose(reference, 0.0, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("ratio-of-means baseline must be non-zero")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, candidate.size, size=(resamples, candidate.size))
    sampled_reference = np.mean(baseline[indices], axis=1)
    if np.any(np.isclose(sampled_reference, 0.0, rtol=0.0, atol=1e-15)):
        raise ValueError("bootstrap ratio encountered a zero baseline mean")
    sampled_ratio = np.mean(candidate[indices], axis=1) / sampled_reference
    return {
        "point": float(np.mean(candidate) / reference),
        "percentile_95_interval": [
            float(np.quantile(sampled_ratio, 0.025)),
            float(np.quantile(sampled_ratio, 0.975)),
        ],
        "paired_ratios": (candidate / baseline).tolist(),
        "worst_individual_ratio": float(np.max(candidate / baseline)),
        "scenario_count": int(candidate.size),
        "resamples": int(resamples),
        "seed": int(seed),
    }


def _contrast(
    candidate: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    scenarios: list[str],
    *,
    seed_offset: int,
) -> dict[str, Any]:
    endpoints = {}
    for endpoint_index, endpoint in enumerate((*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)):
        endpoints[endpoint] = paired_ratio_interval(
            np.asarray([candidate[name][endpoint] for name in scenarios], dtype=float),
            np.asarray([baseline[name][endpoint] for name in scenarios], dtype=float),
            seed=BOOTSTRAP_SEED + seed_offset + endpoint_index,
        )
    return {"candidate_over_reference": endpoints}


def _candidate_gate(contrast: dict[str, Any]) -> dict[str, Any]:
    endpoints = contrast["candidate_over_reference"]
    common = {
        endpoint: {
            "interval_upper_pass": (
                endpoints[endpoint]["percentile_95_interval"][1]
                <= THRESHOLDS["common_ratio_interval_upper_max"]
            ),
            "worst_individual_pass": (
                endpoints[endpoint]["worst_individual_ratio"]
                <= THRESHOLDS["common_worst_individual_ratio_max"]
            ),
        }
        for endpoint in COMMON_ENDPOINTS
    }
    differential = {
        endpoint: {
            "point_material_pass": (
                endpoints[endpoint]["point"]
                <= THRESHOLDS["differential_point_ratio_max"]
            ),
            "interval_excludes_one_pass": (
                endpoints[endpoint]["percentile_95_interval"][1]
                < THRESHOLDS["differential_ratio_interval_upper_max_exclusive"]
            ),
        }
        for endpoint in DIFFERENTIAL_ENDPOINTS
    }
    passed = all(all(values.values()) for values in (*common.values(), *differential.values()))
    return {"passed": passed, "common_no_harm": common, "differential_materiality": differential}


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    by_arm: dict[str, dict[str, dict[str, Any]]] = {}
    invalid: list[str] = []
    for job in seal["jobs"]:
        path = out_dir / "records" / f"{job['name']}.json"
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("seal_sha256") != expected_sha256:
            raise RuntimeError(f"record seal mismatch: {path}")
        if record["guards"]["completed"] is not True:
            invalid.append(job["name"])
            continue
        metrics = summarise_fast_md_trace(
            record,
            final_window_steps=development.FINAL_WINDOW_STEPS,
            fast_window_steps=development.FAST_WINDOW_STEPS,
        )
        by_arm.setdefault(job["arm"]["name"], {})[job["scenario"]["name"]] = metrics

    scenarios = sorted(item["name"] for item in seal["scenarios"])
    complete = all(set(by_arm.get(arm["name"], {})) == set(scenarios) for arm in seal["arms"])
    contrasts: dict[str, Any] = {}
    gates: dict[str, Any] = {}
    if complete and not invalid:
        baseline = by_arm["equal_sharing_pi"]
        for offset, name in enumerate(("central_vector__ks1", "distributed_dapi__ks1")):
            contrasts[f"{name}_over_equal_sharing_pi"] = _contrast(
                by_arm[name], baseline, scenarios, seed_offset=100 * (offset + 1)
            )
            gates[name] = _candidate_gate(
                contrasts[f"{name}_over_equal_sharing_pi"]
            )
        formulation = _contrast(
            by_arm["distributed_dapi__ks1"],
            by_arm["central_vector__ks1"],
            scenarios,
            seed_offset=900,
        )
        contrasts["distributed_dapi__ks1_over_central_vector__ks1"] = formulation
        diff_rows = formulation["candidate_over_reference"]
        if all(diff_rows[key]["percentile_95_interval"][1] < 1.0 for key in DIFFERENTIAL_ENDPOINTS):
            formulation_result = "DISTRIBUTED-EXECUTED-FORMULATION-CLEARER"
        elif all(diff_rows[key]["percentile_95_interval"][0] > 1.0 for key in DIFFERENTIAL_ENDPOINTS):
            formulation_result = "CENTRAL-EXECUTED-FORMULATION-CLEARER"
        else:
            formulation_result = "NO-CLEAR-EXECUTED-FORMULATION-DIFFERENCE"
    else:
        formulation_result = "INVALID"

    if invalid or not complete:
        classification = "INVALID"
    else:
        central_pass = bool(gates["central_vector__ks1"]["passed"])
        distributed_pass = bool(gates["distributed_dapi__ks1"]["passed"])
        if central_pass and distributed_pass:
            classification = "VALID-BOTH-VECTOR-CONTROLLERS-PASS"
        elif distributed_pass:
            classification = "VALID-DISTRIBUTED-ONLY-PASS"
        elif central_pass:
            classification = "VALID-CENTRAL-ONLY-PASS"
        else:
            classification = "VALID-NO-VECTOR-CONTROLLER-PASS"

    endpoint_names = (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
    arm_means = {
        name: {
            endpoint: float(np.mean([row[endpoint] for row in rows.values()]))
            for endpoint in endpoint_names
        }
        for name, rows in by_arm.items()
        if rows
    }
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": expected_sha256,
        "classification": classification,
        "executed_formulation_contrast": formulation_result,
        "guards": {
            "all_records_present_and_valid": complete and not invalid,
            "invalid_jobs": invalid,
            "record_count": sum(len(rows) for rows in by_arm.values()),
            "expected_record_count": len(seal["jobs"]),
        },
        "candidate_gates": gates,
        "contrasts": contrasts,
        "arm_endpoint_means": arm_means,
        "thresholds": THRESHOLDS,
        "claim_boundary": seal["claim_boundary"],
    }
    path = out_dir / "formal_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={classification}")
    print(f"formulation_contrast={formulation_result}")
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
