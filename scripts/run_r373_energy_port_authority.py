#!/usr/bin/env python3
"""Rehearse, seal, and execute the create-only R373 authority bank.

Usage (WSL):
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r373_energy_port_authority.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r373_energy_port_authority.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r373_energy_port_authority.py execute \
        --expected-seal-sha256 <sha256>

The adapter has no training, tuning, retry, output-path, bank-resize, or
parallel-execution command.  Formal artifacts are create-only.
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
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

for thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

from run_r372_energy_port_object_gate import (  # noqa: E402
    _assert_wsl_scratch,
    _canonical_bytes,
    _identity,
    _installed_runtime,
    _memory_resources,
    _other_research_python_processes,
    _port_row,
    _read_hashed_json,
    _relative,
    _sha256_file,
    _write_new_json,
)

from andes_rl_kundur.evaluation.vsg_energy_port_authority import (  # noqa: E402
    action_request,
    build_contract,
    classify_records,
)

ROUND_ID = "R373"
ROUND_DIR = ROOT / "memory/rounds/R373"
PLAN = ROUND_DIR / "plan.md"
REHEARSAL = ROUND_DIR / "rehearsal_v2.json"
CAPACITY = ROUND_DIR / "capacity_evidence_v2.json"
SEAL = ROUND_DIR / "formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r373_energy_port_authority"


def _payload_sha256(payload: object) -> str:
    import hashlib

    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r373_energy_port_authority.py",
        "classifier": (
            ROOT
            / "src/andes_rl_kundur/evaluation/vsg_energy_port_authority.py"
        ),
        "classifier_tests": (
            ROOT / "tests/test_vsg_energy_port_authority.py"
        ),
        "r372_runner_infrastructure": (
            ROOT / "scripts/run_r372_energy_port_object_gate.py"
        ),
        "energy_contract": (
            ROOT / "src/andes_rl_kundur/control/active_power.py"
        ),
        "energy_port": (
            ROOT / "src/andes_rl_kundur/control/vsg_energy_port.py"
        ),
        "energy_port_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py"
        ),
        "base_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/base_env.py"
        ),
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _source_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R373 source: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _parent_paths() -> dict[str, Path]:
    return {
        "object_claim": ROOT / "memory/claims/CLM-1005.md",
        "object_feed": ROOT / "paper/paralleled_vsg_marl/reports/R372.md",
        "object_verdict": ROOT / "memory/rounds/R372/verdict.md",
        "object_seal": ROOT / "memory/rounds/R372/formal_seal.json",
        "object_analysis": (
            ROOT
            / "results/research_loop/r372_energy_port_object_gate/formal_analysis.json"
        ),
        "object_execution": (
            ROOT
            / "results/research_loop/r372_energy_port_object_gate/formal_execution.json"
        ),
        "object_capacity": ROOT / "memory/rounds/R372/capacity_evidence.json",
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _parent_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R373 parent: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _plan_is_active() -> bool:
    text = PLAN.read_text(encoding="utf-8")
    return "round: R373" in text and "state: active" in text


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    return bool(
        contract.get("round") == ROUND_ID
        and contract.get("condition_ids")
        == ["nominal", "load_bus14_plus_0p5", "load_bus15_plus_0p5"]
        and contract.get("mode_ids")
        == ["common", "inter_area", "local_area_1", "local_area_2"]
        and int(contract.get("record_count", -1)) == 30
        and int(contract.get("steps", -1)) == 40
        and float(contract.get("dt_seconds", -1.0)) == 0.2
        and float(contract.get("request_component_magnitude_system_pu", -1.0))
        == 0.04
        and contract.get("retry_authorized") is False
        and contract.get("training_authorized") is False
    )


def _projected_artifact_bytes(contract: Mapping[str, Any]) -> int:
    zero4 = [0.0, 0.0, 0.0, 0.0]
    row = {
        "step_index": 0,
        "time": 0.0,
        "requested_power_system_pu": zero4,
        "commanded_power_system_pu": zero4,
        "sampled_omega_pu": zero4,
        "baseline_pref_system_pu": zero4,
        "pref_written_system_pu": zero4,
        "pref_readback_system_pu": zero4,
        "torque_readback_system_pu": zero4,
        "achieved_power_system_pu": zero4,
        "soc": zero4,
        "charged_energy_mwh": zero4,
        "discharged_energy_mwh": zero4,
        "total_charged_energy_mwh": zero4,
        "total_discharged_energy_mwh": zero4,
        "saturation_reasons": [[], [], [], []],
        "omega": zero4,
        "freq_hz_physical": zero4,
        "P_es": zero4,
        "M_es": zero4,
        "D_es": zero4,
        "delta_M": zero4,
        "delta_D": zero4,
        "md_action_norm": [[0.0, 0.0]] * 4,
        "tds_failed": False,
        "done": False,
    }
    records = []
    for condition in contract["conditions"]:
        for arm_id in contract["arm_ids"]:
            records.append(
                {
                    "condition_id": condition["condition_id"],
                    "delta_u": condition["delta_u"],
                    "arm_id": arm_id,
                    "identity": {},
                    "steps": [row] * int(contract["steps"]),
                    "completed_steps": int(contract["steps"]),
                    "tds_failed": False,
                    "failure": None,
                }
            )
    placeholder = {
        "formal_execution": {"records": records},
        "formal_analysis": {
            "classification": "BOUNDED-ENERGY-PORT-AUTHORITY-PASS",
            "conditions": contract["condition_ids"],
            "modes": contract["mode_ids"],
        },
        "formal_manifest": {},
        "formal_attempt": {},
    }
    return 2 * len(_canonical_bytes(placeholder))


def _build_capacity_payload(
    *,
    anchor_execution: Mapping[str, Any],
    anchor_capacity: Mapping[str, Any],
    projected_artifact_bytes: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
) -> dict[str, Any]:
    anchor_steps = 10 * 5
    formal_steps = int(build_contract()["record_count"]) * int(
        build_contract()["steps"]
    )
    anchor_wall = float(anchor_execution["wall_seconds"])
    projected_wall = 1.5 * anchor_wall * formal_steps / anchor_steps
    anchor_runtime = dict(anchor_capacity["installed_runtime"])
    host = dict(anchor_capacity["host"])
    checks = {
        "anchor_complete": (
            int(anchor_execution.get("record_count", -1)) == 10
            and not any(
                bool(record.get("tds_failed"))
                for record in anchor_execution.get("records", [])
            )
        ),
        "anchor_serial": (
            int(anchor_capacity.get("wsl_python_processes", -1)) == 1
            and int(anchor_capacity.get("native_threads_per_process", -1)) == 1
        ),
        "runtime_match": (
            runtime.get("andes_version") == anchor_runtime.get("andes_version")
            and runtime.get("case_sha256") == anchor_runtime.get("case_sha256")
        ),
        "current_host": (
            logical_processors == int(host["logical_processors"])
            and physical_memory_bytes == int(host["physical_memory_bytes"])
        ),
        "memory_fit": wsl_memory_available_bytes > 8 * int(
            anchor_capacity["empirical_anchor"]["max_rss_kib"]
        ) * 1024,
        "artifact_fit": disk_free_bytes > 100 * projected_artifact_bytes,
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if all(checks.values()) else "HOLD",
        "checks": checks,
        "empirical_anchor": {
            "all_records_valid": True,
            "concurrent_workers": 1,
            "native_threads_per_worker": 1,
            "execution_path": parents["object_execution"]["path"],
            "execution_sha256": parents["object_execution"]["sha256"],
            "capacity_path": parents["object_capacity"]["path"],
            "capacity_sha256": parents["object_capacity"]["sha256"],
            "record_count": int(anchor_execution["record_count"]),
            "environment_steps": anchor_steps,
            "wall_seconds": anchor_wall,
        },
        "formal_projection": {
            "record_count": int(build_contract()["record_count"]),
            "environment_steps": formal_steps,
            "wall_seconds_with_1p5_safety_factor": projected_wall,
        },
        "artifact_projection": {
            "method": "two times complete empty-value formal schema",
            "projected_bytes": projected_artifact_bytes,
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
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "sources": dict(sources),
        "parents": dict(parents),
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }


def _rehearsal_checks(payload: Mapping[str, Any]) -> bool:
    checks = dict(payload.get("checks", {}))
    expected = {
        "source_hash",
        "parent_hash",
        "installed_package",
        "installed_case",
        "output_absence",
        "active_plan",
        "contract_closed",
        "capacity_ready",
        "competing_process_absence",
        "artifact_fit",
        "physical_trajectory_executed",
    }
    return (
        set(checks) == expected
        and all(bool(value) for name, value in checks.items() if name != "physical_trajectory_executed")
        and checks["physical_trajectory_executed"] is False
    )


def rehearse() -> tuple[str, str]:
    _assert_wsl_scratch()
    collisions = [
        path
        for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT)
        if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R373 readiness output collision: {collisions}")
    contract = build_contract()
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    other = _other_research_python_processes()
    logical, physical, wsl_available = _memory_resources()
    disk_free = shutil.disk_usage(ROOT).free
    anchor_execution = _read_hashed_json(_parent_paths()["object_execution"])
    anchor_capacity = _read_hashed_json(_parent_paths()["object_capacity"])
    projected_bytes = _projected_artifact_bytes(contract)
    capacity = _build_capacity_payload(
        anchor_execution=anchor_execution,
        anchor_capacity=anchor_capacity,
        projected_artifact_bytes=projected_bytes,
        disk_free_bytes=disk_free,
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=wsl_available,
        runtime=runtime,
        sources=sources,
        parents=parents,
    )
    capacity["other_processes"] = other
    capacity["checks"]["competing_process_absence"] = not other
    if other:
        capacity["readiness"] = "HOLD"
    capacity_sha = _write_new_json(CAPACITY, capacity)
    checks = {
        "source_hash": all(item["sha256"] for item in sources.values()),
        "parent_hash": all(item["sha256"] for item in parents.values()),
        "installed_package": runtime.get("andes_version") == "2.0.0",
        "installed_case": bool(runtime.get("case_sha256")),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": _plan_is_active(),
        "contract_closed": _contract_is_closed(contract),
        "capacity_ready": capacity["readiness"] == "RUN-READY",
        "competing_process_absence": not other,
        "artifact_fit": bool(capacity["checks"]["artifact_fit"]),
        "physical_trajectory_executed": False,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "checks": checks,
        "readiness": "RUN-READY" if _rehearsal_checks({"checks": checks}) else "HOLD",
        "contract_sha256": _payload_sha256(contract),
        "capacity_sha256": capacity_sha,
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "formal_authority": False,
        "training_executed": False,
    }
    rehearsal_sha = _write_new_json(REHEARSAL, payload)
    if payload["readiness"] != "RUN-READY":
        raise RuntimeError(f"R373 rehearsal HOLD: {checks}")
    print(f"readiness=RUN-READY rehearsal_sha256={rehearsal_sha}", flush=True)
    return rehearsal_sha, capacity_sha


def prepare() -> str:
    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R373 seal or formal output already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if rehearsal.get("readiness") != "RUN-READY" or not _rehearsal_checks(rehearsal):
        raise RuntimeError("R373 rehearsal is not RUN-READY")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R373 capacity is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    if sources != rehearsal["sources"] or parents != rehearsal["parents"]:
        raise RuntimeError("R373 source or parent drift after rehearsal")
    contract = build_contract()
    if _payload_sha256(contract) != rehearsal["contract_sha256"]:
        raise RuntimeError("R373 contract drift after rehearsal")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": _payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": rehearsal["installed_runtime"],
        "capacity_sha256": _sha256_file(CAPACITY),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "launch": {
            "host_process_budget": 1,
            "wsl_python_processes": 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
        },
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(SEAL, payload)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R373 expected seal hash does not match")
    if seal.get("contract_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R373 sealed contract hash mismatch")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R373 source drift after seal")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R373 parent drift after seal")
    if seal.get("rehearsal_sha256") != _sha256_file(REHEARSAL):
        raise RuntimeError("R373 rehearsal drift after seal")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R373 capacity drift after seal")
    return seal, digest


def _run_arm(
    condition: Mapping[str, Any],
    arm_id: str,
    *,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(int(contract["seed"]))
    base_env.STEPS_PER_EPISODE = int(contract["steps"])
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    failure: str | None = None
    try:
        port_env.reset(delta_u=dict(condition["delta_u"]))
        identity = _identity(base_env)
        request = action_request(arm_id, contract=contract)
        for step_index in range(int(contract["steps"])):
            _observation, _reward, done, info = port_env.step(request)
            row = _port_row(info, step_index=step_index, done=bool(done))
            rows.append(row)
            if row["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:  # retained in the immutable attempt
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        port_env.close()
    return {
        "condition_id": str(condition["condition_id"]),
        "delta_u": dict(condition["delta_u"]),
        "arm_id": arm_id,
        "identity": identity or {},
        "steps": rows,
        "completed_steps": len(rows),
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def execute(*, expected_sha256: str) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R373 output collision: {DEFAULT_OUT}")
    attempt_digest = _write_new_json(
        DEFAULT_OUT / "formal_attempt.json",
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
    try:
        records = [
            _run_arm(condition, str(arm_id), contract=seal["contract"])
            for condition in seal["contract"]["conditions"]
            for arm_id in seal["contract"]["arm_ids"]
        ]
        execution = {
            "schema_version": 1,
            "round": ROUND_ID,
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "wall_seconds": time.perf_counter() - started,
            "record_count": len(records),
            "records": records,
            "reward_used_for_gate": False,
            "training_executed": False,
        }
        execution_digest = _write_new_json(
            DEFAULT_OUT / "formal_execution.json", execution
        )
        analysis = classify_records(records, contract=seal["contract"])
        analysis.update(
            {
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
            }
        )
        analysis_digest = _write_new_json(
            DEFAULT_OUT / "formal_analysis.json", analysis
        )
        _write_new_json(
            DEFAULT_OUT / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": _relative(DEFAULT_OUT / "formal_attempt.json"),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": _relative(DEFAULT_OUT / "formal_execution.json"),
                        "sha256": execution_digest,
                    },
                    {
                        "path": _relative(DEFAULT_OUT / "formal_analysis.json"),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        print(f"classification={analysis['classification']}", flush=True)
        return analysis_digest
    except Exception as exc:
        _write_new_json(
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
        rehearse()
    elif args.command == "prepare":
        prepare()
    else:
        execute(expected_sha256=args.expected_seal_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
