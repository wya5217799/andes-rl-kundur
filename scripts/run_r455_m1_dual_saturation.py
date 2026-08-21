"""R455 M1 projected-dual ceiling and fixed-bank actor diagnostic.

All physical commands are WSL-only through ``andes_scratch.py``.  Formal
artifacts are create-only and paired with SHA-256 sidecars.  The intervention
uses fresh Adam and a frozen R425 critic; it is not a reconstruction of the
historical training trajectory.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_r425_guard_constraints_signfix as R425
from andes_rl_kundur.agents.cd_matd3 import augment_joint_obs_np
from andes_rl_kundur.agents.cd_matd3_dual_factorial import (
    balanced_dual_replay,
    fixed_bank_actor_intervention,
    projected_dual_step,
)
from andes_rl_kundur.agents.cd_matd3_guard_constraints_vfix import (
    GUARD_RESIDUAL_EPSILON,
)
from andes_rl_kundur.control.per_vsg_md import PerVSGMDActionProjector
from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile

ROUND_ID = "R455"
PLAN = ROOT / "memory/rounds/R455/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R455/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R455/rehearsal.json"
SEAL = ROOT / "memory/rounds/R455/formal_seal.json"
STATE_SHARDS = ROOT / "tmp/andes/r455_m1_state_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r455_m1_eval_shards.json"
OUT = ROOT / "results/research_loop/r455_m1_dual_saturation"
PARENT_OUT = ROOT / "results/research_loop/r425_guard_constraints_signfix"

ARMS = ("cd_matd3_no_message", "cd_matd3_message")
SEEDS = (401, 402, 403)
CELLS: tuple[dict[str, Any], ...] = (
    {"cell_id": "U10_eta050", "ceiling": 10.0, "eta": 0.05, "per_profile": False},
    {"cell_id": "U100_eta050", "ceiling": 100.0, "eta": 0.05, "per_profile": False},
    {"cell_id": "U10_eta005", "ceiling": 10.0, "eta": 0.005, "per_profile": False},
    {"cell_id": "U100_eta005", "ceiling": 100.0, "eta": 0.005, "per_profile": False},
    {
        "cell_id": "profile_U100_eta050",
        "ceiling": 100.0,
        "eta": 0.05,
        "per_profile": True,
    },
)
DUAL_REPLAY_STEPS = 20
ACTOR_UPDATE_STEPS = 16
CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS = 32
WORKER_RSS_FLOOR_BYTES = 944_214_016
OS_FLOOR_BYTES = 3 * 1024**3


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    sidecar = Path(f"{path}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    digest = _sha256_file(path)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _write_new_checkpoint(path: Path, agent: Any) -> str:
    sidecar = Path(f"{path}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _verify_sidecar(path: Path) -> str:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(path)
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if expected != actual:
        raise RuntimeError(f"hash mismatch: {path}")
    return actual


def state_shard_ids() -> list[str]:
    return [f"{arm}|{seed}" for arm in ARMS for seed in SEEDS]


def eval_shard_ids() -> list[str]:
    return [f"{cell['cell_id']}|{arm}|{seed}" for cell in CELLS for arm in ARMS for seed in SEEDS]


def _cell(cell_id: str) -> dict[str, Any]:
    for value in CELLS:
        if value["cell_id"] == cell_id:
            return dict(value)
    raise KeyError(cell_id)


def build_contract() -> dict[str, Any]:
    parent = R425.build_contract()
    actor_lr = float(parent["learner_contract"]["lr"])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "parent_round": "R425",
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "cells": [dict(value) for value in CELLS],
        "development_profiles": [
            str(row["profile_id"]) for row in parent["profiles"] if row["split"] == "development"
        ],
        "evaluation_profiles": [
            str(row["profile_id"]) for row in parent["profiles"] if row["split"] == "evaluation"
        ],
        "steps_per_trajectory": int(parent["steps"]),
        "state_trajectory_count": 144,
        "state_transition_count": 4320,
        "evaluation_trajectory_count": 720,
        "evaluation_transition_count": 21600,
        "dual_replay_steps": DUAL_REPLAY_STEPS,
        "actor_update_steps": ACTOR_UPDATE_STEPS,
        "actor_lr": actor_lr,
        "initial_mu_source": "R425 final checkpoint terminal mu_rms/mu_tv",
        "guard_thresholds": {
            "maximum_common_harm": 0.03,
            "maximum_action_stress_harm": 0.10,
            "maximum_action_saturation_fraction": 0.05,
            "nonconstant_action_variation_floor": 1.0e-6,
            "independent_action_dispersion_floor": 1.0e-6,
        },
        "mechanism_thresholds": {
            "multiplier_increase_min": 10.0,
            "gradient_norm_ratio_min": 1.10,
            "fixed_residual_improvement_min": 0.05,
            "physical_stress_improvement_min": 0.05,
            "checkpoint_support_min": 4,
            "ceiling_multiplier_support_min": 5,
            "gradient_conflict_cosine_max": -0.25,
            "gradient_material_ratio_min": 0.10,
            "primal_action_relative_delta_max": 1.0e-3,
            "primal_residual_improvement_max": 0.01,
            "projection_active_fraction_max": 0.10,
            "aggregation_endpoint_or_common_harm_max": 0.03,
        },
        "plan_sha256": _sha256_file(PLAN),
        "parent_contract_sha256": R425.contract_sha256(parent),
    }


def contract_sha256() -> str:
    return _canonical_sha256(build_contract())


def _checkpoint_path(arm: str, seed: int) -> Path:
    return PARENT_OUT / "train" / arm / f"seed{seed}" / "final.pt"


def _checkpoint_inventory() -> list[dict[str, Any]]:
    result = []
    for arm in ARMS:
        for seed in SEEDS:
            path = _checkpoint_path(arm, seed)
            result.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "path": _relative(path),
                    "sha256": _verify_sidecar(path),
                }
            )
    return result


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    checkpoints = _checkpoint_inventory()
    parent_reference = PARENT_OUT / "reference_action_stats.json"
    parent_analysis = PARENT_OUT / "formal_analysis.json"
    return {
        "active_plan": "round: R455" in plan_text and "state: active" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "cell_inventory": len(CELLS) == 5 and len({row["cell_id"] for row in CELLS}) == 5,
        "shard_inventory": len(state_shard_ids()) == 6 and len(eval_shard_ids()) == 30,
        "checkpoint_inventory": len(checkpoints) == 6,
        "parent_reference": bool(_verify_sidecar(parent_reference)),
        "parent_analysis": bool(_verify_sidecar(parent_analysis)),
        "ceiling_release_law": projected_dual_step(10.0, -1.0, eta=0.05, ceiling=10.0) < 10.0,
        "output_absence": not OUT.exists(),
    }


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R455 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R455 must run through scripts/andes_scratch.py")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


def installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID or seal.get("contract_sha256") != contract_sha256():
        raise RuntimeError("R455 seal or contract drift")
    if _sha256_file(CAPACITY) != seal.get("capacity_sha256"):
        raise RuntimeError("capacity evidence drift")
    if _sha256_file(REHEARSAL) != seal.get("rehearsal_sha256"):
        raise RuntimeError("rehearsal evidence drift")
    for entry in (seal.get("sources") or {}).values():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {entry['path']}")
    for entry in seal.get("checkpoints", []):
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed checkpoint drift: {entry['path']}")
    for entry in seal.get("parent_inputs", []):
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed parent input drift: {entry['path']}")
    return seal


def _profile_rows(split: str) -> list[dict[str, Any]]:
    return [dict(row) for row in R425.build_contract()["profiles"] if str(row["split"]) == split]


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))


def _episode_residuals(
    actions: np.ndarray,
    previous_actions: np.ndarray,
    *,
    profile_id: str,
    reference: Mapping[str, Any],
) -> tuple[float, float]:
    action_array = np.asarray(actions, dtype=float)
    previous_array = np.asarray(previous_actions, dtype=float)
    profile_ref = reference["profiles"][profile_id]
    rms_mean = float(np.mean(action_array**2))
    tv_sum = float(np.sum(np.mean(np.abs(action_array - previous_array), axis=(1, 2))))
    rms_denominator = max(
        1.1**2 * float(profile_ref["action_rms_ref"]) ** 2,
        GUARD_RESIDUAL_EPSILON,
    )
    tv_denominator = max(
        1.1 * float(profile_ref["tv_ref_scenario_mean"]),
        GUARD_RESIDUAL_EPSILON,
    )
    return rms_mean / rms_denominator - 1.0, tv_sum / tv_denominator - 1.0


def _run_policy_trajectory(
    *,
    agent: Any,
    env: Any,
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
    keep_state_bank: bool,
    arm_id: str,
    seed: int,
) -> dict[str, Any]:
    contract = R425.build_contract()
    projector = PerVSGMDActionProjector(action_slew_limit=float(contract["action_slew_limit"]))
    observation = env.reset(delta_u=dict(scenario["delta_u"]))
    projector.reset()
    previous = np.zeros((4, 2), dtype=np.float32)
    initial_frequency = np.asarray(env._get_vsg_omega(), dtype=float) * float(
        contract["physical_nominal_frequency_hz"]
    )
    rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    failure = None
    identity = {
        "n_agents": int(env.N_AGENTS),
        "vsg_idx": [str(value) for value in env.vsg_idx],
        "vsg_buses": [int(env.ss.GENCLS.bus.v[position]) for position in env._vsg_pos],
        "obs_dim": int(env.OBS_DIM),
        "baseline_m0": [float(value) for value in profile["baseline_m0"]],
        "baseline_d0": [float(value) for value in profile["baseline_d0"]],
        "control_nominal_frequency_hz": float(env.FN),
        "physical_nominal_frequency_hz": float(env.andes_nominal_frequency_hz),
    }
    for step_index in range(int(contract["steps"])):
        joint = R425._joint_obs(observation)
        augmented = augment_joint_obs_np(joint, previous)
        raw = agent.act(augmented, deterministic=True)
        action = projector.project(raw)
        action_dict = {actor: np.asarray(action[actor], dtype=np.float32) for actor in range(4)}
        next_observation, _rewards, done, info = env.step(action_dict)
        next_joint = R425._joint_obs(next_observation)
        actual_m = np.asarray(
            [env.ss.GENCLS.M.v[position] for position in env._vsg_pos], dtype=float
        )
        actual_d = np.asarray(
            [env.ss.GENCLS.D.v[position] for position in env._vsg_pos], dtype=float
        )
        row = {
            "step_index": step_index,
            "time": float(info["time"]),
            "action_norm": np.asarray(action, dtype=float).tolist(),
            "freq_hz_physical": np.asarray(info["freq_hz_physical"], dtype=float).tolist(),
            "M_es": actual_m.tolist(),
            "D_es": actual_d.tolist(),
            "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
            "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
            "tds_failed": bool(info["tds_failed"]),
            "done": bool(done),
        }
        rows.append(row)
        if keep_state_bank:
            state_rows.append(
                {
                    "profile_id": str(profile["profile_id"]),
                    "scenario_id": str(scenario["scenario_id"]),
                    "step_index": step_index,
                    "joint_observation": joint.astype(float).tolist(),
                    "augmented_observation": augmented.astype(float).tolist(),
                    "previous_action": previous.astype(float).reshape(-1).tolist(),
                    "raw_action": np.asarray(raw, dtype=float).reshape(-1).tolist(),
                    "executed_action": np.asarray(action, dtype=float).reshape(-1).tolist(),
                    "next_joint_observation": next_joint.astype(float).tolist(),
                    "done": bool(done),
                    "tds_failed": bool(info["tds_failed"]),
                    "M_es": actual_m.tolist(),
                    "D_es": actual_d.tolist(),
                }
            )
        previous = np.asarray(action, dtype=np.float32).copy()
        observation = next_observation
        if bool(info["tds_failed"]):
            failure = "TDS failed"
            break
    return {
        "profile_id": str(profile["profile_id"]),
        "split": str(profile["split"]),
        "scenario_id": str(scenario["scenario_id"]),
        "pair_kind": str(scenario["pair_kind"]),
        "sign": str(scenario["sign"]),
        "magnitude": float(scenario["magnitude"]),
        "delta_u": dict(scenario["delta_u"]),
        "arm_id": arm_id,
        "training_seed": int(seed),
        "identity": identity,
        "initial_freq_hz_physical": initial_frequency.tolist(),
        "steps": rows,
        "state_rows": state_rows,
        "completed_steps": len(rows),
        "completed": failure is None and len(rows) == int(contract["steps"]),
        "tds_failed": failure is not None,
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _state_path(arm: str, seed: int) -> Path:
    return OUT / "state" / arm / f"seed{seed}.json"


def run_state_shard(shard_id: str) -> str:
    _assert_wsl_scratch()
    load_seal()
    arm, seed_text = shard_id.split("|")
    seed = int(seed_text)
    if shard_id not in state_shard_ids():
        raise ValueError(shard_id)
    _seed_everything(seed)
    agent = R425._agent_for(arm, "cpu")
    checkpoint = _checkpoint_path(arm, seed)
    checkpoint_before = _sha256_file(checkpoint)
    agent.load(checkpoint)
    reference = _read_hashed_json(PARENT_OUT / "reference_action_stats.json")
    trajectories = []
    envs = {row["profile_id"]: R425._build_env(row) for row in _profile_rows("development")}
    try:
        for profile in _profile_rows("development"):
            env = envs[profile["profile_id"]]
            for scenario in profile["scenarios"]:
                trajectories.append(
                    _run_policy_trajectory(
                        agent=agent,
                        env=env,
                        profile=profile,
                        scenario=scenario,
                        keep_state_bank=True,
                        arm_id=arm,
                        seed=seed,
                    )
                )
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass
    episode_residuals = []
    for trajectory in trajectories:
        actions = np.asarray(
            [row["executed_action"] for row in trajectory["state_rows"]], dtype=float
        ).reshape(-1, 4, 2)
        previous = np.asarray(
            [row["previous_action"] for row in trajectory["state_rows"]], dtype=float
        ).reshape(-1, 4, 2)
        rms, tv = _episode_residuals(
            actions,
            previous,
            profile_id=trajectory["profile_id"],
            reference=reference,
        )
        episode_residuals.append(
            {
                "profile_id": trajectory["profile_id"],
                "scenario_id": trajectory["scenario_id"],
                "rms_residual": rms,
                "tv_residual": tv,
            }
        )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "arm": arm,
        "seed": seed,
        "checkpoint_sha256": checkpoint_before,
        "checkpoint_immutable": checkpoint_before == _sha256_file(checkpoint),
        "trajectories": trajectories,
        "episode_residuals": episode_residuals,
        "trajectory_count": len(trajectories),
        "transition_count": sum(len(row["state_rows"]) for row in trajectories),
        "all_completed": all(row["completed"] for row in trajectories),
    }
    digest = _write_new_json(_state_path(arm, seed), payload)
    return json.dumps({"shard_id": shard_id, "sha256": digest}, sort_keys=True)


def _bank_arrays(payload: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    rows = [row for trajectory in payload["trajectories"] for row in trajectory["state_rows"]]
    return (
        np.asarray([row["joint_observation"] for row in rows], dtype=np.float32),
        np.asarray([row["previous_action"] for row in rows], dtype=np.float32),
        [str(row["profile_id"]) for row in rows],
        [f"{row['profile_id']}|{row['scenario_id']}" for row in rows],
    )


def _profile_mean_residuals(payload: Mapping[str, Any], key: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in payload["episode_residuals"]:
        grouped[str(row["profile_id"])].append(float(row[key]))
    return {profile: float(np.mean(values)) for profile, values in sorted(grouped.items())}


def _fixed_residual_summary(
    actions: np.ndarray,
    previous: np.ndarray,
    profiles: Sequence[str],
    episodes: Sequence[str],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    action_rows = np.asarray(actions, dtype=float).reshape(-1, 4, 2)
    previous_rows = np.asarray(previous, dtype=float).reshape(-1, 4, 2)
    for profile in sorted(set(profiles)):
        episode_values = []
        for episode in sorted(
            {episodes[i] for i, value in enumerate(profiles) if value == profile}
        ):
            indices = [i for i, value in enumerate(episodes) if value == episode]
            rms, tv = _episode_residuals(
                action_rows[indices],
                previous_rows[indices],
                profile_id=profile,
                reference=reference,
            )
            episode_values.append((rms, tv))
        result[profile] = {
            "rms_residual_mean": float(np.mean([row[0] for row in episode_values])),
            "tv_residual_mean": float(np.mean([row[1] for row in episode_values])),
            "episode_count": len(episode_values),
        }
    result["profile_balanced_mean"] = {
        "rms_residual_mean": float(
            np.mean(
                [
                    value["rms_residual_mean"]
                    for key, value in result.items()
                    if key != "profile_balanced_mean"
                ]
            )
        ),
        "tv_residual_mean": float(
            np.mean(
                [
                    value["tv_residual_mean"]
                    for key, value in result.items()
                    if key != "profile_balanced_mean"
                ]
            )
        ),
    }
    return result


def _intervention_path(cell_id: str, arm: str, seed: int) -> Path:
    return OUT / "intervention" / cell_id / arm / f"seed{seed}.json"


def _intervention_checkpoint_path(cell_id: str, arm: str, seed: int) -> Path:
    return OUT / "intervention" / cell_id / arm / f"seed{seed}.pt"


def _parent_tail_audit(arm: str, seed: int) -> dict[str, Any]:
    manifest = _read_hashed_json(PARENT_OUT / "train" / arm / f"seed{seed}" / "manifest.json")
    guards = manifest["guard_multipliers"]
    result = {}
    for name in ("rms", "tv"):
        mus = [float(value) for value in guards[f"mu_{name}_trace"]]
        residuals = [float(value) for value in guards[f"{name}_residual_trace"]]
        identifiable = []
        for index in range(1, min(len(mus), len(residuals))):
            predicted = projected_dual_step(
                mus[index - 1], residuals[index], eta=0.05, ceiling=10.0
            )
            identifiable.append(
                {
                    "index": index,
                    "mu_pre": mus[index - 1],
                    "residual_pre": residuals[index],
                    "mu_recorded_post": mus[index],
                    "mu_predicted_post": predicted,
                    "matches": bool(np.isclose(predicted, mus[index], rtol=0.0, atol=1.0e-12)),
                }
            )
        result[name] = {
            "identifiable_events": identifiable,
            "all_match": all(row["matches"] for row in identifiable),
        }
    return result


def intervene() -> str:
    _assert_wsl_scratch()
    load_seal()
    reference = _read_hashed_json(PARENT_OUT / "reference_action_stats.json")
    summaries = []
    for arm in ARMS:
        for seed in SEEDS:
            bank = _read_hashed_json(_state_path(arm, seed))
            if not bank["all_completed"] or bank["transition_count"] != 720:
                raise RuntimeError(f"invalid state bank: {arm}/{seed}")
            observations, previous, labels, episodes = _bank_arrays(bank)
            rms_profiles = _profile_mean_residuals(bank, "rms_residual")
            tv_profiles = _profile_mean_residuals(bank, "tv_residual")
            tail_audit = _parent_tail_audit(arm, seed)
            if not all(value["all_match"] for value in tail_audit.values()):
                raise RuntimeError(f"parent tail replay mismatch: {arm}/{seed}")
            for cell in CELLS:
                _seed_everything(seed)
                agent = R425._agent_for(arm, "cpu")
                parent_checkpoint = _checkpoint_path(arm, seed)
                parent_before = _sha256_file(parent_checkpoint)
                agent.load(parent_checkpoint)
                initial_mu_rms = float(agent.mu_rms)
                initial_mu_tv = float(agent.mu_tv)
                rms_replay = balanced_dual_replay(
                    initial_mu_rms,
                    rms_profiles,
                    eta=float(cell["eta"]),
                    ceiling=float(cell["ceiling"]),
                    steps=DUAL_REPLAY_STEPS,
                    per_profile=bool(cell["per_profile"]),
                )
                tv_replay = balanced_dual_replay(
                    initial_mu_tv,
                    tv_profiles,
                    eta=float(cell["eta"]),
                    ceiling=float(cell["ceiling"]),
                    steps=DUAL_REPLAY_STEPS,
                    per_profile=bool(cell["per_profile"]),
                )
                if cell["per_profile"]:
                    mu_rms: float | Mapping[str, float] = rms_replay["final_by_profile"]
                    mu_tv: float | Mapping[str, float] = tv_replay["final_by_profile"]
                    agent._mu_rms = float(np.mean(list(mu_rms.values())))
                    agent._mu_tv = float(np.mean(list(mu_tv.values())))
                else:
                    mu_rms = float(rms_replay["final"])
                    mu_tv = float(tv_replay["final"])
                    agent._mu_rms = mu_rms
                    agent._mu_tv = mu_tv
                diagnostic = fixed_bank_actor_intervention(
                    agent,
                    observations=observations,
                    previous_actions=previous,
                    profile_labels=labels,
                    mu_rms=mu_rms,
                    mu_tv=mu_tv,
                    actor_lr=float(build_contract()["actor_lr"]),
                    update_steps=ACTOR_UPDATE_STEPS,
                )
                fixed_before = _fixed_residual_summary(
                    diagnostic["initial_actions"], previous, labels, episodes, reference
                )
                fixed_after = _fixed_residual_summary(
                    diagnostic["final_actions"], previous, labels, episodes, reference
                )
                checkpoint_path = _intervention_checkpoint_path(str(cell["cell_id"]), arm, seed)
                checkpoint_sha = _write_new_checkpoint(checkpoint_path, agent)
                payload = {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "contract_sha256": contract_sha256(),
                    "cell": dict(cell),
                    "arm": arm,
                    "seed": seed,
                    "parent_checkpoint_sha256": parent_before,
                    "intervention_checkpoint_sha256": checkpoint_sha,
                    "initial_mu": {"rms": initial_mu_rms, "tv": initial_mu_tv},
                    "profile_residuals": {"rms": rms_profiles, "tv": tv_profiles},
                    "dual_replay": {"rms": rms_replay, "tv": tv_replay},
                    "parent_tail_audit": tail_audit,
                    "gradient_trace": diagnostic["trace"],
                    "parameter_relative_deltas": diagnostic["parameter_relative_deltas"],
                    "action_rms_delta": diagnostic["action_rms_delta"],
                    "action_relative_rms_delta": diagnostic["action_relative_rms_delta"],
                    "fixed_residual_before": fixed_before,
                    "fixed_residual_after": fixed_after,
                    "frozen_networks_unchanged": diagnostic["frozen_networks_unchanged"],
                    "parent_checkpoint_immutable": parent_before == _sha256_file(parent_checkpoint),
                    "scope": "fresh-Adam frozen-critic fixed-bank actor-only intervention",
                }
                digest = _write_new_json(
                    _intervention_path(str(cell["cell_id"]), arm, seed), payload
                )
                summaries.append(
                    {
                        "cell": cell["cell_id"],
                        "arm": arm,
                        "seed": seed,
                        "json_sha256": digest,
                        "checkpoint_sha256": checkpoint_sha,
                    }
                )
    EVAL_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    EVAL_SHARDS.write_text(json.dumps(eval_shard_ids()) + "\n", encoding="utf-8")
    digest = _write_new_json(
        OUT / "intervention_manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(),
            "cells": summaries,
            "cell_count": len(summaries),
        },
    )
    return json.dumps({"sha256": digest, "cell_count": len(summaries)}, sort_keys=True)


def _eval_path(cell_id: str, arm: str, seed: int) -> Path:
    return OUT / "eval" / cell_id / arm / f"seed{seed}.json"


def run_eval_shard(shard_id: str) -> str:
    _assert_wsl_scratch()
    load_seal()
    cell_id, arm, seed_text = shard_id.split("|")
    seed = int(seed_text)
    if shard_id not in eval_shard_ids():
        raise ValueError(shard_id)
    intervention = _read_hashed_json(_intervention_path(cell_id, arm, seed))
    checkpoint = _intervention_checkpoint_path(cell_id, arm, seed)
    checkpoint_sha = _verify_sidecar(checkpoint)
    if checkpoint_sha != intervention["intervention_checkpoint_sha256"]:
        raise RuntimeError("intervention checkpoint mismatch")
    _seed_everything(seed)
    agent = R425._agent_for(arm, "cpu")
    agent.load(checkpoint)
    evaluation_arm = f"r455_{cell_id}_{arm}"
    profiles = _profile_rows("evaluation")
    envs = {row["profile_id"]: R425._build_env(row) for row in profiles}
    records = []
    summaries = []
    try:
        for profile in profiles:
            profile_records = []
            for scenario in profile["scenarios"]:
                record = _run_policy_trajectory(
                    agent=agent,
                    env=envs[profile["profile_id"]],
                    profile=profile,
                    scenario=scenario,
                    keep_state_bank=False,
                    arm_id=evaluation_arm,
                    seed=seed,
                )
                record.pop("state_rows", None)
                record["cell_id"] = cell_id
                record["parent_arm"] = arm
                record["checkpoint_sha256"] = checkpoint_sha
                profile_records.append(record)
                records.append(record)
            summary = summarise_profile(profile_records, contract=R425.build_contract())
            summary.update(
                {
                    "cell_id": cell_id,
                    "parent_arm": arm,
                    "training_seed": seed,
                }
            )
            summaries.append(summary)
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "cell_id": cell_id,
        "arm": arm,
        "seed": seed,
        "checkpoint_sha256": checkpoint_sha,
        "records": records,
        "summaries": summaries,
        "trajectory_count": len(records),
        "transition_count": sum(len(row["steps"]) for row in records),
        "all_completed": all(row["completed"] for row in records),
    }
    digest = _write_new_json(_eval_path(cell_id, arm, seed), payload)
    return json.dumps({"shard_id": shard_id, "sha256": digest}, sort_keys=True)


def _read_parent_profile_records(
    arm: str, seed: int | None, profile_id: str
) -> list[dict[str, Any]]:
    folder = "deterministic" if seed is None else f"seed{seed}"
    path = PARENT_OUT / "eval" / arm / folder / f"{profile_id}.json"
    return list(_read_hashed_json(path)["records"])


def _parent_summaries() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = R425.build_contract()
    profile_ids = [row["profile_id"] for row in _profile_rows("evaluation")]
    deterministic_arm = str(contract["deterministic_arm_id"])
    deterministic = {
        profile_id: summarise_profile(
            _read_parent_profile_records(deterministic_arm, None, profile_id),
            contract=contract,
        )
        for profile_id in profile_ids
    }
    parents = {
        f"{arm}|{seed}|{profile_id}": summarise_profile(
            _read_parent_profile_records(arm, seed, profile_id), contract=contract
        )
        for arm in ARMS
        for seed in SEEDS
        for profile_id in profile_ids
    }
    return deterministic, parents


def guard_checks(candidate: Mapping[str, Any], reference: Mapping[str, Any]) -> dict[str, bool]:
    thresholds = build_contract()["guard_thresholds"]
    return {
        "common_frequency_no_harm": float(candidate["common_frequency_iae_hz_s"])
        <= 1.03 * float(reference["common_frequency_iae_hz_s"]) + 1.0e-15,
        "worst_peak_no_harm": float(candidate["worst_unit_peak_hz"])
        <= 1.03 * float(reference["worst_unit_peak_hz"]) + 1.0e-15,
        "rocof_no_harm": float(candidate["worst_rocof_hz_s"])
        <= 1.03 * float(reference["worst_rocof_hz_s"]) + 1.0e-15,
        "action_rms_no_harm": float(candidate["action_rms"])
        <= 1.10 * float(reference["action_rms"]) + 1.0e-15,
        "action_variation_no_harm": float(candidate["action_total_variation"])
        <= 1.10 * float(reference["action_total_variation"]) + 1.0e-15,
        "saturation_budget": float(candidate["action_saturation_fraction"])
        <= float(thresholds["maximum_action_saturation_fraction"]),
        "nonconstant_action": float(candidate["minimum_record_total_variation"])
        > float(thresholds["nonconstant_action_variation_floor"]),
        "independent_per_vsg_action": float(candidate["minimum_record_action_row_dispersion"])
        > float(thresholds["independent_action_dispersion_floor"]),
    }


def _aggregate_metric(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    return float(sum(float(row[key]) for row in rows))


def _relative_improvement(baseline: float, candidate: float) -> float:
    return float((baseline - candidate) / max(abs(baseline), 1.0e-12))


def _step_zero_gradient(payload: Mapping[str, Any], constraint: str) -> dict[str, float]:
    actors = payload["gradient_trace"][0]["actors"]
    value_norms = np.asarray([row["gradient_norms"]["value"] for row in actors], dtype=float)
    weighted_norms = np.asarray(
        [row["gradient_norms"][f"{constraint}_weighted"] for row in actors], dtype=float
    )
    cosines = np.asarray(
        [row["gradient_cosines"][f"value_vs_{constraint}_weighted"] for row in actors],
        dtype=float,
    )
    return {
        "value_norm_median": float(np.median(value_norms)),
        "weighted_norm_median": float(np.median(weighted_norms)),
        "weighted_to_value_ratio_median": float(
            np.median(weighted_norms / np.maximum(value_norms, 1.0e-20))
        ),
        "cosine_median": float(np.median(cosines)),
        "projection_active_fraction_median": float(
            np.median([row["projection_active_fraction"] for row in actors])
        ),
    }


def _mechanism_analysis(
    interventions: Mapping[str, Mapping[str, Any]],
    evaluations: Mapping[str, Mapping[str, Any]],
    parents: Mapping[str, Mapping[str, Any]],
    guards: Mapping[str, Mapping[str, bool]],
) -> dict[str, Any]:
    pairs = [(arm, seed) for arm in ARMS for seed in SEEDS]
    constraints = ("rms", "tv")
    ceiling = {}
    for constraint in constraints:
        pair_rows = []
        for arm, seed in pairs:
            low = interventions[f"U10_eta050|{arm}|{seed}"]
            high = interventions[f"U100_eta050|{arm}|{seed}"]
            low_final = float(low["dual_replay"][constraint]["final"])
            high_final = float(high["dual_replay"][constraint]["final"])
            low_gradient = _step_zero_gradient(low, constraint)
            high_gradient = _step_zero_gradient(high, constraint)
            residual_key = f"{constraint}_residual_mean"
            low_residual = float(low["fixed_residual_after"]["profile_balanced_mean"][residual_key])
            high_residual = float(
                high["fixed_residual_after"]["profile_balanced_mean"][residual_key]
            )
            metric_key = "action_rms" if constraint == "rms" else "action_total_variation"
            low_eval = evaluations[f"U10_eta050|{arm}|{seed}"]["summaries"]
            high_eval = evaluations[f"U100_eta050|{arm}|{seed}"]["summaries"]
            low_metric = _aggregate_metric(low_eval, metric_key)
            high_metric = _aggregate_metric(high_eval, metric_key)
            pair_rows.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "low_final_mu": low_final,
                    "high_final_mu": high_final,
                    "multiplier_above_10": high_final > 10.0 + 1.0e-12,
                    "gradient_norm_ratio": high_gradient["weighted_norm_median"]
                    / max(low_gradient["weighted_norm_median"], 1.0e-20),
                    "fixed_residual_improvement": _relative_improvement(
                        low_residual, high_residual
                    ),
                    "physical_stress_improvement": _relative_improvement(low_metric, high_metric),
                }
            )
        counts = {
            "multiplier": sum(row["multiplier_above_10"] for row in pair_rows),
            "gradient": sum(row["gradient_norm_ratio"] >= 1.10 for row in pair_rows),
            "fixed": sum(row["fixed_residual_improvement"] >= 0.05 for row in pair_rows),
            "physical": sum(row["physical_stress_improvement"] >= 0.05 for row in pair_rows),
        }
        ceiling[constraint] = {
            "pairs": pair_rows,
            "support_counts": counts,
            "supported": counts["multiplier"] >= 5
            and counts["gradient"] >= 4
            and counts["fixed"] >= 4
            and counts["physical"] >= 4,
        }

    step_pairs = []
    for arm, seed in pairs:
        u10_fast = interventions[f"U10_eta050|{arm}|{seed}"]
        u10_slow = interventions[f"U10_eta005|{arm}|{seed}"]
        u100_fast = interventions[f"U100_eta050|{arm}|{seed}"]
        u100_slow = interventions[f"U100_eta005|{arm}|{seed}"]
        step_pairs.append(
            {
                "arm": arm,
                "seed": seed,
                "u10_identical": all(
                    np.isclose(
                        float(u10_fast["dual_replay"][name]["final"]),
                        float(u10_slow["dual_replay"][name]["final"]),
                        rtol=0.0,
                        atol=1.0e-12,
                    )
                    for name in constraints
                ),
                "u100_fast_farther": all(
                    float(u100_fast["dual_replay"][name]["final"])
                    > float(u100_slow["dual_replay"][name]["final"]) + 1.0e-12
                    for name in constraints
                ),
            }
        )

    gradient_conflict = {}
    primal_nonresponse = {}
    for constraint in constraints:
        conflict_rows = []
        nonresponse_rows = []
        for arm, seed in pairs:
            payload = interventions[f"U100_eta050|{arm}|{seed}"]
            gradient = _step_zero_gradient(payload, constraint)
            residual_key = f"{constraint}_residual_mean"
            before = float(payload["fixed_residual_before"]["profile_balanced_mean"][residual_key])
            after = float(payload["fixed_residual_after"]["profile_balanced_mean"][residual_key])
            improvement = _relative_improvement(before, after)
            conflict_rows.append(
                {
                    "arm": arm,
                    "seed": seed,
                    **gradient,
                    "meets": gradient["cosine_median"] <= -0.25
                    and gradient["weighted_to_value_ratio_median"] >= 0.10,
                }
            )
            nonresponse_rows.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "gradient_material": gradient["weighted_to_value_ratio_median"] >= 0.10,
                    "action_relative_delta": float(payload["action_relative_rms_delta"]),
                    "fixed_residual_improvement": improvement,
                    "projection_active_fraction": gradient["projection_active_fraction_median"],
                    "meets": gradient["weighted_to_value_ratio_median"] >= 0.10
                    and float(payload["action_relative_rms_delta"]) < 1.0e-3
                    and improvement < 0.01,
                }
            )
        gradient_conflict[constraint] = {
            "pairs": conflict_rows,
            "support_count": sum(row["meets"] for row in conflict_rows),
            "supported": sum(row["meets"] for row in conflict_rows) >= 4,
        }
        primal_nonresponse[constraint] = {
            "pairs": nonresponse_rows,
            "support_count": sum(row["meets"] for row in nonresponse_rows),
            "supported": sum(row["meets"] for row in nonresponse_rows) >= 4,
            "projection_suppressed_count": sum(
                row["meets"] and row["projection_active_fraction"] < 0.10
                for row in nonresponse_rows
            ),
        }

    aggregation_rows = []
    for arm, seed in pairs:
        aggregate = interventions[f"U100_eta050|{arm}|{seed}"]
        profile = interventions[f"profile_U100_eta050|{arm}|{seed}"]
        aggregate_eval = evaluations[f"U100_eta050|{arm}|{seed}"]["summaries"]
        profile_eval = evaluations[f"profile_U100_eta050|{arm}|{seed}"]["summaries"]
        fixed_improvements = []
        physical_improvements = []
        for profile_id in build_contract()["development_profiles"]:
            aggregate_worst = max(
                float(aggregate["fixed_residual_after"][profile_id]["rms_residual_mean"]),
                float(aggregate["fixed_residual_after"][profile_id]["tv_residual_mean"]),
            )
            profile_worst = max(
                float(profile["fixed_residual_after"][profile_id]["rms_residual_mean"]),
                float(profile["fixed_residual_after"][profile_id]["tv_residual_mean"]),
            )
            fixed_improvements.append(_relative_improvement(aggregate_worst, profile_worst))
        for aggregate_row, profile_row in zip(aggregate_eval, profile_eval):
            aggregate_stress = max(
                float(aggregate_row["action_rms"]),
                float(aggregate_row["action_total_variation"]),
            )
            profile_stress = max(
                float(profile_row["action_rms"]),
                float(profile_row["action_total_variation"]),
            )
            physical_improvements.append(_relative_improvement(aggregate_stress, profile_stress))
        aggregate_endpoint = sum(
            _aggregate_metric(aggregate_eval, key)
            for key in ("off_diagonal_response_energy", "disturbance_differential_energy")
        )
        profile_endpoint = sum(
            _aggregate_metric(profile_eval, key)
            for key in ("off_diagonal_response_energy", "disturbance_differential_energy")
        )
        aggregate_common = _aggregate_metric(aggregate_eval, "common_frequency_iae_hz_s")
        profile_common = _aggregate_metric(profile_eval, "common_frequency_iae_hz_s")
        row = {
            "arm": arm,
            "seed": seed,
            "worst_profile_fixed_improvement": float(min(fixed_improvements)),
            "worst_profile_physical_improvement": float(min(physical_improvements)),
            "endpoint_harm": float(profile_endpoint / max(aggregate_endpoint, 1.0e-20) - 1.0),
            "common_harm": float(profile_common / max(aggregate_common, 1.0e-20) - 1.0),
        }
        row["meets"] = bool(
            row["worst_profile_fixed_improvement"] >= 0.05
            and row["worst_profile_physical_improvement"] >= 0.05
            and row["endpoint_harm"] <= 0.03
            and row["common_harm"] <= 0.03
        )
        aggregation_rows.append(row)

    feasible = []
    for cell in CELLS:
        for arm in ARMS:
            passing_seeds = []
            for seed in SEEDS:
                profile_keys = [
                    f"{cell['cell_id']}|{arm}|{seed}|{profile_id}"
                    for profile_id in build_contract()["evaluation_profiles"]
                ]
                all_guards = all(all(guards[key].values()) for key in profile_keys)
                candidate = evaluations[f"{cell['cell_id']}|{arm}|{seed}"]["summaries"]
                parent = [
                    parents[f"{arm}|{seed}|{profile_id}"]
                    for profile_id in build_contract()["evaluation_profiles"]
                ]
                endpoints_no_worse = all(
                    _aggregate_metric(candidate, endpoint)
                    <= _aggregate_metric(parent, endpoint) + 1.0e-15
                    for endpoint in (
                        "off_diagonal_response_energy",
                        "disturbance_differential_energy",
                    )
                )
                if all_guards and endpoints_no_worse:
                    passing_seeds.append(seed)
            feasible.append(
                {
                    "cell": cell["cell_id"],
                    "arm": arm,
                    "passing_seeds": passing_seeds,
                    "supported": len(passing_seeds) >= 2,
                }
            )

    tags = []
    if any(value["supported"] for value in ceiling.values()):
        tags.append("CEILING-LIMITED-LOCAL")
    if all(row["u10_identical"] and row["u100_fast_farther"] for row in step_pairs):
        tags.append("STEP-CONTROLS-TRANSIT")
    if any(value["supported"] for value in gradient_conflict.values()):
        tags.append("GRADIENT-CONFLICT")
    if any(value["supported"] for value in primal_nonresponse.values()):
        tags.append("PRIMAL-NONRESPONSE-LOCAL")
    if sum(row["meets"] for row in aggregation_rows) >= 4:
        tags.append("AGGREGATION-MASK-LOCAL")
    if any(row["supported"] for row in feasible):
        tags.append("TESTED-CELL-GUARD-FEASIBLE")
    if not tags:
        tags.append("M1-DEEP-CAUSE-INCONCLUSIVE")
    return {
        "tags": tags,
        "ceiling": ceiling,
        "step": {
            "pairs": step_pairs,
            "supported": all(
                row["u10_identical"] and row["u100_fast_farther"] for row in step_pairs
            ),
        },
        "gradient_conflict": gradient_conflict,
        "primal_nonresponse": primal_nonresponse,
        "aggregation": {
            "pairs": aggregation_rows,
            "support_count": sum(row["meets"] for row in aggregation_rows),
            "supported": sum(row["meets"] for row in aggregation_rows) >= 4,
        },
        "tested_cell_guard_feasible": feasible,
    }


def aggregate() -> str:
    _assert_wsl_scratch()
    seal = load_seal()
    interventions = {
        f"{cell['cell_id']}|{arm}|{seed}": _read_hashed_json(
            _intervention_path(str(cell["cell_id"]), arm, seed)
        )
        for cell in CELLS
        for arm in ARMS
        for seed in SEEDS
    }
    evaluations = {
        f"{cell['cell_id']}|{arm}|{seed}": _read_hashed_json(
            _eval_path(str(cell["cell_id"]), arm, seed)
        )
        for cell in CELLS
        for arm in ARMS
        for seed in SEEDS
    }
    deterministic, parents = _parent_summaries()
    invalid_reasons = []
    if len(interventions) != 30 or len(evaluations) != 30:
        invalid_reasons.append("wrong intervention/evaluation inventory")
    if any(not row["all_completed"] for row in evaluations.values()):
        invalid_reasons.append("incomplete physical evaluation")
    if any(
        row["trajectory_count"] != 24 or row["transition_count"] != 720
        for row in evaluations.values()
    ):
        invalid_reasons.append("wrong evaluation trajectory/transition count")
    if any(
        not all(row["frozen_networks_unchanged"].values()) or not row["parent_checkpoint_immutable"]
        for row in interventions.values()
    ):
        invalid_reasons.append("frozen network or parent checkpoint drift")
    if any(
        not all(value["all_match"] for value in row["parent_tail_audit"].values())
        for row in interventions.values()
    ):
        invalid_reasons.append("parent tail update-law mismatch")
    algebra = {
        "positive_at_ceiling_persists": projected_dual_step(10.0, 1.0, eta=0.05, ceiling=10.0)
        == 10.0,
        "zero_at_ceiling_persists": projected_dual_step(10.0, 0.0, eta=0.05, ceiling=10.0) == 10.0,
        "negative_at_ceiling_releases": projected_dual_step(10.0, -1.0, eta=0.05, ceiling=10.0)
        < 10.0,
    }
    if not all(algebra.values()):
        invalid_reasons.append("ceiling-release algebra failure")
    candidate_summaries = [
        summary for payload in evaluations.values() for summary in payload["summaries"]
    ]
    if len(candidate_summaries) != 120 or any(
        not summary["valid"] for summary in candidate_summaries
    ):
        invalid_reasons.append("invalid/incomplete summary bank")
    guards = {}
    for summary in candidate_summaries:
        key = (
            f"{summary['cell_id']}|{summary['parent_arm']}|"
            f"{summary['training_seed']}|{summary['profile_id']}"
        )
        guards[key] = guard_checks(summary, deterministic[str(summary["profile_id"])])
    mechanisms = (
        {"tags": ["CANARY-INVALID"]}
        if invalid_reasons
        else _mechanism_analysis(interventions, evaluations, parents, guards)
    )
    inventory_after = _checkpoint_inventory()
    sealed_inventory = {
        (row["arm"], int(row["seed"])): row["sha256"] for row in seal["checkpoints"]
    }
    if any(
        row["sha256"] != sealed_inventory[(row["arm"], int(row["seed"]))] for row in inventory_after
    ):
        invalid_reasons.append("parent checkpoint inventory drifted from seal")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "valid": not invalid_reasons,
        "classification": "CANARY-INVALID" if invalid_reasons else mechanisms["tags"],
        "invalid_reasons": invalid_reasons,
        "ceiling_update_law": algebra,
        "state_shards": 6,
        "state_trajectories": 144,
        "state_transitions": 4320,
        "intervention_cells": len(interventions),
        "evaluation_shards": len(evaluations),
        "evaluation_trajectories": sum(row["trajectory_count"] for row in evaluations.values()),
        "evaluation_transitions": sum(row["transition_count"] for row in evaluations.values()),
        "guard_checks": guards,
        "guard_failure_counts": {
            name: sum(not row[name] for row in guards.values())
            for name in next(iter(guards.values()))
        },
        "mechanisms": mechanisms,
        "scope": "R425 checkpoint-local fresh-Adam frozen-critic fixed-bank diagnostic",
        "evidence_boundary": (
            "not original optimizer/replay training reproduction; not KKT, global feasibility, "
            "or policy-class infeasibility evidence"
        ),
    }
    json.dumps(payload, allow_nan=False)
    digest = _write_new_json(OUT / "formal_analysis.json", payload)
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_analysis_sha256": digest,
        "contract_sha256": contract_sha256(),
        "source_seal_sha256": _sha256_file(SEAL),
        "state_artifacts": [
            {
                "path": _relative(_state_path(arm, seed)),
                "sha256": _sha256_file(_state_path(arm, seed)),
            }
            for arm in ARMS
            for seed in SEEDS
        ],
        "intervention_artifacts": [
            {
                "path": _relative(_intervention_path(str(cell["cell_id"]), arm, seed)),
                "sha256": _sha256_file(_intervention_path(str(cell["cell_id"]), arm, seed)),
                "checkpoint_path": _relative(
                    _intervention_checkpoint_path(str(cell["cell_id"]), arm, seed)
                ),
                "checkpoint_sha256": _sha256_file(
                    _intervention_checkpoint_path(str(cell["cell_id"]), arm, seed)
                ),
            }
            for cell in CELLS
            for arm in ARMS
            for seed in SEEDS
        ],
        "evaluation_artifacts": [
            {
                "path": _relative(_eval_path(str(cell["cell_id"]), arm, seed)),
                "sha256": _sha256_file(_eval_path(str(cell["cell_id"]), arm, seed)),
            }
            for cell in CELLS
            for arm in ARMS
            for seed in SEEDS
        ],
    }
    manifest_sha = _write_new_json(OUT / "formal_manifest.json", manifest)
    return json.dumps(
        {
            "formal_analysis_sha256": digest,
            "formal_manifest_sha256": manifest_sha,
            "valid": payload["valid"],
            "classification": payload["classification"],
        },
        indent=2,
        sort_keys=True,
    )


def _capacity_job(job_id: int) -> dict[str, Any]:
    arm, seed = ARMS[0], SEEDS[0]
    _seed_everything(seed)
    agent = R425._agent_for(arm, "cpu")
    agent.load(_checkpoint_path(arm, seed))
    profile = _profile_rows("development")[job_id % 4]
    scenario = profile["scenarios"][job_id % 6]
    env = R425._build_env(profile)
    try:
        row = _run_policy_trajectory(
            agent=agent,
            env=env,
            profile=profile,
            scenario=scenario,
            keep_state_bank=False,
            arm_id=arm,
            seed=seed,
        )
    finally:
        try:
            env.close()
        except Exception:
            pass
    return {"completed": row["completed"], "steps": row["completed_steps"]}


def _meminfo() -> dict[str, int]:
    result = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, value = line.split(":", 1)
        result[key] = int(value.strip().split()[0]) * 1024
    return result


def measure_capacity() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    mem = _meminfo()
    other = R425._other_research_python_processes()
    rungs = []
    selected = 0
    previous_throughput = None
    accepting = True
    for workers in CAPACITY_RUNGS:
        memory_safe = workers * WORKER_RSS_FLOOR_BYTES + OS_FLOOR_BYTES <= mem["MemAvailable"]
        started = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_capacity_job, range(CAPACITY_TASKS)))
        wall = time.monotonic() - started
        throughput = len(rows) / max(wall, 1.0e-12)
        gain = None if previous_throughput is None else throughput / previous_throughput
        accepted = bool(
            accepting
            and memory_safe
            and all(row["completed"] and row["steps"] == 30 for row in rows)
            and (gain is None or gain >= 1.05)
        )
        if accepted:
            selected = workers
            previous_throughput = throughput
        else:
            accepting = False
        rungs.append(
            {
                "workers": workers,
                "trajectories": len(rows),
                "wall_seconds": wall,
                "throughput_trajectories_per_second": throughput,
                "marginal_gain": gain,
                "memory_safe": memory_safe,
                "all_valid": all(row["completed"] and row["steps"] == 30 for row in rows),
                "accepted": accepted,
            }
        )
    selected_row = next(row for row in rungs if row["workers"] == selected)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "authority": checks,
        "rungs": rungs,
        "tasks_per_rung": CAPACITY_TASKS,
        "selected_workers": selected,
        "worker_rss_floor_bytes": WORKER_RSS_FLOOR_BYTES,
        "os_floor_bytes": OS_FLOOR_BYTES,
        "wsl_mem_total_bytes": mem["MemTotal"],
        "wsl_mem_available_bytes": mem["MemAvailable"],
        "other_python_processes": other,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "native_threads_per_process": 1,
        "estimated_formal_seconds": 864
        / max(selected_row["throughput_trajectories_per_second"], 1.0e-12),
        "readiness": "RUN-READY" if selected > 0 and not other else "LOAD-CHECK-REVIEW",
    }
    digest = _write_new_json(CAPACITY, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def rehearsal() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    arm, seed = ARMS[1], SEEDS[0]
    checkpoint = _checkpoint_path(arm, seed)
    checkpoint_before = _sha256_file(checkpoint)
    _seed_everything(seed)
    agent = R425._agent_for(arm, "cpu")
    agent.load(checkpoint)
    profile = _profile_rows("development")[0]
    env = R425._build_env(profile)
    try:
        trajectory = _run_policy_trajectory(
            agent=agent,
            env=env,
            profile=profile,
            scenario=profile["scenarios"][0],
            keep_state_bank=True,
            arm_id=arm,
            seed=seed,
        )
    finally:
        try:
            env.close()
        except Exception:
            pass
    reference = _read_hashed_json(PARENT_OUT / "reference_action_stats.json")
    actions = np.asarray(
        [row["executed_action"] for row in trajectory["state_rows"]], dtype=float
    ).reshape(-1, 4, 2)
    previous = np.asarray(
        [row["previous_action"] for row in trajectory["state_rows"]], dtype=float
    ).reshape(-1, 4, 2)
    rms, tv = _episode_residuals(
        actions, previous, profile_id=profile["profile_id"], reference=reference
    )
    observations = np.asarray(
        [row["joint_observation"] for row in trajectory["state_rows"]], dtype=np.float32
    )
    previous_flat = previous.reshape(-1, 8).astype(np.float32)
    diagnostic = fixed_bank_actor_intervention(
        agent,
        observations=observations,
        previous_actions=previous_flat,
        profile_labels=[profile["profile_id"]] * len(observations),
        mu_rms=10.0,
        mu_tv=10.0,
        actor_lr=float(build_contract()["actor_lr"]),
        update_steps=1,
    )
    with tempfile.TemporaryDirectory(prefix="r455-rehearsal-") as folder:
        path = Path(folder) / "roundtrip.pt"
        agent.save(path)
        clone = R425._agent_for(arm, "cpu")
        clone.load(path)
        roundtrip_ok = all(
            torch.equal(left, right)
            for left_actor, right_actor in zip(agent.actors, clone.actors)
            for left, right in zip(left_actor.parameters(), right_actor.parameters())
        )
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_authority": False,
        "training_executed": False,
        "authority": checks,
        "runtime": installed_runtime(),
        "trajectory_completed": trajectory["completed"],
        "trajectory_steps": trajectory["completed_steps"],
        "residuals": {"rms": rms, "tv": tv},
        "ceiling_law": {
            "positive_persists": projected_dual_step(10.0, 1.0, eta=0.05, ceiling=10.0) == 10.0,
            "negative_releases": projected_dual_step(10.0, -1.0, eta=0.05, ceiling=10.0) < 10.0,
        },
        "gradient_finite": bool(
            np.all(
                np.isfinite(
                    [
                        value
                        for actor_row in diagnostic["trace"][0]["actors"]
                        for value in actor_row["gradient_norms"].values()
                    ]
                )
            )
        ),
        "fresh_update_finite": bool(np.isfinite(diagnostic["action_relative_rms_delta"])),
        "frozen_networks_unchanged": diagnostic["frozen_networks_unchanged"],
        "save_load_roundtrip": roundtrip_ok,
        "checkpoint_immutable": checkpoint_before == _sha256_file(checkpoint),
    }
    payload["passed"] = bool(
        all(checks.values())
        and payload["trajectory_completed"]
        and payload["trajectory_steps"] == 30
        and all(payload["ceiling_law"].values())
        and payload["gradient_finite"]
        and payload["fresh_update_finite"]
        and all(payload["frozen_networks_unchanged"].values())
        and payload["save_load_roundtrip"]
        and payload["checkpoint_immutable"]
    )
    digest = _write_new_json(REHEARSAL, payload)
    return json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True)


def prepare() -> str:
    _assert_wsl_scratch()
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity not RUN-READY: {capacity.get('readiness')}")
    selected = int(capacity["selected_workers"])
    sources = {
        "runner": Path(__file__).resolve(),
        "diagnostic_module": ROOT / "src/andes_rl_kundur/agents/cd_matd3_dual_factorial.py",
        "runner_tests": ROOT / "tests/test_run_r455_m1_dual_saturation.py",
        "module_tests": ROOT / "tests/test_cd_matd3_dual_factorial.py",
        "parent_runner": ROOT / "scripts/run_r425_guard_constraints_signfix.py",
        "parent_learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3_guard_constraints_vfix.py",
        "base_learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "summariser": ROOT / "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    }
    parent_paths = [
        PARENT_OUT / "reference_action_stats.json",
        PARENT_OUT / "formal_analysis.json",
        *[
            PARENT_OUT / "train" / arm / f"seed{seed}" / "manifest.json"
            for arm in ARMS
            for seed in SEEDS
        ],
        *[
            PARENT_OUT
            / "eval"
            / str(R425.build_contract()["deterministic_arm_id"])
            / "deterministic"
            / f"{profile_id}.json"
            for profile_id in build_contract()["evaluation_profiles"]
        ],
        *[
            PARENT_OUT / "eval" / arm / f"seed{seed}" / f"{profile_id}.json"
            for arm in ARMS
            for seed in SEEDS
            for profile_id in build_contract()["evaluation_profiles"]
        ],
    ]
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "capacity_sha256": _sha256_file(CAPACITY),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "authority": checks,
        "runtime": rehearsal_payload["runtime"],
        "launch": {
            "host_process_budget": selected + 1,
            "wsl_python_processes": selected + 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "state_shards": len(state_shard_ids()),
            "intervention_cells": len(eval_shard_ids()),
            "evaluation_shards": len(eval_shard_ids()),
        },
        "sources": {
            name: {"path": _relative(path), "sha256": _sha256_file(path)}
            for name, path in sources.items()
        },
        "checkpoints": _checkpoint_inventory(),
        "parent_inputs": [
            {"path": _relative(path), "sha256": _verify_sidecar(path)} for path in parent_paths
        ],
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    STATE_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    STATE_SHARDS.write_text(json.dumps(state_shard_ids()) + "\n", encoding="utf-8")
    return json.dumps(
        {
            "seal_sha256": digest,
            "selected_workers": selected,
            "state_shards": len(state_shard_ids()),
            "evaluation_shards": len(eval_shard_ids()),
        },
        indent=2,
        sort_keys=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "capacity",
            "rehearse",
            "prepare",
            "seal",
            "state-shards",
            "state-shard",
            "intervene",
            "eval-shards",
            "eval-shard",
            "aggregate",
        ),
    )
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "capacity":
        print(measure_capacity(), flush=True)
    elif args.command == "rehearse":
        print(rehearsal(), flush=True)
    elif args.command in ("prepare", "seal"):
        print(prepare(), flush=True)
    elif args.command == "state-shards":
        print(json.dumps(state_shard_ids()), flush=True)
    elif args.command == "eval-shards":
        print(json.dumps(eval_shard_ids()), flush=True)
    elif args.command == "intervene":
        print(intervene(), flush=True)
    elif args.command == "aggregate":
        print(aggregate(), flush=True)
    elif args.command == "state-shard":
        if args.shard_id is None:
            raise SystemExit("state-shard requires an id")
        print(run_state_shard(args.shard_id), flush=True)
    else:
        if args.shard_id is None:
            raise SystemExit("eval-shard requires an id")
        print(run_eval_shard(args.shard_id), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
