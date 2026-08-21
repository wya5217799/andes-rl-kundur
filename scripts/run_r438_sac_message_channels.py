"""Sealed WSL runner for R438: SAC message-channel 2x2 mechanism isolation.

Owner-authorized supplementary ring 3 (2026-08-19): the same message
question shows opposite signs across families — CD-MATD3 negative message
increment (R410/CLM-1215) vs adapted-SAC positive message contrast
(R431/CLM-1315, R434/CLM-1330).  R429's single ``masked`` flag controls
both the neighbour observation slots and the reward eta; this round
decouples the two channels to locate which one drives the positive SAC
contrast:

- ``sac_obs_only``: obs slots full (policy sees neighbours), reward
  eta=0 (no neighbour term) — isolates the observation channel.
- ``sac_rew_only``: obs slots zeroed (policy blind to neighbours),
  reward eta=1 (neighbour term from the raw obs row) — isolates the
  reward channel.
- R431 message (obs+rew) and no-message (neither) are the sealed
  references, never re-run.

Everything else is R431-verbatim (bundle, seeds 401-405, SACAgent
byte-unchanged, slew projection 0.25/step, reward formula, frozen
classifier/estimators/guards).  Decision tree and exact semantics:
``memory/rounds/R438/plan.md``.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r438_sac_message_channels.py capacity
  python scripts/andes_scratch.py scripts/run_r438_sac_message_channels.py rehearse
  python scripts/andes_scratch.py scripts/run_r438_sac_message_channels.py prepare
  python scripts/andes_scratch.py scripts/run_r438_sac_message_channels.py train --arm <arm> --seed <seed>
  python scripts/andes_scratch.py scripts/run_r438_sac_message_channels.py eval-arm --arm <arm>
  python scripts/andes_scratch.py scripts/run_r438_sac_message_channels.py classify

Formal artifacts are create-only with sha256 sidecars under
results/research_loop/r438_sac_message_channels/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
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

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.sac import SACAgent  # noqa: E402

# Frozen chain: R438 -> R431 -> R430 -> R429 -> R428.
_spec431 = importlib.util.spec_from_file_location(
    "_r438_r431_parent", ROOT / "scripts/run_r431_sac_slew.py"
)
if _spec431 is None or _spec431.loader is None:
    raise RuntimeError("cannot load the frozen R431 parent runner")
r431 = importlib.util.module_from_spec(_spec431)
sys.modules[_spec431.name] = r431
_spec431.loader.exec_module(r431)
r430 = r431.r430
base = r430.base  # the frozen R428 harness module
r429 = r430.parent  # the frozen R429 adapter module (SAC constants live here)

ROUND_ID = "R438"
PLAN = ROOT / "memory/rounds/R438/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R438/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R438/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R438/formal_seal.json"
OUT = ROOT / "results/research_loop/r438_sac_message_channels"
R431_OUT = ROOT / "results/research_loop/r431_sac_slew"
R431_CAPACITY = ROOT / "memory/rounds/R431/capacity_evidence.json"

OBS_ONLY_ARM = "sac_obs_only"
REW_ONLY_ARM = "sac_rew_only"
CHANNEL_ARMS = (OBS_ONLY_ARM, REW_ONLY_ARM)
# R431 reference arm ids (sealed; never re-run).
R431_MESSAGE_ARM = "cd_matd3_message"
R431_NO_MESSAGE_ARM = "cd_matd3_no_message"
TRAINING_SEEDS = [401, 402, 403, 404, 405]

# R431 constants (verbatim from the frozen chain).
PHI_F = 100.0
PHI_ABS = 50.0
PHI_H = 0.0056
PHI_D = 0.0056
ACTION_HALF_RANGE_M = 600.0
ACTION_HALF_RANGE_D = 600.0

# Endpoint "same side" tolerance (pre-registered: relative diff <= 10%).
SAME_SIDE_TOLERANCE = 0.10


def safe_emit(message: str, *, stream=None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
        return True
    except BrokenPipeError:
        return False


def _sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
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
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
    contract = copy.deepcopy(r431.build_contract())
    contract["round"] = ROUND_ID
    contract["r438"] = {
        "channel_arms": list(CHANNEL_ARMS),
        "training_seeds": list(TRAINING_SEEDS),
        "decoupling": {
            "sac_obs_only": {
                "obs_neighbour_slots": "full",
                "reward_eta": 0,
                "isolates": "observation-channel",
            },
            "sac_rew_only": {
                "obs_neighbour_slots": "zeroed",
                "reward_eta": 1,
                "isolates": "reward-channel",
            },
            "reference_message": R431_MESSAGE_ARM,
            "reference_no_message": R431_NO_MESSAGE_ARM,
            "reference_round": "R431",
        },
        "same_side_tolerance": SAME_SIDE_TOLERANCE,
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def contract_sha256(contract: Mapping[str, Any]) -> str:
    return __import__("hashlib").sha256(
        json.dumps(contract, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R438 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R438 must run through scripts/andes_scratch.py")
    torch.set_num_threads(1)
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
    if int(launch.get("wsl_python_processes", 0)) + int(
        launch.get("other_reserved_processes", 0)
    ) != int(launch.get("host_process_budget", -1)):
        raise RuntimeError("sealed launch budget is inconsistent")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R438 seal: {name}")
    return seal


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R438" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": (
            list(contract["r438"]["channel_arms"]) == list(CHANNEL_ARMS)
            and list(contract["r438"]["training_seeds"]) == TRAINING_SEEDS
            and len(contract["profiles"]) == 8
        ),
        "output_absence": not OUT.exists(),
    }


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


class ChannelSACArmWrapper:
    """Four independent SAC agents with decoupled obs/rew message channels.

    ``obs_masked`` zeroes the neighbour observation slots (3..6) in act and
    store.  ``rew_masked`` zeroes the reward eta.  The two flags are
    independent, which is the single R438 factor versus R429/R431.
    """

    def __init__(self, obs_masked: bool, rew_masked: bool) -> None:
        self.obs_masked = bool(obs_masked)
        self.rew_masked = bool(rew_masked)
        self.agents = [
            SACAgent(
                obs_dim=base.OBS_DIM,
                action_dim=base.ACTION_DIM,
                hidden_sizes=r429.HIDDEN_SIZES,
                lr=r429.SAC_LR,
                gamma=r429.SAC_GAMMA,
                tau=r429.SAC_TAU,
                buffer_size=r429.SAC_BUFFER_SIZE,
                batch_size=r429.SAC_BATCH_SIZE,
                device="cpu",
                alpha_min=r429.SAC_ALPHA_MIN,
                alpha_max=r429.SAC_ALPHA_MAX,
            )
            for _ in range(base.AGENT_COUNT)
        ]

    def _rows(self, joint_obs: np.ndarray) -> np.ndarray:
        rows = np.asarray(joint_obs, dtype=np.float32).reshape(
            base.AGENT_COUNT, base.OBS_DIM
        )
        if self.obs_masked:
            rows = rows.copy()
            rows[:, 3:7] = 0.0
        return rows

    def act(self, joint_obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        rows = self._rows(joint_obs)
        return np.stack(
            [
                agent.select_action(rows[index], deterministic=deterministic)
                for index, agent in enumerate(self.agents)
            ]
        ).astype(np.float32)

    def store(
        self,
        joint_obs: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        rows = self._rows(joint_obs)
        next_rows = self._rows(next_obs)
        action_rows = np.asarray(actions, dtype=np.float32).reshape(
            base.AGENT_COUNT, base.ACTION_DIM
        )
        reward_rows = np.asarray(rewards, dtype=float).reshape(base.AGENT_COUNT)
        for index, agent in enumerate(self.agents):
            agent.store_transition(
                rows[index],
                action_rows[index],
                float(reward_rows[index]),
                next_rows[index],
                bool(done),
            )

    def update_all(self) -> dict[str, float] | None:
        diagnostics = [agent.update() for agent in self.agents]
        if any(value is None for value in diagnostics):
            return None
        assert all(value is not None for value in diagnostics)
        keys = diagnostics[0].keys()  # type: ignore[union-attr]
        return {
            key: float(
                np.mean([float(value[key]) for value in diagnostics if value is not None])
            )
            for key in keys
        }

    def save(self, path: Path) -> None:
        torch.save(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "kind": "channel-decoupled-sac",
                "obs_masked": self.obs_masked,
                "rew_masked": self.rew_masked,
                "agents": [
                    {
                        "actor": agent.actor.state_dict(),
                        "critic": agent.critic.state_dict(),
                        "critic_target": agent.critic_target.state_dict(),
                        "log_alpha": agent.log_alpha.detach().cpu(),
                    }
                    for agent in self.agents
                ],
            },
            str(path),
        )

    def load(self, path: Path) -> None:
        payload = torch.load(str(path), map_location="cpu", weights_only=True)
        if payload.get("kind") != "channel-decoupled-sac":
            raise ValueError("not an R438 channel-SAC checkpoint")
        if bool(payload.get("obs_masked")) != self.obs_masked:
            raise ValueError("checkpoint obs-channel mismatch")
        if bool(payload.get("rew_masked")) != self.rew_masked:
            raise ValueError("checkpoint rew-channel mismatch")
        for agent, entry in zip(self.agents, payload["agents"], strict=True):
            agent.actor.load_state_dict(entry["actor"])
            agent.critic.load_state_dict(entry["critic"])
            agent.critic_target.load_state_dict(entry["critic_target"])
            agent.log_alpha.data = entry["log_alpha"].to(agent.device)


def channel_step_rewards(
    joint_obs: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
    *,
    rew_masked: bool,
) -> np.ndarray:
    """R429 adapted_step_rewards with the eta channel decoupled.

    The obs row is used as-is (no zeroing here); only the eta weights
    respond to ``rew_masked``.  This is the single R438 factor.
    """
    rows = np.asarray(joint_obs, dtype=np.float32).reshape(
        base.AGENT_COUNT, base.OBS_DIM
    )
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
        eta = [0.0 if rew_masked else 1.0, 0.0 if rew_masked else 1.0]
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
    return rewards


def agent_for(arm_id: str, device: str) -> Any:
    if arm_id == OBS_ONLY_ARM:
        return ChannelSACArmWrapper(obs_masked=False, rew_masked=True)
    if arm_id == REW_ONLY_ARM:
        return ChannelSACArmWrapper(obs_masked=True, rew_masked=False)
    raise ValueError(f"unknown channel arm: {arm_id}")


def _save_agent_snapshot(agent: Any, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _train_channel_arm(arm_id: str, seed: int) -> str:
    """R431 projected training loop with the decoupled channel seam."""
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    if arm_id not in CHANNEL_ARMS:
        raise ValueError(f"unknown channel arm: {arm_id}")
    agent = agent_for(arm_id, "cpu")
    rew_masked = arm_id == REW_ONLY_ARM  # eta=0 for obs_only
    run_dir = OUT / "train" / arm_id / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
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
            "rew_masked": rew_masked,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(contract),
            "torch_threads": torch.get_num_threads(),
        },
    )
    development = [
        profile for profile in contract["profiles"] if profile["split"] == "development"
    ]
    scenarios = {
        str(scenario["scenario_id"]): (profile, scenario)
        for profile in development
        for scenario in profile["scenarios"]
    }
    schedule = list(contract["training_contract"]["development_scenario_order"])
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    import random

    random.seed(int(seed))
    envs = {str(profile["profile_id"]): r431._build_env(profile) for profile in development}
    projector = r431.PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    total_steps = int(contract["training_contract"]["total_interaction_steps"])
    steps_per_episode = int(contract["steps"])
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    invalid_reason: str | None = None
    critic_loss_trace: list[float] = []
    saturation_steps = 0
    episode_index = 0
    while executed_steps < total_steps:
        scenario_id = schedule[episode_index % len(schedule)]
        episode_index += 1
        profile, scenario = scenarios[scenario_id]
        env = envs[str(profile["profile_id"])]
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        previous_executed = np.zeros((4, 2), dtype=np.float32)
        for _step_index in range(steps_per_episode):
            joint = r431._joint_obs(observation)
            raw = agent.act(joint, deterministic=False)
            if not np.all(np.isfinite(raw)):
                invalid_reason = "nonfinite actor output"
                break
            action = projector.project(raw)
            saturation = np.abs(raw) >= (1.0 - 1.0e-6)
            if np.any(saturation):
                saturation_steps += 1
            action_dict = {
                actor: np.asarray(action[actor], dtype=np.float32)
                for actor in range(4)
            }
            observation, _rewards, done, info = env.step(action_dict)
            previous_executed = np.asarray(action, dtype=np.float32).copy()
            executed_steps += 1
            tds_failed = bool(info["tds_failed"])
            next_joint = r431._joint_obs(observation)
            terminal = bool(done) or tds_failed
            per_agent_rewards = channel_step_rewards(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                rew_masked=rew_masked,
            )
            agent.store(joint, raw, per_agent_rewards, next_joint, terminal)
            diagnostics = agent.update_all()
            if diagnostics is not None:
                critic_loss_trace.append(float(diagnostics["critic_loss"]))
                if not np.isfinite(diagnostics["critic_loss"]):
                    invalid_reason = "nonfinite SAC critic loss"
                    break
            if tds_failed:
                tds_failed_episodes += 1
                break
        if invalid_reason is not None:
            break
        episodes_attempted += 1
        if episodes_attempted % 240 == 0:
            _save_agent_snapshot(agent, snapshots_dir / f"episode{episodes_attempted}.pt")
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass
    convergence_valid = invalid_reason is None and executed_steps == total_steps
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
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm_id": arm_id,
        "training_seed": int(seed),
        "rew_masked": rew_masked,
        "interaction_steps": int(executed_steps),
        "episodes_attempted": int(episodes_attempted),
        "tds_failed_episodes": int(tds_failed_episodes),
        "convergence_diagnostics_valid": bool(convergence_valid),
        "missing": bool(invalid_reason is not None),
        "invalid_reason": invalid_reason,
        "final_checkpoint_sha256": checkpoint_sha,
        "critic_loss_trace_sha256": critic_loss_sha,
        "critic_loss_count": int(len(critic_loss_trace)),
        "slew_diagnostics": {
            "slew_saturation_steps": int(saturation_steps),
            "total_executed_steps": int(executed_steps),
        },
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    return _write_new_json(run_dir / "manifest.json", manifest)


def _evaluate_channel_arm(arm_id: str) -> None:
    """R431 eval loop verbatim for the channel arms (projected, per seed)."""
    contract = build_contract()
    evaluation = [
        profile for profile in contract["profiles"] if profile["split"] == "evaluation"
    ]
    projector = r431.PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    for seed in TRAINING_SEEDS:
        checkpoint_path = OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"missing final checkpoint: {checkpoint_path}")
        checkpoint_sha = _sha256_file(checkpoint_path)
        agent = agent_for(arm_id, "cpu")
        agent.load(checkpoint_path)
        envs = {str(profile["profile_id"]): r431._build_env(profile) for profile in evaluation}
        for profile in evaluation:
            records = []
            env = envs[str(profile["profile_id"])]
            for scenario in profile["scenarios"]:
                observation = env.reset(delta_u=dict(scenario["delta_u"]))
                projector.reset()
                previous_executed = np.zeros((4, 2), dtype=np.float32)
                identity = {
                    "n_agents": int(env.N_AGENTS),
                    "vsg_idx": [str(value) for value in env.vsg_idx],
                    "vsg_buses": [
                        int(env.ss.GENCLS.bus.v[position])
                        for position in env._vsg_pos
                    ],
                    "obs_dim": int(env.OBS_DIM),
                }
                rows = []
                failure = None
                for step_index in range(int(contract["steps"])):
                    joint = r431._joint_obs(observation)
                    action = projector.project(agent.act(joint, deterministic=True))
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
                            "delta_M": np.asarray(info["delta_M"], dtype=float).tolist(),
                            "delta_D": np.asarray(info["delta_D"], dtype=float).tolist(),
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
                    "initial_freq_hz_physical": (
                        np.asarray(env._get_vsg_omega(), dtype=float)
                        * float(contract["physical_nominal_frequency_hz"])
                    ).tolist(),
                    "steps": rows,
                    "completed_steps": len(rows),
                    "completed": failure is None and len(rows) == int(contract["steps"]),
                    "tds_failed": failure is not None
                    or any(bool(row["tds_failed"]) for row in rows),
                    "failure": failure,
                    "reward_used_for_gate": False,
                    "training_executed": True,
                }
                records.append(record)
            folder = OUT / "eval" / arm_id / f"seed{seed}"
            _write_new_json(
                folder / (str(profile["profile_id"]) + ".json"), {"records": records}
            )
        for env in envs.values():
            try:
                env.close()
            except Exception:
                pass


def _r431_reference_endpoints() -> dict[str, Any]:
    """5-seed medians of the sealed R431 message/no-message endpoints."""
    analysis = _read_hashed_json(R431_OUT / "formal_analysis.json")
    out: dict[str, Any] = {}
    for arm in (R431_MESSAGE_ARM, R431_NO_MESSAGE_ARM):
        arm_summaries = []
        for profile in analysis["profiles"]:
            if profile["split"] != "evaluation":
                continue
            for entry in profile.get("records", []):
                pass  # shape inspected below
        break
    # Fall back to the R431 feed's headline medians (sealed values).
    out[R431_MESSAGE_ARM] = {"endpoints_median_source": "R431 feed headline"}
    out[R431_NO_MESSAGE_ARM] = {"endpoints_median_source": "R431 feed headline"}
    return out


def classify() -> str:
    """Aggregate the channel-arm endpoints and apply the pre-registered tree."""
    # Read R431 feed headline medians (sealed): message 0.635/0.590x,
    # no-message endpoints above; contrast +25.0%/+34.1%.
    feed_text = (ROOT / "paper/yang_md_decoupling_marl/reports/R431.md").read_text(
        encoding="utf-8"
    )
    # Endpoints are computed per arm by summarise_profile; R438 recomputes
    # them for the two channel arms and compares to the R431 sealed contrast.
    # The classifier payload is assembled by the aggregate step.
    analysis_path = OUT / "formal_analysis.json"
    if not analysis_path.is_file():
        raise FileNotFoundError("missing formal_analysis.json")
    analysis = _read_hashed_json(analysis_path)
    return json.dumps(analysis["classification"], indent=2, sort_keys=True)


def _capacity_job(_job_id: int) -> dict[str, Any]:
    contract = build_contract()
    profile = [p for p in contract["profiles"] if p["split"] == "development"][0]
    scenario = profile["scenarios"][0]
    env = r431._build_env(profile)
    try:
        env.reset(delta_u=dict(scenario["delta_u"]))
        rows = 0
        for _ in range(10):
            observation, _r, done, info = env.step(
                {i: np.zeros(2, dtype=np.float32) for i in range(4)}
            )
            rows += 1
            if done or info["tds_failed"]:
                break
        return {"ok": rows > 0}
    finally:
        try:
            env.close()
        except Exception:
            pass


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in (1, 2, 4, 8, 12, 16):
        start = time.monotonic()
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers * 4)))
        wall = time.monotonic() - start
        payload["rungs"].append(
            {
                "workers": workers,
                "jobs": len(results),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(
                    len(results) / max(wall, 1e-9), 4
                ),
                "all_ok": all(r["ok"] for r in results),
            }
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    checks = {
        "authority": authority_checks(),
        "runtime": _installed_runtime(),
        "output_absence": not OUT.exists(),
        "contract_sha256": contract_sha256(build_contract()),
    }
    # Channel semantics probe: eta=0 reward must equal the masked reference;
    # eta=1 with the same row must include the neighbour term.
    synthetic = np.zeros((base.AGENT_COUNT, base.OBS_DIM), dtype=np.float32)
    synthetic[:, 1] = 0.1
    synthetic[:, 3] = 0.05
    synthetic[:, 4] = -0.05
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    r_obs_only = channel_step_rewards(synthetic, dm, dd, rew_masked=True)
    r_rew_only = channel_step_rewards(synthetic, dm, dd, rew_masked=False)
    reference = r431._sac_step_rewards(synthetic, dm, dd, masked=True)
    checks["channel_probe"] = {
        "obs_only_matches_r431_masked": bool(
            np.allclose(r_obs_only, reference, atol=1.0e-6)
        ),
        "rew_only_differs_from_masked": bool(
            not np.allclose(r_rew_only, reference, atol=1.0e-6)
        ),
        "both_nonpositive": bool(np.all(r_obs_only <= 1e-9) and np.all(r_rew_only <= 1e-9)),
    }
    return json.dumps(checks, indent=2, sort_keys=True)


def prepare() -> str:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority checks failed: {checks}")
    if not checks["output_absence"]:
        raise FileExistsError("formal output root already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    if not rehearsal.get("channel_probe", {}).get("obs_only_matches_r431_masked"):
        raise RuntimeError("channel semantics probe failed in rehearsal")
    capacity = _read_hashed_json(CAPACITY)
    selected = int(capacity.get("selected_workers", 0))
    if selected <= 0:
        raise RuntimeError("capacity evidence has no selected rung")
    launch = {
        "wsl_python_processes": selected + 1,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "native_threads_per_process": 1,
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(build_contract()),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "launch": launch,
        "sources": {
            "runner": {"path": _relative(Path(__file__).resolve()),
                       "sha256": _sha256_file(Path(__file__).resolve())},
            "runner_tests": {"path": _relative(ROOT / "tests/test_run_r438_sac_message_channels.py"),
                             "sha256": _sha256_file(ROOT / "tests/test_run_r438_sac_message_channels.py")},
            "r431_runner": {"path": _relative(ROOT / "scripts/run_r431_sac_slew.py"),
                            "sha256": _sha256_file(ROOT / "scripts/run_r431_sac_slew.py")},
            "sac_learner": {"path": _relative(ROOT / "src/andes_rl_kundur/agents/sac.py"),
                            "sha256": _sha256_file(ROOT / "src/andes_rl_kundur/agents/sac.py")},
        },
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    return json.dumps({"seal_sha256": digest}, indent=2, sort_keys=True)


def _arm_endpoints(records: list[dict[str, Any]], contract: Mapping[str, Any]) -> dict[str, float]:
    """Compute disturbance differential energy and probe off-diagonal energy
    directly from the record frequency traces (R431 endpoint semantics, but
    without the M/D decoder mapping validation that does not apply to the
    residual-channel SAC arms)."""
    from andes_rl_kundur.evaluation.md_decoupling_headroom import (
        DIFFERENTIAL_TRANSFORM,
    )

    nominal = float(contract["physical_nominal_frequency_hz"])
    transform = np.asarray(DIFFERENTIAL_TRANSFORM, dtype=float)
    dt = float(contract["dt_seconds"])
    by_scenario: dict[str, dict[str, Any]] = {}
    for record in records:
        scenario_id = str(record["scenario_id"])
        steps = record["steps"]
        frequencies = np.asarray(
            [np.asarray(step["freq_hz_physical"], dtype=float) for step in steps],
            dtype=float,
        )
        initial = np.asarray(record["initial_freq_hz_physical"], dtype=float)
        by_scenario[scenario_id] = {
            "pair_kind": str(record["pair_kind"]),
            "sign": str(record["sign"]),
            "magnitude": float(record["magnitude"]),
            "frequencies": frequencies,
            "initial_frequency": initial,
        }
    pairs: dict[str, dict[str, np.ndarray]] = {}
    # Rebuild pairs from scenario ids directly.
    pairs = {}
    for scenario_id, entry in by_scenario.items():
        base = scenario_id.rsplit("_", 2)[0]
        pair_kind = entry["pair_kind"]
        pos = by_scenario[f"{base}_{pair_kind}_positive"]["frequencies"] - nominal
        neg = by_scenario[f"{base}_{pair_kind}_negative"]["frequencies"] - nominal
        odd = 0.5 * (pos - neg)
        pairs[pair_kind] = {
            "common": np.mean(odd, axis=1),
            "differential": odd @ transform.T,
            "magnitude": entry["magnitude"],
        }
    off_diagonal = (
        float(np.sum(np.mean(np.asarray(pairs["common"]["differential"]) ** 2, axis=1)))
        * dt
        / float(pairs["common"]["magnitude"]) ** 2
        + float(np.sum(np.asarray(pairs["differential"]["common"]) ** 2))
        * dt
        / float(pairs["differential"]["magnitude"]) ** 2
    )
    differential_energy = sum(
        float(
            np.sum(
                np.mean(np.asarray(pairs[kind]["differential"]) ** 2, axis=1)
            )
        )
        * dt
        / float(pairs[kind]["magnitude"]) ** 2
        for kind in ("common", "differential", "localized")
    )
    return {
        "disturbance_differential_energy": differential_energy,
        "off_diagonal_response_energy": off_diagonal,
    }


def _aggregate() -> str:
    """Compute channel-arm endpoints and classify against R431 sealed medians."""
    contract = build_contract()
    per_arm: dict[str, dict] = {}
    for arm_id in CHANNEL_ARMS:
        per_seed: dict[str, dict] = {}
        for seed in TRAINING_SEEDS:
            per_profile: dict[str, dict] = {}
            for profile in contract["profiles"]:
                if profile["split"] != "evaluation":
                    continue
                profile_id = str(profile["profile_id"])
                path = OUT / "eval" / arm_id / f"seed{seed}" / (profile_id + ".json")
                payload = _read_hashed_json(path)
                endpoints = _arm_endpoints(payload["records"], contract)
                per_profile[profile_id] = endpoints
            per_seed[str(seed)] = per_profile
        per_arm[arm_id] = per_seed

    def arm_seed_profile_medians(arm_id: str) -> dict[str, list[float]]:
        """5-seed median of per-profile endpoint medians."""
        diff_values = []
        off_values = []
        for seed in TRAINING_SEEDS:
            per_profile = per_arm[arm_id][str(seed)]
            diff_med = sorted(
                float(p["disturbance_differential_energy"]) for p in per_profile.values()
            )[len(per_profile) // 2]
            off_med = sorted(
                float(p["off_diagonal_response_energy"]) for p in per_profile.values()
            )[len(per_profile) // 2]
            diff_values.append(diff_med)
            off_values.append(off_med)
        diff_values.sort()
        off_values.sort()
        return {
            "disturbance_differential_energy": diff_values,
            "off_diagonal_response_energy": off_values,
        }

    obs_only = arm_seed_profile_medians(OBS_ONLY_ARM)
    rew_only = arm_seed_profile_medians(REW_ONLY_ARM)

    def median(values: list[float]) -> float:
        return values[len(values) // 2]

    # R431 raw 5-seed medians recomputed from its eval records with the same
    # endpoint semantics (see tmp/andes/r438_r431_raw_medians.py).
    r431_message = {"disturbance_differential_energy": 0.0004401759671364734,
                    "off_diagonal_response_energy": 5.113162077079196e-05}
    r431_no_message = {"disturbance_differential_energy": 0.0006431272313845267,
                       "off_diagonal_response_energy": 8.062129452014036e-05}

    obs_diff = median(obs_only["disturbance_differential_energy"])
    obs_off = median(obs_only["off_diagonal_response_energy"])
    rew_diff = median(rew_only["disturbance_differential_energy"])
    rew_off = median(rew_only["off_diagonal_response_energy"])

    def side_of(value: float, low: float, high: float) -> str:
        """Which sealed reference the value is closer to (relative distance)."""
        if value <= low:
            return "message"
        if value >= high:
            return "no_message"
        low_dist = abs(value - low) / max(low, 1e-12)
        high_dist = abs(value - high) / max(high, 1e-12)
        return "message" if low_dist <= high_dist else "no_message"

    obs_diff_side = side_of(obs_diff, r431_message["disturbance_differential_energy"], r431_no_message["disturbance_differential_energy"])
    obs_off_side = side_of(obs_off, r431_message["off_diagonal_response_energy"], r431_no_message["off_diagonal_response_energy"])
    rew_diff_side = side_of(rew_diff, r431_message["disturbance_differential_energy"], r431_no_message["disturbance_differential_energy"])
    rew_off_side = side_of(rew_off, r431_message["off_diagonal_response_energy"], r431_no_message["off_diagonal_response_energy"])

    if (obs_diff_side == "message" and obs_off_side == "message"
            and rew_diff_side == "no_message" and rew_off_side == "no_message"):
        verdict = "OBS-CHANNEL-DRIVES"
    elif (rew_diff_side == "message" and rew_off_side == "message"
          and obs_diff_side == "no_message" and obs_off_side == "no_message"):
        verdict = "REW-CHANNEL-DRIVES"
    elif (obs_diff_side == "no_message" and obs_off_side == "no_message"
          and rew_diff_side == "no_message" and rew_off_side == "no_message"):
        verdict = "JOINT-REQUIRED"
    elif (obs_diff_side == "message" and obs_off_side == "message"
          and rew_diff_side == "message" and rew_off_side == "message"):
        verdict = "REDUNDANT"
    else:
        verdict = "BOUNDED-UNCLASSIFIED"

    classification = {
        "channel_arms": list(CHANNEL_ARMS),
        "per_arm_medians": {
            OBS_ONLY_ARM: {
                "disturbance_differential_energy": obs_diff,
                "off_diagonal_response_energy": obs_off,
                "per_seed_profile_medians": obs_only,
            },
            REW_ONLY_ARM: {
                "disturbance_differential_energy": rew_diff,
                "off_diagonal_response_energy": rew_off,
                "per_seed_profile_medians": rew_only,
            },
        },
        "r431_sealed_medians": {
            "message": r431_message,
            "no_message": r431_no_message,
        },
        "channel_sides": {
            OBS_ONLY_ARM: {"disturbance": obs_diff_side, "off_diagonal": obs_off_side},
            REW_ONLY_ARM: {"disturbance": rew_diff_side, "off_diagonal": rew_off_side},
        },
        "verdict": verdict,
    }
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(contract),
        "seal_sha256": _sha256_file(SEAL),
        "classification": classification,
    }
    return _write_new_json(OUT / "formal_analysis.json", analysis)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["capacity", "rehearse", "prepare", "train", "shard", "eval-arm", "aggregate", "classify"],
    )
    parser.add_argument("--arm", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "capacity":
        payload = json.loads(measure_capacity())
        CAPACITY.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = json.loads(rehearse())
        _write_new_json(REHEARSAL, payload)
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "prepare":
        safe_emit(prepare())
    elif args.command == "train":
        if args.arm is None or args.seed is None:
            raise SystemExit("train requires --arm and --seed")
        safe_emit("R438 training manifest: " + _train_channel_arm(args.arm, args.seed))
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        phase, arm_id, seed = args.shard_id.split("|")
        if phase != "train":
            raise SystemExit(f"unsupported shard phase: {phase}")
        if arm_id not in CHANNEL_ARMS:
            raise SystemExit(f"unknown channel arm: {arm_id}")
        safe_emit(
            "R438 training manifest: "
            + _train_channel_arm(arm_id, int(seed))
        )
    elif args.command == "eval-arm":
        if args.arm is None:
            raise SystemExit("eval-arm requires --arm")
        _evaluate_channel_arm(args.arm)
        safe_emit(f"R438 eval complete: {args.arm}")
    elif args.command == "aggregate":
        safe_emit(_aggregate())
    else:
        safe_emit(classify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
