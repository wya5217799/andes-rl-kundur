"""R86 — Cross-ckpt replication of R84-D2 critic-monotone-Q pathology.

Extends ``r84_d2_q_landscape.py`` from a single R72_w4 SOTA ckpt to a
multi-ckpt sweep (SAC / TD3 / TD3-LSTM × multiple seeds) and adds an
explicit **monotone-Q fraction** statistic that R84 only inspected
visually via 8 subplots.

R83 (obs-space refactor training) holds the WSL ANDES lock; R85
(classical PI/Droop baseline) holds another ckpt-eval slot. R86 is pure
Windows-side Python forensics on read-only ``.pt`` files — no ANDES,
no env, no train.

Per ckpt × per agent × per (obs, action_dim) we measure:

1. Advantage A(s) = Q(s, a_sota) − mean_{a~U} Q(s, a)
2. argmax_dist = ||argmax_random_a Q − a_sota||_2
3. Q1/Q2 disagreement at a_sota
4. ||∇_a Q(s, a_sota)||_2 (autograd)
5. NEW: monotone fraction = fraction of (obs, dim) pairs where the
   1-D Q(s, action[d]) sweep along [-1, 1] has ≤ 1 sign change in
   its discrete derivative. R84-D2 inspected this visually only.

Algo fork: SAC / TD3 use non-recurrent critic ``critic(obs, action) →
(q1, q2)``; TD3-LSTM uses ``critic(obs, action, h) → (q1, q2, _)``.
Branched via ``agent.is_recurrent``.

Output: ``results/r86_qlandscape_multickpt/{summary.json,
per_ckpt_<name>.json, per_ckpt_<name>_sweep.png}``.
"""
from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Stub the ANDES module so the andes_rl_kundur package can finish loading
# on Windows host (mirrors r84_d2_q_landscape.py contract).
if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402

# --- Knobs (kept identical to R84-D2 for direct comparability) ----------

N_OBS_SAMPLES: int = 200
N_ACTION_SAMPLES: int = 100
N_GRID_PER_DIM: int = 51
OBS_PRIOR_STD: float = 1.0
ACTION_BOUND: float = 1.0
DEVICE = "cpu"
RNG_SEED_BASE = 86

# --- Ckpt registry ------------------------------------------------------

CKPT_SET: list[tuple[str, str]] = [
    # (dir_name, role_label)
    ("r72_w4_lstm_tau001_warmup5_s54",    "anchor_td3lstm_sota_s54"),
    ("r58_paper_strict_pure_td3_lstm_s49", "td3lstm_s49"),
    ("r58_paper_strict_pure_td3_lstm_s50", "td3lstm_s50"),
    ("r58_paper_strict_pure_td3_s49",      "td3_mlp_s49"),
    ("r58_paper_strict_pure_sac_s49",      "sac_mlp_s49"),
    ("r63_w4_td3_combo_s49",               "td3_mlp_r63_s49"),
]

OUT_DIR = ROOT / "results" / "r86_qlandscape_multickpt"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# --- Critic API adapter -------------------------------------------------

@dataclass(frozen=True)
class CriticResult:
    q1: torch.Tensor
    q2: torch.Tensor


def _critic_forward(agent, obs: torch.Tensor, action: torch.Tensor) -> CriticResult:
    """Unified critic call across SAC / TD3 / TD3-LSTM.

    Recurrent critics need an initial hidden state — use zeros (episode
    start) consistent with R84-D2 / eval inference convention.
    """
    if getattr(agent, "is_recurrent", False):
        h0 = agent.critic.init_hidden(obs.shape[0], DEVICE)
        q1, q2, _ = agent.critic(obs, action, h0)
    else:
        q1, q2 = agent.critic(obs, action)
    return CriticResult(q1=q1.squeeze(-1), q2=q2.squeeze(-1))


def _actor_forward(agent, obs: torch.Tensor) -> torch.Tensor:
    """Deterministic actor at episode-start hidden state. Returns (B, A)."""
    with torch.no_grad():
        if getattr(agent, "is_recurrent", False):
            h0 = agent.actor.init_hidden(obs.shape[0], DEVICE)
            a, _ = agent.actor(obs, h0)
        else:
            # SAC GaussianActor returns (mean_action, log_std) or similar
            # in non-deterministic mode. For SOTA-action proxy, use the
            # deterministic mean: SAC's `.act(obs, deterministic=True)`.
            if hasattr(agent, "act"):
                # agent.act expects np obs in eval; use the underlying
                # actor.forward → take the mean (first return) directly.
                out = agent.actor(obs)
            else:
                out = agent.actor(obs)
            # Convention across actors: first element is action / mean.
            if isinstance(out, tuple):
                a = out[0]
            else:
                a = out
    return a


def _sample_obs(n: int, obs_dim: int, rng: np.random.Generator) -> torch.Tensor:
    arr = rng.normal(0.0, OBS_PRIOR_STD, size=(n, obs_dim)).astype(np.float32)
    return torch.from_numpy(arr).to(DEVICE)


def _sample_actions(n: int, action_dim: int, rng: np.random.Generator) -> torch.Tensor:
    arr = rng.uniform(-ACTION_BOUND, ACTION_BOUND, size=(n, action_dim)).astype(np.float32)
    return torch.from_numpy(arr).to(DEVICE)


# --- Forensics measurements --------------------------------------------

def _advantage_pkg(agent, obs: torch.Tensor, rng: np.random.Generator) -> dict:
    a_sota = _actor_forward(agent, obs)
    res_sota = _critic_forward(agent, obs, a_sota)
    q_sota_mean = (res_sota.q1 + res_sota.q2) / 2

    B, A = a_sota.shape
    a_rand = _sample_actions(N_ACTION_SAMPLES * B, A, rng).view(N_ACTION_SAMPLES, B, A)
    q_rand_buf: list[torch.Tensor] = []
    best_q = torch.full((B,), -1e9, device=DEVICE)
    a_rand_argmax = torch.empty_like(a_sota)
    with torch.no_grad():
        for k in range(N_ACTION_SAMPLES):
            res_k = _critic_forward(agent, obs, a_rand[k])
            q_k = (res_k.q1 + res_k.q2) / 2
            q_rand_buf.append(q_k)
            mask = q_k > best_q
            best_q = torch.where(mask, q_k, best_q)
            a_rand_argmax = torch.where(mask.unsqueeze(-1), a_rand[k], a_rand_argmax)

    q_rand_mean = torch.stack(q_rand_buf, dim=0).mean(dim=0)
    advantage = q_sota_mean - q_rand_mean
    argmax_dist = torch.norm(a_rand_argmax - a_sota, dim=-1)
    q1q2_disagree = (res_sota.q1 - res_sota.q2).abs()

    return {
        "q_sota_mean": q_sota_mean.detach().cpu().numpy(),
        "q_rand_mean": q_rand_mean.detach().cpu().numpy(),
        "advantage":   advantage.detach().cpu().numpy(),
        "argmax_dist": argmax_dist.detach().cpu().numpy(),
        "q1q2_disagree": q1q2_disagree.detach().cpu().numpy(),
        "best_random_q": best_q.detach().cpu().numpy(),
    }


def _grad_norm(agent, obs: torch.Tensor) -> np.ndarray:
    a = _actor_forward(agent, obs).clone().requires_grad_(True)
    res = _critic_forward(agent, obs, a)
    q_mean = (res.q1 + res.q2) / 2
    grad = torch.autograd.grad(q_mean.sum(), a, retain_graph=False)[0]
    return grad.detach().norm(dim=-1).cpu().numpy()


def _monotone_fraction_and_sweep(agent, obs: torch.Tensor) -> tuple[float, np.ndarray]:
    """Monotone-fraction along each action dim + raw sweep for viz.

    For each (obs, action_dim), sweep action[d] over N_GRID_PER_DIM points
    in [-1, 1] (hold the other dim at a_sota[d']). Discrete derivative
    has N_GRID_PER_DIM - 1 entries; count sign changes. ``monotone`` is
    defined as ≤ 1 sign change (allows numerical noise at one boundary).

    Returns (monotone_fraction, sweep_array of shape (B, A, N_GRID_PER_DIM)).
    Aggregate B × A curves into one scalar.
    """
    B, _ = obs.shape
    a_sota = _actor_forward(agent, obs)
    A = a_sota.shape[1]
    grid = torch.linspace(-ACTION_BOUND, ACTION_BOUND, N_GRID_PER_DIM, device=DEVICE)

    sweep = np.zeros((B, A, N_GRID_PER_DIM), dtype=np.float32)
    monotone_count = 0
    total = 0

    with torch.no_grad():
        for d in range(A):
            for gi, g in enumerate(grid):
                a_probe = a_sota.clone()
                a_probe[:, d] = g
                res = _critic_forward(agent, obs, a_probe)
                q = (res.q1 + res.q2) / 2
                sweep[:, d, gi] = q.detach().cpu().numpy()
            # For each obs, check sign changes of dQ/d action[d]
            for b in range(B):
                curve = sweep[b, d]
                diffs = np.diff(curve)
                signs = np.sign(diffs)
                # Treat 0 (rare) as same as previous sign
                # Count actual sign changes
                nonzero = signs[signs != 0]
                if len(nonzero) <= 1:
                    sign_changes = 0
                else:
                    sign_changes = int(np.sum(nonzero[1:] != nonzero[:-1]))
                if sign_changes <= 1:
                    monotone_count += 1
                total += 1
    return monotone_count / max(total, 1), sweep


def _agent_record(ckpt_label: str, agent_idx: int, agent, rng: np.random.Generator) -> dict:
    obs = _sample_obs(N_OBS_SAMPLES, agent.obs_dim, rng)
    adv = _advantage_pkg(agent, obs, rng)
    grads = _grad_norm(agent, obs)
    monotone_frac, sweep = _monotone_fraction_and_sweep(
        agent, obs[:8]  # 8 obs is enough for the action-axis viz subplots
    )
    return {
        "ckpt": ckpt_label,
        "agent_idx": agent_idx,
        "obs_dim": agent.obs_dim,
        "action_dim": agent.action_dim,
        "is_recurrent": bool(getattr(agent, "is_recurrent", False)),
        "advantage_median": float(np.median(adv["advantage"])),
        "advantage_positive_frac": float((adv["advantage"] > 0).mean()),
        "argmax_dist_median": float(np.median(adv["argmax_dist"])),
        "q1q2_disagreement_median": float(np.median(adv["q1q2_disagree"])),
        "grad_norm_median": float(np.median(grads)),
        "q_sota_mean_abs_median": float(np.median(np.abs(adv["q_sota_mean"]))),
        "best_random_minus_sota_median": float(
            np.median(adv["best_random_q"] - adv["q_sota_mean"])
        ),
        "monotone_fraction": float(monotone_frac),  # over 8 obs × A dims
        "_sweep_array": sweep,  # kept in-memory for viz; not serialised
    }


# --- Per-ckpt aggregate -------------------------------------------------

def _ckpt_aggregate(ckpt_label: str, records: list[dict]) -> dict:
    """Aggregate over the 4 agents of one ckpt."""
    keys = [
        "advantage_median", "advantage_positive_frac", "argmax_dist_median",
        "q1q2_disagreement_median", "grad_norm_median",
        "q_sota_mean_abs_median", "best_random_minus_sota_median",
        "monotone_fraction",
    ]
    agg = {k: float(np.median([r[k] for r in records])) for k in keys}
    agg["ckpt"] = ckpt_label
    agg["n_agents"] = len(records)

    q_mag = agg["q_sota_mean_abs_median"]
    eps_grad = 0.01 * q_mag if q_mag > 0 else 1e-6
    healthy_critic = (
        agg["advantage_median"] > 0
        and agg["argmax_dist_median"] < 0.5
        and agg["grad_norm_median"] > eps_grad
        and agg["monotone_fraction"] < 0.5
    )
    agg["healthy_critic"] = bool(healthy_critic)
    agg["q_magnitude_ref"] = q_mag
    return agg


# --- Visualisation ------------------------------------------------------

def _save_sweep_viz(ckpt_label: str, records: list[dict], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_agents = len(records)
    A = records[0]["action_dim"]
    fig, axes = plt.subplots(n_agents, A, figsize=(4.0 * A, 2.5 * n_agents), squeeze=False)
    grid = np.linspace(-ACTION_BOUND, ACTION_BOUND, N_GRID_PER_DIM)
    for i, rec in enumerate(records):
        sweep = rec["_sweep_array"]  # (8, A, N_GRID_PER_DIM)
        for d in range(A):
            ax = axes[i, d]
            for b in range(sweep.shape[0]):
                ax.plot(grid, sweep[b, d], alpha=0.55, linewidth=1.0)
            ax.axhline(0.0, color="grey", linewidth=0.5)
            ax.set_title(f"{ckpt_label} agent{i} dim{d}", fontsize=8)
            ax.set_xlabel("action[d]")
            ax.set_ylabel("Q(s, a)")
            ax.grid(True, alpha=0.3)
    fig.suptitle(
        f"R86 Q-action sweep — {ckpt_label} (8 obs / agent, hold other dim at a_sota)",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# --- Main ---------------------------------------------------------------

def main() -> None:
    print(f"R86: ckpt set = {len(CKPT_SET)} entries")
    per_ckpt_summary: list[dict] = []
    per_agent_dump: list[dict] = []

    for ckpt_dir, ckpt_label in CKPT_SET:
        ckpt_path = ROOT / "results" / ckpt_dir
        if not ckpt_path.exists():
            print(f"  SKIP missing: {ckpt_dir}")
            continue
        print(f"\n=== {ckpt_label} ({ckpt_dir}) ===")
        agents = load_agents(ckpt_path, suffix="best")
        rng = np.random.default_rng(RNG_SEED_BASE + hash(ckpt_label) % 100)
        records = [_agent_record(ckpt_label, i, a, rng) for i, a in enumerate(agents)]

        # Save viz before stripping the in-memory sweep array
        viz_path = OUT_DIR / f"per_ckpt_{ckpt_label}_sweep.png"
        _save_sweep_viz(ckpt_label, records, viz_path)
        print(f"  viz → {viz_path}")

        # Strip the in-memory sweep arrays before JSON serialisation
        records_clean = [{k: v for k, v in r.items() if k != "_sweep_array"} for r in records]
        per_agent_dump.extend(records_clean)

        agg = _ckpt_aggregate(ckpt_label, records_clean)
        per_ckpt_summary.append(agg)
        print(f"  advantage_median={agg['advantage_median']:+.4f}  "
              f"argmax_dist_median={agg['argmax_dist_median']:.3f}  "
              f"q1q2_disagree={agg['q1q2_disagreement_median']:.4f}  "
              f"grad_norm={agg['grad_norm_median']:.4f}  "
              f"monotone={agg['monotone_fraction']:.2f}  "
              f"healthy_critic={agg['healthy_critic']}")

    # Cross-ckpt aggregate
    if per_ckpt_summary:
        n_total = len(per_ckpt_summary)
        n_healthy = sum(1 for a in per_ckpt_summary if a["healthy_critic"])
        n_monotone_heavy = sum(1 for a in per_ckpt_summary if a["monotone_fraction"] >= 0.5)
        n_argmax_boundary = sum(1 for a in per_ckpt_summary if a["argmax_dist_median"] >= 0.5)
        cross = {
            "n_ckpts": n_total,
            "n_healthy_critics": n_healthy,
            "n_monotone_heavy_ckpts": n_monotone_heavy,
            "n_argmax_boundary_ckpts": n_argmax_boundary,
            "median_advantage_across_ckpts": float(
                np.median([a["advantage_median"] for a in per_ckpt_summary])
            ),
            "median_argmax_dist_across_ckpts": float(
                np.median([a["argmax_dist_median"] for a in per_ckpt_summary])
            ),
            "median_monotone_fraction_across_ckpts": float(
                np.median([a["monotone_fraction"] for a in per_ckpt_summary])
            ),
        }
    else:
        cross = {"error": "no ckpts loaded"}

    summary = {
        "round": "R86",
        "kind": "cross_ckpt_q_landscape",
        "ckpt_set_size": len(CKPT_SET),
        "n_obs_samples": N_OBS_SAMPLES,
        "n_action_samples": N_ACTION_SAMPLES,
        "n_grid_per_dim": N_GRID_PER_DIM,
        "per_ckpt": per_ckpt_summary,
        "cross_ckpt": cross,
        "interpretation": _interpret(cross),
        "synthetic_obs_caveat": (
            "Obs sampled from N(0, I) prior, NOT ANDES trajectory. Critic "
            "monotone-in-action on prior obs ⇒ critic is monotone on a "
            "large region of obs space (synthetic obs is a stress test of "
            "the function shape, not the manifold). ANDES-trajectory replay "
            "still pending (Q-0018 from R84)."
        ),
    }

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    (OUT_DIR / "per_agent.json").write_text(json.dumps(per_agent_dump, indent=2))
    print("\n--- R86 cross-ckpt aggregate ---")
    print(json.dumps(cross, indent=2))
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")


def _interpret(cross: dict) -> str:
    if "error" in cross:
        return cross["error"]
    n = cross["n_ckpts"]
    n_monotone = cross["n_monotone_heavy_ckpts"]
    n_boundary = cross["n_argmax_boundary_ckpts"]
    if n_monotone >= n - 1 and n_boundary >= n - 1:
        return (
            f"UNIVERSAL pathology — {n_monotone}/{n} ckpts have monotone-heavy "
            f"Q (fraction ≥ 0.5) AND {n_boundary}/{n} have argmax on boundary. "
            f"R84 mechanism (CLM-0148/0149) replicates across SAC / TD3 / "
            f"TD3-LSTM × multiple seeds. R87 should change critic representation."
        )
    if n_monotone == 0 and n_boundary == 0:
        return (
            f"R84 NOT replicated — 0/{n} ckpts show monotone-Q or boundary-"
            f"argmax. R72_w4 SOTA is a single-ckpt outlier; mechanism layer "
            f"search restarts."
        )
    return (
        f"PARTIAL replication — {n_monotone}/{n} monotone-heavy, "
        f"{n_boundary}/{n} boundary-argmax. R84 mechanism is algo- or seed-"
        f"specific; need to identify which ckpts share the pathology and why."
    )


if __name__ == "__main__":
    main()
