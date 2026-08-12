"""Seal and execute the R372 VSG energy-port physical object gate.

All physical trajectories must run through ``scripts/andes_scratch.py`` in
WSL.  Rehearsal performs only static/runtime/resource checks, creates no ANDES
environment, and derives the one-process capacity record from the measured
R365 same-plant anchor.  The runner has no training, tuning, retry, resize, or
alternate-output surface.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.vsg_energy_port_object_gate import (
    action_request,
    build_contract,
    classify_records,
)


ROUND_ID = "R372"
PLAN = ROOT / "memory/rounds/R372/plan.md"
REHEARSAL = ROOT / "memory/rounds/R372/rehearsal.json"
CAPACITY_ANCHOR = ROOT / "memory/rounds/R365/capacity_evidence_v2.json"
CAPACITY = ROOT / "memory/rounds/R372/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R372/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r372_energy_port_object_gate"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = _sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/vsg_energy_port_object_gate.py",
        "classifier_tests": ROOT / "tests/test_vsg_energy_port_object_gate.py",
        "runner_tests": ROOT / "tests/test_r372_energy_port_object_gate.py",
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "energy_contract": ROOT
        / "src/andes_rl_kundur/control/active_power.py",
        "energy_port": ROOT / "src/andes_rl_kundur/control/vsg_energy_port.py",
        "energy_port_environment": ROOT
        / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py",
        "energy_port_tests": ROOT / "tests/test_vsg_energy_port.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_environment": ROOT
        / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "static_contract_claim": ROOT / "memory/claims/CLM-1000.md",
        "static_contract_feed": ROOT / "paper/paralleled_vsg_marl/reports/R371.md",
        "static_contract_analysis": ROOT
        / "results/research_loop/r371_vsg_energy_port_design/analysis_v5.json",
        "static_contract_verdict": ROOT / "memory/rounds/R371/verdict.md",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in parents.items()
    }


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R372 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R372 must run through scripts/andes_scratch.py")


def _other_research_python_processes() -> list[dict[str, Any]]:
    if os.name != "posix":
        return []
    own_pid = os.getpid()
    matches: list[dict[str, Any]] = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            pid = int(path.parent.name)
            if pid == own_pid:
                continue
            command = path.read_bytes().replace(b"\x00", b" ").decode(
                "utf-8", errors="replace"
            )
        except (OSError, ValueError):
            continue
        lowered = command.lower()
        if "python" not in lowered:
            continue
        if "andes-rl-kundur" in lowered and (
            "run_r" in lowered or "train" in lowered or "eval" in lowered
        ):
            matches.append({"pid": pid, "command": command.strip()})
    return matches


def _memory_resources() -> tuple[int, int, int]:
    logical_processors = int(os.cpu_count() or 1)
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition(":")
        if not separator:
            continue
        meminfo[name] = int(value.strip().split()[0]) * 1024
    wsl_available = int(meminfo.get("MemAvailable", 0))
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        physical_memory = int(completed.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        physical_memory = int(meminfo.get("MemTotal", 0))
    if min(logical_processors, physical_memory, wsl_available) <= 0:
        raise RuntimeError("failed to capture positive host/WSL capacity resources")
    return logical_processors, physical_memory, wsl_available


def _runtime_matches_anchor(
    runtime: Mapping[str, Any],
    anchor_runtime: Mapping[str, Any],
) -> bool:
    identity_fields = (
        "andes_version",
        "andes_module",
        "case_path",
        "case_sha256",
    )
    compared = [field for field in identity_fields if field in anchor_runtime]
    return bool(compared) and all(
        runtime.get(field) == anchor_runtime.get(field) for field in compared
    )


def _projected_artifact_bytes(contract: Mapping[str, Any]) -> int:
    zero4 = [0.0] * 4
    row = {
        "step_index": 0,
        "time": 0.2,
        "requested_power_system_pu": zero4,
        "commanded_power_system_pu": zero4,
        "sampled_omega_pu": [1.0] * 4,
        "baseline_pref_system_pu": zero4,
        "pref_written_system_pu": zero4,
        "pref_readback_system_pu": zero4,
        "torque_readback_system_pu": zero4,
        "achieved_power_system_pu": zero4,
        "soc": [float(contract["soc_initial"])] * 4,
        "charged_energy_mwh": zero4,
        "discharged_energy_mwh": zero4,
        "total_charged_energy_mwh": zero4,
        "total_discharged_energy_mwh": zero4,
        "saturation_reasons": [[], [], [], []],
        "omega": [1.0] * 4,
        "freq_hz_physical": [60.0] * 4,
        "P_es": zero4,
        "M_es": [200.0] * 4,
        "D_es": [100.0] * 4,
        "delta_M": zero4,
        "delta_D": zero4,
        "md_action_norm": [[0.0, 0.0] for _ in range(4)],
        "tds_failed": False,
        "done": False,
    }
    records = [
        {
            "arm_id": arm_id,
            "identity": {
                "n_agents": 4,
                "vsg_idx": contract["expected_vsg_idx"],
                "vsg_buses": contract["expected_vsg_buses"],
            },
            "steps": [dict(row) for _ in range(int(contract["steps"]))],
            "completed_steps": int(contract["steps"]),
            "tds_failed": False,
            "failure": None,
        }
        for arm_id in contract["arm_ids"]
    ]
    placeholders = (
        {"round": ROUND_ID, "seal_sha256": "0" * 64},
        {"round": ROUND_ID, "records": records},
        {"round": ROUND_ID, "classification": "ANALYSIS-INVALID"},
        {"round": ROUND_ID, "entries": [{"sha256": "0" * 64}] * 3},
    )
    payload_bytes = sum(len(_canonical_bytes(value)) for value in placeholders)
    sidecars_and_metadata = 8 * 1024
    return payload_bytes + sidecars_and_metadata


def _build_capacity_payload(
    *,
    anchor: Mapping[str, Any],
    anchor_path: str,
    anchor_sha256: str,
    projected_artifact_bytes: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
    other_processes: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    contract = build_contract()
    empirical = anchor.get("empirical_anchor", {})
    representative_seconds = float(empirical.get("wall_seconds", 0.0))
    max_rss_kib = int(anchor.get("max_rss_kib", 0))
    anchor_host = anchor.get("host", {})
    anchor_runtime = anchor.get("installed_runtime", {})
    checks = {
        "anchor_valid": empirical.get("all_records_valid") is True,
        "anchor_serial": empirical.get("concurrent_workers") == 1
        and empirical.get("native_threads_per_worker") == 1,
        "anchor_five_steps": empirical.get("representative_steps") == 5,
        "current_host": logical_processors
        == int(anchor_host.get("logical_processors", -1))
        and physical_memory_bytes
        == int(anchor_host.get("physical_memory_bytes", -1)),
        "runtime_match": _runtime_matches_anchor(runtime, anchor_runtime),
        "memory_fit": wsl_memory_available_bytes > max_rss_kib * 1024 * 2,
        "artifact_fit": disk_free_bytes > projected_artifact_bytes,
        "competing_process_absence": not other_processes,
    }
    readiness = "RUN-READY" if all(checks.values()) else "HOLD"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": readiness,
        "checks": checks,
        "whole_host_python_process_budget": 1,
        "host": {
            "logical_processors": int(logical_processors),
            "physical_memory_bytes": int(physical_memory_bytes),
        },
        "wsl": {"memory_available_bytes": int(wsl_memory_available_bytes)},
        "empirical_anchor": {
            "path": anchor_path,
            "sha256": anchor_sha256,
            "all_records_valid": empirical.get("all_records_valid"),
            "representative_steps": empirical.get("representative_steps"),
            "representative_wall_seconds": representative_seconds,
            "max_rss_kib": max_rss_kib,
            "concurrent_workers": empirical.get("concurrent_workers"),
            "native_threads_per_worker": empirical.get(
                "native_threads_per_worker"
            ),
        },
        "projected_formal_wall_seconds": representative_seconds
        * len(contract["arm_ids"]),
        "artifact_projection": {
            "method": "serialized complete empty-value 50-row formal schema plus metadata",
            "projected_bytes": int(projected_artifact_bytes),
            "disk_free_bytes": int(disk_free_bytes),
        },
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "other_processes": [dict(process) for process in other_processes],
        "installed_runtime": dict(runtime),
        "sources": dict(sources),
        "parents": dict(parents),
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }


def _rehearsal_checks(payload: Mapping[str, Any]) -> bool:
    checks = payload.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        return False
    positive_checks = {
        key: value
        for key, value in checks.items()
        if key != "physical_trajectory_executed"
    }
    return bool(positive_checks) and all(
        value is True for value in positive_checks.values()
    ) and checks.get("physical_trajectory_executed") is False


def rehearse() -> tuple[str, str]:
    _assert_wsl_scratch()
    collisions = [
        candidate
        for candidate in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT)
        if candidate.exists()
    ]
    if collisions:
        raise FileExistsError(f"R372 pre-attempt artifact exists: {collisions}")
    anchor = _read_hashed_json(CAPACITY_ANCHOR)
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    logical, physical_memory, wsl_available = _memory_resources()
    disk_free = int(shutil.disk_usage(ROOT).free)
    projection = _projected_artifact_bytes(build_contract())
    other = _other_research_python_processes()
    capacity = _build_capacity_payload(
        anchor=anchor,
        anchor_path=_relative(CAPACITY_ANCHOR),
        anchor_sha256=_sha256_file(CAPACITY_ANCHOR),
        projected_artifact_bytes=projection,
        disk_free_bytes=disk_free,
        logical_processors=logical,
        physical_memory_bytes=physical_memory,
        wsl_memory_available_bytes=wsl_available,
        runtime=runtime,
        sources=sources,
        parents=parents,
        other_processes=other,
    )
    plan_text = PLAN.read_text(encoding="utf-8")
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": "state: active" in plan_text
        and "manuscript_line: paralleled-vsg-marl" in plan_text,
        "contract_closed": len(build_contract()["arm_ids"]) == 10
        and build_contract()["steps"] == 5
        and build_contract()["training_authorized"] is False,
        "capacity_anchor": capacity["checks"]["anchor_valid"] is True
        and capacity["checks"]["anchor_serial"] is True
        and capacity["checks"]["runtime_match"] is True,
        "current_host": capacity["checks"]["current_host"] is True
        and capacity["checks"]["memory_fit"] is True,
        "competing_process_absence": not other,
        "artifact_fit": capacity["checks"]["artifact_fit"] is True,
        "physical_trajectory_executed": False,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": _payload_sha256(build_contract()),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "checks": checks,
        "capacity_readiness": capacity["readiness"],
        "formal_authority": False,
        "training_executed": False,
    }
    if not _rehearsal_checks(payload) or capacity["readiness"] != "RUN-READY":
        raise RuntimeError(
            f"R372 rehearsal is HOLD: rehearsal={checks}, "
            f"capacity={capacity['checks']}"
        )
    rehearsal_digest = _write_new_json(REHEARSAL, payload)
    capacity_digest = _write_new_json(CAPACITY, capacity)
    return rehearsal_digest, capacity_digest


def prepare() -> str:
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if not _rehearsal_checks(rehearsal):
        raise RuntimeError("R372 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R372 capacity gate is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    if rehearsal["sources"] != sources or capacity["sources"] != sources:
        raise RuntimeError("R372 source drift before sealing")
    if rehearsal["parents"] != parents or capacity["parents"] != parents:
        raise RuntimeError("R372 parent drift before sealing")
    if rehearsal["installed_runtime"] != runtime:
        raise RuntimeError("R372 installed runtime drift before sealing")
    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R372 seal/formal artifact collision")
    contract = build_contract()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": _payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "capacity_sha256": _sha256_file(CAPACITY),
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
    return _write_new_json(SEAL, payload)


def _identity(env: Any) -> dict[str, Any]:
    positions = list(env._vsg_pos)
    return {
        "n_agents": int(env.N_AGENTS),
        "vsg_idx": [str(value) for value in env.vsg_idx],
        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in positions],
    }


def _vsg_vector(env: Any, variable_name: str) -> np.ndarray:
    variable = getattr(env.ss.GENCLS, variable_name)
    return np.asarray(
        [variable.v[position] for position in env._vsg_pos], dtype=float
    )


def _pref_vector(env: Any) -> np.ndarray:
    return np.asarray(
        [env.ss.SynGen.get_pref(env.ss, index) for index in env.vsg_idx],
        dtype=float,
    )


def _base_row(
    env: Any,
    *,
    step_index: int,
    baseline_pref: np.ndarray,
    omega_before: np.ndarray,
    info: Mapping[str, Any],
    done: bool,
) -> dict[str, Any]:
    omega_after = np.asarray(info["omega"], dtype=float)
    torque = _vsg_vector(env, "tm")
    achieved = (torque - baseline_pref) * 0.5 * (
        omega_before + omega_after
    )
    zeros = np.zeros(4)
    return {
        "step_index": step_index,
        "time": float(info["time"]),
        "requested_power_system_pu": zeros.tolist(),
        "commanded_power_system_pu": zeros.tolist(),
        "sampled_omega_pu": omega_before.tolist(),
        "baseline_pref_system_pu": baseline_pref.tolist(),
        "pref_written_system_pu": baseline_pref.tolist(),
        "pref_readback_system_pu": _pref_vector(env).tolist(),
        "torque_readback_system_pu": torque.tolist(),
        "achieved_power_system_pu": achieved.tolist(),
        "soc": [float(build_contract()["soc_initial"])] * 4,
        "charged_energy_mwh": zeros.tolist(),
        "discharged_energy_mwh": zeros.tolist(),
        "total_charged_energy_mwh": zeros.tolist(),
        "total_discharged_energy_mwh": zeros.tolist(),
        "saturation_reasons": [[], [], [], []],
        "omega": omega_after.tolist(),
        "freq_hz_physical": np.asarray(
            info["freq_hz_physical"], dtype=float
        ).tolist(),
        "P_es": np.asarray(info["P_es"], dtype=float).tolist(),
        "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
        "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
        "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
        "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
        "md_action_norm": np.zeros((4, 2)).tolist(),
        "tds_failed": bool(info["tds_failed"]),
        "done": bool(done),
    }


def _port_row(
    info: Mapping[str, Any],
    *,
    step_index: int,
    done: bool,
) -> dict[str, Any]:
    def values(key: str) -> list[Any]:
        return np.asarray(info[key], dtype=float).tolist()

    return {
        "step_index": step_index,
        "time": float(info["time"]),
        "requested_power_system_pu": values(
            "vsg_energy_port_requested_power_system_pu"
        ),
        "commanded_power_system_pu": values(
            "vsg_energy_port_commanded_power_system_pu"
        ),
        "sampled_omega_pu": values("vsg_energy_port_sampled_omega_pu"),
        "baseline_pref_system_pu": values(
            "vsg_energy_port_baseline_pref_system_pu"
        ),
        "pref_written_system_pu": values(
            "vsg_energy_port_pref_written_system_pu"
        ),
        "pref_readback_system_pu": values(
            "vsg_energy_port_pref_readback_system_pu"
        ),
        "torque_readback_system_pu": values(
            "vsg_energy_port_torque_readback_system_pu"
        ),
        "achieved_power_system_pu": values(
            "vsg_energy_port_achieved_power_system_pu"
        ),
        "soc": values("vsg_energy_port_soc"),
        "charged_energy_mwh": values("vsg_energy_port_charged_energy_mwh"),
        "discharged_energy_mwh": values(
            "vsg_energy_port_discharged_energy_mwh"
        ),
        "total_charged_energy_mwh": values(
            "vsg_energy_port_total_charged_energy_mwh"
        ),
        "total_discharged_energy_mwh": values(
            "vsg_energy_port_total_discharged_energy_mwh"
        ),
        "saturation_reasons": [
            list(reasons)
            for reasons in info["vsg_energy_port_saturation_reasons"]
        ],
        "omega": values("omega"),
        "freq_hz_physical": values("freq_hz_physical"),
        "P_es": values("P_es"),
        "M_es": values("M_es"),
        "D_es": values("D_es"),
        "delta_M": values("delta_M"),
        "delta_D": values("delta_D"),
        "md_action_norm": values("vsg_energy_port_md_action_norm"),
        "tds_failed": bool(info["tds_failed"]),
        "done": bool(done),
    }


def _run_arm(arm_id: str) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    contract = build_contract()
    base_env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(int(contract["seed"]))
    base_env.STEPS_PER_EPISODE = int(contract["steps"])
    port_env = None if arm_id == "base_zero" else AndesVSGEnergyPortEnv(
        base_env=base_env
    )
    active_env = base_env if port_env is None else port_env
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    failure: str | None = None
    try:
        active_env.reset(delta_u={})
        identity = _identity(base_env)
        baseline_pref = _pref_vector(base_env)
        request = action_request(arm_id, contract=contract)
        for step_index in range(int(contract["steps"])):
            if port_env is None:
                omega_before = _vsg_vector(base_env, "omega")
                _observation, _reward, done, info = base_env.step(
                    {index: np.zeros(2) for index in range(4)}
                )
                row = _base_row(
                    base_env,
                    step_index=step_index,
                    baseline_pref=baseline_pref,
                    omega_before=omega_before,
                    info=info,
                    done=bool(done),
                )
            else:
                _observation, _reward, done, info = port_env.step(request)
                row = _port_row(info, step_index=step_index, done=bool(done))
            rows.append(row)
            if row["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:  # retained in the immutable formal attempt
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        active_env.close()
    return {
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


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R372 seal digest mismatch")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R372 contract drift")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R372 sealed source drift")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R372 sealed parent drift")
    if seal.get("installed_runtime") != _installed_runtime():
        raise RuntimeError("R372 sealed runtime drift")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R372 capacity drift")
    return seal, digest


def execute(*, expected_sha256: str) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R372 output collision: {DEFAULT_OUT}")
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
        records = [_run_arm(arm_id) for arm_id in seal["contract"]["arm_ids"]]
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
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        rehearsal_digest, capacity_digest = rehearse()
        print(f"rehearsal_sha256={rehearsal_digest}")
        print(f"capacity_sha256={capacity_digest}")
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        print(
            "analysis_sha256="
            f"{execute(expected_sha256=args.expected_seal_sha256)}"
        )
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
