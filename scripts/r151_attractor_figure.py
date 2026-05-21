"""R151 — Paper-ready Fig 9 attractor structure (2-panel).

Merges R139 (bimodal cluster density, CLM-0264) + R141 (per-algo
breakdown, CLM-0268) into a single paper-quality figure for Sec.IV-D.

Panel A (left): 2D scatter (cum_rf, geo) with cluster region shading
+ per-algo marker colour, key anchors annotated.

Panel B (right): per-algo cluster fraction stacked horizontal bars
showing 0/8 SAC+MLP reach LSTM SOTA.

Output: results/r151_attractor_figure/{fig9.png, fig9.pdf, summary.json}.
Zero ANDES.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "r151_attractor_figure"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _classify(label: str) -> str:
    l = label.lower()
    if "sac" in l: return "sac"
    if "transformer" in l: return "transformer"
    if "lstm" in l or "baseline" in l or "hawe" in l: return "td3_lstm"
    if "td3" in l or "paper" in l: return "td3_mlp"
    return "unknown"


def main() -> None:
    src = json.loads((ROOT / "results/r135_freshscore/summary.json").read_text())
    records = src["all_records"]
    for r in records:
        r["algo"] = _classify(r["label"])
        r["geo"] = float(r["geo"])
        r["cum_rf"] = float(r["cum_rf"])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    algo_colour = {
        "td3_lstm": "tab:blue",
        "sac": "tab:orange",
        "td3_mlp": "tab:green",
        "unknown": "lightgray",
        "transformer": "tab:purple",
    }
    algo_label = {
        "td3_lstm": "TD3+LSTM",
        "sac": "SAC",
        "td3_mlp": "TD3-MLP",
        "unknown": "unknown",
        "transformer": "Transformer",
    }

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.5),
                                    gridspec_kw={"width_ratios": [1.6, 1]})

    # ─── Panel A: scatter ─────────────────────────────────────────
    # Cluster region shading
    axA.axhspan(0.30, 0.50, color="tab:blue",  alpha=0.07, label="LSTM SOTA region")
    axA.axhspan(0.10, 0.30, color="gray",      alpha=0.05, label="Mid region")
    axA.axhspan(0.00, 0.10, color="tab:red",   alpha=0.07, label="Degenerate region")

    for algo in ["td3_lstm", "td3_mlp", "sac", "unknown"]:
        recs = [r for r in records if r["algo"] == algo]
        if not recs:
            continue
        x = [r["cum_rf"] for r in recs]
        y = [r["geo"] for r in recs]
        axA.scatter(x, y, s=24, c=algo_colour[algo], alpha=0.75,
                    edgecolor="black", linewidth=0.3,
                    label=f"{algo_label[algo]} (n={len(recs)})")

    # Anchor annotations
    anchors = {
        "r75_w2_lstm_tau001_warmup20_s59": ("R75 W2 s59\n(geo SOTA, CLM-0131)", "tab:blue"),
        "r72_w4_lstm_tau001_warmup5_s54": ("R72_w4\n(paper Fig 7\ncanonical CLM-0123)", "tab:blue"),
        "r67_w2a_td3_combo_tau001_6axis": ("r67_w2a\n(cum_rf SOTA, CLM-0118)", "tab:green"),
    }
    for r in records:
        if r["label"] in anchors:
            txt, _ = anchors[r["label"]]
            axA.annotate(txt, (r["cum_rf"], r["geo"]),
                         xytext=(8, 0), textcoords="offset points",
                         fontsize=7, va="center",
                         arrowprops=dict(arrowstyle="-", color="black", lw=0.4))

    axA.set_xlabel("cum_rf (paper §IV-C metric, less negative = better)")
    axA.set_ylabel("11-axis geo (project metric)")
    axA.set_title("Panel A — Bimodal attractor structure (N=91 ckpts)")
    axA.grid(True, alpha=0.3)
    axA.legend(loc="center right", fontsize=7, framealpha=0.9)

    # ─── Panel B: per-algo cluster fraction bars ─────────────────
    algos_ordered = ["td3_lstm", "td3_mlp", "sac"]
    bar_data = {}
    for algo in algos_ordered:
        recs = [r for r in records if r["algo"] == algo]
        n = len(recs)
        if n == 0:
            continue
        n_deg = sum(1 for r in recs if r["geo"] < 0.10)
        n_mid = sum(1 for r in recs if 0.10 <= r["geo"] <= 0.30)
        n_lstm = sum(1 for r in recs if r["geo"] > 0.30)
        bar_data[algo] = (n, n_deg, n_mid, n_lstm)

    ypos = np.arange(len(bar_data))
    labels = [f"{algo_label[a]} (n={bar_data[a][0]})" for a in bar_data]
    deg_pct = [100 * bar_data[a][1] / bar_data[a][0] for a in bar_data]
    mid_pct = [100 * bar_data[a][2] / bar_data[a][0] for a in bar_data]
    lstm_pct = [100 * bar_data[a][3] / bar_data[a][0] for a in bar_data]

    axB.barh(ypos, deg_pct,  color="tab:red",   alpha=0.6, label="Degenerate (geo<0.10)")
    axB.barh(ypos, mid_pct,  left=deg_pct, color="gray",  alpha=0.4, label="Mid (0.10-0.30)")
    axB.barh(ypos, lstm_pct,
             left=[d + m for d, m in zip(deg_pct, mid_pct)],
             color="tab:blue", alpha=0.7, label="LSTM SOTA (geo>0.30)")

    # Annotate fractions
    for i, a in enumerate(bar_data):
        if deg_pct[i] > 5:
            axB.text(deg_pct[i] / 2, i, f"{deg_pct[i]:.0f}%", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        if mid_pct[i] > 5:
            axB.text(deg_pct[i] + mid_pct[i] / 2, i, f"{mid_pct[i]:.0f}%", ha="center", va="center", fontsize=8)
        if lstm_pct[i] > 5:
            axB.text(deg_pct[i] + mid_pct[i] + lstm_pct[i] / 2, i, f"{lstm_pct[i]:.0f}%", ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    axB.set_yticks(ypos)
    axB.set_yticklabels(labels)
    axB.set_xlabel("% of evaluated ckpts in each cluster")
    axB.set_title("Panel B — Per-algo cluster reachability")
    axB.set_xlim(0, 100)
    axB.legend(loc="lower right", fontsize=8, framealpha=0.9)
    axB.grid(True, axis="x", alpha=0.3)

    fig.suptitle(
        "Fig. 9 — Bimodal attractor structure across 91 trained policies, "
        "LSTM SOTA cluster is algo-exclusive",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_DIR / "fig9.png", dpi=200)
    fig.savefig(OUT_DIR / "fig9.pdf")
    print(f"saved: fig9.png + fig9.pdf")

    # Summary JSON for provenance
    summary = {
        "round": "R151",
        "kind": "paper_fig9_attractor_structure",
        "n_records": len(records),
        "per_algo": {a: {"n": bar_data[a][0], "deg": bar_data[a][1],
                         "mid": bar_data[a][2], "lstm": bar_data[a][3]} for a in bar_data},
        "headline": "LSTM SOTA cluster algo-exclusive: 0/8 SAC+MLP reach geo>0.30",
        "sources": ["CLM-0264 (R139 bimodal)", "CLM-0268 (R141 algo breakdown)",
                    "CLM-0118 (multi-controller)", "CLM-0131 (R75 geo SOTA)",
                    "CLM-0123 (R72_w4 paper Fig 7 canonical)"],
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["per_algo"], indent=2))


if __name__ == "__main__":
    main()
