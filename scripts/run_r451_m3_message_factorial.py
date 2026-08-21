"""R451 M3: actor/critic/reward neighbour-access factorial plus shuffle placebo.

Physical commands are WSL-only and must run through ``andes_scratch.py``.
All formal outputs are create-only and carry SHA-256 sidecars.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import random
import subprocess
import sys
from collections.abc import Mapping
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
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from andes_rl_kundur.agents.sac import SACAgent

_spec = importlib.util.spec_from_file_location(
    "_r451_r438_parent", ROOT / "scripts/run_r438_sac_message_channels.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load R438 parent runner")
parent = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = parent
_spec.loader.exec_module(parent)

r431 = parent.r431
r429 = parent.r429
base = parent.base
_PARENT_BUILD_CONTRACT = parent.build_contract

ROUND_ID = "R451"
PLAN = ROOT / "memory/rounds/R451/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R451/rehearsal.json"
FAILED_REHEARSAL_V1 = ROOT / "memory/rounds/R451/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R451/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R451/formal_seal.json"
OUT = ROOT / "results/research_loop/r451_m3_message_factorial"
R438_CAPACITY = ROOT / "memory/rounds/R438/capacity_evidence.json"
TRAIN_SHARDS = ROOT / "tmp/andes/r451_train_shards.json"
EVAL_SHARDS = ROOT / "tmp/andes/r451_eval_shards.json"

TRAINING_SEEDS = (401, 402, 403, 404, 405)
FACTORIAL_ARMS = tuple(
    f"a{actor}_c{critic}_r{reward}"
    for actor in (0, 1)
    for critic in (0, 1)
    for reward in (0, 1)
)
SHUFFLED_ARM = "a1_c1_r1_shuffled"
ARMS = FACTORIAL_ARMS + (SHUFFLED_ARM,)
NEIGHBOUR_SLICE = slice(3, 7)
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 451
ANCHOR_TOLERANCE = 0.10

PHI_F = 100.0
PHI_ABS = 50.0
PHI_H = 0.0056
PHI_D = 0.0056
ACTION_HALF_RANGE_M = 600.0
ACTION_HALF_RANGE_D = 600.0

SEALED_ANCHORS = {
    "a0_c0_r0": {
        "disturbance_differential_energy": 0.0006431272313845267,
        "off_diagonal_response_energy": 8.062129452014036e-05,
        "source": "R431 no-message",
    },
    "a1_c1_r1": {
        "disturbance_differential_energy": 0.0004401759671364734,
        "off_diagonal_response_energy": 5.113162077079196e-05,
        "source": "R431 message",
    },
    "a1_c1_r0": {
        "disturbance_differential_energy": 0.0005160439825440163,
        "off_diagonal_response_energy": 6.809853001321975e-05,
        "source": "R438 obs-only",
    },
    "a0_c0_r1": {
        "disturbance_differential_energy": 0.0007094475978791034,
        "off_diagonal_response_energy": 9.068492411745009e-05,
        "source": "R438 reward-only",
    },
}


def _sha256_file(path: Path) -> str:
    return parent._sha256_file(path)


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    return parent._write_new_json(path, payload)


def _read_hashed_json(path: Path) -> dict[str, Any]:
    return parent._read_hashed_json(path)


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def safe_emit(value: Any) -> None:
    print(value, flush=True)


def arm_factors(arm_id: str) -> dict[str, bool]:
    if arm_id == SHUFFLED_ARM:
        return {
            "actor_access": True,
            "critic_access": True,
            "reward_access": True,
            "shuffled": True,
        }
    if arm_id not in FACTORIAL_ARMS:
        raise ValueError(f"unknown arm: {arm_id}")
    actor, critic, reward = arm_id.split("_")
    return {
        "actor_access": actor == "a1",
        "critic_access": critic == "c1",
        "reward_access": reward == "r1",
        "shuffled": False,
    }


def build_contract() -> dict[str, Any]:
    contract = copy.deepcopy(_PARENT_BUILD_CONTRACT())
    contract["round"] = ROUND_ID
    contract.pop("r438", None)
    contract["r451"] = {
        "factorial_arms": list(FACTORIAL_ARMS),
        "shuffled_arm": SHUFFLED_ARM,
        "training_seeds": list(TRAINING_SEEDS),
        "neighbour_slots": [3, 4, 5, 6],
        "shuffle": "rows i receive neighbour block from row (i+2) mod 4",
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "anchor_tolerance": ANCHOR_TOLERANCE,
        "reward": {
            "phi_f": PHI_F,
            "phi_abs": PHI_ABS,
            "phi_h": PHI_H,
            "phi_d": PHI_D,
            "eta_off": 0.0,
            "eta_on": 1.0,
        },
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def contract_sha256(contract: Mapping[str, Any] | None = None) -> str:
    payload = build_contract() if contract is None else contract
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R451 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R451 must run through scripts/andes_scratch.py")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    return {
        "active_plan": "round: R451" in plan_text and "state: active" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": len(FACTORIAL_ARMS) == 8
        and len(ARMS) == 9
        and len(TRAINING_SEEDS) == 5,
        "output_absence": not OUT.exists(),
    }


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != contract_sha256():
        raise RuntimeError("contract drifted from seal")
    for name, entry in (seal.get("sources") or {}).items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed source drift: {name}")
    return seal


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


class SplitAccessSACAgent(SACAgent):
    """SACAgent with separate actor and critic transforms at replay update."""

    def __init__(self, *, actor_access: bool, critic_access: bool) -> None:
        super().__init__(
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
        self.actor_access = bool(actor_access)
        self.critic_access = bool(critic_access)

    @staticmethod
    def _masked_numpy(obs: np.ndarray, access: bool) -> np.ndarray:
        row = np.asarray(obs, dtype=np.float32).copy()
        if not access:
            row[..., NEIGHBOUR_SLICE] = 0.0
        return row

    @staticmethod
    def _masked_tensor(obs: torch.Tensor, access: bool) -> torch.Tensor:
        if access:
            return obs
        row = obs.clone()
        row[..., NEIGHBOUR_SLICE] = 0.0
        return row

    def select_action(self, obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        return super().select_action(
            self._masked_numpy(obs, self.actor_access), deterministic=deterministic
        )

    def update(self) -> dict[str, float] | None:
        if len(self.buffer) < self.batch_size:
            return None
        batch = self.buffer.sample(self.batch_size, self.device)
        raw_obs = batch["obs"]
        raw_next = batch["next_obs"]
        actor_obs = self._masked_tensor(raw_obs, self.actor_access)
        actor_next = self._masked_tensor(raw_next, self.actor_access)
        critic_obs = self._masked_tensor(raw_obs, self.critic_access)
        critic_next = self._masked_tensor(raw_next, self.critic_access)
        actions = batch["actions"]
        rewards = batch["rewards"]
        dones = batch["dones"]

        with torch.no_grad():
            next_actions, next_log_prob = self.actor.sample(actor_next)
            q1_target, q2_target = self.critic_target(critic_next, next_actions)
            q_target = torch.min(q1_target, q2_target)
            y = rewards + self.gamma * (1 - dones) * (
                q_target - self.alpha * next_log_prob
            )
        q1, q2 = self.critic(critic_obs, actions)
        critic_loss = F.mse_loss(q1, y) + F.mse_loss(q2, y)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), self.max_grad_norm)
        self.critic_optimizer.step()

        new_actions, log_prob = self.actor.sample(actor_obs)
        q1_new, q2_new = self.critic(critic_obs, new_actions)
        actor_loss = (self.alpha.detach() * log_prob - torch.min(q1_new, q2_new)).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        grad_sq = torch.zeros((), dtype=torch.float32)
        for parameter in self.actor.parameters():
            if parameter.grad is not None:
                grad_sq = grad_sq + torch.sum(parameter.grad.detach() ** 2)
        actor_grad_norm = float(torch.sqrt(grad_sq).cpu())
        nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
        self.actor_optimizer.step()

        alpha_loss = -(
            self.log_alpha * (log_prob.detach() + self.target_entropy)
        ).mean()
        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        nn.utils.clip_grad_norm_([self.log_alpha], self.max_grad_norm)
        self.alpha_optimizer.step()
        with torch.no_grad():
            self.log_alpha.data.clamp_(self._log_alpha_min, self._log_alpha_max)
        self._soft_update()
        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss": float(actor_loss.detach().cpu()),
            "alpha_loss": float(alpha_loss.detach().cpu()),
            "alpha": float(self.alpha.detach().cpu()),
            "actor_grad_norm": actor_grad_norm,
        }


def shuffle_neighbour_blocks(rows: np.ndarray) -> np.ndarray:
    value = np.asarray(rows, dtype=np.float32).reshape(base.AGENT_COUNT, base.OBS_DIM)
    shuffled = value.copy()
    shuffled[:, NEIGHBOUR_SLICE] = np.roll(
        value[:, NEIGHBOUR_SLICE], shift=2, axis=0
    )
    return shuffled


class FactorialSACWrapper:
    def __init__(self, arm_id: str) -> None:
        self.arm_id = arm_id
        factors = arm_factors(arm_id)
        self.actor_access = factors["actor_access"]
        self.critic_access = factors["critic_access"]
        self.reward_access = factors["reward_access"]
        self.shuffled = factors["shuffled"]
        self.agents = [
            SplitAccessSACAgent(
                actor_access=self.actor_access, critic_access=self.critic_access
            )
            for _ in range(base.AGENT_COUNT)
        ]

    def rows(self, joint_obs: np.ndarray) -> np.ndarray:
        rows = np.asarray(joint_obs, dtype=np.float32).reshape(
            base.AGENT_COUNT, base.OBS_DIM
        )
        return shuffle_neighbour_blocks(rows) if self.shuffled else rows.copy()

    def act(self, joint_obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        rows = self.rows(joint_obs)
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
        rows = self.rows(joint_obs)
        next_rows = self.rows(next_obs)
        actions = np.asarray(actions, dtype=np.float32).reshape(
            base.AGENT_COUNT, base.ACTION_DIM
        )
        rewards = np.asarray(rewards, dtype=float).reshape(base.AGENT_COUNT)
        for index, agent in enumerate(self.agents):
            agent.store_transition(
                rows[index], actions[index], float(rewards[index]), next_rows[index], done
            )

    def update_all(self) -> dict[str, float] | None:
        diagnostics = [agent.update() for agent in self.agents]
        if any(item is None for item in diagnostics):
            return None
        assert all(item is not None for item in diagnostics)
        return {
            key: float(np.mean([item[key] for item in diagnostics if item is not None]))
            for key in diagnostics[0]
        }

    def save(self, path: Path) -> None:
        torch.save(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "arm_id": self.arm_id,
                "factors": arm_factors(self.arm_id),
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
        if payload.get("arm_id") != self.arm_id:
            raise ValueError("checkpoint arm mismatch")
        for agent, entry in zip(self.agents, payload["agents"], strict=True):
            agent.actor.load_state_dict(entry["actor"])
            agent.critic.load_state_dict(entry["critic"])
            agent.critic_target.load_state_dict(entry["critic_target"])
            agent.log_alpha.data = entry["log_alpha"].to(agent.device)


def agent_for(arm_id: str, _device: str = "cpu") -> FactorialSACWrapper:
    return FactorialSACWrapper(arm_id)


def step_rewards(
    joint_obs: np.ndarray,
    delta_m: np.ndarray,
    delta_d: np.ndarray,
    *,
    reward_access: bool,
) -> np.ndarray:
    return parent.channel_step_rewards(
        joint_obs, delta_m, delta_d, rew_masked=not reward_access
    )


def _save_checkpoint(agent: FactorialSACWrapper, path: Path) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"checkpoint exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _effective_condition(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values, dtype=float)
    std = np.std(values, axis=0)
    active = std > 1.0e-12
    if not np.any(active):
        return {"rank": 0, "active_features": 0, "condition_number": 1.0}
    normalized = (values[:, active] - np.mean(values[:, active], axis=0)) / std[active]
    covariance = np.cov(normalized, rowvar=False)
    covariance = np.atleast_2d(covariance)
    singular = np.linalg.svd(covariance, compute_uv=False)
    kept = singular[singular > 1.0e-10]
    condition = float(kept.max() / kept.min()) if kept.size else 1.0
    return {
        "rank": int(kept.size),
        "active_features": int(np.sum(active)),
        "condition_number": condition,
    }


def _td_split(agent: SplitAccessSACAgent, seed: int) -> dict[str, float]:
    size = int(agent.buffer.size)
    rng = np.random.default_rng(seed)
    order = rng.permutation(size)
    split = max(1, int(0.8 * size))

    def score(indices: np.ndarray, torch_seed: int) -> float:
        torch.manual_seed(torch_seed)
        losses: list[float] = []
        for start in range(0, len(indices), 512):
            idx = indices[start : start + 512]
            obs = torch.as_tensor(agent.buffer.obs[idx], dtype=torch.float32)
            actions = torch.as_tensor(agent.buffer.actions[idx], dtype=torch.float32)
            rewards = torch.as_tensor(agent.buffer.rewards[idx], dtype=torch.float32)
            next_obs = torch.as_tensor(agent.buffer.next_obs[idx], dtype=torch.float32)
            dones = torch.as_tensor(agent.buffer.dones[idx], dtype=torch.float32)
            actor_next = agent._masked_tensor(next_obs, agent.actor_access)
            critic_next = agent._masked_tensor(next_obs, agent.critic_access)
            critic_obs = agent._masked_tensor(obs, agent.critic_access)
            with torch.no_grad():
                next_actions, next_log_prob = agent.actor.sample(actor_next)
                q1_t, q2_t = agent.critic_target(critic_next, next_actions)
                target = rewards + agent.gamma * (1 - dones) * (
                    torch.min(q1_t, q2_t) - agent.alpha * next_log_prob
                )
                q1, q2 = agent.critic(critic_obs, actions)
                losses.extend(((q1 - target) ** 2 + (q2 - target) ** 2).flatten().tolist())
        return float(np.mean(losses))

    train = score(order[:split], seed + 10_000)
    validation = score(order[split:], seed + 20_000)
    return {
        "train_td_mse": train,
        "validation_td_mse": validation,
        "validation_train_ratio": validation / max(train, 1.0e-12),
    }


def _final_diagnostics(
    agent: FactorialSACWrapper,
    seed: int,
    actor_grad_norms: list[float],
) -> dict[str, Any]:
    per_agent = []
    for index, member in enumerate(agent.agents):
        raw = member.buffer.obs[: member.buffer.size]
        actor = member._masked_numpy(raw, member.actor_access)
        critic = member._masked_numpy(raw, member.critic_access)
        per_agent.append(
            {
                "agent": index,
                "td": _td_split(member, seed + index * 100),
                "raw_features": _effective_condition(raw),
                "actor_features": _effective_condition(actor),
                "critic_features": _effective_condition(critic),
            }
        )
    return {
        "per_agent": per_agent,
        "actor_gradient_norm": {
            "count": len(actor_grad_norms),
            "mean": float(np.mean(actor_grad_norms)),
            "variance": float(np.var(actor_grad_norms)),
            "q25": float(np.quantile(actor_grad_norms, 0.25)),
            "q75": float(np.quantile(actor_grad_norms, 0.75)),
        },
        "validation_train_td_ratio_mean": float(
            np.mean([row["td"]["validation_train_ratio"] for row in per_agent])
        ),
        "active_feature_condition_max": float(
            max(
                max(row["actor_features"]["condition_number"], row["critic_features"]["condition_number"])
                for row in per_agent
            )
        ),
    }


def train_arm_seed(arm_id: str, seed: int) -> str:
    _assert_wsl_scratch()
    load_seal()
    if arm_id not in ARMS or seed not in TRAINING_SEEDS:
        raise ValueError("unregistered arm/seed")
    contract = build_contract()
    run_dir = OUT / "train" / arm_id / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    run_dir.mkdir(parents=True)
    factors = arm_factors(arm_id)
    agent = agent_for(arm_id)
    development = [p for p in contract["profiles"] if p["split"] == "development"]
    scenarios = {
        str(s["scenario_id"]): (profile, s)
        for profile in development
        for s in profile["scenarios"]
    }
    schedule = list(contract["training_contract"]["development_scenario_order"])
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    envs = {str(p["profile_id"]): r431._build_env(p) for p in development}
    projector = r431.PerVSGMDActionProjector(
        action_slew_limit=float(contract["action_slew_limit"])
    )
    total_steps = int(contract["training_contract"]["total_interaction_steps"])
    steps_per_episode = int(contract["steps"])
    executed = 0
    episode_index = 0
    tds_failures = 0
    invalid_reason: str | None = None
    critic_losses: list[float] = []
    actor_grad_norms: list[float] = []
    while executed < total_steps:
        scenario_id = schedule[episode_index % len(schedule)]
        episode_index += 1
        profile, scenario = scenarios[scenario_id]
        env = envs[str(profile["profile_id"])]
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector.reset()
        for _ in range(steps_per_episode):
            joint = r431._joint_obs(observation)
            raw_action = agent.act(joint, deterministic=False)
            if not np.all(np.isfinite(raw_action)):
                invalid_reason = "nonfinite actor output"
                break
            action = projector.project(raw_action)
            observation, _reward, done, info = env.step(
                {i: np.asarray(action[i], dtype=np.float32) for i in range(4)}
            )
            executed += 1
            next_joint = r431._joint_obs(observation)
            terminal = bool(done) or bool(info["tds_failed"])
            rewards = step_rewards(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                reward_access=factors["reward_access"],
            )
            agent.store(joint, raw_action, rewards, next_joint, terminal)
            diagnostics = agent.update_all()
            if diagnostics is not None:
                critic_losses.append(diagnostics["critic_loss"])
                actor_grad_norms.append(diagnostics["actor_grad_norm"])
                if not all(np.isfinite(list(diagnostics.values()))):
                    invalid_reason = "nonfinite learner diagnostic"
                    break
            if info["tds_failed"]:
                tds_failures += 1
                break
        if invalid_reason is not None:
            break
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass
    valid = invalid_reason is None and executed == total_steps
    checkpoint_sha = _save_checkpoint(agent, run_dir / "final.pt") if valid else None
    trace_sha = _write_new_json(
        run_dir / "training_diagnostics.json",
        {
            "critic_loss": critic_losses,
            "actor_gradient_norm": actor_grad_norms,
        },
    )
    final_diagnostics = (
        _final_diagnostics(agent, seed, actor_grad_norms) if valid else None
    )
    return _write_new_json(
        run_dir / "manifest.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "factors": factors,
            "training_seed": seed,
            "interaction_steps": executed,
            "episodes_attempted": episode_index,
            "tds_failed_episodes": tds_failures,
            "convergence_diagnostics_valid": valid,
            "missing": not valid,
            "invalid_reason": invalid_reason,
            "checkpoint_sha256": checkpoint_sha,
            "training_diagnostics_sha256": trace_sha,
            "diagnostics": final_diagnostics,
            "contract_sha256": contract_sha256(contract),
            "created_utc": datetime.now(UTC).isoformat(),
        },
    )


def _activate_parent_eval() -> None:
    parent.ROUND_ID = ROUND_ID
    parent.OUT = OUT
    parent.CHANNEL_ARMS = ARMS
    parent.TRAINING_SEEDS = list(TRAINING_SEEDS)
    parent.agent_for = agent_for
    parent.build_contract = build_contract


def evaluate_arm(arm_id: str) -> None:
    _assert_wsl_scratch()
    load_seal()
    if arm_id not in ARMS:
        raise ValueError(f"unknown arm: {arm_id}")
    _activate_parent_eval()
    parent._evaluate_channel_arm(arm_id)


def _sync_agent(source: SACAgent, target: SACAgent) -> None:
    target.actor.load_state_dict(source.actor.state_dict())
    target.critic.load_state_dict(source.critic.state_dict())
    target.critic_target.load_state_dict(source.critic_target.state_dict())
    target.log_alpha.data = source.log_alpha.data.clone()


def _fill_probe_buffer(
    agent: SACAgent, *, reward: float, seed: int = 9, count: int | None = None
) -> None:
    rng = np.random.default_rng(seed)
    for _ in range(agent.batch_size if count is None else count):
        obs = rng.normal(size=base.OBS_DIM).astype(np.float32)
        action = np.tanh(rng.normal(size=base.ACTION_DIM)).astype(np.float32)
        next_obs = rng.normal(size=base.OBS_DIM).astype(np.float32)
        agent.store_transition(obs, action, reward, next_obs, True)


def rehearsal() -> dict[str, Any]:
    _assert_wsl_scratch()
    if OUT.exists() or SEAL.exists():
        raise FileExistsError("formal output or seal already exists")
    checks: dict[str, Any] = {
        "authority": authority_checks(),
        "runtime": installed_runtime(),
        "contract_sha256": contract_sha256(),
        "output_absence": True,
    }
    rows = np.arange(base.AGENT_COUNT * base.OBS_DIM, dtype=np.float32).reshape(
        base.AGENT_COUNT, base.OBS_DIM
    )
    shuffled = shuffle_neighbour_blocks(rows)
    checks["shuffle"] = {
        "pooled_marginal_preserved": bool(
            np.array_equal(
                np.sort(rows[:, NEIGHBOUR_SLICE], axis=0),
                np.sort(shuffled[:, NEIGHBOUR_SLICE], axis=0),
            )
        ),
        "pairing_changed": bool(
            not np.array_equal(rows[:, NEIGHBOUR_SLICE], shuffled[:, NEIGHBOUR_SLICE])
        ),
    }
    probe = SplitAccessSACAgent(actor_access=False, critic_access=True)
    tensor = torch.as_tensor(rows[0:1])
    checks["mask"] = {
        "actor_neighbours_zero": bool(
            torch.all(probe._masked_tensor(tensor, False)[..., NEIGHBOUR_SLICE] == 0)
        ),
        "critic_neighbours_full": bool(
            torch.equal(probe._masked_tensor(tensor, True), tensor)
        ),
    }

    standard = SACAgent(
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
    split = SplitAccessSACAgent(actor_access=True, critic_access=True)
    _sync_agent(standard, split)
    _fill_probe_buffer(standard, reward=-0.2)
    _fill_probe_buffer(split, reward=-0.2)
    np.random.seed(33)
    torch.manual_seed(33)
    standard.update()
    np.random.seed(33)
    torch.manual_seed(33)
    split.update()
    parameter_delta = max(
        float(torch.max(torch.abs(left.detach() - right.detach())))
        for left, right in zip(standard.actor.parameters(), split.actor.parameters())
    )
    parameter_delta = max(
        parameter_delta,
        max(
                float(torch.max(torch.abs(left.detach() - right.detach())))
            for left, right in zip(standard.critic.parameters(), split.critic.parameters())
        ),
    )
    checks["full_update_parity"] = {
        "max_parameter_abs_delta": parameter_delta,
        "passed": parameter_delta <= 1.0e-9,
    }

    direction_agent = SplitAccessSACAgent(actor_access=True, critic_access=True)
    _fill_probe_buffer(direction_agent, reward=0.0, seed=15)
    probe_obs = torch.as_tensor(
        direction_agent.buffer.obs[: direction_agent.batch_size], dtype=torch.float32
    )
    probe_actions = torch.as_tensor(
        direction_agent.buffer.actions[: direction_agent.batch_size], dtype=torch.float32
    )
    q_probe = direction_agent.critic(probe_obs, probe_actions)[0]
    neutral_target = torch.zeros_like(q_probe)
    negative_target = -torch.ones_like(q_probe)
    neutral_dloss_dq = torch.autograd.grad(
        F.mse_loss(q_probe, neutral_target), q_probe, retain_graph=True
    )[0]
    negative_dloss_dq = torch.autograd.grad(
        F.mse_loss(q_probe, negative_target), q_probe
    )[0]
    neutral_descent = float((-neutral_dloss_dq).mean().detach().cpu())
    negative_descent = float((-negative_dloss_dq).mean().detach().cpu())
    checks["penalty_direction_probe"] = {
        "neutral_mean_negative_dloss_dq": neutral_descent,
        "negative_reward_mean_negative_dloss_dq": negative_descent,
        "negative_reward_descent_more_negative": negative_descent < neutral_descent,
        "terminal_target_units": "reward units",
    }
    checks["objective_semantics_probe"] = r429.semantics_probe(
        agent_for("a1_c1_r1"), masked=False
    )
    checks["objective_semantics_probe"]["reward_access_direction_ok"] = checks[
        "penalty_direction_probe"
    ]["negative_reward_descent_more_negative"]

    contract = build_contract()
    profile = next(p for p in contract["profiles"] if p["split"] == "development")
    scenario = profile["scenarios"][0]
    env = r431._build_env(profile)
    wrapper = agent_for("a0_c1_r0")
    for index, member in enumerate(wrapper.agents):
        _fill_probe_buffer(
            member, reward=-0.1, seed=80 + index, count=member.batch_size - 1
        )
    rows_completed = 0
    real_update: dict[str, float] | None = None
    try:
        observation = env.reset(delta_u=dict(scenario["delta_u"]))
        projector = r431.PerVSGMDActionProjector(
            action_slew_limit=float(contract["action_slew_limit"])
        )
        for _ in range(3):
            joint = r431._joint_obs(observation)
            raw_action = wrapper.act(joint)
            action = projector.project(raw_action)
            observation, _reward, done, info = env.step(
                {i: np.asarray(action[i], dtype=np.float32) for i in range(4)}
            )
            next_joint = r431._joint_obs(observation)
            rewards = step_rewards(
                joint,
                np.asarray(info["delta_M"], dtype=float),
                np.asarray(info["delta_D"], dtype=float),
                reward_access=False,
            )
            wrapper.store(
                joint,
                raw_action,
                rewards,
                next_joint,
                bool(done) or bool(info["tds_failed"]),
            )
            real_update = wrapper.update_all()
            rows_completed += 1
            if done or info["tds_failed"]:
                break
    finally:
        env.close()
    checks["short_andes_path"] = {
        "rows": rows_completed,
        "store_update_exercised": real_update is not None,
        "update_finite": bool(
            real_update is not None and all(np.isfinite(list(real_update.values())))
        ),
        "passed": bool(
            rows_completed == 3
            and real_update is not None
            and all(np.isfinite(list(real_update.values())))
        ),
    }
    checks["passed"] = bool(
        all(checks["authority"].values())
        and all(checks["shuffle"].values())
        and all(checks["mask"].values())
        and checks["full_update_parity"]["passed"]
        and checks["penalty_direction_probe"]["negative_reward_descent_more_negative"]
        and all(checks["objective_semantics_probe"].values())
        and checks["short_andes_path"]["passed"]
    )
    return checks


def measure_capacity() -> dict[str, Any]:
    _assert_wsl_scratch()
    inherited = _read_hashed_json(R438_CAPACITY)
    meminfo = Path("/proc/meminfo").read_text(encoding="ascii")
    fields = {
        line.split(":", 1)[0]: int(line.split()[1]) * 1024
        for line in meminfo.splitlines()
        if ":" in line and len(line.split()) >= 2 and line.split()[1].isdigit()
    }
    ps = subprocess.run(
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    other = [
        line.strip()
        for line in ps
        if ("scripts/run_" in line or "soft_spot_shard_driver.py" in line)
        and "run_r451" not in line
    ]
    worker_rss = int(inherited["training_worker_rss_anchor"]["bytes"])
    os_floor = 3 * 1024**3
    mem_total = int(fields["MemTotal"])
    safe = [
        rung
        for rung in (1, 2, 4, 8, 12, 16)
        if rung * worker_rss + os_floor <= mem_total
    ]
    selected = max(safe)
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "formal_authority": False,
        "training_executed": False,
        "inherited_ladder": {
            "path": _relative(R438_CAPACITY),
            "sha256": _sha256_file(R438_CAPACITY),
            "basis": "same SAC learner, bundle, hardware, and one-thread worker",
        },
        "rungs": [1, 2, 4, 8, 12, 16],
        "memory_safe_rungs": safe,
        "worker_rss_anchor_bytes": worker_rss,
        "os_floor_bytes": os_floor,
        "wsl_mem_total_bytes": mem_total,
        "wsl_mem_available_bytes": int(fields["MemAvailable"]),
        "other_python_processes": other,
        "other_reserved_processes": 0,
        "selected_workers": selected,
        "wsl_python_processes": selected + 1,
        "host_process_budget": selected + 1,
        "native_threads_per_process": 1,
        "readiness": "RUN-READY" if selected > 0 and not other else "LOAD-CHECK-REVIEW",
    }


def prepare() -> dict[str, Any]:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority failed: {checks}")
    rehearsal_payload = _read_hashed_json(REHEARSAL)
    if not rehearsal_payload.get("passed"):
        raise RuntimeError("rehearsal did not pass")
    capacity = _read_hashed_json(CAPACITY)
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError(f"capacity is not ready: {capacity.get('readiness')}")
    selected = int(capacity["selected_workers"])
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r451_m3_message_factorial.py",
        "r438_runner": ROOT / "scripts/run_r438_sac_message_channels.py",
        "r431_runner": ROOT / "scripts/run_r431_sac_slew.py",
        "sac_learner": ROOT / "src/andes_rl_kundur/agents/sac.py",
        "replay_buffer": ROOT / "src/andes_rl_kundur/agents/replay_buffer.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "v4_environment": ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "launch": {
            "wsl_python_processes": selected + 1,
            "other_reserved_processes": 0,
            "host_process_budget": selected + 1,
            "native_threads_per_process": 1,
        },
        "runtime": rehearsal_payload["runtime"],
        "sources": {
            name: {"path": _relative(path), "sha256": _sha256_file(path)}
            for name, path in sources.items()
        },
        "formal_authority": True,
        "training_executed": False,
    }
    seal_sha = _write_new_json(SEAL, seal)
    TRAIN_SHARDS.parent.mkdir(parents=True, exist_ok=True)
    TRAIN_SHARDS.write_text(
        json.dumps([f"train|{arm}|{seed}" for arm in ARMS for seed in TRAINING_SEEDS])
        + "\n",
        encoding="utf-8",
    )
    EVAL_SHARDS.write_text(
        json.dumps([f"eval|{arm}|0" for arm in ARMS]) + "\n", encoding="utf-8"
    )
    return {
        "seal_sha256": seal_sha,
        "selected_workers": selected,
        "train_shards": 45,
        "eval_shards": 9,
    }


def _upper_median(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    return ordered[len(ordered) // 2]


def _bootstrap_improvement(candidate: list[float], reference: list[float]) -> dict[str, Any]:
    candidate_array = np.asarray(candidate, dtype=float)
    reference_array = np.asarray(reference, dtype=float)
    paired = (reference_array - candidate_array) / np.maximum(reference_array, 1e-12)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = np.empty(BOOTSTRAP_RESAMPLES, dtype=float)
    for index in range(BOOTSTRAP_RESAMPLES):
        draw = rng.integers(0, len(paired), size=len(paired))
        samples[index] = float(np.mean(paired[draw]))
    return {
        "paired_values": paired.tolist(),
        "mean": float(np.mean(paired)),
        "median": float(np.median(paired)),
        "ci90": [float(np.quantile(samples, 0.05)), float(np.quantile(samples, 0.95))],
        "positive_pairs": int(np.sum(paired > 0)),
    }


def aggregate() -> str:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    endpoints: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    integrity_errors: list[str] = []
    for arm in ARMS:
        seed_metrics = {
            "disturbance_differential_energy": [],
            "off_diagonal_response_energy": [],
        }
        seed_diagnostics: list[dict[str, float]] = []
        for seed in TRAINING_SEEDS:
            manifest = _read_hashed_json(OUT / "train" / arm / f"seed{seed}" / "manifest.json")
            if not manifest.get("convergence_diagnostics_valid") or int(
                manifest.get("interaction_steps", 0)
            ) != 43_200:
                integrity_errors.append(f"invalid training {arm} seed{seed}")
            diag = manifest["diagnostics"]
            seed_diagnostics.append(
                {
                    "validation_train_td_ratio": float(diag["validation_train_td_ratio_mean"]),
                    "actor_gradient_norm_variance": float(diag["actor_gradient_norm"]["variance"]),
                    "active_feature_condition_number": float(diag["active_feature_condition_max"]),
                }
            )
            per_profile = []
            for profile in contract["profiles"]:
                if profile["split"] != "evaluation":
                    continue
                path = OUT / "eval" / arm / f"seed{seed}" / f"{profile['profile_id']}.json"
                payload = _read_hashed_json(path)
                if any(
                    not row.get("completed") or row.get("tds_failed")
                    for row in payload["records"]
                ):
                    integrity_errors.append(f"invalid eval {arm} seed{seed} {profile['profile_id']}")
                per_profile.append(parent._arm_endpoints(payload["records"], contract))
            for metric in seed_metrics:
                seed_metrics[metric].append(_upper_median([row[metric] for row in per_profile]))
        endpoints[arm] = {
            "per_seed_profile_medians": seed_metrics,
            "five_seed_medians": {
                metric: _upper_median(values) for metric, values in seed_metrics.items()
            },
        }
        diagnostics[arm] = {
            "per_seed": seed_diagnostics,
            "five_seed_medians": {
                key: _upper_median([row[key] for row in seed_diagnostics])
                for key in seed_diagnostics[0]
            },
        }

    anchor_checks: dict[str, Any] = {}
    for arm, expected in SEALED_ANCHORS.items():
        rows = {}
        for metric in ("disturbance_differential_energy", "off_diagonal_response_energy"):
            actual = endpoints[arm]["five_seed_medians"][metric]
            relative = abs(actual - expected[metric]) / expected[metric]
            rows[metric] = {"actual": actual, "expected": expected[metric], "relative_error": relative, "passes": relative <= ANCHOR_TOLERANCE}
        anchor_checks[arm] = {"source": expected["source"], "metrics": rows, "passes": all(row["passes"] for row in rows.values())}
        if not anchor_checks[arm]["passes"]:
            integrity_errors.append(f"anchor drift {arm}")

    comparisons: dict[str, Any] = {}
    for label, candidate_arm, reference_arm in (
        ("true_vs_no_message", "a1_c1_r1", "a0_c0_r0"),
        ("true_vs_shuffled", "a1_c1_r1", SHUFFLED_ARM),
        ("shuffled_vs_no_message", SHUFFLED_ARM, "a0_c0_r0"),
    ):
        comparisons[label] = {
            metric: _bootstrap_improvement(
                endpoints[candidate_arm]["per_seed_profile_medians"][metric],
                endpoints[reference_arm]["per_seed_profile_medians"][metric],
            )
            for metric in ("disturbance_differential_energy", "off_diagonal_response_energy")
        }

    value_supported = all(
        comparisons[label][metric]["ci90"][0] > 0
        for label in ("true_vs_no_message", "true_vs_shuffled")
        for metric in ("disturbance_differential_energy", "off_diagonal_response_energy")
    )
    shuffled_jointly_better = all(
        comparisons["shuffled_vs_no_message"][metric]["ci90"][0] > 0
        for metric in ("disturbance_differential_energy", "off_diagonal_response_energy")
    )
    cost_metrics = (
        "validation_train_td_ratio",
        "actor_gradient_norm_variance",
        "active_feature_condition_number",
    )
    cost_rows = {
        metric: {
            "shuffled": diagnostics[SHUFFLED_ARM]["five_seed_medians"][metric],
            "no_message": diagnostics["a0_c0_r0"]["five_seed_medians"][metric],
            "shuffled_higher": diagnostics[SHUFFLED_ARM]["five_seed_medians"][metric]
            > diagnostics["a0_c0_r0"]["five_seed_medians"][metric],
        }
        for metric in cost_metrics
    }
    cost_count = sum(row["shuffled_higher"] for row in cost_rows.values())
    finite_cost_supported = (not shuffled_jointly_better) and cost_count >= 2

    factorial_effects: dict[str, Any] = {}
    for metric in ("disturbance_differential_energy", "off_diagonal_response_energy"):
        effects = {}
        for factor, position in (("actor", 0), ("critic", 1), ("reward", 2)):
            off = []
            on = []
            for arm in FACTORIAL_ARMS:
                bits = [int(part[1]) for part in arm.split("_")]
                target = on if bits[position] else off
                target.append(np.log(endpoints[arm]["five_seed_medians"][metric]))
            effects[factor] = float(np.mean(off) - np.mean(on))
        factorial_effects[metric] = effects

    if integrity_errors:
        verdict = "CANARY-INVALID"
    elif value_supported and finite_cost_supported:
        verdict = "VALUE-AND-FINITE-COST"
    elif value_supported:
        verdict = "VALUE-ONLY"
    elif finite_cost_supported:
        verdict = "FINITE-COST-ONLY"
    else:
        verdict = "M3-REFUTED"
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(contract),
        "seal_sha256": _sha256_file(SEAL),
        "integrity": {"errors": integrity_errors, "valid": not integrity_errors},
        "anchor_checks": anchor_checks,
        "factorial": {"endpoints": endpoints, "main_log_effects": factorial_effects},
        "placebo": comparisons,
        "diagnostics": diagnostics,
        "finite_cost_check": {"metrics": cost_rows, "higher_count": cost_count, "shuffled_jointly_better": shuffled_jointly_better},
        "classification": {
            "information_value": "SUPPORTED" if value_supported else "NOT-SUPPORTED",
            "finite_learning_cost": "SUPPORTED" if finite_cost_supported else "NOT-SUPPORTED",
            "verdict": verdict,
        },
    }
    return _write_new_json(OUT / "formal_analysis.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("capacity", "rehearse", "prepare", "shard", "eval-arm", "aggregate"))
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--arm")
    args = parser.parse_args()
    if args.command == "capacity":
        payload = measure_capacity()
        digest = _write_new_json(CAPACITY, payload)
        safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = rehearsal()
        digest = _write_new_json(REHEARSAL, payload)
        safe_emit(json.dumps({**payload, "sha256": digest}, indent=2, sort_keys=True))
    elif args.command == "prepare":
        safe_emit(json.dumps(prepare(), indent=2, sort_keys=True))
    elif args.command == "eval-arm":
        if args.arm is None:
            raise SystemExit("eval-arm requires --arm")
        evaluate_arm(args.arm)
    elif args.command == "aggregate":
        safe_emit(aggregate())
    else:
        if args.shard_id is None:
            raise SystemExit("shard requires phase|arm|seed")
        phase, arm, seed_text = args.shard_id.split("|")
        if phase == "train":
            safe_emit(train_arm_seed(arm, int(seed_text)))
        elif phase == "eval":
            evaluate_arm(arm)
        else:
            raise SystemExit(f"unsupported phase: {phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
