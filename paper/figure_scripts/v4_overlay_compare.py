"""V4 Overlay Comparison — multi-controller Δf / ΔP_es / max_df side-by-side.

Plots paper-quality 2-panel (LS1 left, LS2 right) figure showing Δf time-series
of N controllers overlaid (no_control + best ckpts) with paper benchmark dashed lines.

Output: paper/figures/v4_overlay_compare/{ls1,ls2}_df.{png,pdf}

Run: /home/wya/andes_venv/bin/python paper/figure_scripts/v4_overlay_compare.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from plotting.paper_style import apply_ieee_style, save_fig  # noqa: E402

EVAL = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT = ROOT / "paper" / "figures" / "v4_overlay_compare"
OUT.mkdir(parents=True, exist_ok=True)

# Controllers to overlay (label → (json_label, color, linestyle, plot_label, score)).
# Scores are POST-RANKER-FIX (B1+B2+C1+C2 in evaluation/paper_grade_axes.py per
# r28 / r30 verdicts); pre-fix 0.110/0.419/0.554/0.607/0.613 are retracted.
CONTROLLERS = [
    ("no_control", "#888888", "--", "No control", 0.104),
    ("ddic_v4_8_R21_best", "#2e7d32", "-", "ws8 (warmstart, 0.255)", 0.255),
    ("ddic_v4_ens2_R21ws8_w8515", "#ff9800", "-", "Ens 85/15 (0.413)", 0.413),
    ("ddic_v4_ens2_R21ws8_w9802", "#d32f2f", "-", "Ens 98/2 (0.439, ours)", 0.439),
    ("ddic_v4_h50_s49", "#1565c0", "-.", "R21 (single-seed, 0.444)", 0.444),
]

# Paper benchmark per scenario (from probes/andes_common/paper_constants.py)
PAPER_BENCH = {
    "load_step_1": {"max": 0.13, "final": 0.08, "settle": 3.0, "sign": +1.0},
    "load_step_2": {"max": 0.10, "final": 0.05, "settle": 2.5, "sign": -1.0},
}

F_NOM = 50.0


def load_traj(label: str, scen: str) -> dict | None:
    p = EVAL / f"{label}_{scen}.json"
    if not p.exists():
        return None
    j = json.load(open(p))
    tr = j["traces"]
    return {
        "t":         np.array([s["t"] for s in tr]),
        "freq_hz":   np.array([s["freq_hz"] for s in tr]),
        "max_df":    j.get("max_df", 0.0),
    }


def plot_overlay_df(scen: str, scen_label: str):
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bench = PAPER_BENCH[scen]

    for json_label, color, ls, plot_lbl, score in CONTROLLERS:
        traj = load_traj(json_label, scen)
        if traj is None:
            print(f"  SKIP: {json_label} not found")
            continue
        t = traj["t"] - traj["t"][0]
        # Mean across 4 ESS for cleanest comparison
        df_mean = (traj["freq_hz"] - F_NOM).mean(axis=1)
        ax.plot(t, df_mean, color=color, ls=ls, lw=1.5,
                label=f"{plot_lbl} | max|Δf|={traj['max_df']:.3f}Hz")

    # Paper benchmarks
    ax.axhline(bench["sign"] * bench["max"], color="black", lw=0.8, ls=":",
               label=f"paper max±{bench['max']}Hz", alpha=0.7)
    ax.axhline(bench["sign"] * bench["final"], color="black", lw=0.8, ls="--",
               label=f"paper final±{bench['final']}Hz", alpha=0.7)
    ax.axhline(0, color="gray", lw=0.4, ls=":")
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.25, zorder=-1)

    ax.set_xlabel("Time since disturbance (s)", fontsize=10)
    ax.set_ylabel(r"$\overline{\Delta f}$ (Hz, 4-ESS mean)", fontsize=10)
    ax.set_title(f"{scen_label} — Controller comparison (V4 paper-faithful ANDES)", fontsize=10)
    ax.legend(loc="best", fontsize=7.5, ncol=1, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    save_fig(fig, OUT, f"overlay_{scen}_df_mean")
    plt.close(fig)
    print(f"  saved overlay_{scen}_df_mean.png/.pdf")


def plot_score_summary():
    """Bar chart of 6-axis scores for top controllers."""
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.0))

    labels, scores, colors = [], [], []
    for json_label, color, ls, plot_lbl, score in CONTROLLERS:
        labels.append(plot_lbl.split(" |")[0].split(" (")[0])  # short label
        scores.append(score)
        colors.append(color)

    bars = ax.bar(labels, scores, color=colors, edgecolor="black", linewidth=0.8)
    for bar, s in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, s + 0.015,
                f"{s:.3f}\n({s/0.110:.2f}x)", ha="center", fontsize=8.5)

    ax.axhline(1.0, color="black", ls="--", lw=0.8, label="Paper (target)")
    ax.set_ylabel("6-axis score (mean LS1+LS2)", fontsize=10)
    ax.set_title("Controller comparison — paper-grade alignment scores", fontsize=10)
    ax.set_ylim(0, 1.1)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=15, ha="right", fontsize=9)
    plt.subplots_adjust(bottom=0.25)

    save_fig(fig, OUT, "score_bar_summary")
    plt.close(fig)
    print(f"  saved score_bar_summary.png/.pdf")


def main():
    print(f"[overlay] output → {OUT}")
    for scen, lbl in [("load_step_1", "LS1: Bus14 −2.48 p.u."),
                       ("load_step_2", "LS2: Bus15 +1.88 p.u.")]:
        plot_overlay_df(scen, lbl)
    plot_score_summary()
    print("[overlay] done.")


if __name__ == "__main__":
    main()
