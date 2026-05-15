"""V4 paper-faithful no-control eval — generate Fig.6/8 baseline trace JSON.

Mirrors eval_paper_spec_v2.py format so paper_grade_axes.py + figs6_9_ls_traces.py
can read directly. No DDIC ckpt needed (zero-action baseline = paper Fig.6/8).

Output: results/research_loop/eval_v4_baseline/no_control_load_step_{1,2}.json

Run: /home/wya/andes_venv/bin/python scripts/eval_no_control.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

OUT_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STEPS = 150  # 30s @ DT=0.2 (settling axis needs ≥10s, 30s safe)
SEED = 42


def eval_no_control(scenario_name: str, delta_u: dict) -> dict:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(SEED)
    env.STEPS_PER_EPISODE = STEPS
    obs = env.reset(delta_u=delta_u)

    N = env.N_AGENTS
    F_NOM = env.FN
    traces = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0

    for step in range(STEPS):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(N)}
        obs, rewards, done, info = env.step(actions)
        if info.get("tds_failed"):
            break

        freq_hz = info["freq_hz"].astype(float).tolist()
        delta_f = [(f - F_NOM) for f in freq_hz]
        f_bar = float(np.mean(freq_hz))
        step_rf = float(np.mean([(d - (f_bar - F_NOM)) ** 2 for d in delta_f]))
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

    env.close()
    return {
        "controller":   "no_control",
        "scenario":     scenario_name,
        "env_version":  "v4",
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "osc":          osc_accum,
        "n_steps":      len(traces),
        "traces":       traces,
    }


def main():
    print(f"[V4 eval] no-control baseline → {OUT_DIR}")
    for scen, du in SCENARIOS.items():
        print(f"  running {scen} (delta_u={du})...")
        rep = eval_no_control(scen, du)
        out_path = OUT_DIR / f"no_control_{scen}.json"
        out_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(f"  saved {out_path} (max_df={rep['max_df']:.3f}, n_steps={rep['n_steps']})")
    print("\n[V4 eval] all done.")


if __name__ == "__main__":
    main()
