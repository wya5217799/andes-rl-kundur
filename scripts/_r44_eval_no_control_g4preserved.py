"""R44-β — re-run no-control baseline with ZERO_G4_INERTIA=False
(G4 inertia preserved, the paper-claimed setting).

Addresses Q-0001 (opened R37). The current eval_no_control.py uses
V4Config.paper_faithful() which sets zero_g4_inertia=True (the
silent V2-inheritance state pinned in R37 / CLM-0040 to keep
bit-identical paper headlines). This script flips the flag and
re-measures.

Cheapest answer to "does the paper-cited 0.444 / 0.439 / 0.104
ranking survive G4 preservation?": rerun the no_control baseline.
If 6-axis stays in [0.09, 0.12], headline ranking is robust to G4
and Q-0001 can be closed-negative.

Output JSON files are saved under
results/research_loop/eval_v4_baseline/ with label
'no_control_g4preserved' so they don't overwrite the canonical
paper-faithful baseline at no_control_load_step_*.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

OUT_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LABEL = "no_control_g4preserved"
STEPS = 150
SEED = 42


def zero_action(n_agents: int):
    return {i: np.zeros(2, dtype=np.float32) for i in range(n_agents)}


def run_one(scen_name: str, delta_u: dict) -> dict:
    cfg = V4Config.paper_faithful()
    # Flip G4 inertia: preserved instead of zeroed
    from dataclasses import replace
    cfg = replace(cfg, zero_g4_inertia=False)

    env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        config=cfg,
    )
    traces: list[dict] = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0
    try:
        env.seed(SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS
        f_nom = env.FN

        for step in range(STEPS):
            actions = zero_action(n_agents)
            obs, _rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                break
            freq_hz = info["freq_hz"].astype(float).tolist()
            delta_f = [(f - f_nom) for f in freq_hz]
            f_bar = float(np.mean(freq_hz))
            step_rf = float(np.mean([(d - (f_bar - f_nom)) ** 2 for d in delta_f]))
            cum_rf -= step_rf
            max_df = max(max_df, float(np.max(np.abs(delta_f))))
            osc_accum += float(np.std(delta_f))

            traces.append({
                "step":       step,
                "t":          float(info["time"]),
                "freq_hz":    freq_hz,
                "f_bar":      f_bar,
                "step_rf":    step_rf,
                "delta_P_es": info["P_es"].astype(float).tolist(),
                "delta_f_es": delta_f,
                "M_es":       info["M_es"].astype(float).tolist(),
                "D_es":       info["D_es"].astype(float).tolist(),
                "delta_M":    info["delta_M"].astype(float).tolist(),
                "delta_D":    info["delta_D"].astype(float).tolist(),
            })
            if done:
                break
    finally:
        try:
            env.close()
        except Exception:
            pass

    return {
        "controller":   LABEL,
        "scenario":     scen_name,
        "env_version":  "v4",
        "zero_g4_inertia": False,
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "osc_total":    osc_accum,
        "n_steps":      len(traces),
        "traces":       traces,
    }


def main():
    print(f"[R44-beta] no-control eval with G4 PRESERVED (zero_g4_inertia=False)")
    for scen, du in SCENARIOS.items():
        print(f"  running {scen} (delta_u={du})...")
        rec = run_one(scen, du)
        out = OUT_DIR / f"{LABEL}_{scen}.json"
        out.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
        print(f"  saved {out} (max_df={rec['max_df']:.3f}, n_steps={rec['n_steps']})")
    print("[R44-beta] done.")


if __name__ == "__main__":
    main()
