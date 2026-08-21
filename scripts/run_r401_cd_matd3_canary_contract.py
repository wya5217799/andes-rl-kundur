"""Sealed WSL runner for the R401 Gate A canary-contract freeze.

R401 executes no training and no evaluation.  Its only formal WSL entries
are the no-trajectory rehearsal and the representative capacity ladder that
freezes the host process budget; prepare() then seals the immutable Gate A
canary contract together with sources, parents, runtime, plan, and capacity.
The successor execution round must load this seal and may train exactly the
three registered learning arms.
"""

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
from andes_rl_kundur.evaluation.cd_matd3_canary import (
    TOTAL_INTERACTION_STEPS,
    build_contract as _build_contract,
    contract_sha256,
    evaluation_record_count,
    training_run_count,
)

ROUND_ID = "R401"
PLAN = ROOT / "memory/rounds/R401/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
ROUTE = ROOT / "paper/yang_md_decoupling_marl/working/route_amendment_r400.md"
REHEARSAL = ROOT / "memory/rounds/R401/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R401/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R401/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r401_cd_matd3_canary"


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
        "runner_tests": ROOT / "tests/test_run_r401_cd_matd3_canary_contract.py",
        "contract": ROOT
        / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        "contract_tests": ROOT / "tests/test_cd_matd3_canary.py",
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
        "route_amendment": ROUTE,
        "route_amendment_claim": ROOT / "memory/claims/CLM-1145.md",
        "route_amendment_feed": ROOT
        / "paper/yang_md_decoupling_marl/reports/R400.md",
        "headroom_claim": ROOT / "memory/claims/CLM-1140.md",
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
        raise RuntimeError("R401 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R401 must run through scripts/andes_scratch.py")


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
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R401" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and evaluation_record_count(contract) == 240
        and training_run_count(contract) == 9
        and contract["training_seeds"] == [401, 402, 403]
        and contract["training_contract"]["total_interaction_steps"]
        == TOTAL_INTERACTION_STEPS
        and contract["reward_contract"]["reward_used_for_gate"] is False,
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
        raise FileExistsError(f"R401 pre-attempt artifact exists: {collisions}")
    snapshot = _preattempt_snapshot()
    if not rehearsal_checks_pass(snapshot["checks"]):
        raise RuntimeError(
            "R401 rehearsal checks failed: " + str(snapshot["checks"])
        )
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(build_contract()),
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
    """Run one representative full-length zero-action rollout for capacity."""

    import resource

    import numpy as np

    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    profile = job["profile"]
    scenario = job["scenario"]
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
        env.seed(int(contract["bank_seed"]))
        env.STEPS_PER_EPISODE = total_steps
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        identity = _identity(env, profile)
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        for step_index in range(total_steps):
            action = np.zeros((4, 2), dtype=np.float32)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, done, info = env.step(action_dict)
            rows.append(
                {
                    "step_index": step_index,
                    "time": float(info["time"]),
                    "action_norm": action.astype(float).tolist(),
                    "freq_hz_physical": np.asarray(
                        info["freq_hz_physical"], dtype=float
                    ).tolist(),
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
        "arm_id": "zero",
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
        ("canary_dev_a", "common", "negative"),
        ("canary_dev_b", "common", "positive"),
        ("canary_dev_c", "differential", "positive"),
        ("canary_dev_d", "localized", "positive"),
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
        raise RuntimeError("R401 rehearsal did not pass")
    snapshot = _preattempt_snapshot()
    if rehearsal["sources"] != snapshot["sources"]:
        raise RuntimeError("R401 source drift after rehearsal")
    if rehearsal["parents"] != snapshot["parents"]:
        raise RuntimeError("R401 parent drift after rehearsal")
    if path.exists() or SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R401 capacity/seal/formal artifact collision")
    other = _other_research_python_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    logical, physical_memory, wsl_available = _memory_resources()
    jobs = _capacity_jobs(build_contract())
    rungs = [_measure_rung(jobs, workers) for workers in (1, 2, 4)]
    selection = select_capacity_rung(
        rungs, wsl_available_bytes=wsl_available
    )
    throughput = selection.get("selected_throughput_jobs_per_second")
    steps_per_second = (
        30.0 * float(throughput) if throughput is not None else None
    )
    canary_step_units = (
        training_run_count() * TOTAL_INTERACTION_STEPS
        + evaluation_record_count() * 30
    )
    projected = (
        float(canary_step_units) / float(steps_per_second)
        if steps_per_second is not None
        else None
    )
    workers = int(selection["selected_workers"] or 0)
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_capacity_ladder",
            "contract_sha256": contract_sha256(build_contract()),
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "disk_free_bytes": int(shutil.disk_usage(ROOT).free),
            "rungs": rungs,
            **selection,
            "whole_host_python_process_budget": int(
                selection["host_process_budget"]
            ),
            "empirical_anchor": {
                "all_records_valid": True,
                "concurrent_workers": workers + 1,
                "simulator_workers": workers,
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "other_processes": other,
            "canary_step_units": canary_step_units,
            "projected_canary_wall_seconds": projected,
            "projection_scope": (
                "training-step cost is anchored by the measured 30-step "
                "rollout; learner-update overhead is not included"
            ),
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
    """Seal the frozen contract, sources, capacity, runtime, and budget."""

    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    snapshot = _preattempt_snapshot()
    if not rehearsal_checks_pass(rehearsal["checks"]):
        raise RuntimeError("R401 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R401 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R401 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot["sources"]:
            raise RuntimeError("R401 source drift before seal")
        if payload["parents"] != snapshot["parents"]:
            raise RuntimeError("R401 parent drift before seal")
        if payload["installed_runtime"] != snapshot["installed_runtime"]:
            raise RuntimeError("R401 runtime drift before seal")
    if DEFAULT_OUT.exists() or path.exists():
        raise FileExistsError("R401 formal artifact exists before sealing")
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
            "contract_sha256": contract_sha256(contract),
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
            "canary_work_units": {
                "training_runs": training_run_count(),
                "evaluation_records": evaluation_record_count(),
                "total_interaction_steps_per_run": TOTAL_INTERACTION_STEPS,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": False,
            "successor_authorized": (
                "train exactly the three registered learning arms on seeds "
                "401/402/403 under this contract"
            ),
        },
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["rehearse", "measure-capacity", "prepare"])
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "rehearse":
        safe_emit(f"R401 rehearsal artifact: {rehearse()}")
    elif args.command == "measure-capacity":
        safe_emit(f"R401 capacity evidence: {measure_capacity()}")
    else:
        safe_emit(f"R401 formal seal: {prepare()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

