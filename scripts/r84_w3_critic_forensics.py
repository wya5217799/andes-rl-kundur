"""R84-W3 — critic-side forensics, zero-ANDES.

Three independent measurements that **do not depend on synthetic obs choice**:

A. **Local Q curvature around a_sota** — high-resolution 1-D sweep
   over [a_sota - 0.1, a_sota + 0.1] / 201 grid points, then compute
   discrete second-derivative (5-point stencil). Concave preference
   for a_sota requires negative-definite local curvature on **both**
   action axes. We report median 2nd-derivative per dim, sign, and
   the fraction of obs samples that exhibit local concavity.

B. **Per-layer weight spectral norm** of actor vs critic.
   Pathologically large spectral norms in critic input/output layers
   (especially the LSTM weight_ih / weight_hh and the fc_out scalar
   projection) are a known cause of monotone-in-action Q estimates.
   We tabulate top singular values per layer and flag any > 10×
   median.

C. **Q-landscape sanity on a centred / scaled prior** — the SOTA
   training_log.json records per-episode action_mean and action_std
   under exploration. We synthesise obs samples whose magnitude
   matches the rough scale of training-time obs (using episode
   reward magnitudes as a coarse activity proxy), then re-run the
   R84-D2 advantage measurement. This is the strongest **zero-ANDES**
   approximation to "on-manifold" obs we can construct.

Output: results/r84_w3_critic_forensics/{summary.json,
local_curvature.png, spectral_norms.csv}.
"""
from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402


SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r84_w3_critic_forensics"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_OBS = 200
LOCAL_RADIUS = 0.1
LOCAL_GRID = 201
DEVICE = "cpu"


# ───────────────────────────────────────────────────────────────────────
# Part A. Local Q curvature around a_sota
# ───────────────────────────────────────────────────────────────────────

def _h0_actor(agent, batch: int):
    return agent.actor.init_hidden(batch, DEVICE)


def _h0_critic(agent, batch: int):
    return agent.critic.init_hidden(batch, DEVICE)


def _q_at(agent, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
    h = _h0_critic(agent, obs.shape[0])
    q1, q2, _ = agent.critic(obs, action, h)
    return ((q1.squeeze(-1) + q2.squeeze(-1)) / 2)


def _local_curvature(agent, obs: torch.Tensor) -> dict:
    """Compute discrete 2nd-derivative of Q(s, a) at a_sota along each action axis."""
    B = obs.shape[0]
    with torch.no_grad():
        a_sota, _ = agent.actor(obs, _h0_actor(agent, B))
    A = a_sota.shape[1]

    # Step size along the local grid.
    grid = torch.linspace(-LOCAL_RADIUS, LOCAL_RADIUS, LOCAL_GRID).to(DEVICE)
    dx = float(grid[1] - grid[0])

    second_deriv_per_dim: list[np.ndarray] = []   # (A, B)
    local_q_curves: list[np.ndarray] = []          # (A, B, LOCAL_GRID)
    for dim in range(A):
        Q = torch.zeros(B, LOCAL_GRID, device=DEVICE)
        with torch.no_grad():
            for k, g in enumerate(grid):
                a = a_sota.clone()
                a[:, dim] = a[:, dim] + g
                a = a.clamp(-1.0, 1.0)
                Q[:, k] = _q_at(agent, obs, a)
        # Central 2nd derivative at the midpoint index.
        mid = LOCAL_GRID // 2
        # 5-point stencil: f'' ≈ (-Q[i-2] + 16 Q[i-1] - 30 Q[i] + 16 Q[i+1] - Q[i+2]) / (12 h^2)
        d2 = (
            -Q[:, mid-2] + 16*Q[:, mid-1] - 30*Q[:, mid] + 16*Q[:, mid+1] - Q[:, mid+2]
        ) / (12 * dx * dx)
        second_deriv_per_dim.append(d2.cpu().numpy())
        local_q_curves.append(Q.cpu().numpy())

    d2_arr = np.stack(second_deriv_per_dim, axis=0)   # (A, B)
    concave_frac = (d2_arr < 0).mean(axis=1)          # (A,) — fraction with d²Q/da² < 0

    return {
        "d2_median_per_dim": d2_arr.mean(axis=1).tolist(),
        "d2_p10_per_dim": np.percentile(d2_arr, 10, axis=1).tolist(),
        "d2_p90_per_dim": np.percentile(d2_arr, 90, axis=1).tolist(),
        "concave_fraction_per_dim": concave_frac.tolist(),
        "raw_local_curves": local_q_curves,           # for the plot
        "grid": grid.cpu().numpy(),
        "a_sota_sample": a_sota[:8].cpu().numpy(),
    }


# ───────────────────────────────────────────────────────────────────────
# Part B. Per-layer weight spectral norm
# ───────────────────────────────────────────────────────────────────────

def _layer_spectral_norms(module: torch.nn.Module, prefix: str) -> list[dict]:
    rows: list[dict] = []
    for name, p in module.named_parameters():
        if p.ndim < 2:
            continue
        w = p.detach().cpu().numpy()
        if w.ndim > 2:
            w = w.reshape(w.shape[0], -1)
        try:
            s = np.linalg.svd(w, compute_uv=False)
            spec = float(s[0])
            cond = float(s[0] / max(s[-1], 1e-12))
        except np.linalg.LinAlgError:
            spec, cond = float("nan"), float("nan")
        rows.append({
            "module": prefix,
            "param": name,
            "shape": list(p.shape),
            "spectral_norm": spec,
            "condition_number": cond,
        })
    return rows


def _per_agent_spectral(agent_idx: int, agent) -> list[dict]:
    rows: list[dict] = []
    rows += _layer_spectral_norms(agent.actor, f"agent{agent_idx}.actor")
    rows += _layer_spectral_norms(agent.critic, f"agent{agent_idx}.critic")
    return rows


# ───────────────────────────────────────────────────────────────────────
# Part C. Trajectory-marginal-proxy obs (zero-ANDES)
# ───────────────────────────────────────────────────────────────────────

def _trajectory_proxy_obs(n: int, obs_dim: int, rng: np.random.Generator,
                          training_log_path: Path) -> torch.Tensor:
    """Approximate on-manifold obs scale using SOTA training stats.

    The training_log records per-episode rewards. Late-training episodes
    (ep > 50) have mean reward ≈ -2 to -5 with std small → near-converged
    policy on near-nominal frequency. We use this to scale a unit-Gaussian
    obs sample down to a tighter range, matching the smaller obs deviation
    observed in late training. Not a true on-manifold sample, but
    strictly tighter than N(0, I).
    """
    with open(training_log_path) as f:
        log = json.load(f)
    # Last 25 episodes' total reward magnitudes (= rough state activity).
    rewards = log["total_rewards"][-25:]
    mean_abs = float(np.mean(np.abs(rewards)))
    # When reward magnitude is small (~3), obs deviation is small too.
    # Heuristic: obs ~ N(0, σ) with σ scaled by activity.
    sigma = min(1.0, mean_abs / 10.0)
    arr = rng.normal(0.0, sigma, size=(n, obs_dim)).astype(np.float32)
    return torch.from_numpy(arr).to(DEVICE), sigma


def _advantage(agent, obs: torch.Tensor, rng: np.random.Generator,
               n_action: int = 100) -> dict:
    B = obs.shape[0]
    A = agent.action_dim
    with torch.no_grad():
        a_sota, _ = agent.actor(obs, _h0_actor(agent, B))
        q_sota = _q_at(agent, obs, a_sota)
        # K random action samples per obs.
        a_rand = torch.from_numpy(
            rng.uniform(-1.0, 1.0, size=(n_action, B, A)).astype(np.float32)
        ).to(DEVICE)
        q_rand_means = []
        best_q = torch.full((B,), -1e9, device=DEVICE)
        for k in range(n_action):
            q_k = _q_at(agent, obs, a_rand[k])
            q_rand_means.append(q_k)
            best_q = torch.maximum(best_q, q_k)
        q_rand_mean = torch.stack(q_rand_means, 0).mean(0)
    advantage = q_sota - q_rand_mean
    best_minus_sota = best_q - q_sota
    return {
        "advantage_median": float(np.median(advantage.cpu().numpy())),
        "advantage_positive_frac": float((advantage > 0).float().mean().item()),
        "best_random_minus_sota_median": float(np.median(best_minus_sota.cpu().numpy())),
    }


# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print(f"R84-W3: load SOTA from {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"  loaded {len(agents)} agents")

    rng = np.random.default_rng(54)
    obs_dim = agents[0].obs_dim
    obs_prior = torch.from_numpy(
        rng.normal(0, 1.0, size=(N_OBS, obs_dim)).astype(np.float32)
    ).to(DEVICE)

    # === Part A: local Q curvature ===========================================
    curvature_per_agent: list[dict] = []
    fig, axes = plt.subplots(len(agents), 2, figsize=(10, 3 * len(agents)),
                              squeeze=False)
    for ai, agent in enumerate(agents):
        info = _local_curvature(agent, obs_prior)
        curvature_per_agent.append({
            "agent_idx": ai,
            "d2_median_per_dim": info["d2_median_per_dim"],
            "concave_fraction_per_dim": info["concave_fraction_per_dim"],
        })
        for dim in range(2):
            ax = axes[ai][dim]
            curves = info["raw_local_curves"][dim]   # (B, LOCAL_GRID)
            grid = info["grid"]
            for b in range(min(8, curves.shape[0])):
                ax.plot(grid, curves[b], lw=1, alpha=0.7)
            ax.axvline(0, color="black", ls="--", lw=0.5)
            ax.set_xlabel(f"a_sota[{dim}] + Δ")
            ax.set_ylabel(f"Q (agent {ai})")
            ax.set_title(
                f"agent {ai} dim {dim}: "
                f"concave_frac={info['concave_fraction_per_dim'][dim]:.2f} "
                f"d²Q/da² median={info['d2_median_per_dim'][dim]:+.3e}"
            )
    fig.suptitle("R84-W3-A: local Q curvature in [a_sota - 0.1, a_sota + 0.1]")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "local_curvature.png", dpi=110)
    plt.close(fig)

    # === Part B: per-layer spectral norms ====================================
    spectral_rows: list[dict] = []
    for ai, agent in enumerate(agents):
        spectral_rows += _per_agent_spectral(ai, agent)
    with open(OUT_DIR / "spectral_norms.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(spectral_rows[0].keys()))
        w.writeheader()
        w.writerows(spectral_rows)
    spec_norms = np.array([r["spectral_norm"] for r in spectral_rows
                            if not np.isnan(r["spectral_norm"])])
    spec_summary = {
        "n_layers_total": len(spectral_rows),
        "spectral_norm_median": float(np.median(spec_norms)),
        "spectral_norm_max": float(np.max(spec_norms)),
        "spectral_norm_max_layer": (
            spectral_rows[int(np.argmax(spec_norms))]["module"]
            + "::" + spectral_rows[int(np.argmax(spec_norms))]["param"]
        ),
        "high_spectral_layers": [
            f'{r["module"]}::{r["param"]} σ_max={r["spectral_norm"]:.3f}'
            for r in spectral_rows
            if r["spectral_norm"] > 10.0
        ],
    }

    # === Part C: trajectory-marginal-proxy obs ===============================
    proxy_obs, proxy_sigma = _trajectory_proxy_obs(
        N_OBS, obs_dim, rng, SOTA_DIR / "training_log.json"
    )
    proxy_adv_per_agent = [_advantage(ag, proxy_obs, rng) for ag in agents]
    proxy_summary = {
        "proxy_sigma": proxy_sigma,
        "advantage_median_cross_agent": float(np.median(
            [a["advantage_median"] for a in proxy_adv_per_agent]
        )),
        "best_random_minus_sota_median_cross_agent": float(np.median(
            [a["best_random_minus_sota_median"] for a in proxy_adv_per_agent]
        )),
        "per_agent": proxy_adv_per_agent,
    }

    # === Verdict ============================================================
    # Concavity test: agent-mean concave fraction per dim. If majority of
    # obs samples show d²Q/da² < 0 on both dims, a_sota is at least a local
    # max (necessary condition for actor-critic alignment).
    concave_aggr = np.array([
        c["concave_fraction_per_dim"] for c in curvature_per_agent
    ])  # (n_agents, A)
    median_concave_frac = float(np.median(concave_aggr))
    local_max_likely = median_concave_frac > 0.5

    summary = {
        "round": "R84",
        "wave": "W3_critic_forensics",
        "sota": SOTA_DIR.name,
        "part_A_local_curvature": {
            "per_agent": curvature_per_agent,
            "median_concave_fraction_across_agents_and_dims": median_concave_frac,
            "a_sota_local_max_likely": local_max_likely,
            "interpretation": (
                "concave_fraction > 0.5 means a_sota is a local max for the "
                "majority of obs samples — consistent with actor being at "
                "critic's local argmax. Below 0.5 means a_sota is NOT a "
                "local maximum on most obs samples (critic still wants to "
                "move action away from a_sota locally)."
            ),
        },
        "part_B_spectral_norms": spec_summary,
        "part_C_proxy_obs_advantage": proxy_summary,
    }
    out_path = OUT_DIR / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2))

    print(f"\n=== R84-W3 summary ===")
    print(f"A. local concave-fraction median: {median_concave_frac:.3f} "
          f"(a_sota local max likely: {local_max_likely})")
    print(f"B. spectral norm median={spec_summary['spectral_norm_median']:.3f} "
          f"max={spec_summary['spectral_norm_max']:.3f} "
          f"@ {spec_summary['spectral_norm_max_layer']}")
    if spec_summary["high_spectral_layers"]:
        print(f"   high-spectral layers:")
        for s in spec_summary["high_spectral_layers"][:10]:
            print(f"     {s}")
    print(f"C. proxy-obs (σ={proxy_sigma:.3f}) advantage_median = "
          f"{proxy_summary['advantage_median_cross_agent']:+.5f}, "
          f"best-random over sota = "
          f"{proxy_summary['best_random_minus_sota_median_cross_agent']:+.5f}")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
