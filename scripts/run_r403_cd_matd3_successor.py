"""Run the R403 repaired CD-MATD3 disclosed-profile development gate.

Usage (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r403_cd_matd3_successor.py rehearse
  python scripts/andes_scratch.py scripts/run_r403_cd_matd3_successor.py seal
  python scripts/andes_scratch.py scripts/run_r403_cd_matd3_successor.py run

The adapter is create-only.  It never touches the R402 evaluation profiles or
changes the R402 decision; its output under tmp is development-only and cannot
serve as manuscript evidence.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.cd_matd3 import (
    CDMATD3,
    FixedWeightCDMATD3,
    mask_neighbour_slots,
    physical_costs,
    physical_costs_with_action_effort,
)
from andes_rl_kundur.control.per_vsg_md import (
    LocalNeighbourMDExecution,
    PerVSGMDActionProjector,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)
from andes_rl_kundur.evaluation.cd_matd3_canary import (
    build_contract as build_r402_contract,
)
from andes_rl_kundur.evaluation.cd_matd3_successor import (
    DETERMINISTIC_BASELINE,
    R402_BASELINE,
    REPAIRED_ARMS,
    ROUND_ID,
    build_successor_contract,
    classify_development_gate,
    contract_sha256,
)

PLAN = ROOT / "memory/rounds/R403/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R403/rehearsal.json"
SEAL = ROOT / "memory/rounds/R403/development_seal.json"
OUT = ROOT / "tmp/r403_cd_matd3_successor"
R402_CHECKPOINT = (
    ROOT
    / "results/research_loop/r402_cd_matd3_canary/train"
    / "cd_matd3_message/seed403/final.pt"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    sidecar = Path(f"{path}.sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    path.write_text(text + "\n", encoding="utf-8")
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


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r403_cd_matd3_successor.py",
        "learner": ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
        "learner_tests": ROOT / "tests/test_cd_matd3_successor.py",
        "gate": ROOT
        / "src/andes_rl_kundur/evaluation/cd_matd3_successor.py",
        "gate_tests": ROOT / "tests/test_cd_matd3_successor_gate.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT
        / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing source inputs: {missing}")
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
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
        raise RuntimeError("R403 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R403 must run through scripts/andes_scratch.py")


def _baseline_checkpoint_valid() -> bool:
    sidecar = Path(f"{R402_CHECKPOINT}.sha256")
    if not R402_CHECKPOINT.is_file() or not sidecar.is_file():
        return False
    return sidecar.read_text(encoding="ascii").split()[0] == _sha256_file(
        R402_CHECKPOINT
    )


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R403" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "parent_hash": _baseline_checkpoint_valid(),
        "output_absence": not OUT.exists(),
    }


def _agent_kwargs() -> dict[str, Any]:
    learner = build_successor_contract()["learner_contract"]
    return {
        "hidden_sizes": list(learner["actor"]["hidden_sizes"]),
        "lr": float(learner["lr"]),
        "gamma": float(learner["gamma"]),
        "tau": float(learner["tau"]),
        "buffer_size": int(learner["buffer_size"]),
        "batch_size": int(learner["batch_size"]),
        "policy_noise": float(learner["policy_noise"]),
        "noise_clip": float(learner["noise_clip"]),
        "explore_noise": float(learner["explore_noise"]),
        "policy_delay": int(learner["policy_delay"]),
        "device": "cpu",
    }


def _repaired_agent() -> FixedWeightCDMATD3:
    contract = build_successor_contract()
    return FixedWeightCDMATD3(
        common_weight=float(contract["fixed_common_weight"]),
        **_agent_kwargs(),
    )


def _r402_agent() -> CDMATD3:
    return CDMATD3(lagrange_initial=1.0, **_agent_kwargs())


def _mask_actor_obs(arm_id: str, joint: np.ndarray) -> np.ndarray:
    if arm_id == "cd_matd3_no_message":
        return mask_neighbour_slots(joint)
    return np.asarray(joint, dtype=np.float32)


def _joint_obs(observation: Mapping[int, Any]) -> np.ndarray:
    return np.concatenate(
        [np.asarray(observation[index], dtype=np.float32) for index in range(4)]
    ).astype(np.float32)


def _build_env(profile: Mapping[str, Any]) -> Any:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config

    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    base_contract = build_r402_contract()
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
    env.seed(int(base_contract["bank_seed"]))
    env.STEPS_PER_EPISODE = int(base_contract["steps"])
    return env


def _deterministic_controller() -> LocalNeighbourMDExecution:
    candidates = {row.name: row for row in local_neighbour_md_candidates()}
    arm_id = str(build_r402_contract()["deterministic_arm_id"])
    return LocalNeighbourMDExecution(candidates[arm_id])


def rehearse() -> str:
    """Exercise the same physical and checkpoint seams without an attempt."""

    _assert_wsl_scratch()
    sources = _source_manifest()
    runtime = _installed_runtime()
    checks = {
        **_authority_checks(),
        "source_hash": all(len(row["sha256"]) == 64 for row in sources.values()),
        "installed_package": Path(runtime["andes_module"]).is_file(),
        "installed_case": Path(runtime["case_path"]).is_file(),
    }
    if not all(checks.values()):
        raise RuntimeError(f"R403 rehearsal checks failed: {checks}")
    contract = build_successor_contract()
    profile = contract["profiles"][0]
    scenario = profile["scenarios"][0]
    env = _build_env(profile)
    checkpoint_dir = ROOT / "tmp/andes/r403_rehearsal_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        initial = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(contract["physical_nominal_frequency_hz"])
        )
        for arm_id in REPAIRED_ARMS:
            torch.manual_seed(0)
            np.random.seed(0)
            random.seed(0)
            agent = _repaired_agent()
            projector = PerVSGMDActionProjector(
                action_slew_limit=float(contract["action_slew_limit"])
            )
            projector.reset()
            joint = _joint_obs(observation)
            raw = agent.act(_mask_actor_obs(arm_id, joint), deterministic=False)
            action = projector.project(raw)
            action_dict = {
                index: np.asarray(action[index], dtype=np.float32)
                for index in range(4)
            }
            next_observation, _reward, done, info = env.step(action_dict)
            next_joint = _joint_obs(next_observation)
            frequencies = np.asarray(info["freq_hz_physical"], dtype=float)
            rocof = (frequencies - initial) / float(contract["dt_seconds"])
            differential, common, _effort = physical_costs_with_action_effort(
                frequencies[None, :],
                rocof[None, :],
                np.asarray(info["P_es"], dtype=float)[None, :],
                action[None, :, :],
                contract=contract,
                action_weight=float(contract["action_effort_weight"]),
            )
            agent.store(
                joint,
                action.reshape(-1),
                np.array([-differential[0], -common[0]], dtype=np.float32),
                next_joint,
                bool(done) or bool(info["tds_failed"]),
            )
            probe = checkpoint_dir / f"{arm_id}.pt"
            if probe.exists():
                probe.unlink()
            agent.save(probe)
            restored = _repaired_agent()
            restored.load(probe)
            if restored.lagrange != 1.0:
                raise RuntimeError("fixed common weight did not survive restore")
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
            "contract": contract,
            "contract_sha256": contract_sha256(contract),
            "sources": sources,
            "installed_runtime": runtime,
            "checks": checks,
            "physical_trajectory_executed": True,
            "formal_artifacts_created": False,
            "training_executed": False,
        },
    )


def seal() -> str:
    """Seal the successful rehearsal, sources, runtime and dev contract."""

    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    checks = _authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"R403 seal checks failed: {checks}")
    sources = _source_manifest()
    runtime = _installed_runtime()
    contract = build_successor_contract()
    if rehearsal.get("sources") != sources:
        raise RuntimeError("source drift after rehearsal")
    if rehearsal.get("installed_runtime") != runtime:
        raise RuntimeError("runtime drift after rehearsal")
    if rehearsal.get("contract") != contract:
        raise RuntimeError("contract drift after rehearsal")
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_sha256": contract_sha256(contract),
            "sources": sources,
            "installed_runtime": runtime,
            "r402_checkpoint": {
                "path": _relative(R402_CHECKPOINT),
                "sha256": _sha256_file(R402_CHECKPOINT),
            },
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "launch": {
                "host_process_budget": 9,
                "wsl_python_processes": 2,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "output_root": _relative(OUT),
        },
    )


def _load_seal() -> dict[str, Any]:
    sealed = _read_hashed_json(SEAL)
    contract = build_successor_contract()
    if sealed.get("round") != ROUND_ID or sealed.get("contract") != contract:
        raise RuntimeError("R403 sealed contract mismatch")
    if sealed.get("sources") != _source_manifest():
        raise RuntimeError("R403 sealed sources drifted")
    if sealed.get("installed_runtime") != _installed_runtime():
        raise RuntimeError("R403 installed runtime drifted")
    baseline = sealed.get("r402_checkpoint", {})
    if baseline.get("sha256") != _sha256_file(R402_CHECKPOINT):
        raise RuntimeError("R402 baseline checkpoint drifted")
    if OUT.exists():
        raise FileExistsError(f"R403 output already exists: {OUT}")
    return sealed


def _save_checkpoint(agent: Any, path: Path) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"checkpoint already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _train_arm(arm_id: str, run_root: Path) -> dict[str, Any]:
    contract = build_successor_contract()
    seed = int(contract["scratch_seed"])
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    agent = _repaired_agent()
    profiles = {str(row["profile_id"]): row for row in contract["profiles"]}
    scenarios = {
        str(scenario["scenario_id"]): (profile, scenario)
        for profile in contract["profiles"]
        for scenario in profile["scenarios"]
    }
    envs = {
        profile_id: _build_env(profile)
        for profile_id, profile in profiles.items()
    }
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    total_steps = int(contract["total_interaction_steps"])
    episode_steps = int(contract["steps_per_episode"])
    schedule = list(contract["scenario_order"])
    executed_steps = 0
    episode_index = 0
    tds_failed_episodes = 0
    episode_diagnostics: list[dict[str, Any]] = []
    update_diagnostics: list[dict[str, float]] = []
    invalid_reason: str | None = None
    started = time.monotonic()
    try:
        while executed_steps < total_steps:
            scenario_id = schedule[episode_index % len(schedule)]
            episode_index += 1
            profile, scenario = scenarios[scenario_id]
            env = envs[str(profile["profile_id"])]
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            projector.reset()
            previous_frequency = (
                np.asarray(env._get_vsg_omega(), dtype=float)
                * float(contract["physical_nominal_frequency_hz"])
            )
            differential_total = 0.0
            common_total = 0.0
            effort_total = 0.0
            abs_action_total = 0.0
            action_components = 0
            slew_hits = 0
            previous_action = np.zeros((4, 2), dtype=float)
            step_count = 0
            tds_failed = False
            for _ in range(episode_steps):
                if executed_steps >= total_steps:
                    break
                joint = _joint_obs(observation)
                raw = agent.act(_mask_actor_obs(arm_id, joint), deterministic=False)
                if not np.all(np.isfinite(raw)):
                    invalid_reason = "nonfinite actor output"
                    break
                action = projector.project(raw)
                delta_action = action - previous_action
                previous_action = action.copy()
                slew_hits += int(
                    np.sum(
                        np.isclose(
                            np.abs(delta_action),
                            float(contract["action_slew_limit"]),
                            atol=1e-6,
                            rtol=0.0,
                        )
                    )
                )
                abs_action_total += float(np.sum(np.abs(action)))
                action_components += int(action.size)
                action_dict = {
                    index: np.asarray(action[index], dtype=np.float32)
                    for index in range(4)
                }
                observation, _rewards, done, info = env.step(action_dict)
                executed_steps += 1
                step_count += 1
                frequencies = np.asarray(info["freq_hz_physical"], dtype=float)
                rocof = (frequencies - previous_frequency) / float(
                    contract["dt_seconds"]
                )
                previous_frequency = frequencies.copy()
                next_joint = _joint_obs(observation)
                tds_failed = bool(info["tds_failed"])
                if tds_failed:
                    differential_cost = 50.0
                    common_cost = 50.0
                    action_effort = float(np.mean(np.sum(action**2, axis=1)))
                else:
                    differential, common, effort = (
                        physical_costs_with_action_effort(
                            frequencies[None, :],
                            rocof[None, :],
                            np.asarray(info["P_es"], dtype=float)[None, :],
                            action[None, :, :],
                            contract=contract,
                            action_weight=float(contract["action_effort_weight"]),
                        )
                    )
                    differential_cost = float(differential[0])
                    common_cost = float(common[0])
                    action_effort = float(effort[0])
                differential_total += differential_cost
                common_total += common_cost
                effort_total += action_effort
                agent.store(
                    joint,
                    action.reshape(-1),
                    np.array(
                        [-differential_cost, -common_cost], dtype=np.float32
                    ),
                    next_joint,
                    bool(done) or tds_failed,
                )
                update = agent.update()
                if update is not None:
                    row = {key: float(value) for key, value in update.items()}
                    update_diagnostics.append(row)
                    if not all(np.isfinite(value) for value in row.values()):
                        invalid_reason = "nonfinite learner diagnostic"
                        break
                if tds_failed:
                    tds_failed_episodes += 1
                    break
            episode_diagnostics.append(
                {
                    "episode_index": episode_index - 1,
                    "scenario_id": scenario_id,
                    "executed_steps": step_count,
                    "differential_cost": differential_total,
                    "common_cost": common_total,
                    "action_effort": effort_total,
                    "mean_abs_action": (
                        abs_action_total / action_components
                        if action_components
                        else None
                    ),
                    "slew_bound_hit_fraction": (
                        slew_hits / action_components if action_components else None
                    ),
                    "tds_failed": tds_failed,
                }
            )
            if invalid_reason is not None:
                break
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass
    checkpoint_path = run_root / "train" / arm_id / "final.pt"
    checkpoint_sha = None
    if invalid_reason is None and executed_steps == total_steps:
        checkpoint_sha = _save_checkpoint(agent, checkpoint_path)
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm_id": arm_id,
        "scratch_seed": seed,
        "interaction_steps": executed_steps,
        "episodes_attempted": len(episode_diagnostics),
        "tds_failed_episodes": tds_failed_episodes,
        "invalid_reason": invalid_reason,
        "diagnostics_complete": invalid_reason is None
        and executed_steps == total_steps
        and len(episode_diagnostics) == episode_index,
        "episode_diagnostics": episode_diagnostics,
        "update_diagnostics": update_diagnostics,
        "final_checkpoint_sha256": checkpoint_sha,
        "elapsed_seconds": time.monotonic() - started,
    }
    _write_new_json(run_root / "train" / arm_id / "manifest.json", manifest)
    return manifest


def _policy_for(label: str, run_root: Path) -> tuple[Any, Any]:
    if label == DETERMINISTIC_BASELINE:
        return _deterministic_controller(), None
    if label == R402_BASELINE:
        agent = _r402_agent()
        agent.load(R402_CHECKPOINT)
        return agent, "cd_matd3_message"
    agent = _repaired_agent()
    agent.load(run_root / "train" / label / "final.pt")
    return agent, label


def _evaluate_label(
    label: str,
    run_root: Path,
    training_manifest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    contract = build_successor_contract()
    controller, arm_id = _policy_for(label, run_root)
    projector = PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    record_differential: list[float] = []
    record_common: list[float] = []
    abs_action_total = 0.0
    action_components = 0
    slew_hits = 0
    tds_failed_records = 0
    for profile in contract["profiles"]:
        env = _build_env(profile)
        try:
            for scenario in profile["scenarios"]:
                observation = env.reset(delta_u=dict(scenario["delta_u"]))
                projector.reset()
                if label == DETERMINISTIC_BASELINE:
                    controller.reset()
                previous_frequency = (
                    np.asarray(env._get_vsg_omega(), dtype=float)
                    * float(contract["physical_nominal_frequency_hz"])
                )
                previous_action = np.zeros((4, 2), dtype=float)
                differential_total = 0.0
                common_total = 0.0
                failed = False
                for _ in range(int(contract["steps_per_episode"])):
                    if label == DETERMINISTIC_BASELINE:
                        action = np.asarray(
                            controller.act(
                                adapt_v4_observations_to_physical(observation)
                            ),
                            dtype=float,
                        )
                    else:
                        joint = _joint_obs(observation)
                        raw = controller.act(
                            _mask_actor_obs(str(arm_id), joint),
                            deterministic=True,
                        )
                        action = projector.project(raw)
                    delta_action = action - previous_action
                    previous_action = action.copy()
                    slew_hits += int(
                        np.sum(
                            np.isclose(
                                np.abs(delta_action),
                                float(contract["action_slew_limit"]),
                                atol=1e-6,
                                rtol=0.0,
                            )
                        )
                    )
                    abs_action_total += float(np.sum(np.abs(action)))
                    action_components += int(action.size)
                    action_dict = {
                        index: np.asarray(action[index], dtype=np.float32)
                        for index in range(4)
                    }
                    observation, _rewards, _done, info = env.step(action_dict)
                    frequencies = np.asarray(
                        info["freq_hz_physical"], dtype=float
                    )
                    rocof = (frequencies - previous_frequency) / float(
                        contract["dt_seconds"]
                    )
                    previous_frequency = frequencies.copy()
                    differential, common = physical_costs(
                        frequencies[None, :],
                        rocof[None, :],
                        np.asarray(info["P_es"], dtype=float)[None, :],
                        contract=contract,
                    )
                    differential_total += float(differential[0])
                    common_total += float(common[0])
                    if bool(info["tds_failed"]):
                        failed = True
                        break
                record_differential.append(differential_total)
                record_common.append(common_total)
                if failed:
                    tds_failed_records += 1
        finally:
            try:
                env.close()
            except Exception:
                pass
    diagnostics_complete = (
        True
        if training_manifest is None
        else bool(training_manifest.get("diagnostics_complete", False))
    )
    training_tds_failures = (
        0
        if training_manifest is None
        else int(training_manifest.get("tds_failed_episodes", -1))
    )
    return {
        "mean_abs_action": abs_action_total / action_components,
        "slew_bound_hit_fraction": slew_hits / action_components,
        "mean_per_record_common": float(np.mean(record_common)),
        "mean_per_record_differential": float(np.mean(record_differential)),
        "diagnostics_complete": diagnostics_complete,
        "tds_failed_episodes": training_tds_failures + tds_failed_records,
        "evaluation_records": len(record_common),
    }


def run() -> str:
    """Train, evaluate and classify the single frozen R403 dev attempt."""

    _assert_wsl_scratch()
    sealed = _load_seal()
    OUT.mkdir(parents=True, exist_ok=False)
    _write_new_json(
        OUT / "started.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": _sha256_file(SEAL),
            "contract_sha256": sealed["contract_sha256"],
        },
    )
    manifests = {
        arm_id: _train_arm(arm_id, OUT) for arm_id in REPAIRED_ARMS
    }
    metrics: dict[str, dict[str, Any]] = {}
    for label in (*REPAIRED_ARMS, R402_BASELINE, DETERMINISTIC_BASELINE):
        metrics[label] = _evaluate_label(label, OUT, manifests.get(label))
    metrics_sha = _write_new_json(
        OUT / "development_metrics.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "metrics": metrics,
        },
    )
    outcome = classify_development_gate(metrics)
    return _write_new_json(
        OUT / "decision.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": sealed["contract_sha256"],
            "development_metrics_sha256": metrics_sha,
            **outcome,
        },
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rehearse", "seal", "run"))
    return parser


def main() -> int:
    command = _parser().parse_args().command
    if command == "rehearse":
        print(f"R403 rehearsal: {rehearse()}", flush=True)
    elif command == "seal":
        print(f"R403 development seal: {seal()}", flush=True)
    else:
        print(f"R403 development decision: {run()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
