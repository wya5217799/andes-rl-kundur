"""ANDES Kundur 4-VSG training entry point.

Runs in WSL with the andes_venv interpreter. Trains four independent
SAC agents (or one CTDE shared-critic ensemble) on the V4 paper-faithful
env. Replaces the historic train_andes.py + train_andes_v4.py +
train_andes_warmstart.py trio (now under _legacy/scenarios/kundur/).

Typical usage:

    /home/wya/andes_venv/bin/python scripts/train.py \\
        --episodes 75 --seed 49 --save-dir results/v4_h50_s49

    # Resume from a prior run
    /home/wya/andes_venv/bin/python scripts/train.py \\
        --episodes 1000 --seed 49 --resume results/v4_h50_s49 \\
        --save-dir results/v4_h50_s49_resumed

    # Shared-actor warmstart for all four agents
    /home/wya/andes_venv/bin/python scripts/train.py \\
        --episodes 500 --warmstart-shared results/phase9/actor.pt \\
        --save-dir results/v4_warmstart
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config as cfg  # noqa: E402
from agents.sac import SACAgent  # noqa: E402
from agents.sac_ctde import CTDECoordinator, SACAgentCTDE  # noqa: E402
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from utils.monitor import TrainingMonitor  # noqa: E402

# ─── CLI ───────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train MADRL agents on the V4 ANDES Kundur 4-VSG env.",
    )

    # Core training
    p.add_argument("--episodes", type=int, default=500)
    p.add_argument("--warmup", type=int, default=None,
                   help="Warmup steps (default: config.WARMUP_STEPS).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--seed-offset", type=int, default=0,
                   help="Seed offset, avoids replaying old episode trajectories.")
    p.add_argument("--save-dir", type=str, default="results/v4_train")
    p.add_argument("--log-interval", type=int, default=10)

    # Resume / warmstart
    p.add_argument("--resume", type=str, default=None,
                   help="Directory containing agent_i_final.pt (or latest agent_i_epN.pt) "
                        "to resume each agent's state from.")
    p.add_argument("--warmstart-shared", type=str, default=None,
                   help="Path to a single shared-actor checkpoint to use as the "
                        "initial state of every one of the N agents.")
    p.add_argument("--warmstart-mode", choices=["actor_only", "actor_and_critic"],
                   default="actor_only",
                   help="What to copy from --warmstart-shared.")

    # CTDE
    p.add_argument("--ctde", action="store_true",
                   help="Use Centralized-Training-Decentralized-Execution SAC "
                        "(shared centralized critic; decentralized actors).")

    # Env hyperparameters — override V4 class attrs before any env() call.
    # None = keep V4 default.
    p.add_argument("--phi-f",     type=float, default=None)
    p.add_argument("--phi-h",     type=float, default=None)
    p.add_argument("--phi-d",     type=float, default=None)
    p.add_argument("--phi-abs",   type=float, default=None,
                   help="Kundur tight-coupling penalty (not in paper Eq.14).")
    p.add_argument("--phi-max",   type=float, default=None,
                   help="R31 shaping: r_max_df = -max_i(|d_omega|)^2.")
    p.add_argument("--phi-settle", type=float, default=None,
                   help="R33 shaping: -1 per step where |d_omega_i| > SETTLE_THRESHOLD_HZ.")
    p.add_argument("--vsg-m0", type=float, default=None,
                   help="VSG_M0 = 2 H₀. V4 paper-faithful default = 200 (H₀=100s).")
    p.add_argument("--vsg-d0", type=float, default=None)
    p.add_argument("--dm-min", type=float, default=None)
    p.add_argument("--dm-max", type=float, default=None)
    p.add_argument("--dd-min", type=float, default=None)
    p.add_argument("--dd-max", type=float, default=None)
    p.add_argument("--comm-fail", type=float, default=None,
                   help="Override env comm_fail_prob.")

    # SAC hyperparameter overrides
    p.add_argument("--batch-size",  type=int, default=None)
    p.add_argument("--hidden-size", type=int, default=None,
                   help="Uniform width across all hidden layers.")

    return p.parse_args()


# ─── Setup helpers ─────────────────────────────────────────────────────


def patch_env_class_attrs(args: argparse.Namespace) -> dict[str, tuple[float, float]]:
    """Monkey-patch ``AndesMultiVSGEnvV4`` class attributes from CLI flags.

    Must run BEFORE the first env instance is constructed, because
    ``base_env.__init__`` reads the class attrs to compute ``self.M0`` /
    ``self.D0`` per agent.

    Returns a dict of ``{attr: (old, new)}`` for the training log.
    """
    overrides: dict[str, tuple[float, float]] = {}
    flag_to_attr = {
        "phi_f":      "PHI_F",
        "phi_h":      "PHI_H",
        "phi_d":      "PHI_D",
        "phi_abs":    "PHI_ABS",
        "phi_max":    "PHI_MAX",
        "phi_settle": "PHI_SETTLE",
        "vsg_m0":     "VSG_M0",
        "vsg_d0":     "VSG_D0",
        "dm_min":     "DM_MIN",
        "dm_max":     "DM_MAX",
        "dd_min":     "DD_MIN",
        "dd_max":     "DD_MAX",
    }
    for flag, attr in flag_to_attr.items():
        val = getattr(args, flag)
        if val is None:
            continue
        old = getattr(AndesMultiVSGEnvV4, attr)
        setattr(AndesMultiVSGEnvV4, attr, float(val))
        overrides[attr] = (float(old), float(val))

    if overrides:
        print(" [hparam-override]")
        for k, (old, new) in overrides.items():
            print(f"   {k}: {old} -> {new}")
    return overrides


def restore_env_class_attrs(overrides: dict[str, tuple[float, float]]) -> None:
    """Undo ``patch_env_class_attrs`` so re-imports in the same process
    see the original V4 class defaults (relevant for sweep harnesses)."""
    for attr, (old, _) in overrides.items():
        setattr(AndesMultiVSGEnvV4, attr, old)


def pick_device() -> str:
    """Resolve DEVICE env var with CUDA-availability fallback."""
    requested = os.environ.get("DEVICE", "cpu").lower()
    if requested == "cuda" and not torch.cuda.is_available():
        print("[device] DEVICE=cuda requested but unavailable, falling back to cpu")
        return "cpu"
    print(f"[device] using {requested}")
    return requested


def obs_dim_with_optional_action(base_dim: int) -> tuple[int, bool]:
    """Apply the INCLUDE_OWN_ACTION_OBS env-var augmentation (+2)."""
    include = bool(int(os.environ.get("INCLUDE_OWN_ACTION_OBS", "0")))
    if include:
        return base_dim + 2, True
    return base_dim, False


def build_agents(
    args: argparse.Namespace,
    obs_dim: int,
    action_dim: int,
    hidden_sizes: list[int],
    lr: float,
    gamma: float,
    tau: float,
    buffer_size: int,
    batch_size: int,
    device: str,
) -> tuple[list, "CTDECoordinator | None"]:
    """Construct N actors (and optionally a shared CTDE critic)."""
    N = AndesMultiVSGEnvV4.N_AGENTS
    coordinator: CTDECoordinator | None = None

    if args.ctde:
        print("[CTDE] shared centralized critic enabled.")
        agents = [
            SACAgentCTDE(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes, lr=lr,
                buffer_size=buffer_size, batch_size=batch_size, device=device,
            )
            for _ in range(N)
        ]
        coordinator = CTDECoordinator(
            n_agents=N, obs_dim=obs_dim, action_dim=action_dim,
            hidden_sizes=hidden_sizes, lr=lr, gamma=gamma, tau=tau,
            batch_size=batch_size, device=device,
        )
        print(f"[CTDE] centralized critic input dim: {obs_dim * N + action_dim * N}")
    else:
        agents = [
            SACAgent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes,
                lr=lr, gamma=gamma, tau=tau,
                buffer_size=buffer_size, batch_size=batch_size, device=device,
            )
            for _ in range(N)
        ]

    return agents, coordinator


def apply_resume(agents: list, args: argparse.Namespace,
                 coordinator: "CTDECoordinator | None") -> None:
    """Restore agent state from ``args.resume``."""
    if not args.resume:
        return
    import glob
    N = len(agents)
    for i in range(N):
        path = Path(args.resume) / f"agent_{i}_final.pt"
        if not path.exists():
            ep_ckpts = sorted(
                glob.glob(str(Path(args.resume) / f"agent_{i}_ep*.pt")),
                key=lambda p: int(p.rsplit("ep", 1)[-1].split(".")[0]),
            )
            if ep_ckpts:
                path = Path(ep_ckpts[-1])
        if path.exists():
            if args.ctde:
                agents[i].load_actor_only(str(path))
                print(f"  Resumed agent {i} actor from {path} (CTDE warmstart)")
            else:
                agents[i].load(str(path))
                print(f"  Resumed agent {i} from {path}")
        else:
            print(f"  [WARN] no checkpoint found for agent {i}; starting fresh")

    if args.ctde and coordinator is not None:
        critic_path = Path(args.resume) / "ctde_critic.pt"
        if critic_path.exists():
            coordinator.load_critic(str(critic_path))
            print(f"  Resumed CTDE shared critic from {critic_path}")


def apply_warmstart_shared(agents: list, args: argparse.Namespace) -> None:
    """Copy one shared-actor checkpoint into every agent."""
    if not args.warmstart_shared:
        return
    src = Path(args.warmstart_shared)
    if not src.exists():
        raise FileNotFoundError(f"warmstart-shared checkpoint not found: {src}")
    state = torch.load(src, map_location="cpu", weights_only=False)
    if "actor" not in state:
        raise KeyError(
            f"warmstart-shared ckpt missing 'actor' key. "
            f"Available keys: {list(state.keys())}"
        )
    print(f"[warmstart-shared] loading actor from {src} into all {len(agents)} agents")
    for i, ag in enumerate(agents):
        ag.actor.load_state_dict(state["actor"])
        if args.warmstart_mode == "actor_and_critic" and "critic" in state:
            ag.critic.load_state_dict(state["critic"])
            if "critic_target" in state:
                ag.critic_target.load_state_dict(state["critic_target"])
            print(f"  agent {i}: actor + critic copied")
        else:
            print(f"  agent {i}: actor only")


# ─── Training loop ─────────────────────────────────────────────────────


def run_episode(
    env: AndesMultiVSGEnvV4,
    agents: list,
    total_steps: int,
    args: argparse.Namespace,
    action_dim: int,
) -> dict:
    """Roll out one episode, collect rewards / actions / monitor stats."""
    N = env.N_AGENTS
    try:
        obs = env.reset()
    except Exception as e:
        return {"reset_failed": True, "reason": str(e)}

    ep_reward = {i: 0.0 for i in range(N)}
    ep_r_f, ep_r_h, ep_r_d = 0.0, 0.0, 0.0
    ep_actions_list: list[np.ndarray] = []
    ep_max_freq = 0.0
    ep_tds_failed = False

    for step in range(AndesMultiVSGEnvV4.STEPS_PER_EPISODE):
        actions = {}
        for i in range(N):
            if total_steps < args.warmup:
                actions[i] = np.random.uniform(-1, 1, size=action_dim)
            else:
                actions[i] = agents[i].select_action(obs[i])

        try:
            next_obs, rewards, done, info = env.step(actions)
        except Exception as e:
            print(f"  [step {step}] step failed: {e}")
            break

        ep_actions_list.append(np.array([actions[i] for i in range(N)]))
        ep_r_f += info.get("r_f", 0.0)
        ep_r_h += info.get("r_h", 0.0)
        ep_r_d += info.get("r_d", 0.0)
        ep_max_freq = max(ep_max_freq, info.get("max_freq_deviation_hz", 0.0))
        ep_tds_failed = ep_tds_failed or info.get("tds_failed", False)

        for i in range(N):
            agents[i].buffer.add(obs[i], actions[i], rewards[i],
                                 next_obs[i], float(done))
            ep_reward[i] += rewards[i]
        obs = next_obs
        total_steps += 1
        if done:
            break

    return {
        "reset_failed": False,
        "ep_reward":      ep_reward,
        "ep_r_f":         ep_r_f,
        "ep_r_h":         ep_r_h,
        "ep_r_d":         ep_r_d,
        "ep_actions":     ep_actions_list,
        "ep_max_freq":    ep_max_freq,
        "ep_tds_failed":  ep_tds_failed,
        "total_steps":    total_steps,
    }


def run_updates(
    agents: list,
    coordinator: "CTDECoordinator | None",
    batch_size: int,
    n_epoch: int = 10,
) -> list[dict | None]:
    """Run N_EPOCH × per-agent (or coordinator) SAC updates."""
    N = len(agents)
    ep_sac_losses: list[dict | None] = [None] * N

    if coordinator is not None:
        last_loss = None
        for _ in range(n_epoch):
            loss_info = coordinator.update(agents)
            if loss_info is not None:
                last_loss = loss_info
        if last_loss is not None:
            ep_sac_losses = [last_loss] * N
    else:
        for _ in range(n_epoch):
            for i in range(N):
                if len(agents[i].buffer) >= batch_size:
                    loss_info = agents[i].update()
                    if loss_info is not None:
                        ep_sac_losses[i] = loss_info
    return ep_sac_losses


# ─── Main ──────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()

    if args.warmup is None:
        args.warmup = cfg.WARMUP_STEPS

    np.random.seed(args.seed + args.seed_offset)
    torch.manual_seed(args.seed + args.seed_offset)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed + args.seed_offset)

    print("=" * 60)
    print(f" ANDES Kundur 4-VSG training — {args.episodes} episodes (V4 env)")
    print("=" * 60)

    hparam_overrides = patch_env_class_attrs(args)

    os.makedirs(args.save_dir, exist_ok=True)

    # Env probe to read N_AGENTS / OBS_DIM consistently
    N = AndesMultiVSGEnvV4.N_AGENTS
    obs_dim, include_action_obs = obs_dim_with_optional_action(
        AndesMultiVSGEnvV4.OBS_DIM
    )
    if include_action_obs:
        print(f"[obs] INCLUDE_OWN_ACTION_OBS=1 -> obs_dim {AndesMultiVSGEnvV4.OBS_DIM} -> {obs_dim}")
    action_dim = 2

    # SAC hyperparameters
    hidden_sizes = cfg.HIDDEN_SIZES
    batch_size = cfg.BATCH_SIZE
    if args.batch_size is not None:
        print(f"[hparam-override] BATCH_SIZE: {batch_size} -> {args.batch_size}")
        batch_size = args.batch_size
    if args.hidden_size is not None:
        new_hidden = [args.hidden_size] * len(hidden_sizes)
        print(f"[hparam-override] HIDDEN_SIZES: {hidden_sizes} -> {new_hidden}")
        hidden_sizes = new_hidden

    device = pick_device()
    agents, coordinator = build_agents(
        args, obs_dim, action_dim, hidden_sizes,
        lr=cfg.LR, gamma=cfg.GAMMA, tau=cfg.TAU_SOFT,
        buffer_size=cfg.BUFFER_SIZE, batch_size=batch_size, device=device,
    )

    apply_resume(agents, args, coordinator)
    apply_warmstart_shared(agents, args)

    # Best-reward callback saves best.pt
    def on_best_reward(ep: int, reward: float) -> None:
        print(f"  [Monitor] New best reward: {reward:.1f} @ ep {ep}")
        for i in range(N):
            agents[i].save(os.path.join(args.save_dir, f"agent_{i}_best.pt"))
        if coordinator is not None:
            coordinator.save_critic(
                os.path.join(args.save_dir, "ctde_critic_best.pt"),
            )

    monitor = TrainingMonitor(best_reward_callback=on_best_reward)

    # Comm-failure override (M1 review 2026-05-07)
    comm_fail = args.comm_fail if args.comm_fail is not None else 0.1

    episode_rewards: dict[int, list[float]] = {i: [] for i in range(N)}
    total_rewards: list[float] = []
    total_steps = 0
    last_ep = -1
    interrupted = False
    t_start = time.time()

    try:
        for ep in range(args.episodes):
            env = AndesMultiVSGEnvV4(random_disturbance=True, comm_fail_prob=comm_fail)
            env.seed(args.seed + args.seed_offset + ep)

            stats = run_episode(env, agents, total_steps, args, action_dim)
            if stats.get("reset_failed"):
                print(f"  [ep {ep}] reset failed: {stats['reason']}; skipping")
                continue
            total_steps = stats["total_steps"]

            ep_sac_losses: list[dict | None] = [None] * N
            if total_steps >= args.warmup:
                ep_sac_losses = run_updates(agents, coordinator, batch_size)

            if stats["ep_actions"]:
                should_stop = monitor.log_and_check(
                    episode=ep,
                    rewards=sum(stats["ep_reward"].values()),
                    reward_components={
                        "r_f": stats["ep_r_f"],
                        "r_h": stats["ep_r_h"],
                        "r_d": stats["ep_r_d"],
                    },
                    actions=np.array(stats["ep_actions"]),
                    info={
                        "tds_failed": stats["ep_tds_failed"],
                        "max_freq_deviation_hz": stats["ep_max_freq"],
                    },
                    per_agent_rewards=stats["ep_reward"],
                    sac_losses=[l for l in ep_sac_losses if l is not None] or None,
                )
                if should_stop:
                    break

            if cfg.CLEAR_BUFFER_PER_EPISODE:
                for i in range(N):
                    agents[i].buffer.clear()

            for i in range(N):
                episode_rewards[i].append(stats["ep_reward"][i])
            total_rewards.append(sum(stats["ep_reward"].values()))
            last_ep = ep

            if (ep + 1) % args.log_interval == 0:
                elapsed = time.time() - t_start
                window = max(1, args.log_interval)
                avg_reward = float(np.mean(total_rewards[-window:]))
                print(
                    f"  Ep {ep+1}/{args.episodes} | "
                    f"Avg Reward: {avg_reward:.1f} | "
                    f"Steps: {total_steps} | "
                    f"Time: {elapsed:.0f}s",
                )

            if (ep + 1) % 100 == 0:
                for i in range(N):
                    agents[i].save(os.path.join(args.save_dir, f"agent_{i}_ep{ep+1}.pt"))
                if coordinator is not None:
                    coordinator.save_critic(
                        os.path.join(args.save_dir, f"ctde_critic_ep{ep+1}.pt"),
                    )

            env.close()

    except KeyboardInterrupt:
        interrupted = True
        print(f"\n[!] Training interrupted at ep {last_ep + 1}. Saving checkpoint...")

    monitor.summary()
    monitor.save_checkpoint(os.path.join(args.save_dir, "monitor_checkpoint.json"))
    monitor.export_csv(os.path.join(args.save_dir, "monitor_data.csv"))

    if last_ep >= 0:
        for i in range(N):
            agents[i].save(os.path.join(args.save_dir, f"agent_{i}_final.pt"))
        if coordinator is not None:
            coordinator.save_critic(os.path.join(args.save_dir, "ctde_critic.pt"))

        log = {
            "episode_rewards":   {str(i): episode_rewards[i] for i in range(N)},
            "total_rewards":     total_rewards,
            "total_steps":       total_steps,
            "episodes_completed": last_ep + 1,
            "episodes_planned":  args.episodes,
            "interrupted":       interrupted,
            "hparam_overrides":  {k: new for k, (_, new) in hparam_overrides.items()},
            "hparam_effective":  {
                "PHI_F":  AndesMultiVSGEnvV4.PHI_F,
                "PHI_H":  AndesMultiVSGEnvV4.PHI_H,
                "PHI_D":  AndesMultiVSGEnvV4.PHI_D,
                "VSG_M0": AndesMultiVSGEnvV4.VSG_M0,
                "VSG_D0": AndesMultiVSGEnvV4.VSG_D0,
                "DM_MIN": AndesMultiVSGEnvV4.DM_MIN,
                "DM_MAX": AndesMultiVSGEnvV4.DM_MAX,
                "DD_MIN": AndesMultiVSGEnvV4.DD_MIN,
                "DD_MAX": AndesMultiVSGEnvV4.DD_MAX,
            },
        }
        log_path = os.path.join(args.save_dir, "training_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log, f)
        print(f"\nTraining log saved to {log_path}")
    else:
        print("\nNo episodes completed, nothing to save.")

    restore_env_class_attrs(hparam_overrides)
    print(f"\nTotal time: {time.time() - t_start:.0f}s")
    print("Done!")


if __name__ == "__main__":
    main()
