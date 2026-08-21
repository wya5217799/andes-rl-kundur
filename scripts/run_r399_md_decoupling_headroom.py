"""Sealed WSL runner for the R399 Yang-compatible joint-headroom gate."""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.per_vsg_md import (
    LocalNeighbourMDExecution,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (
    build_contract as _build_contract,
    classify_bank,
    summarise_profile,
)

ROUND_ID = "R399"
PLAN = ROOT / "memory/rounds/R399/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
ROUTE = ROOT / "paper/yang_md_decoupling_marl/working/route_contract.md"
REHEARSAL_V1 = ROOT / "memory/rounds/R399/rehearsal.json"
REHEARSAL_V2 = ROOT / "memory/rounds/R399/rehearsal_v2.json"
REHEARSAL = ROOT / "memory/rounds/R399/rehearsal_v3.json"
CAPACITY_V1 = ROOT / "memory/rounds/R399/capacity_evidence.json"
CAPACITY_V2 = ROOT / "memory/rounds/R399/capacity_evidence_v2.json"
CAPACITY = ROOT / "memory/rounds/R399/capacity_evidence_v3.json"
SEAL = ROOT / "memory/rounds/R399/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r399_md_decoupling_headroom"


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    """Best-effort progress output that cannot invalidate a completed job."""

    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def build_contract() -> dict[str, Any]:
    """Return the exact pure scientific contract used by the formal runner."""

    return _build_contract()


def formal_job_count(contract: Mapping[str, Any]) -> int:
    """Return the complete profile-scenario-arm record count."""

    return sum(len(profile["scenarios"]) for profile in contract["profiles"]) * len(
        contract["arm_ids"]
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r399_md_decoupling_headroom.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "classifier_tests": ROOT / "tests/test_md_decoupling_headroom.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "controller_tests": ROOT / "tests/test_per_vsg_md.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "route_contract": ROUTE,
        "line_registration_claim": ROOT / "memory/claims/CLM-1135.md",
        "line_registration_feed": ROOT
        / "paper/yang_md_decoupling_marl/reports/R398.md",
        "line_adr": ROOT
        / "docs/adr/0019-separate-yang-md-decoupling-marl-successor.md",
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
        raise RuntimeError("R399 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R399 must run through scripts/andes_scratch.py")


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


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 6
        and formal_job_count(contract) == 360
        and contract["reward_used_for_gate"] is False
        and contract["training_authorized"] is False,
    }


def rehearsal_checks_pass(checks: Mapping[str, Any]) -> bool:
    """Return whether the exact no-trajectory pre-attempt checks passed."""

    required_true = {
        "source_hash",
        "parent_hash",
        "installed_package",
        "installed_case",
        "output_absence",
        "active_plan",
        "active_line",
        "contract_closed",
    }
    return bool(
        all(checks.get(key) is True for key in required_true)
        and checks.get("physical_trajectory_executed") is False
    )


def _preattempt_snapshot() -> dict[str, Any]:
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        **_authority_checks(),
        "physical_trajectory_executed": False,
    }
    return {
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "checks": checks,
    }


def rehearse(path: Path = REHEARSAL) -> str:
    """Exercise the formal pre-attempt path without a physical trajectory."""

    _assert_wsl_scratch()
    collisions = [
        candidate
        for candidate in (path, CAPACITY, SEAL, DEFAULT_OUT)
        if candidate.exists()
    ]
    if collisions:
        raise FileExistsError(f"R399 pre-attempt artifact exists: {collisions}")
    snapshot = _preattempt_snapshot()
    if not rehearsal_checks_pass(snapshot["checks"]):
        raise RuntimeError(f"R399 rehearsal checks failed: {snapshot['checks']}")
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": _payload_sha256(build_contract()),
            **snapshot,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def _controller_for(arm_id: str) -> LocalNeighbourMDExecution | None:
    if arm_id == "zero":
        return None
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    if arm_id not in contracts:
        raise ValueError(f"unknown arm: {arm_id}")
    return LocalNeighbourMDExecution(contracts[arm_id])


def _identity(env: Any, profile: Mapping[str, Any]) -> dict[str, Any]:
    positions = list(env._vsg_pos)
    return {
        "n_agents": int(env.N_AGENTS),
        "vsg_idx": [str(value) for value in env.vsg_idx],
        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in positions],
        "obs_dim": int(env.OBS_DIM),
        "baseline_m0": [float(value) for value in profile["baseline_m0"]],
        "baseline_d0": [float(value) for value in profile["baseline_d0"]],
        "control_nominal_frequency_hz": float(env.FN),
        "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
    }


def _run_job(job: Mapping[str, Any]) -> dict[str, Any]:
    import resource

    import numpy as np

    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    profile = job["profile"]
    scenario = job["scenario"]
    arm_id = str(job["arm_id"])
    contract = build_contract()
    total_steps = int(job.get("steps_override") or contract["steps"])
    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    env: Any | None = None
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    initial_frequency: list[float] = []
    failure: str | None = None
    try:
        env = AndesMultiVSGEnvV4(
            random_disturbance=False,
            comm_fail_prob=0.0,
            config=V4Config(
                vsg_m0=200.0,
                d0_per_agent=tuple(float(value) for value in baseline_d),
            ),
            comm_delay_steps=0,
        )
        env.M0 = baseline_m.copy()
        env.D0_HETEROGENEOUS = baseline_d.copy()
        env.NEW_LOADS = {
            14: {
                "p0": float(profile["steady_loads"]["PQ_Bus14"]),
                "q0": 0.0,
            },
            15: {
                "p0": float(profile["steady_loads"]["PQ_Bus15"]),
                "q0": 0.0,
            },
        }
        env.seed(int(contract["seed"]))
        env.STEPS_PER_EPISODE = total_steps
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        identity = _identity(env, profile)
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        controller = _controller_for(arm_id)
        if controller is not None:
            controller.reset()
        for step_index in range(total_steps):
            if controller is None:
                action = np.zeros((4, 2), dtype=np.float32)
            else:
                action = controller.act(adapt_v4_observations_to_physical(observation))
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, done, info = env.step(action_dict)
            actual_m = np.asarray(
                [env.ss.GENCLS.M.v[position] for position in env._vsg_pos],
                dtype=float,
            )
            actual_d = np.asarray(
                [env.ss.GENCLS.D.v[position] for position in env._vsg_pos],
                dtype=float,
            )
            rows.append(
                {
                    "step_index": step_index,
                    "time": float(info["time"]),
                    "action_norm": action.astype(float).tolist(),
                    "freq_hz_physical": np.asarray(
                        info["freq_hz_physical"], dtype=float
                    ).tolist(),
                    "M_es": actual_m.tolist(),
                    "D_es": actual_d.tolist(),
                    "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
                    "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
                    "tds_failed": bool(info["tds_failed"]),
                    "done": bool(done),
                }
            )
            if info["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        if env is not None:
            env.close()
    return {
        "profile_id": str(profile["profile_id"]),
        "split": str(profile["split"]),
        "scenario_id": str(scenario["scenario_id"]),
        "pair_kind": str(scenario["pair_kind"]),
        "sign": str(scenario["sign"]),
        "magnitude": float(scenario["magnitude"]),
        "delta_u": dict(scenario["delta_u"]),
        "arm_id": arm_id,
        "identity": identity,
        "initial_freq_hz_physical": initial_frequency,
        "steps": rows,
        "completed_steps": len(rows),
        "completed": failure is None and len(rows) == total_steps,
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "worker_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _capacity_jobs(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    choices = (
        ("dev_a", "common", "negative"),
        ("eval_a", "common", "positive"),
        ("eval_a", "differential", "positive"),
        ("eval_a", "localized", "positive"),
    )
    profiles = {str(row["profile_id"]): row for row in contract["profiles"]}
    jobs = []
    for profile_id, pair_kind, sign in choices:
        profile = profiles[profile_id]
        scenario = next(
            row
            for row in profile["scenarios"]
            if row["pair_kind"] == pair_kind and row["sign"] == sign
        )
        jobs.append(
            {
                "profile": profile,
                "scenario": scenario,
                "arm_id": "zero",
                "steps_override": int(contract["steps"]),
            }
        )
    return jobs


def select_capacity_rung(
    rungs: Sequence[Mapping[str, Any]],
    *,
    wsl_available_bytes: int,
) -> dict[str, Any]:
    """Select the highest safe rung with five-percent marginal throughput."""

    selected: Mapping[str, Any] | None = None
    decisions: list[dict[str, Any]] = []
    for rung in rungs:
        workers = int(rung["workers"])
        throughput = float(rung["throughput_jobs_per_second"])
        projected_rss = int(rung["maximum_worker_rss_bytes"]) * workers
        memory_safe = projected_rss <= int(wsl_available_bytes) / 2
        valid = bool(rung["all_records_valid"])
        if not valid:
            accepted = False
            reason = "invalid_representative_records"
        elif not memory_safe:
            accepted = False
            reason = "memory_reserve_guard"
        elif selected is None:
            accepted = True
            reason = "first_safe_rung"
        elif throughput < 1.05 * float(selected["throughput_jobs_per_second"]):
            accepted = False
            reason = "insufficient_throughput_gain"
        else:
            accepted = True
            reason = "safe_throughput_gain"
        decisions.append(
            {
                "workers": workers,
                "accepted": accepted,
                "reason": reason,
                "projected_concurrent_worker_rss_bytes": projected_rss,
                "memory_safe": memory_safe,
            }
        )
        if accepted:
            selected = rung
    if selected is None:
        return {
            "readiness": "HOLD",
            "selected_workers": None,
            "host_process_budget": None,
            "wsl_python_processes": None,
            "rung_decisions": decisions,
        }
    workers = int(selected["workers"])
    return {
        "readiness": "RUN-READY",
        "selected_workers": workers,
        "host_process_budget": workers + 1,
        "wsl_python_processes": workers + 1,
        "selected_throughput_jobs_per_second": float(
            selected["throughput_jobs_per_second"]
        ),
        "rung_decisions": decisions,
    }


def upgrade_capacity_payload(
    original: Mapping[str, Any],
    *,
    snapshot: Mapping[str, Any],
    original_path: str,
    original_sha256: str,
) -> dict[str, Any]:
    """Add the repository host-budget field without rerunning measurements."""

    payload = dict(original)
    payload.update(
        {
            "schema_version": 2,
            "created_utc": datetime.now(UTC).isoformat(),
            "whole_host_python_process_budget": int(
                original["host_process_budget"]
            ),
            "empirical_anchor": {
                "all_records_valid": True,
                "concurrent_workers": int(original["wsl_python_processes"]),
                "simulator_workers": int(original["selected_workers"]),
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "sources": dict(snapshot["sources"]),
            "parents": dict(snapshot["parents"]),
            "installed_runtime": dict(snapshot["installed_runtime"]),
            "physical_capacity_rerun_executed": False,
            "capacity_schema_correction": (
                "adds the preflight whole-host budget alias; measured rungs, "
                "selection, resources, and ETA are unchanged"
            ),
            "supersedes_capacity": {
                "path": original_path,
                "sha256": original_sha256,
                "reason": "v1 omitted whole_host_python_process_budget",
            },
        }
    )
    return payload


def _memory_resources() -> tuple[int, int, int]:
    logical_processors = int(os.cpu_count() or 1)
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition(":")
        if separator:
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
        raise RuntimeError("failed to capture positive host/WSL resources")
    return logical_processors, physical_memory, wsl_available


def _measure_rung(jobs: Sequence[Mapping[str, Any]], workers: int) -> dict[str, Any]:
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        records = list(executor.map(_run_job, jobs))
    wall_seconds = time.perf_counter() - started
    valid = all(
        record["completed"] is True and record["tds_failed"] is False
        for record in records
    )
    return {
        "workers": workers,
        "native_threads_per_worker": 1,
        "wall_seconds": wall_seconds,
        "job_count": len(records),
        "valid_completions": sum(
            record["completed"] is True and record["tds_failed"] is False
            for record in records
        ),
        "all_records_valid": bool(valid),
        "throughput_jobs_per_second": len(records) / wall_seconds,
        "maximum_worker_rss_bytes": max(
            int(record["worker_max_rss_kib"]) * 1024 for record in records
        ),
        "failures": [
            {
                "profile_id": record["profile_id"],
                "scenario_id": record["scenario_id"],
                "failure": record["failure"],
            }
            for record in records
            if record["completed"] is not True or record["tds_failed"] is not False
        ],
    }


def measure_capacity(path: Path = CAPACITY) -> str:
    """Measure representative full-length work at the frozen worker ladder."""

    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    if not rehearsal_checks_pass(rehearsal["checks"]):
        raise RuntimeError("R399 rehearsal did not pass")
    snapshot = _preattempt_snapshot()
    if rehearsal["sources"] != snapshot["sources"]:
        raise RuntimeError("R399 source drift after rehearsal")
    if rehearsal["parents"] != snapshot["parents"]:
        raise RuntimeError("R399 parent drift after rehearsal")
    if path.exists() or SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R399 capacity/seal/formal artifact collision")
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    source_capacity = CAPACITY_V2 if CAPACITY_V2.exists() else CAPACITY_V1
    if source_capacity.exists():
        original = _read_hashed_json(source_capacity)
        if original.get("round") != ROUND_ID:
            raise RuntimeError("R399 v1 capacity belongs to another round")
        if original.get("contract_sha256") != _payload_sha256(build_contract()):
            raise RuntimeError("R399 v1 capacity contract drift")
        if original.get("parents") != snapshot["parents"]:
            raise RuntimeError("R399 v1 capacity parent drift")
        if original.get("installed_runtime") != snapshot["installed_runtime"]:
            raise RuntimeError("R399 v1 capacity runtime drift")
        allowed_operational_drift = {"runner", "runner_tests"}
        for name, current in snapshot["sources"].items():
            if name in allowed_operational_drift:
                continue
            if original["sources"].get(name) != current:
                raise RuntimeError(f"R399 v1 capacity source drift: {name}")
        corrected = upgrade_capacity_payload(
            original,
            snapshot=snapshot,
            original_path=_relative(source_capacity),
            original_sha256=_sha256_file(source_capacity),
        )
        return _write_new_json(path, corrected)
    logical, physical_memory, wsl_available = _memory_resources()
    jobs = _capacity_jobs(build_contract())
    rungs = [_measure_rung(jobs, workers) for workers in (1, 2, 4)]
    selection = select_capacity_rung(
        rungs, wsl_available_bytes=wsl_available
    )
    throughput = selection.get("selected_throughput_jobs_per_second")
    projected = (
        formal_job_count(build_contract()) / float(throughput)
        if throughput is not None
        else None
    )
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_capacity_ladder",
            "contract_sha256": _payload_sha256(build_contract()),
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "disk_free_bytes": int(shutil.disk_usage(ROOT).free),
            "rungs": rungs,
            **selection,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "other_processes": other,
            "projected_formal_wall_seconds": projected,
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": snapshot["sources"],
            "parents": snapshot["parents"],
            "installed_runtime": snapshot["installed_runtime"],
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def _plan_process_budget_matches(capacity: Mapping[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    expected = int(capacity["wsl_python_processes"])
    return bool(
        f"host_process_budget: {expected}" in plan_text
        and f"wsl_python_processes: {expected}" in plan_text
        and "native_threads_per_process: 1" in plan_text
        and "other_reserved_processes: 0" in plan_text
    )


def prepare(path: Path = SEAL) -> str:
    """Seal sources, contract, capacity, runtime, and the actual worker budget."""

    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    snapshot = _preattempt_snapshot()
    if not rehearsal_checks_pass(rehearsal["checks"]):
        raise RuntimeError("R399 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R399 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R399 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot["sources"]:
            raise RuntimeError("R399 source drift before seal")
        if payload["parents"] != snapshot["parents"]:
            raise RuntimeError("R399 parent drift before seal")
        if payload["installed_runtime"] != snapshot["installed_runtime"]:
            raise RuntimeError("R399 runtime drift before seal")
    if DEFAULT_OUT.exists() or path.exists():
        raise FileExistsError("R399 formal artifact exists before sealing")
    contract = build_contract()
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": _payload_sha256(contract),
            "sources": snapshot["sources"],
            "parents": snapshot["parents"],
            "installed_runtime": snapshot["installed_runtime"],
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "route_sha256": _sha256_file(ROUTE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "launch": {
                "host_process_budget": process_count,
                "wsl_python_processes": process_count,
                "worker_processes": workers,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_job_count": formal_job_count(contract),
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R399 seal digest mismatch")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R399 contract drift")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R399 source drift")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R399 parent drift")
    if seal.get("installed_runtime") != _installed_runtime():
        raise RuntimeError("R399 runtime drift")
    if seal.get("plan_sha256") != _sha256_file(PLAN):
        raise RuntimeError("R399 plan drift")
    if seal.get("line_sha256") != _sha256_file(LINE):
        raise RuntimeError("R399 line drift")
    if seal.get("route_sha256") != _sha256_file(ROUTE):
        raise RuntimeError("R399 route drift")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R399 capacity drift")
    return seal, digest


def _formal_jobs(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"profile": profile, "scenario": scenario, "arm_id": arm_id}
        for profile in contract["profiles"]
        for scenario in profile["scenarios"]
        for arm_id in contract["arm_ids"]
    ]


def execute(*, expected_sha256: str, out_dir: Path = DEFAULT_OUT) -> str:
    """Create one immutable complete formal attempt and terminal analysis."""

    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if out_dir.exists():
        raise FileExistsError(f"R399 output collision: {out_dir}")
    attempt_digest = _write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "launch": dict(seal["launch"]),
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    started = time.perf_counter()
    try:
        jobs = _formal_jobs(seal["contract"])
        workers = int(seal["launch"]["worker_processes"])
        records: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for index, record in enumerate(executor.map(_run_job, jobs), start=1):
                records.append(record)
                safe_emit(f"completed_jobs={index}/{len(jobs)}")
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
            out_dir / "formal_execution.json", execution
        )
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for record in records:
            key = (str(record["profile_id"]), str(record["arm_id"]))
            grouped.setdefault(key, []).append(record)
        summaries = [
            summarise_profile(grouped[key], contract=seal["contract"])
            for key in sorted(grouped)
        ]
        analysis = classify_bank(summaries, contract=seal["contract"])
        analysis.update(
            {
                "summaries": summaries,
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
            }
        )
        analysis_digest = _write_new_json(
            out_dir / "formal_analysis.json", analysis
        )
        manifest_digest = _write_new_json(
            out_dir / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": _relative(out_dir / "formal_attempt.json"),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": _relative(out_dir / "formal_execution.json"),
                        "sha256": execution_digest,
                    },
                    {
                        "path": _relative(out_dir / "formal_analysis.json"),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        safe_emit(f"manifest_sha256={manifest_digest}")
        safe_emit(f"classification={analysis['classification']}")
        return analysis_digest
    except Exception as exc:
        _write_new_json(
            out_dir / "formal_failure.json",
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
    commands.add_parser("measure-capacity")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        safe_emit(f"rehearsal_sha256={rehearse()}")
    elif args.command == "measure-capacity":
        safe_emit(f"capacity_sha256={measure_capacity()}")
    elif args.command == "prepare":
        safe_emit(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        safe_emit(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
