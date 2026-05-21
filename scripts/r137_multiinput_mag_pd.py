"""R137 — Multi-input magnitude-PD controller (close 1.5x RL gap test).

R85/R102 mag-PI used ONLY obs[i][1] (local Δω). Paper Eq.11 obs has m=2
neighbors (obs[i][3], obs[i][4] = neighbor Δω) + derivative (obs[i][2] =
Δω̇). R72_w4 SOTA exploits all 7 obs dims. R102 verdict hypothesised:
"RL advantage from multi-input use" (CLM-0230). R137 tests this.

Multi-input magnitude-PD:
  err   = |obs[i][1]|              # local |Δω|
  derr  = |obs[i][2]|              # local |Δω̇|
  nerr  = mean(|obs[i][3..3+m-1]|) # neighbor avg |Δω|

  ΔM_norm[i] = clip(Kp_M*err + Kd_M*derr + Kn_M*nerr, 0, 1)
  ΔD_norm[i] = clip(Kp_D*err + Kd_D*derr + Kn_D*nerr, 0, 1)

Tests 6 single-axis additions to find which obs dim contributes most.
Single ANDES session. Uses D5-fair bounds (dm_max=600, dm_min=-200) for
apples-to-apples vs R72_w4 SOTA.

Wait-pattern uses `[r]133` bracket trick to avoid self-match bug
(R114 wait-task got stuck because `pgrep -f r102` matched its own
command line).
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import run_scenario, zero_action_fn  # noqa: E402
from andes_rl_kundur.evaluation.summary import format_headline, score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402
from andes_rl_kundur.scenarios.contract import KUNDUR  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r137")

OUT_DIR = ROOT / "results" / "r137_multiinput_mag_pd"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STEPS = 150
SEED = 42

CFG_D5_FAIR = V4Config(dm_max=600.0, dm_min=-200.0, dd_max=600.0, dd_min=-200.0)

# Number of neighbor obs slots = KUNDUR.max_neighbors = 2
M_NEIGHBORS = KUNDUR.max_neighbors


class MultiInputMagPDController:
    """Multi-input magnitude-PD using local Δω, |Δω̇|, neighbor avg |Δω|.

    Returns ΔM, ΔD ∈ [0, 1] (magnitude-symmetric, both add inertia/damping).
    """
    def __init__(self, kp_M, kd_M, kn_M, kp_D, kd_D, kn_D, n_agents):
        self.kp_M, self.kd_M, self.kn_M = kp_M, kd_M, kn_M
        self.kp_D, self.kd_D, self.kn_D = kp_D, kd_D, kn_D
        self.n_agents = n_agents

    def __call__(self, step, obs, n_agents):
        actions = {}
        for i in range(n_agents):
            o = obs[i]
            err = abs(float(o[1]))
            derr = abs(float(o[2]))
            # neighbor avg |Δω| — slots 3 .. 3+M_NEIGHBORS-1
            nerr_vals = [abs(float(o[3 + k])) for k in range(M_NEIGHBORS)]
            nerr = float(np.mean(nerr_vals))

            dM = self.kp_M * err + self.kd_M * derr + self.kn_M * nerr
            dD = self.kp_D * err + self.kd_D * derr + self.kn_D * nerr
            actions[i] = np.array([
                float(np.clip(dM, 0.0, 1.0)),
                float(np.clip(dD, 0.0, 1.0)),
            ], dtype=np.float32)
        return actions


def eval_combo(kp_M, kd_M, kn_M, kp_D, kd_D, kn_D, label: str) -> dict:
    sub = OUT_DIR / label
    sub.mkdir(parents=True, exist_ok=True)

    nc_paths = {}
    for scen, du in SCENARIOS.items():
        nc_path = sub / f"no_control_{scen}.json"
        if not nc_path.exists():
            rep = run_scenario(scen, du, action_fn=zero_action_fn,
                               label="no_control", seed=SEED, steps=STEPS,
                               config=CFG_D5_FAIR)
            nc_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        nc_paths[scen] = nc_path

    trace_paths = {}
    for scen, du in SCENARIOS.items():
        fn = MultiInputMagPDController(kp_M, kd_M, kn_M, kp_D, kd_D, kn_D,
                                        KUNDUR.n_agents)
        rep = run_scenario(scen, du, action_fn=fn,
                           label="mag_pd_mi", seed=SEED, steps=STEPS,
                           config=CFG_D5_FAIR)
        p = sub / f"mag_pd_mi_{scen}.json"
        p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        trace_paths[scen] = p
        log.info(f"  {label}/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
    summary = score_trace_files(trace_paths, label="mag_pd_mi", is_ddic=True)
    log.info(f"  → {format_headline(summary)}")
    return summary


def main():
    log.info(f"R137 — multi-input magnitude-PD; output → {OUT_DIR}")
    log.info(f"  config: dm_max=600 (D5-fair), neighbors m={M_NEIGHBORS}")

    # Base: R102 best Kp_M=2, Kp_D=5. Add 1 extra term at a time.
    base = {"kp_M": 2.0, "kp_D": 5.0}
    # Each test = base + one additional input gain. Compare against base (kd=kn=0).
    combos = [
        # (label, kp_M, kd_M, kn_M, kp_D, kd_D, kn_D)
        ("base_p_only",      2.0, 0.0, 0.0, 5.0, 0.0, 0.0),  # baseline = R102 best at D5-fair
        ("plus_dM",          2.0, 1.0, 0.0, 5.0, 0.0, 0.0),  # add derivative on M
        ("plus_dD",          2.0, 0.0, 0.0, 5.0, 1.0, 0.0),  # add derivative on D
        ("plus_dM_dD",       2.0, 1.0, 0.0, 5.0, 1.0, 0.0),  # both derivatives
        ("plus_nM",          2.0, 0.0, 1.0, 5.0, 0.0, 0.0),  # add neighbor on M
        ("plus_nD",          2.0, 0.0, 0.0, 5.0, 0.0, 1.0),  # add neighbor on D
        ("plus_nM_nD",       2.0, 0.0, 1.0, 5.0, 0.0, 1.0),  # both neighbors
        ("full",             2.0, 1.0, 1.0, 5.0, 1.0, 1.0),  # everything on
    ]

    grand = {
        "round": 137,
        "config": "dm_max=600 dm_min=-200 (D5-fair)",
        "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "neighbors_m": M_NEIGHBORS,
        "reference": {
            "r72_w4_sota_geo": 0.391,
            "r85_default_mag_pi_geo": 0.260,
        },
        "evals": [],
    }
    best_geo, best_label = -1, None
    for combo in combos:
        label, kp_M, kd_M, kn_M, kp_D, kd_D, kn_D = combo
        log.info(f"\n=== [mi-mag-PD] {label} ===")
        log.info(f"  M-gains: P={kp_M} D={kd_M} N={kn_M}  D-gains: P={kp_D} D={kd_D} N={kn_D}")
        s = eval_combo(kp_M, kd_M, kn_M, kp_D, kd_D, kn_D, label)
        grand["evals"].append({
            "label": label, "kp_M": kp_M, "kd_M": kd_M, "kn_M": kn_M,
            "kp_D": kp_D, "kd_D": kd_D, "kn_D": kn_D, **s,
        })
        (OUT_DIR / "r137_summary.json").write_text(
            json.dumps(grand, indent=2, default=str), encoding="utf-8")
        geo = s.get("geo") or 0
        if geo > best_geo:
            best_geo = geo
            best_label = label

    log.info("\n" + "=" * 60)
    log.info("R137 HEADLINE")
    log.info("=" * 60)
    log.info(f"  R102 mag-PI at dm_max=300 (handicapped): geo = 0.260")
    log.info(f"  R137 multi-input best: geo = {best_geo:.4f}  ({best_label})")
    log.info(f"  R72_w4 SOTA: geo = 0.391")
    log.info(f"  RL advantage: {0.391 / best_geo:.2f}x")
    log.info("=" * 60)
    grand["headline"] = {
        "best_mi_geo": best_geo, "best_mi_label": best_label,
        "rl_advantage": 0.391 / best_geo if best_geo > 0 else None,
        "finished_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / "r137_summary.json").write_text(
        json.dumps(grand, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
