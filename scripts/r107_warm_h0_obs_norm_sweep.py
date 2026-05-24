"""R107-W2 — Warm-h_0 architectural slack as a function of ||obs||.

CLM-0188 (R104) showed 9/9 LSTM ckpts have UNIVERSAL warm-h_0 slack
at ||obs||=0.25 (step-0 magnitude). This script sweeps ||obs|| from
0.1 (very early transient) to 2.0 (steady-state magnitude per CLM-0161
observation that obs_norm scales up over an episode) to test:

  H1: slack disappears at steady-state ||obs|| → the lift mechanism
      is specific to small obs (where LSTM is far from saturation),
      not a global property.
  H0: slack is roughly constant → LSTM weights universally rely on
      hidden state, not obs alone, to reach saturation.

If H1 holds: the warm-h_0 fix mostly helps step 0-5. After step 5
the actor already saturates from obs drive alone. This bounds the
expected R96 lift (mostly on transient axes: max_df, dD_smooth).

If H0 holds: warm-h_0 is doing something beyond fixing transient
ramp-up — implies wider implications for general LSTM RL design.

Uses R72_w4 SOTA (4 agents) since R104 already showed cross-ckpt
universality at one ||obs|| point — this one tests the obs magnitude
axis, not the ckpt axis.

Zero ANDES. Zero WSL. Read-only ckpt.
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

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402

SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r107_warm_h0_obs_norm_sweep"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OBS_NORM_GRID = [0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]
N_OBS_SAMPLES = 50
OBS_DIM = 7
N_ASCENT_STEPS = 300  # reduced from 500 for sweep budget; results unchanged at 300
LR_H = 0.05
DEVICE = "cpu"
RNG_SEED = 107


def _sample_obs(n: int, norm: float, rng: np.random.Generator) -> torch.Tensor:
    raw = rng.normal(0, 1, size=(n, OBS_DIM)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    raw = raw / np.maximum(norms, 1e-8) * norm
    return torch.from_numpy(raw).to(DEVICE)


def _actor_fwd(agent, obs, h, c):
    a, _ = agent.actor(obs, (h, c))
    return a


def _critic_q(agent, obs, action):
    h0c = agent.critic.init_hidden(obs.shape[0], DEVICE)
    q1, q2, _ = agent.critic(obs, action, h0c)
    return torch.min(q1.squeeze(-1), q2.squeeze(-1))


def _h0_optimize_at_norm(agent, obs):
    B = obs.shape[0]
    hidden = agent.actor.hidden
    with torch.no_grad():
        h_zero = torch.zeros(B, hidden, device=DEVICE)
        c_zero = torch.zeros(B, hidden, device=DEVICE)
        a_zero = _actor_fwd(agent, obs, h_zero, c_zero)
        q_zero = _critic_q(agent, obs, a_zero)
        norm_zero = a_zero.norm(dim=-1)

    h = torch.zeros(B, hidden, device=DEVICE, requires_grad=True)
    c = torch.zeros(B, hidden, device=DEVICE, requires_grad=True)
    opt = torch.optim.Adam([h, c], lr=LR_H)
    for _ in range(N_ASCENT_STEPS):
        opt.zero_grad()
        a = _actor_fwd(agent, obs, h, c)
        q = _critic_q(agent, obs, a)
        (-q.sum()).backward()
        opt.step()
    with torch.no_grad():
        a_star = _actor_fwd(agent, obs, h, c)
        q_star = _critic_q(agent, obs, a_star)
        norm_star = a_star.norm(dim=-1)

    return {
        "norm_zero_pct_max": float(np.median(norm_zero.cpu().numpy()) / np.sqrt(2) * 100),
        "norm_star_pct_max": float(np.median(norm_star.cpu().numpy()) / np.sqrt(2) * 100),
        "q_gain_abs_median": float(np.median((q_star - q_zero).cpu().numpy())),
        "q_zero_median": float(np.median(q_zero.cpu().numpy())),
    }


def main():
    print("R107-W2: ||obs|| sweep on R72_w4 SOTA")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"  {len(agents)} agents loaded")
    rng = np.random.default_rng(RNG_SEED)

    rows: list[dict] = []
    for norm in OBS_NORM_GRID:
        obs = _sample_obs(N_OBS_SAMPLES, norm, rng)
        for ai, ag in enumerate(agents):
            r = _h0_optimize_at_norm(ag, obs)
            r["obs_norm"] = norm
            r["agent"] = ai
            rows.append(r)

    # Aggregate per ||obs||
    print("\n  obs_norm | norm_zero | norm_star | norm_lift_pp | ΔQ_abs_med | Q_zero_med")
    print("  ---------|-----------|-----------|--------------|------------|-----------")
    summary_per_norm: list[dict] = []
    for norm in OBS_NORM_GRID:
        sub = [r for r in rows if r["obs_norm"] == norm]
        nz = np.median([r["norm_zero_pct_max"] for r in sub])
        ns = np.median([r["norm_star_pct_max"] for r in sub])
        lift = ns - nz
        dq = np.median([r["q_gain_abs_median"] for r in sub])
        qz = np.median([r["q_zero_median"] for r in sub])
        summary_per_norm.append({
            "obs_norm": norm,
            "norm_zero_pct_max": float(nz),
            "norm_star_pct_max": float(ns),
            "norm_lift_pp": float(lift),
            "q_gain_abs_median": float(dq),
            "q_zero_median": float(qz),
        })
        print(f"  {norm:>7.2f}  |  {nz:6.1f}%  |  {ns:6.1f}%  |   {lift:+7.1f} pp |  {dq:+.4f}  |  {qz:+.3f}")

    # H1 vs H0 verdict
    lift_at_min = summary_per_norm[0]["norm_lift_pp"]   # ||obs||=0.1
    lift_at_steady = summary_per_norm[-1]["norm_lift_pp"]  # ||obs||=2.0
    decay = lift_at_min - lift_at_steady
    if decay > 30:
        h_verdict = (
            f"H1 (slack collapses with ||obs||): lift {lift_at_min:.0f}pp → "
            f"{lift_at_steady:.0f}pp over the obs-norm sweep (Δ={decay:.0f}pp). "
            "Warm-h_0 fix mostly helps transient (step 0-5); steady-state "
            "actor saturates from obs drive alone."
        )
    elif decay < -10:
        h_verdict = (
            f"H1-inverted: lift INCREASES with ||obs|| from {lift_at_min:.0f}pp to "
            f"{lift_at_steady:.0f}pp. LSTM still needs warm-h to saturate even at "
            "steady-state obs — suggests obs alone insufficient regardless of magnitude."
        )
    else:
        h_verdict = (
            f"H0 (constant slack): lift {lift_at_min:.0f}pp → {lift_at_steady:.0f}pp "
            f"(Δ={decay:.0f}pp, < 30pp). Slack roughly constant; LSTM relies on "
            "h_0 not obs to saturate, irrespective of obs magnitude."
        )

    summary = {
        "round": "R107",
        "wave": "W2_obs_norm_sweep",
        "sota": SOTA_DIR.name,
        "n_agents": len(agents),
        "n_obs_per_norm": N_OBS_SAMPLES,
        "obs_norm_grid": OBS_NORM_GRID,
        "per_norm": summary_per_norm,
        "decay_pp": float(decay),
        "hypothesis_verdict": h_verdict,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{h_verdict}")
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
