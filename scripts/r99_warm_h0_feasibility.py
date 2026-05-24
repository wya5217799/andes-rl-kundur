"""R99 — Architectural feasibility test for Q-0022 (LSTM warm-h_0 initialiser).

CLM-0174 (R95) found the R72_w4 SOTA actor outputs ||a||_step0 ≈ 0.149
(10% of max) because the LSTM hidden state starts at (h, c) = (0, 0).
Q-0022 proposes: learn `h_0 = MLP(obs_0)` so the LSTM starts in a
non-zero state and step-0 output can reach saturation immediately.

This script tests **the architectural premise** without training:
given the FROZEN R72_w4 actor + critic weights, does there EXIST an
h_0 (and c_0) such that step-0 actor output reaches saturation AND
the critic Q is higher than at h_0 = 0?

If YES (large slack): Q-0022 has architectural feasibility. The
question becomes whether a learned MLP can find such h_0 from obs.

If NO (h has no effect on step-0 action OR no h gives higher Q):
Q-0022 is architecturally limited. The LSTM weights themselves
constrain step-0 outputs in a way no h_0 can unlock.

Method: for each step-0-like obs:
1. Forward actor with h=0  →  a_0, record Q(s, a_0)
2. Gradient-ascent over h (h_dim=64) initial state for 200 steps to
   maximize Q(s, actor(s, h_0)) — h_0 is the variable.
3. Compare ||a_0(h=0)|| vs ||a_0(h=h*)||  and  Q(h=0) vs Q(h*)

Zero ANDES. Zero WSL. Read-only ckpt. Pure offline architectural test.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Same ANDES stub trick as R86 / R84
if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402

SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r99_warm_h0_feasibility"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Knobs
N_OBS_SAMPLES = 100     # step-0-like obs synthetic samples
OBS_NORM_TARGET = 0.25  # CLM-0161: median obs_norm at step 0 ≈ 0.25
OBS_DIM = 7
N_ASCENT_STEPS = 500    # gradient ascent over h_0
LR_H = 0.05
DEVICE = "cpu"
RNG_SEED = 99


def _sample_step0_obs(n: int, rng: np.random.Generator) -> torch.Tensor:
    """Sample obs with ||obs||_2 ≈ OBS_NORM_TARGET (small, transient-like)."""
    raw = rng.normal(0, 1, size=(n, OBS_DIM)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    raw = raw / np.maximum(norms, 1e-8) * OBS_NORM_TARGET
    return torch.from_numpy(raw).to(DEVICE)


def _actor_forward(agent, obs: torch.Tensor, h: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
    """Recurrent actor forward at given (h, c). Returns action tanh."""
    a, _ = agent.actor(obs, (h, c))
    return a


def _critic_q(agent, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
    """min(Q1, Q2) at given (s, a) with critic h_critic = 0 (episode start convention)."""
    h0_critic = agent.critic.init_hidden(obs.shape[0], DEVICE)
    q1, q2, _ = agent.critic(obs, action, h0_critic)
    # TD3 target: min(Q1, Q2) — what training maximizes
    q = torch.min(q1.squeeze(-1), q2.squeeze(-1))
    return q


def _h0_optimize(agent, obs: torch.Tensor) -> dict:
    """Per-obs gradient ascent over (h_0, c_0) to maximise critic Q."""
    B = obs.shape[0]
    hidden = agent.actor.hidden

    # Baseline: h=0, c=0
    with torch.no_grad():
        h_zero = torch.zeros(B, hidden, device=DEVICE)
        c_zero = torch.zeros(B, hidden, device=DEVICE)
        a_zero = _actor_forward(agent, obs, h_zero, c_zero)
        q_zero = _critic_q(agent, obs, a_zero)
        norm_zero = a_zero.norm(dim=-1)

    # Optimisable h_0, c_0 (start at zero so we measure the lift, not blind h init)
    h = torch.zeros(B, hidden, device=DEVICE, requires_grad=True)
    c = torch.zeros(B, hidden, device=DEVICE, requires_grad=True)
    opt = torch.optim.Adam([h, c], lr=LR_H)
    for _ in range(N_ASCENT_STEPS):
        opt.zero_grad()
        a = _actor_forward(agent, obs, h, c)
        q = _critic_q(agent, obs, a)
        loss = -q.sum()
        loss.backward()
        opt.step()

    with torch.no_grad():
        a_star = _actor_forward(agent, obs, h, c)
        q_star = _critic_q(agent, obs, a_star)
        norm_star = a_star.norm(dim=-1)
        h_norm_star = h.norm(dim=-1)
        c_norm_star = c.norm(dim=-1)

    # Aggregate to median for robustness to outliers
    return {
        "n_obs": int(B),
        "q_zero_median":   float(np.median(q_zero.cpu().numpy())),
        "q_star_median":   float(np.median(q_star.cpu().numpy())),
        "q_gain_median":   float(np.median((q_star - q_zero).cpu().numpy())),
        "q_gain_pct_of_q0_median": float(
            np.median(((q_star - q_zero) / (q_zero.abs() + 1e-6)).cpu().numpy()) * 100
        ),
        "norm_zero_median": float(np.median(norm_zero.cpu().numpy())),
        "norm_star_median": float(np.median(norm_star.cpu().numpy())),
        "norm_zero_max_pct": float(np.median(norm_zero.cpu().numpy()) / np.sqrt(2) * 100),
        "norm_star_max_pct": float(np.median(norm_star.cpu().numpy()) / np.sqrt(2) * 100),
        "h_norm_star_median": float(np.median(h_norm_star.cpu().numpy())),
        "c_norm_star_median": float(np.median(c_norm_star.cpu().numpy())),
    }


def main() -> None:
    print(f"R99: load SOTA from {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    rng = np.random.default_rng(RNG_SEED)
    obs = _sample_step0_obs(N_OBS_SAMPLES, rng)
    print(f"  {N_OBS_SAMPLES} synthetic step-0-like obs (||obs||={OBS_NORM_TARGET})")

    per_agent: list[dict] = []
    for i, ag in enumerate(agents):
        print(f"\n--- agent {i} ---")
        res = _h0_optimize(ag, obs)
        res["agent"] = i
        per_agent.append(res)
        print(f"  Q: {res['q_zero_median']:+.4f} → {res['q_star_median']:+.4f}  "
              f"(gain {res['q_gain_median']:+.4f} = {res['q_gain_pct_of_q0_median']:+.1f}%)")
        print(f"  ||a||: {res['norm_zero_median']:.3f} ({res['norm_zero_max_pct']:.1f}% of max) "
              f"→ {res['norm_star_median']:.3f} ({res['norm_star_max_pct']:.1f}% of max)")
        print(f"  ||h*||={res['h_norm_star_median']:.2f}, ||c*||={res['c_norm_star_median']:.2f}")

    agg = {
        "n_agents": len(per_agent),
        "n_obs_per_agent": N_OBS_SAMPLES,
        "obs_norm_target": OBS_NORM_TARGET,
        "q_gain_median_across_agents": float(
            np.median([a["q_gain_median"] for a in per_agent])
        ),
        "q_gain_pct_median_across_agents": float(
            np.median([a["q_gain_pct_of_q0_median"] for a in per_agent])
        ),
        "norm_zero_median_across_agents": float(
            np.median([a["norm_zero_median"] for a in per_agent])
        ),
        "norm_star_median_across_agents": float(
            np.median([a["norm_star_median"] for a in per_agent])
        ),
        "norm_star_pct_of_max_median": float(
            np.median([a["norm_star_max_pct"] for a in per_agent])
        ),
        "norm_zero_pct_of_max_median": float(
            np.median([a["norm_zero_max_pct"] for a in per_agent])
        ),
    }

    # Feasibility gate
    norm_lift = agg["norm_star_pct_of_max_median"] - agg["norm_zero_pct_of_max_median"]
    q_lift_pct = agg["q_gain_pct_median_across_agents"]
    feasibility = (
        "FEASIBLE — warm-h_0 unlocks ≥ 50% additional action magnitude AND Q lift > 20%"
        if norm_lift > 50 and q_lift_pct > 20
        else "PARTIAL — measurable lift but below feasibility gate"
        if norm_lift > 10 or q_lift_pct > 5
        else "INFEASIBLE — h_0 has no actionable effect on step-0 output"
    )

    summary = {
        "round": "R99",
        "kind": "warm_h0_feasibility",
        "sota": SOTA_DIR.name,
        "per_agent": per_agent,
        "agg": agg,
        "norm_lift_pct_pts": norm_lift,
        "q_lift_pct": q_lift_pct,
        "feasibility": feasibility,
        "interpretation": (
            "Test: does there exist (h_0, c_0) such that the FROZEN R72_w4 "
            "actor outputs near-saturation action AND the critic prefers it "
            "over the h=0 output? If yes, Q-0022 (learning h_0 = MLP(obs_0)) "
            "has architectural slack. If no, LSTM weights constrain step-0 "
            "irrespective of any h_0 initialiser."
        ),
        "synthetic_caveat": (
            "Obs ~ random direction × ||obs||=0.25. Real step-0 obs is a "
            "specific direction in the 7-D space (loaded from cached ANDES "
            "trace). Synthetic obs averages over direction; per-direction "
            "feasibility may be tighter."
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print("\n=== R99 aggregate ===")
    print(json.dumps(agg, indent=2))
    print(f"\nFeasibility: {feasibility}")
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
