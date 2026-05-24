"""R116 — Obs-gradient ascent at h=0 (complement to R104 h-gradient ascent).

R107-W2 (CLM-0193) showed LSTM ||a||(h=0) stays at 10% across ||obs||
sweep [0.1, 2.0]. That tested RANDOM obs directions. R116 tests
**optimised** obs directions: is there a specific obs direction such
that the LSTM at h=0 reaches saturation?

If YES (some obs direction unlocks saturation at h=0):
  → an obs-conditioning trick could substitute for warm-h_0
  → the LSTM has a "saturation key" in obs that random sampling misses

If NO (no obs direction works at h=0):
  → R107-W2 is even stronger: LSTM categorically rejects obs as a
    saturation trigger when h=0
  → warm-h_0 is the only viable fix

Method: per ckpt × per agent × 50 init obs (random direction, ||obs||
free to grow under ascent budget):
  obs* = argmax_obs (||a||(obs, h=0)) - regulariser × ||obs||
where the regulariser keeps obs in a plausible range (penalty when
||obs|| > 5, far above any realistic ANDES obs).

Compares ||a||(obs*, h=0) vs ||a||(obs_init, h=0) and also vs
||a||(obs_init, h*) (R104 baseline). Zero ANDES.
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
OUT_DIR = ROOT / "results" / "r116_obs_grad_at_h0"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_INIT = 50
OBS_DIM = 7
OBS_INIT_NORM = 0.25
OBS_NORM_CEILING = 5.0  # far above realistic ANDES obs
N_ASCENT = 500
LR = 0.05
LAMBDA_NORM = 0.1  # penalty coefficient
DEVICE = "cpu"
RNG_SEED = 116


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
    """Gradient-ascent over obs at h=0 to maximise ||a||, with soft
    norm penalty above OBS_NORM_CEILING."""
    obs = obs_init.clone().detach().requires_grad_(True)
    opt = torch.optim.Adam([obs], lr=LR)
    for _ in range(N_ASCENT):
        opt.zero_grad()
        a_norm = _action_norm(agent, obs)
        # Penalty: max(0, ||obs|| - ceiling)^2
        on = obs.norm(dim=-1)
        penalty = LAMBDA_NORM * torch.clamp(on - OBS_NORM_CEILING, min=0.0) ** 2
        loss = -(a_norm - penalty).sum()
        loss.backward()
        opt.step()

    with torch.no_grad():
        a_norm_star = _action_norm(agent, obs)
        obs_norm_star = obs.norm(dim=-1)
    return {
        "a_norm_star": a_norm_star.cpu().numpy(),
        "obs_norm_star": obs_norm_star.cpu().numpy(),
    }


def main():
    print("R116: obs-gradient ascent at h=0 on R72_w4 SOTA")
    agents = load_agents(SOTA_DIR, suffix="best")
    rng = np.random.default_rng(RNG_SEED)
    obs_init = _sample_init_obs(N_INIT, rng)

    per_agent = []
    for i, ag in enumerate(agents):
        with torch.no_grad():
            a_init = _action_norm(ag, obs_init).cpu().numpy()
        ascended = _obs_ascend(ag, obs_init)
        rec = {
            "agent": i,
            "a_init_med":   float(np.median(a_init)),
            "a_star_med":   float(np.median(ascended["a_norm_star"])),
            "a_star_max":   float(np.max(ascended["a_norm_star"])),
            "obs_init_norm_med":  OBS_INIT_NORM,
            "obs_star_norm_med":  float(np.median(ascended["obs_norm_star"])),
            "a_init_pct_max": float(np.median(a_init) / np.sqrt(2) * 100),
            "a_star_pct_max": float(np.median(ascended["a_norm_star"]) / np.sqrt(2) * 100),
        }
        per_agent.append(rec)
        print(f"  agent {i}: ||a|| {rec['a_init_pct_max']:5.1f}% → {rec['a_star_pct_max']:5.1f}%  "
              f"(obs norm {rec['obs_init_norm_med']:.2f} → {rec['obs_star_norm_med']:.2f}, ceiling {OBS_NORM_CEILING})  "
              f"max ||a||={rec['a_star_max']:.3f}")

    # Aggregate
    lift_pp = float(np.median([r["a_star_pct_max"] for r in per_agent])) - float(
        np.median([r["a_init_pct_max"] for r in per_agent])
    )
    can_hit_50pct = float(np.mean([r["a_star_max"] >= 0.71 for r in per_agent]))
    can_hit_95pct = float(np.mean([r["a_star_max"] >= 1.34 for r in per_agent]))

    summary = {
        "round": "R116",
        "kind": "obs_grad_ascent_at_h0",
        "sota": SOTA_DIR.name,
        "n_agents": len(agents),
        "n_init_obs": N_INIT,
        "obs_norm_ceiling": OBS_NORM_CEILING,
        "per_agent": per_agent,
        "lift_median_pp": lift_pp,
        "frac_agents_can_hit_50pct_max": can_hit_50pct,
        "frac_agents_can_hit_95pct_max": can_hit_95pct,
        "interpretation": (
            "Tests whether an OBS direction can substitute for warm-h_0 "
            "in unlocking step-0 actor saturation. Complements R107-W2 "
            "(random obs, decay=0) with optimised obs."
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    if can_hit_95pct >= 0.75 and lift_pp > 60:
        verdict = (
            f"OBS_PATH_UNLOCKS — {can_hit_95pct*100:.0f}% of agents can reach "
            f">=95% saturation via obs alone (norm budget {OBS_NORM_CEILING}). "
            "Alternative fix to warm-h_0 exists."
        )
    elif lift_pp > 30:
        verdict = (
            f"PARTIAL — obs alone lifts {lift_pp:.1f} pp from h=0 baseline, "
            "but cannot reach saturation. Warm-h_0 still primary fix."
        )
    else:
        verdict = (
            f"OBS_PATH_BLOCKED — obs-gradient ascent at h=0 gives only "
            f"+{lift_pp:.1f} pp lift, well below the +89 pp warm-h_0 lift. "
            "LSTM categorically rejects obs as a saturation trigger when h=0; "
            "warm-h_0 (or analogous h-conditioning) is the ONLY viable fix."
        )
    print(f"\n{verdict}")
    summary["verdict"] = verdict
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
