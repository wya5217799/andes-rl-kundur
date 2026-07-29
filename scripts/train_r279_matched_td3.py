#!/usr/bin/env python3
"""Seal and train the six prospectively matched R279 TD3 checkpoints."""

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

from andes_rl_kundur.agents.central_scalar_td3 import CentralScalarTD3  # noqa: E402
from andes_rl_kundur.agents.shared_area_td3 import SharedAreaTD3  # noqa: E402
from andes_rl_kundur.control.area_inertia_residual import (  # noqa: E402
    r278_area_inertia_contract,
)
from andes_rl_kundur.env.andes.andes_vsg_storage_env import (  # noqa: E402
    AndesMultiVSGEnvV4Storage,
)
from andes_rl_kundur.env.andes.icems_residual_env import ICEMSResidualEnv  # noqa: E402
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R279"
SEEDS = (17, 53, 89)
ARCHITECTURES = ("shared", "centralized")
EPISODES = 300
TRAINING_STEPS = 15
WARMUP_STEPS = 512
BANK_PATH = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R279/training_seal.json"
DEFAULT_OUT = ROOT / "results/r279_matched_training"
CAUSAL_GUARD_SUMMARY = ROOT / "results/r279_causal_guard/causal_guard_summary.json"


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
        "plan": ROOT / "memory/rounds/R279/plan.md",
        "script": Path(__file__).resolve(),
        "launcher": ROOT / "scripts/run_r279_matched_training.sh",
        "shared_policy": ROOT / "src/andes_rl_kundur/agents/shared_area_td3.py",
        "central_policy": ROOT / "src/andes_rl_kundur/agents/central_scalar_td3.py",
        "residual_environment": ROOT
        / "src/andes_rl_kundur/env/andes/icems_residual_env.py",
        "residual_contract": ROOT
        / "src/andes_rl_kundur/control/area_inertia_residual.py",
        "development_bank": BANK_PATH,
        "causal_guard_summary": CAUSAL_GUARD_SUMMARY,
    }


def _run_dir(out_root: Path, architecture: str, seed: int) -> Path:
    return out_root / f"{architecture}_s{seed}"


def _actor_parameter_counts() -> dict[str, int]:
    shared = SharedAreaTD3()
    central = CentralScalarTD3()
    return {
        "shared": sum(parameter.numel() for parameter in shared.actor.parameters()),
        "centralized": central.actor_parameter_count,
    }


def prepare_seal(manifest_path: Path, out_root: Path) -> None:
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            run_dir = _run_dir(out_root, architecture, seed)
            if (run_dir / "controller_contract.json").exists():
                raise ValueError("training seal must precede all six contracts")
    bank = _load_json(BANK_PATH)
    causal_guard = _load_json(CAUSAL_GUARD_SUMMARY)
    if causal_guard.get("round") != ROUND_ID:
        raise ValueError("matched training requires the completed R279 causal guard")
    if not causal_guard.get("decision", {}).get("pass", False):
        raise ValueError("matched training requires a passing causal guard")
    if len(bank.get("scenarios", [])) != 24:
        raise ValueError("training bank must contain 24 scenarios")
    counts = _actor_parameter_counts()
    if counts != {"shared": 4737, "centralized": 4731}:
        raise ValueError(f"actor capacity drift: {counts}")
    sources = {
        name: {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in _source_paths().items()
    }
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "matched-td3-training",
        "repository_head": _git_head(),
        "architectures": list(ARCHITECTURES),
        "seeds": list(SEEDS),
        "actor_parameter_counts": counts,
        "actor_parameter_difference": abs(counts["shared"] - counts["centralized"]),
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
            "shared_actor_hidden_sizes": [64, 64],
            "central_actor_hidden_sizes": [55, 55],
        },
        "development_bank": {
            "path": str(BANK_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(BANK_PATH),
            "scenario_count": 24,
            "role": "training_only_viewed_development",
        },
        "causal_guard": {
            "path": str(CAUSAL_GUARD_SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(CAUSAL_GUARD_SUMMARY),
            "classification": causal_guard["decision"]["classification"],
            "pass": causal_guard["decision"]["pass"],
        },
        "action_and_reward": r278_area_inertia_contract().telemetry(),
        "packages": {
            package: importlib.metadata.version(package)
            for package in ("andes", "numpy", "torch")
        }
        | {"python": sys.version},
        "sources": sources,
        "training_contract_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, manifest)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    manifest = _load_json(path, expected_sha256)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "matched-td3-training":
        raise ValueError("manifest is not the R279 matched-training seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed training source drift: {entry['path']}")
    if sha256_file(BANK_PATH) != manifest["development_bank"]["sha256"]:
        raise ValueError("training bank drift")
    return manifest


def _flatten_obs(observation: dict[int, np.ndarray]) -> np.ndarray:
    return np.concatenate(
        [np.asarray(observation[index], dtype=np.float32) for index in range(4)]
    ).astype(np.float32)


def _make_agent(architecture: str, device: str) -> SharedAreaTD3:
    kwargs = {
        "obs_dim": 7,
        "agent_count": 4,
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
    if architecture == "shared":
        return SharedAreaTD3(hidden_sizes=[64, 64], **kwargs)
    if architecture == "centralized":
        return CentralScalarTD3(
            critic_hidden_sizes=[64, 64],
            actor_hidden_sizes=[55, 55],
            **kwargs,
        )
    raise ValueError(f"unknown architecture: {architecture}")


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
        "question": "Q-0041",
        "architecture": architecture,
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
    manifest = _verify_manifest(manifest_path, expected_sha256)
    if architecture not in ARCHITECTURES or seed not in SEEDS:
        raise ValueError("architecture or seed is outside the frozen six-run matrix")
    episodes = EPISODES if smoke_episodes is None else smoke_episodes
    if smoke_episodes is not None and not 1 <= smoke_episodes <= 3:
        raise ValueError("smoke episodes must be in [1,3]")
    if smoke_episodes is None and episodes != manifest["training"]["episodes"]:
        raise ValueError("formal episode budget drift")
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
    bank = _load_json(BANK_PATH, manifest["development_bank"]["sha256"])
    scenarios = list(bank["scenarios"])

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
        env = ICEMSResidualEnv(
            AndesMultiVSGEnvV4Storage(
                random_disturbance=False,
                comm_fail_prob=0.0,
            )
        )
        env.seed(seed + episode)
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
                joint_observation = _flatten_obs(observation)
                if total_steps < WARMUP_STEPS:
                    raw = exploration_rng.uniform(-1.0, 1.0, size=4).astype(
                        np.float32
                    )
                else:
                    raw = agent.select_raw_actions(
                        observation,
                        deterministic=False,
                        rng=exploration_rng,
                    )
                next_observation, _rewards, done, info = env.step(raw)
                tds_failed = bool(info.get("tds_failed", False))
                terminal = bool(
                    done or tds_failed or step == TRAINING_STEPS - 1
                )
                agent.store(
                    joint_observation,
                    q_normalized=float(info["r278_q_normalized"]),
                    reward=float(info["r278_team_reward"]),
                    next_observation=_flatten_obs(next_observation),
                    done=terminal,
                )
                total_steps += 1
                completed_steps += 1
                episode_reward += float(info["r278_team_reward"])
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
            "mean_critic_loss": float(np.mean(critic_losses))
            if critic_losses
            else None,
            "mean_actor_loss": float(np.mean(actor_losses))
            if actor_losses
            else None,
            "total_steps": total_steps,
            "actor_update_steps": agent.actor_update_steps,
        }
        monitor.append(row)
        _atomic_json(run_dir / "training_monitor.json", monitor)
        print(
            f"[R279 {architecture} s{seed} {episode + 1:03d}/{episodes:03d}] "
            f"{scenario['name']} reward={episode_reward:.6f} "
            f"|q|max={row['max_abs_q']:.6f} completed={row['completed']}",
            flush=True,
        )
        if not row["completed"]:
            failed = True
            break

    metadata = {
        "round": ROUND_ID,
        "question": "Q-0041",
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
        "final_20_mean_abs_q": float(
            np.mean([row["mean_abs_q"] for row in monitor[-20:]])
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
    rows = []
    artifacts: dict[str, str] = {}
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            run_dir = _run_dir(out_root, architecture, seed)
            contract_path = run_dir / "controller_contract.json"
            summary_path = run_dir / "training_summary.json"
            checkpoint_path = run_dir / "final.pt"
            replay_path = run_dir / "replay_buffer.npz"
            monitor_path = run_dir / "training_monitor.json"
            contract = _load_json(contract_path)
            summary = _load_json(summary_path)
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
                    raise ValueError(
                        f"training matrix mismatch in {summary_path}: {key}"
                    )
            if contract.get("training_seal_sha256") != expected_sha256:
                raise ValueError(f"training contract seal mismatch: {contract_path}")
            checks = {
                "checkpoint": summary["checkpoint_sha256"]
                == sha256_file(checkpoint_path),
                "replay": summary["replay_buffer_sha256"]
                == sha256_file(replay_path),
                "monitor": summary["training_monitor_sha256"]
                == sha256_file(monitor_path),
                "contract": summary["controller_contract_sha256"]
                == sha256_file(contract_path),
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
                    "final_20_mean_abs_q": summary["final_20_mean_abs_q"],
                    "checkpoint_sha256": summary["checkpoint_sha256"],
                    "checks": checks,
                }
            )
            for artifact in (
                contract_path,
                summary_path,
                checkpoint_path,
                replay_path,
                monitor_path,
            ):
                artifacts[
                    str(artifact.relative_to(ROOT)).replace("\\", "/")
                ] = sha256_file(artifact)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": "Q-0041",
        "phase": "matched-td3-training-complete",
        "training_seal_sha256": expected_sha256,
        "expected_run_count": 6,
        "observed_run_count": len(rows),
        "all_completed": len(rows) == 6,
        "seed_selection_performed": False,
        "rows": rows,
        "artifact_hashes": dict(sorted(artifacts.items())),
    }
    summary_digest = _write_new(out_root / "training_matrix_summary.json", payload)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "repository_head": _git_head(),
        "training_seal_sha256": expected_sha256,
        "training_matrix_summary_sha256": summary_digest,
        "paper_files_modified": False,
    }
    provenance_digest = _write_new(out_root / "provenance.json", provenance)
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
