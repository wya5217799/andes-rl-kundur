"""Execute the sealed R367 deterministic-efficacy/headroom gate.

All physical commands must run through ``scripts/andes_scratch.py`` in WSL.
The runner exposes no training surface, executes the complete finite bank
serially, and writes every scientific artifact create-only.
"""

from __future__ import annotations

import os

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    LocalNeighbourMDExecution,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.evaluation.deterministic_headroom import (  # noqa: E402
    build_contract,
    classify_summaries,
    summarise_record,
)


ROUND_ID = "R367"
QUESTION_ID = "Q-0103"
PLAN = ROOT / "memory/rounds/R367/plan.md"
QUESTION = ROOT / "memory/questions/Q-0103.md"
REHEARSAL = ROOT / "memory/rounds/R367/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R367/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R367/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r367_deterministic_headroom"


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
        / "src/andes_rl_kundur/evaluation/deterministic_headroom.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "classifier_tests": ROOT / "tests/test_deterministic_headroom.py",
        "runner_tests": ROOT / "tests/test_r367_deterministic_headroom.py",
        "plan": PLAN,
        "question": QUESTION,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
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
        "design_claim": ROOT / "memory/claims/CLM-0980.md",
        "design_feed": ROOT / "paper/paralleled_vsg_marl/reports/R366.md",
        "design_analysis": ROOT
        / "results/research_loop/r366_per_vsg_md_design/analysis_v3.json",
        "scenario_source": ROOT
        / "results/r274_prospective_active_power_authority/formal_bank.json",
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
        raise RuntimeError("R367 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R367 must run through scripts/andes_scratch.py")


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


def _rehearsal_checks(payload: Mapping[str, Any]) -> bool:
    checks = payload.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        return False
    positive = {
        key: value
        for key, value in checks.items()
        if key != "physical_trajectory_executed"
    }
    return bool(positive) and all(value is True for value in positive.values()) and (
        checks.get("physical_trajectory_executed") is False
    )


def rehearse(path: Path = REHEARSAL) -> str:
    _assert_wsl_scratch()
    collisions = [candidate for candidate in (path, CAPACITY, SEAL, DEFAULT_OUT) if candidate.exists()]
    if collisions:
        raise FileExistsError(f"R367 pre-attempt artifact exists: {collisions}")
    runtime = _installed_runtime()
    contract = build_contract()
    checks = {
        "source_hash": bool(_source_manifest()),
        "parent_hash": bool(_parent_manifest()),
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": "state: active" in PLAN.read_text(encoding="utf-8")
        and "manuscript_line: paralleled-vsg-marl" in PLAN.read_text(encoding="utf-8"),
        "in_flight_question": "status: in-flight"
        in QUESTION.read_text(encoding="utf-8"),
        "contract_closed": len(contract["scenarios"]) == 8
        and len(contract["arm_ids"]) == 10
        and contract["training_authorized"] is False,
        "physical_trajectory_executed": False,
    }
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": _payload_sha256(contract),
            "sources": _source_manifest(),
            "parents": _parent_manifest(),
            "installed_runtime": runtime,
            "checks": checks,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def _identity(env: Any, *, baseline_d0: np.ndarray) -> dict[str, Any]:
    positions = list(env._vsg_pos)
    return {
        "n_agents": int(env.N_AGENTS),
        "vsg_idx": [str(value) for value in env.vsg_idx],
        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in positions],
        "obs_dim": int(env.OBS_DIM),
        "baseline_m0": np.asarray(env.M0, dtype=float).tolist(),
        "baseline_d0": baseline_d0.astype(float).tolist(),
        "control_nominal_frequency_hz": float(env.FN),
        "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
    }


def _controller_for(arm_id: str) -> LocalNeighbourMDExecution | None:
    if arm_id == "zero":
        return None
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    if arm_id not in contracts:
        raise ValueError(f"unknown arm: {arm_id}")
    return LocalNeighbourMDExecution(contracts[arm_id])


def _run_scenario_arm(
    scenario: Mapping[str, Any],
    arm_id: str,
    *,
    steps_override: int | None = None,
) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    contract = build_contract()
    total_steps = int(steps_override or contract["steps"])
    d0 = np.asarray(contract["baseline_d0"], dtype=float)
    env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        config=V4Config(d0_per_agent=tuple(float(value) for value in d0)),
        comm_delay_steps=0,
    )
    env.seed(int(contract["seed"]))
    env.STEPS_PER_EPISODE = total_steps
    controller = _controller_for(arm_id)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    failure: str | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        identity = _identity(env, baseline_d0=d0)
        if controller is not None:
            controller.reset()
        for step_index in range(total_steps):
            if controller is None:
                action = np.zeros((4, 2), dtype=np.float32)
            else:
                adapted = adapt_v4_observations_to_physical(observation)
                action = controller.act(adapted)
            action_dict = {
                agent: np.asarray(action[agent], dtype=np.float32)
                for agent in range(4)
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
                    "P_es": np.asarray(info["P_es"], dtype=float).tolist(),
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
        env.close()
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "location": str(scenario["location"]),
        "sign": str(scenario["sign"]),
        "delta_u": dict(scenario["delta_u"]),
        "arm_id": arm_id,
        "identity": identity or {},
        "steps": rows,
        "completed_steps": len(rows),
        "completed": failure is None and len(rows) == total_steps,
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
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
        raise RuntimeError("failed to capture positive host/WSL capacity resources")
    return logical_processors, physical_memory, wsl_available


def _build_capacity_payload(
    *,
    representative_valid: bool,
    representative_wall_seconds: float,
    max_rss_kib: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
) -> dict[str, Any]:
    contract = build_contract()
    jobs = len(contract["scenarios"]) * len(contract["arm_ids"])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if representative_valid else "HOLD",
        "whole_host_python_process_budget": 1,
        "host": {
            "logical_processors": int(logical_processors),
            "physical_memory_bytes": int(physical_memory_bytes),
        },
        "wsl": {"memory_available_bytes": int(wsl_memory_available_bytes)},
        "empirical_anchor": {
            "all_records_valid": bool(representative_valid),
            "concurrent_workers": 1,
            "native_threads_per_worker": 1,
            "representative_steps": 5,
            "wall_seconds": float(representative_wall_seconds),
        },
        "representative_steps": 5,
        "representative_wall_seconds": float(representative_wall_seconds),
        "projected_formal_wall_seconds": float(representative_wall_seconds)
        * (jobs * int(contract["steps"]) / 5.0),
        "max_rss_kib": int(max_rss_kib),
        "disk_free_bytes": int(disk_free_bytes),
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "other_processes": [],
        "installed_runtime": dict(runtime),
        "sources": dict(sources),
        "parents": dict(parents),
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }


def measure_capacity(path: Path = CAPACITY) -> str:
    import resource

    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    if not _rehearsal_checks(rehearsal):
        raise RuntimeError("R367 rehearsal did not pass")
    if rehearsal["sources"] != _source_manifest() or rehearsal["parents"] != _parent_manifest():
        raise RuntimeError("R367 source or parent drift after rehearsal")
    if path.exists() or SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R367 capacity/seal/formal artifact collision")
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    scenario = build_contract()["scenarios"][0]
    started = time.perf_counter()
    representative = _run_scenario_arm(scenario, "zero", steps_override=5)
    wall_seconds = time.perf_counter() - started
    valid = bool(representative["completed"] and not representative["tds_failed"])
    usage = resource.getrusage(resource.RUSAGE_SELF)
    disk = shutil.disk_usage(ROOT)
    logical, physical_memory, wsl_available = _memory_resources()
    payload = _build_capacity_payload(
        representative_valid=valid,
        representative_wall_seconds=wall_seconds,
        max_rss_kib=int(usage.ru_maxrss),
        disk_free_bytes=int(disk.free),
        logical_processors=logical,
        physical_memory_bytes=physical_memory,
        wsl_memory_available_bytes=wsl_available,
        runtime=_installed_runtime(),
        sources=_source_manifest(),
        parents=_parent_manifest(),
    )
    payload["other_processes"] = other
    return _write_new_json(path, payload)


def prepare(path: Path = SEAL) -> str:
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if not _rehearsal_checks(rehearsal):
        raise RuntimeError("R367 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R367 capacity gate is not RUN-READY")
    if rehearsal["sources"] != _source_manifest() or capacity["sources"] != _source_manifest():
        raise RuntimeError("R367 source drift before sealing")
    if rehearsal["parents"] != _parent_manifest() or capacity["parents"] != _parent_manifest():
        raise RuntimeError("R367 parent drift before sealing")
    if rehearsal["installed_runtime"] != _installed_runtime():
        raise RuntimeError("R367 installed runtime drift before sealing")
    if DEFAULT_OUT.exists():
        raise FileExistsError("R367 formal output exists before sealing")
    contract = build_contract()
    return _write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": _payload_sha256(contract),
            "sources": _source_manifest(),
            "parents": _parent_manifest(),
            "installed_runtime": _installed_runtime(),
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
        },
    )


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R367 seal digest mismatch")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R367 contract drift")
    if seal.get("sources") != _source_manifest() or seal.get("parents") != _parent_manifest():
        raise RuntimeError("R367 sealed source or parent drift")
    if seal.get("installed_runtime") != _installed_runtime():
        raise RuntimeError("R367 sealed runtime drift")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R367 capacity drift")
    return seal, digest


def execute(*, expected_sha256: str, out_dir: Path = DEFAULT_OUT) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if out_dir.exists():
        raise FileExistsError(f"R367 output collision: {out_dir}")
    attempt_digest = _write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    started = time.perf_counter()
    try:
        records: list[dict[str, Any]] = []
        jobs = [
            (scenario, arm_id)
            for scenario in seal["contract"]["scenarios"]
            for arm_id in seal["contract"]["arm_ids"]
        ]
        for index, (scenario, arm_id) in enumerate(jobs, start=1):
            records.append(_run_scenario_arm(scenario, arm_id))
            print(f"completed_jobs={index}/{len(jobs)}", flush=True)
        execution = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "wall_seconds": time.perf_counter() - started,
            "record_count": len(records),
            "records": records,
            "reward_used_for_gate": False,
            "training_executed": False,
        }
        execution_digest = _write_new_json(out_dir / "formal_execution.json", execution)
        summaries = [summarise_record(record, contract=seal["contract"]) for record in records]
        analysis = classify_summaries(summaries, contract=seal["contract"])
        analysis.update(
            {
                "summaries": summaries,
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
            }
        )
        analysis_digest = _write_new_json(out_dir / "formal_analysis.json", analysis)
        _write_new_json(
            out_dir / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {"path": _relative(out_dir / "formal_attempt.json"), "sha256": attempt_digest},
                    {"path": _relative(out_dir / "formal_execution.json"), "sha256": execution_digest},
                    {"path": _relative(out_dir / "formal_analysis.json"), "sha256": analysis_digest},
                ],
            },
        )
        print(f"classification={analysis['classification']}", flush=True)
        return analysis_digest
    except Exception as exc:
        _write_new_json(
            out_dir / "formal_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
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
        print(f"rehearsal_sha256={rehearse()}")
    elif args.command == "measure-capacity":
        print(f"capacity_sha256={measure_capacity()}")
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        print(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
