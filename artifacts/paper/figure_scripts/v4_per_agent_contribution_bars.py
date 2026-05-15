"""V4 Per-Agent Contribution Bar Chart — paper-quality figure.

Visualizes ΔH range per ESS agent across top controllers, demonstrating that:
- R21 + w9802 reproduce paper Fig.7 ES2-dominant pattern
- ws8 (single warmstart) shows ES3 monopolization with 10x larger ranges
- Equal-Gini ensembles (w8515) lose performance

Output: paper/figures/v4_per_agent_contribution_bars.{png,pdf}
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
OUT = ROOT / "paper" / "figures"

# Controllers to plot (ordered by 6-axis score, dominant pattern).
# Scores are POST-RANKER-FIX (B1+B2+C1+C2 in evaluation/paper_grade_axes.py,
# applied 2026-05-07 per r28 / r30 verdicts). Pre-fix scores
# 0.110/0.419/0.554/0.607/0.613 are retracted; full re-rank in
# results/research_loop/r31_eval_v4_baseline_ranking.json.
CONTROLLERS = [
    ("no_control",                  "no\\_control",        "#888888", 0.104),
    ("ddic_v4_8_R21_best",          "ws8 (single)",         "#2e7d32", 0.255),
    ("ddic_v4_ens2_R21ws8_w8515",   "Ens 85/15",            "#ff9800", 0.413),
    ("ddic_v4_ens2_R21ws8_w9802",   "Ens 98/2 (FINAL)",     "#d32f2f", 0.439),
    ("ddic_v4_h50_s49",             "R21 (lucky)",          "#1565c0", 0.444),
]

ES_NAMES = ["ES1\n(Bus12)", "ES2\n(Bus16)", "ES3\n(Bus14)", "ES4\n(Bus15)"]


def get_dH_range(label: str, scen: str) -> np.ndarray | None:
    p = EVAL / f"{label}_{scen}.json"
    if not p.exists():
        return None
    j = json.load(open(p))
    tr = j["traces"]
    dM = np.array([s["delta_M"] for s in tr])  # (T, 4)
    dH = dM / 2.0
    return dH.max(axis=0) - dH.min(axis=0)  # per-agent range, shape (4,)


def gini(values: np.ndarray) -> float:
    if values.sum() == 0:
        return 0.0
    v = np.sort(values)
    n = len(v)
    cum = np.cumsum(v)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def plot_grouped_bars():
    apply_ieee_style()

    # 2-panel: LS1 + LS2
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.6))

    for ax_idx, scen in enumerate(["load_step_1", "load_step_2"]):
        ax = axes[ax_idx]
        scen_lbl = "LS1: Bus 14 −2.48 p.u." if scen == "load_step_1" else "LS2: Bus 15 +1.88 p.u."

        # Collect data
        data = []
        labels = []
        colors = []
        ginis = []
        for json_lbl, plt_lbl, color, score in CONTROLLERS:
            r = get_dH_range(json_lbl, scen)
            if r is None:
                continue
            data.append(r)
            labels.append(f"{plt_lbl}\n(0={score:.3f})")
            colors.append(color)
            ginis.append(gini(r))

        data = np.array(data)  # (n_ctrl, 4 agents)
        n_ctrl = len(data)
        n_agents = 4

        x = np.arange(n_agents)
        width = 0.8 / n_ctrl

        for i in range(n_ctrl):
            offset = (i - (n_ctrl - 1) / 2) * width
            bars = ax.bar(x + offset, data[i], width, color=colors[i],
                          edgecolor="black", linewidth=0.5,
                          label=labels[i])

        ax.set_xticks(x)
        ax.set_xticklabels(ES_NAMES, fontsize=8.5)
        ax.set_ylabel(r"$\Delta H$ range (s) over episode", fontsize=9)
        ax.set_title(f"{scen_lbl} — Per-agent inertia adjustment range", fontsize=9.5)

        # Use log scale because R21/w9802 use 0.2-3 while ws8 uses 15-45
        ax.set_yscale("log")
        ax.set_ylim(0.05, 100)
        ax.grid(True, axis="y", which="both", alpha=0.3)

        if ax_idx == 0:
            ax.legend(loc="upper left", fontsize=7, ncol=1, framealpha=0.92)

    fig.suptitle(
        "Per-agent $\\Delta H$ contribution — paper Fig.7 expects ES2 (Bus 16) to dominate LS1",
        fontsize=10, y=1.02)
    fig.tight_layout()

    save_fig(fig, OUT, "v4_per_agent_contribution_bars")
    plt.close(fig)
    print("  saved v4_per_agent_contribution_bars.png/.pdf")


def plot_gini_vs_score():
    """Secondary fig: scatter Gini ΔH vs 6-axis score, showing inequality correlation."""
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(5.5, 3.6))

    for scen, marker, scen_lbl in [("load_step_1", "o", "LS1"), ("load_step_2", "s", "LS2")]:
        for json_lbl, plt_lbl, color, score in CONTROLLERS:
            r = get_dH_range(json_lbl, scen)
            if r is None:
                continue
            g = gini(r)
            ax.scatter(g, score, s=80, color=color, marker=marker,
                       edgecolor="black", linewidth=0.7, alpha=0.85,
                       label=f"{plt_lbl} ({scen_lbl})" if scen == "load_step_1" else None)
            ax.annotate(plt_lbl.replace("\\_", "_").split(" (")[0],
                        (g, score), xytext=(5, 3), textcoords="offset points",
                        fontsize=7, color=color)

    ax.set_xlabel("Gini coefficient of per-agent $\\Delta H$ range  (0=equal, 1=monopoly)", fontsize=9)
    ax.set_ylabel("6-axis score (mean LS1+LS2)", fontsize=9)
    ax.set_title("Action distribution inequality vs paper-grade score", fontsize=9.5)
    ax.set_xlim(0.0, 0.6)
    ax.set_ylim(0.0, 0.7)
    ax.grid(True, alpha=0.3)

    # Annotation: the surprising finding
    ax.annotate("Counterintuitive:\nmore equal $\\Rightarrow$ lower score",
                xy=(0.26, 0.554), xytext=(0.05, 0.30),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.7),
                fontsize=8, color="black",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="gray", alpha=0.85))

    save_fig(fig, OUT, "v4_gini_vs_score")
    plt.close(fig)
    print("  saved v4_gini_vs_score.png/.pdf")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[per-agent fig] output → {OUT}")
    plot_grouped_bars()
    plot_gini_vs_score()


if __name__ == "__main__":
    main()
