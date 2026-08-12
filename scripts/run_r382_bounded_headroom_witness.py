#!/usr/bin/env python3
"""Rehearse, seal, and execute the create-only R382 headroom witness.

Usage (WSL)::

    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r382_bounded_headroom_witness.py rehearse
    /home/wya/andes_venv/bin/python \
        scripts/run_r382_bounded_headroom_witness.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r382_bounded_headroom_witness.py execute \
        --expected-seal-sha256 <sha256>

The runner executes exactly four frozen non-causal residual schedules over
each of ten immutable R381 local-baseline conditions.  It contains no tuning,
retry, evaluation-bank access, learning, or training command.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
for import_path in (ROOT, SCRIPT_DIR, ROOT / "src"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

for thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np  # noqa: E402

import run_r379_gate_b3_deterministic as _infra  # noqa: E402

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.feasibility_native_deterministic import (  # noqa: E402
    FeasibilityNativeLocalController,
)
from andes_rl_kundur.control.feasibility_native_vsg_action import (  # noqa: E402
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.evaluation.bounded_headroom_witness import (  # noqa: E402
    assemble_outcome_oracle,
    build_contract,
    derive_residual_schedule,
    record_key,
)


ROUND_ID = "R382"
ROUND_DIR = ROOT / "memory/rounds/R382"
PLAN = ROUND_DIR / "plan.md"
REHEARSAL = ROUND_DIR / "rehearsal.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
SEAL = ROUND_DIR / "formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r382_bounded_headroom_witness"


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r382_bounded_headroom_witness.py",
        "classifier": (
            ROOT
            / "src/andes_rl_kundur/evaluation/bounded_headroom_witness.py"
        ),
        "classifier_tests": ROOT / "tests/test_bounded_headroom_witness.py",
        "local_controller": (
            ROOT
            / "src/andes_rl_kundur/control/feasibility_native_deterministic.py"
        ),
        "action_map": (
            ROOT
            / "src/andes_rl_kundur/control/feasibility_native_vsg_action.py"
        ),
        "energy_contract": ROOT / "src/andes_rl_kundur/control/active_power.py",
        "energy_port": ROOT / "src/andes_rl_kundur/control/vsg_energy_port.py",
        "energy_port_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py"
        ),
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }


def _parent_paths() -> dict[str, Path]:
    result_root = ROOT / "results/research_loop/r381_gate_b4_deterministic"
    return {
        "r381_seal": ROOT / "memory/rounds/R381/formal_seal.json",
        "r381_capacity": ROOT / "memory/rounds/R381/capacity_evidence.json",
        "r381_development": result_root / "development_execution.json",
        "r381_development_analysis": result_root / "development_analysis.json",
        "r381_analysis": result_root / "formal_analysis.json",
        "r381_feed": ROOT / "paper/paralleled_vsg_marl/reports/R381.md",
        "r381_claim": ROOT / "memory/claims/CLM-1050.md",
        "r381_verdict": ROOT / "memory/rounds/R381/verdict.md",
    }


def _manifest(paths: Mapping[str, Path]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R382 input: {path}")
        result[name] = {
            "path": _infra._relative(path),
            "sha256": _infra._sha256_file(path),
        }
    return result


def _source_manifest() -> dict[str, dict[str, str]]:
    return _manifest(_source_paths())


def _parent_manifest() -> dict[str, dict[str, str]]:
    return _manifest(_parent_paths())


def _source_baseline_records() -> list[dict[str, Any]]:
    payload = _infra._read_hashed_json(_parent_paths()["r381_development"])
    records = [
        dict(row)
        for row in payload["records"]
        if row.get("arm_id") == "local_feasibility_native"
    ]
    if len(records) != 10:
        raise RuntimeError("R381 local baseline does not contain ten conditions")
    return records


def candidate_jobs(
    baseline_records: list[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Cross each immutable parent condition with four frozen candidates."""

    frozen = build_contract() if contract is None else contract
    by_key = {record_key(row): row for row in baseline_records}
    expected = [
        (
            str(row["experiment_kind"]),
            str(row["condition_id"]),
            row["input_mode"],
            row["sign"],
        )
        for row in frozen["source_jobs"]
    ]
    if len(by_key) != len(baseline_records) or set(by_key) != set(expected):
        raise ValueError("baseline records do not match the frozen source jobs")
    jobs: list[dict[str, Any]] = []
    for source_key in expected:
        for candidate in frozen["candidate_specs"]:
            jobs.append(
                {
                    "order": len(jobs),
                    "candidate_id": str(candidate["candidate_id"]),
                    "amplitude": float(candidate["amplitude"]),
                    "polarity": float(candidate["polarity"]),
                    "parent_record": by_key[source_key],
                }
            )
    if len(jobs) != int(frozen["candidate_record_count"]):
        raise RuntimeError("candidate jobs do not match the frozen record count")
    return jobs


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    try:
        return bool(
            contract["round"] == ROUND_ID
            and int(contract["steps"]) == 50
            and float(contract["dt_seconds"]) == 0.2
            and int(contract["lead_steps"]) == 2
            and len(contract["source_jobs"]) == 10
            and len(contract["candidate_specs"]) == 4
            and int(contract["candidate_record_count"]) == 40
            and float(contract["thresholds"]["headroom_ratio_max"]) == 0.95
            and contract["training_authorized"] is False
            and len(candidate_jobs(_source_baseline_records(), contract=contract))
            == 40
        )
    except (KeyError, TypeError, ValueError):
        return False


def _plan_is_active() -> bool:
    text = PLAN.read_text(encoding="utf-8")
    return "round: R382" in text and "state: active" in text


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R382 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R382 must run through scripts/andes_scratch.py")


def _projected_artifact_bytes() -> int:
    parent_bytes = _parent_paths()["r381_development"].stat().st_size
    return int(2.0 * parent_bytes * 40.0 / 30.0)


def _capacity_payload(
    *,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    disk_free_bytes: int,
    other_processes: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_capacity = _infra._read_hashed_json(_parent_paths()["r381_capacity"])
    anchor_analysis = _infra._read_hashed_json(_parent_paths()["r381_analysis"])
    anchor_wall = float(anchor_analysis["wall_seconds"])
    projected_wall = anchor_wall * 40.0 / 30.0
    projected_bytes = _projected_artifact_bytes()
    host = anchor_capacity["host"]
    prior_available = int(anchor_capacity["wsl"]["memory_available_bytes"])
    checks = {
        "anchor_complete": int(
            anchor_analysis["development_analysis_sha256"] is not None
        )
        == 1
        and anchor_wall > 0.0,
        "runtime_match": all(
            runtime.get(field) == anchor_capacity["installed_runtime"].get(field)
            for field in ("andes_version", "case_sha256")
        ),
        "current_host": (
            logical_processors == int(host["logical_processors"])
            and physical_memory_bytes == int(host["physical_memory_bytes"])
        ),
        "memory_fit": wsl_memory_available_bytes >= 0.8 * prior_available,
        "artifact_fit": disk_free_bytes > 100 * projected_bytes,
        "competing_process_absence": not other_processes,
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if all(checks.values()) else "HOLD",
        "checks": checks,
        "empirical_anchor": {
            "record_count": 30,
            "environment_steps": 1500,
            "wall_seconds": anchor_wall,
            "analysis_path": parents["r381_analysis"]["path"],
            "analysis_sha256": parents["r381_analysis"]["sha256"],
        },
        "formal_projection": {
            "record_count": 40,
            "environment_steps": 2000,
            "wall_seconds": projected_wall,
            "wall_seconds_with_1p5_safety_factor": 1.5 * projected_wall,
        },
        "artifact_projection": {
            "projected_bytes": projected_bytes,
            "disk_free_bytes": disk_free_bytes,
        },
        "host": {
            "logical_processors": logical_processors,
            "physical_memory_bytes": physical_memory_bytes,
        },
        "wsl": {"memory_available_bytes": wsl_memory_available_bytes},
        "installed_runtime": dict(runtime),
        "whole_host_python_process_budget": 1,
        "host_process_budget": 1,
        "host_process_budget_classification": "intentional_attempt_level_hard_cap",
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "other_processes": other_processes,
        "sources": dict(sources),
        "parents": dict(parents),
        "formal_authority": False,
        "training_executed": False,
    }


def rehearse() -> tuple[str, str]:
    _assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R382 readiness output collision: {collisions}")
    contract = build_contract()
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _infra._installed_runtime()
    logical, physical, wsl_available = _infra._memory_resources()
    other = _infra._other_research_python_processes()
    capacity = _capacity_payload(
        runtime=runtime,
        sources=sources,
        parents=parents,
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=wsl_available,
        disk_free_bytes=shutil.disk_usage(ROOT).free,
        other_processes=other,
    )
    capacity_digest = _infra._write_new_json(CAPACITY, capacity)
    checks = {
        "source_hash": all(row["sha256"] for row in sources.values()),
        "parent_hash": all(row["sha256"] for row in parents.values()),
        "installed_package": runtime.get("andes_version") == "2.0.0",
        "installed_case": bool(runtime.get("case_sha256")),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": _plan_is_active(),
        "contract_closed": _contract_is_closed(contract),
        "capacity_ready": capacity["readiness"] == "RUN-READY",
        "competing_process_absence": not other,
        "physical_trajectory_executed": False,
    }
    rehearsal_digest = _infra._write_new_json(
        REHEARSAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "checks": checks,
            "contract_sha256": _infra._payload_sha256(contract),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "capacity_sha256": capacity_digest,
            "formal_authority": False,
            "training_executed": False,
        },
    )
    if not all(value for name, value in checks.items() if name != "physical_trajectory_executed"):
        raise RuntimeError("R382 rehearsal did not pass")
    return rehearsal_digest, capacity_digest


def prepare() -> str:
    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R382 seal or formal output already exists")
    rehearsal = _infra._read_hashed_json(REHEARSAL)
    capacity = _infra._read_hashed_json(CAPACITY)
    checks = dict(rehearsal.get("checks", {}))
    if not all(value for name, value in checks.items() if name != "physical_trajectory_executed"):
        raise RuntimeError("R382 rehearsal checks did not pass")
    if checks.get("physical_trajectory_executed") is not False:
        raise RuntimeError("R382 rehearsal executed a physical trajectory")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R382 capacity is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    if rehearsal.get("sources") != sources or capacity.get("sources") != sources:
        raise RuntimeError("R382 source drift before seal")
    if rehearsal.get("parents") != parents or capacity.get("parents") != parents:
        raise RuntimeError("R382 parent drift before seal")
    runtime = _infra._installed_runtime()
    if rehearsal.get("installed_runtime") != runtime:
        raise RuntimeError("R382 runtime drift before seal")
    contract = build_contract()
    return _infra._write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": _infra._payload_sha256(contract),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "rehearsal_sha256": _infra._sha256_file(REHEARSAL),
            "capacity_sha256": _infra._sha256_file(CAPACITY),
            "launch": {
                "host_process_budget": 1,
                "wsl_python_processes": 1,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _infra._read_hashed_json(SEAL)
    digest = _infra._sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R382 expected seal hash does not match")
    if seal.get("contract_sha256") != _infra._payload_sha256(seal["contract"]):
        raise RuntimeError("R382 sealed contract hash mismatch")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R382 source drift after seal")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R382 parent drift after seal")
    if seal.get("rehearsal_sha256") != _infra._sha256_file(REHEARSAL):
        raise RuntimeError("R382 rehearsal drift after seal")
    if seal.get("capacity_sha256") != _infra._sha256_file(CAPACITY):
        raise RuntimeError("R382 capacity drift after seal")
    if not _contract_is_closed(seal["contract"]):
        raise RuntimeError("R382 sealed contract is not closed")
    return seal, digest


def _probe_request(parent_record: Mapping[str, Any], contract: Mapping[str, Any]) -> np.ndarray:
    if parent_record["experiment_kind"] != "probe":
        return np.zeros(4, dtype=float)
    direction = 1.0 if parent_record["sign"] == "positive" else -1.0
    return (
        direction
        * float(contract["probe_component_action"])
        * np.asarray(contract["modes"][parent_record["input_mode"]], dtype=float)
    )


def _run_job(job: Mapping[str, Any], *, contract: Mapping[str, Any]) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    parent = job["parent_record"]
    schedule = derive_residual_schedule(
        parent,
        amplitude=float(job["amplitude"]),
        polarity=float(job["polarity"]),
        lead_steps=int(contract["lead_steps"]),
    )
    base_env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(42)
    base_env.STEPS_PER_EPISODE = int(contract["steps"])
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    local = FeasibilityNativeLocalController(
        device_count=int(contract["device_count"]),
        nominal_frequency_hz=float(contract["nominal_frequency_hz"]),
        kp_n_per_hz=float(contract["local_gains"]["kp_n_per_hz"]),
        ki_n_per_hz_s=float(contract["local_gains"]["ki_n_per_hz_s"]),
    )
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    failure: str | None = None
    previous_power = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    try:
        port_env.reset(delta_u=dict(parent["delta_u"]))
        identity = _infra._identity(base_env)
        for step_index in range(int(contract["steps"])):
            frequencies = (
                np.asarray(base_env._get_vsg_omega(), dtype=float)
                * float(contract["nominal_frequency_hz"])
            )
            baseline_action = local.act(
                frequencies_hz=frequencies,
                dt_seconds=float(contract["dt_seconds"]),
            ) + _probe_request(parent, contract)
            voltage = np.asarray(
                [base_env.ss.GENCLS.v.v[position] for position in base_env._vsg_pos],
                dtype=float,
            )
            baseline_mapped = action_map.map_action(
                normalized_actions=baseline_action,
                previous_power_system_pu=previous_power,
                soc=current_soc,
                voltage_pu=voltage,
                dt_seconds=float(contract["dt_seconds"]),
            )
            residual = schedule[step_index]
            mapped = action_map.map_residual_action(
                normalized_residual_actions=residual,
                baseline_power_system_pu=baseline_mapped.feasible_power_system_pu,
                previous_power_system_pu=previous_power,
                soc=current_soc,
                voltage_pu=voltage,
                dt_seconds=float(contract["dt_seconds"]),
            )
            _observation, _reward, done, info = port_env.step(
                mapped.feasible_power_system_pu
            )
            row = _infra._port_row(info, step_index=step_index, done=bool(done))
            row.update(
                {
                    "baseline_normalized_action": baseline_action.tolist(),
                    "normalized_residual_action": residual.tolist(),
                    "common_residual_action": (
                        np.mean(residual) * np.ones(4, dtype=float)
                    ).tolist(),
                    "differential_residual_action": (
                        residual - np.mean(residual)
                    ).tolist(),
                    "baseline_power_system_pu": (
                        baseline_mapped.feasible_power_system_pu.tolist()
                    ),
                    "lower_power_system_pu": mapped.lower_power_system_pu.tolist(),
                    "upper_power_system_pu": mapped.upper_power_system_pu.tolist(),
                    "feasible_power_system_pu": mapped.feasible_power_system_pu.tolist(),
                    "noncausal_source_step": min(
                        step_index + int(contract["lead_steps"]),
                        int(contract["steps"]) - 1,
                    ),
                }
            )
            rows.append(row)
            previous_power = np.asarray(row["commanded_power_system_pu"], dtype=float)
            current_soc = np.asarray(row["soc"], dtype=float)
            if row["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        port_env.close()
    return {
        "phase": "development_outcome_witness",
        "arm_id": "bounded_outcome_residual",
        "candidate_id": str(job["candidate_id"]),
        "amplitude": float(job["amplitude"]),
        "polarity": float(job["polarity"]),
        "lead_steps": int(contract["lead_steps"]),
        "experiment_kind": str(parent["experiment_kind"]),
        "condition_id": str(parent["condition_id"]),
        "delta_u": dict(parent["delta_u"]),
        "input_mode": parent["input_mode"],
        "sign": parent["sign"],
        "identity": identity or {},
        "steps": rows,
        "completed_steps": len(rows),
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "outcome_privileged": True,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def execute(*, expected_sha256: str) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _infra._other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R382 output collision: {DEFAULT_OUT}")
    attempt_path = DEFAULT_OUT / "formal_attempt.json"
    attempt_digest = _infra._write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    started = time.perf_counter()
    entries = [_infra._manifest_entry(attempt_path, attempt_digest)]
    try:
        contract = seal["contract"]
        baseline_records = _source_baseline_records()
        records = [
            _run_job(job, contract=contract)
            for job in candidate_jobs(baseline_records, contract=contract)
        ]
        execution_path = DEFAULT_OUT / "formal_execution.json"
        execution_digest = _infra._write_new_json(
            execution_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "record_count": len(records),
                "records": records,
                "outcome_privileged": True,
                "reward_used_for_gate": False,
                "training_executed": False,
            },
        )
        entries.append(_infra._manifest_entry(execution_path, execution_digest))
        analysis = assemble_outcome_oracle(
            baseline_records,
            records,
            contract=contract,
        )
        analysis.update(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "wall_seconds": time.perf_counter() - started,
                "training_authorized": False,
            }
        )
        analysis_path = DEFAULT_OUT / "formal_analysis.json"
        analysis_digest = _infra._write_new_json(analysis_path, analysis)
        entries.append(_infra._manifest_entry(analysis_path, analysis_digest))
        _infra._write_new_json(
            DEFAULT_OUT / "formal_manifest.json",
            {"schema_version": 1, "round": ROUND_ID, "entries": entries},
        )
        print(f"classification={analysis['decision']['classification']}", flush=True)
        return analysis_digest
    except Exception as exc:
        _infra._write_new_json(
            DEFAULT_OUT / "formal_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "attempt_sha256": attempt_digest,
                "classification": "ANALYSIS-INVALID",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "wall_seconds": time.perf_counter() - started,
                "retry_authorized": False,
                "training_authorized": False,
            },
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("rehearse")
    subparsers.add_parser("prepare")
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        rehearsal, capacity = rehearse()
        print(f"rehearsal_sha256={rehearsal}", flush=True)
        print(f"capacity_sha256={capacity}", flush=True)
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}", flush=True)
    elif args.command == "execute":
        print(
            f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}",
            flush=True,
        )
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
