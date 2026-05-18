"""R57-β — HAWE-LSTM ensemble eval on R56 ckpts {s49, s51}.

R56 produced 3 LSTM ckpts: s49 (geo 0.333), s50 (collapsed, 0.109),
s51 (geo 0.526 — new V4 single-seed record). s50 is excluded from
the ensemble pool. This script evaluates 3 ensemble configurations
across the 2 converged seeds:

1. **mean** (uniform 50/50)
2. **weighted 0.9 / 0.1** — s51-anchored (R44-α pattern)
3. **weighted 0.75 / 0.25** — s51-dominant, gentler smoothing

(Median for n=2 is mathematically equal to mean, so skipped.)

Prerequisites: ``scripts/eval_ensemble.py:_ensemble_action_fn`` must
call ``begin_episode()`` on recurrent agents at ``step == 0`` — added
in R57-β code patch and unit-tested in
``tests/test_eval_ensemble_recurrent.py``.

Outputs the same diagnostic block as :mod:`_r56_score_lstm` plus the
3-axis ensemble comparison.

Run: /home/wya/andes_venv/bin/python scripts/_r57_beta_hawe_lstm.py
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
from andes_rl_kundur.evaluation.paper_grade_axes import (  # noqa: E402
    PAPER,
    evaluate_trace,
)
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402
from eval_ensemble import _ensemble_action_fn  # noqa: E402

EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
CKPT_DIRS = [
    ROOT / "results" / "td3_lstm_h64_s49",
    ROOT / "results" / "td3_lstm_h64_s51",
]
CONFIGS = [
    {"label": "hawe_lstm_mean",      "agg": "mean",     "weights": [0.5,  0.5 ]},
    {"label": "hawe_lstm_w90s51",    "agg": "weighted", "weights": [0.1,  0.9 ]},
    {"label": "hawe_lstm_w75s51",    "agg": "weighted", "weights": [0.25, 0.75]},
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
            f'  {r["label"]:25s} LS1={r["LS1"]:.3f} LS2={r["LS2"]:.3f} '
            f'geo={r["geo"]:.3f} | dM_sp%={r["dM_span_pct"]:.1f} '
            f'dD_u={r["dD_util"]:.3f}'
        )

    print()
    print("=== R57-β HAWE-LSTM ensemble (2-actor pool {s49, s51}) ===")
    best = max(rows, key=lambda r: r["geo"])
    print(f"  best config: {best['label']}  geo={best['geo']:.4f}")
    print()
    print("Reference (R56-α singles):")
    print("  s49 single = 0.333  (dM_sp 122%)")
    print("  s51 single = 0.526  (dM_sp 90%; current V4 single-seed SOTA)")
    print("  R48-δ HAWE MLP h=64 median = 0.351 (production ensemble)")

    summary = {
        "label": "r57_beta_hawe_lstm",
        "ckpt_dirs": [str(d) for d in CKPT_DIRS],
        "configs": rows,
        "best_label": best["label"],
        "best_geo": best["geo"],
    }
    out = ROOT / "results" / "research_loop" / "r57_beta_hawe_lstm.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
