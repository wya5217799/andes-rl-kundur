"""R145 — Focused multi-input magnitude-PD ceiling test.

Replaces R137 which was killed by WSL reboot (1.5/8 evals completed).
R145 runs ONLY the 2 most informative combos to answer:
"Does adding neighbor obs to magnitude-PD close the 1.50× RL gap?"

  plus_nM_nD : add neighbor avg |Δω| on BOTH M and D (no derivatives)
  full       : everything (P + derivative + neighbor on both M and D)

If either combo geo ≥ 0.30, multi-input narrows the gap (RL advantage <1.30×).
If both stay ≈ 0.26, single-input ceiling is real (RL retains 1.50×).

Reuses R85 no_control cache where possible (D5-fair bounds need fresh cache).
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
log = logging.getLogger("r145")

OUT_DIR = ROOT / "results" / "r145_mag_pd_focused"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Re-use R137's no_control cache if exists (saves 2 evals, ~6 min)
R137_BASE = ROOT / "results" / "r137_multiinput_mag_pd" / "base_p_only"

STEPS = 150
SEED = 42
CFG_D5_FAIR = V4Config(dm_max=600.0, dm_min=-200.0, dd_max=600.0, dd_min=-200.0)
M_NEIGHBORS = KUNDUR.max_neighbors


class MultiInputMagPDController:
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
        # Try copy from R137 base cache (D5-fair compatible) first
        r137_cached = R137_BASE / f"no_control_{scen}.json"
        if not nc_path.exists():
            if r137_cached.exists():
                shutil.copy(r137_cached, nc_path)
                log.info(f"  no_ctrl/{scen}: reused R137 cache")
            else:
                rep = run_scenario(scen, du, action_fn=zero_action_fn,
                                   label="no_control", seed=SEED, steps=STEPS,
                                   config=CFG_D5_FAIR)
                nc_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
                log.info(f"  no_ctrl/{scen}: fresh max_df={rep['max_df']:.4f}")
        nc_paths[scen] = nc_path

    trace_paths = {}
    for scen, du in SCENARIOS.items():
        trace_p = sub / f"mag_pd_mi_{scen}.json"
        if trace_p.exists():
            log.info(f"  {label}/{scen}: cached, skipping")
            trace_paths[scen] = trace_p
            continue
        fn = MultiInputMagPDController(kp_M, kd_M, kn_M, kp_D, kd_D, kn_D,
                                        KUNDUR.n_agents)
        rep = run_scenario(scen, du, action_fn=fn,
                           label="mag_pd_mi", seed=SEED, steps=STEPS,
                           config=CFG_D5_FAIR)
        trace_p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        trace_paths[scen] = trace_p
        log.info(f"  {label}/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
    summary = score_trace_files(trace_paths, label="mag_pd_mi", is_ddic=True)
    log.info(f"  → {format_headline(summary)}")
    return summary


def main():
    log.info(f"R145 — focused multi-input mag-PD; output → {OUT_DIR}")
    log.info(f"  Base gains R102 best: Kp_M=2, Kp_D=5; adding neighbor (1.0) and/or derivative (1.0)")

    grand = {
        "round": 145,
        "config": "dm_max=600 (D5-fair)",
        "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "predecessor": "R137 killed by WSL reboot mid-eval",
        "reference": {
            "r72_w4_sota_geo": 0.391,
            "r102_mag_pi_base_geo": 0.260,
        },
        "evals": [],
    }

    # 2 critical combos: neighbor-only, full
    combos = [
        # (label,            kp_M, kd_M, kn_M, kp_D, kd_D, kn_D)
        ("plus_nM_nD",       2.0,  0.0,  1.0,  5.0,  0.0,  1.0),
        ("full",             2.0,  1.0,  1.0,  5.0,  1.0,  1.0),
    ]

    best_geo, best_label = -1, None
    for combo in combos:
        label, kp_M, kd_M, kn_M, kp_D, kd_D, kn_D = combo
        log.info(f"\n=== [mi-mag-PD] {label} (M={kp_M},{kd_M},{kn_M}  D={kp_D},{kd_D},{kn_D}) ===")
        s = eval_combo(kp_M, kd_M, kn_M, kp_D, kd_D, kn_D, label)
        grand["evals"].append({"label": label, "kp_M": kp_M, "kd_M": kd_M, "kn_M": kn_M,
                               "kp_D": kp_D, "kd_D": kd_D, "kn_D": kn_D, **s})
        (OUT_DIR / "r145_summary.json").write_text(
            json.dumps(grand, indent=2, default=str), encoding="utf-8")
        geo = s.get("geo") or 0
        if geo > best_geo:
            best_geo = geo
            best_label = label

    log.info("\n" + "=" * 60)
    log.info("R145 HEADLINE")
    log.info("=" * 60)
    log.info(f"  R102 mag-PI (P-only, single-input): geo = 0.260")
    log.info(f"  R145 best multi-input: geo = {best_geo:.4f}  ({best_label})")
    log.info(f"  R72_w4 SOTA: geo = 0.391")
    log.info(f"  RL advantage: {0.391 / best_geo:.2f}x")
    log.info("=" * 60)
    grand["headline"] = {
        "best_mi_geo": best_geo, "best_mi_label": best_label,
        "rl_advantage": 0.391 / best_geo if best_geo > 0 else None,
        "finished_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / "r145_summary.json").write_text(
        json.dumps(grand, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
