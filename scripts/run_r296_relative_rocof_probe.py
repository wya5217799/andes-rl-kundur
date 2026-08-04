#!/usr/bin/env python3
"""Run R296's sealed zero-sum neighbour relative-RoCoF residual probe."""

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

import run_r294_fast_controller_development as development  # noqa: E402
from andes_rl_kundur.control.coupling_aware_power import (  # noqa: E402
    row_normalized_laplacian,
)
from andes_rl_kundur.control.relative_rocof_residual import (  # noqa: E402
    DecentralizedRelativeRoCoFResidualExecution,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R296"
QUESTION_ID = "Q-0053"
STAGE = "relative_rocof_residual_probe"
SHARD_COUNT = 3
FILTER_TAU_S = 0.2
ANCHOR_MODE_HZ = 1.1352719219086884
ANCHOR_OMEGA_RAD_S = 2.0 * math.pi * ANCHOR_MODE_HZ
FILTER_MAGNITUDE_PER_S = ANCHOR_OMEGA_RAD_S / math.sqrt(
    1.0 + (ANCHOR_OMEGA_RAD_S * FILTER_TAU_S) ** 2
)
RESIDUAL_GAINS = (0.0, 0.25 / FILTER_MAGNITUDE_PER_S, 0.5 / FILTER_MAGNITUDE_PER_S)
DEFAULT_SEAL = ROOT / "memory/rounds/R296/relative_rocof_probe_seal.json"
DEFAULT_OUT = ROOT / "results/r296_relative_rocof_probe"
CONTROLLER_SOURCE = ROOT / "src/andes_rl_kundur/control/relative_rocof_residual.py"
DEVELOPMENT_RUNNER = ROOT / "scripts/run_r294_fast_controller_development.py"
FAST_ENDPOINT_SOURCE = ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
R295_SUMMARY = ROOT / "results/r295_consensus_timescale_probe/development_summary.json"
COMMON_ENDPOINTS = development.COMMON_ENDPOINTS
DIFFERENTIAL_ENDPOINTS = development.DIFFERENTIAL_ENDPOINTS
THRESHOLDS = {
    "fast_inter_area_iae_ratio_max": 0.99,
    "normalized_sync_loss_ratio_max": 1.01,
    "common_mean_ratio_max": 1.05,
    "common_worst_individual_ratio_max": 1.10,
    "residual_sum_abs_max_system_pu": 1e-12,
    "residual_rms_nonzero_min_system_pu": 1e-12,
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
    return [dict(item) for item in development.scenario_bank()]


def arm_bank() -> list[dict[str, Any]]:
    labels = ("kv0", "kv25pct", "kv50pct")
    fractions = (0.0, 0.25, 0.5)
    return [
        {
            "name": f"relative_rocof_local__{label}",
            "architecture": "distributed_dapi",
            "execution": "explicit_local_agents",
            "sync_gain": 1.0,
            "consensus_gain": 1.0,
            "relative_rocof_gain": gain,
            "target_static_sync_fraction": fraction,
        }
        for label, fraction, gain in zip(labels, fractions, RESIDUAL_GAINS, strict=True)
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


def _seal_payload() -> dict[str, Any]:
    _verify_sidecar(R295_SUMMARY)
    laplacian = row_normalized_laplacian(development.COMM_ADJ, device_count=4)
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "outcome_aware_of": ["R294 controller stages", "R295"],
        "plant": "AndesMultiVSGEnvV4Storage full nonlinear DAE",
        "steps": development.STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "controller_gains": {
            "kp_system_pu_per_hz_per_device": development.KP,
            "ki_system_pu_per_hz_s_per_device": development.KI,
            "sync_gain_system_pu_per_hz": 1.0,
            "consensus_gain_per_s": 1.0,
            "rocof_filter_time_constant_s": FILTER_TAU_S,
            "relative_rocof_gain_candidates_system_pu_s_per_hz": list(
                RESIDUAL_GAINS
            ),
        },
        "gain_derivation": {
            "anchor_mode_hz": ANCHOR_MODE_HZ,
            "anchor_omega_rad_s": ANCHOR_OMEGA_RAD_S,
            "continuous_filter_magnitude_per_s": FILTER_MAGNITUDE_PER_S,
            "target_static_sync_fractions": [0.0, 0.25, 0.5],
            "formula": "Kv=fraction/(omega/sqrt(1+(omega*tau)^2))",
        },
        "communication_adjacency": development.COMM_ADJ,
        "row_normalized_laplacian": laplacian.tolist(),
        "zero_sum_reason": "undirected regular ring makes row-normalized L symmetric",
        "thresholds": THRESHOLDS,
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "estimand": (
            "development-only matched-case effect of a locally filtered zero-sum "
            "relative-RoCoF residual on top of explicit DAPI"
        ),
        "claim_boundary": (
            "fixed modified Kundur development diagnosis only; no held-out efficacy, "
            "architecture, MARL, neural, topology-generalization, stability, safety, "
            "robustness, or deployment claim"
        ),
        "prior_evidence": {"r295_summary": _source_entry(R295_SUMMARY)},
        "sources": {
            "runner": _source_entry(Path(__file__).resolve()),
            "controller": _source_entry(CONTROLLER_SOURCE),
            "development_runner": _source_entry(DEVELOPMENT_RUNNER),
            "fast_endpoints": _source_entry(FAST_ENDPOINT_SOURCE),
        },
    }


class RecordingRelativeRoCoF(DecentralizedRelativeRoCoFResidualExecution):
    """Local residual controller plus read-only mechanism telemetry."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.mechanism_trace: list[dict[str, float]] = []

    def act(self, **kwargs: Any) -> np.ndarray:
        request = super().act(**kwargs)
        base = self.last_base_requests_system_pu
        residual = self.last_residual_requests_system_pu
        filtered = self.last_filtered_rocof_hz_s
        count = math.sqrt(self.device_count)
        self.mechanism_trace.append(
            {
                "base_request_differential_rms_system_pu": float(
                    np.linalg.norm(base - np.mean(base)) / count
                ),
                "residual_request_rms_system_pu": float(
                    np.linalg.norm(residual) / count
                ),
                "total_request_differential_rms_system_pu": float(
                    np.linalg.norm(request - np.mean(request)) / count
                ),
                "filtered_rocof_differential_rms_hz_s": float(
                    np.linalg.norm(filtered - np.mean(filtered)) / count
                ),
                "residual_sum_system_pu": float(np.sum(residual)),
            }
        )
        return request


_LAST_CONTROLLER: RecordingRelativeRoCoF | None = None


def _local_controller(arm: dict[str, Any], *, device_count: int, nominal_hz: float):
    global _LAST_CONTROLLER
    _LAST_CONTROLLER = RecordingRelativeRoCoF(
        adjacency=development.COMM_ADJ,
        device_count=device_count,
        nominal_frequency_hz=nominal_hz,
        kp_system_pu_per_hz_per_device=development.KP,
        ki_system_pu_per_hz_s_per_device=development.KI,
        sync_gain_system_pu_per_hz=float(arm["sync_gain"]),
        consensus_gain_per_s=float(arm["consensus_gain"]),
        rocof_filter_time_constant_s=FILTER_TAU_S,
        relative_rocof_gain_system_pu_s_per_hz=float(arm["relative_rocof_gain"]),
    )
    return _LAST_CONTROLLER


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    global _LAST_CONTROLLER
    original = {
        "factory": development._controller,
        "stage": development.STAGE,
        "round": development.ROUND_ID,
        "question": development.QUESTION_ID,
    }
    _LAST_CONTROLLER = None
    try:
        development._controller = _local_controller
        development.STAGE = STAGE
        development.ROUND_ID = ROUND_ID
        development.QUESTION_ID = QUESTION_ID
        record = development._run_job(job, seal_hash)
        record["controller_config"] = {
            "kp": development.KP,
            "ki": development.KI,
            "sync_gain": float(job["arm"]["sync_gain"]),
            "consensus_gain": float(job["arm"]["consensus_gain"]),
            "rocof_filter_time_constant_s": FILTER_TAU_S,
            "relative_rocof_gain_system_pu_s_per_hz": float(
                job["arm"]["relative_rocof_gain"]
            ),
            "architecture": DecentralizedRelativeRoCoFResidualExecution.architecture,
        }
        record["mechanism_trace"] = (
            list(_LAST_CONTROLLER.mechanism_trace) if _LAST_CONTROLLER is not None else []
        )
        return record
    finally:
        development._controller = original["factory"]
        development.STAGE = original["stage"]
        development.ROUND_ID = original["round"]
        development.QUESTION_ID = original["question"]
        _LAST_CONTROLLER = None


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
    for group in ("sources", "prior_evidence"):
        for name, entry in seal[group].items():
            if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
                raise RuntimeError(f"sealed source drift for {group}.{name}")
    return seal


def smoke(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    job = next(item for item in seal["jobs"] if item["arm"]["target_static_sync_fraction"] == 0.5)
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
        raise RuntimeError("retained smoke violates zero-sum residual contract")
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


def _safe_ratio(value: float, reference: float) -> float:
    if math.isclose(reference, 0.0, rel_tol=0.0, abs_tol=1e-15):
        return 1.0 if math.isclose(value, 0.0, abs_tol=1e-15) else float("inf")
    return value / reference


def evaluate_candidate(
    candidate: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]],
    *,
    residual_rms: float,
) -> dict[str, Any]:
    scenarios = sorted(baseline)
    endpoints = (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
    mean_ratios = {
        endpoint: _safe_ratio(
            float(np.mean([candidate[name][endpoint] for name in scenarios])),
            float(np.mean([baseline[name][endpoint] for name in scenarios])),
        )
        for endpoint in endpoints
    }
    paired_common_ratios = {
        name: {
            endpoint: _safe_ratio(candidate[name][endpoint], baseline[name][endpoint])
            for endpoint in COMMON_ENDPOINTS
        }
        for name in scenarios
    }
    worst_common = max(
        value for row in paired_common_ratios.values() for value in row.values()
    )
    gates = {
        "fast_inter_area_improvement": mean_ratios["fast_inter_area_iae_hz_s"]
        <= THRESHOLDS["fast_inter_area_iae_ratio_max"],
        "sync_no_harm": mean_ratios["normalized_sync_loss_hz2"]
        <= THRESHOLDS["normalized_sync_loss_ratio_max"],
        "common_mean_no_harm": all(
            mean_ratios[endpoint] <= THRESHOLDS["common_mean_ratio_max"]
            for endpoint in COMMON_ENDPOINTS
        ),
        "common_individual_no_harm": worst_common
        <= THRESHOLDS["common_worst_individual_ratio_max"],
        "residual_nonzero": residual_rms
        > THRESHOLDS["residual_rms_nonzero_min_system_pu"],
    }
    return {
        "passed": all(gates.values()),
        "gates": gates,
        "mean_endpoint_ratios": mean_ratios,
        "worst_individual_common_endpoint_ratio": worst_common,
        "paired_common_ratios": paired_common_ratios,
        "mean_residual_rms_system_pu": residual_rms,
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
        residual_sum_max = (
            max(abs(row["residual_sum_system_pu"]) for row in trace)
            if trace
            else float("inf")
        )
        valid = bool(
            record.get("seal_sha256") == expected_sha256
            and record["guards"]["completed"] is True
            and len(trace) == development.STEPS
            and residual_sum_max <= THRESHOLDS["residual_sum_abs_max_system_pu"]
        )
        if not valid:
            invalid.append(job["name"])
            continue
        metrics = summarise_fast_md_trace(
            record,
            final_window_steps=development.FINAL_WINDOW_STEPS,
            fast_window_steps=development.FAST_WINDOW_STEPS,
        )
        arm_name = job["arm"]["name"]
        scenario_name = job["scenario"]["name"]
        by_arm.setdefault(arm_name, {})[scenario_name] = {
            endpoint: float(metrics[endpoint])
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        mechanism.setdefault(arm_name, {})[scenario_name] = {
            **{
                field: float(np.mean([row[field] for row in trace]))
                for field in trace[0]
                if field != "residual_sum_system_pu"
            },
            "residual_sum_abs_max_system_pu": residual_sum_max,
        }

    expected_scenarios = {item["name"] for item in seal["scenarios"]}
    baseline_name = "relative_rocof_local__kv0"
    baseline = by_arm.get(baseline_name, {})
    complete = bool(
        not invalid
        and set(baseline) == expected_scenarios
        and all(set(by_arm.get(arm["name"], {})) == expected_scenarios for arm in seal["arms"])
    )
    candidates: dict[str, Any] = {}
    if complete:
        for arm in seal["arms"]:
            if float(arm["relative_rocof_gain"]) == 0.0:
                continue
            mechanism_rows = mechanism[arm["name"]].values()
            residual_rms = float(
                np.mean([row["residual_request_rms_system_pu"] for row in mechanism_rows])
            )
            candidates[arm["name"]] = {
                "relative_rocof_gain_system_pu_s_per_hz": float(
                    arm["relative_rocof_gain"]
                ),
                "target_static_sync_fraction": float(
                    arm["target_static_sync_fraction"]
                ),
                **evaluate_candidate(
                    by_arm[arm["name"]],
                    baseline,
                    residual_rms=residual_rms,
                ),
            }

    passed = [(name, row) for name, row in candidates.items() if row["passed"]]
    selected = (
        min(
            passed,
            key=lambda pair: (
                pair[1]["mean_endpoint_ratios"]["fast_inter_area_iae_hz_s"],
                pair[1]["relative_rocof_gain_system_pu_s_per_hz"],
            ),
        )[0]
        if passed
        else None
    )
    if not complete:
        classification = "INVALID-RELATIVE-ROCOF-PROBE"
    elif selected is not None:
        classification = "RELATIVE-ROCOF-CANDIDATE-IDENTIFIED"
    else:
        classification = "RELATIVE-ROCOF-NO-GO"

    arm_endpoint_means = {
        arm: {
            endpoint: float(np.mean([row[endpoint] for row in rows.values()]))
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        for arm, rows in by_arm.items()
        if rows
    }
    mechanism_means = {
        arm: {
            field: float(np.mean([row[field] for row in rows.values()]))
            if field != "residual_sum_abs_max_system_pu"
            else float(max(row[field] for row in rows.values()))
            for field in next(iter(rows.values()))
        }
        for arm, rows in mechanism.items()
        if rows
    }
    summary = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "seal_sha256": expected_sha256,
        "classification": classification,
        "selected_candidate": selected,
        "invalid_jobs": invalid,
        "record_count": sum(len(rows) for rows in by_arm.values()),
        "expected_record_count": len(seal["jobs"]),
        "thresholds": THRESHOLDS,
        "candidates": candidates,
        "arm_endpoint_means": arm_endpoint_means,
        "mechanism_diagnostic_means": mechanism_means,
        "claim_boundary": seal["claim_boundary"],
        "next_step": (
            "open a separately sealed full held-out evaluation on a disjoint bank"
            if classification == "RELATIVE-ROCOF-CANDIDATE-IDENTIFIED"
            else "close the relative-RoCoF residual negative before another structure"
            if classification == "RELATIVE-ROCOF-NO-GO"
            else "diagnose validity only; performance endpoints are non-evidence"
        ),
    }
    path = out_dir / "development_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={classification}")
    print(f"selected_candidate={selected}")
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
