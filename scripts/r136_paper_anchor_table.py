"""R136 — Paper-ready 5-anchor table + refreshed scatter figure.

Integrates R135 fresh-SOTA discovery (r75_baseline / r74_w3) with
R134 metric-divergence (r67_w2a degenerate cum_rf-top) and R112
warm-h_0 (degenerate inference) + no_control floor.

Output:
- results/r136_paper_anchor/{table.md, anchor_scatter.png, anchor_scatter.pdf,
  summary.json}
"""
from __future__ import annotations

import json
import math
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.evaluation.paper_grade_axes import evaluate_trace, PAPER  # noqa: E402
from andes_rl_kundur.evaluation.paper_strict_eval import compute_global_cum_rf  # noqa: E402


OUT_DIR = ROOT / "results" / "r136_paper_anchor"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 5 paper anchors: each entry = (label, LS1 trace, LS2 trace, role, is_ddic)
ANCHORS = [
    ("r74_w3_lstm_tau0007_warmup20_s54",
     "results/research_loop/eval_v4_baseline/r74_w3_lstm_tau0007_warmup20_s54_s54_load_step_1.json",
     "results/research_loop/eval_v4_baseline/r74_w3_lstm_tau0007_warmup20_s54_s54_load_step_2.json",
     "BEST-OF-BOTH (R135 candidate)", True),
    ("r75_baseline (s59)",
     "results/research_loop/eval_v4_baseline/r75_baseline_s59_load_step_1.json",
     "results/research_loop/eval_v4_baseline/r75_baseline_s59_load_step_2.json",
     "FRESH GEO SOTA (R135)", True),
    ("r72_w4_lstm_tau001_warmup5_s54 (declared SOTA)",
     "results/r112_warmh0_env_eval/traces/baseline_load_step_1.json",
     "results/r112_warmh0_env_eval/traces/baseline_load_step_2.json",
     "DECLARED SOTA", True),
    ("r67_w2a_td3_combo_tau001 (CUM_RF-TOP DEGENERATE)",
     "results/research_loop/eval_v4_baseline/r67_w2a_td3_combo_tau001_6axis_s50_load_step_1.json",
     "results/research_loop/eval_v4_baseline/r67_w2a_td3_combo_tau001_6axis_s50_load_step_2.json",
     "CUM_RF-TOP, GEO-DEGENERATE (R135 corrected)", True),
    ("warm-h_0 inference on R72_w4",
     "results/r112_warmh0_env_eval/traces/warmh0_load_step_1.json",
     "results/r112_warmh0_env_eval/traces/warmh0_load_step_2.json",
     "WARM-H_0 INFERENCE (R112)", True),
    ("no_control (floor)",
     "results/r80_v5_cross_eval/v4_baseline/no_control_load_step_1.json",
     "results/r80_v5_cross_eval/v4_baseline/no_control_load_step_2.json",
     "NO-CONTROL FLOOR", False),
]


def _score(label, p1, p2, is_ddic):
    p1, p2 = (Path(p1) if Path(p1).is_absolute() else ROOT / p1,
              Path(p2) if Path(p2).is_absolute() else ROOT / p2)
    if not p1.exists() or not p2.exists():
        return None
    ts1 = evaluate_trace(p1, PAPER["load_step_1"], is_ddic=is_ddic, label=label)
    ts2 = evaluate_trace(p2, PAPER["load_step_2"], is_ddic=is_ddic, label=label)
    vals = [max(ts1.overall, 0.01), max(ts2.overall, 0.01)]
    geo = math.exp(sum(math.log(v) for v in vals) / len(vals))
    cum_rf = sum(compute_global_cum_rf(json.loads(p.read_text())) for p in (p1, p2))
    return {
        "label": label,
        "LS1_geo": ts1.overall,
        "LS2_geo": ts2.overall,
        "geo": geo,
        "cum_rf": cum_rf,
        "ls1_path": str(p1),
        "ls2_path": str(p2),
    }


def main():
    rows = []
    print(f"R136: scoring {len(ANCHORS)} anchors\n")
    for label, p1, p2, role, is_ddic in ANCHORS:
        rec = _score(label, p1, p2, is_ddic)
        if rec is None:
            print(f"  MISSING: {label}")
            continue
        rec["role"] = role
        rows.append(rec)
        print(f"  {label[:50]:50s}  geo={rec['geo']:.4f}  cum_rf={rec['cum_rf']:+.4f}")

    # Markdown table
    lines = ["| Ckpt | Role | Fresh geo | cum_rf | Notes |", "|---|---|---|---|---|"]
    for r in rows:
        notes = []
        if "FRESH GEO SOTA" in r["role"]:
            notes.append("**new 11-axis SOTA**")
        if "DECLARED" in r["role"]:
            notes.append("project declared, but fresh #8")
        if "CUM_RF-TOP" in r["role"]:
            notes.append("warm-h_0-equivalent degenerate")
        if "WARM-H_0" in r["role"]:
            notes.append("inference test (CLM-0204)")
        if "FLOOR" in r["role"]:
            notes.append("zero-action baseline")
        if "BEST-OF-BOTH" in r["role"]:
            notes.append("Pareto-optimal joint metric")
        lines.append(f"| `{r['label'][:50]}` | {r['role']} | {r['geo']:.4f} | {r['cum_rf']:+.4f} | {'; '.join(notes)} |")
    (OUT_DIR / "table.md").write_text("\n".join(lines) + "\n")

    # Anchor scatter
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    role_color = {
        "BEST-OF-BOTH (R135 candidate)": ("tab:green", "*", 220, "r74_w3 BEST-OF-BOTH"),
        "FRESH GEO SOTA (R135)": ("tab:blue", "*", 220, "r75_baseline FRESH SOTA"),
        "DECLARED SOTA": ("tab:orange", "D", 150, "R72_w4 DECLARED SOTA"),
        "CUM_RF-TOP, GEO-DEGENERATE (R135 corrected)": ("tab:purple", "X", 150, "r67_w2a CUM_RF-TOP (degenerate)"),
        "WARM-H_0 INFERENCE (R112)": ("tab:red", "v", 140, "warm-h_0 (CLM-0204)"),
        "NO-CONTROL FLOOR": ("gray", "s", 120, "no_control"),
    }

    for r in rows:
        color, marker, size, leg = role_color.get(r["role"], ("black", "o", 100, r["role"]))
        ax.scatter(r["cum_rf"], r["geo"], c=color, marker=marker, s=size,
                   edgecolor="black", linewidth=0.6, label=leg, zorder=3)
        ax.annotate(r["label"][:25], (r["cum_rf"], r["geo"]),
                    xytext=(6, -4), textcoords="offset points", fontsize=7)

    ax.axhline(0.430, color="tab:blue", linewidth=0.5, linestyle=":", alpha=0.5)
    ax.axhline(0.391, color="tab:orange", linewidth=0.5, linestyle=":", alpha=0.5)
    ax.axvline(-0.031, color="tab:purple", linewidth=0.5, linestyle=":", alpha=0.5)
    ax.axvline(-0.068, color="tab:orange", linewidth=0.5, linestyle=":", alpha=0.5)

    ax.set_xlabel("cum_rf (paper §IV-C; less negative = better)")
    ax.set_ylabel("Fresh 11-axis geo (current paper_grade_axes)")
    ax.set_title("R136 — Paper anchor table for Sec.IV-D\n"
                 "5 representative ckpts in (cum_rf × geo) plane")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=7, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "anchor_scatter.png", dpi=180)
    fig.savefig(OUT_DIR / "anchor_scatter.pdf")
    print(f"\nsaved: table.md, anchor_scatter.png, .pdf")

    (OUT_DIR / "summary.json").write_text(json.dumps({"anchors": rows}, indent=2))


if __name__ == "__main__":
    main()
