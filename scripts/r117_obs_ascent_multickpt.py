"""R117 — Multi-ckpt extension of R116 obs-ascent hard-ceiling.

R116 (CLM-0212) on R72_w4 SOTA found obs-ascent at h=0 max ||a||*
= 41% of max. R117 extends to the R104 9-ckpt set to verify the
~40% architectural hard ceiling is universal across LSTM ckpts.

Output: results/r117_obs_ascent_multickpt/summary.json.
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


CKPT_SET: list[tuple[str, str]] = [
    ("r72_w4_lstm_tau001_warmup5_s54",    "r72_w4_lstm_s54_SOTA"),
    ("r58_paper_strict_pure_td3_lstm_s49", "r58_lstm_s49"),
    ("r58_paper_strict_pure_td3_lstm_s50", "r58_lstm_s50"),
    ("r58_paper_strict_pure_td3_lstm_s51", "r58_lstm_s51"),
    ("r62_recon_lstm_h128_s51",            "r62_lstm_h128_s51"),
    ("r72_w1_lstm_paper_strict_s51",       "r72_w1_lstm_s51"),
    ("r72_w2_lstm_paper_strict_s50",       "r72_w2_lstm_s50"),
    ("r72_w3_lstm_paper_strict_s52",       "r72_w3_lstm_s52"),
    ("r72_w5_lstm_tau001_warmup5_s55",     "r72_w5_lstm_s55"),
]

N_INIT = 30
OBS_DIM = 7
OBS_INIT_NORM = 0.25
OBS_NORM_CEILING = 5.0
N_ASCENT = 300  # reduced from R116's 500 for budget
LR = 0.05
LAMBDA_NORM = 0.1
DEVICE = "cpu"
RNG_SEED = 117

OUT_DIR = ROOT / "results" / "r117_obs_ascent_multickpt"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _sample_init_obs(n, rng):
    raw = rng.normal(0, 1, size=(n, OBS_DIM)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    raw = raw / np.maximum(norms, 1e-8) * OBS_INIT_NORM
    return torch.from_numpy(raw).to(DEVICE)


def _action_norm(agent, obs):
    h0 = agent.actor.init_hidden(obs.shape[0], DEVICE)
    a, _ = agent.actor(obs, h0)
    return a.norm(dim=-1)


def _obs_ascend(agent, obs_init):
    obs = obs_init.clone().detach().requires_grad_(True)
    opt = torch.optim.Adam([obs], lr=LR)
    for _ in range(N_ASCENT):
        opt.zero_grad()
        a_norm = _action_norm(agent, obs)
        on = obs.norm(dim=-1)
        penalty = LAMBDA_NORM * torch.clamp(on - OBS_NORM_CEILING, min=0.0) ** 2
        (-(a_norm - penalty).sum()).backward()
        opt.step()
    with torch.no_grad():
        return _action_norm(agent, obs).cpu().numpy()


def main():
    print(f"R117: obs-ascent across {len(CKPT_SET)} LSTM ckpts")
    rng = np.random.default_rng(RNG_SEED)
    obs_init = _sample_init_obs(N_INIT, rng)

    per_ckpt = []
    for ckpt_dir, label in CKPT_SET:
        path = ROOT / "results" / ckpt_dir
        if not path.exists():
            continue
        agents = load_agents(path, suffix="best")
        a_inits, a_stars = [], []
        for ag in agents:
            with torch.no_grad():
                a_inits.extend(_action_norm(ag, obs_init).cpu().numpy().tolist())
            a_stars.extend(_obs_ascend(ag, obs_init).tolist())
        a_inits, a_stars = np.array(a_inits), np.array(a_stars)
        rec = {
            "ckpt": label,
            "a_init_med_pct": float(np.median(a_inits) / np.sqrt(2) * 100),
            "a_star_med_pct": float(np.median(a_stars) / np.sqrt(2) * 100),
            "a_star_max_pct": float(np.max(a_stars) / np.sqrt(2) * 100),
            "lift_pp": float((np.median(a_stars) - np.median(a_inits)) / np.sqrt(2) * 100),
        }
        per_ckpt.append(rec)
        print(f"  {label:25s} init={rec['a_init_med_pct']:5.1f}%  ascent_med={rec['a_star_med_pct']:5.1f}%  "
              f"ascent_max={rec['a_star_max_pct']:5.1f}%  lift={rec['lift_pp']:+5.1f}pp")

    # Cross-ckpt aggregate
    star_med_pcts = [r["a_star_med_pct"] for r in per_ckpt]
    star_max_pcts = [r["a_star_max_pct"] for r in per_ckpt]
    aggregate = {
        "n_ckpts": len(per_ckpt),
        "median_a_star_pct": float(np.median(star_med_pcts)),
        "max_a_star_pct": float(np.max(star_max_pcts)),
        "p90_a_star_pct": float(np.percentile(star_max_pcts, 90)),
        "frac_ckpts_below_50pct_max": float(np.mean([m < 50 for m in star_max_pcts])),
    }
    summary = {
        "round": "R117",
        "kind": "obs_ascent_multickpt_hard_ceiling",
        "n_ckpts": len(CKPT_SET),
        "per_ckpt": per_ckpt,
        "aggregate": aggregate,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print("\nAggregate:")
    print(json.dumps(aggregate, indent=2))
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
