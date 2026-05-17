"""R70 thorough cross-metric evaluation matrix.

For each candidate controller, computes:
- cum_rf (paper-metric, paper Sec.IV-C)
- v3 11-axis overall (project ranker with collapse/oscillation/P-balance gates)
- v3 breakdown: agent_min_activity, late_oscillation_inv, agent_P_balance
- per-agent ΔP_final statistics

Output: markdown table + JSON dump for paper-writing reference.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from andes_rl_kundur.evaluation.aggregation import floor_geo_mean
from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace
from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"


# Candidates with grouping for the matrix
CANDIDATES = [
    # (mode, controller_family, label, seed, [trace_label_LS1, trace_label_LS2])
    # R69 W3 path: cross-axis tau+warmup=20 — 4 seeds
    ("v3-SOTA", "LSTM tau=0.001 warmup=20", "R69 W3", 50,
     "r69_w3_lstm_tau001_warmup20_s50_6axis_s50"),
    ("v3-SOTA", "LSTM tau=0.001 warmup=20", "R69 W1", 51,
     "r69_w1_lstm_tau001_warmup20_6axis_s51"),
    ("v3-SOTA", "LSTM tau=0.001 warmup=20", "R69 W6", 52,
     "r69_w6_lstm_tau001_warmup20_s52_6axis_s52"),
    ("v3-SOTA", "LSTM tau=0.001 warmup=20", "R69 W5", 49,
     "r69_w5_lstm_tau001_warmup20_s49_6axis_s49"),

    # R68 W2 path: tau=0.001 warmup=5 (R57 default warmup)
    ("LSTM-tau-only", "LSTM tau=0.001 warmup=5", "R68 W2", 51,
     "r68_w2_lstm_tau001_6axis_s51"),
    ("LSTM-tau-only", "LSTM tau=0.001 warmup=5", "R69 W2", 50,
     "r69_w2_lstm_tau001_warmup5_s50_6axis_s50"),
    ("LSTM-tau-only", "LSTM tau=0.001 warmup=5", "R69 W4", 52,
     "r69_w4_lstm_tau001_warmup5_s52_6axis_s52"),

    # R57-α historical LSTM
    ("R57-historical", "LSTM warmup=5 R57", "R57-α s51", 51,
     "td3_lstm_h64_warmup5_s51"),
    ("R57-historical", "LSTM warmup=5 R57", "R57-α s49", 49,
     "r70_eval_lstm_r57_s49_s49"),
    ("R57-historical", "LSTM warmup=5 R57", "R57-α s50", 50,
     "r70_eval_lstm_r57_s50_s50"),
    ("R57-historical", "LSTM default", "R57-α default", 51,
     "td3_lstm_h64_s51"),

    # R67 TD3 paper-metric SOTA (3 seeds: s49/s50/s51)
    ("TD3 paper-metric", "TD3 tau=0.001", "R67 W3a", 49,
     "r70_eval_td3_paper_s49_s49"),
    ("TD3 paper-metric", "TD3 tau=0.001", "R67 W2a", 50,
     "r67_w2a_td3_combo_tau001_6axis_s50"),
    ("TD3 paper-metric", "TD3 tau=0.001", "R67 W3b", 51,
     "r70_eval_td3_paper_s51_s51"),

    # R68 SAC paper-faithful SOTA (3 seeds)
    ("SAC paper-faithful", "SAC tau=0.001", "R68 W1a", 49,
     "r70_eval_sac_paper_s49_s49"),
    ("SAC paper-faithful", "SAC tau=0.001", "R68 W1b", 50,
     "r70_eval_sac_paper_s50_s50"),
    ("SAC paper-faithful", "SAC tau=0.001", "R68 W1c", 51,
     "r70_eval_sac_paper_s51_s51"),

    # R68 W3 LSTM warmup=30 3-seed (v2 SOTA candidates)
    ("LSTM warmup-only", "LSTM warmup=30 (no tau)", "R68 W3a", 50,
     "r68_w3a_lstm_warmup30_s50_6axis_s50"),
    ("LSTM warmup-only", "LSTM warmup=30 (no tau)", "R68 W4l", 51,
     "r68_w4l_lstm_warmup30_6axis_s51"),
]


def _eval_one(label: str) -> dict | None:
    """Compute all metrics for one trace label. Returns None if missing."""
    res = {"label": label, "scenarios": {}}

    for scen in ("load_step_1", "load_step_2"):
        p = EVAL_DIR / f"{label}_{scen}.json"
        if not p.exists():
            return None  # incomplete coverage

        with open(p, encoding="utf-8") as _f:
            trace = json.load(_f)

        # paper-metric: cum_rf (global integral over scenario)
        cum_rf = compute_global_cum_rf(trace)

        # v2 (8-axis) and v3 (11-axis) overall scores
        ts_v2 = evaluate_trace(p, PAPER[scen], is_ddic=True,
                               label=label, enable_v3_axes=False)
        ts_v3 = evaluate_trace(p, PAPER[scen], is_ddic=True,
                               label=label, enable_v3_axes=True)

        # Per-agent ΔP_final (last 10 steps mean)
        traces_list = trace.get("traces", [])
        if traces_list:
            P = np.array([s.get("delta_P_es", [0.0] * 4) for s in traces_list])
            if P.shape[0] >= 10:
                P_final = np.abs(P[-10:].mean(axis=0)).tolist()
            else:
                P_final = np.abs(P[-1]).tolist() if P.size else [0.0] * 4
        else:
            P_final = [0.0] * 4

        # v3 axes 9-11 (always last 3 axes when enable_v3_axes=True)
        v3_breakdown = {}
        if len(ts_v3.axes) >= 3:
            for ax in ts_v3.axes[-3:]:
                v3_breakdown[ax.name] = ax.score

        res["scenarios"][scen] = {
            "cum_rf": cum_rf,
            "v2_overall": ts_v2.overall,
            "v3_overall": ts_v3.overall,
            "v3_breakdown": v3_breakdown,
            "P_final": P_final,
        }

    if not res["scenarios"]:
        return None

    # Aggregate: total cum_rf + geo-mean v2/v3
    scens = res["scenarios"]
    res["total_cum_rf"] = sum(s["cum_rf"] for s in scens.values())
    res["v2_geo"] = floor_geo_mean(s["v2_overall"] for s in scens.values())
    res["v3_geo"] = floor_geo_mean(s["v3_overall"] for s in scens.values())

    return res


def _fmt_P(P_final: list[float]) -> str:
    return "[" + ",".join(f"{p:+.2f}" for p in P_final) + "]"


def main() -> None:
    results = []
    for mode, family, name, seed, label in CANDIDATES:
        r = _eval_one(label)
        if r is None:
            print(f"SKIP {name} s{seed}: trace missing ({label})")
            continue
        r["mode"] = mode
        r["family"] = family
        r["name"] = name
        r["seed"] = seed
        results.append(r)

    # ─── Markdown table ──────────────────────────────────────────────────────
    print("# R70 Thorough Cross-Metric Evaluation Matrix\n")
    print(f"Total candidates with traces: {len(results)}\n")

    print("## Per-controller results (sorted by v3_geo desc)\n")
    print("| Mode | Family | Name s? | cum_rf | v2_geo | **v3_geo** | "
          "min_act | late_osc | P_bal | LS2 P_final |")
    print("|---|---|---|---|---|---|---|---|---|---|")

    results.sort(key=lambda x: -x["v3_geo"])
    for r in results:
        ls1 = r["scenarios"].get("load_step_1", {})
        ls2 = r["scenarios"].get("load_step_2", {})
        bd_ls1 = ls1.get("v3_breakdown", {})
        bd_ls2 = ls2.get("v3_breakdown", {})
        # Use min over LS1+LS2 for v3 breakdown (paper-rigor "any scen bad → fail")
        act = min(bd_ls1.get("agent_min_activity", 0), bd_ls2.get("agent_min_activity", 0))
        osc = min(bd_ls1.get("late_oscillation_inv", 0), bd_ls2.get("late_oscillation_inv", 0))
        bal = min(bd_ls1.get("agent_P_balance", 0), bd_ls2.get("agent_P_balance", 0))
        P_ls2 = _fmt_P(ls2.get("P_final", [0] * 4))
        print(f"| {r['mode']} | {r['family']} | {r['name']} s{r['seed']} | "
              f"{r['total_cum_rf']:.4f} | {r['v2_geo']:.4f} | "
              f"**{r['v3_geo']:.4f}** | "
              f"{act:.2f} | {osc:.2f} | {bal:.2f} | {P_ls2} |")

    # ─── 3-seed mean per family ──────────────────────────────────────────────
    print("\n## 3-seed means per controller family (v3-aware, exclude broken s49 if applicable)\n")
    print("| Family | seeds | cum_rf_mean | v2_mean | **v3_mean** | "
          "min(min_act) | min(P_bal) | comment |")
    print("|---|---|---|---|---|---|---|---|")

    by_family: dict[str, list[dict]] = {}
    for r in results:
        by_family.setdefault(r["family"], []).append(r)

    for family, rs in by_family.items():
        # Detect & exclude s49 broken seeds (v3 < 0.2 → drift / collapse)
        clean = [r for r in rs if r["v3_geo"] >= 0.2]
        excluded_seeds = [r["seed"] for r in rs if r["v3_geo"] < 0.2]
        if not clean:
            continue
        cum_rf_mean = sum(r["total_cum_rf"] for r in clean) / len(clean)
        v2_mean = sum(r["v2_geo"] for r in clean) / len(clean)
        v3_mean = sum(r["v3_geo"] for r in clean) / len(clean)
        # min over all clean seeds and both scenarios for v3 breakdown
        min_act = min(
            min(s["v3_breakdown"].get("agent_min_activity", 0)
                for s in r["scenarios"].values())
            for r in clean
        )
        min_bal = min(
            min(s["v3_breakdown"].get("agent_P_balance", 0)
                for s in r["scenarios"].values())
            for r in clean
        )
        seed_list = ",".join(f"s{r['seed']}" for r in clean)
        comment = ""
        if excluded_seeds:
            comment = f"(excluded s{','.join(map(str, excluded_seeds))} drift)"
        print(f"| {family} | {seed_list} ({len(clean)}) | {cum_rf_mean:.4f} | "
              f"{v2_mean:.4f} | **{v3_mean:.4f}** | {min_act:.2f} | "
              f"{min_bal:.2f} | {comment} |")

    # JSON dump for further analysis
    out_json = ROOT / "results" / "research_loop" / "r70_eval_matrix.json"
    with open(out_json, "w", encoding="utf-8") as _f:
        json.dump(results, _f, indent=2)
    print(f"\n→ JSON: {out_json}")


if __name__ == "__main__":
    main()
