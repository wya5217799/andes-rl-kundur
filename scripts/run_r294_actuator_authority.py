#!/usr/bin/env python3
"""Run the sealed R294 Stage-B full-DAE M/D/P authority map.

Commands:
    python scripts/run_r294_actuator_authority.py prepare
    python scripts/andes_scratch.py scripts/run_r294_actuator_authority.py smoke \
      --expected-seal-sha256 HASH
    python scripts/andes_scratch.py scripts/run_r294_actuator_authority.py run \
      --expected-seal-sha256 HASH --shard-index 0 --shard-count 3
    python scripts/run_r294_actuator_authority.py analyse \
      --expected-seal-sha256 HASH
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.coupled_actuator_authority import (  # noqa: E402
    aggregate_authority,
    paired_authority_metrics,
    physical_coordinate_matrix,
)

ROUND_ID = "R294"
QUESTION_ID = "Q-0051"
STAGE = "stage_b_full_dae_actuator_authority"
SHARD_COUNT = 3
STEPS = 50
ACTIVE_STEPS = 15
DT_SECONDS = 0.2
DEFAULT_SEAL = ROOT / "memory/rounds/R294/actuator_authority_stage_b_seal.json"
DEFAULT_OUT = ROOT / "results/r294_model_validation/stage_b"
PROTOCOL = ROOT / "memory/rounds/R294/stage_b_protocol.md"
PURE_MODULE = ROOT / "src/andes_rl_kundur/evaluation/coupled_actuator_authority.py"
COORDINATE_MODULE = ROOT / "src/andes_rl_kundur/evaluation/model_validation.py"
ENV_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
STORAGE_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py"
BASE_ENV_SOURCE = ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
ACTIVE_POWER_SOURCE = ROOT / "src/andes_rl_kundur/control/active_power.py"
TIE_IDX = ("Line_4", "Line_5", "Line_6")
LOCATIONS = ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
DISTURBANCE_SIGNS = (-1.0, 1.0)
TIE_LEVELS = (1.0, 2.0)
ACTUATORS = ("M", "D", "P")
COORDINATES = ("common", "interarea")
ORIENTATIONS = ("minus", "plus")
PHYSICAL_AMPLITUDES = {"M": 40.0, "D": 40.0, "P": 0.20}
THRESHOLDS = {
    "budget_relevance_ratio_min": 0.25,
    "linearity_nonlinearity_ratio_median_max": 0.25,
    "linearity_nonlinearity_ratio_worst_max": 0.50,
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
    rows = []
    for tie_k, location, delta in itertools.product(
        TIE_LEVELS, LOCATIONS, DISTURBANCE_SIGNS
    ):
        sign_name = "pos" if delta > 0 else "neg"
        rows.append(
            {
                "name": f"k{tie_k:g}__{location.lower()}__{sign_name}",
                "tie_k": tie_k,
                "location": location,
                "delta_u": delta,
            }
        )
    return rows


def arm_bank() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"name": "baseline", "actuator": "zero", "coordinate": "none", "orientation": "zero"}
    ]
    for actuator, coordinate, orientation in itertools.product(
        ACTUATORS, COORDINATES, ORIENTATIONS
    ):
        rows.append(
            {
                "name": f"{actuator.lower()}__{coordinate}__{orientation}",
                "actuator": actuator,
                "coordinate": coordinate,
                "orientation": orientation,
            }
        )
    return rows


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
        "plant": "AndesMultiVSGEnvV4Storage full nonlinear DAE",
        "steps": STEPS,
        "active_steps": ACTIVE_STEPS,
        "dt_seconds": DT_SECONDS,
        "tie_lines": list(TIE_IDX),
        "coordinate_matrix": physical_coordinate_matrix().tolist(),
        "physical_coordinate_amplitudes": PHYSICAL_AMPLITUDES,
        "thresholds": THRESHOLDS,
        "scenarios": scenario_bank(),
        "arms": arm_bank(),
        "jobs": job_bank(),
        "shard_count": SHARD_COUNT,
        "estimand": (
            "central paired full-DAE trajectory sensitivity under each declared safe "
            "probe budget; cross-actuator ratios are budget-normalized, not equal-unit gains"
        ),
        "claim_boundary": (
            "authority screening only; no controller performance, multi-agent value, neural value, "
            "general stability, or deployment conclusion"
        ),
        "sources": {
            "protocol": _source_entry(PROTOCOL),
            "runner": _source_entry(Path(__file__).resolve()),
            "pure_module": _source_entry(PURE_MODULE),
            "coordinate_module": _source_entry(COORDINATE_MODULE),
            "base_environment": _source_entry(BASE_ENV_SOURCE),
            "environment": _source_entry(ENV_SOURCE),
            "storage_environment": _source_entry(STORAGE_SOURCE),
            "active_power_contract": _source_entry(ACTIVE_POWER_SOURCE),
        },
    }


def prepare(seal_path: Path, out_dir: Path) -> None:
    payload = _seal_payload()
    digest = _write_new(seal_path, payload)
    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke").mkdir(parents=True, exist_ok=True)
    print(f"seal_sha256={digest}")
    print(f"scenarios={len(payload['scenarios'])} arms={len(payload['arms'])} jobs={len(payload['jobs'])}")


def _verify_seal(path: Path, expected_sha256: str) -> dict[str, Any]:
    observed = _verify_sidecar(path)
    if observed != expected_sha256:
        raise RuntimeError(f"seal hash mismatch: {expected_sha256} != {observed}")
    seal = json.loads(path.read_text(encoding="utf-8"))
    for name, entry in seal["sources"].items():
        observed_source = sha256_file(ROOT / entry["path"])
        if observed_source != entry["sha256"]:
            raise RuntimeError(f"sealed source drift for {name}")
    return seal


def _pattern(coordinate: str) -> np.ndarray:
    row = {"common": 0, "interarea": 1}[coordinate]
    return physical_coordinate_matrix()[row]


def _normalized_md_action(desired: np.ndarray) -> np.ndarray:
    desired = np.asarray(desired, dtype=float)
    return np.where(desired >= 0.0, desired / 600.0, desired / 200.0)


def _commands(arm: dict[str, Any], step: int) -> tuple[dict[int, np.ndarray], np.ndarray]:
    md = {index: np.zeros(2, dtype=float) for index in range(4)}
    power = np.zeros(4, dtype=float)
    if step >= ACTIVE_STEPS or arm["actuator"] == "zero":
        return md, power
    orientation = 1.0 if arm["orientation"] == "plus" else -1.0
    physical = orientation * PHYSICAL_AMPLITUDES[arm["actuator"]] * _pattern(arm["coordinate"])
    if arm["actuator"] == "P":
        power = physical
    else:
        normalized = _normalized_md_action(physical)
        channel = 0 if arm["actuator"] == "M" else 1
        for index in range(4):
            md[index][channel] = normalized[index]
    return md, power


def _run_job(job: dict[str, Any], seal_hash: str) -> dict[str, Any]:
    os.environ["DISABLE_TOGGLER"] = "1"
    import andes

    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    tie_k = float(job["scenario"]["tie_k"])

    class AuthorityEnvironment(AndesMultiVSGEnvV4Storage):
        def _build_system(self):
            system = super()._build_system()
            if abs(tie_k - 1.0) > 1e-12:
                for idx in TIE_IDX:
                    position = list(system.Line.idx.v).index(idx)
                    system.Line.set("r", idx, float(system.Line.r.v[position] * tie_k), attr="v")
                    system.Line.set("x", idx, float(system.Line.x.v[position] * tie_k), attr="v")
            return system

    env = AuthorityEnvironment(random_disturbance=False, comm_fail_prob=0.0)
    traces: list[dict[str, Any]] = []
    tds_failed = False
    tds_test_ok = False
    exit_code = 1
    failure: str | None = None
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
        for step in range(STEPS):
            md_actions, power_request = _commands(job["arm"], step)
            _, _, done, info = env.step(
                md_actions,
                bess_power_request_pu=power_request,
            )
            if info.get("tds_failed"):
                tds_failed = True
                break
            frequency = np.asarray(info["freq_hz_physical"], dtype=float)
            traces.append(
                {
                    "step": step,
                    "time": float(info["time"]),
                    "frequency_deviation_hz": (frequency - nominal).tolist(),
                    "omega_dot_pu_s": np.asarray(info["omega_dot"], dtype=float).tolist(),
                    "md_action_norm": [md_actions[index].tolist() for index in range(4)],
                    "m_values": np.asarray(info["M_es"], dtype=float).tolist(),
                    "d_values": np.asarray(info["D_es"], dtype=float).tolist(),
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
                    "bess_voltage_pu": np.asarray(
                        info["bess_bus_voltage_pu"], dtype=float
                    ).tolist(),
                    "bess_saturation_reasons": info["bess_saturation_reasons"],
                    "bess_constraint_violations": info["bess_constraint_violations"],
                }
            )
            if done:
                break
        tds_test_ok = bool(env.ss.TDS.test_ok)
        exit_code = int(env.ss.exit_code)
    except Exception as exc:  # retained as an invalid, non-retried trajectory
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            env.close()
        except Exception as exc:  # pragma: no cover - defensive ANDES cleanup
            if failure is None:
                failure = f"close {type(exc).__name__}: {exc}"
    arrays = []
    for trace in traces:
        arrays.extend(
            [
                trace["frequency_deviation_hz"],
                trace["m_values"],
                trace["d_values"],
                trace["bess_commanded_power_system_pu"],
                trace["bess_soc"],
                trace["bess_voltage_pu"],
            ]
        )
    finite = bool(arrays and np.all(np.isfinite(np.asarray(arrays, dtype=float))))
    violations = [
        violation for trace in traces for violation in trace["bess_constraint_violations"]
    ]
    action_contract_pass = False
    action_contract_detail: dict[str, Any] = {}
    if len(traces) == STEPS:
        executed_m = np.asarray([trace["m_values"] for trace in traces], dtype=float)
        executed_d = np.asarray([trace["d_values"] for trace in traces], dtype=float)
        requested_p = np.asarray(
            [trace["bess_requested_power_system_pu"] for trace in traces],
            dtype=float,
        )
        commanded_p = np.asarray(
            [trace["bess_commanded_power_system_pu"] for trace in traces],
            dtype=float,
        )
        expected_m = []
        expected_d = []
        expected_p = []
        for step in range(STEPS):
            expected_md, step_expected_p = _commands(job["arm"], step)
            action_array = np.asarray(
                [expected_md[index] for index in range(4)], dtype=float
            )
            delta_m = np.where(
                action_array[:, 0] >= 0.0,
                action_array[:, 0] * 600.0,
                action_array[:, 0] * 200.0,
            )
            delta_d = np.where(
                action_array[:, 1] >= 0.0,
                action_array[:, 1] * 600.0,
                action_array[:, 1] * 200.0,
            )
            expected_m.append(200.0 + delta_m)
            expected_d.append(100.0 + delta_d)
            expected_p.append(step_expected_p)
        expected_m_array = np.asarray(expected_m)
        expected_d_array = np.asarray(expected_d)
        expected_p_array = np.asarray(expected_p)
        initial_command = np.zeros((1, 4), dtype=float)
        commanded_slew = np.diff(
            np.concatenate([initial_command, commanded_p], axis=0), axis=0
        )
        action_contract_detail = {
            "m_target_exact": bool(
                np.allclose(executed_m, expected_m_array, rtol=0.0, atol=1e-8)
            ),
            "d_target_exact": bool(
                np.allclose(executed_d, expected_d_array, rtol=0.0, atol=1e-8)
            ),
            "power_request_exact": bool(
                np.allclose(requested_p, expected_p_array, rtol=0.0, atol=1e-12)
            ),
            "power_nameplate_pass": bool(np.max(np.abs(commanded_p)) <= 0.36 + 1e-12),
            "power_ramp_pass": bool(
                np.max(np.abs(commanded_slew)) <= 0.072 + 1e-12
            ),
            "soc_bounds_pass": bool(
                min(min(trace["bess_soc"]) for trace in traces) >= 0.2 - 1e-9
                and max(max(trace["bess_soc"]) for trace in traces) <= 0.8 + 1e-9
            ),
        }
        action_contract_pass = all(action_contract_detail.values())
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
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": seal_hash,
        "job": job,
        "runtime": {
            "wall_clock_seconds": time.perf_counter() - started,
            "python": sys.version,
            "platform": platform.platform(),
            "andes_version": getattr(andes, "__version__", "unknown"),
        },
        "guards": {
            "completed": completed,
            "requested_steps": STEPS,
            "recorded_steps": len(traces),
            "tds_failed": tds_failed,
            "tds_test_ok": tds_test_ok,
            "system_exit_code": exit_code,
            "finite_telemetry": finite,
            "storage_constraint_violation_count": len(violations),
            "action_contract_pass": action_contract_pass,
            "action_contract_detail": action_contract_detail,
            "failure": failure,
        },
        "traces": traces,
    }


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
    print(
        f"smoke_pass=True steps={record['guards']['recorded_steps']} "
        f"wall={record['runtime']['wall_clock_seconds']:.2f}s"
    )


def run_shard(
    seal_path: Path,
    expected_sha256: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    if shard_count != int(seal["shard_count"]) or not 0 <= shard_index < shard_count:
        raise ValueError("shard contract mismatch")
    for job in seal["jobs"]:
        if int(job["order"]) % shard_count != shard_index:
            continue
        path = out_dir / "records" / f"{job['order']:03d}__{job['name']}.json"
        if path.exists():
            _verify_sidecar(path)
            retained = json.loads(path.read_text(encoding="utf-8"))
            if retained.get("seal_sha256") != expected_sha256:
                raise RuntimeError(f"retained record seal mismatch: {path}")
            print(f"[resume] {path.name} pass={retained['guards']['completed']}", flush=True)
            continue
        record = _run_job(job, expected_sha256)
        digest = _write_new(path, record)
        print(
            f"[job] {job['order'] + 1}/{len(seal['jobs'])} {job['name']} "
            f"pass={record['guards']['completed']} wall={record['runtime']['wall_clock_seconds']:.2f}s "
            f"sha256={digest}",
            flush=True,
        )


def _load_records(seal: dict[str, Any], out_dir: Path, expected: str) -> dict[str, Any]:
    records = {}
    missing = []
    for job in seal["jobs"]:
        path = out_dir / "records" / f"{job['order']:03d}__{job['name']}.json"
        if not path.exists():
            missing.append(path.name)
            continue
        _verify_sidecar(path)
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("seal_sha256") != expected:
            raise RuntimeError(f"record seal mismatch: {path}")
        records[job["name"]] = record
    if missing:
        raise RuntimeError(f"missing records: {missing[:10]} (total {len(missing)})")
    return records


def analyse(seal_path: Path, expected_sha256: str, out_dir: Path) -> None:
    seal = _verify_seal(seal_path, expected_sha256)
    records = _load_records(seal, out_dir, expected_sha256)
    invalid = [name for name, record in records.items() if record["guards"]["completed"] is not True]
    result: dict[str, Any] = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": STAGE,
        "seal_sha256": expected_sha256,
        "record_count": len(records),
        "invalid_records": invalid,
        "thresholds": seal["thresholds"],
        "estimand": seal["estimand"],
        "claim_boundary": seal["claim_boundary"],
    }
    if invalid:
        result.update(
            {
                "classification": "INVALID-STAGE-B-EXECUTION",
                "authority": None,
                "pointwise": [],
            }
        )
    else:
        pointwise = []
        for scenario in seal["scenarios"]:
            baseline_name = f"{scenario['name']}__baseline"
            baseline = records[baseline_name]
            baseline_trace = [row["frequency_deviation_hz"] for row in baseline["traces"]]
            for actuator, coordinate in itertools.product(ACTUATORS, COORDINATES):
                prefix = f"{scenario['name']}__{actuator.lower()}__{coordinate}"
                plus = records[f"{prefix}__plus"]
                minus = records[f"{prefix}__minus"]
                metrics = paired_authority_metrics(
                    baseline_trace,
                    [row["frequency_deviation_hz"] for row in plus["traces"]],
                    [row["frequency_deviation_hz"] for row in minus["traces"]],
                    target_coordinate=coordinate,
                    dt_seconds=DT_SECONDS,
                    fast_steps=ACTIVE_STEPS,
                )
                pointwise.append(
                    {
                        "scenario": scenario,
                        "actuator": actuator,
                        "coordinate": coordinate,
                        "plus_record": plus["job"]["name"],
                        "minus_record": minus["job"]["name"],
                        "metrics": metrics,
                    }
                )
        authority = aggregate_authority(
            pointwise,
            relevance_ratio=seal["thresholds"]["budget_relevance_ratio_min"],
            linearity_median_max=seal["thresholds"]["linearity_nonlinearity_ratio_median_max"],
            linearity_worst_max=seal["thresholds"]["linearity_nonlinearity_ratio_worst_max"],
        )
        result.update(
            {
                "classification": "VALID-BUDGET-NORMALIZED-AUTHORITY-MAP",
                "authority": authority,
                "pointwise": pointwise,
            }
        )
    summary_path = out_dir / "stage_b_summary.json"
    summary_hash = _write_new(summary_path, result)
    provenance = {
        "seal": {"path": seal_path.relative_to(ROOT).as_posix(), "sha256": expected_sha256},
        "summary": {"path": summary_path.relative_to(ROOT).as_posix(), "sha256": summary_hash},
        "record_hashes": {
            name: sha256_file(
                out_dir / "records" / f"{record['job']['order']:03d}__{name}.json"
            )
            for name, record in records.items()
        },
        "analysis_runtime": {"python": sys.version, "platform": platform.platform()},
    }
    _write_new(out_dir / "provenance.json", provenance)
    print(f"classification={result['classification']}")
    if result["authority"] is not None:
        print(f"trajectory_model_decision={result['authority']['trajectory_model_decision']}")
        for coordinate, row in result["authority"]["coordinates"].items():
            print(
                f"{coordinate}: dominant={row['dominant_budget_normalized_actuator']} "
                f"relevant={','.join(row['budget_relevant_actuators'])}"
            )
    print(f"summary_sha256={summary_hash}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    smoke_parser = commands.add_parser("smoke")
    smoke_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    smoke_parser.add_argument("--expected-seal-sha256", required=True)
    smoke_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    run_parser.add_argument("--expected-seal-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    analyse_parser = commands.add_parser("analyse")
    analyse_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.seal, args.out_dir)
    elif args.command == "smoke":
        smoke(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "run":
        run_shard(
            args.seal,
            args.expected_seal_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    elif args.command == "analyse":
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    else:  # pragma: no cover
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
