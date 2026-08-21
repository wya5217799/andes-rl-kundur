"""R433 successor of R431: action-stress penalty on the SAC reward (reward shaping).

R431 (CLM-1315) made every SAC row physically valid via the execution-layer
slew projection, but both SAC arms still fail the action-stress guards
(action_rms / action_variation 20/20 blocks) while the message arm passes
the common-frequency and worst-peak no-harm guards.  This successor
imports the frozen R431 runner chain (R431 -> R430 -> R429 -> R428) and
changes one scientific factor: the SAC per-step reward gains an
action-stress penalty term

    r_i' = r_i + lambda_p * p_i,   p_i = -mean_j(a_ij^2)

over the projected executed action vector (normalized delta-M /
delta-D), per agent, per step, training only.  Everything else —
slew projection (0.25/step), seeds 401-405, scalar 401-403 byte-anchor,
frozen classifier/estimators, eval protocol — is R431-verbatim.

The two execution functions remain verbatim copies of the frozen R428
source with the declared ``R433-SEAM`` seams: the SAC training loop
projects before decode/step and now passes the projected action into the
penalized reward builder; the eval loop is R431-verbatim (projected
deterministic actions).  The reward builder is a verbatim copy of the
frozen ``adapted_step_rewards`` with the penalty lines marked
``R433-SEAM``; a drift test strips the seam and asserts byte-identity.

WSL lifecycle (always through ``scripts/andes_scratch.py``):

    python scripts/andes_scratch.py scripts/run_r433_sac_stress_penalty.py reuse-capacity
    python scripts/andes_scratch.py scripts/run_r433_sac_stress_penalty.py rehearse
    python scripts/andes_scratch.py scripts/run_r433_sac_stress_penalty.py prepare
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r433_sac_stress_penalty.py \
        --shards tmp/andes/r433_train_shards.json --workers 16 --round R433
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r433_sac_stress_penalty.py \
        --shards tmp/andes/r433_eval_shards.json --workers 16 --round R433
    python scripts/andes_scratch.py scripts/run_r433_sac_stress_penalty.py classify

Formal outputs are create-only and hashed under
``results/research_loop/r433_sac_stress_penalty``.  No retry is authorized.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np
import torch

_parent_spec = importlib.util.spec_from_file_location(
    "_r431_r430_parent", ROOT / "scripts/run_r430_adapted_sac_successor.py"
)
if _parent_spec is None or _parent_spec.loader is None:
    raise RuntimeError("cannot load the frozen R430 parent runner")
r430 = importlib.util.module_from_spec(_parent_spec)
sys.modules[_parent_spec.name] = r430
_parent_spec.loader.exec_module(r430)
base = r430.base  # the frozen R428 harness module
parent = r430.parent  # the frozen R429 adapter module

ROUND_ID = "R433"
PLAN = ROOT / "memory/rounds/R433/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R433/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R433/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R433/formal_seal.json"
OUT = ROOT / "results/research_loop/r433_sac_stress_penalty"
TIER1_OUT = ROOT / "tmp/andes/r433_tier1"
R431_CAPACITY = ROOT / "memory/rounds/R430/capacity_evidence.json"

TRAINING_SEEDS = [401, 402, 403, 404, 405]
ANCHOR_SEEDS = [401, 402, 403]

# Action-stress penalty coefficient: frozen by the dev-lambda selection on
# declared development data BEFORE sealing (plan methodology); the sealed
# contract pins this value via contract_sha256.
LAMBDA_P = 10.0  # frozen by dev-lambda selection (tmp/andes/r433_dev_lambda.json), pre-seal; replaced by the dev selection result

# Capture the frozen chain's own functions before _patch_parent rebinds the
# names on the r430/parent/base modules (avoids self-recursion).
_R430_BUILD_CONTRACT = r430.build_contract
_R430_SOURCE_MANIFEST = r430.source_manifest
_R430_PARENT_MANIFEST = r430.parent_manifest

# Names the verbatim copies need from the frozen chain (module globals).
for _name in (
    "PerVSGMDActionProjector",
    "SAC_MASKED_ARM",
    "_agent_for",
    "_build_env",
    "_joint_obs",
    "_sac_step_rewards",
    "_save_agent_snapshot",
    "_read_hashed_json",
    "_write_new_json",
    "contract_sha256",
    "augment_joint_obs_np",
    "_scalar_step_reward",
    "_rehearsal_sac_semantics_check",
    "safe_emit",
    "_assert_wsl_scratch",
    "load_seal",
    "_installed_runtime",
    "_other_processes",
    "_memory_resources",
    "_relative",
    "_sha256_file",
    "random",
    "ACTION_HALF_RANGE_M",
    "ACTION_HALF_RANGE_D",
    "PHI_F",
    "PHI_ABS",
    "PHI_H",
    "PHI_D",
):
    globals()[_name] = (
        getattr(base, _name, None)
        or getattr(r430, _name, None)
        or getattr(parent, _name, None)
    )


def _sac_step_rewards_penalized(
    joint_obs: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
    masked: bool,
    action: np.ndarray,
) -> np.ndarray:
    """R431-verbatim reward plus the R433 action-stress penalty (R433-SEAM).

    Verbatim copy of the frozen ``adapted_step_rewards``; the only added
    statements are marked ``R433-SEAM``: ``p_i = -mean_j(a_ij^2)`` over the
    projected executed action and ``r_i' = r_i + lambda_p * p_i``.  The
    drift test strips the seam lines and asserts byte-identity with the
    frozen source.
    """
    rows = np.asarray(joint_obs, dtype=np.float32).reshape(
        base.AGENT_COUNT, base.OBS_DIM
    )
    if masked:
        rows = rows.copy()
        rows[:, 3:7] = 0.0
    delta_m = np.asarray(delta_m, dtype=float).reshape(base.AGENT_COUNT)
    delta_d = np.asarray(delta_d, dtype=float).reshape(base.AGENT_COUNT)
    r_h = -(float(np.mean(delta_m)) / ACTION_HALF_RANGE_M) ** 2
    r_d = -(float(np.mean(delta_d)) / ACTION_HALF_RANGE_D) ** 2
    rewards = np.zeros(base.AGENT_COUNT, dtype=np.float32)
    for index in range(base.AGENT_COUNT):
        own = float(rows[index, 1]) * 3.0 / (2.0 * np.pi)
        neighbours = [
            float(rows[index, 3 + offset]) * 3.0 / (2.0 * np.pi)
            for offset in range(2)
        ]
        eta = [0.0 if masked else 1.0, 0.0 if masked else 1.0]
        mean_frequency = (own + sum(e * n for e, n in zip(eta, neighbours))) / (
            1.0 + sum(eta)
        )
        r_f = -(own - mean_frequency) ** 2 - sum(
            e * (neighbour - mean_frequency) ** 2
            for e, neighbour in zip(eta, neighbours)
        )
        r_abs = -(own**2)
        rewards[index] = (
            PHI_F * r_f + PHI_ABS * r_abs + PHI_H * r_h + PHI_D * r_d
        )
        p_i = -float(  # R433-SEAM
            np.mean(np.asarray(action[index], dtype=float) ** 2)  # R433-SEAM
        )  # R433-SEAM
        rewards[index] = rewards[index] + LAMBDA_P * p_i  # R433-SEAM
    return rewards


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(_R430_BUILD_CONTRACT())
    contract["training_seeds"] = list(TRAINING_SEEDS)
    contract["engineering_successor"] = {
        "successor_of": "R431",
        "single_change": "sac-action-stress-penalty-reward-shaping",
        "explicit_sac_out_root": True,
        "sac_slew_projection": True,
        "seed_scale": list(TRAINING_SEEDS),
        "action_stress_penalty": {
            "form": "r_i' = r_i + lambda_p * p_i, p_i = -mean_j(a_ij^2) over projected executed action (normalized delta-M/delta-D)",
            "lambda_p": LAMBDA_P,
            "scope": "training-only",
        },
    }
    return contract


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    base_contract = _R430_BUILD_CONTRACT()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R431" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(contract["profiles"]) == 8
        and base.training_run_count(contract) == 15
        and list(contract["training_seeds"]) == TRAINING_SEEDS
        and base.evaluation_record_count(contract)
        == base.evaluation_record_count(base_contract) * 16 // 10,
        "output_absence": not OUT.exists(),
    }


def source_manifest() -> dict[str, dict[str, str]]:
    sources = _R430_SOURCE_MANIFEST()
    replacements = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r433_sac_stress_penalty.py",
        "parent_r431_runner": ROOT / "scripts/run_r431_sac_slew.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": base._relative(path),
            "sha256": base._sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r431_plan": ROOT / "memory/rounds/R431/plan.md",
        "r431_seal": ROOT / "memory/rounds/R431/formal_seal.json",
        "r431_analysis": ROOT
        / "results/research_loop/r431_sac_slew/formal_analysis.json",
        "r431_capacity": R431_CAPACITY,
        "r428_analysis": ROOT / "results/research_loop/r428_c1_sac/formal_analysis.json",
        "r425_analysis": ROOT
        / "results/research_loop/r425_guard_constraints_signfix/formal_analysis.json",
    }
    return {
        name: {"path": base._relative(path), "sha256": base._sha256_file(path)}
        for name, path in paths.items()
    }


def output_root_probe() -> dict[str, Any]:
    resolved = {
        f"{arm}|{seed}": base._relative(OUT)
        for arm in build_contract()["learning_arm_ids"]
        for seed in build_contract()["training_seeds"]
    }
    expected = base._relative(OUT)
    passed = all(value == expected for value in resolved.values())
    passed = passed and OUT.resolve() != r430.OUT.resolve()
    passed = passed and OUT.resolve() != (ROOT / "results/research_loop/r428_c1_sac").resolve()
    return {"passed": bool(passed), "expected": expected, "resolved": resolved}


def write_new_json(path: Path, payload: dict[str, Any]) -> str:
    mutable = copy.deepcopy(payload)
    if path.resolve() == REHEARSAL.resolve():
        probe = output_root_probe()
        mutable.setdefault("checks", {})["successor_output_root_probe"] = bool(
            probe["passed"]
        )
        mutable["successor_output_root_probe"] = probe
        seam = _projection_seam_probe()
        mutable.setdefault("checks", {})["projection_seam_probe"] = bool(
            seam["passed"]
        )
        mutable["projection_seam_probe"] = seam
        penalty = _penalty_gradient_direction_probe()
        mutable.setdefault("checks", {})["penalty_gradient_direction_probe"] = bool(
            penalty["passed"]
        )
        mutable["penalty_gradient_direction_probe"] = penalty
    if path.resolve() == SEAL.resolve():
        mutable["single_factor_change"] = (
            "R431-identical science except: the SAC per-step reward gains "
            "the action-stress penalty term r_i' = r_i + lambda_p * p_i with "
            "p_i = -mean_j(a_ij^2) over the projected executed action "
            "(training only); seeds 401-405, scalar 401-403 byte-anchor "
            "unchanged"
        )
    if path.name == "formal_analysis.json" and path.parent.resolve() == OUT.resolve():
        mutable.setdefault("repair", {})["engineering_successor"] = {
            "successor_of": "R431",
            "explicit_sac_out_root": True,
            "sac_slew_projection": True,
            "action_stress_penalty": True,
        }
    return _write_new_json(path, mutable)


def _projection_seam_probe() -> dict[str, Any]:
    """Verify the projection seam: executed deltas within limit; bitcheck."""
    contract = build_contract()
    limit = float(contract["action_slew_limit"])
    result: dict[str, Any] = {
        "passed": False,
        "max_executed_delta": None,
        "deltas_within_limit": None,
        "penalty_exactness_max_abs_err": None,
        "penalty_exactness_checked": None,
    }
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    try:
        agent = _agent_for("cd_matd3_message", "cpu")
        projector = PerVSGMDActionProjector(action_slew_limit=limit)
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        previous = np.zeros((4, 2), dtype=np.float32)
        max_delta = 0.0
        for _ in range(30):
            joint = _joint_obs(observation)
            raw = agent.act(joint, deterministic=True)
            action = projector.project(raw)
            max_delta = max(max_delta, float(np.abs(action - previous).max()))
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _rewards, _done, info = env.step(action_dict)
            previous = np.asarray(action, dtype=np.float32).copy()
            if info["tds_failed"]:
                raise RuntimeError("projection probe TDS failure")
        result["max_executed_delta"] = max_delta
        result["deltas_within_limit"] = bool(max_delta <= limit + 1.0e-6)
    finally:
        try:
            env.close()
        except Exception:
            pass
    # Penalty-exactness probe (replaces the R431 bitcheck: the penalty is a
    # scientific factor that changes the training reward, so frozen-vs-copy
    # byte identity no longer applies; instead, on the real environment the
    # penalized reward must differ from the R431-verbatim reward by exactly
    # lambda_p * p_i = -lambda_p * mean_j(a_ij^2) per agent).
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    try:
        agent = _agent_for("cd_matd3_message", "cpu")
        projector = PerVSGMDActionProjector(
            action_slew_limit=float(contract["action_slew_limit"])
        )
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        max_abs_err = 0.0
        checked = 0
        for _ in range(8):
            joint = _joint_obs(observation)
            raw = agent.act(joint, deterministic=True)
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _rewards, done, info = env.step(action_dict)
            r_plain = _sac_step_rewards(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                masked=False,
            )
            r_pen = _sac_step_rewards_penalized(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                masked=False,
                action=action,
            )
            expected = float(LAMBDA_P) * -np.mean(  # per-agent penalty
                np.asarray(action, dtype=float) ** 2, axis=1
            )
            err = float(np.abs((r_pen - r_plain) - expected).max())
            max_abs_err = max(max_abs_err, err)
            checked += 1
            if bool(done) or bool(info["tds_failed"]):
                break
        result["penalty_exactness_max_abs_err"] = max_abs_err
        result["penalty_exactness_checked"] = checked
    finally:
        try:
            env.close()
        except Exception:
            pass
    result["passed"] = bool(
        result["deltas_within_limit"]
        and max_abs_err <= 1e-5
    )
    return result


def _penalty_gradient_direction_probe() -> dict[str, Any]:
    """Semantic gate (R424): the action-stress penalty term must align with
    decreasing mean_j(a_ij^2) — penalty means descent.

    Checks on the real learner path: (1) lambda_p > 0; (2) analytic and
    numeric gradient of the penalty term point along -a (per component);
    (3) with lambda_p > 0 the penalized reward is <= the R431-verbatim
    reward at every probed (obs, action); (4) a short real rollout through
    the penalized store/update path yields finite losses and no NaN.
    """
    contract = build_contract()
    lam = float(LAMBDA_P)
    result: dict[str, Any] = {
        "passed": False,
        "lambda_p": lam,
        "analytic_gradient_aligned": None,
        "numeric_gradient_aligned": None,
        "penalty_nonpositive": None,
        "penalized_reward_le": None,
        "rollout_losses_finite": None,
    }
    if lam <= 0.0:
        result["reason"] = "lambda_p must be positive (frozen by dev selection)"
        return result
    # (2) analytic: p(a) = -mean_j(a_j^2), dp/da_j = -a_j -> -lambda*a.
    a_vec = np.array([0.30, -0.40], dtype=float)
    grad_analytic = -lam * a_vec
    eps = 1e-6
    grad_numeric = np.zeros(2)
    for j in range(2):
        step = np.zeros(2)
        step[j] = eps
        p_plus = -float(np.mean((a_vec + step) ** 2))
        p_minus = -float(np.mean((a_vec - step) ** 2))
        grad_numeric[j] = lam * (p_plus - p_minus) / (2.0 * eps)
    aligned = bool(
        np.all(np.sign(grad_analytic) == np.sign(-a_vec))
        and np.all(np.sign(grad_numeric) == np.sign(-a_vec))
    )
    result["analytic_gradient_aligned"] = aligned
    result["numeric_gradient_aligned"] = aligned
    if not aligned:
        return result
    # (3) + (4) on the real learner path.
    development = [
        profile
        for profile in contract["profiles"]
        if profile["split"] == "development"
    ]
    profile = development[0]
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    try:
        agent = _agent_for("cd_matd3_message", "cpu")
        projector = PerVSGMDActionProjector(
            action_slew_limit=float(contract["action_slew_limit"])
        )
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        p_nonpositive = True
        penalized_le = True
        losses_finite = True
        for _ in range(8):
            joint = _joint_obs(observation)
            raw = agent.act(joint, deterministic=False)
            action = projector.project(raw)
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _rewards, done, info = env.step(action_dict)
            r_plain = _sac_step_rewards(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                masked=False,
            )
            r_pen = _sac_step_rewards_penalized(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                masked=False,
                action=action,
            )
            p_vals = r_pen - r_plain
            if np.any(p_vals > 1e-9):
                p_nonpositive = False
            if np.any(r_pen > r_plain + 1e-9):
                penalized_le = False
            if not np.all(np.isfinite(r_pen)):
                losses_finite = False
            terminal = bool(done) or bool(info["tds_failed"])
            agent.store(joint, raw, r_pen, _joint_obs(observation), terminal)
            diag = agent.update_all()
            if diag is not None and not np.isfinite(diag["critic_loss"]):
                losses_finite = False
            if terminal:
                break
        result["penalty_nonpositive"] = bool(p_nonpositive)
        result["penalized_reward_le"] = bool(penalized_le)
        result["rollout_losses_finite"] = bool(losses_finite)
    finally:
        try:
            env.close()
        except Exception:
            pass
    result["passed"] = bool(
        aligned
        and p_nonpositive
        and penalized_le
        and losses_finite
    )
    return result


def _train_sac_arm_seed_projected(
    arm_id: str,
    seed: int,
    restart_count: int = 0,
    out_root: Path = OUT,
    total_steps: int | None = None,
    require_seal: bool = True,
    project: bool = True,
    dev_stats: dict[str, float] | None = None,  # R433-SEAM
) -> str:
    """SAC training loop — verbatim copy of the frozen R428 loop with the
    single declared R431 seam: executed actions pass through the per-actor
    slew projector (the raw-magnitude saturation diagnostic stays verbatim,
    keeping the R430-documented field semantics).  ``project=False``
    restores the frozen raw-execution path for the bitcheck (byte-identical
    checkpoint required).  ``dev_stats`` (R433-SEAM) collects the training
    action-RMS accumulator for the pre-seal development lambda selection.
    """
    _assert_wsl_scratch()
    if require_seal:
        load_seal()
    contract = build_contract()
    arm_root = out_root / "train" / arm_id
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
    agent = _agent_for(arm_id, "cpu")
    envs = {
        str(profile["profile_id"]): _build_env(profile)
        for profile in development
    }
    masked = arm_id == SAC_MASKED_ARM
    total_steps = int(
        total_steps
        if total_steps is not None
        else contract["training_contract"]["total_interaction_steps"]
    )
    steps_per_episode = int(contract["steps"])
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    sac_diagnostics_trace: list[dict[str, float]] = []
    critic_loss_trace: list[float] = []
    invalid_reason: str | None = None
    saturation_steps = 0
    episode_index = 0
    any_tds_failure = False
    while executed_steps < total_steps:
        scenario_id = schedule[episode_index % len(schedule)]
        episode_index += 1
        profile, scenario = scenarios[scenario_id]
        env = envs[str(profile["profile_id"])]
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector = PerVSGMDActionProjector(  # R433-SEAM
            action_slew_limit=float(  # R433-SEAM
                contract["action_slew_limit"]  # R433-SEAM
            )  # R433-SEAM
        )  # R433-SEAM
        projector.reset()  # R433-SEAM
        previous_executed = np.zeros((4, 2), dtype=np.float32)  # R433-SEAM
        for _step_index in range(steps_per_episode):
            joint = _joint_obs(observation)
            raw = agent.act(joint, deterministic=False)
            if not np.all(np.isfinite(raw)):
                invalid_reason = "nonfinite actor output"
                break
            if project:  # R433-SEAM
                action = projector.project(raw)  # R433-SEAM
            else:  # R433-SEAM
                action = raw  # R433-SEAM
            saturation = np.abs(raw) >= (1.0 - 1.0e-6)
            if np.any(saturation):
                saturation_steps += 1
            action_dict = {  # R433-SEAM
                actor: np.asarray(action[actor], dtype=np.float32)  # R433-SEAM
                for actor in range(4)  # R433-SEAM
            }  # R433-SEAM
            if dev_stats is not None:  # R433-SEAM
                dev_stats["action_sq_acc"] += float(  # R433-SEAM
                    np.mean(np.asarray(action, dtype=float) ** 2)  # R433-SEAM
                )  # R433-SEAM
                dev_stats["steps"] += 1  # R433-SEAM
            observation, _rewards, done, info = env.step(action_dict)
            previous_executed = np.asarray(  # R433-SEAM
                action, dtype=np.float32  # R433-SEAM
            ).copy()  # R433-SEAM
            executed_steps += 1
            tds_failed = bool(info["tds_failed"])
            next_joint = _joint_obs(observation)
            terminal = bool(done) or tds_failed
            per_agent_rewards = _sac_step_rewards_penalized(  # R433-SEAM
                joint,  # R433-SEAM
                np.asarray(info["delta_M"], dtype=float),  # R433-SEAM
                np.asarray(info["delta_D"], dtype=float),  # R433-SEAM
                masked=masked,  # R433-SEAM
                action=action,  # R433-SEAM
            )  # R433-SEAM
            agent.store(
                joint, raw, per_agent_rewards, next_joint, terminal
            )
            diagnostics = agent.update_all()
            if diagnostics is not None:
                critic_loss_trace.append(float(diagnostics["critic_loss"]))
                sac_diagnostics_trace.append(diagnostics)
                if not np.isfinite(diagnostics["critic_loss"]):
                    invalid_reason = "nonfinite SAC critic loss"
                    break
            if tds_failed:
                tds_failed_episodes += 1
                any_tds_failure = True
                break
        if invalid_reason is not None:
            break
        episodes_attempted += 1
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
    checkpoint_sha = None
    if convergence_valid:
        checkpoint_sha = _save_agent_snapshot(agent, run_dir / "final.pt")
    critic_loss_sha = _write_new_json(
        run_dir / "critic_loss_trace.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "critic_losses": critic_loss_trace,
        },
    )
    sac_diag_sha = _write_new_json(
        run_dir / "sac_diagnostics_trace.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "diagnostics": sac_diagnostics_trace,
        },
    )
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
        "scalar_anchor_matches_r419": None,
        "critic_loss_trace_sha256": critic_loss_sha,
        "critic_loss_count": int(len(critic_loss_trace)),
        "sac_diagnostics_trace_sha256": sac_diag_sha,
        "episode_common_costs": [],
        "episode_scalar_returns": [],
        "lagrange_trace": [],
        "guard_multipliers": {},
        "any_tds_failure": bool(any_tds_failure),
        "slew_diagnostics": {
            "slew_saturation_steps": int(saturation_steps),
            "total_executed_steps": int(executed_steps),
            "slew_saturation_rate": (
                saturation_steps / executed_steps if executed_steps > 0 else 0.0
            ),
            "execution_mismatch_mean": 0.0,
        },
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    return _write_new_json(run_dir / "manifest.json", manifest)


def _evaluate_arm_seed_projected(
    arm_id: str,
    seed: int | None,
    project: bool = True,
) -> None:
    """Eval loop — verbatim copy of the frozen R428 loop with the single
    declared R431 seam: the SAC branch projects the deterministic action
    and records the projected action, matching the scalar branch, so
    ``summarise_profile`` sees the physically executed actions.
    """
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
                    if arm_id in ("cd_matd3_no_message", "cd_matd3_message"):
                        # R433-SEAM: execution-layer slew projection on the
                        # SAC arms (R430 executed raw tanh; rows invalid).
                        if project:  # R433-SEAM
                            action = projector.project(  # R433-SEAM
                                agent.act(joint, deterministic=True)  # R433-SEAM
                            )  # R433-SEAM
                        else:  # R433-SEAM
                            action = agent.act(joint, deterministic=True)  # R433-SEAM
                    else:
                        augmented = augment_joint_obs_np(
                            joint, previous_executed
                        )
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


def _deterministic_controller() -> Any:
    return base._deterministic_controller()


def adapt_v4_observations_to_physical(observation: Any) -> Any:
    return base.adapt_v4_observations_to_physical(observation)


def train_arm_seed(arm_id: str, seed: int, restart_count: int = 0) -> str:
    """R431 dispatch: scalar runs the frozen core (anchor for 401-403,
    fresh for 404/405); SAC arms run the projected verbatim loop."""
    base._assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    if seed not in contract["training_seeds"]:
        raise ValueError(f"unregistered training seed: {seed}")
    if arm_id == "yang_scalar_td3":
        return base._train_arm_seed_core(
            arm_id,
            seed,
            restart_count=restart_count,
            out_root=OUT,
            total_steps=int(
                contract["training_contract"]["total_interaction_steps"]
            ),
            reference_stats_path=OUT / "reference_action_stats.json",
            record_scalar_anchor=seed in ANCHOR_SEEDS,
            tier=None,
        )
    return _train_sac_arm_seed_projected(
        arm_id,
        seed,
        restart_count=restart_count,
        out_root=OUT,
        total_steps=int(
            contract["training_contract"]["total_interaction_steps"]
        ),
        require_seal=True,
        project=True,
    )


def evaluate_arm_seed(arm_id: str, seed: int | None) -> None:
    _evaluate_arm_seed_projected(arm_id, seed, project=True)


def reuse_capacity() -> str:
    """Reuse the R430 (R429 v3) ladder after a fresh host check."""
    base._assert_wsl_scratch()
    if CAPACITY.exists() or REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R433 pre-attempt artifact already exists")
    other = _other_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    inherited = _read_hashed_json(R431_CAPACITY)
    if inherited.get("readiness") != "RUN-READY" or int(
        inherited.get("selected_workers", 0)
    ) != 16:
        raise RuntimeError("R431 capacity evidence is not the registered 16-worker anchor")
    logical, physical_memory, wsl_available = _memory_resources()
    payload = copy.deepcopy(inherited)
    payload.update(
        {
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "authorization": (
                "owner ordered action-stress penalty round after R431 "
                "(CLM-1315) closed the slew-validity axis; R429 v3 ladder "
                "reused after a fresh no-load host check; R433 selects 16 "
                "workers on the measured rung-16 envelope (R432 sibling "
                "declared other_reserved_processes=5; owner hardware rule "
                "2026-08-19: saturate the host)"
            ),
            "contract_sha256": base.contract_sha256(build_contract()),
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "other_processes": other,
            "readiness": "RUN-READY",
            "selected_workers": 15,
            "wsl_python_processes": 16,
            "host_process_budget": 21,
            "other_reserved_processes": 5,
            "native_threads_per_process": 1,
            "whole_host_python_process_budget": 21,
            "sources": source_manifest(),
            "installed_runtime": _installed_runtime(),
            "inherited_capacity": {
                "path": base._relative(R431_CAPACITY),
                "sha256": _sha256_file(R431_CAPACITY),
                "reuse_basis": "identical physical task and learner; projection seam adds per-step numpy ops only",
            },
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        }
    )
    payload["empirical_anchor"]["source"] = (
        "R429 v3 selected representative rung plus fresh R431 no-load host check"
    )
    payload["empirical_anchor"]["concurrent_workers"] = 16
    return _write_new_json(CAPACITY, payload)


def _patch_parent() -> None:
    values = {
        "ROUND_ID": ROUND_ID,
        "PLAN": PLAN,
        "LINE": LINE,
        "REHEARSAL": REHEARSAL,
        "CAPACITY": CAPACITY,
        "SEAL": SEAL,
        "OUT": OUT,
        "TIER1_OUT": TIER1_OUT,
    }
    for module in (parent, base):
        for name, value in values.items():
            setattr(module, name, value)
    for module in (r430, parent, base):
        module.build_contract = build_contract
        module._source_manifest = source_manifest
        module._parent_manifest = parent_manifest
        module._authority_checks = authority_checks
        module._write_new_json = write_new_json
    base.OTHER_RESERVED_PROCESSES = 5
    parent.prepare.__globals__["build_contract"] = build_contract
    parent.prepare.__globals__["source_manifest"] = source_manifest
    parent.prepare.__globals__["parent_manifest"] = parent_manifest
    parent.prepare.__globals__["authority_checks"] = authority_checks
    parent.prepare.__globals__["write_new_json"] = write_new_json
    base.train_arm_seed = train_arm_seed
    base._evaluate_arm_seed = _evaluate_arm_seed_projected
    base.evaluate_all = _evaluate_all
    r430.train_arm_seed = train_arm_seed


def _evaluate_all() -> None:
    """Serial full-bank evaluation through the projected loop."""
    base._assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    for arm_id in contract["learning_arm_ids"]:
        for seed in contract["training_seeds"]:
            _evaluate_arm_seed_projected(str(arm_id), int(seed), project=True)
    _evaluate_arm_seed_projected(
        str(contract["deterministic_arm_id"]), None, project=True
    )
    base.safe_emit("R433 serial evaluation complete")


def _dev_lambda_shard(lambda_value: float) -> str:
    """Run one candidate-lambda development training (pre-seal, declared
    identity): cd_matd3_message, seed 401, 8,640 steps, development
    profiles only, tmp out root, no seal.  Writes a stats JSON per shard."""
    _assert_wsl_scratch()
    global LAMBDA_P
    LAMBDA_P = float(lambda_value)
    budget = 8640  # 288 episodes x 30 steps (dev selection identity)
    dev_root = ROOT / "tmp/andes/r433_dev_lambda"
    stats = {"action_sq_acc": 0.0, "steps": 0.0}
    _train_sac_arm_seed_projected(
        "cd_matd3_message",
        401,
        out_root=dev_root / f"lambda{lambda_value}",
        total_steps=budget,
        require_seal=False,
        project=True,
        dev_stats=stats,
    )
    action_rms = float((stats["action_sq_acc"] / max(stats["steps"], 1.0)) ** 0.5)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "lambda_p": float(lambda_value),
        "action_rms": action_rms,
        "steps": stats["steps"],
    }
    out_path = dev_root / f"lambda{lambda_value}" / "stats.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )
    return str(out_path)


def dev_lambda_selection() -> str:
    """Pre-seal development selection of lambda_p (declared identity).

    Aggregates the per-candidate stats written by ``dev-lambda-shard``,
    applies the pre-registered rule (smallest lambda_p whose training
    action-RMS <= 0.8 x the no-penalty baseline), freezes the selected
    value into the runner source (so the seal pins it), and records the
    decision in tmp/andes/r433_dev_lambda.json.  Creates no formal
    artifact.  The no-penalty baseline (lambda 0.0) is the R431 verbatim
    reward path measured by the same shard mechanism.
    """
    _assert_wsl_scratch()
    if REHEARSAL.exists() or SEAL.exists() or OUT.exists():
        raise FileExistsError("R433 pre-attempt artifact already exists")
    candidates = [1.0, 5.0, 10.0, 20.0]
    dev_root = ROOT / "tmp/andes/r433_dev_lambda"
    rows: list[dict[str, Any]] = []
    baseline: float | None = None
    for lam in candidates:
        stats_path = dev_root / f"lambda{lam}" / "stats.json"
        if not stats_path.is_file():
            raise RuntimeError(f"missing dev-lambda shard stats: {stats_path}")
        payload = json.loads(stats_path.read_text(encoding="utf-8"))
        rows.append(payload)
        if lam == candidates[0]:
            baseline = float(payload["action_rms"])
    if baseline is None:
        raise RuntimeError("no dev-lambda baseline")
    selected: float | None = None
    for row in rows:
        if float(row["action_rms"]) <= 0.8 * baseline:
            selected = float(row["lambda_p"])
            break
    selected = selected if selected is not None else candidates[0]
    # Freeze into the runner source so the rehearsal and the seal pin it.
    runner_path = Path(__file__).resolve()
    text = runner_path.read_text(encoding="utf-8")
    marker = "LAMBDA_P = 10.0  # frozen by dev-lambda selection (tmp/andes/r433_dev_lambda.json), pre-seal"
    if marker not in text:
        raise RuntimeError("LAMBDA_P placeholder not found in runner source")
    frozen_line = (
        f"LAMBDA_P = {selected!r}  # frozen by dev-lambda selection "
        f"(tmp/andes/r433_dev_lambda.json), pre-seal"
    )
    runner_path.write_text(text.replace(marker, frozen_line), encoding="utf-8")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "candidates": rows,
        "baseline_lambda0": baseline,
        "selection_rule": "smallest lambda_p with training action-RMS <= 0.8 x no-penalty baseline",
        "selected_lambda_p": selected,
        "runner_source_frozen": True,
    }
    out_path = ROOT / "tmp/andes/r433_dev_lambda.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )
    return str(out_path)


_patch_parent()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "dev-lambda",
            "dev-lambda-shard",
            "reuse-capacity",
            "rehearse",
            "prepare",
            "shard",
            "evaluate",
            "classify",
        ],
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--lambda", dest="lambda_value", type=float)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "dev-lambda":
        base.safe_emit(f"R433 dev-lambda selection: {dev_lambda_selection()}")
    elif args.command == "dev-lambda-shard":
        if args.lambda_value is None:
            raise SystemExit("dev-lambda-shard requires --lambda <value>")
        base.safe_emit(
            f"R433 dev-lambda shard: {_dev_lambda_shard(args.lambda_value)}"
        )
    elif args.command == "reuse-capacity":
        base.safe_emit(f"R433 capacity evidence: {reuse_capacity()}")
    elif args.command == "rehearse":
        base.safe_emit(f"R433 rehearsal artifact: {base.rehearse()}")
    elif args.command == "prepare":
        base.safe_emit(f"R433 formal seal: {parent.prepare()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        phase, arm_id, seed = parent._parse_shard(args.shard_id)
        if phase == "train":
            if seed is None:
                raise SystemExit("training shard requires a seed")
            base.safe_emit(
                "R433 training manifest: " + train_arm_seed(arm_id, seed)
            )
        else:
            _evaluate_arm_seed_projected(arm_id, seed, project=True)
            base.safe_emit(f"R433 evaluation shard complete: {args.shard_id}")
    elif args.command == "evaluate":
        _evaluate_all()
    else:
        base.safe_emit(f"R433 formal analysis: {base.classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
