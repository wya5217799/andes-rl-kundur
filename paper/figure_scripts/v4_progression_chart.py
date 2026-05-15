"""V4 Progression Chart — visualises Stage 2 ANDES improvement cascade.

Shows the methodology progression: no_control (baseline) → vanilla SAC attractor
(0.136) → warmstart-finetune (0.255) → ensemble (0.413, 0.439) → best-trained R21 (0.444).
Includes paper benchmark (1.0) as target. All scores POST-RANKER-FIX
(B1+B2+C1+C2 in evaluation/paper_grade_axes.py per r28/r30).

Output: paper/figures/v4_progression_chart.{png,pdf}
"""
from __future__ import annotations
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from plotting.paper_style import apply_ieee_style, save_fig  # noqa: E402

OUT = ROOT / "paper" / "figures"


def plot_progression():
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(8, 4.8))

    # Stages of progression — POST-RANKER-FIX scores (r28/r30; pre-fix
    # 0.110/0.137/0.419/0.554/0.607/0.613 retracted).
    stages = [
        ("no_control",      "no_control\n(reference)",        0.104, "#888888", "baseline"),
        ("vanilla_attr",    "Vanilla SAC\nattractor",          0.136, "#9e9e9e", "+31%"),
        ("ws8",             "Warmstart\nfinetune (ws8)",        0.255, "#2e7d32", "+145%"),
        ("ens85",           "Ensemble\n85/15 (R30)",            0.413, "#ff9800", "+297%"),
        ("ens98",           "Ensemble\n98/2 (R36)",             0.439, "#d32f2f", "+322%"),
        ("R21",             "R21 best-trained\n(BEST)",         0.444, "#1565c0", "+327%"),
        ("paper",           "Paper\nbenchmark",                 1.000, "#000000", "target"),
    ]

    x = np.arange(len(stages))
    scores = [s[2] for s in stages]
    colors = [s[3] for s in stages]
    labels = [s[1] for s in stages]
    annots = [s[4] for s in stages]

    bars = ax.bar(x, scores, color=colors, edgecolor="black", linewidth=0.9, width=0.7)

    # Add value + improvement annotation
    for i, (bar, score, annot) in enumerate(zip(bars, scores, annots)):
        ax.text(bar.get_x() + bar.get_width() / 2, score + 0.02,
                f"{score:.3f}", ha="center", fontsize=9, fontweight="bold")
        if i > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, score - 0.05,
                    f"({annot})", ha="center", fontsize=7.5, color="black",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.8))

    # Highlight R21 with star
    ax.text(5, 0.65, "★", fontsize=20, color="#1565c0", ha="center")
    ax.text(5, 0.69, "Best trained", fontsize=8, color="#1565c0", ha="center", fontweight="bold")

    # Paper benchmark dashed line
    ax.axhline(1.0, color="black", ls=":", lw=0.8, alpha=0.5)

    # Connect arrows showing progression
    for i in range(1, 6):  # stages 0→5 (excluding paper benchmark)
        arrow = FancyArrowPatch(
            (x[i-1] + 0.35, scores[i-1] + 0.005),
            (x[i] - 0.35, scores[i] + 0.005),
            arrowstyle='->,head_length=4,head_width=3',
            color='gray', alpha=0.5, lw=0.8,
            connectionstyle='arc3,rad=-0.15')
        ax.add_patch(arrow)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("6-axis paper-grade score", fontsize=10)
    ax.set_title("Stage 2 ANDES progression — from baseline to best-trained controller",
                 fontsize=10.5, pad=12)
    ax.set_ylim(0, 1.18)
    ax.grid(True, axis="y", alpha=0.3)

    # Annotate "4.27x over no-control" at top (post-fix multiplier;
    # pre-fix 5.57× retracted per r28).
    ax.annotate(r"$4.27\times$ over no\_control",
                xy=(5, 0.444), xytext=(5.0, 0.85),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.7),
                fontsize=8.5, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="black"))

    plt.subplots_adjust(bottom=0.18)
    save_fig(fig, OUT, "v4_progression_chart")
    plt.close(fig)
    print("  saved v4_progression_chart.png/.pdf")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    plot_progression()
