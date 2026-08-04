#!/usr/bin/env python3
"""Seal, train, and verify the six matched R292 vector TD3 checkpoints."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.vector_residual_td3 import (  # noqa: E402
    CentralVectorTD3,
    DistributedEdgeTD3,
)
from andes_rl_kundur.control.vector_inertia_residual import (  # noqa: E402
    r292_vector_residual_contract,
)
from andes_rl_kundur.env.andes.distributed_residual_env import (  # noqa: E402
    DistributedVectorResidualEnv,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R292"
QUESTION_ID = "Q-0049"
SEEDS = (101, 137, 173)
ARCHITECTURES = ("central_vector", "distributed_edge")
EPISODES = 300
TRAINING_STEPS = 15
WARMUP_STEPS = 512
BANK_PATH = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R292/training_seal.json"
DEFAULT_OUT = ROOT / "results/r292_vector_training"


def _write_new(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _load_json(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    actual = sha256_file(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError(f"hash mismatch for {path}: expected {expected_sha256}, got {actual}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R292/plan.md",
        "training_script": Path(__file__).resolve(),
        "launcher": ROOT / "scripts/run_r292_unattended.sh",
        "vector_policy": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "development_bank": BANK_PATH,
    }


def _run_dir(out_root: Path, architecture: str, seed: int) -> Path:
    return out_root / f"{architecture}_s{seed}"


def _make_agent(
    architecture: str,
    device: str,
) -> DistributedEdgeTD3:
    kwargs = {
        "obs_dim": 5,
        "lr": 3e-4,
        "gamma": 0.99,
        "tau": 0.005,
        "buffer_size": 100_000,
        "batch_size": 256,
        "device": device,
        "policy_noise": 0.1,
        "noise_clip": 0.2,
        "explore_noise": 0.1,
        "policy_delay": 2,
    }
    if architecture == "distributed_edge":
        return DistributedEdgeTD3(hidden_sizes=[64, 64], **kwargs)
    if architecture == "central_vector":
        return CentralVectorTD3(
            critic_hidden_sizes=[64, 64],
            actor_hidden_sizes=[59, 59],
            **kwargs,
        )
    raise ValueError(f"unknown architecture: {architecture}")


def _actor_parameter_counts() -> dict[str, int]:
    return {
        architecture: sum(
            parameter.numel()
            for parameter in _make_agent(architecture, "cpu").actor.parameters()
        )
        for architecture in ARCHITECTURES
    }


def prepare_seal(manifest_path: Path, out_root: Path) -> None:
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            if (_run_dir(out_root, architecture, seed) / "controller_contract.json").exists():
                raise ValueError("training seal must precede all six contracts")
    bank = _load_json(BANK_PATH)
    if len(bank.get("scenarios", [])) != 24:
        raise ValueError("development bank must contain exactly 24 scenarios")
    counts = _actor_parameter_counts()
    if counts != {"central_vector": 4959, "distributed_edge": 4929}:
        raise ValueError(f"actor capacity drift: {counts}")
    sources = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    packages: dict[str, str] = {"python": sys.version}
    for package in ("andes", "numpy", "torch"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "not-installed-on-sealing-host"
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "matched-vector-td3-training",
        "repository_head": _git_head(),
        "architectures": list(ARCHITECTURES),
        "seeds": list(SEEDS),
        "actor_parameter_counts": counts,
        "actor_parameter_relative_difference": abs(
            counts["central_vector"] - counts["distributed_edge"]
        )
        / counts["distributed_edge"],
        "training": {
            "episodes": EPISODES,
            "steps_per_episode": TRAINING_STEPS,
            "steps_per_checkpoint": EPISODES * TRAINING_STEPS,
            "checkpoint_count": 6,
            "total_real_andes_steps": 6 * EPISODES * TRAINING_STEPS,
            "warmup_steps": WARMUP_STEPS,
            "final_checkpoint_only": True,
            "best_checkpoint": False,
            "early_stopping": False,
            "retry_after_failure": False,
        },
        "hyperparameters": {
            "actor_lr": 3e-4,
            "critic_lr": 3e-4,
            "gamma": 0.99,
            "tau": 0.005,
            "batch_size": 256,
            "buffer_size": 100_000,
            "policy_noise": 0.1,
            "noise_clip": 0.2,
            "policy_delay": 2,
            "explore_noise": 0.1,
            "critic_hidden_sizes": [64, 64],
            "distributed_actor_hidden_sizes": [64, 64],
            "central_actor_hidden_sizes": [59, 59],
        },
        "development_bank": {
            "path": str(BANK_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(BANK_PATH),
            "scenario_count": 24,
            "role": "training_only_viewed_development",
        },
        "action_and_reward": r292_vector_residual_contract().telemetry(),
        "packages": packages,
        "sources": sources,
        "training_contract_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, manifest)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    manifest = _load_json(path, expected_sha256)
    if manifest.get("round") != ROUND_ID:
        raise ValueError("manifest is not the R292 training seal")
    if manifest.get("phase") != "matched-vector-td3-training":
        raise ValueError("unexpected R292 training phase")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed training source drift: {entry['path']}")
    return manifest


def _flatten_obs(observation: dict[int, np.ndarray]) -> np.ndarray:
    return np.concatenate(
        [np.asarray(observation[index], dtype=np.float32) for index in range(4)]
    ).astype(np.float32)


def _controller_contract(
    manifest: dict[str, Any],
    *,
    manifest_sha256: str,
    architecture: str,
    seed: int,
    device: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "architecture": architecture,
        "execution_information": (
            "joint_20d" if architecture == "central_vector" else "endpoint_10d_per_edge"
        ),
        "central_action_aggregation": False,
        "seed": seed,
        "device": device,
        "training_seal_sha256": manifest_sha256,
        "actor_parameter_count": manifest["actor_parameter_counts"][architecture],
        "training": manifest["training"],
        "hyperparameters": manifest["hyperparameters"],
        "development_bank": manifest["development_bank"],
        "action_and_reward": manifest["action_and_reward"],
        "repository_head": _git_head(),
        "source_sha256": {
            name: entry["sha256"] for name, entry in manifest["sources"].items()
        },
        "command": [sys.executable, *sys.argv],
    }


def train(
    manifest_path: Path,
    expected_sha256: str,
    out_root: Path,
    architecture: str,
    seed: int,
    device: str,
    smoke_episodes: int | None,
) -> int:
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    manifest = _verify_manifest(manifest_path, expected_sha256)
    if architecture not in ARCHITECTURES or seed not in SEEDS:
        raise ValueError("architecture or seed is outside the frozen matrix")
    episodes = EPISODES if smoke_episodes is None else smoke_episodes
    if smoke_episodes is not None and not 1 <= smoke_episodes <= 3:
        raise ValueError("smoke episodes must be in [1,3]")
    run_dir = (
        _run_dir(out_root, architecture, seed)
        if smoke_episodes is None
        else out_root / "smoke" / f"{architecture}_s{seed}_e{episodes}"
    )
    contract_path = run_dir / "controller_contract.json"
    if contract_path.exists():
        raise FileExistsError(f"refusing to overwrite training run: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    contract = _controller_contract(
        manifest,
        manifest_sha256=expected_sha256,
        architecture=architecture,
        seed=seed,
        device=device,
    )
    contract["smoke_episodes"] = smoke_episodes
    contract_digest = _write_new(contract_path, contract)
    scenarios = list(
        _load_json(BANK_PATH, manifest["development_bank"]["sha256"])["scenarios"]
    )

    np.random.seed(seed)
    torch.manual_seed(seed)
    scenario_rng = np.random.default_rng(seed)
    exploration_rng = np.random.default_rng(seed + 10_000)
    agent = _make_agent(architecture, device)
    monitor: list[dict[str, Any]] = []
    total_steps = 0
    failed = False
    for episode in range(episodes):
        scenario = scenarios[int(scenario_rng.integers(0, len(scenarios)))]
        env = DistributedVectorResidualEnv(
            AndesMultiVSGEnvV4Storage(
                random_disturbance=False,
                comm_fail_prob=0.0,
            )
        )
        env.seed(seed + episode)
        env.STEPS_PER_EPISODE = TRAINING_STEPS
        episode_reward = 0.0
        edge_values: list[float] = []
        critic_losses: list[float] = []
        actor_losses: list[float] = []
        completed_steps = 0
        tds_failed = False
        try:
            observation = env.reset(delta_u=scenario["delta_u"])
            for step in range(TRAINING_STEPS):
                joint_observation = _flatten_obs(observation)
                if total_steps < WARMUP_STEPS:
                    raw = exploration_rng.uniform(-1.0, 1.0, size=3).astype(
                        np.float32
                    )
                else:
                    raw = agent.select_edge_actions(
                        observation,
                        deterministic=False,
                        rng=exploration_rng,
                    )
                next_observation, _rewards, done, info = env.step(raw)
                tds_failed = bool(info.get("tds_failed", False))
                terminal = bool(done or tds_failed or step == TRAINING_STEPS - 1)
                executed_edge = np.asarray(
                    info["r292_edge_flow_norm"], dtype=np.float32
                ) / np.float32(agent.contract.edge_flow_max)
                agent.store(
                    joint_observation,
                    executed_edge,
                    reward=float(info["r292_team_reward"]),
                    next_observation=_flatten_obs(next_observation),
                    done=terminal,
                )
                total_steps += 1
                completed_steps += 1
                episode_reward += float(info["r292_team_reward"])
                edge_values.extend(np.asarray(info["r292_edge_flow_norm"]).tolist())
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
            "mean_abs_edge": float(np.mean(np.abs(edge_values))) if edge_values else 0.0,
            "max_abs_edge": float(np.max(np.abs(edge_values))) if edge_values else 0.0,
            "mean_critic_loss": float(np.mean(critic_losses)) if critic_losses else None,
            "mean_actor_loss": float(np.mean(actor_losses)) if actor_losses else None,
            "total_steps": total_steps,
            "actor_update_steps": agent.actor_update_steps,
        }
        monitor.append(row)
        _atomic_json(run_dir / "training_monitor.json", monitor)
        print(
            f"[R292 {architecture} s{seed} {episode + 1:03d}/{episodes:03d}] "
            f"{scenario['name']} reward={episode_reward:.6f} "
            f"|edge|max={row['max_abs_edge']:.6f} completed={row['completed']}",
            flush=True,
        )
        if not row["completed"]:
            failed = True
            break

    metadata = {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "architecture": architecture,
        "seed": seed,
        "episodes_completed": len(monitor),
        "total_steps": total_steps,
        "controller_contract_sha256": contract_digest,
        "development_bank_sha256": manifest["development_bank"]["sha256"],
        "training_seal_sha256": expected_sha256,
        "smoke": smoke_episodes is not None,
    }
    checkpoint_path = run_dir / "final.pt"
    agent.save(checkpoint_path, metadata=metadata)
    replay_path = run_dir / "replay_buffer.npz"
    agent.buffer.save(str(replay_path))
    monitor_path = run_dir / "training_monitor.json"
    summary = {
        **metadata,
        "checkpoint": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "replay_buffer_sha256": sha256_file(replay_path),
        "training_monitor_sha256": sha256_file(monitor_path),
        "failed": failed,
        "all_completed": len(monitor) == episodes
        and all(row["completed"] for row in monitor),
        "final_20_mean_reward": float(
            np.mean([row["episode_reward"] for row in monitor[-20:]])
        ),
        "final_20_mean_abs_edge": float(
            np.mean([row["mean_abs_edge"] for row in monitor[-20:]])
        ),
    }
    _write_new(run_dir / "training_summary.json", summary)
    return 1 if failed else 0


def verify_matrix(
    manifest_path: Path,
    expected_sha256: str,
    out_root: Path,
) -> None:
    _verify_manifest(manifest_path, expected_sha256)
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            run_dir = _run_dir(out_root, architecture, seed)
            paths = {
                "contract": run_dir / "controller_contract.json",
                "summary": run_dir / "training_summary.json",
                "checkpoint": run_dir / "final.pt",
                "replay": run_dir / "replay_buffer.npz",
                "monitor": run_dir / "training_monitor.json",
            }
            contract = _load_json(paths["contract"])
            summary = _load_json(paths["summary"])
            expected = {
                "round": ROUND_ID,
                "architecture": architecture,
                "seed": seed,
                "episodes_completed": EPISODES,
                "total_steps": EPISODES * TRAINING_STEPS,
                "training_seal_sha256": expected_sha256,
                "smoke": False,
                "failed": False,
                "all_completed": True,
            }
            for key, value in expected.items():
                if summary.get(key) != value:
                    raise ValueError(f"training matrix mismatch in {paths['summary']}: {key}")
            checks = {
                "checkpoint": summary["checkpoint_sha256"]
                == sha256_file(paths["checkpoint"]),
                "replay": summary["replay_buffer_sha256"]
                == sha256_file(paths["replay"]),
                "monitor": summary["training_monitor_sha256"]
                == sha256_file(paths["monitor"]),
                "contract": summary["controller_contract_sha256"]
                == sha256_file(paths["contract"]),
            }
            if not all(checks.values()):
                raise ValueError(f"training artifact hash mismatch: {run_dir}")
            rows.append(
                {
                    "architecture": architecture,
                    "seed": seed,
                    "actor_parameter_count": contract["actor_parameter_count"],
                    "episodes_completed": summary["episodes_completed"],
                    "total_steps": summary["total_steps"],
                    "final_20_mean_reward": summary["final_20_mean_reward"],
                    "final_20_mean_abs_edge": summary["final_20_mean_abs_edge"],
                    "checkpoint_sha256": summary["checkpoint_sha256"],
                    "checks": checks,
                }
            )
            for path in paths.values():
                artifacts[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256_file(path)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "matched-vector-td3-training-complete",
        "training_seal_sha256": expected_sha256,
        "expected_run_count": 6,
        "observed_run_count": len(rows),
        "all_completed": len(rows) == 6,
        "seed_selection_performed": False,
        "rows": rows,
        "artifact_hashes": dict(sorted(artifacts.items())),
    }
    summary_digest = _write_new(out_root / "training_matrix_summary.json", payload)
    provenance_digest = _write_new(
        out_root / "provenance.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "repository_head": _git_head(),
            "training_seal_sha256": expected_sha256,
            "training_matrix_summary_sha256": summary_digest,
            "paper_files_modified": False,
        },
    )
    print(
        f"[verified] runs={len(rows)} summary_sha256={summary_digest} "
        f"provenance_sha256={provenance_digest}",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    prepare_parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    train_parser = subparsers.add_parser("run")
    train_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    train_parser.add_argument("--expected-manifest-sha256", required=True)
    train_parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    train_parser.add_argument("--architecture", choices=ARCHITECTURES, required=True)
    train_parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    train_parser.add_argument("--device", default="cpu")
    train_parser.add_argument("--smoke-episodes", type=int)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path, default=DEFAULT_SEAL)
    verify_parser.add_argument("--expected-manifest-sha256", required=True)
    verify_parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare_seal(args.manifest, args.out_root)
        return 0
    if args.command == "verify":
        verify_matrix(args.manifest, args.expected_manifest_sha256, args.out_root)
        return 0
    return train(
        args.manifest,
        args.expected_manifest_sha256,
        args.out_root,
        args.architecture,
        args.seed,
        args.device,
        args.smoke_episodes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
