"""Sealed WSL runner for R416 (soft-spot program A3): headroom expansion.

Owner-authorized by the soft-spot experiment program
(``paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md``,
item A3, creative mode): re-run the R399 joint-headroom gate with the
expanded frozen candidate family of
``andes_rl_kundur/evaluation/soft_spot_headroom_expansion.py`` (a densified
20-law gain grid containing the original nine plus one PI-type law).  The
frozen R399 profiles, estimators, thresholds, guards, and the outcome-seeing
oracle are consumed verbatim via ``md_decoupling_headroom.classify_bank``.

Two registered anchors: the nine original laws' re-evaluated summaries must
reproduce the R399 records bit-identically, and the nine-law subset
classification must reproduce the R399 development selection and oracle
improvements within 1e-6 relative.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py rehearse
  python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py prepare
  python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py shards
  python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py shard <arm_id> [--resume]
  python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r416_headroom_expansion/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    adapt_v4_observations_to_physical,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    build_contract as _r399_contract,
    classify_bank,
    summarise_profile,
)
from andes_rl_kundur.evaluation.soft_spot_headroom_expansion import (  # noqa: E402
    build_contract as _expansion_contract,
    controller_for,
    extended_candidate_ids,
    original_nine_ids,
)
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R416"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R416/plan.md"
REHEARSAL = ROOT / "memory/rounds/R416/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R416/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R416/formal_seal.json"
OUT = ROOT / "results/research_loop/r416_headroom_expansion"
R399_OUT = ROOT / "results/research_loop/r399_md_decoupling_headroom"

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32
EVAL_WORKER_RSS_FLOOR_BYTES = 944214016
MARGINAL_GAIN_MIN = 1.05
MARGINAL_GAIN_CONFIRM_LOW = 1.03
MARGINAL_GAIN_CONFIRM_HIGH = 1.07
ANCHOR_TOLERANCE_RELATIVE = 1.0e-6


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R416 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R416 must run through scripts/andes_scratch.py")
    import torch

    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def build_contract() -> dict[str, Any]:
    return _expansion_contract()


def shard_list() -> list[str]:
    return [str(value) for value in build_contract()["arm_ids"]]


def _run_job(
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    arm_id: str,
) -> dict[str, Any]:
    """R399-faithful record loop (env, adaptation, action path verbatim)."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    contract = build_contract()
    total_steps = int(contract["steps"])
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
        positions = list(env._vsg_pos)
        identity = {
            "n_agents": int(env.N_AGENTS),
            "vsg_idx": [str(value) for value in env.vsg_idx],
            "vsg_buses": [
                int(env.ss.GENCLS.bus.v[position]) for position in positions
            ],
            "obs_dim": int(env.OBS_DIM),
            "baseline_m0": [float(value) for value in profile["baseline_m0"]],
            "baseline_d0": [float(value) for value in profile["baseline_d0"]],
            "control_nominal_frequency_hz": float(env.FN),
            "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
        }
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        controller = controller_for(arm_id)
        if controller is not None:
            controller.reset()
        for step_index in range(total_steps):
            if controller is None:
                action = np.zeros((4, 2), dtype=np.float32)
            else:
                action = controller.act(
                    adapt_v4_observations_to_physical(observation)
                )
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
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _evaluate_shard(arm_id: str, *, resume: bool) -> None:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    profiles = {
        str(profile["profile_id"]): profile for profile in contract["profiles"]
    }
    folder = OUT / "eval" / str(arm_id)
    for profile in contract["profiles"]:
        path = folder / (str(profile["profile_id"]) + ".json")
        sidecar = Path(f"{path}.sha256")
        if path.exists() or sidecar.exists():
            if resume and path.is_file() and sidecar.is_file():
                _read_hashed_json(path)
                continue
            raise FileExistsError(f"create-only output exists: {path}")
        records = [
            _run_job(profiles[str(profile["profile_id"])], scenario, str(arm_id))
            for scenario in profile["scenarios"]
        ]
        _write_new_json(path, {"records": records, "arm_id": str(arm_id)})


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("candidate_arm_ids") != extended_candidate_ids():
        raise RuntimeError("frozen candidates drifted from the R416 seal")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R416 seal: {name}")
    return seal


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r416_headroom_expansion.py",
        "expansion": ROOT
        / "src/andes_rl_kundur/evaluation/soft_spot_headroom_expansion.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "classifier_tests": ROOT / "tests/test_md_decoupling_headroom.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "controller_tests": ROOT / "tests/test_per_vsg_md.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
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
        "r399_formal_analysis": R399_OUT / "formal_analysis.json",
        "r399_formal_execution": R399_OUT / "formal_execution.json",
        "r399_formal_manifest": R399_OUT / "formal_manifest.json",
        "r399_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R399.md",
        "program": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
        "owner_decision": ROOT
        / "paper/yang_md_decoupling_marl/working"
        / "route_owner_decision_soft_spot_program_2026-08-16.md",
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


def _other_processes() -> list[dict[str, Any]]:
    own_pids = {os.getpid()}
    parent = int(os.getppid())
    while parent > 1 and len(own_pids) < 16:
        own_pids.add(parent)
        try:
            stat_fields = Path(f"/proc/{parent}/stat").read_text(
                encoding="utf-8"
            ).split()
            parent = int(stat_fields[3])
        except (OSError, ValueError, IndexError):
            break
    matches: list[dict[str, Any]] = []
    for entry in _other_research_python_processes():
        if int(entry["pid"]) in own_pids:
            continue
        command = str(entry.get("command", ""))
        if any(
            marker in command
            for marker in (
                "run_r410_message_repair.py",
                "run_r411_probe_amplitude_ladder.py",
                "run_r413_topology_robustness.py",
                "run_r415_energy_port_extra_banks.py",
                "run_r416_headroom_expansion.py",
                "soft_spot_shard_driver.py",
            )
        ):
            continue
        matches.append(entry)
    return matches


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = _r399_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R416" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_shape": len(contract["profiles"]) == 6
        and int(contract["steps"]) == 30,
        "candidates_frozen": len(extended_candidate_ids()) == 21
        and set(original_nine_ids()).issubset(set(extended_candidate_ids())),
        "output_absence": not OUT.exists(),
    }


def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    contract = build_contract()
    profile = contract["profiles"][0]
    scenario = next(
        row
        for row in profile["scenarios"]
        if row["pair_kind"] == "differential" and row["sign"] == "positive"
    )
    record = _run_job(profile, scenario, "local_neighbour_md_km2_kd2")
    return {
        "completed": bool(record["completed"] and not record["tds_failed"]),
        "tds_failed": bool(record["tds_failed"]),
        "failure": record["failure"],
        "worker_max_rss_kib": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ),
    }


def _measure_rung(workers: int) -> dict[str, Any]:
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(
            executor.map(_capacity_task, range(CAPACITY_TASKS_PER_RUNG))
        )
    wall_seconds = time.perf_counter() - started
    valid = all(
        result["completed"] is True and result["tds_failed"] is False
        for result in results
    )
    return {
        "workers": workers,
        "native_threads_per_worker": 1,
        "wall_seconds": wall_seconds,
        "job_count": len(results),
        "valid_completions": sum(
            result["completed"] is True and result["tds_failed"] is False
            for result in results
        ),
        "all_records_valid": bool(valid),
        "throughput_jobs_per_second": len(results) / wall_seconds,
        "maximum_worker_rss_bytes": max(
            int(result["worker_max_rss_kib"]) * 1024 for result in results
        ),
        "failures": [
            {"task": index, "failure": result["failure"]}
            for index, result in enumerate(results)
            if result["completed"] is not True or result["tds_failed"] is not False
        ],
    }


def _select_rung(
    final_throughput: Mapping[int, float],
    *,
    wsl_available_bytes: int,
) -> dict[str, Any]:
    selected: int | None = None
    selected_throughput: float | None = None
    decisions: list[dict[str, Any]] = []
    for workers in CAPACITY_RUNGS:
        throughput = final_throughput[workers]
        projected = EVAL_WORKER_RSS_FLOOR_BYTES * workers
        memory_safe = projected <= int(wsl_available_bytes) / 2
        if not memory_safe:
            accepted, reason = False, "memory_reserve_guard"
        elif selected is None:
            accepted, reason = True, "first_safe_rung"
        elif throughput < MARGINAL_GAIN_MIN * float(selected_throughput):
            accepted, reason = False, "insufficient_throughput_gain"
        else:
            accepted, reason = True, "safe_throughput_gain"
        decisions.append(
            {
                "workers": workers,
                "accepted": accepted,
                "reason": reason,
                "projected_concurrent_worker_rss_bytes": projected,
                "memory_safe": memory_safe,
                "final_throughput_jobs_per_second": throughput,
            }
        )
        if accepted:
            selected = workers
            selected_throughput = throughput
    if selected is None:
        return {
            "readiness": "HOLD",
            "selected_workers": None,
            "host_process_budget": None,
            "wsl_python_processes": None,
            "rung_decisions": decisions,
        }
    return {
        "readiness": "RUN-READY",
        "selected_workers": selected,
        "host_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "selected_throughput_jobs_per_second": float(selected_throughput),
        "rung_decisions": decisions,
    }


def measure_capacity() -> str:
    _assert_wsl_scratch()
    for candidate in (CAPACITY, REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R416 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R416 formal output exists before capacity")
    other = _other_processes()
    if other:
        raise RuntimeError(
            "other research Python processes are active: " + str(other)
        )
    logical, physical_memory, wsl_available = _memory_resources()
    first_pass = [_measure_rung(workers) for workers in CAPACITY_RUNGS]
    final: dict[int, float] = {
        workers: first_pass[index]["throughput_jobs_per_second"]
        for index, workers in enumerate(CAPACITY_RUNGS)
    }
    confirm_pairs: list[tuple[int, int]] = []
    for index in range(len(CAPACITY_RUNGS) - 1):
        low = CAPACITY_RUNGS[index]
        high = CAPACITY_RUNGS[index + 1]
        gain = final[high] / max(final[low], 1e-12)
        if MARGINAL_GAIN_CONFIRM_LOW <= gain <= MARGINAL_GAIN_CONFIRM_HIGH:
            confirm_pairs.append((low, high))
    remeasure = sorted({worker for pair in confirm_pairs for worker in pair})
    second_pass: list[dict[str, Any]] = []
    if remeasure:
        second_pass = [_measure_rung(workers) for workers in remeasure]
        for workers in remeasure:
            values = [
                first_pass[CAPACITY_RUNGS.index(workers)][
                    "throughput_jobs_per_second"
                ],
                second_pass[remeasure.index(workers)]["throughput_jobs_per_second"],
            ]
            final[workers] = float(np.mean(values))
    selection = _select_rung(final, wsl_available_bytes=wsl_available)
    return _write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_eval_capacity_ladder_rungs_1_2_4_8_12_16",
            "authorization": "owner-authorized soft-spot A3 headroom expansion",
            "representative_task": {
                "arm_id": "local_neighbour_md_km2_kd2",
                "profile": str(build_contract()["profiles"][0]["profile_id"]),
                "tasks_per_rung": CAPACITY_TASKS_PER_RUNG,
            },
            "eval_worker_rss_floor": {
                "bytes": EVAL_WORKER_RSS_FLOOR_BYTES,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative per-worker RSS floor (R402 anchor)",
            },
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "rungs": first_pass,
            "confirmation_pairs": [
                {"low_workers": low, "high_workers": high}
                for low, high in confirm_pairs
            ],
            "confirmation_pass_2": second_pass,
            "final_throughput_jobs_per_second": final,
            **selection,
            "whole_host_python_process_budget": selection.get(
                "host_process_budget"
            ),
            "empirical_anchor": {
                "all_records_valid": True,
                "concurrent_workers": (
                    int(selection["selected_workers"]) + 1
                    if selection["selected_workers"] is not None
                    else None
                ),
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "other_processes": other,
            "memory_rule": (
                "projected concurrent eval-worker RSS must not exceed half "
                "of WSL total memory"
            ),
            "marginal_rule": (
                "next rung accepted only at >=5 percent marginal throughput "
                "gain; pairs within 5%+-2pp re-measured once and averaged"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": _source_manifest(),
            "installed_runtime": _installed_runtime(),
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def rehearse() -> str:
    _assert_wsl_scratch()
    for candidate in (REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R416 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_shape",
        "candidates_frozen",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R416 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    contract = build_contract()
    profile = contract["profiles"][0]
    scenario = next(
        row
        for row in profile["scenarios"]
        if row["pair_kind"] == "differential" and row["sign"] == "positive"
    )
    rehearsal = {}
    for arm_id in ("zero", "local_neighbour_md_km2_kd2", "pi_frequency_md"):
        record = _run_job(profile, scenario, arm_id)
        if not record["completed"] or record["tds_failed"]:
            raise RuntimeError(f"R416 rehearsal trajectory failed: {arm_id}")
        rehearsal[arm_id] = {
            "completed_steps": record["completed_steps"],
            "tds_failed": record["tds_failed"],
        }
    return _write_new_json(
        REHEARSAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "checks": checks,
            "rehearsal_records": rehearsal,
            "physical_trajectory_executed": True,
            "formal_artifacts_created": False,
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


def prepare() -> str:
    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    snapshot_sources = _source_manifest()
    snapshot_parents = _parent_manifest()
    snapshot_runtime = _installed_runtime()
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_shape",
        "candidates_frozen",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R416 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R416 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R416 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R416 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R416 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R416 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R416 formal artifact exists before sealing")
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "candidate_arm_ids": extended_candidate_ids(),
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "the candidate family only: the R399 nine-law grid is "
                "densified to 20 laws and one PI-type law is added; "
                "profiles, estimators, thresholds, guards, and the oracle "
                "semantics are the R399 assets read-only"
            ),
            "launch": {
                "host_process_budget": process_count,
                "wsl_python_processes": process_count,
                "worker_processes": workers,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": False,
        },
    )


def _collect_summaries() -> list[dict[str, Any]]:
    contract = build_contract()
    summaries = []
    for arm_id in contract["arm_ids"]:
        for profile in contract["profiles"]:
            path = OUT / "eval" / str(arm_id) / (
                str(profile["profile_id"]) + ".json"
            )
            payload = _read_hashed_json(path)
            summary = summarise_profile(payload["records"], contract=contract)
            summary["profile_id"] = str(profile["profile_id"])
            summary["arm_id"] = str(arm_id)
            summaries.append(summary)
    return summaries


def _nine_law_anchor(summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    nine = set(original_nine_ids())
    r399_contract = _r399_contract()
    subset = [
        dict(row)
        for row in summaries
        if str(row["arm_id"]) in nine or str(row["arm_id"]) == "zero"
    ]
    r416_nine = classify_bank(subset, contract=r399_contract)
    r399_analysis = _read_hashed_json(R399_OUT / "formal_analysis.json")
    r399_classification = r399_analysis.get("classification", {})
    deviations: dict[str, float] = {}
    comparisons = (
        ("selected_deterministic_arm", "selected_deterministic_arm"),
    )
    for r416_key, r399_key in comparisons:
        left = r416_nine.get(r416_key)
        right = r399_classification.get(r399_key)
        if left is not None and right is not None and left == right:
            deviations[f"{r416_key}_equal"] = 0.0
        else:
            deviations[f"{r416_key}_equal"] = 1.0
    off_improvement = float(
        r416_nine.get("oracle_gate", {}).get("off_diagonal_improvement", float("nan"))
    )
    differential_improvement = float(
        r416_nine.get("oracle_gate", {}).get(
            "differential_improvement", float("nan")
        )
    )
    r399_oracle = r399_classification.get("oracle_gate", {})
    for name, left, right in (
        (
            "off_diagonal_improvement",
            off_improvement,
            float(r399_oracle.get("off_diagonal_improvement", float("nan"))),
        ),
        (
            "differential_improvement",
            differential_improvement,
            float(
                r399_oracle.get("differential_improvement", float("nan"))
            ),
        ),
    ):
        denominator = max(abs(left), abs(right), 1.0e-30)
        deviations[name] = abs(left - right) / denominator
    verdict = (
        "NINE-LAW-ANCHOR-REPRODUCED"
        if all(value <= ANCHOR_TOLERANCE_RELATIVE for value in deviations.values())
        else "NINE-LAW-ANCHOR-DRIFT"
    )
    return {
        "verdict": verdict,
        "deviations": deviations,
        "r416_nine_law_classification": r416_nine["classification"],
        "r399_classification": r399_classification.get("classification"),
    }


def classify() -> str:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    summaries = _collect_summaries()
    classification = classify_bank(summaries, contract=contract)
    anchor = _nine_law_anchor(summaries)
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": "yang-md-decoupling-marl",
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": _sha256_file(SEAL),
        "classification": classification,
        "nine_law_anchor": anchor,
        "reward_used_for_gate": False,
        "training_executed": False,
    }
    analysis_path = OUT / "formal_analysis.json"
    digest = _write_new_json(analysis_path, analysis)
    manifest_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "analysis_sha256": digest,
        "input_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("*.json"))
            if path.name not in {"formal_analysis.json", "formal_manifest.json"}
        ],
        "arm_count": len(contract["arm_ids"]),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "measure-capacity",
            "rehearse",
            "prepare",
            "shards",
            "shard",
            "classify",
        ],
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "measure-capacity":
        safe_emit(f"R416 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R416 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R416 formal seal: {prepare()}")
    elif args.command == "shards":
        safe_emit(json.dumps(shard_list(), separators=(",", ":")))
    elif args.command == "shard":
        if not args.args:
            raise SystemExit("shard requires an arm id")
        extra = [item for item in args.args[1:] if item not in ("--resume",)]
        if extra:
            raise SystemExit(f"unexpected shard argument: {extra[0]}")
        resume = "--resume" in args.args
        _evaluate_shard(str(args.args[0]), resume=resume)
        safe_emit(f"R416 shard complete: {args.args[0]}")
    else:
        safe_emit(f"R416 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
