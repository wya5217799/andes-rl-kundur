"""Sealed WSL runner for the B3 diagnostics-instrumented rerun (R421).

Owner-authorized by the soft-spot program override deck item B3 (feedback
loop): rerun the repaired no-message and message arms at seeds 401/402/403
with the diagnostic learner subclasses
(``DiagnosticCDMATD3``) that replicate the frozen computation exactly and
add read-only instrumentation (P3 diagnostic set: critic/actor losses,
Bellman residuals, log-scale gradient norms, replay-coverage proxies).
Logging never consumes the RNG stream, so every run must be byte-identical
to the R410 checkpoints -- the pre-registered drift anchor compares the
final checkpoint sha256 with the R410 sealed records.

Completion criterion: per-run diagnostic CSVs + a hashed summary JSON with
the pre-registered readout-to-failure-class mapping; no evaluation bank is
consumed.

Lifecycle (WSL only, always through the scratch launcher):
  ... measure-capacity | rehearse | prepare | shard <arm>|<seed> | summarize
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
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
import torch

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    physical_costs,
)
from andes_rl_kundur.agents.cd_matd3_diagnostics import (  # noqa: E402
    DiagnosticCDMATD3,
)
from andes_rl_kundur.control.per_vsg_md import PerVSGMDActionProjector  # noqa: E402
from andes_rl_kundur.evaluation.cd_matd3_canary import (  # noqa: E402
    TOTAL_INTERACTION_STEPS,
    build_contract as _build_contract,
    contract_sha256,
    training_run_count,
)
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R421"
PLAN = ROOT / "memory/rounds/R421/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R421/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R421/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R421/formal_seal.json"
OUT = ROOT / "results/research_loop/r421_diagnostics"
R410_OUT = ROOT / "results/research_loop/r410_message_repair"

R402_TRAINING_WORKER_RSS_BYTES = 944214016
CAPACITY_RUNGS = (1, 2, 4, 8)
CAPACITY_TASKS_PER_RUNG = 32

DIAGNOSTIC_ARMS = ("cd_matd3_no_message", "cd_matd3_message")

DIAGNOSTIC_FIELDS = (
    "update_count",
    "critic_loss",
    "actor_loss_mean",
    "lagrange",
    "bellman_residual_mean",
    "bellman_residual_abs_max",
    "bellman_residual_std",
    "bellman_residual_q25",
    "bellman_residual_q50",
    "bellman_residual_q75",
    "critic_grad_norm_mean",
    "critic_grad_norm_max",
    "actor_grad_norm_mean",
    "actor_grad_norm_max",
    "td_error_std",
    "sampled_state_variance_mean",
)


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


def build_contract() -> dict[str, Any]:
    return _build_contract()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R421 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R421 must run through scripts/andes_scratch.py")
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != contract_sha256(build_contract()):
        raise RuntimeError("sealed contract drifted from the frozen module")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R421 seal: {name}")
    return seal


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r421_diagnostics.py",
        "learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "learner_tests": ROOT / "tests/test_cd_matd3_learner.py",
        "diagnostic_tests": ROOT / "tests/test_cd_matd3_diagnostics.py",
        "contract": ROOT / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r410_formal_analysis": R410_OUT / "formal_analysis.json",
        "r410_endpoint_table": R410_OUT / "endpoint_table.json",
        "program": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
        "feedback_research": ROOT
        / "paper/yang_md_decoupling_marl/working"
        / "feedback_loop_deep_research_2026-08-17.md",
    }
    for arm_id in DIAGNOSTIC_ARMS:
        for seed in (401, 402, 403):
            parents[f"r410_checkpoint_{arm_id}_s{seed}"] = (
                R410_OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
            )
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


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R421" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and list(contract["training_seeds"]) == [401, 402, 403],
        "output_absence": not OUT.exists(),
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
        if "run_r421_diagnostics.py" in command:
            continue
        matches.append(entry)
    return matches


def _agent_for(arm_id: str, device: str) -> Any:
    contract = build_contract()
    learner = contract["learner_contract"]
    kwargs = dict(
        hidden_sizes=list(learner["actor"]["hidden_sizes"]),
        lr=float(learner["lr"]),
        gamma=float(learner["gamma"]),
        tau=float(learner["tau"]),
        buffer_size=int(learner["buffer_size"]),
        batch_size=int(learner["batch_size"]),
        policy_noise=float(learner["policy_noise"]),
        noise_clip=float(learner["noise_clip"]),
        explore_noise=float(learner["explore_noise"]),
        policy_delay=int(learner["policy_delay"]),
        device=device,
    )
    if arm_id in DIAGNOSTIC_ARMS:
        return DiagnosticCDMATD3(
            lagrange_initial=1.0,
            actor_neighbour_mask=(arm_id == "cd_matd3_no_message"),
            **kwargs,
        )
    raise ValueError(f"unknown diagnostic arm: {arm_id}")


def _build_env(profile: Mapping[str, Any]) -> Any:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
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
        14: {"p0": float(profile["steady_loads"]["PQ_Bus14"]), "q0": 0.0},
        15: {"p0": float(profile["steady_loads"]["PQ_Bus15"]), "q0": 0.0},
    }
    env.seed(int(build_contract()["bank_seed"]))
    env.STEPS_PER_EPISODE = int(build_contract()["steps"])
    return env


def _joint_obs(observation: Mapping[int, Any]) -> np.ndarray:
    rows = [np.asarray(observation[i], dtype=np.float32) for i in range(4)]
    return np.concatenate(rows).astype(np.float32)


def _save_agent_snapshot(agent: Any, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def train_diagnostic_arm_seed(arm_id: str, seed: int) -> str:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    arm_root = OUT / "train" / arm_id
    run_dir = arm_root / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_new_json(
        run_dir / "started.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(contract),
            "torch_threads": torch.get_num_threads(),
        },
    )
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    scenarios = {
        str(scenario["scenario_id"]): (profile, scenario)
        for profile in development
        for scenario in profile["scenarios"]
    }
    schedule = list(contract["training_contract"]["development_scenario_order"])
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    random.seed(int(seed))
    agent = _agent_for(arm_id, "cpu")
    envs = {
        str(profile["profile_id"]): _build_env(profile)
        for profile in development
    }
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    total_steps = int(contract["training_contract"]["total_interaction_steps"])
    steps_per_episode = int(contract["steps"])
    csv_path = run_dir / "diagnostics.csv"
    csv_handle = csv_path.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_handle, fieldnames=list(DIAGNOSTIC_FIELDS))
    writer.writeheader()
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    episode_common_costs: list[float] = []
    invalid_reason: str | None = None
    lagrange_trace: list[float] = []
    reward = contract["reward_contract"]["cd_matd3"]
    budget = float(reward["common_budget_per_episode"])
    multiplier_step = float(reward["lagrange_step"])
    multiplier_max = float(reward["lagrange_maximum"])
    episode_index = 0
    update_count = 0
    any_tds_failure = False
    try:
        while executed_steps < total_steps:
            scenario_id = schedule[episode_index % len(schedule)]
            episode_index += 1
            profile, scenario = scenarios[scenario_id]
            env = envs[str(profile["profile_id"])]
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            projector.reset()
            initial_frequency = (
                np.asarray(env._get_vsg_omega(), dtype=float)
                * float(contract["physical_nominal_frequency_hz"])
            )
            previous_frequency = initial_frequency.copy()
            episode_common = 0.0
            for _step_index in range(steps_per_episode):
                joint = _joint_obs(observation)
                raw_action = agent.act(joint, deterministic=False)
                if not np.all(np.isfinite(raw_action)):
                    invalid_reason = "nonfinite actor output"
                    break
                action = projector.project(raw_action)
                action_dict = {
                    actor: np.asarray(action[actor], dtype=np.float32)
                    for actor in range(4)
                }
                observation, _rewards, done, info = env.step(action_dict)
                executed_steps += 1
                frequencies = np.asarray(info["freq_hz_physical"], dtype=float)
                rocof = (frequencies - previous_frequency) / float(
                    contract["dt_seconds"]
                )
                previous_frequency = frequencies.copy()
                tds_failed = bool(info["tds_failed"])
                next_joint = _joint_obs(observation)
                terminal = bool(done) or tds_failed
                if tds_failed:
                    differential_cost = 50.0
                    common_cost = 50.0
                else:
                    differential, common = physical_costs(
                        frequencies[None, :],
                        rocof[None, :],
                        np.asarray(info["P_es"], dtype=float)[None, :],
                        contract=contract,
                    )
                    differential_cost = float(differential[0])
                    common_cost = float(common[0])
                episode_common += common_cost
                agent.store(
                    joint,
                    action.reshape(-1),
                    np.array(
                        [-differential_cost, -common_cost], dtype=np.float32
                    ),
                    next_joint,
                    terminal,
                )
                diagnostics = agent.update()
                if diagnostics is not None:
                    update_count += 1
                    if not np.isfinite(diagnostics["critic_loss"]):
                        invalid_reason = "nonfinite critic loss"
                        break
                    row = {
                        "update_count": update_count,
                        **{
                            key: diagnostics.get(key, float("nan"))
                            for key in DIAGNOSTIC_FIELDS
                            if key != "update_count"
                        },
                    }
                    writer.writerow(row)
                if tds_failed:
                    tds_failed_episodes += 1
                    any_tds_failure = True
                    break
            if invalid_reason is not None:
                break
            episodes_attempted += 1
            multiplier = agent.lagrange_step(
                episode_common,
                budget=budget,
                step=multiplier_step,
                maximum=multiplier_max,
            )
            lagrange_trace.append(multiplier)
            episode_common_costs.append(episode_common)
    finally:
        csv_handle.close()
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass
    convergence_valid = invalid_reason is None and executed_steps == total_steps
    checkpoint_path = run_dir / "final.pt"
    checkpoint_sha = None
    if convergence_valid:
        checkpoint_sha = _save_agent_snapshot(agent, checkpoint_path)
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm_id": arm_id,
        "training_seed": int(seed),
        "interaction_steps": int(executed_steps),
        "episodes_attempted": int(episodes_attempted),
        "tds_failed_episodes": int(tds_failed_episodes),
        "convergence_diagnostics_valid": bool(convergence_valid),
        "missing": invalid_reason is not None,
        "invalid_reason": invalid_reason,
        "final_checkpoint_sha256": checkpoint_sha,
        "episode_common_costs": episode_common_costs[-20:],
        "lagrange_trace": lagrange_trace[-20:],
        "any_tds_failure": bool(any_tds_failure),
        "diagnostics_csv_sha256": _sha256_file(csv_path),
        "diagnostic_update_count": update_count,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    return _write_new_json(run_dir / "manifest.json", manifest)


# ── capacity / rehearsal / seal / summarize ───────────────────────────

def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    contract = build_contract()
    profile = next(
        row for row in contract["profiles"] if row["split"] == "development"
    )
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    agent = _agent_for("cd_matd3_message", "cpu")
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    completed = 0
    failure: str | None = None
    tds_failed = False
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        for _step_index in range(int(contract["steps"])):
            raw = agent.act(_joint_obs(observation), deterministic=True)
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, _done, info = env.step(action_dict)
            completed += 1
            if info["tds_failed"]:
                tds_failed = True
                failure = "TDS failed"
                break
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            env.close()
        except Exception:
            pass
    return {
        "completed": failure is None and completed == int(contract["steps"]),
        "tds_failed": bool(tds_failed),
        "failure": failure,
        "worker_max_rss_kib": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ),
    }


def _select_rung(
    rungs: Sequence[Mapping[str, Any]],
    *,
    wsl_available_bytes: int,
) -> dict[str, Any]:
    selected: Mapping[str, Any] | None = None
    selected_throughput: float | None = None
    decisions: list[dict[str, Any]] = []
    for rung in rungs:
        workers = int(rung["workers"])
        throughput = float(rung["throughput_jobs_per_second"])
        effective_rss = max(
            int(rung["maximum_worker_rss_bytes"]),
            R402_TRAINING_WORKER_RSS_BYTES,
        )
        projected = effective_rss * workers
        memory_safe = projected <= int(wsl_available_bytes) / 2
        valid = bool(rung["all_records_valid"])
        if not valid:
            accepted, reason = False, "invalid_representative_records"
        elif not memory_safe:
            accepted, reason = False, "training_memory_reserve_guard"
        elif selected is None:
            accepted, reason = True, "first_safe_rung"
        elif selected_throughput is not None and throughput < 1.05 * selected_throughput:
            accepted, reason = False, "insufficient_throughput_gain"
        else:
            accepted, reason = True, "safe_throughput_gain"
        decisions.append(
            {
                "workers": workers,
                "accepted": accepted,
                "reason": reason,
                "projected_training_worker_memory_bytes": projected,
                "training_worker_rss_bytes": effective_rss,
                "memory_safe": memory_safe,
            }
        )
        if accepted:
            selected = rung
            selected_throughput = throughput
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
        "selected_throughput_jobs_per_second": float(selected_throughput),
        "rung_decisions": decisions,
    }


def measure_capacity() -> str:
    _assert_wsl_scratch()
    for candidate in (CAPACITY, REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R421 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R421 formal output exists before capacity")
    other = _other_processes()
    if other:
        raise RuntimeError(
            "other research Python processes are active: " + str(other)
        )
    logical, physical_memory, wsl_available = _memory_resources()
    rungs = []
    for workers in CAPACITY_RUNGS:
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(
                executor.map(_capacity_task, range(CAPACITY_TASKS_PER_RUNG))
            )
        wall = time.perf_counter() - started
        valid = all(
            result["completed"] is True and result["tds_failed"] is False
            for result in results
        )
        rungs.append(
            {
                "workers": workers,
                "native_threads_per_worker": 1,
                "wall_seconds": wall,
                "job_count": len(results),
                "valid_completions": sum(
                    result["completed"] is True
                    and result["tds_failed"] is False
                    for result in results
                ),
                "all_records_valid": bool(valid),
                "throughput_jobs_per_second": len(results) / wall,
                "maximum_worker_rss_bytes": max(
                    int(result["worker_max_rss_kib"]) * 1024 for result in results
                ),
                "failures": [
                    {"task": index, "failure": result["failure"]}
                    for index, result in enumerate(results)
                    if result["completed"] is not True
                    or result["tds_failed"] is not False
                ],
            }
        )
    selection = _select_rung(rungs, wsl_available_bytes=wsl_available)
    return _write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_training_capacity_ladder_rungs_1_2_4_8",
            "authorization": "owner-authorized B3 diagnostics rerun",
            "contract_sha256": contract_sha256(build_contract()),
            "training_worker_rss_anchor": {
                "bytes": R402_TRAINING_WORKER_RSS_BYTES,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative live-training RSS floor",
            },
            "representative_task": {
                "arm_id": "cd_matd3_message",
                "tasks_per_rung": CAPACITY_TASKS_PER_RUNG,
            },
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "disk_free_bytes": int(shutil.disk_usage(ROOT).free),
            "rungs": rungs,
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
                "projected concurrent training-worker RSS must not exceed "
                "half of WSL total memory"
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
            raise FileExistsError(f"R421 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_closed",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R421 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    contract = build_contract()
    profile = next(
        row for row in contract["profiles"] if row["split"] == "development"
    )
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    rehearsal_dir = ROOT / "tmp" / "andes" / "r421_rehearsal_checkpoints"
    rehearsal_dir.mkdir(parents=True, exist_ok=True)
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)
        for arm_id in DIAGNOSTIC_ARMS:
            agent = _agent_for(arm_id, "cpu")
            projector = PerVSGMDActionProjector(
                action_slew_limit=float(contract["action_slew_limit"])
            )
            projector.reset()
            joint = _joint_obs(observation)
            raw = agent.act(joint, deterministic=False)
            if not np.all(np.isfinite(raw)):
                raise RuntimeError("nonfinite rehearsal actor output")
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, _done, info = env.step(action_dict)
            if info["tds_failed"]:
                raise RuntimeError("rehearsal TDS failure")
            next_joint = _joint_obs(observation)
            agent.store(
                joint,
                action.reshape(-1),
                np.array([-0.5, -0.5], dtype=np.float32),
                next_joint,
                False,
            )
            diagnostics = agent.update()
            if diagnostics is not None and not np.isfinite(
                diagnostics["critic_loss"]
            ):
                raise RuntimeError("nonfinite rehearsal update")
            probe = rehearsal_dir / f"{arm_id}.pt"
            if probe.exists():
                probe.unlink()
            agent.save(probe)
            restored = _agent_for(arm_id, "cpu")
            restored.load(probe)
    finally:
        try:
            env.close()
        except Exception:
            pass
    return _write_new_json(
        REHEARSAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(contract),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "checks": checks,
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
        "contract_closed",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R421 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R421 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R421 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R421 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R421 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R421 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R421 formal artifact exists before sealing")
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": build_contract(),
            "contract_sha256": contract_sha256(build_contract()),
            "diagnostic_arms": list(DIAGNOSTIC_ARMS),
            "diagnostic_fields": list(DIAGNOSTIC_FIELDS),
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "logging only: the diagnostic learner subclasses replicate "
                "the frozen computation exactly (bit-comparable to R410) "
                "and add read-only instrumentation; the R410 mask repair, "
                "arms, seeds, rewards, and budgets are unchanged"
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
            "training_authorized_in_this_round": True,
        },
    )


def summarize() -> str:
    _assert_wsl_scratch()
    load_seal()
    rows = []
    anchor_results = {}
    for arm_id in DIAGNOSTIC_ARMS:
        for seed in (401, 402, 403):
            manifest = _read_hashed_json(
                OUT / "train" / arm_id / f"seed{seed}" / "manifest.json"
            )
            r410_checkpoint = R410_OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
            r410_sha = _sha256_file(r410_checkpoint)
            anchor_results[f"{arm_id}|{seed}"] = {
                "r421_checkpoint_sha256": manifest.get(
                    "final_checkpoint_sha256"
                ),
                "r410_checkpoint_sha256": r410_sha,
                "byte_identical": (
                    manifest.get("final_checkpoint_sha256") == r410_sha
                ),
            }
            csv_path = OUT / "train" / arm_id / f"seed{seed}" / "diagnostics.csv"
            rows.append(
                {
                    "arm_id": arm_id,
                    "training_seed": int(seed),
                    "manifest": manifest,
                    "csv_sha256": _sha256_file(csv_path),
                }
            )
    anchor_verdict = (
        "R410-BIT-IDENTICAL"
        if all(value["byte_identical"] for value in anchor_results.values())
        else "DRIFT"
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": "yang-md-decoupling-marl",
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": _sha256_file(SEAL),
        "diagnostic_fields": list(DIAGNOSTIC_FIELDS),
        "runs": rows,
        "r410_anchor": anchor_results,
        "r410_anchor_verdict": anchor_verdict,
        "reward_used_for_gate": False,
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
        "csv_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("*.csv"))
        ],
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
            "shard",
            "summarize",
        ],
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "measure-capacity":
        safe_emit(f"R421 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R421 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R421 formal seal: {prepare()}")
    elif args.command == "shard":
        if not args.args:
            raise SystemExit("shard requires <arm>|<seed>")
        parts = str(args.args[0]).split("|")
        if len(parts) != 2 or parts[0] not in DIAGNOSTIC_ARMS:
            raise SystemExit("shard id must be <arm>|<seed> with a registered arm")
        safe_emit(
            "R421 training manifest: "
            + train_diagnostic_arm_seed(parts[0], int(parts[1]))
        )
    else:
        safe_emit(f"R421 formal analysis: {summarize()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
