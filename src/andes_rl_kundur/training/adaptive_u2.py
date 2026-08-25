"""Adaptive training cell for the corrected-card U2 SAC family.

This module owns the variable-budget seam only.  A round runner supplies the
already-reviewed R482-compatible runtime, verifies formal authority, and then
calls :func:`train_cell`.  The cell fails closed: it may stop early only after
all frozen convergence gates pass; otherwise it runs to ``max_steps``.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .adaptive_stop import AdaptiveStopConfig, AdaptiveStopMonitor, StopDecision

CURVE_KEYS = (
    "critic_loss",
    "actor_loss",
    "alpha_loss",
    "alpha",
    "actor_grad_norm",
)
PROBE_GENERATOR_SEED = 482_000
PROBE_SAMPLES_PER_SCENARIO = 5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def config_sha256(config: AdaptiveStopConfig) -> str:
    payload = json.dumps(
        asdict(config), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_probe_bank(runtime: Any, path: Path) -> str:
    """Freeze deterministic samples across complete development trajectories."""

    core = runtime.base.base.base.core
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"probe bank exists: {path}")
    contract = runtime.build_contract()
    profiles = [row for row in contract["profiles"] if row["split"] == "development"]
    core._seed_all(PROBE_GENERATOR_SEED)
    envs = {str(row["profile_id"]): core.r431._build_env(row) for row in profiles}
    observations: list[np.ndarray] = []
    previous_actions: list[np.ndarray] = []
    labels: list[str] = []
    time_labels: list[int] = []
    context_labels: list[str] = []
    steps = int(contract["steps"])
    sample_steps = set(
        int(value)
        for value in np.linspace(
            0, steps - 1, num=min(PROBE_SAMPLES_PER_SCENARIO, steps), dtype=int
        )
    )
    zero_action = np.zeros((4, 2), dtype=np.float32)
    alternating_action = np.asarray(
        [[0.25, -0.25], [-0.25, 0.25], [0.25, 0.25], [-0.25, -0.25]],
        dtype=np.float32,
    )
    contexts = (("zero", zero_action), ("alternating", alternating_action))
    try:
        for profile in profiles:
            env = envs[str(profile["profile_id"])]
            for scenario in profile["scenarios"]:
                observation = env.reset(delta_u=dict(scenario["delta_u"]))
                for time_index in range(steps):
                    joint = np.asarray(core.r431._joint_obs(observation), dtype=np.float32)
                    if joint.shape == (28,):
                        joint = joint.reshape(4, 7)
                    if joint.shape != (4, 7):
                        raise RuntimeError(
                            f"unexpected physical probe observation shape: {joint.shape}"
                        )
                    if not np.all(np.isfinite(joint)):
                        raise RuntimeError("non-finite observation in probe bank")
                    if time_index in sample_steps:
                        for context_name, previous in contexts:
                            observations.append(joint.copy())
                            previous_actions.append(previous.copy())
                            labels.append(str(scenario["scenario_id"]))
                            time_labels.append(time_index)
                            context_labels.append(context_name)
                    observation, _reward, done, info = env.step(
                        {index: zero_action[index] for index in range(4)}
                    )
                    if info["tds_failed"]:
                        raise RuntimeError("TDS failure while building probe trajectory")
                    if done and time_index < steps - 1:
                        raise RuntimeError("premature terminal while building probe trajectory")
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass
    if not observations:
        raise RuntimeError("empty development action-probe bank")
    probe_definition = {
        "generator_seed": PROBE_GENERATOR_SEED,
        "generator_version": "development-zero-action-trajectory-v1",
        "steps": steps,
        "sample_steps": sorted(sample_steps),
        "profile_ids": [str(row["profile_id"]) for row in profiles],
        "scenario_ids": labels,
        "previous_action_contexts": context_labels,
    }
    definition_sha = hashlib.sha256(
        json.dumps(probe_definition, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return core._write_new_npz(
        path,
        joint_observations=np.stack(observations),
        previous_actions=np.stack(previous_actions),
        scenario_ids=np.asarray(labels),
        time_indices=np.asarray(time_labels, dtype=np.int64),
        previous_action_contexts=np.asarray(context_labels),
        generator_seed=np.asarray([PROBE_GENERATOR_SEED], dtype=np.int64),
        generator_version=np.asarray(["development-zero-action-trajectory-v1"]),
        probe_definition_sha256=np.asarray([definition_sha]),
    )


def load_probe_bank(path: Path, expected_sha256: str) -> tuple[np.ndarray, np.ndarray]:
    if sha256_file(path) != expected_sha256:
        raise RuntimeError("action-probe bank hash mismatch")
    with np.load(path, allow_pickle=False) as payload:
        joint = np.asarray(payload["joint_observations"], dtype=np.float32)
        previous = np.asarray(payload["previous_actions"], dtype=np.float32)
    if joint.ndim != 3 or joint.shape[1:] != (4, 7):
        raise ValueError(f"unexpected probe observation shape: {joint.shape}")
    if previous.shape != (joint.shape[0], 4, 2):
        raise ValueError(f"unexpected probe previous-action shape: {previous.shape}")
    if not np.all(np.isfinite(joint)) or not np.all(np.isfinite(previous)):
        raise ValueError("non-finite action-probe bank")
    return joint, previous


def action_probe_outputs(
    runtime: Any,
    wrapper: Any,
    arm_id: str,
    joint_bank: np.ndarray,
    previous_bank: np.ndarray,
) -> np.ndarray:
    factors = runtime.arm_factors(arm_id)
    rows = []
    for joint, previous in zip(joint_bank, previous_bank, strict=True):
        actor_rows = runtime.base.base.source_rows(joint, factors["actor_source"])
        _raw, executed = wrapper.act(actor_rows, previous, deterministic=True)
        rows.append(executed)
    outputs = np.asarray(rows, dtype=np.float32)
    if not np.all(np.isfinite(outputs)):
        raise RuntimeError("non-finite deterministic action-probe output")
    return outputs


def action_probe_drift(previous: np.ndarray, current: np.ndarray) -> float:
    """Worst per-state RMS movement on normalized actions in [-1, 1]."""

    if previous.shape != current.shape or previous.size == 0:
        raise ValueError("incompatible action-probe outputs")
    squared = (current.astype(float) - previous) ** 2
    per_state = np.sqrt(np.mean(squared.reshape(squared.shape[0], -1), axis=1))
    drift = float(np.max(per_state))
    if not math.isfinite(drift):
        raise ValueError("non-finite action-probe drift")
    return drift


def _load_base_from_source(
    runtime: Any,
    wrapper: Any,
    source_out: Path,
    seed: int,
    *,
    source_round: str,
    expected_manifest_sha256: str,
    expected_base_sha256: str,
) -> tuple[dict[str, Any], str, str]:
    core = runtime.base.base.base.core
    manifest_path = source_out / "donors" / f"seed{seed}" / "manifest.json"
    manifest = core._read_hashed_json(manifest_path)
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise RuntimeError("source donor manifest differs from formal seal")
    if manifest.get("round") != source_round or int(manifest["training_seed"]) != seed:
        raise RuntimeError("source donor manifest identity mismatch")
    raw_path = Path(str(manifest["base_state_path"]))
    base_path = raw_path if raw_path.is_absolute() else core.ROOT / raw_path
    digest = sha256_file(base_path)
    if digest != manifest["base_state_sha256"] or digest != expected_base_sha256:
        raise RuntimeError("base state hash mismatch")
    payload = core.torch.load(str(base_path), map_location="cpu", weights_only=True)
    if payload.get("kind") != "r470-common-base-state" or int(payload["training_seed"]) != seed:
        raise RuntimeError("base state identity mismatch")
    wrapper.import_states(payload["agents"])
    try:
        display_path = core._relative(base_path)
    except ValueError:
        display_path = str(base_path)
    return manifest, display_path, digest


def _decision_row(decision: StopDecision) -> dict[str, Any]:
    return {
        "interaction_steps": decision.interaction_steps,
        "checked": decision.checked,
        "should_stop": decision.should_stop,
        "converged": decision.converged,
        "reason": decision.reason,
        "consecutive_passes": decision.consecutive_passes,
        "evidence": dict(decision.evidence),
    }


def train_cell(
    runtime: Any,
    *,
    round_id: str,
    out: Path,
    source_out: Path,
    arm_id: str,
    seed: int,
    stop_config: AdaptiveStopConfig,
    probe_path: Path,
    probe_sha256: str,
    source_round: str,
    source_manifest_sha256: str,
    source_base_sha256: str,
) -> str:
    """Train one create-only cell and return its manifest SHA-256."""

    core = runtime.base.base.base.core
    core._assert_wsl_scratch()
    final_dir = out / "train" / arm_id / f"seed{seed}"
    if final_dir.exists():
        raise FileExistsError(f"training output exists: {final_dir}")
    attempt_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + f"_pid{os.getpid()}"
    run_dir = out / "recovery_attempts" / arm_id / f"seed{seed}" / attempt_id
    run_dir.mkdir(parents=True)

    envs: dict[str, Any] = {}
    try:
        contract = runtime.build_contract()
        factors = runtime.arm_factors(arm_id)
        core._seed_all(seed)
        profiles = [row for row in contract["profiles"] if row["split"] == "development"]
        wrapper = core.FactorialWrapper(arm_id)
        donor_manifest, base_path, base_sha = _load_base_from_source(
            runtime,
            wrapper,
            source_out,
            seed,
            source_round=source_round,
            expected_manifest_sha256=source_manifest_sha256,
            expected_base_sha256=source_base_sha256,
        )
        joint_probe, previous_probe = load_probe_bank(probe_path, probe_sha256)
        envs = {str(row["profile_id"]): core.r431._build_env(row) for row in profiles}
    except Exception as exc:
        core._write_new_json(
            run_dir / "initialization_failure.json",
            {
                "schema_version": 1,
                "round": round_id,
                "arm_id": arm_id,
                "training_seed": seed,
                "attempt_id": attempt_id,
                "failure_type": type(exc).__name__,
                "failure": str(exc),
                "created_utc": datetime.now(UTC).isoformat(),
            },
        )
        raise
    scenarios = {
        str(scenario["scenario_id"]): (profile, scenario)
        for profile in profiles
        for scenario in profile["scenarios"]
    }
    schedule = list(contract["training_contract"]["development_scenario_order"])
    steps_per_episode = int(contract["steps"])
    monitor = AdaptiveStopMonitor(stop_config)
    probe_baseline_step = max(1, stop_config.min_steps - stop_config.check_interval)
    previous_probe_outputs: np.ndarray | None = None
    baseline_probe_outputs: np.ndarray | None = None
    executed_steps = 0
    episode_index = 0
    tds_failures = 0
    invalid_reason: str | None = None
    stop_decision: StopDecision | None = None
    stop_requested = False
    curves: dict[str, list[float]] = {key: [] for key in CURVE_KEYS}
    trace: list[dict[str, Any]] = []
    half_sha: str | None = None
    caught_exception: Exception | None = None

    try:
        while executed_steps < stop_config.max_steps and not stop_requested:
            scenario_id = str(schedule[episode_index % len(schedule)])
            profile, scenario = scenarios[scenario_id]
            env = envs[str(profile["profile_id"])]
            observation = env.reset(delta_u=dict(scenario["delta_u"]))
            previous = np.zeros((4, 2), dtype=np.float32)
            for _time_index in range(steps_per_episode):
                joint = core.r431._joint_obs(observation)
                actor_rows = runtime.base.base.source_rows(joint, factors["actor_source"])
                critic_rows = runtime.base.base.source_rows(joint, factors["critic_source"])
                raw, executed = wrapper.act(actor_rows, previous, deterministic=False)
                if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(executed)):
                    invalid_reason = "nonfinite action"
                    break
                observation, _unused_reward, done, info = env.step(
                    {index: executed[index] for index in range(4)}
                )
                executed_steps += 1
                if info["tds_failed"]:
                    tds_failures += 1
                next_joint = core.r431._joint_obs(observation)
                next_actor_rows = runtime.base.base.source_rows(next_joint, factors["actor_source"])
                next_critic_rows = runtime.base.base.source_rows(
                    next_joint, factors["critic_source"]
                )
                terminal = bool(done) or bool(info["tds_failed"])
                if arm_id == runtime.PHASE3B_ARM:
                    rewards = runtime._r482_penalized_step_rewards(
                        joint,
                        np.asarray(info["delta_M"], dtype=float),
                        np.asarray(info["delta_D"], dtype=float),
                        True,
                        executed,
                    )
                else:
                    rewards = core.legacy.step_rewards(
                        joint,
                        np.asarray(info["delta_M"], dtype=float),
                        np.asarray(info["delta_D"], dtype=float),
                        reward_access=bool(factors["reward_access"]),
                    )
                wrapper.store(
                    actor_rows,
                    critic_rows,
                    previous,
                    raw,
                    executed,
                    rewards,
                    next_actor_rows,
                    next_critic_rows,
                    terminal,
                )
                diagnostics = wrapper.update_all()
                if diagnostics is not None:
                    for key in curves:
                        curves[key].append(float(diagnostics[key]))
                    if not all(np.isfinite(list(diagnostics.values()))):
                        invalid_reason = "nonfinite learner diagnostic"
                        break
                previous = executed.copy()
                if executed_steps == stop_config.max_steps // 2:
                    half_sha = wrapper.save(run_dir / "half.pt", stage="half", base_sha256=base_sha)
                probe_due = executed_steps == probe_baseline_step or (
                    executed_steps >= stop_config.min_steps
                    and (
                        executed_steps == stop_config.max_steps
                        or (executed_steps - stop_config.min_steps) % stop_config.check_interval
                        == 0
                    )
                )
                if probe_due:
                    current_outputs = action_probe_outputs(
                        runtime,
                        wrapper,
                        arm_id,
                        joint_probe,
                        previous_probe,
                    )
                    if previous_probe_outputs is None:
                        previous_probe_outputs = current_outputs
                        baseline_probe_outputs = current_outputs
                    else:
                        if baseline_probe_outputs is None:
                            raise RuntimeError("missing action-probe baseline")
                        adjacent_drift = action_probe_drift(previous_probe_outputs, current_outputs)
                        cumulative_drift = action_probe_drift(
                            baseline_probe_outputs, current_outputs
                        )
                        drift = max(adjacent_drift, cumulative_drift)
                        stop_decision = monitor.observe(
                            interaction_steps=executed_steps,
                            curves=curves,
                            action_probe_drift=drift,
                            tds_failures=tds_failures,
                        )
                        decision_row = _decision_row(stop_decision)
                        decision_row["action_probe_adjacent_drift"] = adjacent_drift
                        decision_row["action_probe_cumulative_drift"] = cumulative_drift
                        trace.append(decision_row)
                        previous_probe_outputs = current_outputs
                        stop_requested = stop_decision.should_stop
                if info["tds_failed"]:
                    break
                if stop_requested or executed_steps >= stop_config.max_steps:
                    break
            episode_index += 1
            if invalid_reason is not None:
                break
    except Exception as exc:
        caught_exception = exc
        invalid_reason = f"{type(exc).__name__}: {exc}"
    finally:
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass

    if half_sha is None and executed_steps > stop_config.max_steps // 2:
        invalid_reason = invalid_reason or "missing half checkpoint"
    valid = (
        invalid_reason is None
        and stop_decision is not None
        and stop_decision.should_stop
        and half_sha is not None
        and stop_config.min_steps <= executed_steps <= stop_config.max_steps
    )
    final_sha = (
        wrapper.save(run_dir / "final.pt", stage="final", base_sha256=base_sha) if valid else None
    )
    curve_sha = core._write_new_npz(
        run_dir / "full_curves.npz",
        **{key: np.asarray(value, dtype=np.float64) for key, value in curves.items()},
    )
    trace_sha = core._write_new_json(
        run_dir / "adaptive_trace.json",
        {
            "schema_version": 1,
            "round": round_id,
            "arm_id": arm_id,
            "training_seed": seed,
            "attempt_id": attempt_id,
            "stop_config": asdict(stop_config),
            "stop_config_sha256": config_sha256(stop_config),
            "probe_bank_sha256": probe_sha256,
            "checks": trace,
            "monitor_state": monitor.state_dict(),
        },
    )
    stop_reason = stop_decision.reason if stop_decision is not None else "invalid"
    stability = {
        key: core._curve_stability(np.asarray(curves[key])) for key in ("critic_loss", "actor_loss")
    }
    manifest_sha = core._write_new_json(
        run_dir / "manifest.json",
        {
            "schema_version": 2,
            "round": round_id,
            "training_mode": "adaptive_stop_v1",
            "arm_id": arm_id,
            "factors": factors,
            "training_seed": seed,
            "attempt_id": attempt_id,
            "rng_set_before_environment_network_optimizer_replay": True,
            "base_state_path": base_path,
            "base_state_sha256": base_sha,
            "donor_manifest_sha256": sha256_file(
                source_out / "donors" / f"seed{seed}" / "manifest.json"
            ),
            "source_round": source_round,
            "reward_function_sha256": (
                runtime._penalized_reward_sha()
                if arm_id == runtime.PHASE3B_ARM
                else donor_manifest["reward_function_sha256"]
            ),
            "interaction_steps": executed_steps,
            "minimum_interaction_steps": stop_config.min_steps,
            "maximum_interaction_steps": stop_config.max_steps,
            "episodes_attempted": episode_index,
            "tds_failed_episodes": tds_failures,
            "stop_reason": stop_reason,
            "converged": bool(stop_decision and stop_decision.converged),
            "valid": valid,
            "invalid_reason": invalid_reason,
            "half_checkpoint_sha256": half_sha,
            "final_checkpoint_sha256": final_sha,
            "full_curves_sha256": curve_sha,
            "adaptive_trace_sha256": trace_sha,
            "stop_config_sha256": config_sha256(stop_config),
            "probe_bank_sha256": probe_sha256,
            "curve_count": len(curves["critic_loss"]),
            "stability": stability,
            "contract_sha256": core.contract_sha256(),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )
    if not valid:
        raise RuntimeError(
            f"adaptive cell invalid after preserving manifest: {arm_id}|{seed}"
        ) from caught_exception
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        raise FileExistsError(f"training output appeared before publication: {final_dir}")
    run_dir.replace(final_dir)
    return manifest_sha
