"""R133 — Magnitude-PI re-eval at D5-fair action bounds (dm_max=600, dm_min=-200).

R102 magnitude-PI ran on V4Config DEFAULT (dm_max=300 paper Eq.12 literal).
R72_w4 SOTA was trained at dm_max=600, dm_min=-200 (CLM-0233 D5 finding,
2× paper bounds). "1.50× RL advantage" comparison handicapped classical
with smaller action range. R133 re-evaluates magnitude-PI at SOTA's bounds.

Output: ``results/r133_mag_pi_d5_fair/{summary.json, traces}``

Run (WSL only):
    /home/wya/andes_venv/bin/python scripts/r133_mag_pi_d5_fair.py
"""
from __future__ import annotations

import json
import logging
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
log = logging.getLogger("r133")

OUT_DIR = ROOT / "results" / "r133_mag_pi_d5_fair"
OUT_DIR.mkdir(parents=True, exist_ok=True)
R85_NC_CACHE = ROOT / "results" / "r85_classical_baseline" / "_no_control_cache"

STEPS = 150
SEED = 42
DT = KUNDUR.dt


# D5-fair config: matches R72_w4 SOTA training bounds (CLM-0233)
# Paper Eq.12 is [-100, +300] for dM; R72_w4 trained at [-200, +600] (2x).
CFG_D5_FAIR = V4Config(dm_max=600.0, dm_min=-200.0, dd_max=600.0, dd_min=-200.0)


class MagnitudePIController:
    """Same as R102, magnitude-symmetric P (Ki=0 was always best)."""
    def __init__(self, kp_M: float, kp_D: float, n_agents: int):
        self.kp_M = kp_M
        self.kp_D = kp_D
        self.n_agents = n_agents

    def __call__(self, step, obs, n_agents):
        actions = {}
        for i in range(n_agents):
            abserr = abs(float(obs[i][1]))
            dM = self.kp_M * abserr
            dD = self.kp_D * abserr
            actions[i] = np.array([
                float(np.clip(dM, 0.0, 1.0)),
                float(np.clip(dD, 0.0, 1.0)),
            ], dtype=np.float32)
        return actions


def eval_at_d5_fair(kp_M: float, kp_D: float, label: str) -> dict:
    """Eval a gain combo at D5-fair bounds, reuse R85 no_control cache."""
    sub = OUT_DIR / label
    sub.mkdir(parents=True, exist_ok=True)
    # We need a fresh no_control cache at D5-fair bounds (R85 cache used default)
    nc_paths = {}
    for scen, du in SCENARIOS.items():
        nc_path = sub / f"no_control_{scen}.json"
        if not nc_path.exists():
            rep = run_scenario(scen, du, action_fn=zero_action_fn,
                               label="no_control", seed=SEED, steps=STEPS,
                               config=CFG_D5_FAIR)
            nc_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
            log.info(f"  no_ctrl/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
        nc_paths[scen] = nc_path
    # Now controller
    trace_paths = {}
    for scen, du in SCENARIOS.items():
        fn = MagnitudePIController(kp_M, kp_D, KUNDUR.n_agents)
        rep = run_scenario(scen, du, action_fn=fn,
                           label="mag_pi", seed=SEED, steps=STEPS,
                           config=CFG_D5_FAIR)
        p = sub / f"mag_pi_{scen}.json"
        p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        trace_paths[scen] = p
        log.info(f"  mag-PI(K={kp_M},{kp_D})/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
    summary = score_trace_files(trace_paths, label="mag_pi", is_ddic=True)
    log.info(f"  → {format_headline(summary)}")
    return summary


def main():
    log.info("R133 — magnitude-PI at D5-fair bounds (dm_max=600, dm_min=-200)")
    log.info(f"  output → {OUT_DIR}")

    grand = {
        "round": 133,
        "config": {"dm_max": 600.0, "dm_min": -200.0, "dd_max": 600.0, "dd_min": -200.0},
        "reference": {
            "r72_w4_sota_geo": 0.391,
            "r85_default_droop_best_geo": 0.197,
            "r85_default_mag_pi_best_geo": 0.260,
        },
        "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "evals": [],
    }
    # Test R102 winning gains + scaled-up gains for the wider range
    test_combos = [
        (2.0, 5.0),    # R102 best at dm_max=300, see how it changes at dm_max=600
        (4.0, 10.0),   # 2x scaled gains (use wider range)
        (8.0, 20.0),   # 4x scaled (aggressive)
    ]
    best_geo = -1
    best_combo = None
    for (kp_M, kp_D) in test_combos:
        label = f"kpM{kp_M}_kpD{kp_D}"
        log.info(f"\n=== [mag-PI] {label} ===")
        s = eval_at_d5_fair(kp_M, kp_D, label)
        grand["evals"].append({"kp_M": kp_M, "kp_D": kp_D, **s})
        (OUT_DIR / "r133_summary.json").write_text(
            json.dumps(grand, indent=2, default=str), encoding="utf-8")
        geo = s.get("geo") or 0
        if geo > best_geo:
            best_geo = geo
            best_combo = (kp_M, kp_D)

    log.info("\n" + "=" * 60)
    log.info("R133 HEADLINE")
    log.info("=" * 60)
    log.info("  R85 mag-PI at dm_max=300 (handicapped): geo = 0.260")
    log.info(f"  R133 mag-PI best at dm_max=600 (D5-fair): geo = {best_geo:.4f}  K={best_combo}")
    log.info("  R72_w4 SOTA at dm_max=600 (D5-trained): geo = 0.391")
    log.info(f"  RL advantage (apples-to-apples): {0.391 / best_geo:.2f}x")
    log.info("=" * 60)
    grand["headline"] = {
        "best_d5_fair_geo": best_geo,
        "best_d5_fair_gains": best_combo,
        "rl_advantage_apples_to_apples": 0.391 / best_geo if best_geo > 0 else None,
        "finished_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / "r133_summary.json").write_text(
        json.dumps(grand, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
