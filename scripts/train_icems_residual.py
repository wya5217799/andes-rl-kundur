#!/usr/bin/env python3
"""Train the single frozen R278 shared two-area TD3 pilot seed."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3  # noqa: E402
from andes_rl_kundur.control.area_inertia_residual import (  # noqa: E402
    r278_area_inertia_contract,
)
from andes_rl_kundur.env.andes.andes_vsg_storage_env import (  # noqa: E402
    AndesMultiVSGEnvV4Storage,
)
from andes_rl_kundur.env.andes.icems_residual_env import (  # noqa: E402
    ICEMSResidualEnv,
)

FORMAL_EPISODES = 300
FORMAL_SEED = 49
TRAINING_STEPS = 15
WARMUP_STEPS = 512
DEFAULT_BANK = (
    ROOT
    / "results"
    / "r274_prospective_active_power_authority"
    / "formal_bank.json"
)
SOURCE_PATHS = (
    ROOT / "scripts" / "train_icems_residual.py",
    ROOT
    / "src"
    / "andes_rl_kundur"
    / "agents"
    / "shared_area_td3.py",
    ROOT
    / "src"
    / "andes_rl_kundur"
    / "control"
    / "area_inertia_residual.py",
    ROOT
    / "src"
    / "andes_rl_kundur"
    / "env"
    / "andes"
    / "icems_residual_env.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results" / "r278_shared_area_td3_s49",
    )
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--seed", type=int, default=FORMAL_SEED)
    parser.add_argument("--episodes", type=int, default=FORMAL_EPISODES)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    temporary = Path(f"{path}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_development_bank(path: Path) -> tuple[list[dict[str, Any]], str]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    scenarios = list(payload.get("scenarios", []))
    if len(scenarios) != 24:
        raise ValueError("R278 development bank must contain exactly 24 scenarios")
    for row in scenarios:
        if set(row) < {"name", "delta_u"}:
            raise ValueError(f"malformed scenario row: {row}")
    return scenarios, sha256_file(path)


def controller_contract(
    args: argparse.Namespace,
    *,
    bank_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": "R278",
        "question": "Q-0038",
        "algorithm": {
            "name": "shared_area_td3",
            "seed": int(args.seed),
            "episodes": int(args.episodes),
            "steps_per_episode": TRAINING_STEPS,
            "total_steps": int(args.episodes) * TRAINING_STEPS,
            "hidden_sizes": [64, 64],
            "actor_lr": 3e-4,
            "critic_lr": 3e-4,
            "gamma": 0.99,
            "tau": 0.005,
            "batch_size": 256,
            "warmup_steps": WARMUP_STEPS,
            "buffer_size": 100_000,
            "policy_noise": 0.1,
            "noise_clip": 0.2,
            "policy_delay": 2,
            "explore_noise": 0.1,
        },
        "action_and_reward": r278_area_inertia_contract().telemetry(),
        "development_bank": {
            "path": str(args.bank.resolve()),
            "sha256": bank_sha256,
            "role": "viewed_development_only",
            "scenario_count": 24,
        },
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
            for path in SOURCE_PATHS
        },
        "repository_head": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
        ).strip(),
        "command": [sys.executable, *sys.argv],
        "smoke": bool(args.smoke),
    }


def flatten_obs(observation: dict[int, np.ndarray]) -> np.ndarray:
    return np.concatenate(
        [np.asarray(observation[index], dtype=np.float32) for index in range(4)]
    ).astype(np.float32)


def main() -> int:
    args = parse_args()
    if not args.smoke:
        if args.seed != FORMAL_SEED:
            raise ValueError("R278 pilot seed is frozen at 49")
        if args.episodes != FORMAL_EPISODES:
            raise ValueError("R278 pilot training is frozen at 300 episodes")
    elif args.episodes > 3:
        raise ValueError("--smoke permits at most three episodes")

    scenarios, bank_sha256 = load_development_bank(args.bank)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    contract_path = args.out_dir / "controller_contract.json"
    if contract_path.exists():
        raise FileExistsError(
            f"refusing to overwrite controller contract: {contract_path}"
        )
    contract = controller_contract(args, bank_sha256=bank_sha256)
    atomic_json(contract_path, contract)

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    scenario_rng = np.random.default_rng(args.seed)
    exploration_rng = np.random.default_rng(args.seed + 10_000)
    agent = SharedAreaTD3(
        obs_dim=7,
        agent_count=4,
        hidden_sizes=[64, 64],
        lr=3e-4,
        gamma=0.99,
        tau=0.005,
        buffer_size=100_000,
        batch_size=256,
        device=args.device,
        policy_noise=0.1,
        noise_clip=0.2,
        explore_noise=0.1,
        policy_delay=2,
    )

    monitor: list[dict[str, Any]] = []
    total_steps = 0
    failed = False
    for episode in range(args.episodes):
        scenario = scenarios[int(scenario_rng.integers(0, len(scenarios)))]
        env = ICEMSResidualEnv(
            AndesMultiVSGEnvV4Storage(
                random_disturbance=False,
                comm_fail_prob=0.0,
            )
        )
        env.seed(args.seed + episode)
        env.STEPS_PER_EPISODE = TRAINING_STEPS
        episode_reward = 0.0
        q_values: list[float] = []
        critic_losses: list[float] = []
        actor_losses: list[float] = []
        completed_steps = 0
        tds_failed = False
        try:
            observation = env.reset(delta_u=scenario["delta_u"])
            for step in range(TRAINING_STEPS):
                joint_observation = flatten_obs(observation)
                if total_steps < WARMUP_STEPS:
                    raw = exploration_rng.uniform(
                        -1.0,
                        1.0,
                        size=4,
                    ).astype(np.float32)
                else:
                    raw = agent.select_raw_actions(
                        observation,
                        deterministic=False,
                        rng=exploration_rng,
                    )
                next_observation, _rewards, done, info = env.step(raw)
                tds_failed = bool(info.get("tds_failed", False))
                terminal = bool(done or tds_failed or step == TRAINING_STEPS - 1)
                team_reward = float(info["r278_team_reward"])
                agent.store(
                    joint_observation,
                    q_normalized=float(info["r278_q_normalized"]),
                    reward=team_reward,
                    next_observation=flatten_obs(next_observation),
                    done=terminal,
                )
                total_steps += 1
                completed_steps += 1
                episode_reward += team_reward
                q_values.append(float(info["r278_q"]))
                if total_steps >= WARMUP_STEPS:
                    losses = agent.update()
                    if losses:
                        critic_losses.append(losses["critic_loss"])
                        if "actor_loss" in losses:
                            actor_losses.append(losses["actor_loss"])
                observation = next_observation
                if terminal:
                    break
        finally:
            env.close()

        row = {
            "episode": episode,
            "scenario": scenario["name"],
            "delta_u": scenario["delta_u"],
            "steps": completed_steps,
            "completed": completed_steps == TRAINING_STEPS and not tds_failed,
            "tds_failed": tds_failed,
            "episode_reward": episode_reward,
            "mean_abs_q": float(np.mean(np.abs(q_values))) if q_values else 0.0,
            "max_abs_q": float(np.max(np.abs(q_values))) if q_values else 0.0,
            "mean_critic_loss": (
                float(np.mean(critic_losses)) if critic_losses else None
            ),
            "mean_actor_loss": (
                float(np.mean(actor_losses)) if actor_losses else None
            ),
            "total_steps": total_steps,
            "actor_update_steps": agent.actor_update_steps,
        }
        monitor.append(row)
        atomic_json(args.out_dir / "training_monitor.json", monitor)
        print(
            f"[R278 {episode + 1:03d}/{args.episodes:03d}] "
            f"{scenario['name']} reward={episode_reward:.6f} "
            f"|q|max={row['max_abs_q']:.6f} completed={row['completed']}",
            flush=True,
        )
        if not row["completed"]:
            failed = True
            break

    metadata = {
        "round": "R278",
        "question": "Q-0038",
        "seed": args.seed,
        "episodes_completed": len(monitor),
        "total_steps": total_steps,
        "controller_contract_sha256": sha256_file(contract_path),
        "development_bank_sha256": bank_sha256,
    }
    checkpoint_path = args.out_dir / "final.pt"
    agent.save(checkpoint_path, metadata=metadata)
    agent.buffer.save(str(args.out_dir / "replay_buffer.npz"))
    summary = {
        **metadata,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "failed": failed,
        "all_completed": (
            len(monitor) == args.episodes
            and all(row["completed"] for row in monitor)
        ),
        "final_20_mean_reward": float(
            np.mean([row["episode_reward"] for row in monitor[-20:]])
        ),
        "final_20_mean_abs_q": float(
            np.mean([row["mean_abs_q"] for row in monitor[-20:]])
        ),
    }
    atomic_json(args.out_dir / "training_summary.json", summary)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
