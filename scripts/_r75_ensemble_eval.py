"""R75 ensemble eval — HAWE-style across healthy LSTM ckpts at warmup=20.

Uses ``andes_rl_kundur.evaluation.ensemble.build_ensemble_action_fn``
(recurrent-aware, R57-β patch).

Tests if averaging across multiple healthy ckpt actors yields a better
v3.1 controller than any single ckpt. Free (no training) — ANDES inference
only.

Configs:
1. **mean_5seed_warmup20**: uniform mean across 5 healthy seeds at warmup=20
2. **mean_top3_warmup20**: uniform mean across {s54, s55, s56} (top 3 by v3.1)
3. **weighted_s54_anchor**: 0.5 s54, 0.125 each of {s50, s52, s55, s56}
4. **mean_top2**: uniform mean of {s54, s55} (best 2 by v3.1)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.aggregation import floor_geo_mean  # noqa: E402
from andes_rl_kundur.evaluation.ensemble import build_ensemble_action_fn  # noqa: E402
from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

# Single source of truth for the single-seed v3.1 SOTA reference
# (CLM-0123, R73 W3 s54+warmup=20). Used to format the headline % delta.
SINGLE_SOTA_GEO_V31 = 0.4099

EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"

# 6 healthy seeds at warmup=20 (excluding s51 which collapses + drift {49,53,57,58,60})
# Ranked by individual v3.1: s59(0.4301) > s54(0.4099) > s55(0.3781) > s56(0.3763) > s50(0.3151) > s52(0.3068)
CKPT_DIRS_ALL = [
    ROOT / "results" / "r69_w3_lstm_tau001_warmup20_s50",        # s50  v3.1=0.3151
    ROOT / "results" / "r69_w6_lstm_tau001_warmup20_s52",        # s52  v3.1=0.3068
    ROOT / "results" / "r73_w3_lstm_tau001_warmup20_s54",        # s54  v3.1=0.4099
    ROOT / "results" / "r73_w6_lstm_tau001_warmup20_s55",        # s55  v3.1=0.3781
    ROOT / "results" / "r74_w2_lstm_tau001_warmup20_s56",        # s56  v3.1=0.3763
    ROOT / "results" / "r75_w2_lstm_tau001_warmup20_s59",        # s59  v3.1=0.4301 (NEW SOTA)
]
SEED_NAMES = ["s50", "s52", "s54", "s55", "s56", "s59"]

CONFIGS = [
    {"label": "r75_ensemble_mean_6seed_warmup20",
     "agg": "mean", "weights": [1/6] * 6},
    {"label": "r75_ensemble_mean_top3_s59_s54_s55",
     "agg": "mean", "weights": [0.0, 0.0, 1/3, 1/3, 0.0, 1/3]},  # s54, s55, s59
    {"label": "r75_ensemble_weighted_s59_anchor",
     "agg": "weighted", "weights": [0.1, 0.1, 0.2, 0.1, 0.1, 0.4]},  # s59 dominant
    {"label": "r75_ensemble_mean_top2_s59_s54",
     "agg": "mean", "weights": [0.0, 0.0, 0.5, 0.0, 0.0, 0.5]},  # s54+s59 only
]


def _eval_one_config(label: str, agg: str, weights: list[float]) -> dict:
    # Filter ckpts to non-zero weight only (saves load time for top-N configs)
    active_idx = [i for i, w in enumerate(weights) if w > 0]
    active_dirs = [CKPT_DIRS_ALL[i] for i in active_idx]
    active_weights = np.array([weights[i] for i in active_idx], dtype=np.float64)
    active_weights = active_weights / active_weights.sum()

    all_actors = [load_agents(cd, suffix="best") for cd in active_dirs]
    afn = build_ensemble_action_fn(all_actors, agg, active_weights)

    per_scen: dict[str, float] = {}
    per_scen_cum_rf: dict[str, float] = {}
    for scen_name, delta_u in SCENARIOS.items():
        rec = run_scenario(
            scen_name, delta_u,
            action_fn=afn,
            label=label, seed=42, steps=150,
        )
        out_path = EVAL_OUT / f"{label}_{scen_name}.json"
        out_path.write_text(json.dumps(rec), encoding="utf-8")
        ts = evaluate_trace(out_path, PAPER[scen_name], is_ddic=True, label=label)
        per_scen[scen_name] = ts.overall
        per_scen_cum_rf[scen_name] = compute_global_cum_rf(rec)

    ls1, ls2 = per_scen.get("load_step_1"), per_scen.get("load_step_2")
    geo = floor_geo_mean(per_scen.values())
    cum_rf_total = sum(per_scen_cum_rf.values())
    return {
        "label": label, "agg": agg,
        "active_seeds": [SEED_NAMES[i] for i in active_idx],
        "weights": active_weights.tolist(),
        "LS1": ls1, "LS2": ls2, "geo": geo,
        "cum_rf": cum_rf_total,
    }


def main() -> None:
    print(f"R75 ensemble eval — {len(CONFIGS)} configs across {len(CKPT_DIRS_ALL)} healthy ckpts\n")
    results = []
    for cfg in CONFIGS:
        print(f"[r75-ens] {cfg['label']} ({cfg['agg']}, weights={cfg['weights']})")
        r = _eval_one_config(cfg["label"], cfg["agg"], cfg["weights"])
        print(f"  → LS1={r['LS1']:.4f}  LS2={r['LS2']:.4f}  geo={r['geo']:.4f}  cum_rf={r['cum_rf']:.4f}")
        results.append(r)

    # Sort by geo desc
    results.sort(key=lambda x: -x["geo"])
    print("\n=== R75 ensemble ranking ===")
    print(f"{'rank':>4} {'label':38s} {'geo':>8} {'cum_rf':>8}  active_seeds")
    for i, r in enumerate(results, 1):
        marker = " <-- BEST" if i == 1 else ""
        print(f"{i:4d} {r['label']:38s} {r['geo']:8.4f} {r['cum_rf']:8.4f}  "
              f"{','.join(r['active_seeds'])}{marker}")

    # vs R73 W3 single SOTA
    print(f"\nSingle SOTA reference: R73 W3 s54+warmup=20 v3.1={SINGLE_SOTA_GEO_V31}")
    best_geo = results[0]["geo"]
    pct_delta = (best_geo - SINGLE_SOTA_GEO_V31) * 100 / SINGLE_SOTA_GEO_V31
    print(f"Best ensemble v3.1 = {best_geo:.4f}  ({pct_delta:+.1f}%)")

    out_path = EVAL_OUT / "r75_ensemble_summary.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()
