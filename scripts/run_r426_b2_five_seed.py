"""Sealed WSL runner for the R426 B2 seed-count extension.

Owner-authorized by the soft-spot program override deck item B2
(``paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md``
lines 200-208): extend the R410-repaired bundle to five seeds per arm.
Seeds 401/402/403 are reused via bit-repro (the stored R410 checkpoints at
``results/research_loop/r410_message_repair/``); seeds 404/405 are trained
fresh; the same budget and guards apply.  The round is reporting-only: it
emits a hashed five-seed median/spread table plus the frozen canary verdict
on the verbatim three-seed contract.

The contract stays VERBATIM R410 (``training_seeds`` [401, 402, 403]) so
the frozen canary tree runs untouched.  B2 trains only seven runs: one live
bit-identity gate (``cd_matd3_message`` seed 401, verified byte-identical
to the stored R410 checkpoint) plus the six fresh 404/405 runs across the
three learning arms.  A mismatch on the gate is recorded, never fatal.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py rehearse
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py prepare
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py train --arm <arm> --seed <seed>
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py shard <arm>|<seed>
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py evaluate
  python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r426_b2_five_seed/.
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

from andes_rl_kundur.agents.cd_matd3 import (
    CDMATD3,
    YangScalarTD3,
    compute_rocof,
    mask_neighbour_slots,
    physical_costs,
)
from andes_rl_kundur.control.per_vsg_md import (
    PerVSGMDActionProjector,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.control.per_vsg_md import LocalNeighbourMDExecution
from andes_rl_kundur.evaluation.cd_matd3_canary import (
    TOTAL_INTERACTION_STEPS,
    TOTAL_TRAINING_EPISODES,
    build_contract as _build_contract,
    classify_canary,
    contract_sha256,
    evaluation_record_count,
    training_run_count,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile

# Round-agnostic capacity helpers from the frozen R401 contract runner.
from run_r401_cd_matd3_canary_contract import (
    _capacity_jobs,
    _measure_rung,
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R426"
PLAN = ROOT / "memory/rounds/R426/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R426/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R426/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R426/formal_seal.json"
OUT = ROOT / "results/research_loop/r426_b2_five_seed"
R410_OUT = ROOT / "results/research_loop/r410_message_repair"

# R402 measured training-worker RSS anchor (capacity_evidence_v2.json,
# projected_training_worker_memory_bytes at one worker).  Conservative floor
# for the half-memory rule; the ladder may only raise it.
R402_TRAINING_WORKER_RSS_BYTES = 944214016

# ── owner-authorized concurrency (2026-08-17) ─────────────────────────
# R425 (guard-aligned constraints signfix) trains concurrently while this
# round runs.  Its sealed 16 workers + 1 driver are declared here as the
# reserved share of the whole-host budget; the ladder is measured under that
# load and the memory rule is total-memory accounting (R422 precedent).
OTHER_RESERVED_PROCESSES = 17  # R425: 16 training workers + 1 driver
OTHER_RESERVED_RSS_BYTES = 17 * 950 * 1024**2  # measured ~930 MiB/worker
OS_FLOOR_BYTES = 3 * 1024**3  # absolute OS/buffers floor, total-memory rule

# B2 seed model.  The frozen contract keeps training_seeds [401, 402, 403]
# verbatim; B2 adds two fresh seeds and one bit-identity gate run.
B2_FRESH_SEEDS = (404, 405)
B2_GATE_ARM = "cd_matd3_message"
B2_GATE_SEED = 401
B2_ALL_SEEDS = (401, 402, 403, 404, 405)

_ENDPOINTS = ("off_diagonal_response_energy", "disturbance_differential_energy")


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def build_contract() -> dict[str, Any]:
    return _build_contract()


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


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r426_b2_five_seed.py",
        "learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "learner_tests": ROOT / "tests/test_cd_matd3_learner.py",
        "contract": ROOT
        / "src/andes_rl_kundur/evaluation/cd_matd3_canary.py",
        "contract_tests": ROOT / "tests/test_cd_matd3_canary.py",
        "estimators": ROOT
        / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "controller_tests": ROOT / "tests/test_per_vsg_md.py",
        "slew_repair_tests": ROOT / "tests/test_per_vsg_md_slew_repair.py",
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
    """Authority and anchor artifacts this execution inherits from."""

    parents = {
        "owner_decision": ROOT
        / "paper/yang_md_decoupling_marl/working"
        / "route_owner_decision_message_repair_2026-08-16.md",
        "r402_capacity_evidence": ROOT
        / "memory/rounds/R402/capacity_evidence_v2.json",
        "r402_formal_analysis": ROOT
        / "results/research_loop/r402_cd_matd3_canary/formal_analysis.json",
        "r402_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R402.md",
        "r410_formal_analysis": R410_OUT / "formal_analysis.json",
        "r410_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R410.md",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in parents.items()
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R426 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R426 must run through scripts/andes_scratch.py")
    _pin_torch_threads()


def _pin_torch_threads() -> None:
    """Pin torch to one native thread per process (frozen launch contract).

    Called at command entry instead of import time so that importing this
    runner into a process that already loaded another frozen runner (test
    collection) never re-pins an already-set inter-op pool.  In WSL
    execution this runner is the only loaded runner, so the pin always
    applies before any physical work.
    """

    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def load_seal() -> dict[str, Any]:
    """Verify and return the R426 seal this execution is authorized by."""

    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract") != build_contract():
        raise RuntimeError("sealed contract drifted from the frozen module")
    if seal.get("contract_sha256") != contract_sha256(build_contract()):
        raise RuntimeError("sealed contract hash mismatch")
    launch = seal.get("launch", {})
    if int(launch.get("wsl_python_processes", 0)) + int(
        launch.get("other_reserved_processes", 0)
    ) != int(launch.get("host_process_budget", -1)):
        raise RuntimeError("sealed launch budget is inconsistent")
    learner_sha = (seal.get("sources") or {}).get("learner", {}).get("sha256")
    if learner_sha != _sha256_file(
        ROOT / "src/andes_rl_kundur/agents/cd_matd3.py"
    ):
        raise RuntimeError("learner source drifted from the R426 seal")
    return seal


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R426" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and evaluation_record_count(contract) == 240
        and training_run_count(contract) == 9
        and list(contract["training_seeds"]) == [401, 402, 403]
        and contract["training_contract"]["total_interaction_steps"]
        == TOTAL_INTERACTION_STEPS
        and contract["reward_contract"]["reward_used_for_gate"] is False,
        "output_absence": not OUT.exists(),
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


def _profile_by_id(contract: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    for profile in contract["profiles"]:
        if str(profile["profile_id"]) == profile_id:
            return profile
    raise ValueError(f"unknown profile: {profile_id}")


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
        14: {
            "p0": float(profile["steady_loads"]["PQ_Bus14"]),
            "q0": 0.0,
        },
        15: {
            "p0": float(profile["steady_loads"]["PQ_Bus15"]),
            "q0": 0.0,
        },
    }
    env.seed(int(build_contract()["bank_seed"]))
    env.STEPS_PER_EPISODE = int(build_contract()["steps"])
    return env


def _joint_obs(observation: Mapping[int, Any]) -> np.ndarray:
    rows = [np.asarray(observation[i], dtype=np.float32) for i in range(4)]
    return np.concatenate(rows).astype(np.float32)


def _agent_for(arm_id: str, device: str) -> Any:
    """R402 arm factory with the single-factor information-contract fix."""

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
    if arm_id == "yang_scalar_td3":
        return YangScalarTD3(**kwargs)
    if arm_id in ("cd_matd3_no_message", "cd_matd3_message"):
        return CDMATD3(
            lagrange_initial=1.0,
            actor_neighbour_mask=(arm_id == "cd_matd3_no_message"),
            **kwargs,
        )
    raise ValueError(f"unknown learning arm: {arm_id}")


def _mask_actor_obs(arm_id: str, joint: np.ndarray) -> np.ndarray:
    if arm_id == "cd_matd3_no_message":
        return mask_neighbour_slots(joint)
    return np.asarray(joint, dtype=np.float32)


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


def _checkpoint_path(arm_id: str, seed: int) -> Path:
    """Resolve the checkpoint source for one arm-seed run.

    Seeds 401/402/403 are the reused (stored) R410 checkpoints under
    ``R410_OUT`` (read-only); seeds 404/405 are the fresh B2 checkpoints
    under ``OUT``.
    """

    if seed in build_contract()["training_seeds"]:
        return R410_OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
    return OUT / "train" / arm_id / f"seed{seed}" / "final.pt"


def _stored_checkpoint_sha256(arm_id: str, seed: int) -> str:
    """Read the stored R410 checkpoint sha256 (sidecar first, then hash)."""

    stored_path = _checkpoint_path(arm_id, seed)
    sidecar = Path(f"{stored_path}.sha256")
    if sidecar.is_file():
        return sidecar.read_text(encoding="ascii").split()[0]
    return _sha256_file(stored_path)


def _b2_gate_matches(fresh_sha: str | None, stored_sha: str | None) -> bool:
    """Bit-identity verdict: both hashes present and byte-equal."""

    return bool(
        fresh_sha is not None
        and stored_sha is not None
        and fresh_sha == stored_sha
    )


def _parse_shard_id(shard_id: str) -> tuple[str, int]:
    """Parse a ``<arm>|<seed>`` shard id (soft_spot_shard_driver SHARD_COMMAND)."""

    parts = str(shard_id).split("|")
    if len(parts) != 2 or not parts[0]:
        raise ValueError(f"shard id must be <arm>|<seed>: {shard_id!r}")
    return parts[0], int(parts[1])


def _seed_arm_valid(arm_id: str, seed: int) -> bool:
    """B2 train admission: seed 401 only on the gate arm; 404/405 any arm."""

    if seed in B2_FRESH_SEEDS:
        return True
    if seed == B2_GATE_SEED:
        return arm_id == B2_GATE_ARM
    return False


def train_arm_seed(
    arm_id: str,
    seed: int,
    restart_count: int = 0,
) -> str:
    """Train one registered arm-seed run to the frozen interaction budget."""

    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
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
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    total_steps = int(contract["training_contract"]["total_interaction_steps"])
    steps_per_episode = int(contract["steps"])
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    episode_common_costs: list[float] = []
    episode_scalar_returns: list[float] = []
    invalid_reason: str | None = None
    lagrange_trace: list[float] = []
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
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(contract["physical_nominal_frequency_hz"])
        )
        previous_frequency = initial_frequency.copy()
        episode_common = 0.0
        episode_scalar = 0.0
        for _step_index in range(steps_per_episode):
            joint = _joint_obs(observation)
            actor_joint = _mask_actor_obs(arm_id, joint)
            raw_action = agent.act(actor_joint, deterministic=False)
            if not np.all(np.isfinite(raw_action)):
                invalid_reason = "nonfinite actor output"
                break
            action = projector.project(raw_action)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, rewards, done, info = env.step(action_dict)
            executed_steps += 1
            frequencies = np.asarray(
                info["freq_hz_physical"], dtype=float
            )
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
                    action.reshape(-1),
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
                    action.reshape(-1),
                    np.array(
                        [-differential_cost, -common_cost], dtype=np.float32
                    ),
                    next_joint,
                    terminal,
                )
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
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    if arm_id == B2_GATE_ARM and seed == B2_GATE_SEED:
        # B2 bit-identity gate: compare the fresh final checkpoint against
        # the stored R410 checkpoint.  Record the verdict only -- a mismatch
        # must not invalidate the run (the parent reviews the drift).
        stored_sha = _stored_checkpoint_sha256(B2_GATE_ARM, B2_GATE_SEED)
        manifest["b2_gate_matches_r410"] = _b2_gate_matches(
            checkpoint_sha, stored_sha
        )
        manifest["b2_gate_stored_sha256"] = stored_sha
        manifest["b2_gate_fresh_sha256"] = checkpoint_sha
    return _write_new_json(run_dir / "manifest.json", manifest)


def _deterministic_controller() -> Any:
    contracts = {row.name: row for row in local_neighbour_md_candidates()}
    contract = build_contract()
    arm_id = str(contract["deterministic_arm_id"])
    return LocalNeighbourMDExecution(contracts[arm_id])


def _evaluate_arm_seed(
    arm_id: str,
    seed: int | None,
) -> None:
    """Run the 24 registered evaluation records for one arm-seed."""

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
        checkpoint_path = _checkpoint_path(arm_id, seed)
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
                    actor_joint = _mask_actor_obs(arm_id, joint)
                    raw = agent.act(actor_joint, deterministic=True)
                    action = projector.project(raw)
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
    """Evaluate the deterministic reference and all fifteen arm-seed policies."""

    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    _evaluate_arm_seed(str(contract["deterministic_arm_id"]), None)
    for arm_id in contract["learning_arm_ids"]:
        for seed in B2_ALL_SEEDS:
            _evaluate_arm_seed(str(arm_id), int(seed))


def _eval_record_path(arm_id: str, seed: int | None, profile_id: str) -> Path:
    """Build the evaluation record path for one arm-seed-profile block."""

    suffix = "deterministic" if seed is None else f"seed{seed}"
    return OUT / "eval" / arm_id / suffix / f"{profile_id}.json"


def _arm_seed_aggregate(
    summaries: Sequence[Mapping[str, Any]], arm_id: str, seed: int | None
) -> dict[str, float]:
    """Sum an arm-seed's endpoint over every evaluation profile."""

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


def _five_seed_aggregate(
    summaries: Sequence[Mapping[str, Any]], arm_id: str
) -> dict[str, dict[str, float]]:
    """Per-endpoint median/min/max over the five per-seed sums of one arm."""

    per_seed = {
        seed: _arm_seed_aggregate(summaries, arm_id, seed)
        for seed in B2_ALL_SEEDS
    }
    return {
        endpoint: {
            "median": float(
                np.median([per_seed[seed][endpoint] for seed in B2_ALL_SEEDS])
            ),
            "min": float(
                np.min([per_seed[seed][endpoint] for seed in B2_ALL_SEEDS])
            ),
            "max": float(
                np.max([per_seed[seed][endpoint] for seed in B2_ALL_SEEDS])
            ),
        }
        for endpoint in _ENDPOINTS
    }


def classify() -> str:
    """Classify the frozen three-seed bank and build the B2 reporting table."""

    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    # Frozen canary tree: the verbatim three-seed contract over the reused
    # (stored) R410 runs.  Manifests are read from the stored R410 tree;
    # evaluation records were written to OUT/eval from the stored checkpoints.
    manifests = []
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            path = R410_OUT / "train" / str(arm_id) / f"seed{seed}" / "manifest.json"
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

    # B2 five-seed reporting table: stored 401/402/403 + fresh 404/405.
    five_seed_summaries = []
    for arm_id in contract["learning_arm_ids"]:
        for seed in B2_ALL_SEEDS:
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
                five_seed_summaries.append(summary)
    b2_five_seed_table = {
        str(arm_id): _five_seed_aggregate(five_seed_summaries, str(arm_id))
        for arm_id in contract["learning_arm_ids"]
    }

    # B2 bit-identity gate verdict, read from the fresh gate manifest.
    gate_manifest = _read_hashed_json(
        OUT / "train" / B2_GATE_ARM / f"seed{B2_GATE_SEED}" / "manifest.json"
    )
    b2_gate = {
        "arm": B2_GATE_ARM,
        "seed": B2_GATE_SEED,
        "matches_r410": bool(gate_manifest.get("b2_gate_matches_r410", False)),
        "stored_sha256": gate_manifest.get("b2_gate_stored_sha256"),
        "fresh_sha256": gate_manifest.get("b2_gate_fresh_sha256"),
    }

    analysis_path = OUT / "formal_analysis.json"
    digest = _write_new_json(
        analysis_path,
        {
            "schema_version": 1,
            "manuscript_line": str(contract["manuscript_line"]),
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(contract),
            "seal_sha256": _sha256_file(SEAL),
            **outcome,
            # the frozen classifier module stamps its own ROUND_ID inside
            # ``outcome``; the B2 round id must win.
            "round": ROUND_ID,
            "b2_gate": b2_gate,
            "b2_five_seed_table": b2_five_seed_table,
        },
    )
    manifest_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "analysis_sha256": digest,
        "input_artifacts": [
            {
                "path": _relative(path),
                "sha256": _sha256_file(path),
            }
            for path in sorted(OUT.rglob("*.json"))
            if path.name not in {"formal_analysis.json", "formal_manifest.json"}
        ],
        "checkpoint_artifacts": [
            {
                "path": _relative(path),
                "sha256": _sha256_file(path),
            }
            for path in sorted(OUT.rglob("*.pt"))
        ],
        "classification": outcome["classification"],
        "training_runs": training_run_count(contract),
        "evaluation_records": evaluation_record_count(contract),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


def rehearse() -> str:
    """Exercise the formal pre-attempt path without formal artifacts.

    Pre-seal rehearsal: authority checks, one real one-step rollout per arm
    through the fixed learner (mask exercised on every arm), save/load
    roundtrip, the two B2 seams (checkpoint-source resolution and the gate
    comparison helper), and a full source/runtime snapshot.
    """

    _assert_wsl_scratch()
    collisions = [
        candidate for candidate in (REHEARSAL, SEAL) if candidate.exists()
    ]
    if collisions:
        raise FileExistsError(f"R426 pre-attempt artifact exists: {collisions}")
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
        raise RuntimeError("R426 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    # B2 seam (a): the checkpoint-source helper resolves stored (401) vs
    # fresh (404) -- the stored path must exist with a verifying sidecar,
    # and the fresh path must not exist pre-attempt.
    stored_checkpoint = _checkpoint_path(B2_GATE_ARM, B2_GATE_SEED)
    if not stored_checkpoint.is_file():
        raise RuntimeError("B2 stored gate checkpoint missing: " + str(stored_checkpoint))
    stored_sidecar = Path(f"{stored_checkpoint}.sha256")
    if not stored_sidecar.is_file():
        raise RuntimeError("B2 stored gate checkpoint sidecar missing")
    if _sha256_file(stored_checkpoint) != stored_sidecar.read_text(
        encoding="ascii"
    ).split()[0]:
        raise RuntimeError("B2 stored gate checkpoint sidecar mismatch")
    fresh_checkpoint = _checkpoint_path(B2_GATE_ARM, B2_FRESH_SEEDS[0])
    if fresh_checkpoint.exists():
        raise RuntimeError("B2 fresh checkpoint exists pre-attempt: " + str(fresh_checkpoint))
    contract = build_contract()
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(contract["physical_nominal_frequency_hz"])
        )
        for arm_id in contract["learning_arm_ids"]:
            agent = _agent_for(str(arm_id), "cpu")
            projector = PerVSGMDActionProjector(
                action_slew_limit=float(contract["action_slew_limit"])
            )
            projector.reset()
            joint = _joint_obs(observation)
            actor_joint = _mask_actor_obs(str(arm_id), joint)
            raw = agent.act(actor_joint, deterministic=False)
            if not np.all(np.isfinite(raw)):
                raise RuntimeError("nonfinite rehearsal actor output")
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            next_observation, rewards, done, info = env.step(action_dict)
            next_joint = _joint_obs(next_observation)
            frequencies = np.asarray(info["freq_hz_physical"], dtype=float)
            rocof = (frequencies - initial_frequency) / float(
                contract["dt_seconds"]
            )
            if arm_id == "yang_scalar_td3":
                agent.store(
                    joint,
                    action.reshape(-1),
                    np.array([_scalar_step_reward(rewards)], dtype=np.float32),
                    next_joint,
                    bool(done),
                )
            else:
                differential, common = physical_costs(
                    frequencies[None, :],
                    rocof[None, :],
                    np.asarray(info["P_es"], dtype=float)[None, :],
                    contract=contract,
                )
                agent.store(
                    joint,
                    action.reshape(-1),
                    np.array(
                        [-float(differential[0]), -float(common[0])],
                        dtype=np.float32,
                    ),
                    next_joint,
                    bool(done),
                )
            rehearsal_dir = ROOT / "tmp" / "andes" / "r426_rehearsal_checkpoints"
            rehearsal_dir.mkdir(parents=True, exist_ok=True)
            probe = rehearsal_dir / f"{arm_id}.pt"
            if probe.exists():
                probe.unlink()
            agent.save(probe)
            restored = _agent_for(str(arm_id), "cpu")
            restored.load(probe)
            # B2 seam (b): the gate comparison helper -- save, reload, then
            # save again under the SAME basename (torch.save embeds the
            # filename in the zip member name, so the comparison is only
            # valid for equal basenames) and assert sha equality plus the
            # matches=True no-op sanity.
            saved_sha = _sha256_file(probe)
            reloaded_dir = rehearsal_dir / "reloaded"
            reloaded_dir.mkdir(parents=True, exist_ok=True)
            reloaded_probe = reloaded_dir / probe.name
            if reloaded_probe.exists():
                reloaded_probe.unlink()
            restored.save(reloaded_probe)
            reloaded_sha = _sha256_file(reloaded_probe)
            if saved_sha != reloaded_sha:
                raise RuntimeError("B2 gate comparison: save/reload sha mismatch")
            if not _b2_gate_matches(saved_sha, reloaded_sha):
                raise RuntimeError("B2 gate comparison helper failed on identical bytes")
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
            "b2_seams": {
                "checkpoint_source_resolved": True,
                "gate_comparison_sanity": True,
            },
            "physical_trajectory_executed": True,
            "formal_artifacts_created": False,
            "training_executed": False,
        },
    )


def _select_rung(
    rungs: Sequence[Mapping[str, Any]],
    *,
    physical_memory_bytes: int,
) -> dict[str, Any]:
    """Highest safe rung under owner-authorized concurrency selection.

    While R425 is active the ladder throughput is measured under shared load,
    so the 5% marginal chain is waived and the largest all-valid memory-safe
    rung is accepted with reason ``owner_concurrent_max_rung``; the memory
    rule is total-memory accounting (projected own workers + declared
    reserved RSS + an absolute OS floor must fit WSL MemTotal).
    """

    selected: Mapping[str, Any] | None = None
    selected_throughput: float | None = None
    decisions: list[dict[str, Any]] = []
    memory_ceiling = max(
        0, int(physical_memory_bytes) - OTHER_RESERVED_RSS_BYTES - OS_FLOOR_BYTES
    )
    for rung in rungs:
        workers = int(rung["workers"])
        throughput = float(rung["throughput_jobs_per_second"])
        effective_rss = max(
            int(rung["maximum_worker_rss_bytes"]), R402_TRAINING_WORKER_RSS_BYTES
        )
        projected = effective_rss * workers
        memory_safe = projected <= memory_ceiling
        valid = bool(rung["all_records_valid"])
        if not valid:
            accepted, reason = False, "invalid_representative_records"
        elif not memory_safe:
            accepted, reason = False, "total_memory_guard"
        elif OTHER_RESERVED_PROCESSES > 0:
            accepted, reason = True, "owner_concurrent_max_rung"
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
                "memory_ceiling_bytes": memory_ceiling,
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
        "host_process_budget": workers + 1 + OTHER_RESERVED_PROCESSES,
        "wsl_python_processes": workers + 1,
        "other_reserved_processes": OTHER_RESERVED_PROCESSES,
        "selected_throughput_jobs_per_second": float(selected_throughput),
        "rung_decisions": decisions,
    }


def _other_processes() -> list[dict[str, Any]]:
    """Other research processes, excluding our own and the declared R425 share.

    The shared R401 helper flags our own bash/python launcher because its
    command line contains this runner's name; this local filter removes our
    own process tree and any process running this runner before reporting.
    R425's live processes are the declared ``OTHER_RESERVED_PROCESSES``
    share, so they are excluded from the unexpected-process check.
    """

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
        if "run_r426_b2_five_seed.py" in command:
            continue
        if "run_r425_guard_constraints_signfix.py" in command:
            # owner-authorized concurrent round: R425 is the declared
            # OTHER_RESERVED_PROCESSES share, not an unexpected process
            continue
        matches.append(entry)
    return matches


def measure_capacity() -> str:
    """Pre-seal capacity ladder (rungs 1/2/4/8) with the R402 RSS anchor."""

    _assert_wsl_scratch()
    collisions = [
        candidate for candidate in (CAPACITY, SEAL) if candidate.exists()
    ]
    if collisions:
        raise FileExistsError(f"R426 capacity artifact exists: {collisions}")
    if REHEARSAL.exists():
        raise FileExistsError("run measure-capacity before rehearse")
    if OUT.exists():
        raise FileExistsError("R426 formal output exists before capacity")
    other = _other_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    logical, physical_memory, wsl_available = _memory_resources()
    jobs = _capacity_jobs(build_contract())
    rungs = [_measure_rung(jobs, workers) for workers in (1, 2, 4, 8)]
    selection = _select_rung(
        rungs,
        physical_memory_bytes=physical_memory,
    )
    throughput = selection.get("selected_throughput_jobs_per_second")
    steps_per_second = (
        30.0 * float(throughput) if throughput is not None else None
    )
    canary_step_units = (
        training_run_count(build_contract()) * TOTAL_INTERACTION_STEPS
        + evaluation_record_count(build_contract()) * 30
    )
    projected = (
        float(canary_step_units) / float(steps_per_second)
        if steps_per_second is not None
        else None
    )
    return _write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_capacity_ladder_rungs_1_2_4_8",
            "authorization": (
                "owner-authorized B2 five-seed extension; ladder measured "
                "under the concurrent R425 load (declared reserved), "
                "total-memory accounting per the 2026-08-17 owner grant"
            ),
            "contract_sha256": contract_sha256(build_contract()),
            "training_worker_rss_anchor": {
                "bytes": R402_TRAINING_WORKER_RSS_BYTES,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative live-training RSS floor",
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
                "simulator_workers": selection["selected_workers"],
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": OTHER_RESERVED_PROCESSES,
            "other_reserved_rss_bytes": OTHER_RESERVED_RSS_BYTES,
            "os_floor_bytes": OS_FLOOR_BYTES,
            "other_processes": other,
            "canary_step_units": canary_step_units,
            "projected_canary_wall_seconds": projected,
            "projection_scope": (
                "training-step cost is anchored by the measured 30-step "
                "rollout; learner-update overhead is not included"
            ),
            "memory_rule": (
                "owner-authorized total-memory accounting (2026-08-17): "
                "projected own training-worker RSS + declared reserved RSS "
                "+ a fixed 3 GiB OS floor must not exceed WSL MemTotal"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": _source_manifest(),
            "installed_runtime": _installed_runtime(),
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def _plan_process_budget_matches(capacity: Mapping[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    expected = int(capacity["wsl_python_processes"])
    host = expected + OTHER_RESERVED_PROCESSES
    return bool(
        f"host_process_budget: {host}" in plan_text
        and f"wsl_python_processes: {expected}" in plan_text
        and "native_threads_per_process: 1" in plan_text
        and f"other_reserved_processes: {OTHER_RESERVED_PROCESSES}" in plan_text
    )


def prepare() -> str:
    """Seal the R426 contract, sources, capacity, runtime, and budget."""

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
        raise RuntimeError("R426 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R426 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R426 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R426 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R426 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R426 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R426 formal artifact exists before sealing")
    contract = build_contract()
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
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
            "decision_sha256": _sha256_file(
                ROOT
                / "paper/yang_md_decoupling_marl/working"
                / "route_owner_decision_message_repair_2026-08-16.md"
            ),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "seed-count extension: the R410-repaired bundle is sampled "
                "on five seeds per arm; seeds 401/402/403 are reused via "
                "bit-repro (stored R410 checkpoints), seeds 404/405 are "
                "trained fresh, with the same budget and guards; the "
                "contract and every learner/estimator/guard path are the "
                "R410 assets verbatim"
            ),
            "launch": {
                "host_process_budget": process_count + OTHER_RESERVED_PROCESSES,
                "wsl_python_processes": process_count,
                "worker_processes": workers,
                "native_threads_per_process": 1,
                "other_reserved_processes": OTHER_RESERVED_PROCESSES,
            },
            "canary_work_units": {
                "training_runs": training_run_count(),
                "evaluation_records": evaluation_record_count(),
                "total_interaction_steps_per_run": TOTAL_INTERACTION_STEPS,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": True,
            "successor_authorized": (
                "train the bit-identity gate (cd_matd3_message seed 401) "
                "plus the six fresh 404/405 runs across the three learning "
                "arms; reuse the stored R410 checkpoints for 401/402/403"
            ),
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
        safe_emit(f"R426 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R426 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R426 formal seal: {prepare()}")
    elif args.command in ("train", "shard"):
        if args.command == "shard":
            if not args.args:
                raise SystemExit("shard requires <arm>|<seed>")
            arm, seed = _parse_shard_id(args.args[0])
        else:
            arm = args.arm
            seed = args.seed
        if arm is None or seed is None or not _seed_arm_valid(arm, seed):
            raise SystemExit(
                "train/shard requires a valid B2 arm-seed "
                "(seed 401 gate-only, seeds 404/405 any arm)"
            )
        safe_emit(
            "R426 training manifest: "
            + train_arm_seed(
                arm, seed, restart_count=args.restart_count
            ),
        )
    elif args.command == "evaluate":
        evaluate_all()
        safe_emit("R426 evaluation complete")
    else:
        safe_emit(f"R426 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
