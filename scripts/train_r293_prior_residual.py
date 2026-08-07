#!/usr/bin/env python3
"""Seal, train, and verify ten matched R293 prior-residual TD3 checkpoints."""

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

from andes_rl_kundur.agents.classical_prior_td3 import (  # noqa: E402
    CentralPriorResidualTD3,
    DistributedPriorResidualTD3,
)
from andes_rl_kundur.control.classical_edge_residual import (  # noqa: E402
    ClassicalEdgeContract,
)
from andes_rl_kundur.control.vector_inertia_residual import (  # noqa: E402
    r292_vector_residual_contract,
)
from andes_rl_kundur.env.andes.prior_residual_env import (  # noqa: E402
    PriorResidualEnv,
    R293_ROCOF_REWARD_WEIGHT,
    R293_ROCOF_SCALE_HZ_S,
)
from andes_rl_kundur.evaluation.sealed_bank import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

ROUND_ID = "R293"
QUESTION_ID = "Q-0050"
SEEDS = (211, 257, 293, 331, 379)
ARCHITECTURES = ("central_prior", "distributed_prior")
EPISODES = 300
TRAINING_STEPS = 15
WARMUP_STEPS = 512
BANK_PATH = ROOT / "results/r274_prospective_active_power_authority/formal_bank.json"
GUARD_SUMMARY = ROOT / "results/r293_classical_guard/classical_guard_summary.json"
GUARD_PROVENANCE = ROOT / "results/r293_classical_guard/provenance.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R293/training_seal.json"
DEFAULT_OUT = ROOT / "results/r293_prior_residual_training"


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


def _write_sidecar(path: Path) -> str:
    digest = sha256_file(path)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _load_json(path: Path, expected: str | None = None) -> dict[str, Any]:
    if expected is not None and sha256_file(path) != expected:
        raise ValueError(f"hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _contract_from_telemetry(telemetry: dict[str, Any]) -> ClassicalEdgeContract:
    """Restore both legacy beta-zero and limited-reversal contracts."""

    return ClassicalEdgeContract(
        family=str(telemetry["family"]),
        gain=float(telemetry["gain"]),
        residual_scale=float(telemetry["residual_scale"]),
        reverse_limit=float(telemetry.get("reverse_limit", 0.0)),
    )


def _selected_contract() -> ClassicalEdgeContract:
    guard = _load_json(GUARD_SUMMARY)
    if guard.get("classification") != "CLASSICAL-GUARD-PASS":
        raise ValueError("R293 classical full-horizon guard did not pass")
    return _contract_from_telemetry(guard["selected_classical_contract"])


def _training_budget() -> dict[str, Any]:
    checkpoint_count = len(ARCHITECTURES) * len(SEEDS)
    return {
        "episodes": EPISODES,
        "steps_per_episode": TRAINING_STEPS,
        "steps_per_checkpoint": EPISODES * TRAINING_STEPS,
        "checkpoint_count": checkpoint_count,
        "total_real_andes_steps": checkpoint_count * EPISODES * TRAINING_STEPS,
        "warmup_steps": WARMUP_STEPS,
        "final_checkpoint_only": True,
        "best_checkpoint": False,
        "early_stopping": False,
        "retry_after_failure": False,
    }


def _expected_actor_counts() -> dict[str, int]:
    expected = {"central_prior": 4959, "distributed_prior": 4929}
    unknown = set(ARCHITECTURES) - set(expected)
    if unknown:
        raise ValueError(f"unknown architecture capacity: {sorted(unknown)}")
    return {architecture: expected[architecture] for architecture in ARCHITECTURES}


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R293/plan.md",
        "training_script": Path(__file__).resolve(),
        "prior_agents": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "vector_agents": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "prior_environment": ROOT
        / "src/andes_rl_kundur/env/andes/prior_residual_env.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "development_bank": BANK_PATH,
        "classical_guard_summary": GUARD_SUMMARY,
        "classical_guard_provenance": GUARD_PROVENANCE,
    }


def _run_dir(out_root: Path, architecture: str, seed: int) -> Path:
    return out_root / f"{architecture}_s{seed}"


def _make_agent(
    architecture: str,
    device: str,
    contract: ClassicalEdgeContract,
) -> DistributedPriorResidualTD3:
    kwargs = {
        "classical_contract": contract,
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
    if architecture == "distributed_prior":
        return DistributedPriorResidualTD3(hidden_sizes=[64, 64], **kwargs)
    if architecture == "central_prior":
        return CentralPriorResidualTD3(
            critic_hidden_sizes=[64, 64],
            actor_hidden_sizes=[59, 59],
            **kwargs,
        )
    raise ValueError(f"unknown architecture: {architecture}")


def _actor_counts(contract: ClassicalEdgeContract) -> dict[str, int]:
    return {
        architecture: sum(
            parameter.numel()
            for parameter in _make_agent(architecture, "cpu", contract).actor.parameters()
        )
        for architecture in ARCHITECTURES
    }


def _flatten(observation: dict[int, np.ndarray]) -> np.ndarray:
    return np.concatenate(
        [np.asarray(observation[index], dtype=np.float32) for index in range(4)]
    ).astype(np.float32)


def smoke() -> None:
    """Run non-persisted real-ANDES inference smoke for both architectures."""

    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    scenario = _load_json(BANK_PATH)["scenarios"][0]
    contract = _selected_contract()
    outcome: dict[str, Any] = {}
    for architecture in ARCHITECTURES:
        torch.manual_seed(293)
        agent = _make_agent(architecture, "cpu", contract)
        env = PriorResidualEnv(
            AndesMultiVSGEnvV4Storage(random_disturbance=False, comm_fail_prob=0.0)
        )
        env.seed(293)
        env.STEPS_PER_EPISODE = 3
        completed = 0
        finite = True
        tds_failed = False
        try:
            observation = env.reset(delta_u=scenario["delta_u"])
            for _step in range(3):
                raw = agent.select_edge_actions(observation, deterministic=True)
                observation, _rewards, _done, info = env.step(raw)
                completed += 1
                tds_failed = bool(info.get("tds_failed", False))
                finite = finite and np.isfinite(info["r293_team_reward"])
                if tds_failed:
                    break
        finally:
            env.close()
        outcome[architecture] = {
            "completed_steps": completed,
            "tds_failed": tds_failed,
            "finite": bool(finite),
        }
        if completed != 3 or tds_failed or not finite:
            raise RuntimeError(f"R293 learned smoke failed: {architecture}")
    print(json.dumps(outcome, sort_keys=True), flush=True)


def prepare(manifest_path: Path, out_root: Path) -> None:
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            if (_run_dir(out_root, architecture, seed) / "controller_contract.json").exists():
                raise ValueError("training seal must precede all ten controller contracts")
    bank = _load_json(BANK_PATH)
    if len(bank.get("scenarios", [])) != 24:
        raise ValueError("training bank must contain 24 scenarios")
    contract = _selected_contract()
    counts = _actor_counts(contract)
    if counts != _expected_actor_counts():
        raise ValueError(f"actor capacity drift: {counts}")
    matched_relative_difference = None
    if {"central_prior", "distributed_prior"} <= set(counts):
        matched_relative_difference = abs(
            counts["central_prior"] - counts["distributed_prior"]
        ) / counts["distributed_prior"]
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
            packages[package] = "not-installed"
    vector = r292_vector_residual_contract().telemetry()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "phase": "matched-classical-prior-residual-training",
        "repository_head": _git_head(),
        "architectures": list(ARCHITECTURES),
        "seeds": list(SEEDS),
        "actor_parameter_counts": counts,
        "actor_parameter_relative_difference": matched_relative_difference,
        "training": _training_budget(),
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
        "classical_guard": {
            "summary_sha256": sha256_file(GUARD_SUMMARY),
            "provenance_sha256": sha256_file(GUARD_PROVENANCE),
            "classification": "CLASSICAL-GUARD-PASS",
        },
        "action_and_reward": {
            "vector_contract": vector,
            "classical_prior": contract.telemetry(),
            "actor_output_role": (
                "bounded magnitude residual only"
                if contract.reverse_limit == 0.0
                else "bounded aligned residual with limited reverse"
            ),
            "residual_scale": contract.residual_scale,
            "reverse_limit": contract.reverse_limit,
            "rocof_reward_weight": R293_ROCOF_REWARD_WEIGHT,
            "rocof_reward_scale_hz_s": R293_ROCOF_SCALE_HZ_S,
            "reward_sweep": False,
        },
        "packages": packages,
        "sources": sources,
        "controller_contract_count_at_freeze": 0,
    }
    digest = _write_new(manifest_path, payload)
    print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


def _verify(path: Path, expected: str) -> dict[str, Any]:
    manifest = _load_json(path, expected)
    if manifest.get("round") != ROUND_ID or manifest.get("phase") != "matched-classical-prior-residual-training":
        raise ValueError("not an R293 training seal")
    for entry in manifest["sources"].values():
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError(f"sealed training source drift: {entry['path']}")
    return manifest


def _controller_contract(
    manifest: dict[str, Any],
    *,
    seal_sha256: str,
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
            "joint_20d" if architecture == "central_prior" else "endpoint_10d_per_edge"
        ),
        "central_action_aggregation": False,
        "seed": seed,
        "device": device,
        "training_seal_sha256": seal_sha256,
        "actor_parameter_count": manifest["actor_parameter_counts"][architecture],
        "training": manifest["training"],
        "hyperparameters": manifest["hyperparameters"],
        "development_bank": manifest["development_bank"],
        "classical_guard": manifest["classical_guard"],
        "action_and_reward": manifest["action_and_reward"],
        "repository_head": _git_head(),
        "source_sha256": {
            name: entry["sha256"] for name, entry in manifest["sources"].items()
        },
        "command": [sys.executable, *sys.argv],
    }


def train(
    manifest_path: Path,
    expected: str,
    out_root: Path,
    architecture: str,
    seed: int,
    device: str,
    smoke_episodes: int | None,
) -> int:
    from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
        AndesMultiVSGEnvV4Storage,
    )

    manifest = _verify(manifest_path, expected)
    if architecture not in ARCHITECTURES or seed not in SEEDS:
        raise ValueError("architecture or seed outside frozen matrix")
    episodes = EPISODES if smoke_episodes is None else smoke_episodes
    if smoke_episodes is not None and not 1 <= smoke_episodes <= 3:
        raise ValueError("smoke episodes must lie in [1,3]")
    run_dir = (
        _run_dir(out_root, architecture, seed)
        if smoke_episodes is None
        else out_root / "smoke" / f"{architecture}_s{seed}_e{episodes}"
    )
    if (run_dir / "controller_contract.json").exists():
        raise FileExistsError(f"refusing to overwrite training run: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    controller_contract = _controller_contract(
        manifest,
        seal_sha256=expected,
        architecture=architecture,
        seed=seed,
        device=device,
    )
    controller_contract["smoke_episodes"] = smoke_episodes
    contract_digest = _write_new(run_dir / "controller_contract.json", controller_contract)
    scenarios = list(
        _load_json(BANK_PATH, manifest["development_bank"]["sha256"])["scenarios"]
    )
    classical = manifest["action_and_reward"]["classical_prior"]
    classical_contract = _contract_from_telemetry(classical)

    np.random.seed(seed)
    torch.manual_seed(seed)
    scenario_rng = np.random.default_rng(seed)
    exploration_rng = np.random.default_rng(seed + 10_000)
    agent = _make_agent(architecture, device, classical_contract)
    monitor: list[dict[str, Any]] = []
    total_steps = 0
    failed = False
    for episode in range(episodes):
        scenario = scenarios[int(scenario_rng.integers(0, len(scenarios)))]
        env = PriorResidualEnv(
            AndesMultiVSGEnvV4Storage(random_disturbance=False, comm_fail_prob=0.0)
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
                joint_observation = _flatten(observation)
                if total_steps < WARMUP_STEPS:
                    actor_residual = exploration_rng.uniform(
                        -1.0, 1.0, size=3
                    ).astype(np.float32)
                    raw = agent.compose_actor_residual(observation, actor_residual)
                else:
                    raw = agent.select_edge_actions(
                        observation, deterministic=False, rng=exploration_rng
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
                    reward=float(info["r293_team_reward"]),
                    next_observation=_flatten(next_observation),
                    done=terminal,
                )
                total_steps += 1
                completed_steps += 1
                episode_reward += float(info["r293_team_reward"])
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
            f"[R293 {architecture} s{seed} {episode + 1:03d}/{episodes:03d}] "
            f"completed={row['completed']}",
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
        "training_seal_sha256": expected,
        "smoke": smoke_episodes is not None,
    }
    checkpoint_path = run_dir / "final.pt"
    replay_path = run_dir / "replay_buffer.npz"
    monitor_path = run_dir / "training_monitor.json"
    agent.save(checkpoint_path, metadata=metadata)
    agent.buffer.save(str(replay_path))
    checkpoint_digest = _write_sidecar(checkpoint_path)
    replay_digest = _write_sidecar(replay_path)
    monitor_digest = _write_sidecar(monitor_path)
    summary = {
        **metadata,
        "checkpoint": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_sha256": checkpoint_digest,
        "replay_buffer_sha256": replay_digest,
        "training_monitor_sha256": monitor_digest,
        "failed": failed,
        "all_completed": len(monitor) == episodes and all(row["completed"] for row in monitor),
        "final_20_mean_reward": float(
            np.mean([row["episode_reward"] for row in monitor[-20:]])
        ),
        "final_20_mean_abs_edge": float(
            np.mean([row["mean_abs_edge"] for row in monitor[-20:]])
        ),
    }
    _write_new(run_dir / "training_summary.json", summary)
    return 1 if failed else 0


def verify_matrix(manifest_path: Path, expected: str, out_root: Path) -> None:
    _verify(manifest_path, expected)
    expected_run_count = len(ARCHITECTURES) * len(SEEDS)
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
            expected_fields = {
                "round": ROUND_ID,
                "architecture": architecture,
                "seed": seed,
                "episodes_completed": EPISODES,
                "total_steps": EPISODES * TRAINING_STEPS,
                "training_seal_sha256": expected,
                "smoke": False,
                "failed": False,
                "all_completed": True,
            }
            for key, value in expected_fields.items():
                if summary.get(key) != value:
                    raise ValueError(f"training matrix mismatch in {paths['summary']}: {key}")
            checks = {
                "checkpoint": summary["checkpoint_sha256"] == sha256_file(paths["checkpoint"]),
                "replay": summary["replay_buffer_sha256"] == sha256_file(paths["replay"]),
                "monitor": summary["training_monitor_sha256"] == sha256_file(paths["monitor"]),
                "contract": summary["controller_contract_sha256"] == sha256_file(paths["contract"]),
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
        "phase": "matched-classical-prior-residual-training-complete",
        "training_seal_sha256": expected,
        "expected_run_count": expected_run_count,
        "observed_run_count": len(rows),
        "all_completed": len(rows) == expected_run_count,
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
            "training_seal_sha256": expected,
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
    subparsers.add_parser("smoke")
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
    if args.command == "smoke":
        smoke()
        return 0
    if args.command == "prepare":
        prepare(args.manifest, args.out_root)
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
