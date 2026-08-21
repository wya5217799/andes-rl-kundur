"""R460 U3 executed-action Bellman-semantics evidence bundle.

WSL-only commands (always through ``scripts/andes_scratch.py``):

    ... run_r460_u3_execution_semantics.py probe <job-id> [--steps 3]
    ... run_r460_u3_execution_semantics.py rehearse
    ... run_r460_u3_execution_semantics.py prepare
    ... run_r460_u3_execution_semantics.py shard <job-id>
    ... run_r460_u3_execution_semantics.py consolidate
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import resource
except ModuleNotFoundError:  # pragma: no cover - Windows static/unit checks
    resource = None  # type: ignore[assignment]

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_name, "1")
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from andes_rl_kundur.agents.executed_action_sac import (  # noqa: E402
    ENTROPY_SEMANTICS,
    ExecutedActionSACAgent,
    augment_state_numpy,
    project_action_numpy,
    project_action_torch,
)
from andes_rl_kundur.control.per_vsg_md import (  # noqa: E402
    PerVSGMDActionProjector,
)


ROUND = "R460"
PLAN = ROOT / "memory/rounds/R460/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R460/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R460/rehearsal.json"
REHEARSAL_V2 = ROOT / "memory/rounds/R460/rehearsal_v2.json"
REHEARSAL_AMENDMENT = ROOT / "memory/rounds/R460/rehearsal_amendment.json"
PRESEAL_RUNTIME_AMENDMENT = ROOT / "memory/rounds/R460/preseal_runtime_amendment.json"
SEAL = ROOT / "memory/rounds/R460/formal_seal.json"
OUT = ROOT / "results/research_loop/r460_u3_execution_semantics"
R431_OUT = ROOT / "results/research_loop/r431_sac_slew"
R431_CHECKPOINT = R431_OUT / "train/cd_matd3_message/seed401/final.pt"
R431_RUNNER = ROOT / "scripts/run_r431_sac_slew.py"
REQUEST = ROOT / "paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821"
POLICY_SEED = 460031
STEPS = 30
SLEW_LIMIT = 0.25
HIDDEN_SIZES = [128, 128, 128, 128]


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


r431 = _load_module("_r460_r431_parent", R431_RUNNER)

SOURCE_PATHS = {
    "runner": Path(__file__).resolve(),
    "executed_action_sac": ROOT
    / "src/andes_rl_kundur/agents/executed_action_sac.py",
    "executed_action_sac_tests": ROOT / "tests/test_executed_action_sac.py",
    "runtime_projector": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
    "historical_r431_runner": R431_RUNNER,
    "historical_sac": ROOT / "src/andes_rl_kundur/agents/sac.py",
    "historical_replay": ROOT / "src/andes_rl_kundur/agents/replay_buffer.py",
    "environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
    "scratch_launcher": ROOT / "scripts/andes_scratch.py",
    "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
    "preseal_runtime_amendment": PRESEAL_RUNTIME_AMENDMENT,
    "plan": PLAN,
}


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(path)
    sidecar = Path(f"{path}.sha256")
    if sidecar.exists():
        raise FileExistsError(sidecar)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _write_text_new(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(text, encoding="utf-8")
    return _sha256(path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R460 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R460 must run through scripts/andes_scratch.py")


def _resources(start: float) -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF) if resource is not None else None
    return {
        "wall_seconds": time.perf_counter() - start,
        "user_cpu_seconds": float(usage.ru_utime) if usage is not None else None,
        "system_cpu_seconds": float(usage.ru_stime) if usage is not None else None,
        "peak_rss_bytes": int(usage.ru_maxrss) * 1024 if usage is not None else None,
        "native_threads": {
            name: int(os.environ.get(name, "1"))
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }


def _authority(*, require_output_absent: bool) -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8") if PLAN.is_file() else ""
    line = LINE.read_text(encoding="utf-8") if LINE.is_file() else ""
    checks = {
        "active_plan": "round: R460" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line
        and "status: active" in line,
        "r431_checkpoint_present": R431_CHECKPOINT.is_file(),
        "request_verified": (REQUEST / "IMPORT_NOTE.md").is_file()
        and "12/12" in (REQUEST / "IMPORT_NOTE.md").read_text(encoding="utf-8"),
    }
    if require_output_absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _contract() -> dict[str, Any]:
    source = r431.build_contract()
    evaluation = [p for p in source["profiles"] if p["split"] == "evaluation"]
    jobs: list[dict[str, Any]] = []
    for profile in evaluation:
        for scenario in profile["scenarios"]:
            jobs.append(
                {
                    "job_id": f"{profile['profile_id']}|{scenario['scenario_id']}",
                    "profile": profile,
                    "scenario": scenario,
                }
            )
    if len(jobs) != 24:
        raise RuntimeError(f"expected 24 R431 evaluation jobs, got {len(jobs)}")
    learner = source["learner_contract"]
    return {
        "schema_version": 1,
        "round": ROUND,
        "source_round": "R431",
        "object_id": "Object A",
        "policy_seed": POLICY_SEED,
        "steps": STEPS,
        "slew_limit": SLEW_LIMIT,
        "obs_dim_per_agent": 7,
        "action_dim_per_agent": 2,
        "agent_count": 4,
        "augmented_state": "[obs_t, previous_executed_action_t]",
        "entropy_semantics": ENTROPY_SEMANTICS,
        "gamma": float(learner["gamma"]),
        "hidden_sizes": HIDDEN_SIZES,
        "jobs": jobs,
    }


def _job(job_id: str) -> dict[str, Any]:
    for candidate in _contract()["jobs"]:
        if candidate["job_id"] == job_id:
            return candidate
    raise ValueError(f"unknown R460 job id: {job_id}")


def _make_team() -> list[ExecutedActionSACAgent]:
    torch.manual_seed(POLICY_SEED)
    np.random.seed(POLICY_SEED)
    torch.set_num_threads(1)
    return [
        ExecutedActionSACAgent(
            obs_dim=7,
            action_dim=2,
            hidden_sizes=HIDDEN_SIZES,
            slew_limit=SLEW_LIMIT,
            gamma=float(_contract()["gamma"]),
            device="cpu",
        )
        for _ in range(4)
    ]


def _save_team(path: Path, agents: list[ExecutedActionSACAgent]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    torch.save(
        {
            "schema_version": 1,
            "round": ROUND,
            "kind": "fixed-untrained-executed-action-sac-team",
            "policy_seed": POLICY_SEED,
            "training_executed": False,
            "entropy_semantics": ENTROPY_SEMANTICS,
            "agents": [
                {
                    "actor": agent.actor.state_dict(),
                    "critic": agent.critic.state_dict(),
                    "critic_target": agent.critic_target.state_dict(),
                    "log_alpha": agent.log_alpha.detach().cpu(),
                }
                for agent in agents
            ],
        },
        str(path),
    )
    return _sha256(path)


def _load_team(path: Path) -> list[ExecutedActionSACAgent]:
    agents = _make_team()
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload.get("kind") != "fixed-untrained-executed-action-sac-team":
        raise ValueError("invalid R460 policy checkpoint")
    for agent, entry in zip(agents, payload["agents"], strict=True):
        agent.actor.load_state_dict(entry["actor"])
        agent.critic.load_state_dict(entry["critic"])
        agent.critic_target.load_state_dict(entry["critic_target"])
        agent.log_alpha.data = entry["log_alpha"].to(agent.device)
    return agents


def _reward_components(
    joint_obs: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, float]]]:
    rows = np.asarray(joint_obs, dtype=np.float32).reshape(4, 7)
    mean_delta_m = float(np.mean(delta_m))
    mean_delta_d = float(np.mean(delta_d))
    reward_contract = r431.build_contract()["adapted_sac_contract"]["reward"]
    delta_m_denominator = float(reward_contract["delta_m_denominator"])
    delta_d_denominator = float(reward_contract["delta_d_denominator"])
    r_h = -(mean_delta_m / delta_m_denominator) ** 2
    r_d = -(mean_delta_d / delta_d_denominator) ** 2
    totals = np.asarray(
        r431._sac_step_rewards(joint_obs, delta_m, delta_d, masked=False),
        dtype=np.float32,
    )
    components: list[dict[str, float]] = []
    for index in range(4):
        own = float(rows[index, 1]) * 3.0 / (2.0 * np.pi)
        neighbours = [
            float(rows[index, 3 + offset]) * 3.0 / (2.0 * np.pi)
            for offset in range(2)
        ]
        mean_frequency = (own + sum(neighbours)) / 3.0
        r_f = -(own - mean_frequency) ** 2 - sum(
            (value - mean_frequency) ** 2 for value in neighbours
        )
        r_abs = -(own**2)
        calculated = (
            float(reward_contract["phi_f"]) * r_f
            + float(reward_contract["phi_abs"]) * r_abs
            + float(reward_contract["phi_h"]) * r_h
            + float(reward_contract["phi_d"]) * r_d
        )
        components.append(
            {
                "r_f_unweighted": r_f,
                "r_abs_unweighted": r_abs,
                "r_h_unweighted": r_h,
                "r_d_unweighted": r_d,
                "phi_f": float(reward_contract["phi_f"]),
                "phi_abs": float(reward_contract["phi_abs"]),
                "phi_h": float(reward_contract["phi_h"]),
                "phi_d": float(reward_contract["phi_d"]),
                "delta_m_denominator": delta_m_denominator,
                "delta_d_denominator": delta_d_denominator,
                "calculated_total": calculated,
                "stored_total": float(totals[index]),
                "calculated_minus_stored": calculated - float(totals[index]),
            }
        )
    return totals, components


def _projection_mode(previous: np.ndarray, raw: np.ndarray) -> dict[str, Any]:
    amplitude = np.clip(raw, -1.0, 1.0).astype(np.float32)
    amplitude_active = np.abs(raw) > 1.0
    slew_active = np.abs(amplitude - previous) > SLEW_LIMIT
    return {
        "amplitude_active_mask": amplitude_active.astype(int).tolist(),
        "slew_active_mask": slew_active.astype(int).tolist(),
        "active_mode_id": (
            f"amplitude-{int(np.any(amplitude_active))}__slew-{int(np.any(slew_active))}"
        ),
    }


def _target_audit(
    agents: list[ExecutedActionSACAgent],
    obs_rows: np.ndarray,
    previous: np.ndarray,
    executed: np.ndarray,
    next_rows: np.ndarray,
    rewards: np.ndarray,
    terminal: bool,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index, agent in enumerate(agents):
        state = torch.from_numpy(
            augment_state_numpy(obs_rows[index], previous[index])
        ).unsqueeze(0)
        next_state = torch.from_numpy(
            augment_state_numpy(next_rows[index], executed[index])
        ).unsqueeze(0)
        executed_tensor = torch.from_numpy(executed[index]).unsqueeze(0)
        with torch.no_grad():
            q1_current, q2_current = agent.critic(state, executed_tensor)
            target_raw = agent.actor.deterministic(next_state)
            target_projected = project_action_torch(
                executed_tensor, target_raw, slew_limit=SLEW_LIMIT
            )
            q1_target, q2_target = agent.critic_target(
                next_state, target_projected
            )
            td_target = float(rewards[index]) + agent.gamma * (
                0.0 if terminal else 1.0
            ) * float(torch.minimum(q1_target, q2_target).item())
        records.append(
            {
                "agent_id": index,
                "replay_obs": obs_rows[index].astype(float).tolist(),
                "replay_prev_executed_action": previous[index].astype(float).tolist(),
                "replay_raw_action": None,
                "replay_action": executed[index].astype(float).tolist(),
                "replay_reward": float(rewards[index]),
                "replay_next_obs": next_rows[index].astype(float).tolist(),
                "replay_done": bool(terminal),
                "target_actor_raw_action": target_raw.squeeze(0).numpy().astype(float).tolist(),
                "target_projected_action": target_projected.squeeze(0).numpy().astype(float).tolist(),
                "critic_current_action_input": executed[index].astype(float).tolist(),
                "critic_target_action_input": target_projected.squeeze(0).numpy().astype(float).tolist(),
                "q1_current": float(q1_current.item()),
                "q2_current": float(q2_current.item()),
                "q1_target": float(q1_target.item()),
                "q2_target": float(q2_target.item()),
                "td_target": td_target,
                "target_entropy_term": 0.0,
                "target_entropy_note": "deterministic evaluation audit; training entropy semantics are raw_policy_entropy_regularizer",
            }
        )
    return {
        "entropy_semantics": ENTROPY_SEMANTICS,
        "agents": records,
    }


def _run_trajectory(
    job: dict[str, Any],
    *,
    agents: list[ExecutedActionSACAgent],
    step_limit: int,
) -> dict[str, Any]:
    profile = job["profile"]
    scenario = job["scenario"]
    env = r431._build_env(profile)
    rows: list[dict[str, Any]] = []
    failure: str | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        previous = np.zeros((4, 2), dtype=np.float32)
        initial_frequency = (
            np.asarray(env._get_vsg_omega(), dtype=float)
            * float(env.andes_nominal_frequency_hz)
        ).tolist()
        for step_index in range(step_limit):
            joint = np.asarray(r431._joint_obs(observation), dtype=np.float32)
            obs_rows = joint.reshape(4, 7)
            raw = np.stack(
                [
                    agent.select_raw_action(
                        obs_rows[index], previous[index], deterministic=True
                    )
                    for index, agent in enumerate(agents)
                ]
            ).astype(np.float32)
            amplitude = np.clip(raw, -1.0, 1.0).astype(np.float32)
            executed = project_action_numpy(previous, raw, slew_limit=SLEW_LIMIT)
            action_dict = {
                index: executed[index].copy() for index in range(4)
            }
            next_observation, env_rewards, done, info = env.step(action_dict)
            next_joint = np.asarray(
                r431._joint_obs(next_observation), dtype=np.float32
            )
            next_rows = next_joint.reshape(4, 7)
            tds_failed = bool(info["tds_failed"])
            terminal = bool(done) or tds_failed
            delta_m = np.asarray(info["delta_M"], dtype=np.float64)
            delta_d = np.asarray(info["delta_D"], dtype=np.float64)
            stored_rewards, reward_components = _reward_components(
                joint, delta_m, delta_d
            )
            audit = _target_audit(
                agents,
                obs_rows,
                previous,
                executed,
                next_rows,
                stored_rewards,
                terminal,
            )
            for index, entry in enumerate(audit["agents"]):
                entry["replay_raw_action"] = raw[index].astype(float).tolist()
            mode = _projection_mode(previous, raw)
            rows.append(
                {
                    "run_id": f"R460|{job['job_id']}",
                    "object_id": "A",
                    "arm_id": "fixed_untrained_executed_action_sac_message",
                    "profile_bank_id": "R431-complete-evaluation-bank",
                    "profile_id": str(profile["profile_id"]),
                    "scenario_id": str(scenario["scenario_id"]),
                    "training_seed": None,
                    "policy_initialization_seed": POLICY_SEED,
                    "environment_seed": None,
                    "episode_id": job["job_id"],
                    "step_index": step_index,
                    "time_s": float(info["time"]),
                    "obs_t": joint.astype(float).tolist(),
                    "previous_executed_action": previous.astype(float).tolist(),
                    "raw_policy_action": raw.astype(float).tolist(),
                    "amplitude_clipped_action": amplitude.astype(float).tolist(),
                    "executed_action": executed.astype(float).tolist(),
                    "physical_command": {
                        "delta_M": delta_m.tolist(),
                        "delta_D": delta_d.tolist(),
                        "M_es": np.asarray(info["M_es"], dtype=float).tolist(),
                        "D_es": np.asarray(info["D_es"], dtype=float).tolist(),
                    },
                    "actuator_hidden_state_before": previous.astype(float).tolist(),
                    "actuator_hidden_state_after": executed.astype(float).tolist(),
                    **mode,
                    "reward_total": stored_rewards.astype(float).tolist(),
                    "reward_components": reward_components,
                    "environment_reward": [
                        float(env_rewards[index]) for index in range(4)
                    ],
                    "next_obs": next_joint.astype(float).tolist(),
                    "freq_hz_physical": np.asarray(
                        info["freq_hz_physical"], dtype=float
                    ).tolist(),
                    "omega": np.asarray(info["omega"], dtype=float).tolist(),
                    "omega_dot": np.asarray(info["omega_dot"], dtype=float).tolist(),
                    "P_es": np.asarray(info["P_es"], dtype=float).tolist(),
                    "completed": bool(done and not tds_failed),
                    "valid": bool(not tds_failed and np.all(np.isfinite(next_joint))),
                    "tds_failed": tds_failed,
                    "done": terminal,
                    "termination_reason": "TDS failed" if tds_failed else ("horizon" if done else None),
                    "target_audit": audit,
                }
            )
            previous = executed.copy()
            observation = next_observation
            if tds_failed:
                failure = "TDS failed"
                break
        return {
            "schema_version": 1,
            "round": ROUND,
            "job_id": job["job_id"],
            "object_id": "A",
            "profile_id": str(profile["profile_id"]),
            "scenario_id": str(scenario["scenario_id"]),
            "pair_kind": str(scenario["pair_kind"]),
            "sign": str(scenario["sign"]),
            "magnitude": float(scenario["magnitude"]),
            "delta_u": dict(scenario["delta_u"]),
            "initial_frequency_hz": initial_frequency,
            "training_executed": False,
            "policy_role": "fixed untrained diagnostic policy; semantics evidence only",
            "entropy_semantics": ENTROPY_SEMANTICS,
            "rows": rows,
            "attempted_steps": len(rows),
            "completed": failure is None and len(rows) == step_limit,
            "tds_failed": failure is not None,
            "failure": failure,
        }
    finally:
        try:
            env.close()
        except Exception:
            pass


def _semantic_tests() -> dict[str, Any]:
    rng = np.random.default_rng(460)
    previous = rng.uniform(-1.0, 1.0, size=(1024, 2)).astype(np.float32)
    raw = rng.uniform(-4.0, 4.0, size=(1024, 2)).astype(np.float32)
    numpy_projected = project_action_numpy(previous, raw, slew_limit=SLEW_LIMIT)
    torch_projected = project_action_torch(
        torch.from_numpy(previous), torch.from_numpy(raw), slew_limit=SLEW_LIMIT
    ).numpy()
    torch_error = float(np.max(np.abs(numpy_projected - torch_projected)))

    runtime = PerVSGMDActionProjector(action_slew_limit=SLEW_LIMIT)
    previous_joint = np.zeros((4, 2), dtype=np.float32)
    runtime_error = 0.0
    multistep_rows = []
    for index, raw_joint in enumerate(
        rng.uniform(-3.0, 3.0, size=(64, 4, 2)).astype(np.float32)
    ):
        expected = runtime.project(raw_joint)
        actual = project_action_numpy(
            previous_joint, raw_joint, slew_limit=SLEW_LIMIT
        )
        error = float(np.max(np.abs(expected - actual)))
        runtime_error = max(runtime_error, error)
        multistep_rows.append(
            {
                "step": index,
                "previous": previous_joint.astype(float).tolist(),
                "raw": raw_joint.astype(float).tolist(),
                "executed": actual.astype(float).tolist(),
                "runtime_error": error,
            }
        )
        previous_joint = actual.copy()

    obs = np.asarray([0.3, -0.2], dtype=np.float32)
    exogenous = np.asarray([0.01, -0.02], dtype=np.float32)
    transition_raw = np.asarray([1.0, -1.0], dtype=np.float32)

    def toy_transition(prev: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
        executed = project_action_numpy(prev, transition_raw, slew_limit=SLEW_LIMIT)
        next_obs = 0.8 * obs + 0.25 * executed + exogenous
        reward = -float(np.dot(next_obs, next_obs)) - 0.1 * float(np.dot(executed, executed))
        return executed, reward, next_obs

    full_prev = np.asarray([-0.5, 0.5], dtype=np.float32)
    first = toy_transition(full_prev)
    second = toy_transition(full_prev)
    determinism_error = max(
        float(np.max(np.abs(first[0] - second[0]))),
        abs(first[1] - second[1]),
        float(np.max(np.abs(first[2] - second[2]))),
    )
    alias_a = toy_transition(np.asarray([-1.0, -1.0], dtype=np.float32))
    alias_b = toy_transition(np.asarray([1.0, 1.0], dtype=np.float32))
    aliasing_gap = float(np.max(np.abs(alias_a[2] - alias_b[2])))

    rewards = np.asarray([1.0, 0.5, -0.2, 0.3], dtype=np.float64)
    gamma = 0.9
    hand_returns = np.zeros_like(rewards)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        running = float(rewards[index]) + gamma * running
        hand_returns[index] = running
    td_targets = rewards.copy()
    td_targets[:-1] += gamma * hand_returns[1:]
    toy_error = float(np.max(np.abs(td_targets - hand_returns)))

    agent = _make_team()[0]
    obs7 = np.linspace(-0.2, 0.2, 7, dtype=np.float32)
    prev2 = np.asarray([0.5, -0.5], dtype=np.float32)
    raw2 = np.asarray([-0.8, 0.8], dtype=np.float32)
    executed2 = agent.execute_action(prev2, raw2)
    agent.store_transition(obs7, prev2, raw2, executed2, 0.4, obs7 + 0.01, False)
    batch = agent.buffer.sample(1, "cpu", indices=np.asarray([0]))
    torch.manual_seed(460)
    paths = agent.loss_inputs(batch)
    critic_current_error = float(
        torch.max(
            torch.abs(paths["critic_current_action_input"] - batch["executed_actions"])
        ).item()
    )
    critic_target_error = float(
        torch.max(
            torch.abs(paths["critic_target_action_input"] - paths["target_projected_action"])
        ).item()
    )
    actor_critic_error = float(
        torch.max(
            torch.abs(paths["actor_critic_action_input"] - paths["actor_projected_action"])
        ).item()
    )
    next_prev_error = float(
        torch.max(
            torch.abs(paths["next_state"][:, -2:] - batch["executed_actions"])
        ).item()
    )
    passed = bool(
        torch_error <= 1.0e-7
        and runtime_error <= 1.0e-7
        and determinism_error <= 1.0e-12
        and aliasing_gap > 1.0e-6
        and toy_error <= 1.0e-6
        and critic_current_error <= 1.0e-7
        and critic_target_error <= 1.0e-7
        and actor_critic_error <= 1.0e-7
        and next_prev_error <= 1.0e-7
    )
    return {
        "schema_version": 1,
        "round": ROUND,
        "projector_numpy_torch_max_abs_error": torch_error,
        "runtime_numpy_projector_max_abs_error": runtime_error,
        "multistep_projector_reconstruction_max_abs_error": runtime_error,
        "next_prev_identity_max_abs_error": next_prev_error,
        "full_state_determinism_max_abs_error": determinism_error,
        "full_state_determinism_pass": determinism_error <= 1.0e-12,
        "deleted_previous_action_aliasing_next_state_gap": aliasing_gap,
        "deleted_previous_action_aliasing_pass": aliasing_gap > 1.0e-6,
        "toy_rewards": rewards.tolist(),
        "toy_hand_returns": hand_returns.tolist(),
        "toy_td_targets": td_targets.tolist(),
        "toy_hand_return_td_target_abs_error": toy_error,
        "critic_current_input_error": critic_current_error,
        "critic_target_input_error": critic_target_error,
        "actor_critic_input_error": actor_critic_error,
        "critic_current_uses_executed": critic_current_error <= 1.0e-7,
        "critic_target_uses_projected": critic_target_error <= 1.0e-7,
        "actor_critic_uses_projected": actor_critic_error <= 1.0e-7,
        "entropy_semantics": ENTROPY_SEMANTICS,
        "executed_entropy_claimed": False,
        "multistep_rows": multistep_rows,
        "passed": passed,
    }


def _historical_audit() -> dict[str, Any]:
    result_candidates = []
    for path in sorted(R431_OUT.rglob("*")):
        if not path.is_file():
            continue
        lower = path.name.lower()
        if "replay" in lower or "buffer" in lower or path.suffix.lower() == ".npz":
            result_candidates.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    checkpoint = torch.load(R431_CHECKPOINT, map_location="cpu", weights_only=True)
    checkpoint_keys = sorted(str(key) for key in checkpoint.keys())
    source_lines = R431_RUNNER.read_text(encoding="utf-8").splitlines()
    mismatch_lines = [
        {
            "line": index + 1,
            "text": line.strip(),
        }
        for index, line in enumerate(source_lines)
        if "agent.store(" in line or "joint, raw, per_agent_rewards" in line
    ]
    replay_present = bool(result_candidates) or any(
        "buffer" in key.lower() or "replay" in key.lower()
        for key in checkpoint_keys
    )
    return {
        "schema_version": 1,
        "round": ROUND,
        "source_round": "R431",
        "r431_result_root": R431_OUT.relative_to(ROOT).as_posix(),
        "r431_result_root_file_count": sum(1 for p in R431_OUT.rglob("*") if p.is_file()),
        "replay_artifact_candidates": result_candidates,
        "checkpoint_path": R431_CHECKPOINT.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": _sha256(R431_CHECKPOINT),
        "checkpoint_top_level_keys": checkpoint_keys,
        "historical_replay_status": (
            "available" if replay_present else "historical_bias_not_reconstructible"
        ),
        "reason": None if replay_present else "original replay transitions unavailable",
        "exact_historical_bias_reported": False,
        "mismatch_source_locations": mismatch_lines,
        "historical_runner_sha256": _sha256(R431_RUNNER),
    }


def probe(job_id: str, steps: int) -> dict[str, Any]:
    _assert_wsl_scratch()
    start = time.perf_counter()
    payload = _run_trajectory(_job(job_id), agents=_make_team(), step_limit=steps)
    return {
        "round": ROUND,
        "formal_authority": False,
        "mode": "capacity-probe",
        "job_id": job_id,
        "attempted_steps": payload["attempted_steps"],
        "tds_failed": payload["tds_failed"],
        "resources": _resources(start),
    }


def rehearse() -> dict[str, Any]:
    _assert_wsl_scratch()
    authority = _authority(require_output_absent=True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed before rehearsal: {authority}")
    if REHEARSAL.exists():
        raise FileExistsError(REHEARSAL)
    start = time.perf_counter()
    semantic = _semantic_tests()
    historical = _historical_audit()
    representative = _run_trajectory(
        _contract()["jobs"][0], agents=_make_team(), step_limit=3
    )
    passed = bool(
        semantic["passed"]
        and representative["attempted_steps"] > 0
        and historical["exact_historical_bias_reported"] is False
    )
    payload = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": _utc(),
        "formal_authority": False,
        "training_executed": False,
        "same_pre_attempt_path": True,
        "authority": authority,
        "semantic_tests": semantic,
        "historical_audit": historical,
        "representative_trace": representative,
        "resources": _resources(start),
        "passed": passed,
    }
    _write_json_new(REHEARSAL, payload)
    return payload


def rehearse_v2() -> dict[str, Any]:
    """Preserve the first rehearsal and rerun after its reward-ledger correction."""

    _assert_wsl_scratch()
    authority = _authority(require_output_absent=True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed before corrected rehearsal: {authority}")
    if not REHEARSAL.is_file() or not REHEARSAL_AMENDMENT.is_file():
        raise FileNotFoundError("original rehearsal and amendment are required")
    if REHEARSAL_V2.exists():
        raise FileExistsError(REHEARSAL_V2)
    amendment = _read_json(REHEARSAL_AMENDMENT)
    if amendment.get("original_rehearsal_sha256") != _sha256(REHEARSAL):
        raise RuntimeError("rehearsal amendment does not bind the original")
    start = time.perf_counter()
    semantic = _semantic_tests()
    historical = _historical_audit()
    representative = _run_trajectory(
        _contract()["jobs"][0], agents=_make_team(), step_limit=3
    )
    reward_errors = [
        abs(float(component["calculated_minus_stored"]))
        for row in representative["rows"]
        for component in row["reward_components"]
    ]
    reward_error = max(reward_errors, default=float("inf"))
    passed = bool(
        semantic["passed"]
        and representative["attempted_steps"] > 0
        and historical["exact_historical_bias_reported"] is False
        and reward_error <= 1.0e-6
    )
    payload = {
        "schema_version": 2,
        "round": ROUND,
        "created_utc": _utc(),
        "formal_authority": False,
        "training_executed": False,
        "same_pre_attempt_path": True,
        "supersedes_rehearsal_for_seal": REHEARSAL.relative_to(ROOT).as_posix(),
        "original_rehearsal_sha256": _sha256(REHEARSAL),
        "amendment_sha256": _sha256(REHEARSAL_AMENDMENT),
        "authority": authority,
        "semantic_tests": semantic,
        "historical_audit": historical,
        "representative_trace": representative,
        "reward_component_max_abs_error": reward_error,
        "resources": _resources(start),
        "passed": passed,
    }
    _write_json_new(REHEARSAL_V2, payload)
    return payload


def _runtime_manifest() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "created_utc": _utc(),
        "python": sys.version,
        "python_executable": sys.executable,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "andes": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256(case_path),
        "threads": {name: os.environ.get(name) for name in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"
        )},
    }


def prepare() -> dict[str, Any]:
    _assert_wsl_scratch()
    authority = _authority(require_output_absent=True)
    if not all(authority.values()):
        raise RuntimeError(f"authority failed before formal prepare: {authority}")
    if SEAL.exists():
        raise FileExistsError(SEAL)
    rehearsal = _read_json(REHEARSAL_V2)
    amendment = _read_json(REHEARSAL_AMENDMENT)
    runtime_amendment = _read_json(PRESEAL_RUNTIME_AMENDMENT)
    capacity = _read_json(CAPACITY)
    if not rehearsal.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    if rehearsal.get("original_rehearsal_sha256") != _sha256(REHEARSAL):
        raise RuntimeError("corrected rehearsal does not bind original rehearsal")
    if rehearsal.get("amendment_sha256") != _sha256(REHEARSAL_AMENDMENT):
        raise RuntimeError("corrected rehearsal does not bind amendment")
    if amendment.get("corrected_rehearsal") != REHEARSAL_V2.relative_to(ROOT).as_posix():
        raise RuntimeError("amendment does not name corrected rehearsal")
    if runtime_amendment.get("corrected_rehearsal_sha256") != _sha256(REHEARSAL_V2):
        raise RuntimeError("runtime amendment does not bind corrected rehearsal")
    if runtime_amendment.get("scientific_path_affected") is not False:
        raise RuntimeError("runtime amendment is not provenance-only")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("capacity evidence is not RUN-READY")
    sources = {
        name: {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(path),
        }
        for name, path in SOURCE_PATHS.items()
    }
    contract = _contract()
    seal = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": _utc(),
        "formal_authority": True,
        "training_executed": False,
        "authority": authority,
        "plan_sha256": _sha256(PLAN),
        "capacity_sha256": _sha256(CAPACITY),
        "original_rehearsal_sha256": _sha256(REHEARSAL),
        "rehearsal_amendment_sha256": _sha256(REHEARSAL_AMENDMENT),
        "rehearsal_sha256": _sha256(REHEARSAL_V2),
        "preseal_runtime_amendment_sha256": _sha256(PRESEAL_RUNTIME_AMENDMENT),
        "r431_checkpoint_sha256": _sha256(R431_CHECKPOINT),
        "request_sha256sums_sha256": _sha256(REQUEST / "SHA256SUMS"),
        "contract_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "runtime": _runtime_manifest(),
        "sources": sources,
        "formal_allocation": capacity["formal_allocation"],
        "completion": {
            "required_verdict": "EXECUTION-SEMANTICS-VALID",
            "trajectory_count": 24,
            "output_root": OUT.relative_to(ROOT).as_posix(),
        },
    }
    _write_json_new(SEAL, seal)
    OUT.mkdir(parents=True, exist_ok=False)
    _write_json_new(OUT / "contracts/formal_contract.json", contract)
    _write_json_new(
        OUT / "contracts/trace_metadata.json",
        {
            "schema_version": 1,
            "row_semantics": "one joint Object A transition",
            "array_dtype": "float64 JSON rendering from float32 runtime unless noted",
            "channel_order": {
                "obs_t": "agent-major 4x7 flattened",
                "action": "agent-major 4x2",
                "physical_command": "GENCLS1..4",
            },
            "units": {
                "normalized_action": "dimensionless",
                "time_s": "s",
                "frequency": "Hz",
                "delta_M": "GENCLS M=2H seconds",
                "delta_D": "GENCLS damping pu",
            },
            "entropy_semantics": ENTROPY_SEMANTICS,
        },
    )
    _write_json_new(OUT / "checks/semantic_tests.json", _semantic_tests())
    _write_json_new(OUT / "historical/r431_replay_inventory.json", _historical_audit())
    policy_sha = _save_team(OUT / "inputs/successor_policy.pt", _make_team())
    _write_text_new(
        OUT / "inputs/successor_policy.pt.sha256",
        f"{policy_sha}  successor_policy.pt\n",
    )
    _write_json_new(
        OUT / "provenance/source_hashes.json", seal["sources"]
    )
    _write_json_new(OUT / "provenance/runtime.json", seal["runtime"])
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, check=True,
        text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
    ).stdout
    _write_text_new(OUT / "provenance/git_status_porcelain.txt", status)
    diff = subprocess.run(
        ["git", "diff", "--binary", "--no-ext-diff", "HEAD"], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    ).stdout
    path = OUT / "provenance/git_diff.patch"
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(diff)
    jobs = [entry["job_id"] for entry in contract["jobs"]]
    _write_json_new(OUT / "contracts/shards.json", jobs)
    return {"seal_sha256": _sha256(SEAL), "policy_sha256": policy_sha, "jobs": jobs}


def _load_seal() -> dict[str, Any]:
    seal = _read_json(SEAL)
    if seal.get("round") != ROUND or not seal.get("formal_authority"):
        raise RuntimeError("invalid R460 formal seal")
    for path, expected in (
        (PLAN, seal["plan_sha256"]),
        (CAPACITY, seal["capacity_sha256"]),
        (REHEARSAL, seal["original_rehearsal_sha256"]),
        (REHEARSAL_AMENDMENT, seal["rehearsal_amendment_sha256"]),
        (REHEARSAL_V2, seal["rehearsal_sha256"]),
        (PRESEAL_RUNTIME_AMENDMENT, seal["preseal_runtime_amendment_sha256"]),
        (R431_CHECKPOINT, seal["r431_checkpoint_sha256"]),
    ):
        if _sha256(path) != expected:
            raise RuntimeError(f"sealed input drift: {path}")
    for name, entry in seal["sources"].items():
        if _sha256(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {name}")
    return seal


def _safe_name(job_id: str) -> str:
    return job_id.replace("|", "__").replace("/", "_")


def shard(job_id: str) -> dict[str, Any]:
    _assert_wsl_scratch()
    _load_seal()
    start = time.perf_counter()
    job = _job(job_id)
    policy = OUT / "inputs/successor_policy.pt"
    result = _run_trajectory(job, agents=_load_team(policy), step_limit=STEPS)
    result["resources"] = _resources(start)
    result["policy_sha256"] = _sha256(policy)
    path = OUT / "trajectories" / f"{_safe_name(job_id)}.json"
    _write_json_new(path, result)
    rows = result["rows"]
    numeric_path = OUT / "trajectories_numeric" / f"{_safe_name(job_id)}.npz"
    numeric_path.parent.mkdir(parents=True, exist_ok=True)
    if numeric_path.exists():
        raise FileExistsError(numeric_path)
    np.savez_compressed(
        numeric_path,
        obs_t=np.asarray([row["obs_t"] for row in rows], dtype=np.float32),
        previous_executed_action=np.asarray(
            [row["previous_executed_action"] for row in rows], dtype=np.float32
        ),
        raw_policy_action=np.asarray(
            [row["raw_policy_action"] for row in rows], dtype=np.float32
        ),
        amplitude_clipped_action=np.asarray(
            [row["amplitude_clipped_action"] for row in rows], dtype=np.float32
        ),
        executed_action=np.asarray(
            [row["executed_action"] for row in rows], dtype=np.float32
        ),
        next_obs=np.asarray([row["next_obs"] for row in rows], dtype=np.float32),
        reward_total=np.asarray(
            [row["reward_total"] for row in rows], dtype=np.float32
        ),
        delta_M=np.asarray(
            [row["physical_command"]["delta_M"] for row in rows], dtype=np.float64
        ),
        delta_D=np.asarray(
            [row["physical_command"]["delta_D"] for row in rows], dtype=np.float64
        ),
        freq_hz_physical=np.asarray(
            [row["freq_hz_physical"] for row in rows], dtype=np.float64
        ),
    )
    _write_text_new(
        Path(f"{numeric_path}.sha256"), f"{_sha256(numeric_path)}  {numeric_path.name}\n"
    )
    return {
        "job_id": job_id,
        "trajectory_sha256": _sha256(path),
        "numeric_sha256": _sha256(numeric_path),
        "attempted_steps": result["attempted_steps"],
        "tds_failed": result["tds_failed"],
        "resources": result["resources"],
    }


def _retrospective(rows: list[dict[str, Any]]) -> dict[str, Any]:
    historical = r431._agent_for("cd_matd3_message", "cpu")
    historical.load(R431_CHECKPOINT)
    action_gaps: list[float] = []
    target_action_gaps: list[float] = []
    target_q_gaps: list[float] = []
    samples: list[dict[str, Any]] = []
    for row in rows[: min(128, len(rows))]:
        joint = np.asarray(row["obs_t"], dtype=np.float32)
        next_joint = np.asarray(row["next_obs"], dtype=np.float32)
        previous = np.asarray(row["previous_executed_action"], dtype=np.float32)
        historical_raw = historical.act(joint, deterministic=True)
        historical_executed = project_action_numpy(
            previous, historical_raw, slew_limit=SLEW_LIMIT
        )
        action_gap = float(np.linalg.norm(historical_raw - historical_executed))
        action_gaps.append(action_gap)
        per_agent = []
        for index, agent in enumerate(historical.agents):
            next_obs_tensor = torch.from_numpy(next_joint.reshape(4, 7)[index]).unsqueeze(0)
            with torch.no_grad():
                target_raw = agent.actor.deterministic(next_obs_tensor)
                target_projected = project_action_torch(
                    torch.from_numpy(historical_executed[index]).unsqueeze(0),
                    target_raw,
                    slew_limit=SLEW_LIMIT,
                )
                q1_raw, q2_raw = agent.critic_target(next_obs_tensor, target_raw)
                q1_projected, q2_projected = agent.critic_target(
                    next_obs_tensor, target_projected
                )
                q_raw = float(torch.minimum(q1_raw, q2_raw).item())
                q_projected = float(torch.minimum(q1_projected, q2_projected).item())
            target_gap = float(
                torch.linalg.vector_norm(target_raw - target_projected).item()
            )
            q_gap = q_projected - q_raw
            target_action_gaps.append(target_gap)
            target_q_gaps.append(q_gap)
            per_agent.append(
                {
                    "agent_id": index,
                    "target_raw": target_raw.squeeze(0).numpy().astype(float).tolist(),
                    "target_projected": target_projected.squeeze(0).numpy().astype(float).tolist(),
                    "target_action_l2_gap": target_gap,
                    "target_q_raw": q_raw,
                    "target_q_projected": q_projected,
                    "target_q_difference_projected_minus_raw": q_gap,
                }
            )
        samples.append(
            {
                "run_id": row["run_id"],
                "step_index": row["step_index"],
                "historical_raw_action": historical_raw.astype(float).tolist(),
                "historical_projected_action": historical_executed.astype(float).tolist(),
                "current_action_l2_gap": action_gap,
                "target": per_agent,
            }
        )

    def summary(values: list[float]) -> dict[str, float]:
        array = np.asarray(values, dtype=np.float64)
        return {
            "count": int(array.size),
            "mean": float(np.mean(array)),
            "std": float(np.std(array)),
            "min": float(np.min(array)),
            "p50": float(np.quantile(array, 0.5)),
            "p95": float(np.quantile(array, 0.95)),
            "max": float(np.max(array)),
        }

    return {
        "schema_version": 1,
        "round": ROUND,
        "diagnostic_kind": "retrospective_one_step_on_new_frozen_state_bank",
        "exact_historical_training_bias": False,
        "historical_replay_status": "historical_bias_not_reconstructible",
        "reason": "original replay transitions unavailable",
        "checkpoint_path": R431_CHECKPOINT.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": _sha256(R431_CHECKPOINT),
        "state_sample_count": len(samples),
        "current_action_l2_gap": summary(action_gaps),
        "target_action_l2_gap": summary(target_action_gaps),
        "target_q_difference_projected_minus_raw": summary(target_q_gaps),
        "samples": samples,
    }


def _write_sha256sums(root: Path) -> int:
    excluded = {
        "checks/SHA256SUMS",
        "checks/verification_report.json",
        "checks/verification_report.json.sha256",
    }
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append(f"{_sha256(path)}  {relative}")
    _write_text_new(root / "checks/SHA256SUMS", "\n".join(rows) + "\n")
    return len(rows)


def _verify(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    expected_jobs = [entry["job_id"] for entry in contract["jobs"]]
    files = {
        _read_json(root / "trajectories" / f"{_safe_name(job)}.json")["job_id"]:
        _read_json(root / "trajectories" / f"{_safe_name(job)}.json")
        for job in expected_jobs
    }
    rows = [row for job in expected_jobs for row in files[job]["rows"]]
    continuity_error = 0.0
    replay_error = 0.0
    target_error = 0.0
    mapping_error = 0.0
    for job in expected_jobs:
        previous = np.zeros((4, 2), dtype=np.float32)
        for row in files[job]["rows"]:
            row_previous = np.asarray(row["previous_executed_action"], dtype=np.float32)
            executed = np.asarray(row["executed_action"], dtype=np.float32)
            raw = np.asarray(row["raw_policy_action"], dtype=np.float32)
            continuity_error = max(
                continuity_error, float(np.max(np.abs(row_previous - previous)))
            )
            expected = project_action_numpy(row_previous, raw, slew_limit=SLEW_LIMIT)
            replay_error = max(replay_error, float(np.max(np.abs(expected - executed))))
            dm_expected = np.where(executed[:, 0] >= 0.0, executed[:, 0] * 600.0, executed[:, 0] * 200.0)
            dd_expected = np.where(executed[:, 1] >= 0.0, executed[:, 1] * 600.0, executed[:, 1] * 200.0)
            mapping_error = max(
                mapping_error,
                float(np.max(np.abs(dm_expected - np.asarray(row["physical_command"]["delta_M"])))),
                float(np.max(np.abs(dd_expected - np.asarray(row["physical_command"]["delta_D"])))),
            )
            for audit in row["target_audit"]["agents"]:
                target_error = max(
                    target_error,
                    float(np.max(np.abs(
                        np.asarray(audit["critic_target_action_input"])
                        - np.asarray(audit["target_projected_action"])
                    ))),
                    float(np.max(np.abs(
                        np.asarray(audit["critic_current_action_input"])
                        - executed[int(audit["agent_id"])]
                    ))),
                )
            previous = executed.copy()
    semantic = _read_json(root / "checks/semantic_tests.json")
    historical = _read_json(root / "historical/r431_replay_inventory.json")
    retrospective = _read_json(root / "historical/r431_retrospective_diagnostic.json")
    hash_failures = []
    for line in (root / "checks/SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        if _sha256(root / relative) != expected:
            hash_failures.append(relative)
    passed = bool(
        len(files) == 24
        and len(rows) > 0
        and semantic["passed"]
        and continuity_error <= 1.0e-7
        and replay_error <= 1.0e-7
        and target_error <= 1.0e-7
        and mapping_error <= 1.0e-5
        and historical["historical_replay_status"]
        == "historical_bias_not_reconstructible"
        and retrospective["exact_historical_training_bias"] is False
        and not hash_failures
    )
    return {
        "trajectory_count": len(files),
        "transition_count": len(rows),
        "completed_trajectory_count": sum(bool(files[job]["completed"]) for job in expected_jobs),
        "tds_failed_trajectory_count": sum(bool(files[job]["tds_failed"]) for job in expected_jobs),
        "continuity_max_abs_error": continuity_error,
        "projector_replay_max_abs_error": replay_error,
        "critic_action_identity_max_abs_error": target_error,
        "physical_mapping_max_abs_error": mapping_error,
        "semantic_tests_passed": bool(semantic["passed"]),
        "historical_replay_status": historical["historical_replay_status"],
        "exact_historical_training_bias_reported": retrospective["exact_historical_training_bias"],
        "hash_failures": hash_failures,
        "passed": passed,
    }


def consolidate() -> dict[str, Any]:
    _assert_wsl_scratch()
    seal = _load_seal()
    start = time.perf_counter()
    contract = _contract()
    trajectories = []
    all_rows = []
    for entry in contract["jobs"]:
        path = OUT / "trajectories" / f"{_safe_name(entry['job_id'])}.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = _read_json(path)
        trajectories.append(
            {
                "job_id": payload["job_id"],
                "sha256": _sha256(path),
                "attempted_steps": payload["attempted_steps"],
                "completed": payload["completed"],
                "tds_failed": payload["tds_failed"],
                "resources": payload["resources"],
            }
        )
        all_rows.extend(payload["rows"])
    _write_json_new(OUT / "checks/trajectory_index.json", trajectories)
    transition_lines = []
    target_lines = []
    for transition_id, row in enumerate(all_rows):
        flattened = dict(row)
        audit = flattened.pop("target_audit")
        flattened["transition_row_id"] = transition_id
        transition_lines.append(json.dumps(flattened, ensure_ascii=False, sort_keys=True))
        for agent in audit["agents"]:
            target_lines.append(
                json.dumps(
                    {
                        "transition_row_id": transition_id,
                        "run_id": row["run_id"],
                        "step_index": row["step_index"],
                        "entropy_semantics": audit["entropy_semantics"],
                        **agent,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    _write_text_new(
        OUT / "traces/transition_trace.jsonl", "\n".join(transition_lines) + "\n"
    )
    _write_text_new(
        OUT / "traces/target_audit.jsonl", "\n".join(target_lines) + "\n"
    )
    _write_json_new(OUT / "historical/r431_retrospective_diagnostic.json", _retrospective(all_rows))
    _write_json_new(
        OUT / "provenance/formal_command.json",
        {
            "round": ROUND,
            "created_utc": _utc(),
            "seal_sha256": _sha256(SEAL),
            "allocation": seal["formal_allocation"],
            "training_executed": False,
            "resources": _resources(start),
        },
    )
    hashed_entries = _write_sha256sums(OUT)
    verification = _verify(OUT, contract)
    report = {
        "schema_version": 1,
        "round": ROUND,
        "created_utc": _utc(),
        "training_executed": False,
        "policy_performance_claimed": False,
        "verification": verification,
        "hashed_entries": hashed_entries,
        "resources": _resources(start),
        "passed": bool(verification["passed"]),
        "verdict": (
            "EXECUTION-SEMANTICS-VALID"
            if verification["passed"]
            else "EXECUTION-SEMANTICS-INVALID"
        ),
    }
    _write_json_new(OUT / "checks/verification_report.json", report)
    if not report["passed"]:
        raise RuntimeError(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("probe", "rehearse", "rehearse-v2", "prepare", "shard", "consolidate")
    )
    parser.add_argument("job_id", nargs="?")
    parser.add_argument("--steps", type=int, default=3)
    args = parser.parse_args()
    if args.command == "probe":
        if args.job_id is None:
            raise SystemExit("probe requires a registered job id")
        payload = probe(args.job_id, args.steps)
    elif args.command == "rehearse":
        payload = rehearse()
    elif args.command == "rehearse-v2":
        payload = rehearse_v2()
    elif args.command == "prepare":
        payload = prepare()
    elif args.command == "shard":
        if args.job_id is None:
            raise SystemExit("shard requires a registered job id")
        payload = shard(args.job_id)
    else:
        payload = consolidate()
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
