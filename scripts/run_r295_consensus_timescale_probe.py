#!/usr/bin/env python3
"""Run R295's sealed graph-spectral DAPI consensus-time-scale probe."""

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
from andes_rl_kundur.control.decentralized_dapi import (  # noqa: E402
    DecentralizedDAPIExecution,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R295"
QUESTION_ID = "Q-0052"
STAGE = "consensus_timescale_probe"
SHARD_COUNT = 3
CONSENSUS_GAINS = (1.0, 2.0, 4.0)
BASELINE_GAIN = 1.0
DEFAULT_SEAL = ROOT / "memory/rounds/R295/consensus_timescale_probe_seal.json"
DEFAULT_OUT = ROOT / "results/r295_consensus_timescale_probe"
PROTOCOL = ROOT / "memory/rounds/R295/consensus_timescale_probe_protocol.md"
LOCAL_SOURCE = ROOT / "src/andes_rl_kundur/control/decentralized_dapi.py"
DEVELOPMENT_RUNNER = ROOT / "scripts/run_r294_fast_controller_development.py"
FAST_ENDPOINT_SOURCE = ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
R294_STAGE_A_SUMMARY = ROOT / "results/r294_model_validation/stage_a/stage_a_summary.json"
R294_ROUND_SUMMARY = ROOT / "results/r294_model_validation/round_summary.json"
COMMON_ENDPOINTS = development.COMMON_ENDPOINTS
DIFFERENTIAL_ENDPOINTS = development.DIFFERENTIAL_ENDPOINTS
THRESHOLDS = {
    "fast_inter_area_iae_ratio_max": 0.99,
    "normalized_sync_loss_ratio_max": 1.01,
    "common_mean_ratio_max": 1.05,
    "common_worst_individual_ratio_max": 1.10,
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
    return [
        {
            "name": f"distributed_dapi_local__kc{gain:g}",
            "architecture": "distributed_dapi",
            "execution": "explicit_local_agents",
            "sync_gain": 1.0,
            "consensus_gain": gain,
        }
        for gain in CONSENSUS_GAINS
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


def _graph_spectral_contract() -> dict[str, Any]:
    laplacian = row_normalized_laplacian(
        development.COMM_ADJ,
        device_count=4,
    )
    eigenvalues = np.linalg.eigvalsh(laplacian)
    dt = 0.2
    return {
        "row_normalized_laplacian": laplacian.tolist(),
        "eigenvalues": eigenvalues.tolist(),
        "candidate_discrete_factors_by_gain": {
            f"{gain:g}": (1.0 - dt * gain * eigenvalues).tolist()
            for gain in CONSENSUS_GAINS
        },
        "registered_anchor_inter_area_frequency_hz": 1.1352719219086884,
        "interpretation": (
            "kc affects only graph-differential integral modes in the ideal "
            "controller coordinates; nonlinear plant cross-coupling remains measured"
        ),
    }


def _seal_payload() -> dict[str, Any]:
    _verify_sidecar(R294_STAGE_A_SUMMARY)
    _verify_sidecar(R294_ROUND_SUMMARY)
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "outcome_aware_of": ["R294 Stage C", "R294 Stage D", "R294 Stage E"],
        "plant": "AndesMultiVSGEnvV4Storage full nonlinear DAE",
        "steps": development.STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "controller_gains": {
            "kp_system_pu_per_hz_per_device": development.KP,
            "ki_system_pu_per_hz_s_per_device": development.KI,
            "sync_gain_system_pu_per_hz": 1.0,
            "consensus_gain_candidates_per_s": list(CONSENSUS_GAINS),
        },
        "communication_adjacency": development.COMM_ADJ,
        "graph_spectral_contract": _graph_spectral_contract(),
        "thresholds": THRESHOLDS,
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "estimand": (
            "development-only matched-case effect of changing the explicit local "
            "DAPI integral-consensus gain from 1/s to 2/s or 4/s"
        ),
        "claim_boundary": (
            "fixed modified Kundur development diagnosis only; no held-out efficacy, "
            "architecture, MARL, neural, topology-generalization, stability, safety, "
            "or deployment claim"
        ),
        "prior_evidence": {
            "r294_stage_a_summary": _source_entry(R294_STAGE_A_SUMMARY),
            "r294_round_summary": _source_entry(R294_ROUND_SUMMARY),
        },
        "sources": {
            "protocol": _source_entry(PROTOCOL),
            "runner": _source_entry(Path(__file__).resolve()),
            "local_controller": _source_entry(LOCAL_SOURCE),
            "development_runner": _source_entry(DEVELOPMENT_RUNNER),
            "fast_endpoints": _source_entry(FAST_ENDPOINT_SOURCE),
        },
    }


class RecordingLocalDAPI(DecentralizedDAPIExecution):
    """Explicit local DAPI plus read-only internal mechanism telemetry."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.laplacian = row_normalized_laplacian(
            self.adjacency,
            device_count=self.device_count,
        )
        self.mechanism_trace: list[dict[str, float]] = []

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection=None,
    ) -> np.ndarray:
        frequency = np.asarray(frequencies_hz, dtype=float)
        request = super().act(
            frequencies_hz=frequency,
            dt_seconds=dt_seconds,
            previous_projection=previous_projection,
        )
        integral = np.asarray(
            [agent.integral_power_system_pu for agent in self.agents],
            dtype=float,
        )
        self.mechanism_trace.append(
            {
                "integral_graph_differential_rms_system_pu": float(
                    np.linalg.norm(self.laplacian @ integral) / math.sqrt(self.device_count)
                ),
                "frequency_graph_differential_rms_hz": float(
                    np.linalg.norm(self.laplacian @ frequency) / math.sqrt(self.device_count)
                ),
                "requested_power_differential_rms_system_pu": float(
                    np.linalg.norm(request - np.mean(request)) / math.sqrt(self.device_count)
                ),
            }
        )
        return request


_LAST_CONTROLLER: RecordingLocalDAPI | None = None


def _local_controller(arm: dict[str, Any], *, device_count: int, nominal_hz: float):
    global _LAST_CONTROLLER
    if arm["architecture"] != "distributed_dapi":
        raise ValueError("R295 accepts only explicit local-agent DAPI")
    _LAST_CONTROLLER = RecordingLocalDAPI(
        adjacency=development.COMM_ADJ,
        device_count=device_count,
        nominal_frequency_hz=nominal_hz,
        kp_system_pu_per_hz_per_device=development.KP,
        ki_system_pu_per_hz_s_per_device=development.KI,
        sync_gain_system_pu_per_hz=float(arm["sync_gain"]),
        consensus_gain_per_s=float(arm["consensus_gain"]),
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
            "architecture": "explicit_local_agents_neighbour_messages_independent_actions",
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
    job = next(item for item in seal["jobs"] if item["arm"]["consensus_gain"] == 4.0)
    path = out_dir / "smoke" / f"{job['name']}.json"
    if path.exists():
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        record = _run_job(job, expected_sha256)
        _write_new(path, record)
    if record["guards"]["completed"] is not True:
        raise RuntimeError(f"retained smoke failed: {path}")
    if len(record["mechanism_trace"]) != development.STEPS:
        raise RuntimeError("retained smoke lacks complete mechanism telemetry")
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
    }
    return {
        "passed": all(gates.values()),
        "gates": gates,
        "mean_endpoint_ratios": mean_ratios,
        "worst_individual_common_endpoint_ratio": worst_common,
        "paired_common_ratios": paired_common_ratios,
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
        if record.get("seal_sha256") != expected_sha256:
            raise RuntimeError(f"record seal mismatch: {path}")
        trace = record.get("mechanism_trace", [])
        if record["guards"]["completed"] is not True or len(trace) != development.STEPS:
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
            field: float(np.mean([row[field] for row in trace]))
            for field in trace[0]
        }

    expected_scenarios = {item["name"] for item in seal["scenarios"]}
    baseline_name = f"distributed_dapi_local__kc{BASELINE_GAIN:g}"
    baseline = by_arm.get(baseline_name, {})
    complete = bool(
        not invalid
        and set(baseline) == expected_scenarios
        and all(set(by_arm.get(arm["name"], {})) == expected_scenarios for arm in seal["arms"])
    )
    candidates: dict[str, Any] = {}
    if complete:
        for arm in seal["arms"]:
            if float(arm["consensus_gain"]) == BASELINE_GAIN:
                continue
            candidates[arm["name"]] = {
                "consensus_gain_per_s": float(arm["consensus_gain"]),
                **evaluate_candidate(by_arm[arm["name"]], baseline),
            }

    passed = [(name, row) for name, row in candidates.items() if row["passed"]]
    selected = (
        min(
            passed,
            key=lambda pair: (
                pair[1]["mean_endpoint_ratios"]["fast_inter_area_iae_hz_s"],
                pair[1]["consensus_gain_per_s"],
            ),
        )[0]
        if passed
        else None
    )
    if not complete:
        classification = "INVALID-CONSENSUS-TIMESCALE-PROBE"
    elif selected is not None:
        classification = "CONSENSUS-TIMESCALE-CANDIDATE-IDENTIFIED"
    else:
        classification = "CONSENSUS-TIMESCALE-NO-GO"

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
            if classification == "CONSENSUS-TIMESCALE-CANDIDATE-IDENTIFIED"
            else "stop consensus-gain tuning and design an antisymmetric edge residual"
            if classification == "CONSENSUS-TIMESCALE-NO-GO"
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
