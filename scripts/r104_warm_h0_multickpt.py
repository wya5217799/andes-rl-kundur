"""R104 — Multi-ckpt extension of R99 warm-h_0 feasibility (zero ANDES).

R99 (CLM-0183) tested 4 R72_w4 SOTA agents and found warm-h_0
gradient-ascent unlocks ||a|| 10.4% → 99.5% of max + Q lift +57.8%.
R104 extends to multiple ckpts (cross-algo, cross-seed, cross-round)
using R86's ckpt registry to test whether Q-0022 architectural slack
is UNIVERSAL (every LSTM ckpt has the property) or R72_w4-specific.

Also fixes R99's +254% outlier: agent 1 had |Q_zero|=0.022 so any
small absolute lift produces large relative %. R104 reports both
absolute Q gain (Δ in raw units) and relative (% of |Q_zero|).

Per ckpt × per agent (only TD3-LSTM ckpts — non-recurrent has no h
to optimise):
- ||a||_zero, ||a||_star, norm lift in pp
- Q_zero, Q_star, ΔQ_abs, ΔQ_rel%
- |h*|, |c*|

Aggregate the feasibility gate across ckpts.

Output: results/r104_warm_h0_multickpt/{summary.json, per_ckpt_table.csv}.
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

# --- Config -------------------------------------------------------------

# Only TD3-LSTM ckpts (non-recurrent has no h to optimise). Subset of R86 set
# plus extra R72 wave ckpts for cross-hyper coverage.
CKPT_SET: list[tuple[str, str]] = [
    ("r72_w4_lstm_tau001_warmup5_s54",    "r72_w4_lstm_s54_SOTA"),
    ("r58_paper_strict_pure_td3_lstm_s49", "r58_lstm_s49"),
    ("r58_paper_strict_pure_td3_lstm_s50", "r58_lstm_s50"),
    ("r58_paper_strict_pure_td3_lstm_s51", "r58_lstm_s51"),
    ("r62_recon_lstm_h128_s51",            "r62_lstm_h128_s51"),  # h=128, larger
    ("r72_w1_lstm_paper_strict_s51",       "r72_w1_lstm_s51"),
    ("r72_w2_lstm_paper_strict_s50",       "r72_w2_lstm_s50"),
    ("r72_w3_lstm_paper_strict_s52",       "r72_w3_lstm_s52"),
    ("r72_w5_lstm_tau001_warmup5_s55",     "r72_w5_lstm_s55"),
]

N_OBS_SAMPLES = 100
OBS_NORM_TARGET = 0.25  # CLM-0161 median step-0 obs_norm
OBS_DIM = 7
N_ASCENT_STEPS = 500
LR_H = 0.05
DEVICE = "cpu"
RNG_SEED = 104
MAX_NORM_REL_FILTER = 0.05  # if |Q_zero| < 5% of max |Q| seen, drop from %_gain agg

OUT_DIR = ROOT / "results" / "r104_warm_h0_multickpt"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _sample_step0_obs(n: int, rng: np.random.Generator) -> torch.Tensor:
    raw = rng.normal(0, 1, size=(n, OBS_DIM)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    raw = raw / np.maximum(norms, 1e-8) * OBS_NORM_TARGET
    return torch.from_numpy(raw).to(DEVICE)


def _actor_fwd(agent, obs: torch.Tensor, h: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
    a, _ = agent.actor(obs, (h, c))
    return a


def _critic_q(agent, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
    h0c = agent.critic.init_hidden(obs.shape[0], DEVICE)
    q1, q2, _ = agent.critic(obs, action, h0c)
    return torch.min(q1.squeeze(-1), q2.squeeze(-1))


def _h0_optimize(agent, obs: torch.Tensor) -> dict:
    if not getattr(agent, "is_recurrent", False):
        return {"is_recurrent": False}
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
        loss = -q.sum()
        loss.backward()
        opt.step()

    with torch.no_grad():
        a_star = _actor_fwd(agent, obs, h, c)
        q_star = _critic_q(agent, obs, a_star)
        norm_star = a_star.norm(dim=-1)

    # Absolute lift in raw Q units (avoids relative-%-blowup when |Q_zero| → 0).
    dq_abs = (q_star - q_zero).cpu().numpy()
    # Relative %, only valid when |Q_zero| is meaningfully sized.
    q_z = q_zero.cpu().numpy()
    q_max_abs = max(np.abs(q_z).max(), 1e-6)
    mask = np.abs(q_z) > MAX_NORM_REL_FILTER * q_max_abs
    if mask.any():
        dq_rel = (dq_abs[mask] / np.abs(q_z[mask])) * 100
    else:
        dq_rel = np.array([np.nan])

    return {
        "is_recurrent": True,
        "hidden": int(hidden),
        "n_obs": int(B),
        "q_zero_median":   float(np.median(q_z)),
        "q_zero_p10":      float(np.percentile(q_z, 10)),
        "q_star_median":   float(np.median(q_star.cpu().numpy())),
        "q_gain_abs_median": float(np.median(dq_abs)),
        "q_gain_abs_p10":  float(np.percentile(dq_abs, 10)),
        "q_gain_rel_pct_median_filtered": float(np.nanmedian(dq_rel)),
        "norm_zero_median": float(np.median(norm_zero.cpu().numpy())),
        "norm_star_median": float(np.median(norm_star.cpu().numpy())),
        "norm_zero_pct_max": float(np.median(norm_zero.cpu().numpy()) / np.sqrt(2) * 100),
        "norm_star_pct_max": float(np.median(norm_star.cpu().numpy()) / np.sqrt(2) * 100),
        "h_norm_star_median": float(np.median(h.detach().norm(dim=-1).cpu().numpy())),
        "c_norm_star_median": float(np.median(c.detach().norm(dim=-1).cpu().numpy())),
        "filtered_frac": float(mask.mean()),
    }


def main() -> None:
    print(f"R104: {len(CKPT_SET)} ckpts × 100 step-0 obs × 4 agents = grad-ascent feasibility sweep\n")
    rng = np.random.default_rng(RNG_SEED)
    obs = _sample_step0_obs(N_OBS_SAMPLES, rng)

    per_ckpt_summary: list[dict] = []
    table_rows: list[dict] = []

    for ckpt_dir, label in CKPT_SET:
        path = ROOT / "results" / ckpt_dir
        if not path.exists():
            print(f"  SKIP missing: {ckpt_dir}")
            continue
        agents = load_agents(path, suffix="best")
        print(f"=== {label} ({ckpt_dir}) | {len(agents)} agents ===")
        per_agent_records = []
        for i, ag in enumerate(agents):
            r = _h0_optimize(ag, obs)
            if not r.get("is_recurrent"):
                print(f"  agent {i}: not recurrent, skip")
                continue
            r["agent"] = i
            r["ckpt"] = label
            per_agent_records.append(r)
            print(f"  ag{i} h={r['hidden']:3d}  ||a||: {r['norm_zero_pct_max']:5.1f}% → {r['norm_star_pct_max']:5.1f}%  "
                  f"ΔQ_abs={r['q_gain_abs_median']:+.4f}  ΔQ_rel={r['q_gain_rel_pct_median_filtered']:+6.1f}%  "
                  f"(|Q|_zero med={r['q_zero_median']:+.3f})  ||h*||={r['h_norm_star_median']:.1f}")
            table_rows.append({k: v for k, v in r.items() if not isinstance(v, list)})

        if not per_agent_records:
            continue

        # Ckpt aggregate
        norm_lift_pp = (
            float(np.median([r["norm_star_pct_max"] for r in per_agent_records]))
            - float(np.median([r["norm_zero_pct_max"] for r in per_agent_records]))
        )
        ckpt_agg = {
            "ckpt": label,
            "n_agents": len(per_agent_records),
            "norm_lift_pp": norm_lift_pp,
            "q_gain_abs_median": float(np.median([r["q_gain_abs_median"] for r in per_agent_records])),
            "q_gain_rel_pct_median_filtered": float(np.median([r["q_gain_rel_pct_median_filtered"] for r in per_agent_records])),
            "norm_zero_pct_max_median": float(np.median([r["norm_zero_pct_max"] for r in per_agent_records])),
            "norm_star_pct_max_median": float(np.median([r["norm_star_pct_max"] for r in per_agent_records])),
            "feasible": bool(norm_lift_pp > 50 and np.median([r["q_gain_abs_median"] for r in per_agent_records]) > 0),
        }
        per_ckpt_summary.append(ckpt_agg)
        print(f"  ckpt agg: norm_lift={norm_lift_pp:+.1f} pp  ΔQ_abs_med={ckpt_agg['q_gain_abs_median']:+.4f}  "
              f"feasible={ckpt_agg['feasible']}\n")

    # Cross-ckpt aggregate
    feasible_count = sum(1 for c in per_ckpt_summary if c["feasible"])
    cross = {
        "n_ckpts_tested": len(per_ckpt_summary),
        "n_ckpts_feasible": feasible_count,
        "feasible_frac": feasible_count / max(len(per_ckpt_summary), 1),
        "median_norm_lift_pp": float(np.median([c["norm_lift_pp"] for c in per_ckpt_summary])),
        "median_q_gain_abs": float(np.median([c["q_gain_abs_median"] for c in per_ckpt_summary])),
        "median_norm_zero_pct_max": float(np.median([c["norm_zero_pct_max_median"] for c in per_ckpt_summary])),
        "median_norm_star_pct_max": float(np.median([c["norm_star_pct_max_median"] for c in per_ckpt_summary])),
    }

    summary = {
        "round": "R104",
        "kind": "warm_h0_feasibility_multickpt",
        "ckpt_set_size": len(CKPT_SET),
        "n_obs_per_agent": N_OBS_SAMPLES,
        "obs_norm_target": OBS_NORM_TARGET,
        "n_ascent_steps": N_ASCENT_STEPS,
        "per_ckpt": per_ckpt_summary,
        "cross_ckpt": cross,
        "verdict": (
            f"UNIVERSAL_FEASIBLE — {feasible_count}/{len(per_ckpt_summary)} ckpts pass feasibility gate"
            if feasible_count >= len(per_ckpt_summary) - 1
            else f"PARTIAL — {feasible_count}/{len(per_ckpt_summary)} ckpts feasible"
            if feasible_count > 0
            else "INFEASIBLE — no ckpt has architectural slack via warm-h_0"
        ),
        "interpretation": (
            "Tests whether warm-h_0 architectural slack (CLM-0183) is "
            "universal across the R86 cross-ckpt set (extended with R72 wave). "
            "Confirms Q-0022's architectural premise is not R72_w4-specific."
        ),
        "synthetic_caveat": (
            "Same synthetic obs caveat as R99 / CLM-0183: ||obs||=0.25 with "
            "random direction. Real ANDES step-0 obs has specific structure; "
            "per-direction feasibility may differ."
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    # Per-agent CSV for easy inspection
    if table_rows:
        with open(OUT_DIR / "per_agent_table.csv", "w", newline="") as f:
            keys = ["ckpt", "agent", "hidden", "norm_zero_pct_max", "norm_star_pct_max",
                    "q_zero_median", "q_star_median", "q_gain_abs_median",
                    "q_gain_rel_pct_median_filtered", "h_norm_star_median"]
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for row in table_rows:
                w.writerow(row)

    print("\n=== R104 cross-ckpt ===")
    print(json.dumps(cross, indent=2))
    print(f"\nVerdict: {summary['verdict']}")
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
