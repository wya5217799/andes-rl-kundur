#!/usr/bin/env python3
"""Rehearse, seal, and execute the create-only R374 controller comparison.

Usage (WSL):
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r374_deterministic_decoupling.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r374_deterministic_decoupling.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r374_deterministic_decoupling.py execute \
        --expected-seal-sha256 <sha256>

The adapter contains no training, retry, bank-resize, gain override, output
override, or parallel-execution command. Formal artifacts are create-only.
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

import numpy as np

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

from andes_rl_kundur.control.active_power import PowerProjection  # noqa: E402
from andes_rl_kundur.control.cross_coordinate_decoupler import (  # noqa: E402
    CrossCoordinateAction,
    DistributedCrossCoordinateController,
    LocalDiagonalPIController,
)
from andes_rl_kundur.evaluation.deterministic_decoupling import (  # noqa: E402
    build_contract,
    classify_summaries,
    controller_spec,
    phase_jobs,
    probe_request,
    select_development_candidate,
    summarize_phase_records,
)

ROUND_ID = "R374"
ROUND_DIR = ROOT / "memory/rounds/R374"
PLAN = ROUND_DIR / "plan.md"
REHEARSAL = ROUND_DIR / "rehearsal.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
SEAL = ROUND_DIR / "formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r374_deterministic_decoupling"


def _payload_sha256(payload: object) -> str:
    import hashlib

    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r374_deterministic_decoupling.py",
        "controller": (
            ROOT / "src/andes_rl_kundur/control/cross_coordinate_decoupler.py"
        ),
        "controller_tests": ROOT / "tests/test_cross_coordinate_decoupler.py",
        "classifier": (
            ROOT / "src/andes_rl_kundur/evaluation/deterministic_decoupling.py"
        ),
        "classifier_tests": ROOT / "tests/test_deterministic_decoupling.py",
        "r372_runner_infrastructure": (
            ROOT / "scripts/run_r372_energy_port_object_gate.py"
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


def _source_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _source_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R374 source: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _parent_paths() -> dict[str, Path]:
    return {
        "authority_claim": ROOT / "memory/claims/CLM-1010.md",
        "authority_feed": ROOT / "paper/paralleled_vsg_marl/reports/R373.md",
        "authority_verdict": ROOT / "memory/rounds/R373/verdict.md",
        "authority_seal": ROOT / "memory/rounds/R373/formal_seal.json",
        "authority_analysis": (
            ROOT
            / "results/research_loop/r373_energy_port_authority/formal_analysis.json"
        ),
        "authority_execution": (
            ROOT
            / "results/research_loop/r373_energy_port_authority/formal_execution.json"
        ),
        "authority_capacity": (
            ROOT / "memory/rounds/R373/capacity_evidence_v2.json"
        ),
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _parent_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R374 parent: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _plan_is_active() -> bool:
    text = PLAN.read_text(encoding="utf-8")
    return "round: R374" in text and "state: active" in text


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    try:
        return bool(
            contract["round"] == ROUND_ID
            and int(contract["steps"]) == 50
            and float(contract["dt_seconds"]) == 0.2
            and int(contract["development"]["record_count"]) == 60
            and int(contract["evaluation"]["record_count"]) == 30
            and len(contract["distributed_candidates"]) == 4
            and len(phase_jobs("development", contract=contract)) == 60
            and contract["training_authorized"] is False
        )
    except (KeyError, TypeError, ValueError):
        return False


def _projected_artifact_bytes(contract: Mapping[str, Any]) -> int:
    zero4 = [0.0] * 4
    row = {
        "step_index": 0,
        "time": 0.0,
        "freq_hz_physical": [60.0] * 4,
        "requested_power_system_pu": zero4,
        "commanded_power_system_pu": zero4,
        "achieved_power_system_pu": zero4,
        "common_request_system_pu": zero4,
        "differential_request_system_pu": zero4,
        "common_estimate_hz": zero4,
        "soc": [0.5] * 4,
        "saturation_reasons": [[], [], [], []],
        "md_action_norm": [[0.0, 0.0]] * 4,
        "tds_failed": False,
    }
    record = {
        "phase": "development",
        "arm_id": "zero_feedback",
        "experiment_kind": "probe",
        "condition_id": "placeholder",
        "delta_u": {},
        "input_mode": "common",
        "sign": "positive",
        "identity": {},
        "steps": [row] * int(contract["steps"]),
        "completed_steps": int(contract["steps"]),
        "tds_failed": False,
        "failure": None,
    }
    placeholder = {
        "development_execution": {
            "records": [record] * int(contract["development"]["record_count"])
        },
        "evaluation_execution": {
            "records": [record] * int(contract["evaluation"]["record_count"])
        },
        "development_analysis": {},
        "formal_analysis": {},
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
    contract = build_contract()
    anchor_steps = 30 * 40
    formal_records = int(contract["development"]["record_count"]) + int(
        contract["evaluation"]["record_count"]
    )
    formal_steps = formal_records * int(contract["steps"])
    projected_wall = (
        1.5 * float(anchor_execution["wall_seconds"]) * formal_steps / anchor_steps
    )
    anchor_runtime = dict(anchor_capacity["installed_runtime"])
    host = dict(anchor_capacity["host"])
    runtime_fields = [
        field
        for field in ("andes_version", "case_sha256")
        if field in anchor_runtime
    ]
    empirical_anchor = dict(anchor_capacity.get("empirical_anchor", {}))
    if "max_rss_kib" in empirical_anchor:
        memory_fit = wsl_memory_available_bytes > (
            8 * int(empirical_anchor["max_rss_kib"]) * 1024
        )
    else:
        prior_available = int(
            anchor_capacity.get("wsl", {}).get("memory_available_bytes", 0)
        )
        memory_fit = (
            bool(anchor_capacity.get("checks", {}).get("memory_fit"))
            and prior_available > 0
            and wsl_memory_available_bytes >= 0.8 * prior_available
        )
    checks = {
        "anchor_complete": (
            int(anchor_execution.get("record_count", -1)) == 30
            and not any(
                bool(record.get("tds_failed"))
                for record in anchor_execution.get("records", [])
            )
        ),
        "anchor_serial": (
            int(anchor_capacity.get("wsl_python_processes", -1)) == 1
            and int(anchor_capacity.get("native_threads_per_process", -1)) == 1
        ),
        "runtime_match": bool(runtime_fields)
        and all(runtime.get(field) == anchor_runtime.get(field) for field in runtime_fields),
        "current_host": (
            logical_processors == int(host["logical_processors"])
            and physical_memory_bytes == int(host["physical_memory_bytes"])
        ),
        "memory_fit": memory_fit,
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
            "execution_path": parents["authority_execution"]["path"],
            "execution_sha256": parents["authority_execution"]["sha256"],
            "capacity_path": parents["authority_capacity"]["path"],
            "capacity_sha256": parents["authority_capacity"]["sha256"],
            "record_count": int(anchor_execution["record_count"]),
            "environment_steps": anchor_steps,
            "wall_seconds": float(anchor_execution["wall_seconds"]),
        },
        "formal_projection": {
            "record_count": formal_records,
            "environment_steps": formal_steps,
            "wall_seconds_with_1p5_safety_factor": projected_wall,
        },
        "artifact_projection": {
            "method": "two times complete placeholder formal schema",
            "projected_bytes": projected_artifact_bytes,
            "disk_free_bytes": disk_free_bytes,
        },
        "host": {
            "logical_processors": logical_processors,
            "physical_memory_bytes": physical_memory_bytes,
        },
        "wsl": {"memory_available_bytes": wsl_memory_available_bytes},
        "memory_fit_rule": {
            "anchor_guard_required": True,
            "minimum_current_to_anchor_available_ratio": 0.8,
        },
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
        and all(
            bool(value)
            for name, value in checks.items()
            if name != "physical_trajectory_executed"
        )
        and checks["physical_trajectory_executed"] is False
    )


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R374 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R374 must run through scripts/andes_scratch.py")


def rehearse() -> tuple[str, str]:
    _assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R374 readiness output collision: {collisions}")
    contract = build_contract()
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    other = _other_research_python_processes()
    logical, physical, wsl_available = _memory_resources()
    disk_free = shutil.disk_usage(ROOT).free
    anchor_execution = _read_hashed_json(_parent_paths()["authority_execution"])
    anchor_capacity = _read_hashed_json(_parent_paths()["authority_capacity"])
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
        "readiness": (
            "RUN-READY" if _rehearsal_checks({"checks": checks}) else "HOLD"
        ),
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
        raise RuntimeError(f"R374 rehearsal HOLD: {checks}")
    print(f"readiness=RUN-READY rehearsal_sha256={rehearsal_sha}", flush=True)
    return rehearsal_sha, capacity_sha


def prepare() -> str:
    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R374 seal or formal output already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if rehearsal.get("readiness") != "RUN-READY" or not _rehearsal_checks(rehearsal):
        raise RuntimeError("R374 rehearsal is not RUN-READY")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R374 capacity is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    if sources != rehearsal["sources"] or parents != rehearsal["parents"]:
        raise RuntimeError("R374 source or parent drift after rehearsal")
    contract = build_contract()
    if _payload_sha256(contract) != rehearsal["contract_sha256"]:
        raise RuntimeError("R374 contract drift after rehearsal")
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
        raise RuntimeError("R374 expected seal hash does not match")
    if seal.get("contract_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R374 sealed contract hash mismatch")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R374 source drift after seal")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R374 parent drift after seal")
    if seal.get("rehearsal_sha256") != _sha256_file(REHEARSAL):
        raise RuntimeError("R374 rehearsal drift after seal")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R374 capacity drift after seal")
    return seal, digest


def _make_controller(arm_id: str, contract: Mapping[str, Any]) -> Any | None:
    spec = controller_spec(arm_id, contract=contract)
    architecture = spec["architecture"]
    common = {
        "device_count": int(contract["device_count"]),
        "nominal_frequency_hz": float(contract["nominal_frequency_hz"]),
        "kp_system_pu_per_hz": float(spec.get("kp_system_pu_per_hz", 0.0)),
        "ki_system_pu_per_hz_s": float(spec.get("ki_system_pu_per_hz_s", 0.0)),
    }
    if architecture == "zero_feedback":
        return None
    if architecture == "local_diagonal_pi":
        return LocalDiagonalPIController(**common)
    adjacency = {
        int(index): tuple(neighbours)
        for index, neighbours in contract["adjacency"].items()
    }
    return DistributedCrossCoordinateController(
        adjacency=adjacency,
        **common,
        sync_gain_system_pu_per_hz=float(spec["sync_gain_system_pu_per_hz"]),
        consensus_gain_per_s=float(spec["consensus_gain_per_s"]),
    )


def _zero_action(contract: Mapping[str, Any]) -> CrossCoordinateAction:
    zero = np.zeros(int(contract["device_count"]), dtype=float)
    return CrossCoordinateAction(zero.copy(), zero.copy(), zero.copy(), zero.copy())


def _run_job(job: Mapping[str, Any], *, contract: Mapping[str, Any]) -> dict[str, Any]:
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
    controller = _make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    failure: str | None = None
    previous_projection: PowerProjection | None = None
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = _identity(base_env)
        for step_index in range(int(contract["steps"])):
            frequencies = (
                np.asarray(base_env._get_vsg_omega(), dtype=float)
                * float(contract["nominal_frequency_hz"])
            )
            action = (
                _zero_action(contract)
                if controller is None
                else controller.act(
                    frequencies_hz=frequencies,
                    dt_seconds=float(contract["dt_seconds"]),
                    previous_projection=previous_projection,
                )
            )
            common = action.common_request_system_pu.copy()
            differential = action.differential_request_system_pu.copy()
            if job["experiment_kind"] == "probe":
                external = probe_request(
                    str(job["input_mode"]),
                    str(job["sign"]),
                    contract=contract,
                )
                if job["input_mode"] == "common":
                    common += external
                else:
                    differential += external
            request = common + differential
            _observation, _reward, done, info = port_env.step(request)
            row = _port_row(info, step_index=step_index, done=bool(done))
            row.update(
                {
                    "common_request_system_pu": common.tolist(),
                    "differential_request_system_pu": differential.tolist(),
                    "common_estimate_hz": action.common_estimate_hz.tolist(),
                }
            )
            rows.append(row)
            previous_projection = PowerProjection(
                requested_power_system_pu=np.asarray(
                    row["requested_power_system_pu"], dtype=float
                ),
                commanded_power_system_pu=np.asarray(
                    row["commanded_power_system_pu"], dtype=float
                ),
                saturation_reasons=tuple(
                    tuple(reason) for reason in row["saturation_reasons"]
                ),
            )
            if row["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:  # retained in the immutable attempt
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        port_env.close()
    return {
        "phase": str(job["phase"]),
        "arm_id": str(job["arm_id"]),
        "experiment_kind": str(job["experiment_kind"]),
        "condition_id": str(job["condition_id"]),
        "delta_u": dict(job["delta_u"]),
        "input_mode": job["input_mode"],
        "sign": job["sign"],
        "identity": identity or {},
        "steps": rows,
        "completed_steps": len(rows),
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _manifest_entry(path: Path, digest: str) -> dict[str, str]:
    return {"path": _relative(path), "sha256": digest}


def execute(*, expected_sha256: str) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R374 output collision: {DEFAULT_OUT}")
    attempt_path = DEFAULT_OUT / "formal_attempt.json"
    attempt_digest = _write_new_json(
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
    entries = [_manifest_entry(attempt_path, attempt_digest)]
    try:
        contract = seal["contract"]
        development_records = [
            _run_job(job, contract=contract)
            for job in phase_jobs("development", contract=contract)
        ]
        development_execution_path = DEFAULT_OUT / "development_execution.json"
        development_execution_digest = _write_new_json(
            development_execution_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "record_count": len(development_records),
                "records": development_records,
                "reward_used_for_gate": False,
                "training_executed": False,
            },
        )
        entries.append(
            _manifest_entry(
                development_execution_path,
                development_execution_digest,
            )
        )
        development_phase = summarize_phase_records(
            development_records,
            phase="development",
            contract=contract,
        )
        selection = select_development_candidate(
            development_phase["arm_summaries"],
            contract=contract,
        )
        development_analysis_path = DEFAULT_OUT / "development_analysis.json"
        development_analysis_digest = _write_new_json(
            development_analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "development": development_phase,
                "selection": selection,
                "held_out_inspected": False,
                "training_authorized": False,
            },
        )
        entries.append(
            _manifest_entry(development_analysis_path, development_analysis_digest)
        )

        selected = selection.get("selected_arm_id")
        evaluation_phase: dict[str, Any] | None = None
        if selection["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED":
            evaluation_records = [
                _run_job(job, contract=contract)
                for job in phase_jobs(
                    "evaluation",
                    selected_arm_id=str(selected),
                    contract=contract,
                )
            ]
            evaluation_execution_path = DEFAULT_OUT / "evaluation_execution.json"
            evaluation_execution_digest = _write_new_json(
                evaluation_execution_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "seal_sha256": seal_digest,
                    "development_selection_sha256": development_analysis_digest,
                    "record_count": len(evaluation_records),
                    "records": evaluation_records,
                    "reward_used_for_gate": False,
                    "training_executed": False,
                },
            )
            entries.append(
                _manifest_entry(
                    evaluation_execution_path,
                    evaluation_execution_digest,
                )
            )
            evaluation_phase = summarize_phase_records(
                evaluation_records,
                phase="evaluation",
                selected_arm_id=str(selected),
                contract=contract,
            )
            analysis = classify_summaries(
                selection,
                evaluation_phase["arm_summaries"],
                contract=contract,
            )
        else:
            analysis = {
                "classification": selection["classification"],
                "checks": {"development_candidate": False},
                "selected_arm_id": None,
                "training_authorized": False,
                "next_gate": None,
            }
        analysis.update(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "development_analysis_sha256": development_analysis_digest,
                "development_selection": selection,
                "evaluation": evaluation_phase,
                "wall_seconds": time.perf_counter() - started,
                "training_authorized": False,
            }
        )
        analysis_path = DEFAULT_OUT / "formal_analysis.json"
        analysis_digest = _write_new_json(analysis_path, analysis)
        entries.append(_manifest_entry(analysis_path, analysis_digest))
        _write_new_json(
            DEFAULT_OUT / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": entries,
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
