#!/usr/bin/env python3
"""Run R298's held-out three-arm relative-RoCoF evaluation."""

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

import run_r294_compact_controller_validation as formal_tools  # noqa: E402
import run_r294_fast_controller_development as development  # noqa: E402
import run_r296_relative_rocof_probe as residual  # noqa: E402
import run_r297_relative_rocof_amplitude as selection  # noqa: E402
from andes_rl_kundur.control.coupling_aware_power import (  # noqa: E402
    CentralizedCouplingAwarePI,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R298"
QUESTION_ID = "Q-0055"
STAGE = "relative_rocof_heldout_formal"
SHARD_COUNT = 3
BOOTSTRAP_REPS = 20_000
BOOTSTRAP_SEED = 298_004
DEFAULT_SEAL = ROOT / "memory/rounds/R298/relative_rocof_formal_seal.json"
DEFAULT_OUT = ROOT / "results/r298_relative_rocof_formal"
R297_SEAL = ROOT / "memory/rounds/R297/relative_rocof_amplitude_seal.json"
R297_SUMMARY = ROOT / "results/r297_relative_rocof_amplitude/development_summary.json"
COMMON_ENDPOINTS = development.COMMON_ENDPOINTS
DIFFERENTIAL_ENDPOINTS = development.DIFFERENTIAL_ENDPOINTS
THRESHOLDS = {
    "fast_point_ratio_max": 0.99,
    "fast_interval_upper_exclusive": 1.0,
    "sync_point_ratio_max": 1.0,
    "sync_interval_upper_max": 1.01,
    "common_interval_upper_max": 1.05,
    "common_worst_individual_ratio_max": 1.10,
    "residual_sum_abs_max_system_pu": 1e-12,
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
    return [dict(row) for row in selection.formal_return_bank()]


def arm_bank() -> list[dict[str, Any]]:
    return [
        {
            "name": "distributed_dapi_local__kv0",
            "architecture": "distributed_dapi",
            "execution": "explicit_local_agents",
            "sync_gain": 1.0,
            "consensus_gain": 1.0,
            "relative_rocof_gain": 0.0,
        },
        {
            "name": "distributed_dapi_local__kv100pct",
            "architecture": "distributed_dapi",
            "execution": "explicit_local_agents",
            "sync_gain": 1.0,
            "consensus_gain": 1.0,
            "relative_rocof_gain": selection.FULL_GAIN,
        },
        {
            "name": "central_vector__ks1",
            "architecture": "central_vector",
            "execution": "joint_observation_centralized",
            "sync_gain": 1.0,
            "consensus_gain": None,
            "relative_rocof_gain": None,
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


def _selection_contract() -> dict[str, Any]:
    _verify_sidecar(R297_SEAL)
    _verify_sidecar(R297_SUMMARY)
    seal = json.loads(R297_SEAL.read_text(encoding="utf-8"))
    summary = json.loads(R297_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("classification") != (
        "RELATIVE-ROCOF-FULL-AMPLITUDE-CANDIDATE-IDENTIFIED"
    ):
        raise RuntimeError("R297 does not authorize formal evaluation")
    expected_bank = seal.get("predeclared_formal_return_bank")
    if expected_bank != scenario_bank() or summary.get("predeclared_formal_return_bank") != expected_bank:
        raise RuntimeError("formal bank differs from R297 predeclaration")
    if not math.isclose(
        float(summary["candidate"]["relative_rocof_gain_system_pu_s_per_hz"]),
        selection.FULL_GAIN,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise RuntimeError("formal residual gain differs from R297 selection")
    return {
        "r297_seal_sha256": sha256_file(R297_SEAL),
        "r297_summary_sha256": sha256_file(R297_SUMMARY),
        "selected_gain_system_pu_s_per_hz": selection.FULL_GAIN,
    }


def _seal_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "formal": True,
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
        "controller_gains": {
            "kp": development.KP,
            "ki": development.KI,
            "sync_gain": 1.0,
            "distributed_consensus_gain_per_s": 1.0,
            "rocof_filter_time_constant_s": residual.FILTER_TAU_S,
            "selected_relative_rocof_gain_system_pu_s_per_hz": selection.FULL_GAIN,
        },
        "thresholds": THRESHOLDS,
        "selection_contract": _selection_contract(),
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "primary_estimand": (
            "paired held-out incremental effect of selected explicit local "
            "relative-RoCoF DAPI versus fresh explicit local DAPI"
        ),
        "secondary_estimand": (
            "executed-formulation contrasts to centralized vector PI under matched "
            "physical actions but different information and controller laws"
        ),
        "claim_boundary": (
            "held-out operating conditions within one modified Kundur plant; no "
            "pure architecture, MARL, neural, topology-generalization, robustness, "
            "stability, safety, EMT-HIL, or deployment claim"
        ),
        "prior_evidence": {
            "r297_seal": _source_entry(R297_SEAL),
            "r297_summary": _source_entry(R297_SUMMARY),
        },
        "sources": {
            "runner": _source_entry(Path(__file__).resolve()),
            "controller": _source_entry(residual.CONTROLLER_SOURCE),
            "development_runner": _source_entry(residual.DEVELOPMENT_RUNNER),
            "formal_statistics": _source_entry(Path(formal_tools.__file__).resolve()),
            "fast_endpoints": _source_entry(residual.FAST_ENDPOINT_SOURCE),
        },
    }


_LAST_LOCAL: residual.RecordingRelativeRoCoF | None = None


def _controller(arm: dict[str, Any], *, device_count: int, nominal_hz: float):
    global _LAST_LOCAL
    _LAST_LOCAL = None
    if arm["architecture"] == "central_vector":
        return CentralizedCouplingAwarePI(
            device_count=device_count,
            nominal_frequency_hz=nominal_hz,
            kp_system_pu_per_hz_per_device=development.KP,
            ki_system_pu_per_hz_s_per_device=development.KI,
            sync_gain_system_pu_per_hz=float(arm["sync_gain"]),
        )
    if arm["architecture"] != "distributed_dapi":
        raise ValueError(f"unknown architecture: {arm['architecture']}")
    _LAST_LOCAL = residual.RecordingRelativeRoCoF(
        adjacency=development.COMM_ADJ,
        device_count=device_count,
        nominal_frequency_hz=nominal_hz,
        kp_system_pu_per_hz_per_device=development.KP,
        ki_system_pu_per_hz_s_per_device=development.KI,
        sync_gain_system_pu_per_hz=float(arm["sync_gain"]),
        consensus_gain_per_s=float(arm["consensus_gain"]),
        rocof_filter_time_constant_s=residual.FILTER_TAU_S,
        relative_rocof_gain_system_pu_s_per_hz=float(arm["relative_rocof_gain"]),
    )
    return _LAST_LOCAL


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    global _LAST_LOCAL
    original = (
        development._controller,
        development.ROUND_ID,
        development.QUESTION_ID,
        development.STAGE,
    )
    _LAST_LOCAL = None
    try:
        development._controller = _controller
        development.ROUND_ID = ROUND_ID
        development.QUESTION_ID = QUESTION_ID
        development.STAGE = STAGE
        record = development._run_job(job, seal_hash)
        record["controller_config"] = {
            "kp": development.KP,
            "ki": development.KI,
            "sync_gain": float(job["arm"]["sync_gain"]),
            "consensus_gain": job["arm"]["consensus_gain"],
            "relative_rocof_gain_system_pu_s_per_hz": job["arm"][
                "relative_rocof_gain"
            ],
            "architecture": job["arm"]["execution"],
        }
        record["mechanism_trace"] = (
            list(_LAST_LOCAL.mechanism_trace) if _LAST_LOCAL is not None else []
        )
        return record
    finally:
        (
            development._controller,
            development.ROUND_ID,
            development.QUESTION_ID,
            development.STAGE,
        ) = original
        _LAST_LOCAL = None


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(f"scenarios=12 arms=3 jobs={len(payload['jobs'])}")


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
    job = next(item for item in seal["jobs"] if item["arm"]["relative_rocof_gain"] == selection.FULL_GAIN)
    path = out_dir / "smoke" / f"{job['name']}.json"
    if path.exists():
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
    trace = record.get("mechanism_trace", [])
    if record["guards"]["completed"] is not True or len(trace) != development.STEPS:
        raise RuntimeError(f"retained smoke failed: {path}")
    if max(abs(row["residual_sum_system_pu"]) for row in trace) > THRESHOLDS[
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


def _contrast(
    candidate: dict[str, dict[str, float]],
    reference: dict[str, dict[str, float]],
    scenarios: list[str],
    *,
    seed_offset: int,
) -> dict[str, Any]:
    rows = {}
    for index, endpoint in enumerate((*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)):
        rows[endpoint] = formal_tools.paired_ratio_interval(
            np.asarray([candidate[name][endpoint] for name in scenarios], dtype=float),
            np.asarray([reference[name][endpoint] for name in scenarios], dtype=float),
            seed=BOOTSTRAP_SEED + seed_offset + index,
            resamples=BOOTSTRAP_REPS,
        )
    return {"candidate_over_reference": rows}


def _primary_gate(contrast: dict[str, Any]) -> dict[str, Any]:
    rows = contrast["candidate_over_reference"]
    common = {
        endpoint: {
            "interval_upper_pass": rows[endpoint]["percentile_95_interval"][1]
            <= THRESHOLDS["common_interval_upper_max"],
            "worst_individual_pass": rows[endpoint]["worst_individual_ratio"]
            <= THRESHOLDS["common_worst_individual_ratio_max"],
        }
        for endpoint in COMMON_ENDPOINTS
    }
    fast = {
        "point_material_pass": rows["fast_inter_area_iae_hz_s"]["point"]
        <= THRESHOLDS["fast_point_ratio_max"],
        "interval_excludes_one_pass": rows["fast_inter_area_iae_hz_s"][
            "percentile_95_interval"
        ][1]
        < THRESHOLDS["fast_interval_upper_exclusive"],
    }
    sync = {
        "point_no_harm_pass": rows["normalized_sync_loss_hz2"]["point"]
        <= THRESHOLDS["sync_point_ratio_max"],
        "interval_no_harm_pass": rows["normalized_sync_loss_hz2"][
            "percentile_95_interval"
        ][1]
        <= THRESHOLDS["sync_interval_upper_max"],
    }
    common_pass = all(all(values.values()) for values in common.values())
    fast_pass = all(fast.values())
    sync_pass = all(sync.values())
    return {
        "passed": common_pass and fast_pass and sync_pass,
        "common_no_harm": common,
        "fast_materiality": fast,
        "sync_no_harm": sync,
        "component_pass": {
            "common": common_pass,
            "fast": fast_pass,
            "sync": sync_pass,
        },
    }


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
        local = job["arm"]["architecture"] == "distributed_dapi"
        zero_sum = (
            max(abs(row["residual_sum_system_pu"]) for row in trace)
            if trace
            else (float("inf") if local else 0.0)
        )
        valid = bool(
            record.get("seal_sha256") == expected_sha256
            and record["guards"]["completed"] is True
            and ((not local) or len(trace) == development.STEPS)
            and zero_sum <= THRESHOLDS["residual_sum_abs_max_system_pu"]
        )
        if not valid:
            invalid.append(job["name"])
            continue
        metrics = summarise_fast_md_trace(
            record,
            final_window_steps=development.FINAL_WINDOW_STEPS,
            fast_window_steps=development.FAST_WINDOW_STEPS,
        )
        arm = job["arm"]["name"]
        scenario = job["scenario"]["name"]
        by_arm.setdefault(arm, {})[scenario] = {
            endpoint: float(metrics[endpoint])
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        if local:
            mechanism.setdefault(arm, {})[scenario] = {
                "residual_request_rms_system_pu": float(
                    np.mean([row["residual_request_rms_system_pu"] for row in trace])
                ),
                "residual_sum_abs_max_system_pu": zero_sum,
            }

    scenarios = sorted(item["name"] for item in seal["scenarios"])
    complete = bool(
        not invalid
        and all(set(by_arm.get(arm["name"], {})) == set(scenarios) for arm in seal["arms"])
    )
    contrasts: dict[str, Any] = {}
    gate: dict[str, Any] = {}
    formulation = "INVALID"
    if complete:
        baseline = by_arm["distributed_dapi_local__kv0"]
        candidate = by_arm["distributed_dapi_local__kv100pct"]
        central = by_arm["central_vector__ks1"]
        contrasts["residual_dapi_over_baseline_dapi"] = _contrast(
            candidate, baseline, scenarios, seed_offset=100
        )
        contrasts["residual_dapi_over_central_vector"] = _contrast(
            candidate, central, scenarios, seed_offset=300
        )
        contrasts["baseline_dapi_over_central_vector"] = _contrast(
            baseline, central, scenarios, seed_offset=500
        )
        gate = _primary_gate(contrasts["residual_dapi_over_baseline_dapi"])
        diff = contrasts["residual_dapi_over_central_vector"]["candidate_over_reference"]
        if all(diff[key]["percentile_95_interval"][1] < 1.0 for key in DIFFERENTIAL_ENDPOINTS):
            formulation = "RESIDUAL-DAPI-EXECUTED-FORMULATION-CLEARER"
        elif all(diff[key]["percentile_95_interval"][0] > 1.0 for key in DIFFERENTIAL_ENDPOINTS):
            formulation = "CENTRAL-EXECUTED-FORMULATION-CLEARER"
        else:
            formulation = "NO-CLEAR-EXECUTED-FORMULATION-DIFFERENCE"

    if not complete:
        classification = "INVALID"
    elif gate["passed"]:
        classification = "VALID-RELATIVE-ROCOF-PASS"
    elif gate["component_pass"]["fast"]:
        classification = "VALID-RELATIVE-ROCOF-TRADEOFF"
    else:
        classification = "VALID-RELATIVE-ROCOF-NO-VALUE"

    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": expected_sha256,
        "classification": classification,
        "executed_formulation_contrast": formulation,
        "guards": {
            "all_records_present_and_valid": complete,
            "invalid_jobs": invalid,
            "record_count": sum(len(rows) for rows in by_arm.values()),
            "expected_record_count": len(seal["jobs"]),
        },
        "primary_candidate_gate": gate,
        "contrasts": contrasts,
        "arm_endpoint_means": {
            arm: {
                endpoint: float(np.mean([row[endpoint] for row in rows.values()]))
                for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
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
        "thresholds": THRESHOLDS,
        "claim_boundary": seal["claim_boundary"],
    }
    path = out_dir / "formal_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={classification}")
    print(f"executed_formulation_contrast={formulation}")
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
