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
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur import config as cfg  # noqa: E402
from andes_rl_kundur.agents.episode_result import EpisodeResult  # noqa: E402
from andes_rl_kundur.agents.sac import SACAgent  # noqa: E402
from andes_rl_kundur.agents.sac_ctde import CTDECoordinator, SACAgentCTDE  # noqa: E402
from andes_rl_kundur.agents.td3 import TD3Agent  # noqa: E402
from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.scenarios.kundur.training_checks import (  # noqa: E402
    register_kundur_default_checks,
)
from andes_rl_kundur.utils.monitor import TrainingMonitor  # noqa: E402

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

    # Algorithm selection
    p.add_argument("--algo", choices=["sac", "td3", "td3_lstm"], default="sac",
                   help="Per-agent RL algorithm. 'sac' (default) uses "
                        "entropy-regularized soft AC; 'td3' uses "
                        "deterministic policy + target smoothing + delayed "
                        "policy updates (no entropy bonus); 'td3_lstm' (R56) "
                        "uses TD3 with a recurrent LSTMCell actor/critic — "
                        "policy is structurally time-varying via hidden "
                        "state, escaping the R49-R55 hexagon's static-"
                        "setpoint attractor.")

    # CTDE (SAC only)
    p.add_argument("--ctde", action="store_true",
                   help="Use Centralized-Training-Decentralized-Execution SAC "
                        "(shared centralized critic; decentralized actors). "
                        "Mutually exclusive with --algo td3.")

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
    p.add_argument("--normalize-actions", action="store_true",
                   help="Use V4Config.action_penalty_mode='normalized': "
                        "penalize action in normalized [-1,1] space "
                        "instead of physical ΔM/ΔD space. Avoids the "
                        "CLM-0043 action-vs-frequency reward asymmetry.")

    # SAC hyperparameter overrides
    p.add_argument("--batch-size",  type=int, default=None)
    p.add_argument("--hidden-size", type=int, default=None,
                   help="Uniform width across all hidden layers.")
    # R67 — discount factor sweep (CLI flag, not env var, to avoid
    # import-time RNG state shift suspected in CLM-0104 LSTM drift).
    p.add_argument("--gamma", type=float, default=None,
                   help="Discount factor override (default cfg.GAMMA=0.99).")
    p.add_argument("--tau", type=float, default=None,
                   help="Target soft update rate (default cfg.TAU_SOFT=0.005).")
    p.add_argument("--buffer-size", type=int, default=None,
                   help="Replay buffer size (default cfg.BUFFER_SIZE=10000).")

    # R58 — reward-config selector (ADR-0002)
    p.add_argument(
        "--reward-config",
        choices=["paper_faithful", "paper_strict_pure",
                 "paper_strict_rescaled", "paper_strict_pure_radsec"],
        default=None,
        help="Base V4Config classmethod. Default (None) = paper_faithful "
             "(R56/R57 behaviour, PHI_ABS=50, PHI_H/D=0.0056). "
             "paper_strict_pure: paper Eq.14 nominal (PHI_ABS=0, "
             "PHI_H=PHI_D=1.0). paper_strict_rescaled: PHI_ABS=0 but "
             "R18 PHI_H/D rescale retained. paper_strict_pure_radsec: "
             "as paper_strict_pure but with rad/s frequency units for "
             "r^f (R58 audit A3). Individual --phi-* flags still "
             "override fields of the selected base config.",
    )

    # R57-α — LSTM-specific lr warmup
    p.add_argument("--lstm-lr-warmup-eps", type=int, default=0,
                   help="(--algo td3_lstm only) ramp lr from "
                        "target/N at ep 1 to target at ep N. Mitigates "
                        "early critic-loss explosion that caused the "
                        "R56 s50 collapse. Default 0 = no warmup.")

    # R61 — Q-0007 eval-tracked best.pt
    p.add_argument("--eval-every-n-eps", type=int, default=0,
                   help="Q-0007 (R61): every N episodes, run a paper-"
                        "metric eval probe (LS1+LS2 anchors, ~5s each) "
                        "and save 'agent_i_best_eval.pt' on score "
                        "improvement. Parallel to best.pt (train-reward) "
                        "tracking. Default 0 = disabled. "
                        "Typical N=5 → ~5% wall overhead; insulates "
                        "downstream eval from pre-training best.pt "
                        "spike artifact (R57 s50 collapse mechanism).")

    # R78 — auto post-training dual-eval (paper §IV-C cum_rf + 11-axis geo)
    p.add_argument("--final-eval", dest="final_eval",
                   action=argparse.BooleanOptionalAction, default=True,
                   help="After training, run the canonical dual-eval "
                        "(LS1+LS2 → paper §IV-C cum_rf + 11-axis geo) on "
                        "the saved ckpt and write "
                        "<save-dir>/final_eval_summary.json. Default on. "
                        "Use --no-final-eval to skip (e.g. for smoke runs).")

    return p.parse_args()


# ─── Setup helpers ─────────────────────────────────────────────────────


def build_v4_config(args: argparse.Namespace) -> V4Config:
    """Translate CLI hyperparameter flags into an explicit :class:`V4Config`.

    Flags left at ``None`` inherit the paper-faithful defaults; explicit
    values override them. Replaces the historic ``patch_env_class_attrs``
    + ``restore_env_class_attrs`` monkey-patch pair (root cause of
    CLM-0040 silent inheritance class of bugs).
    """
    # R58: pick the BASE config from --reward-config. The per-field
    # --phi-* / --vsg-* overrides below still win (programmer intent
    # precedence).
    reward_cfg = getattr(args, "reward_config", None)
    if reward_cfg is None or reward_cfg == "paper_faithful":
        base = V4Config.paper_faithful()
    elif reward_cfg == "paper_strict_pure":
        base = V4Config.paper_strict_pure()
    elif reward_cfg == "paper_strict_rescaled":
        base = V4Config.paper_strict_rescaled()
    elif reward_cfg == "paper_strict_pure_radsec":
        base = V4Config.paper_strict_pure_radsec()
    else:
        raise ValueError(
            f"Unknown --reward-config: {reward_cfg!r}. "
            f"Choices: paper_faithful | paper_strict_pure | paper_strict_rescaled"
        )
    overrides = {
        field: getattr(args, flag)
        for flag, field in [
            ("phi_f", "phi_f"), ("phi_h", "phi_h"), ("phi_d", "phi_d"),
            ("phi_abs", "phi_abs"), ("phi_max", "phi_max"),
            ("phi_settle", "phi_settle"),
            ("vsg_m0", "vsg_m0"), ("vsg_d0", "vsg_d0"),
            ("dm_min", "dm_min"), ("dm_max", "dm_max"),
            ("dd_min", "dd_min"), ("dd_max", "dd_max"),
        ]
        if getattr(args, flag) is not None
    }
    if getattr(args, "normalize_actions", False):
        overrides["action_penalty_mode"] = "normalized"
    if overrides:
        print(" [V4Config override]")
        for k, v in overrides.items():
            print(f"   {k}: {getattr(base, k)} -> {v}")
        return dataclasses.replace(base, **overrides)
    return base


def pick_device() -> str:
    """Resolve DEVICE env var with CUDA-availability fallback."""
    requested = os.environ.get("DEVICE", "cpu").lower()
    if requested == "cuda" and not torch.cuda.is_available():
        print("[device] DEVICE=cuda requested but unavailable, falling back to cpu")
        return "cpu"
    print(f"[device] using {requested}")
    return requested


def obs_dim_with_optional_action(base_dim: int) -> tuple[int, bool]:
    """Apply env-var obs augmentations (+2 own_action, +1 time).

    R52 (CLM-0059 follow-up): added INCLUDE_TIME_OBS env var to bump
    obs_dim by 1 (normalized episode progress slot). Mutually exclusive
    with INCLUDE_OWN_ACTION_OBS — enforced both by V4Config.__post_init__
    and inline below.
    """
    include_action = bool(int(os.environ.get("INCLUDE_OWN_ACTION_OBS", "0")))
    include_time = bool(int(os.environ.get("INCLUDE_TIME_OBS", "0")))
    if include_action and include_time:
        raise ValueError(
            "INCLUDE_OWN_ACTION_OBS=1 and INCLUDE_TIME_OBS=1 are mutually "
            "exclusive (slot-layout conflict); pick one."
        )
    if include_action:
        return base_dim + 2, True
    if include_time:
        return base_dim + 1, True
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
) -> tuple[list, CTDECoordinator | None]:
    """Construct N actors (and optionally a shared CTDE critic)."""
    N = AndesMultiVSGEnvV4.N_AGENTS
    coordinator: CTDECoordinator | None = None

    if args.ctde and args.algo in ("td3", "td3_lstm"):
        raise ValueError(
            f"--ctde is SAC-only; pass --algo sac or drop --ctde "
            f"(got --algo {args.algo})"
        )

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
    elif args.algo == "td3":
        print("[algo] TD3 — deterministic policy, twin critics, no entropy bonus")
        agents = [
            TD3Agent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes,
                lr=lr, gamma=gamma, tau=tau,
                buffer_size=buffer_size, batch_size=batch_size, device=device,
            )
            for _ in range(N)
        ]
    elif args.algo == "td3_lstm":
        # R56: LSTMCell recurrent actor + critic. The recurrent path uses
        # its own (sequence) batch size and (episode) buffer size, both
        # decoupled from the step-level SAC/TD3 hyperparameters.
        lstm_batch_size = 32  # sequences per gradient step
        lstm_capacity_episodes = 200
        # LSTMCell is a single-layer cell; only the first hidden width
        # is used. lr clamped to 1e-4 for RNN stability (vs 3e-4 baseline).
        # R65 — LSTM_LR_UNCLAMP=1 env var disables the clamp (hyper sweep).
        if os.environ.get("LSTM_LR_UNCLAMP") == "1":
            lstm_lr = lr
        else:
            lstm_lr = min(lr, 1e-4)
        warmup_eps = getattr(args, "lstm_lr_warmup_eps", 0) or 0
        warmup_note = f" warmup_eps={warmup_eps}" if warmup_eps > 0 else ""
        print(
            f"[algo] TD3+LSTM — recurrent actor/critic, hidden={hidden_sizes[0]}, "
            f"seq=25 burn=5, batch={lstm_batch_size} seq, lr={lstm_lr}{warmup_note}"
        )
        agents = [
            TD3LSTMAgent(
                obs_dim=obs_dim, action_dim=action_dim,
                hidden_sizes=hidden_sizes,
                lr=lstm_lr, gamma=gamma, tau=tau,
                buffer_size=lstm_capacity_episodes,
                batch_size=lstm_batch_size,
                device=device,
                seq_len=25, burn_in=5,
                lr_warmup_eps=warmup_eps,
            )
            for _ in range(N)
        ]
    else:
        print("[algo] SAC — entropy-regularized")
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
                 coordinator: CTDECoordinator | None) -> None:
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
    if args.algo == "td3_lstm":
        # RecurrentActor state_dict has different keys (lstm.weight_ih /
        # lstm.weight_hh / fc_out.*) from GaussianActor (net.*.weight /
        # mean_head / log_std_head). Cross-architecture warmstart is
        # undefined; refuse explicitly rather than silently fail.
        raise ValueError(
            "--warmstart-shared is incompatible with --algo td3_lstm "
            "(MLP-actor and LSTM-actor state_dicts have disjoint keys)"
        )
    src = Path(args.warmstart_shared)
    if not src.exists():
        raise FileNotFoundError(f"warmstart-shared checkpoint not found: {src}")
    state = torch.load(src, map_location="cpu", weights_only=True)
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
) -> EpisodeResult:
    """Roll out one episode, return a typed :class:`EpisodeResult`."""
    N = env.N_AGENTS
    try:
        obs = env.reset()
    except Exception as e:
        return EpisodeResult.from_reset_failure(str(e), total_steps=total_steps)

    # Recurrent agents (R56): reset the per-rollout hidden state and the
    # in-progress transition buffer. No-op for memoryless agents.
    for ag in agents:
        if getattr(ag, "is_recurrent", False):
            ag.begin_episode()

    ep_reward = {i: 0.0 for i in range(N)}
    ep_r_f, ep_r_h, ep_r_d = 0.0, 0.0, 0.0
    ep_actions_list: list[np.ndarray] = []
    ep_max_freq = 0.0
    ep_tds_failed = False

    for step in range(AndesMultiVSGEnvV4.STEPS_PER_EPISODE):
        actions = {}
        for i in range(N):
            if total_steps < args.warmup:
                actions[i] = np.random.uniform(-1, 1, size=action_dim).astype(np.float32)
                # Recurrent agents still need to advance the rollout
                # hidden state even when the action is overridden by
                # warmup-random — call select_action then discard, so
                # the LSTM sees the obs sequence during warmup.
                # ``deterministic=True`` makes the intent explicit: the
                # noise added inside ``select_action`` is irrelevant here
                # (the action is overridden), and we don't want a reader
                # to think the LSTM hidden state is influenced by
                # exploration noise (it isn't, but the call shouldn't
                # invite that misreading).
                if getattr(agents[i], "is_recurrent", False):
                    agents[i].select_action(obs[i], deterministic=True)
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
            # store_transition handles both per-step (SAC/TD3) and
            # per-episode (TD3+LSTM) replay buffers uniformly.
            agents[i].store_transition(
                obs[i], actions[i], rewards[i], next_obs[i], bool(done)
            )
            ep_reward[i] += rewards[i]
        obs = next_obs
        total_steps += 1
        if done:
            break

    # Safety net: if the loop exited without a final done=True (e.g.
    # the inner step raised before env signalled termination), flush
    # any in-progress recurrent episode to its buffer so the data is
    # not lost.
    for ag in agents:
        if getattr(ag, "is_recurrent", False):
            ag.flush_episode()

    return EpisodeResult(
        reset_failed=False,
        ep_reward=ep_reward,
        ep_r_f=ep_r_f, ep_r_h=ep_r_h, ep_r_d=ep_r_d,
        ep_actions=ep_actions_list,
        ep_max_freq=ep_max_freq,
        ep_tds_failed=ep_tds_failed,
        total_steps=total_steps,
    )


def run_updates(
    agents: list,
    coordinator: CTDECoordinator | None,
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
                ag = agents[i]
                # Recurrent agents (R56) gate inside ``update`` itself
                # (the buffer is episode-keyed and may have stored
                # episodes that are too short for the seq window — the
                # step-level ``len(buffer) >= batch_size`` precheck is
                # not meaningful for them, so we short-circuit on
                # ``is_recurrent`` and skip the precheck entirely).
                if ag.is_recurrent or len(ag.buffer) >= batch_size:
                    loss_info = ag.update()
                else:
                    loss_info = None
                if loss_info is not None:
                    ep_sac_losses[i] = loss_info
    return ep_sac_losses


# ─── Main ──────────────────────────────────────────────────────────────


def _save_checkpoint(
    agents: list,
    coordinator: CTDECoordinator | None,
    save_dir: str,
    actor_tag: str,
    critic_filename: str,
) -> None:
    """Save all agent actors with the given tag and (optionally) the CTDE
    shared critic to ``critic_filename``. Centralizes the 4 prior copies
    (on_best_reward / on_best_eval / periodic ep%100 / final)."""
    for i, ag in enumerate(agents):
        ag.save(os.path.join(save_dir, f"agent_{i}_{actor_tag}.pt"))
    if coordinator is not None:
        coordinator.save_critic(os.path.join(save_dir, critic_filename))


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

    env_config = build_v4_config(args)

    os.makedirs(args.save_dir, exist_ok=True)

    # Env probe to read N_AGENTS / OBS_DIM consistently
    N = AndesMultiVSGEnvV4.N_AGENTS
    obs_dim, include_action_obs = obs_dim_with_optional_action(
        AndesMultiVSGEnvV4.OBS_DIM
    )
    if include_action_obs:
        probe = "INCLUDE_TIME_OBS" if os.environ.get("INCLUDE_TIME_OBS", "0") == "1" else "INCLUDE_OWN_ACTION_OBS"
        print(f"[obs] {probe}=1 -> obs_dim {AndesMultiVSGEnvV4.OBS_DIM} -> {obs_dim}")
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
    # R64 — LR env var override (hyper sweep)
    lr = float(os.environ.get("LR", str(cfg.LR)))
    # R67 — gamma / tau / buffer_size CLI overrides
    gamma = args.gamma if args.gamma is not None else cfg.GAMMA
    tau = args.tau if args.tau is not None else cfg.TAU_SOFT
    buf_size = args.buffer_size if args.buffer_size is not None else cfg.BUFFER_SIZE
    agents, coordinator = build_agents(
        args, obs_dim, action_dim, hidden_sizes,
        lr=lr, gamma=gamma, tau=tau,
        buffer_size=buf_size, batch_size=batch_size, device=device,
    )

    apply_resume(agents, args, coordinator)
    apply_warmstart_shared(agents, args)

    # Best-reward callback saves best.pt
    def on_best_reward(ep: int, reward: float) -> None:
        print(f"  [Monitor] New best reward: {reward:.1f} @ ep {ep}")
        _save_checkpoint(agents, coordinator, args.save_dir,
                         actor_tag="best", critic_filename="ctde_critic_best.pt")

    # Q-0007 (R61) — eval-tracked best.pt callback
    def on_best_eval(ep: int, eval_score: float) -> None:
        print(f"  [Monitor] New best eval cum_rf: {eval_score:.4f} @ ep {ep}")
        _save_checkpoint(agents, coordinator, args.save_dir,
                         actor_tag="best_eval",
                         critic_filename="ctde_critic_best_eval.pt")

    monitor = TrainingMonitor(
        best_reward_callback=on_best_reward,
        best_eval_callback=on_best_eval if args.eval_every_n_eps > 0 else None,
    )
    register_kundur_default_checks(monitor)

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
            env = AndesMultiVSGEnvV4(
                random_disturbance=True, comm_fail_prob=comm_fail,
                config=env_config,
            )
            env.seed(args.seed + args.seed_offset + ep)

            result = run_episode(env, agents, total_steps, args, action_dim)
            if result.reset_failed:
                print(f"  [ep {ep}] reset failed: {result.reason}; skipping")
                continue
            total_steps = result.total_steps

            ep_sac_losses: list[dict | None] = [None] * N
            if total_steps >= args.warmup:
                ep_sac_losses = run_updates(agents, coordinator, batch_size)

            if result.ep_actions:
                should_stop = monitor.log_and_check(
                    episode=ep,
                    sac_losses=[loss for loss in ep_sac_losses if loss is not None] or None,
                    **result.to_monitor_kwargs(),
                )
                if should_stop:
                    break

            if cfg.CLEAR_BUFFER_PER_EPISODE:
                for i in range(N):
                    agents[i].buffer.clear()

            for i in range(N):
                episode_rewards[i].append(result.ep_reward[i])
            total_rewards.append(sum(result.ep_reward.values()))
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
                tag = f"ep{ep+1}"
                _save_checkpoint(agents, coordinator, args.save_dir,
                                 actor_tag=tag,
                                 critic_filename=f"ctde_critic_{tag}.pt")

            env.close()

            # Q-0007 (R61) — periodic paper-metric eval probe.
            # **R66 Q-0010 fix**: moved AFTER env.close(). ANDES has
            # single-session-per-process limit (paper_path.py:148-152
            # NOTES_ANDES.md). Pre-R66 placement before env.close()
            # caused training env / eval env conflict for LSTM training,
            # silently corrupting policy (CLM-0099 mechanism narrowed).
            # Skipped during warmup phase to avoid pre-training spikes
            # (CLM-0073).
            if (
                args.eval_every_n_eps > 0
                and (ep + 1) % args.eval_every_n_eps == 0
                and total_steps >= args.warmup
            ):
                from andes_rl_kundur.evaluation.paper_strict_eval import (
                    evaluate_agents_paper_metric,
                )
                # Save+restore numpy/torch RNG state to avoid eval probe
                # shifting training stochastics (Q-0010 secondary cause).
                np_state = np.random.get_state()
                torch_state = torch.get_rng_state()
                try:
                    eval_score = evaluate_agents_paper_metric(
                        agents, config=env_config,
                    )
                finally:
                    np.random.set_state(np_state)
                    torch.set_rng_state(torch_state)
                is_new_best = monitor.update_eval_score(ep, eval_score)
                if not is_new_best:
                    print(
                        f"  [Eval probe] ep {ep+1}: cum_rf = {eval_score:.4f} "
                        f"(best = {monitor._best_eval_score:.4f} @ ep {monitor._best_eval_episode})"
                    )

    except KeyboardInterrupt:
        interrupted = True
        print(f"\n[!] Training interrupted at ep {last_ep + 1}. Saving checkpoint...")

    monitor.summary()
    monitor.save_checkpoint(os.path.join(args.save_dir, "monitor_checkpoint.json"))
    monitor.export_csv(os.path.join(args.save_dir, "monitor_data.csv"))

    if last_ep >= 0:
        # Note: final ctde critic uses bare "ctde_critic.pt" (no tag) for
        # historical compatibility with earlier rounds.
        _save_checkpoint(agents, coordinator, args.save_dir,
                         actor_tag="final", critic_filename="ctde_critic.pt")

        log = {
            "episode_rewards":   {str(i): episode_rewards[i] for i in range(N)},
            "total_rewards":     total_rewards,
            "total_steps":       total_steps,
            "episodes_completed": last_ep + 1,
            "episodes_planned":  args.episodes,
            "interrupted":       interrupted,
            "env_config":        dataclasses.asdict(env_config),
            "hparam_effective":  {
                "PHI_F":  env_config.phi_f,
                "PHI_H":  env_config.phi_h,
                "PHI_D":  env_config.phi_d,
                "VSG_M0": env_config.vsg_m0,
                "VSG_D0": env_config.vsg_d0,
                "DM_MIN": env_config.dm_min,
                "DM_MAX": env_config.dm_max,
                "DD_MIN": env_config.dd_min,
                "DD_MAX": env_config.dd_max,
            },
        }
        log_path = os.path.join(args.save_dir, "training_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, default=list)
        print(f"\nTraining log saved to {log_path}")
    else:
        print("\nNo episodes completed, nothing to save.")

    print(f"\nTotal time: {time.time() - t_start:.0f}s")

    # R78 — auto post-training dual-eval. Failures do NOT kill the run;
    # the ckpt + training log are already saved. The library function
    # owns the suffix-picker, score_seed call, summary persistence, and
    # error swallowing — train.py only does CLI plumbing (print).
    if last_ep >= 0 and args.final_eval:
        _emit_final_eval(args, env_config)

    print("Done!")


def _emit_final_eval(args: argparse.Namespace, env_config: V4Config) -> None:
    """CLI shim around ``evaluation.final_eval.run_final_eval``.

    The library function does the work + writes the sidecars; this
    wrapper handles the human-readable terminal output. R79 — extracted
    from the previous inline implementation so the contract (suffix
    pick + swallow-and-log failure) is unit-tested via DI.
    """
    from andes_rl_kundur.evaluation.final_eval import (
        pick_final_eval_suffix,
        run_final_eval,
    )
    from andes_rl_kundur.evaluation.summary import format_headline

    save_dir = Path(args.save_dir)
    eval_tracked = args.eval_every_n_eps > 0
    suffix = pick_final_eval_suffix(save_dir, eval_tracked=eval_tracked)
    if suffix is None:
        print("[final-eval] no ckpt found in save-dir; skipping.")
        return

    print("\n=== Final dual-eval (paper §IV-C cum_rf + 11-axis geo) ===")
    print(f"[final-eval] ckpt suffix = {suffix}")
    summary = run_final_eval(
        save_dir, env_config, eval_tracked=eval_tracked,
    )
    if summary is not None:
        label = f"final_eval_{save_dir.name}"
        print(f"[final-eval] {label}: {format_headline(summary)}")
        print(f"[final-eval] -> {save_dir / 'final_eval_summary.json'}")
    else:
        err_path = save_dir / "final_eval_error.txt"
        print(f"[final-eval] FAILED — see {err_path}")
        print("[final-eval] training ckpt is intact; re-run eval manually with score_run.py.")


if __name__ == "__main__":
    main()
