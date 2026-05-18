"""R57-β extension — HAWE-LSTM ensemble on R57 warmup ckpts (4-seed pool).

The original `_r57_beta_hawe_lstm.py` ran a 2-seed ensemble on the R56
ckpts {s49, s51}. With R57-α's 5-seed warmup sweep, we have 4 healthy
ckpts (s49, s51, s52, s53) — s50 still collapsed and is excluded from
the pool. Larger pool = more diversity for HAWE consensus.

Configs:
1. **mean** (uniform 4) — same weight per actor, tests pure consensus
2. **median** (4) — outlier-robust aggregation
3. **weighted_s51_anchor** — 0.5 s51, 0.5/3 each of {s49, s52, s53} — R44-α anchor pattern with the SOTA seed
4. **weighted_top2** — 0.7 s51 + 0.3 s53 (the two strongest individuals)

Prerequisite: ``eval_ensemble._ensemble_action_fn`` is recurrent-aware
(R57-β code patch).

Run: /home/wya/andes_venv/bin/python scripts/_r57_beta_hawe_lstm_warmup.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402
from eval_ensemble import _ensemble_action_fn  # noqa: E402

EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
# 4 healthy R57-α warmup ckpts (s50 excluded — collapsed)
CKPT_DIRS = [
    ROOT / "results" / "td3_lstm_h64_warmup5_s49",
    ROOT / "results" / "td3_lstm_h64_warmup5_s51",
    ROOT / "results" / "td3_lstm_h64_warmup5_s52",
    ROOT / "results" / "td3_lstm_h64_warmup5_s53",
]
# Note: weights are in the SAME ORDER as CKPT_DIRS (49, 51, 52, 53)
CONFIGS = [
    {"label": "hawe_lstm_w5_mean",       "agg": "mean",     "weights": [0.25, 0.25, 0.25, 0.25]},
    {"label": "hawe_lstm_w5_median",     "agg": "median",   "weights": [0.25, 0.25, 0.25, 0.25]},
    {"label": "hawe_lstm_w5_s51anchor",  "agg": "weighted", "weights": [0.167, 0.5, 0.167, 0.167]},
    {"label": "hawe_lstm_w5_top2",       "agg": "weighted", "weights": [0.0, 0.7, 0.0, 0.3]},
]


def _eval_one_config(label: str, agg: str, weights: list[float]) -> dict:
    all_actors = [load_agents(cd, suffix="best") for cd in CKPT_DIRS]
    w = np.array(weights, dtype=np.float64)
    w = w / w.sum()
    afn = _ensemble_action_fn(all_actors, agg, w)
    per: dict[str, float] = {}
    util = {"dH": [], "dD": []}
    settling: list[float] = []
    max_df_score: list[float] = []
    span_pct = {"dM": [], "dD": []}
    for scen, du in SCENARIOS.items():
        rec = run_scenario(
            scen, du, action_fn=afn, label=label, seed=42, steps=150,
            extra_keys={"ensemble_agg": agg, "n_actors": len(all_actors)},
        )
        EVAL_OUT.mkdir(parents=True, exist_ok=True)
        (EVAL_OUT / f"{label}_{scen}.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )
        ts = evaluate_trace(
            EVAL_OUT / f"{label}_{scen}.json", PAPER[scen],
            is_ddic=True, label=label,
        )
        per[scen] = ts.overall
        for ax in ts.axes:
            if ax.name == "dH_utilization":
                util["dH"].append(ax.score)
            elif ax.name == "dD_utilization":
                util["dD"].append(ax.score)
            elif ax.name == "settling_s":
                settling.append(ax.score)
            elif ax.name == "max_|df|_Hz":
                max_df_score.append(ax.score)
        t_arr = np.array([s["t"] for s in rec["traces"]])
        mask = t_arr <= t_arr[0] + 6.0
        dM = np.array([s["delta_M"] for s in rec["traces"]])[mask]
        dD = np.array([s["delta_D"] for s in rec["traces"]])[mask]
        span_pct["dM"].append((dM.max(axis=0) - dM.min(axis=0)).mean() / 400 * 100)
        span_pct["dD"].append((dD.max(axis=0) - dD.min(axis=0)).mean() / 800 * 100)
    geo = math.exp(
        sum(math.log(max(x, 0.01)) for x in per.values()) / len(per)
    )
    return {
        "label": label,
        "agg": agg,
        "weights": weights,
        "LS1": per["load_step_1"],
        "LS2": per["load_step_2"],
        "geo": geo,
        "max_df": sum(max_df_score) / 2,
        "settling": sum(settling) / 2,
        "dH_util": sum(util["dH"]) / 2,
        "dD_util": sum(util["dD"]) / 2,
        "dM_span_pct": sum(span_pct["dM"]) / 2,
        "dD_span_pct": sum(span_pct["dD"]) / 2,
    }


def main() -> None:
    print(f"R57-β HAWE-LSTM ensemble eval over {[d.name for d in CKPT_DIRS]}")
    rows = []
    for cfg in CONFIGS:
        r = _eval_one_config(cfg["label"], cfg["agg"], cfg["weights"])
        rows.append(r)
        print(
            f'  {r["label"]:30s} LS1={r["LS1"]:.3f} LS2={r["LS2"]:.3f} '
            f'geo={r["geo"]:.3f} | dM_sp%={r["dM_span_pct"]:.1f} '
            f'dD_u={r["dD_util"]:.3f}'
        )

    print()
    print("=== R57-β HAWE-LSTM (4-seed warmup5 pool {s49, s51, s52, s53}) ===")
    best = max(rows, key=lambda r: r["geo"])
    print(f"  best config: {best['label']}  geo={best['geo']:.4f}")
    print()
    print("Reference singles:")
    print("  s49 = 0.333  s51 = 0.543 (SOTA)  s52 = 0.415  s53 = 0.437")
    print("  R56 R57-β-prior HAWE 2-seed {s49,s51} w90s51 = 0.518")
    print("  R48-δ HAWE MLP h=64 median = 0.351 (prior production ensemble)")

    summary = {
        "label": "r57_beta_hawe_lstm_warmup",
        "ckpt_dirs": [str(d) for d in CKPT_DIRS],
        "configs": rows,
        "best_label": best["label"],
        "best_geo": best["geo"],
    }
    out = ROOT / "results" / "research_loop" / "r57_beta_hawe_lstm_warmup.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
