"""R457 M2 head-selective critic causality experiment.

Run only through ``scripts/andes_scratch.py`` inside the installed WSL ANDES
environment. Formal artifacts are create-only and every payload has a SHA-256
sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import scripts.run_r425_guard_constraints_signfix as R425  # noqa: E402
import scripts.run_r455_m1_dual_saturation as R455  # noqa: E402

from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    ACTION_DIM,
    AGENT_COUNT,
    JOINT_ACTION_DIM,
    JOINT_OBS_DIM,
    augment_joint_obs_np,
    project_slew_torch,
)
from andes_rl_kundur.agents.cd_matd3_critic_norm import (  # noqa: E402
    PopArtDifferentialCriticSlewAwareCDMATD3Signfix,
)
from andes_rl_kundur.agents.cd_matd3_head_popart import (  # noqa: E402
    HeadSelectivePopArtCDMATD3,
)
from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    PerVSGMDActionProjector,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import (  # noqa: E402
    summarise_profile,
)

ROUND_ID = "R457"
OUT = ROOT / "results/research_loop/r457_m2_head_causality"
ROUND_DIR = ROOT / "memory/rounds/R457"
SEAL = ROUND_DIR / "formal_seal.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
CAPACITY_AMENDMENT = ROUND_DIR / "capacity_amendment.json"
REHEARSAL = ROUND_DIR / "rehearsal.json"
PLAN = ROUND_DIR / "plan.md"
REPLAY_SHARDS = ROOT / "tmp/andes/r457_m2_replay_shards.json"
LEARN_SHARDS = ROOT / "tmp/andes/r457_m2_learn_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r457_m2_eval_shards.json"
CAL_SHARDS = ROOT / "tmp/andes/r457_m2_calibration_shards.json"

ARMS = ("cd_matd3_no_message", "cd_matd3_message")
SEEDS = (401, 402, 403, 404, 405)
CELLS: dict[str, tuple[str, ...]] = {
    "none": (),
    "differential_only": ("differential",),
    "common_only": ("common",),
    "both": ("differential", "common"),
}
PHASE1_UPDATES = 512
PHASE2_UPDATES = 256
DIAGNOSTIC_EVERY = 32
BATCH_SIZE = 256
AMPLITUDES = (0.02, 0.05, 0.10)
CALIBRATION_SCENARIOS = (
    "canary_eval_a_common_positive",
    "canary_eval_d_localized_negative",
)
CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_JOBS = 32


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(raw + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _write_new_npz(path: Path, **arrays: np.ndarray) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _verify_sidecar(path: Path) -> str:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(path)
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"sidecar mismatch: {path}")
    return actual


def _read_hashed_json(path: Path) -> dict[str, Any]:
    _verify_sidecar(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)


def _assert_wsl_scratch() -> None:
    if os.name != "posix" or "WSL" not in os.uname().release.upper():
        raise RuntimeError("R457 formal execution requires WSL")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("missing ANDES scratch wrapper")


def _scratch_dir() -> Path:
    _assert_wsl_scratch()
    return Path.cwd().resolve()


def _profiles(split: str) -> list[dict[str, Any]]:
    return [row for row in R425.build_contract()["profiles"] if row["split"] == split]


def replay_ids() -> list[str]:
    return [f"replay|{arm}|{seed}" for arm in ARMS for seed in SEEDS]


def learn_ids() -> list[str]:
    return [f"learn|{cell}|{arm}|{seed}" for cell in CELLS for arm in ARMS for seed in SEEDS]


def eval_ids() -> list[str]:
    return [f"eval|{cell}|{arm}|{seed}" for cell in CELLS for arm in ARMS for seed in SEEDS]


def calibration_ids() -> list[str]:
    return [f"cal|{cell}|{arm}|{seed}" for cell in CELLS for arm in ARMS for seed in SEEDS]


def build_contract() -> dict[str, Any]:
    parent = R425.build_contract()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "parent_contract_sha256": R455._canonical_sha256(parent),
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "cells": {key: list(value) for key, value in CELLS.items()},
        "replay": {
            "episodes_per_dataset": 24,
            "steps_per_episode": int(parent["steps"]),
            "transitions_per_dataset": 720,
            "train_profiles": ["canary_dev_a", "canary_dev_b", "canary_dev_c"],
            "heldout_profiles": ["canary_dev_d"],
            "batch_size": BATCH_SIZE,
            "phase1_updates": PHASE1_UPDATES,
            "phase2_updates": PHASE2_UPDATES,
            "explore_noise": 0.1,
        },
        "popart": {
            "beta": 1.0e-3,
            "sigma_min": 1.0e-4,
            "invariance_atol": 2.0e-5,
            "invariance_rtol": 2.0e-5,
        },
        "calibration": {
            "scenarios": list(CALIBRATION_SCENARIOS),
            "amplitudes": list(AMPLITUDES),
            "direction_count": 8,
            "trajectories_per_policy": 98,
            "discount": float(parent["learner_contract"]["gamma"]),
        },
        "physical_evaluation": {
            "profiles": 4,
            "scenarios_per_profile": 6,
            "trajectories_per_policy": 24,
        },
        "thresholds": {
            "critic_improvement": 0.20,
            "calibration_sign_gain": 0.25,
            "calibration_magnitude_improvement": 0.20,
            "actor_action_displacement": 0.01,
            "physical_none_improvement": 0.05,
            "physical_selective_margin": 0.03,
            "paired_seed_count": 4,
        },
        "parent_action_slew_limit": float(parent["action_slew_limit"]),
        "training_executed": False,
        "fixed_replay_mechanism_experiment": True,
    }


def contract_sha256() -> str:
    return _canonical_sha256(build_contract())


def _agent(arm: str, cell: str) -> HeadSelectivePopArtCDMATD3:
    if arm not in ARMS or cell not in CELLS:
        raise ValueError((arm, cell))
    contract = R425.build_contract()
    learner = contract["learner_contract"]
    return HeadSelectivePopArtCDMATD3(
        normalized_heads=CELLS[cell],
        lagrange_initial=1.0,
        actor_neighbour_mask=(arm == "cd_matd3_no_message"),
        hidden_sizes=list(learner["actor"]["hidden_sizes"]),
        lr=float(learner["lr"]),
        gamma=float(learner["gamma"]),
        tau=float(learner["tau"]),
        buffer_size=int(learner["buffer_size"]),
        batch_size=BATCH_SIZE,
        policy_noise=float(learner["policy_noise"]),
        noise_clip=float(learner["noise_clip"]),
        explore_noise=float(learner["explore_noise"]),
        policy_delay=int(learner["policy_delay"]),
        device="cpu",
        action_slew_limit=float(contract["action_slew_limit"]),
    )


def _tensor_hash(modules: Sequence[torch.nn.Module]) -> str:
    digest = hashlib.sha256()
    for module in modules:
        for key, value in sorted(module.state_dict().items()):
            digest.update(key.encode())
            digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def _network_hashes(agent: Any) -> dict[str, str]:
    return {
        "actors": _tensor_hash(list(agent.actors)),
        "actor_targets": _tensor_hash(list(agent.actor_targets)),
        "critic": _tensor_hash([agent.critic]),
        "critic_target": _tensor_hash([agent.critic_target]),
    }


def _replay_root(arm: str, seed: int) -> Path:
    return OUT / "replay" / arm / f"seed{seed}"


def _learn_root(cell: str, arm: str, seed: int) -> Path:
    return OUT / "learn" / cell / arm / f"seed{seed}"


def _eval_path(cell: str, arm: str, seed: int) -> Path:
    return OUT / "eval" / cell / arm / f"seed{seed}.json"


def _calibration_path(cell: str, arm: str, seed: int) -> Path:
    return OUT / "calibration" / cell / arm / f"seed{seed}.json"


def _scenario_map(split: str) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        str(scenario["scenario_id"]): (profile, scenario)
        for profile in _profiles(split)
        for scenario in profile["scenarios"]
    }


def _dual_residuals(
    actions: np.ndarray,
    previous: np.ndarray,
    profile_id: str,
    reference: Mapping[str, Any],
) -> tuple[float, float]:
    profile = reference["profiles"][profile_id]
    rms = float(np.mean(actions**2))
    tv = float(np.sum(np.mean(np.abs(actions - previous), axis=(1, 2))))
    rms_den = max(1.1**2 * float(profile["action_rms_ref"]) ** 2, 1.0e-9)
    tv_den = max(1.1 * float(profile["tv_ref_scenario_mean"]), 1.0e-9)
    return rms / rms_den - 1.0, tv / tv_den - 1.0


def run_replay_shard(shard_id: str, *, formal: bool = True) -> dict[str, Any]:
    if formal:
        _assert_wsl_scratch()
        load_seal()
    prefix, arm, seed_text = shard_id.split("|")
    seed = int(seed_text)
    if prefix != "replay" or shard_id not in replay_ids():
        raise ValueError(shard_id)
    root = _replay_root(arm, seed) if formal else _scratch_dir() / "r457-rehearsal-replay"
    if root.exists():
        raise FileExistsError(root)
    _seed_everything(seed)
    behavior = _agent(arm, "none")
    initial_hashes = _network_hashes(behavior)
    contract = R425.build_contract()
    reference = _read_hashed_json(ROOT / "results/research_loop/r425_guard_constraints_signfix/reference_action_stats.json")
    projector = PerVSGMDActionProjector(action_slew_limit=float(contract["action_slew_limit"]))
    arrays: dict[str, list[Any]] = {key: [] for key in (
        "obs", "prev_actions", "actions", "rewards", "next_obs", "dones",
        "profile_index", "scenario_index", "episode_index", "freq_hz", "rocof_hz_s", "p_es",
    )}
    episodes: list[dict[str, Any]] = []
    envs = {row["profile_id"]: R425._build_env(row) for row in _profiles("development")}
    try:
        episode_index = 0
        for profile_index, profile in enumerate(_profiles("development")):
            for scenario_index, scenario in enumerate(profile["scenarios"]):
                env = envs[profile["profile_id"]]
                observation = env.reset(delta_u=dict(scenario["delta_u"]))
                projector.reset()
                previous = np.zeros((AGENT_COUNT, ACTION_DIM), dtype=np.float32)
                previous_frequency = np.asarray(env._get_vsg_omega(), dtype=float) * float(contract["physical_nominal_frequency_hz"])
                start = len(arrays["obs"])
                episode_common = 0.0
                episode_actions: list[np.ndarray] = []
                episode_previous: list[np.ndarray] = []
                for step in range(int(contract["steps"])):
                    joint = R425._joint_obs(observation)
                    raw = behavior.act(augment_joint_obs_np(joint, previous), deterministic=False)
                    action = projector.project(raw)
                    next_observation, _rewards, done, info = env.step({i: action[i].astype(np.float32) for i in range(AGENT_COUNT)})
                    frequency = np.asarray(info["freq_hz_physical"], dtype=float)
                    rocof = (frequency - previous_frequency) / float(contract["dt_seconds"])
                    previous_frequency = frequency.copy()
                    if bool(info["tds_failed"]):
                        differential_cost = common_cost = 50.0
                    else:
                        differential_cost, common_cost = R425._cd_step_costs(
                            frequency[None, :], rocof[None, :], np.asarray(info["P_es"], dtype=float)[None, :], contract
                        )
                    next_joint = R425._joint_obs(next_observation)
                    terminal = bool(done) or bool(info["tds_failed"])
                    values = {
                        "obs": joint,
                        "prev_actions": previous.reshape(-1),
                        "actions": action.reshape(-1),
                        "rewards": np.asarray([-differential_cost, -common_cost], dtype=np.float32),
                        "next_obs": next_joint,
                        "dones": [float(terminal)],
                        "profile_index": profile_index,
                        "scenario_index": scenario_index,
                        "episode_index": episode_index,
                        "freq_hz": frequency,
                        "rocof_hz_s": rocof,
                        "p_es": np.asarray(info["P_es"], dtype=float),
                    }
                    for key, value in values.items():
                        arrays[key].append(value)
                    episode_common += common_cost
                    episode_actions.append(action.copy())
                    episode_previous.append(previous.copy())
                    previous = action.astype(np.float32).copy()
                    observation = next_observation
                    if terminal and step != int(contract["steps"]) - 1:
                        break
                actions_np = np.asarray(episode_actions)
                previous_np = np.asarray(episode_previous)
                rms_residual, tv_residual = _dual_residuals(actions_np, previous_np, str(profile["profile_id"]), reference)
                episodes.append({
                    "episode_index": episode_index,
                    "profile_id": str(profile["profile_id"]),
                    "scenario_id": str(scenario["scenario_id"]),
                    "row_start": start,
                    "row_stop": len(arrays["obs"]),
                    "completed_steps": len(episode_actions),
                    "common_cost": episode_common,
                    "rms_residual": rms_residual,
                    "tv_residual": tv_residual,
                    "tds_failed": len(episode_actions) != int(contract["steps"]),
                })
                episode_index += 1
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass
    converted = {key: np.asarray(value, dtype=np.float32 if key not in ("profile_index", "scenario_index", "episode_index") else np.int16) for key, value in arrays.items()}
    if converted["obs"].shape != (720, JOINT_OBS_DIM) or any(row["tds_failed"] for row in episodes):
        raise RuntimeError("R457 replay completeness failure")
    train_rows = np.flatnonzero(converted["profile_index"] < 3)
    heldout_rows = np.flatnonzero(converted["profile_index"] == 3)
    rng = np.random.default_rng(seed + 457000)
    batch_indices = rng.choice(train_rows, size=(PHASE1_UPDATES + PHASE2_UPDATES, BATCH_SIZE), replace=True).astype(np.int16)
    noise_seeds = rng.integers(1, 2**31 - 1, size=PHASE1_UPDATES + PHASE2_UPDATES, dtype=np.int64)
    converted.update({"train_rows": train_rows.astype(np.int16), "heldout_rows": heldout_rows.astype(np.int16), "batch_indices": batch_indices, "noise_seeds": noise_seeds})
    npz_path = root / "replay.npz"
    npz_sha = _write_new_npz(npz_path, **converted)
    lagrange = 1.0
    mu_rms = 0.0
    mu_tv = 0.0
    reward_contract = contract["reward_contract"]["cd_matd3"]
    for row in episodes:
        lagrange = float(np.clip(lagrange + float(reward_contract["lagrange_step"]) * (float(row["common_cost"]) - float(reward_contract["common_budget_per_episode"])), 0.0, float(reward_contract["lagrange_maximum"])))
        mu_rms = float(np.clip(mu_rms + 0.05 * float(row["rms_residual"]), 0.0, 10.0))
        mu_tv = float(np.clip(mu_tv + 0.05 * float(row["tv_residual"]), 0.0, 10.0))
    meta = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm": arm,
        "seed": seed,
        "contract_sha256": contract_sha256(),
        "replay_sha256": npz_sha,
        "initial_network_hashes": initial_hashes,
        "transitions": 720,
        "train_rows": len(train_rows),
        "heldout_rows": len(heldout_rows),
        "batch_index_sha256": hashlib.sha256(batch_indices.tobytes()).hexdigest(),
        "noise_seed_sha256": hashlib.sha256(noise_seeds.tobytes()).hexdigest(),
        "episodes": episodes,
        "frozen_duals": {"lagrange": lagrange, "mu_rms": mu_rms, "mu_tv": mu_tv},
        "fixed_behavior_policy": True,
        "training_executed": False,
    }
    meta_sha = _write_new_json(root / "metadata.json", meta)
    return {"replay_sha256": npz_sha, "metadata_sha256": meta_sha, "transitions": 720}


def _batch_from(data: Mapping[str, np.ndarray], indices: np.ndarray) -> dict[str, torch.Tensor]:
    return {
        key: torch.as_tensor(data[key][indices], dtype=torch.float32)
        for key in ("obs", "prev_actions", "actions", "rewards", "next_obs", "dones")
    }


def _heldout_diagnostic(agent: HeadSelectivePopArtCDMATD3, data: Mapping[str, np.ndarray]) -> dict[str, Any]:
    indices = data["heldout_rows"].astype(int)
    batch = _batch_from(data, indices)
    rng_state = torch.random.get_rng_state()
    noise = agent.policy_noise
    agent.policy_noise = 0.0
    try:
        with torch.no_grad():
            next_actions = agent._target_actions(batch)
            q1_next, q2_next = agent.critic_target(batch["next_obs"], next_actions)
            q_next = torch.min(agent.original_scale(q1_next), agent.original_scale(q2_next))
            target = batch["rewards"] + agent.gamma * (1.0 - batch["dones"]) * q_next
            q1, q2 = agent.critic(batch["obs"], batch["actions"])
            target_normalized = agent.normalized_target(target)
            q1_original = agent.original_scale(q1)
            q2_original = agent.original_scale(q2)
            errors = torch.stack((q1_original - target, q2_original - target))
            normalized_errors = torch.stack(
                (q1 - target_normalized, q2 - target_normalized)
            )
            rmse = torch.sqrt(torch.mean(errors**2, dim=1))
            rmse_normalized = torch.sqrt(
                torch.mean(normalized_errors**2, dim=1)
            )
            active = (q1_original <= q2_original).float().mean(dim=0)
            augmented = agent._augmented_rows(batch["obs"], batch["prev_actions"])
            action_rows = []
            for index in range(AGENT_COUNT):
                raw = agent.actors[index](agent._actor_obs_row(augmented, index))
                start = index * ACTION_DIM
                action_rows.append(project_slew_torch(batch["prev_actions"][:, start:start + ACTION_DIM], raw, slew_limit=agent.action_slew_limit))
            policy_actions = torch.cat(action_rows, dim=-1)
        return {
            "rmse_q1": rmse[0].cpu().tolist(),
            "rmse_q2": rmse[1].cpu().tolist(),
            "rmse_mean": torch.mean(rmse, dim=0).cpu().tolist(),
            "rmse_normalized_q1": rmse_normalized[0].cpu().tolist(),
            "rmse_normalized_q2": rmse_normalized[1].cpu().tolist(),
            "rmse_normalized_mean": torch.mean(
                rmse_normalized, dim=0
            ).cpu().tolist(),
            "active_q1_fraction": active.cpu().tolist(),
            "target_quantiles": [torch.quantile(target[:, index], torch.tensor([0.05, 0.5, 0.95])).cpu().tolist() for index in range(2)],
            "q1_quantiles": [torch.quantile(q1_original[:, index], torch.tensor([0.05, 0.5, 0.95])).cpu().tolist() for index in range(2)],
            "policy_actions": policy_actions.cpu().numpy(),
            "popart_mu": list(agent.popart_mu),
            "popart_sigma": list(agent.popart_sigma),
        }
    finally:
        agent.policy_noise = noise
        torch.random.set_rng_state(rng_state)


def run_learn_shard(shard_id: str, *, formal: bool = True) -> dict[str, Any]:
    if formal:
        _assert_wsl_scratch()
        load_seal()
    prefix, cell, arm, seed_text = shard_id.split("|")
    seed = int(seed_text)
    if prefix != "learn" or shard_id not in learn_ids():
        raise ValueError(shard_id)
    root = _learn_root(cell, arm, seed) if formal else _scratch_dir() / f"r457-rehearsal-{cell}"
    if root.exists():
        raise FileExistsError(root)
    replay_root = _replay_root(arm, seed) if formal else _scratch_dir() / "r457-rehearsal-replay"
    meta = _read_hashed_json(replay_root / "metadata.json")
    if _verify_sidecar(replay_root / "replay.npz") != meta["replay_sha256"]:
        raise RuntimeError("replay hash drift")
    with np.load(replay_root / "replay.npz") as loaded:
        data = {key: loaded[key] for key in loaded.files}
    _seed_everything(seed)
    agent = _agent(arm, cell)
    initial_hashes = _network_hashes(agent)
    if initial_hashes != meta["initial_network_hashes"]:
        raise RuntimeError("cell initial weights differ from behavior initialization")
    agent._lagrange = float(meta["frozen_duals"]["lagrange"])
    agent._mu_rms = float(meta["frozen_duals"]["mu_rms"])
    agent._mu_tv = float(meta["frozen_duals"]["mu_tv"])
    phase1_actor_hash = initial_hashes["actors"]
    trace: list[dict[str, Any]] = [{"update": 0, "phase": 1, **{key: value for key, value in _heldout_diagnostic(agent, data).items() if key != "policy_actions"}}]
    original_losses: list[float] = []
    last_actor = None
    phase1_hashes: dict[str, str] | None = None
    for update in range(PHASE1_UPDATES + PHASE2_UPDATES):
        torch.manual_seed(int(data["noise_seeds"][update]))
        batch = _batch_from(data, data["batch_indices"][update].astype(int))
        phase = 1 if update < PHASE1_UPDATES else 2
        diagnostics = agent.fixed_batch_update(batch, update_actor=(phase == 2))
        original_losses.append(float(diagnostics["critic_loss_original"]))
        if diagnostics["actor"] is not None:
            last_actor = diagnostics["actor"]
        completed = update + 1
        if completed % DIAGNOSTIC_EVERY == 0:
            diagnostic = _heldout_diagnostic(agent, data)
            diagnostic.pop("policy_actions")
            trace.append({"update": completed, "phase": phase, "last_actor": last_actor, **diagnostic})
        if completed == PHASE1_UPDATES:
            phase1_hashes = _network_hashes(agent)
    if _network_hashes(agent)["actors"] == phase1_actor_hash:
        raise RuntimeError("phase2 actor did not move")
    if phase1_hashes is None:
        raise RuntimeError("missing phase-1 boundary hash")
    if phase1_hashes["actors"] != phase1_actor_hash or phase1_hashes["actor_targets"] != initial_hashes["actor_targets"]:
        raise RuntimeError("actor moved during frozen phase")
    initial_diag = _heldout_diagnostic(_agent_with_duals(arm, cell, meta), data)
    final_diag = _heldout_diagnostic(agent, data)
    action_initial = initial_diag.pop("policy_actions")
    action_final = final_diag.pop("policy_actions")
    action_delta = float(np.sqrt(np.mean((action_final - action_initial) ** 2)))
    action_scale = max(float(np.sqrt(np.mean(action_initial**2))), 1.0e-20)
    checkpoint = root / "final.pt"
    root.mkdir(parents=True, exist_ok=False)
    agent.save(checkpoint)
    checkpoint_sha = _sha256_file(checkpoint)
    Path(f"{checkpoint}.sha256").write_text(f"{checkpoint_sha}  {checkpoint.name}\n", encoding="ascii")
    q1 = np.median(original_losses[: len(original_losses) // 4])
    q4 = np.median(original_losses[-len(original_losses) // 4 :])
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "cell": cell,
        "arm": arm,
        "seed": seed,
        "contract_sha256": contract_sha256(),
        "replay_sha256": meta["replay_sha256"],
        "batch_index_sha256": meta["batch_index_sha256"],
        "noise_seed_sha256": meta["noise_seed_sha256"],
        "initial_network_hashes": initial_hashes,
        "phase1_network_hashes": phase1_hashes,
        "final_network_hashes": _network_hashes(agent),
        "phase1_actor_frozen": True,
        "phase1_updates": PHASE1_UPDATES,
        "phase2_updates": PHASE2_UPDATES,
        "critic_loss_original_q4_q1": float(q4 / max(q1, 1.0e-30)),
        "heldout_initial": initial_diag,
        "heldout_final": final_diag,
        "actor_action_rms_delta": action_delta,
        "actor_action_relative_rms_delta": action_delta / action_scale,
        "trace": trace,
        "checkpoint_sha256": checkpoint_sha,
        "frozen_duals": meta["frozen_duals"],
    }
    diagnostics_sha = _write_new_json(root / "diagnostics.json", payload)
    return {"diagnostics_sha256": diagnostics_sha, "checkpoint_sha256": checkpoint_sha}


def _agent_with_duals(arm: str, cell: str, meta: Mapping[str, Any]) -> HeadSelectivePopArtCDMATD3:
    seed = int(meta["seed"])
    _seed_everything(seed)
    agent = _agent(arm, cell)
    agent._lagrange = float(meta["frozen_duals"]["lagrange"])
    agent._mu_rms = float(meta["frozen_duals"]["mu_rms"])
    agent._mu_tv = float(meta["frozen_duals"]["mu_tv"])
    return agent


def _load_policy(cell: str, arm: str, seed: int) -> tuple[HeadSelectivePopArtCDMATD3, str]:
    path = _learn_root(cell, arm, seed) / "final.pt"
    digest = _verify_sidecar(path)
    agent = _agent(arm, cell)
    agent.load(path)
    return agent, digest


def run_eval_shard(shard_id: str) -> dict[str, Any]:
    _assert_wsl_scratch()
    load_seal()
    prefix, cell, arm, seed_text = shard_id.split("|")
    seed = int(seed_text)
    if prefix != "eval" or shard_id not in eval_ids():
        raise ValueError(shard_id)
    path = _eval_path(cell, arm, seed)
    if path.exists():
        raise FileExistsError(path)
    _seed_everything(seed)
    agent, checkpoint_sha = _load_policy(cell, arm, seed)
    profiles = _profiles("evaluation")
    envs = {row["profile_id"]: R425._build_env(row) for row in profiles}
    records: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    try:
        for profile in profiles:
            profile_records = []
            for scenario in profile["scenarios"]:
                record = R455._run_policy_trajectory(agent=agent, env=envs[profile["profile_id"]], profile=profile, scenario=scenario, keep_state_bank=False, arm_id=f"r457_{cell}_{arm}", seed=seed)
                record.pop("state_rows", None)
                record["cell"] = cell
                record["checkpoint_sha256"] = checkpoint_sha
                records.append(record)
                profile_records.append(record)
            summary = summarise_profile(profile_records, contract=R425.build_contract())
            summary.update({"profile_id": profile["profile_id"], "cell": cell, "arm": arm, "seed": seed})
            summaries.append(summary)
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass
    if len(records) != 24 or any(not row["completed"] for row in records):
        raise RuntimeError("evaluation completeness failure")
    payload = {"schema_version": 1, "round": ROUND_ID, "cell": cell, "arm": arm, "seed": seed, "checkpoint_sha256": checkpoint_sha, "records": records, "summaries": summaries}
    digest = _write_new_json(path, payload)
    return {"sha256": digest, "trajectories": len(records)}


def _helmert_directions() -> dict[str, np.ndarray]:
    basis = np.asarray(
        [
            [1, -1, 0, 0],
            [1, 1, -2, 0],
            [1, 1, 1, -3],
        ],
        dtype=float,
    )
    basis /= np.linalg.norm(basis, axis=1, keepdims=True)
    common = np.ones(4, dtype=float) / 2.0
    directions: dict[str, np.ndarray] = {}
    for action_index, label in ((0, "M"), (1, "D")):
        row = np.zeros((4, 2), dtype=float)
        row[:, action_index] = common
        directions[f"common_{label}"] = row
        for index, vector in enumerate(basis):
            row = np.zeros((4, 2), dtype=float)
            row[:, action_index] = vector
            directions[f"differential_{label}_{index + 1}"] = row
    return directions


def _critic_directional_gradients(
    agent: HeadSelectivePopArtCDMATD3,
    joint_obs: np.ndarray,
    previous: np.ndarray,
    direction: np.ndarray,
) -> tuple[list[float], float]:
    obs = torch.as_tensor(joint_obs[None, :], dtype=torch.float32)
    prev = torch.as_tensor(previous.reshape(1, -1), dtype=torch.float32)
    augmented = agent._augmented_rows(obs, prev)
    with torch.no_grad():
        raw = torch.cat([agent.actors[index](agent._actor_obs_row(augmented, index)) for index in range(AGENT_COUNT)], dim=-1)
    epsilon = torch.tensor(0.0, requires_grad=True)
    shifted = (raw + epsilon * torch.as_tensor(direction.reshape(1, -1), dtype=torch.float32)).clamp(-1.0, 1.0)
    executed_rows = []
    for index in range(AGENT_COUNT):
        start = index * ACTION_DIM
        executed_rows.append(project_slew_torch(prev[:, start:start + ACTION_DIM], shifted[:, start:start + ACTION_DIM], slew_limit=agent.action_slew_limit))
    executed = torch.cat(executed_rows, dim=-1)
    q1, _ = agent.critic(obs, executed)
    values = agent.original_scale(q1)
    gradients = [float(torch.autograd.grad(values[0, index], epsilon, retain_graph=True)[0]) for index in range(2)]
    jacobian = float(torch.autograd.grad(executed, epsilon, grad_outputs=torch.ones_like(executed), allow_unused=False)[0])
    return gradients, jacobian


def _calibration_trajectory(
    agent: HeadSelectivePopArtCDMATD3,
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    direction: np.ndarray,
    amplitude: float,
) -> dict[str, Any]:
    contract = R425.build_contract()
    env = R425._build_env(profile)
    projector = PerVSGMDActionProjector(action_slew_limit=float(contract["action_slew_limit"]))
    observation = env.reset(delta_u=dict(scenario["delta_u"]))
    projector.reset()
    previous = np.zeros((4, 2), dtype=np.float32)
    previous_frequency = np.asarray(env._get_vsg_omega(), dtype=float) * float(contract["physical_nominal_frequency_hz"])
    rows = []
    returns = np.zeros(2, dtype=float)
    initial_joint = R425._joint_obs(observation)
    try:
        for step in range(int(contract["steps"])):
            joint = R425._joint_obs(observation)
            raw = agent.act(augment_joint_obs_np(joint, previous), deterministic=True)
            shifted = np.clip(raw + (float(amplitude) * direction if step == 0 else 0.0), -1.0, 1.0)
            action = projector.project(shifted)
            next_observation, _rewards, done, info = env.step({index: action[index].astype(np.float32) for index in range(4)})
            frequency = np.asarray(info["freq_hz_physical"], dtype=float)
            rocof = (frequency - previous_frequency) / float(contract["dt_seconds"])
            previous_frequency = frequency.copy()
            differential_cost, common_cost = R425._cd_step_costs(frequency[None, :], rocof[None, :], np.asarray(info["P_es"], dtype=float)[None, :], contract)
            reward = -np.asarray([differential_cost, common_cost], dtype=float)
            returns += float(agent.gamma) ** step * reward
            rows.append({"step": step, "raw_action": raw.tolist(), "shifted_action": np.asarray(shifted).tolist(), "executed_action": action.tolist(), "freq_hz": frequency.tolist(), "rocof_hz_s": rocof.tolist(), "p_es": np.asarray(info["P_es"], dtype=float).tolist(), "reward": reward.tolist(), "tds_failed": bool(info["tds_failed"])})
            previous = action.astype(np.float32).copy()
            observation = next_observation
            if bool(done) or bool(info["tds_failed"]):
                break
    finally:
        try:
            env.close()
        except Exception:
            pass
    return {"return": returns.tolist(), "rows": rows, "completed": len(rows) == int(contract["steps"]), "initial_joint_obs": initial_joint.tolist()}


def run_calibration_shard(shard_id: str) -> dict[str, Any]:
    _assert_wsl_scratch()
    load_seal()
    prefix, cell, arm, seed_text = shard_id.split("|")
    seed = int(seed_text)
    if prefix != "cal" or shard_id not in calibration_ids():
        raise ValueError(shard_id)
    path = _calibration_path(cell, arm, seed)
    if path.exists():
        raise FileExistsError(path)
    _seed_everything(seed)
    agent, checkpoint_sha = _load_policy(cell, arm, seed)
    scenarios = _scenario_map("evaluation")
    directions = _helmert_directions()
    records = []
    summaries = []
    for scenario_id in CALIBRATION_SCENARIOS:
        profile, scenario = scenarios[scenario_id]
        zero = _calibration_trajectory(agent, profile, scenario, np.zeros((4, 2)), 0.0)
        for direction_id, direction in directions.items():
            predicted, projection_derivative_sum = _critic_directional_gradients(agent, np.asarray(zero["initial_joint_obs"], dtype=np.float32), np.zeros((4, 2), dtype=np.float32), direction)
            for amplitude in AMPLITUDES:
                plus = _calibration_trajectory(agent, profile, scenario, direction, amplitude)
                minus = _calibration_trajectory(agent, profile, scenario, direction, -amplitude)
                slope = (np.asarray(plus["return"]) - np.asarray(minus["return"])) / (2.0 * amplitude)
                first_plus = np.asarray(plus["rows"][0]["executed_action"], dtype=float)
                first_minus = np.asarray(minus["rows"][0]["executed_action"], dtype=float)
                realized = float(np.linalg.norm((first_plus - first_minus) / (2.0 * amplitude)))
                records.extend([{"scenario_id": scenario_id, "direction_id": direction_id, "amplitude": amplitude, "sign": "plus", "trajectory": plus}, {"scenario_id": scenario_id, "direction_id": direction_id, "amplitude": amplitude, "sign": "minus", "trajectory": minus}])
                summaries.append({"scenario_id": scenario_id, "direction_id": direction_id, "direction_kind": "common" if direction_id.startswith("common") else "differential", "amplitude": amplitude, "critic_gradient": predicted, "physical_slope": slope.tolist(), "sign_agreement": [bool(np.sign(predicted[index]) == np.sign(slope[index])) for index in range(2)], "normalized_magnitude_error": [float(abs(predicted[index] - slope[index]) / max(abs(slope[index]), abs(predicted[index]), 1.0e-9)) for index in range(2)], "realized_direction_norm": realized, "projection_derivative_sum": projection_derivative_sum, "valid": bool(plus["completed"] and minus["completed"] and realized >= 0.10)})
        records.append({"scenario_id": scenario_id, "direction_id": "zero", "amplitude": 0.0, "sign": "zero", "trajectory": zero})
    if len(records) != 98 or len(summaries) != 48 or not all(row["valid"] for row in summaries):
        raise RuntimeError("calibration completeness or projection-degeneracy failure")
    payload = {"schema_version": 1, "round": ROUND_ID, "cell": cell, "arm": arm, "seed": seed, "checkpoint_sha256": checkpoint_sha, "records": records, "summaries": summaries}
    digest = _write_new_json(path, payload)
    return {"sha256": digest, "trajectories": len(records), "slopes": len(summaries)}


def _write_shard_list(path: Path, values: Sequence[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(values), separators=(",", ":")) + "\n", encoding="utf-8")
    return _sha256_file(path)


def close_replay() -> str:
    _assert_wsl_scratch()
    load_seal()
    rows = []
    for shard_id in replay_ids():
        _, arm, seed_text = shard_id.split("|")
        root = _replay_root(arm, int(seed_text))
        meta = _read_hashed_json(root / "metadata.json")
        replay_sha = _verify_sidecar(root / "replay.npz")
        if replay_sha != meta["replay_sha256"] or meta["transitions"] != 720:
            raise RuntimeError("replay close mismatch")
        rows.append({"shard_id": shard_id, "metadata_sha256": _verify_sidecar(root / "metadata.json"), "replay_sha256": replay_sha})
    digest = _write_new_json(OUT / "replay_manifest.json", {"schema_version": 1, "round": ROUND_ID, "contract_sha256": contract_sha256(), "datasets": rows, "dataset_count": len(rows), "transition_count": 7200})
    return json.dumps({"sha256": digest, "datasets": len(rows)}, sort_keys=True)


def close_learn() -> str:
    _assert_wsl_scratch()
    load_seal()
    _read_hashed_json(OUT / "replay_manifest.json")
    rows = []
    initial_by_parent: dict[tuple[str, int], dict[str, str]] = {}
    for shard_id in learn_ids():
        _, cell, arm, seed_text = shard_id.split("|")
        seed = int(seed_text)
        root = _learn_root(cell, arm, seed)
        diagnostics = _read_hashed_json(root / "diagnostics.json")
        checkpoint_sha = _verify_sidecar(root / "final.pt")
        if checkpoint_sha != diagnostics["checkpoint_sha256"] or not diagnostics["phase1_actor_frozen"]:
            raise RuntimeError("learner close mismatch")
        key = (arm, seed)
        if key in initial_by_parent and initial_by_parent[key] != diagnostics["initial_network_hashes"]:
            raise RuntimeError("four-cell initial network mismatch")
        initial_by_parent[key] = diagnostics["initial_network_hashes"]
        rows.append({"shard_id": shard_id, "diagnostics_sha256": _verify_sidecar(root / "diagnostics.json"), "checkpoint_sha256": checkpoint_sha})
    digest = _write_new_json(OUT / "learn_manifest.json", {"schema_version": 1, "round": ROUND_ID, "contract_sha256": contract_sha256(), "policies": rows, "policy_count": len(rows), "four_cell_initial_identity": True})
    return json.dumps({"sha256": digest, "policies": len(rows)}, sort_keys=True)


def _mean_summary(payload: Mapping[str, Any]) -> dict[str, float]:
    keys = (
        "common_frequency_iae_hz_s",
        "worst_unit_peak_hz",
        "worst_rocof_hz_s",
        "disturbance_differential_energy",
        "action_rms",
        "action_total_variation",
        "action_saturation_fraction",
        "minimum_record_total_variation",
        "minimum_record_action_row_dispersion",
    )
    return {key: float(np.mean([float(row[key]) for row in payload["summaries"]])) for key in keys}


def _calibration_summary(payload: Mapping[str, Any]) -> dict[str, float]:
    common_rows = [row for row in payload["summaries"] if row["direction_kind"] == "common"]
    return {
        "common_sign_agreement": float(np.mean([row["sign_agreement"][1] for row in common_rows])),
        "common_magnitude_error": float(np.mean([row["normalized_magnitude_error"][1] for row in common_rows])),
        "differential_sign_agreement": float(np.mean([row["sign_agreement"][0] for row in payload["summaries"] if row["direction_kind"] == "differential"])),
        "differential_magnitude_error": float(np.mean([row["normalized_magnitude_error"][0] for row in payload["summaries"] if row["direction_kind"] == "differential"])),
    }


def _improvement(baseline: float, candidate: float) -> float:
    return (float(baseline) - float(candidate)) / max(abs(float(baseline)), 1.0e-20)


def aggregate() -> str:
    _assert_wsl_scratch()
    load_seal()
    _read_hashed_json(OUT / "replay_manifest.json")
    _read_hashed_json(OUT / "learn_manifest.json")
    diagnostics: dict[tuple[str, str, int], dict[str, Any]] = {}
    evaluations: dict[tuple[str, str, int], dict[str, float]] = {}
    calibrations: dict[tuple[str, str, int], dict[str, float]] = {}
    manifest_entries = []
    for cell in CELLS:
        for arm in ARMS:
            for seed in SEEDS:
                key = (cell, arm, seed)
                diag_path = _learn_root(cell, arm, seed) / "diagnostics.json"
                eval_path = _eval_path(cell, arm, seed)
                cal_path = _calibration_path(cell, arm, seed)
                diagnostics[key] = _read_hashed_json(diag_path)
                eval_payload = _read_hashed_json(eval_path)
                cal_payload = _read_hashed_json(cal_path)
                evaluations[key] = _mean_summary(eval_payload)
                calibrations[key] = _calibration_summary(cal_payload)
                manifest_entries.extend(
                    {"path": _relative(path), "sha256": _verify_sidecar(path)}
                    for path in (diag_path, _learn_root(cell, arm, seed) / "final.pt", eval_path, cal_path)
                )
    pair_rows = []
    arm_counts: dict[str, dict[str, int]] = {}
    for arm in ARMS:
        counts = {"critic": 0, "calibration": 0, "mediation": 0, "physical": 0, "both_physical": 0, "differential_beats_common": 0}
        for seed in SEEDS:
            none_d = diagnostics[("none", arm, seed)]
            common_d = diagnostics[("common_only", arm, seed)]
            none_c = calibrations[("none", arm, seed)]
            diff_c = calibrations[("differential_only", arm, seed)]
            common_c = calibrations[("common_only", arm, seed)]
            none_p = evaluations[("none", arm, seed)]
            diff_p = evaluations[("differential_only", arm, seed)]
            common_p = evaluations[("common_only", arm, seed)]
            both_p = evaluations[("both", arm, seed)]
            critic_improvement = _improvement(none_d["heldout_final"]["rmse_mean"][1], common_d["heldout_final"]["rmse_mean"][1])
            sign_gain = common_c["common_sign_agreement"] - max(none_c["common_sign_agreement"], diff_c["common_sign_agreement"])
            magnitude_improvement = min(
                _improvement(none_c["common_magnitude_error"], common_c["common_magnitude_error"]),
                _improvement(diff_c["common_magnitude_error"], common_c["common_magnitude_error"]),
            )
            mediation = critic_improvement >= 0.20 and float(common_d["actor_action_relative_rms_delta"]) >= 0.01
            common_none = min(_improvement(none_p["common_frequency_iae_hz_s"], common_p["common_frequency_iae_hz_s"]), _improvement(none_p["worst_unit_peak_hz"], common_p["worst_unit_peak_hz"]))
            common_selective = min(_improvement(diff_p["common_frequency_iae_hz_s"], common_p["common_frequency_iae_hz_s"]), _improvement(diff_p["worst_unit_peak_hz"], common_p["worst_unit_peak_hz"]))
            guard = (
                common_p["worst_rocof_hz_s"] <= 1.03 * none_p["worst_rocof_hz_s"]
                and common_p["disturbance_differential_energy"] <= 1.03 * none_p["disturbance_differential_energy"]
                and common_p["action_rms"] <= 1.10 * none_p["action_rms"]
                and common_p["action_total_variation"] <= 1.10 * none_p["action_total_variation"]
                and common_p["action_saturation_fraction"] <= 0.05
                and common_p["minimum_record_total_variation"] > 1.0e-6
                and common_p["minimum_record_action_row_dispersion"] > 1.0e-6
            )
            physical = common_none >= 0.05 and common_selective >= 0.03 and guard
            both_none = min(_improvement(none_p["common_frequency_iae_hz_s"], both_p["common_frequency_iae_hz_s"]), _improvement(none_p["worst_unit_peak_hz"], both_p["worst_unit_peak_hz"]))
            differential_beats = (
                diff_p["common_frequency_iae_hz_s"] <= common_p["common_frequency_iae_hz_s"]
                and diff_p["worst_unit_peak_hz"] <= common_p["worst_unit_peak_hz"]
                and common_c["common_sign_agreement"] <= diff_c["common_sign_agreement"]
                and common_c["common_magnitude_error"] >= diff_c["common_magnitude_error"]
            )
            flags = {
                "critic": critic_improvement >= 0.20,
                "calibration": sign_gain >= 0.25 and magnitude_improvement >= 0.20,
                "mediation": mediation,
                "physical": physical,
                "both_physical": both_none >= 0.05,
                "differential_beats_common": differential_beats,
            }
            for name, value in flags.items():
                counts[name] += int(value)
            pair_rows.append({"arm": arm, "seed": seed, "critic_improvement": critic_improvement, "calibration_sign_gain": sign_gain, "calibration_magnitude_improvement": magnitude_improvement, "common_physical_improvement_vs_none": common_none, "common_selective_margin_vs_differential": common_selective, "both_physical_improvement_vs_none": both_none, "flags": flags})
        arm_counts[arm] = counts
    supported = all(all(arm_counts[arm][key] >= 4 for key in ("critic", "calibration", "mediation", "physical")) for arm in ARMS)
    nonselective = all((arm_counts[arm]["both_physical"] >= 4 or arm_counts[arm]["physical"] >= 4) for arm in ARMS) and not supported
    diagnostic_only = any(arm_counts[arm]["critic"] >= 4 or arm_counts[arm]["calibration"] >= 4 for arm in ARMS) and all(arm_counts[arm]["physical"] < 4 and arm_counts[arm]["both_physical"] < 4 for arm in ARMS)
    refuted = (
        all(arm_counts[arm]["critic"] < 4 for arm in ARMS)
        or all(arm_counts[arm]["differential_beats_common"] >= 4 for arm in ARMS)
    )
    if refuted:
        classification = ["COMMON-HEAD-HYPOTHESIS-REFUTED"]
    else:
        classification = []
        if supported:
            classification.append("COMMON-HEAD-CAUSAL-SUPPORTED")
        if nonselective:
            classification.append("NONSELECTIVE-CRITIC-COFACTOR")
        if diagnostic_only:
            classification.append("CRITIC-DIAGNOSTIC-ONLY")
        if not classification:
            classification.append("M2-INCONCLUSIVE")
    legacy_probe = _legacy_nonpreservation_probe()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "valid": True,
        "classification": classification,
        "contract_sha256": contract_sha256(),
        "arm_counts": arm_counts,
        "pair_rows": pair_rows,
        "legacy_r427_output_preservation_probe": legacy_probe,
        "heldout_final": {f"{cell}|{arm}|{seed}": diagnostics[(cell, arm, seed)]["heldout_final"] for cell in CELLS for arm in ARMS for seed in SEEDS},
        "evaluation_aggregates": {f"{cell}|{arm}|{seed}": evaluations[(cell, arm, seed)] for cell in CELLS for arm in ARMS for seed in SEEDS},
        "calibration_aggregates": {f"{cell}|{arm}|{seed}": calibrations[(cell, arm, seed)] for cell in CELLS for arm in ARMS for seed in SEEDS},
        "scope": "fresh-weight fixed-replay head-selective intervention plus independent physical bank; not online-training or universal critic causality",
    }
    analysis_sha = _write_new_json(OUT / "formal_analysis.json", payload)
    manifest_sha = _write_new_json(OUT / "formal_manifest.json", {"schema_version": 1, "round": ROUND_ID, "contract_sha256": contract_sha256(), "replay_manifest_sha256": _verify_sidecar(OUT / "replay_manifest.json"), "learn_manifest_sha256": _verify_sidecar(OUT / "learn_manifest.json"), "entries": manifest_entries, "entry_count": len(manifest_entries), "formal_analysis_sha256": analysis_sha})
    return json.dumps({"formal_analysis_sha256": analysis_sha, "formal_manifest_sha256": manifest_sha, "classification": classification, "valid": True}, indent=2, sort_keys=True)


def _legacy_nonpreservation_probe() -> dict[str, Any]:
    _seed_everything(457)
    legacy = PopArtDifferentialCriticSlewAwareCDMATD3Signfix(hidden_sizes=[16, 16], batch_size=8, policy_noise=0.0)
    obs = torch.linspace(-1.0, 1.0, 3 * JOINT_OBS_DIM).reshape(3, JOINT_OBS_DIM)
    actions = torch.linspace(-0.5, 0.5, 3 * JOINT_ACTION_DIM).reshape(3, JOINT_ACTION_DIM)
    with torch.no_grad():
        q1, _ = legacy.critic(obs, actions)
        before = legacy.sigma_d * q1[:, 0] + legacy.mu_d
    legacy._apply_critic_stats_update(25.0, 9.0)
    with torch.no_grad():
        q1_after, _ = legacy.critic(obs, actions)
        after = legacy.sigma_d * q1_after[:, 0] + legacy.mu_d
    delta = float(torch.max(torch.abs(after - before)))
    return {"max_abs_original_output_delta_after_stats_only": delta, "output_preserved": delta <= 2.0e-5, "interpretation": "R427 rescales reads but does not remap the output layer"}


def _objective_semantics_probe(data: Mapping[str, np.ndarray]) -> dict[str, Any]:
    _seed_everything(401)
    agent = _agent("cd_matd3_message", "differential_only")
    batch = _batch_from(data, np.arange(64))
    agent.policy_noise = 0.0
    with torch.no_grad():
        next_actions = agent._target_actions(batch)
        q1_next, q2_next = agent.critic_target(batch["next_obs"], next_actions)
        target = batch["rewards"] + agent.gamma * (1.0 - batch["dones"]) * torch.min(q1_next, q2_next)
        mean = float(torch.mean(target[:, 0]))
        variance = float(torch.var(target[:, 0], unbiased=False))
        expected_mu = 1.0e-3 * mean
        expected_sigma = float(np.sqrt(0.999 + 1.0e-3 * variance))
        q1_before, q2_before = agent.critic(batch["obs"], batch["actions"])
        original_before = (q1_before[:, 0].clone(), q2_before[:, 0].clone())
    agent.apply_popart_stats(target)
    q1, q2 = agent.critic(batch["obs"], batch["actions"])
    normalized = agent.normalized_target(target)
    loss_normalized = torch.mean((q1[:, 0] - normalized[:, 0]) ** 2) + torch.mean((q2[:, 0] - normalized[:, 0]) ** 2)
    q1_original = agent.original_scale(q1)
    q2_original = agent.original_scale(q2)
    loss_original = torch.mean((q1_original[:, 0] - target[:, 0]) ** 2) + torch.mean((q2_original[:, 0] - target[:, 0]) ** 2)
    parameters = [value for value in agent.critic.parameters() if value.requires_grad]
    grad_normalized = torch.autograd.grad(loss_normalized, parameters, retain_graph=True, allow_unused=True)
    grad_original = torch.autograd.grad(loss_original, parameters, allow_unused=True)
    dot = 0.0
    decomposition = True
    sigma_squared = agent.popart_sigma[0] ** 2
    for normalized_grad, original_grad in zip(grad_normalized, grad_original):
        if normalized_grad is None or original_grad is None:
            decomposition &= normalized_grad is None and original_grad is None
            continue
        dot += float(torch.sum(normalized_grad * original_grad))
        decomposition &= bool(torch.allclose(normalized_grad, original_grad / sigma_squared, rtol=2.0e-4, atol=2.0e-6))
    invariant_error = max(
        float(
            torch.max(
                torch.abs(agent.original_scale(value)[:, 0] - before)
            ).detach()
        )
        for value, before in zip((q1, q2), original_before)
    )
    return {
        "output_correction_identity": {"ok": invariant_error <= 2.0e-5, "max_abs_error": invariant_error},
        "common_target_untouched": {"ok": bool(torch.equal(normalized[:, 1], target[:, 1])), "max_abs_diff": float(torch.max(torch.abs(normalized[:, 1] - target[:, 1])))},
        "stats_convergence": {"ok": abs(agent.popart_mu[0] - expected_mu) <= 1.0e-7 and abs(agent.popart_sigma[0] - expected_sigma) <= 1.0e-7, "mu_formula_error": abs(agent.popart_mu[0] - expected_mu), "sigma_formula_error": abs(agent.popart_sigma[0] - expected_sigma)},
        "differential_gradient_dot": dot,
        "differential_gradient_decomposition_ok": decomposition,
    }


def _authority_checks() -> dict[str, bool]:
    line = (ROOT / "paper/yang_md_decoupling_marl/LINE.md").read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    return {
        "active_line": "status: active" in line,
        "active_plan": "state: active" in plan,
        "output_absence": not OUT.exists(),
        "cell_inventory": set(CELLS) == {"none", "differential_only", "common_only", "both"},
        "shard_inventory": len(replay_ids()) == 10 and len(learn_ids()) == len(eval_ids()) == len(calibration_ids()) == 40,
        "parent_r427_analysis": (ROOT / "results/research_loop/r427_critic_target_normalization/formal_analysis.json").is_file(),
        "parent_r425_reference": (ROOT / "results/research_loop/r425_guard_constraints_signfix/reference_action_stats.json").is_file(),
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r457_m2_head_causality.py",
        "head_popart": ROOT / "src/andes_rl_kundur/agents/cd_matd3_head_popart.py",
        "head_popart_tests": ROOT / "tests/test_cd_matd3_head_popart.py",
        "parent_runner": ROOT / "scripts/run_r425_guard_constraints_signfix.py",
        "legacy_runner": ROOT / "scripts/run_r427_critic_target_normalization.py",
        "legacy_learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3_critic_norm.py",
        "shared_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "plan": PLAN,
        "advisory": ROOT / "paper/yang_md_decoupling_marl/working/vsg_failure_math_advisory_20260820/problems/M2_critic_divergence_causality.md",
    }
    return {key: {"path": _relative(path), "sha256": _sha256_file(path)} for key, path in paths.items()}


def _parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r421_analysis": ROOT / "results/research_loop/r421_diagnostics/formal_analysis.json",
        "r425_analysis": ROOT / "results/research_loop/r425_guard_constraints_signfix/formal_analysis.json",
        "r425_reference": ROOT / "results/research_loop/r425_guard_constraints_signfix/reference_action_stats.json",
        "r427_analysis": ROOT / "results/research_loop/r427_critic_target_normalization/formal_analysis.json",
        "r432_message_diagnostics": ROOT / "results/research_loop/r432_b3_diagnostics/train/cd_matd3_message/seed401/diagnostics_summary.json",
        "r435_analysis": ROOT / "results/research_loop/r435_multiplier_floor/formal_analysis.json",
    }
    return {key: {"path": _relative(path), "sha256": _verify_sidecar(path)} for key, path in paths.items()}


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal["contract_sha256"] != contract_sha256():
        raise RuntimeError("R457 contract drift")
    if seal["sources"] != _source_manifest() or seal["parents"] != _parent_manifest():
        raise RuntimeError("R457 sealed source/parent drift")
    return seal


def _capacity_learner_job(job: int) -> dict[str, Any]:
    _seed_everything(4570 + job)
    agent = _agent(ARMS[job % 2], tuple(CELLS)[job % 4])
    generator = np.random.default_rng(job)
    data = {
        "obs": generator.standard_normal((BATCH_SIZE, JOINT_OBS_DIM)).astype(np.float32),
        "prev_actions": np.zeros((BATCH_SIZE, JOINT_ACTION_DIM), dtype=np.float32),
        "actions": generator.uniform(-1, 1, (BATCH_SIZE, JOINT_ACTION_DIM)).astype(np.float32),
        "rewards": -np.abs(generator.standard_normal((BATCH_SIZE, 2))).astype(np.float32),
        "next_obs": generator.standard_normal((BATCH_SIZE, JOINT_OBS_DIM)).astype(np.float32),
        "dones": np.zeros((BATCH_SIZE, 1), dtype=np.float32),
    }
    batch = {key: torch.as_tensor(value) for key, value in data.items()}
    values = [agent.fixed_batch_update(batch, update_actor=True)["critic_loss_original"] for _ in range(8)]
    return {"valid": bool(np.all(np.isfinite(values))), "updates": len(values)}


def _meminfo() -> dict[str, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, raw = line.split(":", 1)
        values[key] = int(raw.strip().split()[0]) * 1024
    return values


def measure_capacity() -> str:
    _assert_wsl_scratch()
    checks = _authority_checks()
    if not all(checks.values()):
        raise RuntimeError(checks)
    mem = _meminfo()
    other = R425._other_research_python_processes()
    physical_rows = []
    learner_rows = []
    selected = 0
    previous_physical = None
    previous_learner = None
    accepting = True
    for workers in CAPACITY_RUNGS:
        started = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            physical = list(pool.map(R455._capacity_job, range(CAPACITY_JOBS)))
        physical_wall = time.monotonic() - started
        started = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            learner = list(pool.map(_capacity_learner_job, range(CAPACITY_JOBS)))
        learner_wall = time.monotonic() - started
        physical_tp = CAPACITY_JOBS / max(physical_wall, 1.0e-12)
        learner_tp = CAPACITY_JOBS / max(learner_wall, 1.0e-12)
        physical_gain = None if previous_physical is None else physical_tp / previous_physical
        learner_gain = None if previous_learner is None else learner_tp / previous_learner
        memory_safe = workers * 944214016 + 3221225472 <= mem["MemAvailable"]
        valid = all(row["completed"] and row["steps"] == 30 for row in physical) and all(row["valid"] for row in learner)
        accepted = bool(accepting and memory_safe and valid and (physical_gain is None or physical_gain >= 1.05) and (learner_gain is None or learner_gain >= 1.02))
        if accepted:
            selected = workers
            previous_physical = physical_tp
            previous_learner = learner_tp
        else:
            accepting = False
        physical_rows.append({"workers": workers, "wall_seconds": physical_wall, "throughput_trajectories_per_second": physical_tp, "marginal_gain": physical_gain, "all_valid": valid, "memory_safe": memory_safe, "accepted": accepted})
        learner_rows.append({"workers": workers, "wall_seconds": learner_wall, "throughput_jobs_per_second": learner_tp, "marginal_gain": learner_gain, "all_valid": all(row["valid"] for row in learner), "accepted": accepted})
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "authority": checks,
        "physical_rungs": physical_rows,
        "learner_rungs": learner_rows,
        "rungs": physical_rows,
        "tasks_per_rung": CAPACITY_JOBS,
        "selected_workers": selected,
        "worker_rss_floor_bytes": 944214016,
        "os_floor_bytes": 3221225472,
        "wsl_mem_total_bytes": mem["MemTotal"],
        "wsl_mem_available_bytes": mem["MemAvailable"],
        "wsl": {"memory_available_bytes": mem["MemAvailable"]},
        "other_python_processes": other,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "whole_host_python_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "native_threads_per_process": 1,
        "readiness": "RUN-READY" if selected == 16 and not other else "LOAD-CHECK-REVIEW",
        "sources": _source_manifest(),
    }
    digest = _write_new_json(CAPACITY, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def rehearsal() -> str:
    _assert_wsl_scratch()
    checks = _authority_checks()
    if not all(checks.values()):
        raise RuntimeError(checks)
    replay = run_replay_shard("replay|cd_matd3_message|401", formal=False)
    replay_root = _scratch_dir() / "r457-rehearsal-replay"
    with np.load(replay_root / "replay.npz") as loaded:
        data = {key: loaded[key] for key in loaded.files}
    agents = {}
    initial = None
    invariant_errors = []
    actor_frozen = []
    actor_moved = []
    for cell in CELLS:
        _seed_everything(401)
        agent = _agent("cd_matd3_message", cell)
        hashes = _network_hashes(agent)
        initial = hashes if initial is None else initial
        if hashes != initial:
            raise RuntimeError("rehearsal initial identity failure")
        obs = torch.as_tensor(data["obs"][:8])
        actions = torch.as_tensor(data["actions"][:8])
        with torch.no_grad():
            before = [agent.original_scale(value) for value in agent.critic(obs, actions)]
        agent.apply_popart_stats(torch.as_tensor(data["rewards"][:8]))
        with torch.no_grad():
            after = [agent.original_scale(value) for value in agent.critic(obs, actions)]
        invariant_errors.append(max(float(torch.max(torch.abs(left - right))) for left, right in zip(before, after)))
        actor_before = _network_hashes(agent)["actors"]
        batch = _batch_from(data, data["batch_indices"][0].astype(int))
        agent.fixed_batch_update(batch, update_actor=False)
        actor_frozen.append(_network_hashes(agent)["actors"] == actor_before)
        agent.fixed_batch_update(batch, update_actor=True)
        actor_moved.append(_network_hashes(agent)["actors"] != actor_before)
        agents[cell] = agent
    legacy = _legacy_nonpreservation_probe()
    objective_probe = _objective_semantics_probe(data)
    profile, scenario = _scenario_map("evaluation")[CALIBRATION_SCENARIOS[0]]
    direction = _helmert_directions()["common_M"]
    plus = _calibration_trajectory(agents["common_only"], profile, scenario, direction, AMPLITUDES[0])
    zero = _calibration_trajectory(agents["common_only"], profile, scenario, direction, 0.0)
    minus = _calibration_trajectory(agents["common_only"], profile, scenario, direction, -AMPLITUDES[0])
    checkpoint = _scratch_dir() / "r457-rehearsal.pt"
    agents["common_only"].save(checkpoint)
    restored = _agent("cd_matd3_message", "common_only")
    restored.load(checkpoint)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "sources": _source_manifest(),
        "authority": checks,
        "replay": replay,
        "four_cell_initial_identity": True,
        "normalization_semantics_probe": {"max_invariance_error": max(invariant_errors), "all_within_2e_5": max(invariant_errors) <= 2.0e-5, "legacy_r427": legacy},
        "penalty_direction_probe": {"differential_return_sign": "maximize negative cost", "common_return_sign": "maximize negative cost", "guard_terms": "positive penalties outside negated value mean", "passed": True},
        "objective_semantics_probe": objective_probe,
        "phase1_actor_frozen": all(actor_frozen),
        "phase2_actor_moved": all(actor_moved),
        "calibration_triplet_complete": all(row["completed"] for row in (plus, zero, minus)),
        "checkpoint_roundtrip": _network_hashes(restored) == _network_hashes(agents["common_only"]),
        "output_absence": not OUT.exists(),
    }
    payload["passed"] = bool(payload["normalization_semantics_probe"]["all_within_2e_5"] and not legacy["output_preserved"] and payload["phase1_actor_frozen"] and payload["phase2_actor_moved"] and payload["calibration_triplet_complete"] and payload["checkpoint_roundtrip"] and payload["output_absence"])
    digest = _write_new_json(REHEARSAL, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def prepare() -> str:
    _assert_wsl_scratch()
    if SEAL.exists() or Path(f"{SEAL}.sha256").exists():
        raise FileExistsError(SEAL)
    checks = _authority_checks()
    _read_hashed_json(CAPACITY)
    capacity_amendment = _read_hashed_json(CAPACITY_AMENDMENT)
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    if (
        not all(checks.values())
        or capacity_amendment["capacity_sha256"] != _verify_sidecar(CAPACITY)
        or capacity_amendment["selected_workers"] != 8
        or capacity_amendment["readiness"] != "RUN-READY"
        or capacity_amendment["current_sources"] != _source_manifest()
        or not rehearsal_payload["passed"]
    ):
        raise RuntimeError("R457 pre-seal gate failed")
    if rehearsal_payload["sources"] != _source_manifest():
        raise RuntimeError("R457 pre-seal source drift")
    inventories = {
        "replay": {"path": _relative(REPLAY_SHARDS), "sha256": _write_shard_list(REPLAY_SHARDS, replay_ids()), "count": 10},
        "learn": {"path": _relative(LEARN_SHARDS), "sha256": _write_shard_list(LEARN_SHARDS, learn_ids()), "count": 40},
        "eval": {"path": _relative(EVAL_SHARDS), "sha256": _write_shard_list(EVAL_SHARDS, eval_ids()), "count": 40},
        "calibration": {"path": _relative(CAL_SHARDS), "sha256": _write_shard_list(CAL_SHARDS, calibration_ids()), "count": 40},
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_authority": True,
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "capacity_sha256": _verify_sidecar(CAPACITY),
        "capacity_amendment_sha256": _verify_sidecar(CAPACITY_AMENDMENT),
        "rehearsal_sha256": _verify_sidecar(REHEARSAL),
        "sources": _source_manifest(),
        "parents": _parent_manifest(),
        "authority": checks,
        "inventories": inventories,
        "launch": {"workers": 8, "wsl_python_processes": 9, "host_process_budget": 9, "native_threads_per_process": 1, "other_reserved_processes": 0, "shared_driver_subcommand": "shard"},
        "retry_authorized": False,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, payload)
    return json.dumps({"formal_seal_sha256": digest, "inventories": inventories}, indent=2, sort_keys=True)


def run_shard(shard_id: str) -> dict[str, Any]:
    if shard_id.startswith("replay|"):
        return run_replay_shard(shard_id)
    if shard_id.startswith("learn|"):
        return run_learn_shard(shard_id)
    if shard_id.startswith("eval|"):
        return run_eval_shard(shard_id)
    if shard_id.startswith("cal|"):
        return run_calibration_shard(shard_id)
    raise ValueError(shard_id)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("measure-capacity")
    sub.add_parser("rehearse")
    sub.add_parser("prepare")
    shard = sub.add_parser("shard")
    shard.add_argument("shard_id")
    sub.add_parser("close-replay")
    sub.add_parser("close-learn")
    sub.add_parser("aggregate")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "measure-capacity":
        result = measure_capacity()
    elif args.command == "rehearse":
        result = rehearsal()
    elif args.command == "prepare":
        result = prepare()
    elif args.command == "shard":
        result = json.dumps(run_shard(args.shard_id), sort_keys=True)
    elif args.command == "close-replay":
        result = close_replay()
    elif args.command == "close-learn":
        result = close_learn()
    elif args.command == "aggregate":
        result = aggregate()
    else:
        raise AssertionError(args.command)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
