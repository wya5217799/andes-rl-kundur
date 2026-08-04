#!/usr/bin/env python3
"""Run R294's sealed 20-trajectory coupling-aware development screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.control.active_power import (  # noqa: E402
    DroopPIActivePowerController,
)
from andes_rl_kundur.control.coupling_aware_power import (  # noqa: E402
    CentralizedCouplingAwarePI,
    DistributedDAPIController,
)
from andes_rl_kundur.evaluation.fast_md_authority import (  # noqa: E402
    summarise_fast_md_trace,
)

ROUND_ID = "R294"
QUESTION_ID = "Q-0051"
STAGE = "stage_c_fast_controller_development_v1"
STEPS = 100
SHARD_COUNT = 3
FINAL_WINDOW_STEPS = 25
FAST_WINDOW_STEPS = 15
KP = 2.0
KI = 0.2
SYNC_GAINS = (0.0, 1.0)
CONSENSUS_GAIN = 1.0
TIE_IDX = ("Line_4", "Line_5", "Line_6")
COMM_ADJ = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}
DEFAULT_SEAL = ROOT / "memory/rounds/R294/stage_c_fast_controller_development_seal.json"
DEFAULT_OUT = ROOT / "results/r294_model_validation/stage_c_fast_controller_development_v1"
PROTOCOL = ROOT / "memory/rounds/R294/stage_c_fast_controller_development_protocol.md"
CONTROLLER_SOURCE = ROOT / "src/andes_rl_kundur/control/coupling_aware_power.py"
ACTIVE_POWER_SOURCE = ROOT / "src/andes_rl_kundur/control/active_power.py"
ENDPOINT_SOURCE = ROOT / "src/andes_rl_kundur/evaluation/physical_endpoints.py"
FAST_ENDPOINT_SOURCE = ROOT / "src/andes_rl_kundur/evaluation/fast_md_authority.py"
BASE_ENV_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
ENV_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
STORAGE_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
COMMON_ENDPOINTS = (
    "vsg_mean_iae_hz_s",
    "worst_bus_peak_abs_hz",
    "max_abs_rocof_hz_s",
)
DIFFERENTIAL_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
THRESHOLDS = {
    "individual_common_harm_ratio_max": 1.05,
    "mean_normalized_sync_loss_ratio_max": 0.98,
    "mean_fast_inter_area_iae_ratio_max": 0.98,
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
    return [
        {"name": "k1__pq_0__pos", "tie_k": 1.0, "location": "PQ_0", "delta_u": 1.0},
        {"name": "k1__pq_bus15__neg", "tie_k": 1.0, "location": "PQ_Bus15", "delta_u": -1.0},
        {"name": "k2__pq_1__pos", "tie_k": 2.0, "location": "PQ_1", "delta_u": 1.0},
        {"name": "k2__pq_bus14__neg", "tie_k": 2.0, "location": "PQ_Bus14", "delta_u": -1.0},
    ]


def arm_bank() -> list[dict[str, Any]]:
    arms: list[dict[str, Any]] = [
        {
            "name": "equal_sharing_pi",
            "architecture": "scalar_equal_sharing",
            "sync_gain": None,
        }
    ]
    for architecture in ("central_vector", "distributed_dapi"):
        for sync_gain in SYNC_GAINS:
            arms.append(
                {
                    "name": f"{architecture}__ks{sync_gain:g}",
                    "architecture": architecture,
                    "sync_gain": sync_gain,
                }
            )
    return arms


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
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "development_only": True,
        "outcome_aware_of": [
            "R294 Stage-A model validation",
            "R294 Stage-B actuator authority",
        ],
        "plant": "AndesMultiVSGEnvV4Storage full nonlinear DAE",
        "steps": STEPS,
        "dt_seconds": 0.2,
        "shard_count": SHARD_COUNT,
        "controller_gains": {
            "kp_system_pu_per_hz_per_device": KP,
            "ki_system_pu_per_hz_s_per_device": KI,
            "sync_gain_candidates_system_pu_per_hz": list(SYNC_GAINS),
            "distributed_consensus_gain_per_s": CONSENSUS_GAIN,
        },
        "communication_adjacency": COMM_ADJ,
        "thresholds": THRESHOLDS,
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "estimand": (
            "descriptive matched-case development screen for whether a coupling-aware "
            "independent-P vector law improves differential endpoints without material "
            "common-frequency harm relative to scalar equal-sharing PI"
        ),
        "claim_boundary": (
            "outcome-aware development only; no efficacy, architecture superiority, "
            "MARL, MPC, topology-generalization, or deployment claim"
        ),
        "sources": {
            "protocol": _source_entry(PROTOCOL),
            "runner": _source_entry(Path(__file__).resolve()),
            "controller": _source_entry(CONTROLLER_SOURCE),
            "active_power_contract": _source_entry(ACTIVE_POWER_SOURCE),
            "physical_endpoints": _source_entry(ENDPOINT_SOURCE),
            "fast_endpoints": _source_entry(FAST_ENDPOINT_SOURCE),
            "base_environment": _source_entry(BASE_ENV_SOURCE),
            "environment": _source_entry(ENV_SOURCE),
            "storage_environment": _source_entry(STORAGE_SOURCE),
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


def _controller(arm: dict[str, Any], *, device_count: int, nominal_hz: float):
    common = {
        "device_count": device_count,
        "nominal_frequency_hz": nominal_hz,
        "kp_system_pu_per_hz_per_device": KP,
        "ki_system_pu_per_hz_s_per_device": KI,
    }
    if arm["architecture"] == "scalar_equal_sharing":
        return DroopPIActivePowerController(**common)
    if arm["architecture"] == "central_vector":
        return CentralizedCouplingAwarePI(
            **common,
            sync_gain_system_pu_per_hz=float(arm["sync_gain"]),
        )
    if arm["architecture"] == "distributed_dapi":
        return DistributedDAPIController(
            **common,
            adjacency=COMM_ADJ,
            sync_gain_system_pu_per_hz=float(arm["sync_gain"]),
            consensus_gain_per_s=CONSENSUS_GAIN,
        )
    raise ValueError(f"unknown architecture: {arm['architecture']}")


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    os.environ["DISABLE_TOGGLER"] = "1"
    import andes

    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    tie_k = float(job["scenario"]["tie_k"])

    class DevelopmentEnvironment(AndesMultiVSGEnvV4Storage):
        def _build_system(self):
            system = super()._build_system()
            if abs(tie_k - 1.0) > 1e-12:
                for idx in TIE_IDX:
                    position = list(system.Line.idx.v).index(idx)
                    system.Line.set("r", idx, float(system.Line.r.v[position] * tie_k), attr="v")
                    system.Line.set("x", idx, float(system.Line.x.v[position] * tie_k), attr="v")
            return system

    env = DevelopmentEnvironment(random_disturbance=False, comm_fail_prob=0.0)
    traces: list[dict[str, Any]] = []
    tds_failed = False
    tds_test_ok = False
    exit_code = 1
    failure: str | None = None
    nominal = 60.0
    started = time.perf_counter()
    try:
        env.seed(42)
        env.STEPS_PER_EPISODE = STEPS
        env.reset(
            delta_u={
                str(job["scenario"]["location"]): float(job["scenario"]["delta_u"])
            }
        )
        nominal = float(env.andes_nominal_frequency_hz)
        controller = _controller(
            job["arm"],
            device_count=env.bess_contract.device_count,
            nominal_hz=nominal,
        )
        zero_md = {index: np.zeros(2, dtype=float) for index in range(env.N_AGENTS)}
        for step in range(STEPS):
            requested_power = controller.act(
                frequencies_hz=env.get_vsg_frequency_physical_hz(),
                dt_seconds=env.DT,
                previous_projection=env.last_bess_projection,
            )
            _, _, done, info = env.step(
                zero_md,
                bess_power_request_pu=requested_power,
            )
            if info.get("tds_failed"):
                tds_failed = True
                break
            frequency = np.asarray(info["freq_hz_physical"], dtype=float)
            traces.append(
                {
                    "step": step,
                    "t": float(info["time"]),
                    "freq_hz_physical": frequency.tolist(),
                    "delta_f_physical_hz": (frequency - nominal).tolist(),
                    "action_norm": [[0.0, 0.0] for _ in range(env.N_AGENTS)],
                    "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
                    "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
                    "bess_requested_power_system_pu": np.asarray(
                        info["bess_requested_power_system_pu"], dtype=float
                    ).tolist(),
                    "bess_commanded_power_system_pu": np.asarray(
                        info["bess_commanded_power_system_pu"], dtype=float
                    ).tolist(),
                    "bess_actual_power_system_pu": np.asarray(
                        info["bess_actual_power_system_pu"], dtype=float
                    ).tolist(),
                    "bess_soc": np.asarray(info["bess_soc"], dtype=float).tolist(),
                    "bess_bus_voltage_pu": np.asarray(
                        info["bess_bus_voltage_pu"], dtype=float
                    ).tolist(),
                    "bess_saturation_reasons": info["bess_saturation_reasons"],
                    "bess_charge_energy_mwh_total": np.asarray(
                        info["bess_charge_energy_mwh_total"], dtype=float
                    ).tolist(),
                    "bess_discharge_energy_mwh_total": np.asarray(
                        info["bess_discharge_energy_mwh_total"], dtype=float
                    ).tolist(),
                    "bess_constraint_violations": info["bess_constraint_violations"],
                }
            )
            if done:
                break
        tds_test_ok = bool(env.ss.TDS.test_ok)
        exit_code = int(env.ss.exit_code)
    except Exception as exc:  # retained development failure
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            env.close()
        except Exception as exc:  # pragma: no cover
            if failure is None:
                failure = f"close {type(exc).__name__}: {exc}"

    arrays: list[Any] = []
    for trace in traces:
        arrays.extend(
            [
                trace["delta_f_physical_hz"],
                trace["bess_requested_power_system_pu"],
                trace["bess_commanded_power_system_pu"],
                trace["bess_soc"],
            ]
        )
    finite = bool(arrays and np.all(np.isfinite(np.asarray(arrays, dtype=float))))
    violations = [
        violation for trace in traces for violation in trace["bess_constraint_violations"]
    ]
    action_contract: dict[str, Any] = {}
    action_contract_pass = False
    if len(traces) == STEPS:
        requested = np.asarray(
            [trace["bess_requested_power_system_pu"] for trace in traces], dtype=float
        )
        commanded = np.asarray(
            [trace["bess_commanded_power_system_pu"] for trace in traces], dtype=float
        )
        soc = np.asarray([trace["bess_soc"] for trace in traces], dtype=float)
        slew = np.diff(np.concatenate([np.zeros((1, 4)), commanded], axis=0), axis=0)
        scalar_action_exact = bool(
            np.allclose(requested, requested[:, :1], rtol=0.0, atol=1e-12)
        )
        vector_action_observed = bool(np.max(np.ptp(requested, axis=1)) > 1e-8)
        architecture = job["arm"]["architecture"]
        action_contract = {
            "power_nameplate_pass": bool(np.max(np.abs(commanded)) <= 0.36 + 1e-12),
            "power_ramp_pass": bool(np.max(np.abs(slew)) <= 0.072 + 1e-12),
            "soc_bounds_pass": bool(np.min(soc) >= 0.2 - 1e-9 and np.max(soc) <= 0.8 + 1e-9),
            "declared_action_shape_pass": (
                scalar_action_exact if architecture == "scalar_equal_sharing" else vector_action_observed
            ),
            "scalar_action_exact": scalar_action_exact,
            "vector_action_observed": vector_action_observed,
        }
        action_contract_pass = all(
            action_contract[key]
            for key in (
                "power_nameplate_pass",
                "power_ramp_pass",
                "soc_bounds_pass",
                "declared_action_shape_pass",
            )
        )
    completed = bool(
        failure is None
        and not tds_failed
        and len(traces) == STEPS
        and tds_test_ok
        and exit_code == 0
        and finite
        and not violations
        and action_contract_pass
    )
    return {
        "experiment": STAGE,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_hash,
        "job": job,
        "controller": job["arm"]["name"],
        "scenario": job["scenario"]["name"],
        "env_version": "v4_plus_independent_esd1",
        "control_nominal_frequency_hz": float(env.FN),
        "andes_nominal_frequency_hz": nominal,
        "frequency_reporting_basis": "legacy_control_hz",
        "metric_frequency_basis": "andes_physical_hz",
        "requested_steps": STEPS,
        "n_steps": len(traces),
        "tds_failed": tds_failed,
        "completed": completed,
        "guards": {
            "completed": completed,
            "tds_test_ok": tds_test_ok,
            "system_exit_code": exit_code,
            "finite_telemetry": finite,
            "storage_constraint_violation_count": len(violations),
            "action_contract_pass": action_contract_pass,
            "action_contract": action_contract,
            "failure": failure,
        },
        "controller_config": {
            "kp": KP,
            "ki": KI,
            "sync_gain": job["arm"]["sync_gain"],
            "consensus_gain": (
                CONSENSUS_GAIN if job["arm"]["architecture"] == "distributed_dapi" else None
            ),
            "architecture": job["arm"]["architecture"],
        },
        "runtime": {
            "wall_clock_seconds": time.perf_counter() - started,
            "python": sys.version,
            "platform": platform.platform(),
            "andes_version": getattr(andes, "__version__", "unknown"),
        },
        "traces": traces,
    }


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


def _safe_ratio(value: float, reference: float) -> float:
    if math.isclose(reference, 0.0, rel_tol=0.0, abs_tol=1e-15):
        return 1.0 if math.isclose(value, 0.0, abs_tol=1e-15) else float("inf")
    return value / reference


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
            final_window_steps=FINAL_WINDOW_STEPS,
            fast_window_steps=FAST_WINDOW_STEPS,
        )
        by_arm.setdefault(job["arm"]["name"], {})[job["scenario"]["name"]] = metrics

    expected_scenarios = {item["name"] for item in seal["scenarios"]}
    baseline = by_arm.get("equal_sharing_pi", {})
    candidates: dict[str, Any] = {}
    for arm in seal["arms"]:
        name = arm["name"]
        if name == "equal_sharing_pi":
            continue
        rows = by_arm.get(name, {})
        complete = set(rows) == expected_scenarios and set(baseline) == expected_scenarios
        common_ratios: dict[str, dict[str, float]] = {}
        differential_ratios: dict[str, dict[str, float]] = {}
        if complete:
            for scenario in sorted(expected_scenarios):
                common_ratios[scenario] = {
                    endpoint: _safe_ratio(
                        float(rows[scenario][endpoint]),
                        float(baseline[scenario][endpoint]),
                    )
                    for endpoint in COMMON_ENDPOINTS
                }
                differential_ratios[scenario] = {
                    endpoint: _safe_ratio(
                        float(rows[scenario][endpoint]),
                        float(baseline[scenario][endpoint]),
                    )
                    for endpoint in DIFFERENTIAL_ENDPOINTS
                }
        mean_differential = {
            endpoint: (
                float(np.mean([values[endpoint] for values in differential_ratios.values()]))
                if differential_ratios
                else float("inf")
            )
            for endpoint in DIFFERENTIAL_ENDPOINTS
        }
        max_common_harm = (
            max(value for values in common_ratios.values() for value in values.values())
            if common_ratios
            else float("inf")
        )
        eligible = bool(
            complete
            and max_common_harm <= THRESHOLDS["individual_common_harm_ratio_max"]
            and mean_differential["normalized_sync_loss_hz2"]
            <= THRESHOLDS["mean_normalized_sync_loss_ratio_max"]
            and mean_differential["fast_inter_area_iae_hz_s"]
            <= THRESHOLDS["mean_fast_inter_area_iae_ratio_max"]
        )
        score = (
            math.sqrt(
                mean_differential["normalized_sync_loss_hz2"]
                * mean_differential["fast_inter_area_iae_hz_s"]
            )
            if complete
            else float("inf")
        )
        candidates[name] = {
            "architecture": arm["architecture"],
            "sync_gain": arm["sync_gain"],
            "complete": complete,
            "eligible": eligible,
            "differential_geometric_mean_score": score,
            "max_individual_common_endpoint_ratio": max_common_harm,
            "mean_differential_ratios": mean_differential,
            "paired_common_ratios": common_ratios,
            "paired_differential_ratios": differential_ratios,
        }

    selected: dict[str, str | None] = {}
    for architecture in ("central_vector", "distributed_dapi"):
        eligible = [
            (name, item)
            for name, item in candidates.items()
            if item["architecture"] == architecture and item["eligible"]
        ]
        selected[architecture] = (
            min(eligible, key=lambda pair: pair[1]["differential_geometric_mean_score"])[0]
            if eligible
            else None
        )
    if invalid:
        classification = "INVALID-DEVELOPMENT-BANK"
    elif selected["distributed_dapi"] is None:
        classification = "DISTRIBUTED-LAW-REQUIRES-REVISION"
    elif selected["central_vector"] is None:
        classification = "CENTRAL-LAW-REQUIRES-REVISION"
    else:
        classification = "FAST-DEVELOPMENT-CANDIDATES-IDENTIFIED"

    arm_means = {
        name: {
            endpoint: float(np.mean([row[endpoint] for row in rows.values()]))
            for endpoint in (*COMMON_ENDPOINTS, *DIFFERENTIAL_ENDPOINTS)
        }
        for name, rows in by_arm.items()
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
        "invalid_jobs": invalid,
        "record_count": sum(len(rows) for rows in by_arm.values()),
        "expected_record_count": len(seal["jobs"]),
        "selected_candidates": selected,
        "thresholds": THRESHOLDS,
        "candidates": candidates,
        "arm_endpoint_means": arm_means,
        "claim_boundary": seal["claim_boundary"],
        "next_step": (
            "freeze a compact held-out comparison using only the selected gains"
            if classification == "FAST-DEVELOPMENT-CANDIDATES-IDENTIFIED"
            else "diagnose the failed controller law without expanding the scenario bank"
        ),
    }
    path = out_dir / "development_summary.json"
    digest = _write_new(path, summary)
    print(f"classification={classification}")
    print(f"selected={json.dumps(selected, sort_keys=True)}")
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
