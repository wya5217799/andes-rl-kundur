"""R431 engineering successor of R430: execution-layer slew projection for the SAC arms + 5 seeds.

R430 (CLM-1310) showed the topology-adapted per-agent SAC trains stably but
every evaluation row fails ``action_slew_violation`` because the frozen SAC
path executed raw tanh actions with no slew projection.  This successor
imports the frozen R430 runner chain (R430 -> R429 -> R428) and changes one
scientific factor: the SAC arms now execute through the byte-unchanged
``PerVSGMDActionProjector`` (0.25/step, per-actor rowwise clip + slew,
stateful, reset per episode) in training and evaluation, exactly like the
scalar arm.  A second declared delta is statistical scale: training seeds
become [401, 402, 403, 404, 405] (401-403 stay directly comparable to
R430/R428/R425; scalar 401-403 keep the byte-identical R419 anchor, scalar
404/405 are fresh with no anchor).

The two execution functions are verbatim copies of the frozen R428 source
with a single declared seam each (marked ``R431-SEAM``): the SAC training
loop projects before decode/step and measures executed-delta saturation;
the eval loop projects the deterministic SAC action and records the
projected action, so ``summarise_profile`` sees the physically executed
actions.  A ``project=False`` mode restores the frozen behavior exactly for
the bitcheck (byte-identical short-budget checkpoint vs the frozen loop).

WSL lifecycle (always through ``scripts/andes_scratch.py``):

    python scripts/andes_scratch.py scripts/run_r431_sac_slew.py reuse-capacity
    python scripts/andes_scratch.py scripts/run_r431_sac_slew.py rehearse
    python scripts/andes_scratch.py scripts/run_r431_sac_slew.py prepare
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r431_sac_slew.py \
        --shards tmp/andes/r431_train_shards.json --workers 15 --round R431
    python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
        --runner scripts/run_r431_sac_slew.py \
        --shards tmp/andes/r431_eval_shards.json --workers 16 --round R431
    python scripts/andes_scratch.py scripts/run_r431_sac_slew.py classify

Formal outputs are create-only and hashed under
``results/research_loop/r431_sac_slew``.  No retry is authorized.
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

ROUND_ID = "R431"
PLAN = ROOT / "memory/rounds/R431/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R431/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R431/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R431/formal_seal.json"
OUT = ROOT / "results/research_loop/r431_sac_slew"
TIER1_OUT = ROOT / "tmp/andes/r431_tier1"
R430_CAPACITY = ROOT / "memory/rounds/R430/capacity_evidence.json"

TRAINING_SEEDS = [401, 402, 403, 404, 405]
ANCHOR_SEEDS = [401, 402, 403]

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
):
    globals()[_name] = getattr(base, _name, None) or getattr(r430, _name, None)


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(_R430_BUILD_CONTRACT())
    contract["training_seeds"] = list(TRAINING_SEEDS)
    contract["engineering_successor"] = {
        "successor_of": "R430",
        "single_change": "sac-execution-slew-projection-plus-seed-count-5",
        "explicit_sac_out_root": True,
        "sac_slew_projection": True,
        "seed_scale": list(TRAINING_SEEDS),
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
        "runner_tests": ROOT / "tests/test_run_r431_sac_slew.py",
        "parent_r430_runner": ROOT / "scripts/run_r430_adapted_sac_successor.py",
    }
    for name, path in replacements.items():
        sources[name] = {
            "path": base._relative(path),
            "sha256": base._sha256_file(path),
        }
    return sources


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r430_plan": ROOT / "memory/rounds/R430/plan.md",
        "r430_seal": ROOT / "memory/rounds/R430/formal_seal.json",
        "r430_analysis": ROOT
        / "results/research_loop/r430_adapted_sac_successor/formal_analysis.json",
        "r430_capacity": R430_CAPACITY,
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
    if path.resolve() == SEAL.resolve():
        mutable["single_factor_change"] = (
            "R430-identical science except: SAC arms execute through the "
            "byte-unchanged PerVSGMDActionProjector (0.25/step) in training "
            "and evaluation; training seeds extended to 401-405; scalar "
            "401-403 keep the R419 byte-anchor, scalar 404/405 fresh"
        )
    if path.name == "formal_analysis.json" and path.parent.resolve() == OUT.resolve():
        mutable.setdefault("repair", {})["engineering_successor"] = {
            "successor_of": "R430",
            "explicit_sac_out_root": True,
            "sac_slew_projection": True,
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
        "bitcheck_byte_identical": None,
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
    # Bitcheck: frozen loop vs the verbatim copy with project=False, same
    # short budget and seed, must yield byte-identical final checkpoints.
    import tempfile

    tmp_root = Path(tempfile.mkdtemp(prefix="r431_bitcheck_"))
    seed = 777
    budget = 2100  # 70 episodes x 30 steps; exact-budget convergence required
    try:
        frozen_path = tmp_root / "frozen"
        copy_path = tmp_root / "copy"
        base._train_sac_arm_seed(
            "cd_matd3_no_message",
            seed,
            out_root=frozen_path,
            total_steps=budget,
            require_seal=False,
        )
        _train_sac_arm_seed_projected(
            "cd_matd3_no_message",
            seed,
            out_root=copy_path,
            total_steps=budget,
            require_seal=False,
            project=False,
        )
        frozen_sha = _sha256_file(
            frozen_path / "train" / "cd_matd3_no_message" / f"seed{seed}" / "final.pt"
        )
        copy_sha = _sha256_file(
            copy_path / "train" / "cd_matd3_no_message" / f"seed{seed}" / "final.pt"
        )
        result["bitcheck_byte_identical"] = frozen_sha == copy_sha
    except Exception as exc:  # pragma: no cover - defensive
        result["bitcheck_error"] = str(exc)
        result["bitcheck_byte_identical"] = False
    result["passed"] = bool(
        result["deltas_within_limit"] and result["bitcheck_byte_identical"]
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
) -> str:
    """SAC training loop — verbatim copy of the frozen R428 loop with the
    single declared R431 seam: executed actions pass through the per-actor
    slew projector (the raw-magnitude saturation diagnostic stays verbatim,
    keeping the R430-documented field semantics).  ``project=False``
    restores the frozen raw-execution path for the bitcheck (byte-identical
    checkpoint required).
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
        projector = PerVSGMDActionProjector(  # R431-SEAM
            action_slew_limit=float(  # R431-SEAM
                contract["action_slew_limit"]  # R431-SEAM
            )  # R431-SEAM
        )  # R431-SEAM
        projector.reset()  # R431-SEAM
        previous_executed = np.zeros((4, 2), dtype=np.float32)  # R431-SEAM
        for _step_index in range(steps_per_episode):
            joint = _joint_obs(observation)
            raw = agent.act(joint, deterministic=False)
            if not np.all(np.isfinite(raw)):
                invalid_reason = "nonfinite actor output"
                break
            if project:  # R431-SEAM
                action = projector.project(raw)  # R431-SEAM
            else:  # R431-SEAM
                action = raw  # R431-SEAM
            saturation = np.abs(raw) >= (1.0 - 1.0e-6)
            if np.any(saturation):
                saturation_steps += 1
            action_dict = {  # R431-SEAM
                actor: np.asarray(action[actor], dtype=np.float32)  # R431-SEAM
                for actor in range(4)  # R431-SEAM
            }  # R431-SEAM
            observation, _rewards, done, info = env.step(action_dict)
            previous_executed = np.asarray(  # R431-SEAM
                action, dtype=np.float32  # R431-SEAM
            ).copy()  # R431-SEAM
            executed_steps += 1
            tds_failed = bool(info["tds_failed"])
            next_joint = _joint_obs(observation)
            terminal = bool(done) or tds_failed
            per_agent_rewards = _sac_step_rewards(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                masked=masked,
            )
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
                        # R431-SEAM: execution-layer slew projection on the
                        # SAC arms (R430 executed raw tanh; rows invalid).
                        if project:  # R431-SEAM
                            action = projector.project(  # R431-SEAM
                                agent.act(joint, deterministic=True)  # R431-SEAM
                            )  # R431-SEAM
                        else:  # R431-SEAM
                            action = agent.act(joint, deterministic=True)  # R431-SEAM
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
        raise FileExistsError("R431 pre-attempt artifact already exists")
    other = _other_processes()
    if other:
        raise RuntimeError("other research Python processes are active: " + str(other))
    inherited = _read_hashed_json(R430_CAPACITY)
    if inherited.get("readiness") != "RUN-READY" or int(
        inherited.get("selected_workers", 0)
    ) != 16:
        raise RuntimeError("R430 capacity evidence is not the registered 16-worker anchor")
    logical, physical_memory, wsl_available = _memory_resources()
    payload = copy.deepcopy(inherited)
    payload.update(
        {
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "authorization": (
                "owner ordered parallel supplementary experiments; R429 v3 "
                "ladder reused after fresh no-load host check; R431 selects "
                "15 workers (one under the measured rung-16 envelope) sharing "
                "the host with R432 (declared other_reserved_processes=5)"
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
                "path": base._relative(R430_CAPACITY),
                "sha256": _sha256_file(R430_CAPACITY),
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
    base.safe_emit("R431 serial evaluation complete")


_patch_parent()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["reuse-capacity", "rehearse", "prepare", "shard", "evaluate", "classify"],
    )
    parser.add_argument("shard_id", nargs="?")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "reuse-capacity":
        base.safe_emit(f"R431 capacity evidence: {reuse_capacity()}")
    elif args.command == "rehearse":
        base.safe_emit(f"R431 rehearsal artifact: {base.rehearse()}")
    elif args.command == "prepare":
        base.safe_emit(f"R431 formal seal: {parent.prepare()}")
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a registered shard id")
        phase, arm_id, seed = parent._parse_shard(args.shard_id)
        if phase == "train":
            if seed is None:
                raise SystemExit("training shard requires a seed")
            base.safe_emit(
                "R431 training manifest: " + train_arm_seed(arm_id, seed)
            )
        else:
            _evaluate_arm_seed_projected(arm_id, seed, project=True)
            base.safe_emit(f"R431 evaluation shard complete: {args.shard_id}")
    elif args.command == "evaluate":
        _evaluate_all()
    else:
        base.safe_emit(f"R431 formal analysis: {base.classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
