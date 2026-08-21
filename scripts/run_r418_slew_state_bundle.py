"""Sealed WSL runner for R418 (feedback loop / program B1): slew-state bundle.

Owner-authorized by the soft-spot program override deck item B1 (creative
mode, feedback-loop round): the single registered factor versus R410 is
the slew-state contract repair — every arm's actor observation gains the
previous *executed* (post-slew) action (7 -> 9 slots, neighbour mask
kept), and the target and online actor paths evaluate the same
post-projection quantity the environment executes.  Everything else is the
R402/R410 contract verbatim: three arms x seeds 401/402/403, 43,200
interaction steps per run, the same eight-profile partition, the same
hyperparameters, rewards, estimators, guards, and checkpoint rule.

Pre-registered decision rule: guards + endpoints versus R410 and versus
the deterministic reference, plus the message contrast under the repaired
bundle.  Creative mode: any arm passing the physical guards or any
classification flip is recorded, the manuscript is updated per the
evidence, and the loop continues; no pause.

Slew diagnostics (P1, feedback_loop_deep_research_2026-08-17.md): per-run
slew-saturation rate and execution-mismatch gap are recorded in every
training manifest.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py rehearse
  python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py prepare
  python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py train --arm <arm> --seed <seed>
  python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py evaluate
  python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r418_slew_state_bundle/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
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
    SlewAwareCDMATD3,
    SlewAwareYangScalarTD3,
    augment_joint_obs_np,
    physical_costs,
)
from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    PerVSGMDActionProjector,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.control.per_vsg_md import LocalNeighbourMDExecution  # noqa: E402
from andes_rl_kundur.evaluation.cd_matd3_canary import (  # noqa: E402
    TOTAL_INTERACTION_STEPS,
    build_contract as _build_contract,
    classify_canary,
    contract_sha256,
    evaluation_record_count,
    training_run_count,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile  # noqa: E402
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R418"
PLAN = ROOT / "memory/rounds/R418/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R418/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R418/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R418/formal_seal.json"
OUT = ROOT / "results/research_loop/r418_slew_state_bundle"
R410_OUT = ROOT / "results/research_loop/r410_message_repair"

R402_TRAINING_WORKER_RSS_BYTES = 944214016
CAPACITY_RUNGS = (1, 2, 4, 8)
CAPACITY_TASKS_PER_RUNG = 32


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
        raise RuntimeError("R418 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R418 must run through scripts/andes_scratch.py")
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
    launch = seal.get("launch", {})
    if int(launch.get("wsl_python_processes", 0)) != int(
        launch.get("host_process_budget", -1)
    ):
        raise RuntimeError("sealed launch budget is inconsistent")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R418 seal: {name}")
    return seal


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r418_slew_state_bundle.py",
        "learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "learner_tests": ROOT / "tests/test_cd_matd3_learner.py",
        "slew_learner_tests": ROOT / "tests/test_cd_matd3_slew_aware.py",
        "contract": ROOT / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        "contract_tests": ROOT / "tests/test_cd_matd3_canary.py",
        "estimators": ROOT
        / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
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
        "r410_formal_seal": ROOT / "memory/rounds/R410/formal_seal.json",
        "r410_formal_analysis": R410_OUT / "formal_analysis.json",
        "r410_endpoint_table": R410_OUT / "endpoint_table.json",
        "r410_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R410.md",
        "program": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
        "feedback_research": ROOT
        / "paper/yang_md_decoupling_marl/working"
        / "feedback_loop_deep_research_2026-08-17.md",
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


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R418" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and evaluation_record_count(contract) == 240
        and training_run_count(contract) == 9
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
        if "run_r418_slew_state_bundle.py" in command:
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
        action_slew_limit=float(contract["action_slew_limit"]),
    )
    if arm_id == "yang_scalar_td3":
        return SlewAwareYangScalarTD3(**kwargs)
    if arm_id in ("cd_matd3_no_message", "cd_matd3_message"):
        return SlewAwareCDMATD3(
            lagrange_initial=1.0,
            actor_neighbour_mask=(arm_id == "cd_matd3_no_message"),
            **kwargs,
        )
    raise ValueError(f"unknown learning arm: {arm_id}")


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


def _scalar_step_reward(rewards: Mapping[int, float]) -> float:
    return float(sum(float(rewards[i]) for i in range(4)))


def _save_agent_snapshot(agent: Any, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def train_arm_seed(
    arm_id: str,
    seed: int,
    restart_count: int = 0,
) -> str:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    slew_limit = float(contract["action_slew_limit"])
    arm_root = OUT / "train" / arm_id
    run_dir = arm_root / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    if restart_count:
        crash_dir = arm_root / f"seed{seed}-attempt{restart_count}-crash"
        if not crash_dir.is_dir():
            raise RuntimeError(
                "restart requires the preserved crash quarantine directory"
            )
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir = run_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    _write_new_json(
        run_dir / "started.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "restart_count": int(restart_count),
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
    device = "cpu"
    agent = _agent_for(arm_id, device)
    envs = {
        str(profile["profile_id"]): _build_env(profile)
        for profile in development
    }
    projector = PerVSGMDActionProjector(action_slew_limit=slew_limit)
    total_steps = int(contract["training_contract"]["total_interaction_steps"])
    steps_per_episode = int(contract["steps"])
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    episode_common_costs: list[float] = []
    episode_scalar_returns: list[float] = []
    invalid_reason: str | None = None
    lagrange_trace: list[float] = []
    slew_saturation_steps = 0
    slew_mismatch_sum = 0.0
    slew_mismatch_count = 0
    reward = contract["reward_contract"]["cd_matd3"]
    budget = float(reward["common_budget_per_episode"])
    multiplier_step = float(reward["lagrange_step"])
    multiplier_max = float(reward["lagrange_maximum"])
    episode_index = 0
    any_tds_failure = False
    while executed_steps < total_steps:
        scenario_id = schedule[episode_index % len(schedule)]
        episode_index += 1
        profile, scenario = scenarios[scenario_id]
        env = envs[str(profile["profile_id"])]
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        previous_executed = np.zeros((4, 2), dtype=np.float32)
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(contract["physical_nominal_frequency_hz"])
        )
        previous_frequency = initial_frequency.copy()
        episode_common = 0.0
        episode_scalar = 0.0
        for _step_index in range(steps_per_episode):
            joint = _joint_obs(observation)
            augmented = augment_joint_obs_np(joint, previous_executed)
            raw_action = agent.act(augmented, deterministic=False)
            if not np.all(np.isfinite(raw_action)):
                invalid_reason = "nonfinite actor output"
                break
            action = projector.project(raw_action)
            saturation = np.abs(action - previous_executed) >= (
                slew_limit - 1.0e-6
            )
            if np.any(saturation):
                slew_saturation_steps += 1
            slew_mismatch_sum += float(
                np.sum(np.abs(np.asarray(action, dtype=float) - raw_action))
            )
            slew_mismatch_count += 1
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, rewards, done, info = env.step(action_dict)
            executed_steps += 1
            frequencies = np.asarray(info["freq_hz_physical"], dtype=float)
            rocof = (frequencies - previous_frequency) / float(
                contract["dt_seconds"]
            )
            previous_frequency = frequencies.copy()
            tds_failed = bool(info["tds_failed"])
            next_joint = _joint_obs(observation)
            terminal = bool(done) or tds_failed
            if arm_id == "yang_scalar_td3":
                scalar_reward = _scalar_step_reward(rewards)
                episode_scalar += scalar_reward
                agent.store(
                    joint,
                    previous_executed.reshape(-1).astype(np.float32),
                    action.reshape(-1).astype(np.float32),
                    np.array([scalar_reward], dtype=np.float32),
                    next_joint,
                    terminal,
                )
            else:
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
                    previous_executed.reshape(-1).astype(np.float32),
                    action.reshape(-1).astype(np.float32),
                    np.array(
                        [-differential_cost, -common_cost], dtype=np.float32
                    ),
                    next_joint,
                    terminal,
                )
            previous_executed = action.astype(np.float32).copy()
            diagnostics = agent.update()
            if (
                diagnostics is not None
                and not np.isfinite(diagnostics["critic_loss"])
            ):
                invalid_reason = "nonfinite critic loss"
                break
            if tds_failed:
                tds_failed_episodes += 1
                any_tds_failure = True
                break
        if invalid_reason is not None:
            break
        episodes_attempted += 1
        if arm_id != "yang_scalar_td3":
            multiplier = agent.lagrange_step(
                episode_common,
                budget=budget,
                step=multiplier_step,
                maximum=multiplier_max,
            )
            lagrange_trace.append(multiplier)
            episode_common_costs.append(episode_common)
        else:
            episode_scalar_returns.append(episode_scalar)
        if episodes_attempted % 240 == 0:
            _save_agent_snapshot(
                agent, snapshots_dir / f"episode{episodes_attempted}.pt"
            )
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass
    convergence_valid = invalid_reason is None and executed_steps == total_steps
    missing = invalid_reason is not None
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
        "missing": bool(missing),
        "invalid_reason": invalid_reason,
        "restart_count": int(restart_count),
        "final_checkpoint_sha256": checkpoint_sha,
        "episode_common_costs": episode_common_costs[-20:],
        "episode_scalar_returns": episode_scalar_returns[-20:],
        "lagrange_trace": lagrange_trace[-20:],
        "any_tds_failure": bool(any_tds_failure),
        "slew_diagnostics": {
            "slew_saturation_steps": int(slew_saturation_steps),
            "total_executed_steps": int(executed_steps),
            "slew_saturation_rate": (
                slew_saturation_steps / executed_steps
                if executed_steps > 0
                else 0.0
            ),
            "execution_mismatch_mean": (
                slew_mismatch_sum / slew_mismatch_count
                if slew_mismatch_count > 0
                else 0.0
            ),
        },
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    return _write_new_json(run_dir / "manifest.json", manifest)


def _deterministic_controller() -> Any:
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    contract = build_contract()
    arm_id = str(contract["deterministic_arm_id"])
    return LocalNeighbourMDExecution(contracts[arm_id])


def _evaluate_arm_seed(arm_id: str, seed: int | None) -> None:
    contract = build_contract()
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    deterministic = seed is None
    checkpoint_sha = None
    agent = None
    if not deterministic:
        checkpoint_path = OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"missing final checkpoint: {checkpoint_path}")
        checkpoint_sha = _sha256_file(checkpoint_path)
        agent = _agent_for(arm_id, "cpu")
        agent.load(checkpoint_path)
    controller = _deterministic_controller() if deterministic else None
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    envs = {
        str(profile["profile_id"]): _build_env(profile) for profile in evaluation
    }
    for profile in evaluation:
        records = []
        env = envs[str(profile["profile_id"])]
        for scenario in profile["scenarios"]:
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            projector.reset()
            previous_executed = np.zeros((4, 2), dtype=np.float32)
            if controller is not None:
                controller.reset()
            initial_frequency = (
                np.asarray(env._get_vsg_omega(), dtype=float)
                * float(contract["physical_nominal_frequency_hz"])
            ).tolist()
            identity = {
                "n_agents": int(env.N_AGENTS),
                "vsg_idx": [str(value) for value in env.vsg_idx],
                "vsg_buses": [
                    int(env.ss.GENCLS.bus.v[position])
                    for position in env._vsg_pos
                ],
                "obs_dim": int(env.OBS_DIM),
                "baseline_m0": [float(value) for value in profile["baseline_m0"]],
                "baseline_d0": [float(value) for value in profile["baseline_d0"]],
                "control_nominal_frequency_hz": float(env.FN),
                "physical_nominal_frequency_hz": float(
                    env.andes_nominal_frequency_hz
                ),
            }
            rows = []
            failure = None
            for step_index in range(int(contract["steps"])):
                if controller is not None:
                    action = controller.act(
                        adapt_v4_observations_to_physical(observation)
                    )
                else:
                    joint = _joint_obs(observation)
                    augmented = augment_joint_obs_np(joint, previous_executed)
                    raw = agent.act(augmented, deterministic=True)
                    action = projector.project(raw)
                action_dict = {
                    actor: np.asarray(action[actor], dtype=np.float32)
                    for actor in range(4)
                }
                observation, _reward, done, info = env.step(action_dict)
                previous_executed = np.asarray(action, dtype=np.float32).copy()
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
                        "delta_M": np.asarray(
                            info["delta_M"], dtype=float
                        ).tolist(),
                        "delta_D": np.asarray(
                            info["delta_D"], dtype=float
                        ).tolist(),
                        "tds_failed": bool(info["tds_failed"]),
                        "done": bool(done),
                    }
                )
                if info["tds_failed"]:
                    failure = "TDS failed"
                    break
            record = {
                "profile_id": str(profile["profile_id"]),
                "split": str(profile["split"]),
                "scenario_id": str(scenario["scenario_id"]),
                "pair_kind": str(scenario["pair_kind"]),
                "sign": str(scenario["sign"]),
                "magnitude": float(scenario["magnitude"]),
                "delta_u": dict(scenario["delta_u"]),
                "arm_id": arm_id,
                "training_seed": seed,
                "checkpoint_sha256": checkpoint_sha,
                "identity": identity,
                "initial_freq_hz_physical": initial_frequency,
                "steps": rows,
                "completed_steps": len(rows),
                "completed": failure is None
                and len(rows) == int(contract["steps"]),
                "tds_failed": failure is not None
                or any(bool(row["tds_failed"]) for row in rows),
                "failure": failure,
                "reward_used_for_gate": False,
                "training_executed": True,
            }
            records.append(record)
        folder = OUT / "eval" / arm_id / (
            "deterministic" if deterministic else f"seed{seed}"
        )
        _write_new_json(
            folder / (str(profile["profile_id"]) + ".json"),
            {"records": records},
        )
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass


def evaluate_all() -> None:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    _evaluate_arm_seed(str(contract["deterministic_arm_id"]), None)
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            _evaluate_arm_seed(str(arm_id), int(seed))


def _eval_record_path(arm_id: str, seed: int | None, profile_id: str) -> Path:
    suffix = "deterministic" if seed is None else f"seed{seed}"
    return OUT / "eval" / arm_id / suffix / f"{profile_id}.json"


_ENDPOINTS = ("off_diagonal_response_energy", "disturbance_differential_energy")


def _arm_seed_aggregate(summaries: Sequence[Mapping[str, Any]], arm_id: str, seed: int | None) -> dict[str, float]:
    rows = [
        row
        for row in summaries
        if row["arm_id"] == arm_id
        and (row["training_seed"] is None) == (seed is None)
        and (seed is None or row["training_seed"] == seed)
    ]
    return {
        endpoint: float(sum(float(row[endpoint]) for row in rows))
        for endpoint in _ENDPOINTS
    }


def classify() -> str:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    manifests = []
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            path = OUT / "train" / arm_id / f"seed{seed}" / "manifest.json"
            manifests.append(_read_hashed_json(path))
    summaries = []
    evaluation = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            for profile in evaluation:
                path = _eval_record_path(
                    str(arm_id), int(seed), str(profile["profile_id"])
                )
                payload = _read_hashed_json(path)
                summary = summarise_profile(
                    payload["records"], contract=contract
                )
                summary["arm_id"] = str(arm_id)
                summary["training_seed"] = int(seed)
                summaries.append(summary)
    for profile in evaluation:
        path = _eval_record_path(
            str(contract["deterministic_arm_id"]),
            None,
            str(profile["profile_id"]),
        )
        payload = _read_hashed_json(path)
        summary = summarise_profile(payload["records"], contract=contract)
        summary["arm_id"] = str(contract["deterministic_arm_id"])
        summary["training_seed"] = None
        summaries.append(summary)
    outcome = classify_canary(manifests, summaries, contract=contract)

    # B1 decision table: endpoints, guards, message contrast, slew
    # diagnostics, versus the R410 records.
    arm_ids = [str(value) for value in contract["learning_arm_ids"]]
    seeds = [int(value) for value in contract["training_seeds"]]
    deterministic_arm = str(contract["deterministic_arm_id"])
    per_seed: dict[str, dict[str, float]] = {}
    for arm_id in arm_ids:
        for seed in seeds:
            per_seed[f"{arm_id}|{seed}"] = _arm_seed_aggregate(
                summaries, arm_id, seed
            )
    deterministic = _arm_seed_aggregate(summaries, deterministic_arm, None)
    medians = {
        arm_id: {
            endpoint: float(
                np.median([per_seed[f"{arm_id}|{seed}"][endpoint] for seed in seeds])
            )
            for endpoint in _ENDPOINTS
        }
        for arm_id in arm_ids
    }
    versus_deterministic = {
        arm_id: {
            endpoint: float(medians[arm_id][endpoint] / deterministic[endpoint])
            if deterministic[endpoint] > 0.0
            else float("inf")
            for endpoint in _ENDPOINTS
        }
        for arm_id in arm_ids
    }
    full_arm = arm_ids[2]
    improvements = {}
    for comparator in arm_ids[:2]:
        improvements[comparator] = {
            endpoint: float(
                (medians[comparator][endpoint] - medians[full_arm][endpoint])
                / medians[comparator][endpoint]
            )
            for endpoint in _ENDPOINTS
        }
    r410_table = _read_hashed_json(R410_OUT / "endpoint_table.json")
    r410_medians = {
        arm_id: {
            endpoint: float(
                r410_table["seed_medians"][arm_id][endpoint]
            )
            for endpoint in _ENDPOINTS
        }
        for arm_id in arm_ids
    }
    slew_diagnostics = {
        f"{manifest['arm_id']}|{manifest['training_seed']}": manifest[
            "slew_diagnostics"
        ]
        for manifest in manifests
    }
    anchor_verdict = "B1-CLASSIFIED"  # no drift anchor: single factor changes training
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": str(contract["manuscript_line"]),
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
        "seal_sha256": _sha256_file(SEAL),
        "classification": outcome,
        "b1_table": {
            "medians": medians,
            "median_endpoint_ratio_vs_deterministic": versus_deterministic,
            "message_improvement_vs_comparators": improvements,
            "r410_medians": r410_medians,
            "slew_diagnostics": slew_diagnostics,
            "anchor_verdict": anchor_verdict,
        },
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
        "checkpoint_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("*.pt"))
        ],
        "classification": outcome["classification"],
        "training_runs": training_run_count(contract),
        "evaluation_records": evaluation_record_count(contract),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


# ── capacity ladder (training-representative, R402 RSS anchor) ─────────

def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    contract = build_contract()
    profile = next(
        row
        for row in contract["profiles"]
        if row["split"] == "development"
    )
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    agent = _agent_for("cd_matd3_message", "cpu")
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    previous_executed = np.zeros((4, 2), dtype=np.float32)
    completed = 0
    failure: str | None = None
    tds_failed = False
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        for _step_index in range(int(contract["steps"])):
            joint = _joint_obs(observation)
            augmented = augment_joint_obs_np(joint, previous_executed)
            raw = agent.act(augmented, deterministic=True)
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _reward, _done, info = env.step(action_dict)
            previous_executed = np.asarray(action, dtype=np.float32).copy()
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
            raise FileExistsError(f"R418 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R418 formal output exists before capacity")
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
            "authorization": (
                "owner-authorized B1 slew-state bundle; R402/R410 contract "
                "unchanged except the registered slew-state factor"
            ),
            "contract_sha256": contract_sha256(build_contract()),
            "training_worker_rss_anchor": {
                "bytes": R402_TRAINING_WORKER_RSS_BYTES,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative live-training RSS floor",
            },
            "representative_task": {
                "arm_id": "cd_matd3_message",
                "profile": str(
                    next(
                        row
                        for row in build_contract()["profiles"]
                        if row["split"] == "development"
                    )["profile_id"]
                ),
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
            raise FileExistsError(f"R418 pre-attempt artifact exists: {candidate}")
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
        raise RuntimeError("R418 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    contract = build_contract()
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    rehearsal_dir = ROOT / "tmp" / "andes" / "r418_rehearsal_checkpoints"
    rehearsal_dir.mkdir(parents=True, exist_ok=True)
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)
        previous_executed = np.zeros((4, 2), dtype=np.float32)
        for arm_id in contract["learning_arm_ids"]:
            agent = _agent_for(str(arm_id), "cpu")
            projector = PerVSGMDActionProjector(
                action_slew_limit=float(contract["action_slew_limit"])
            )
            projector.reset()
            joint = _joint_obs(observation)
            augmented = augment_joint_obs_np(joint, previous_executed)
            raw = agent.act(augmented, deterministic=False)
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
            # R418-abort lesson: the rehearsal must exercise the replay
            # store path and the learner update seam, not only act/project.
            reward_dim = 1 if str(arm_id) == "yang_scalar_td3" else 2
            agent.store(
                joint,
                previous_executed.reshape(-1).astype(np.float32),
                action.reshape(-1).astype(np.float32),
                np.zeros(reward_dim, dtype=np.float32),
                next_joint,
                False,
            )
            diagnostics = agent.update()
            if diagnostics is not None and not np.isfinite(
                diagnostics["critic_loss"]
            ):
                raise RuntimeError("nonfinite rehearsal update")
            previous_executed = np.asarray(action, dtype=np.float32).copy()
            probe = rehearsal_dir / f"{arm_id}.pt"
            if probe.exists():
                probe.unlink()
            agent.save(probe)
            restored = _agent_for(str(arm_id), "cpu")
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
        raise RuntimeError("R418 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R418 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R418 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R418 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R418 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R418 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R418 formal artifact exists before sealing")
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    contract = build_contract()
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": contract_sha256(contract),
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "slew-state contract: every arm's actor observation gains "
                "the previous executed (post-slew) action (7 -> 9 slots, "
                "neighbour mask kept) and the target/online actor paths "
                "evaluate the same post-projection quantity the environment "
                "executes; arms, seeds, budgets, rewards, estimators, "
                "guards, and hyperparameters are the R402/R410 contract "
                "verbatim"
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "measure-capacity",
            "rehearse",
            "prepare",
            "train",
            "shard",
            "evaluate",
            "classify",
        ],
    )
    parser.add_argument("--arm", choices=list(build_contract()["learning_arm_ids"]))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--restart-count", type=int, default=0)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "measure-capacity":
        safe_emit(f"R418 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R418 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R418 formal seal: {prepare()}")
    elif args.command in ("train", "shard"):
        if args.command == "shard":
            if not args.args:
                raise SystemExit("shard requires <arm>|<seed>")
            parts = str(args.args[0]).split("|")
            if len(parts) != 2:
                raise SystemExit("shard id must be <arm>|<seed>")
            arm = parts[0]
            seed = int(parts[1])
        else:
            arm = args.arm
            seed = args.seed
        if arm is None or seed not in build_contract()["training_seeds"]:
            raise SystemExit("shard/train requires a registered arm and seed")
        safe_emit(
            "R418 training manifest: "
            + train_arm_seed(arm, seed, restart_count=args.restart_count)
        )
    elif args.command == "evaluate":
        evaluate_all()
        safe_emit("R418 evaluation complete")
    else:
        safe_emit(f"R418 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
