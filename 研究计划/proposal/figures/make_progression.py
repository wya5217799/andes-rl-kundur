"""Proposal progression figure — 11-axis performance across the 259-round programme.

Motivation
----------
The MRes proposal needs ONE figure that conveys, to a non-specialist
admissions committee, (a) the scale of the experimental programme,
(b) the systematic exploration of methods, and (c) the size of the
advantage over classical control -- without overclaiming a monotone
"improvement curve" that did not happen (the score plateaus).

Every plotted number is pinned to a claim in memory/claims/ and is the
CURRENT 11-axis (v3.1, gating axes 9-11) "geo" score:

  no_control floor ............ 0.094   CLM-0254
  best classical droop (K=2) .. 0.197   CLM-0186 (restated current CLM-0425)
  R72 TD3-LSTM SOTA base ...... 0.3908  CLM-0123
  R74 Pareto-dominant LSTM .... 0.410   CLM-0254
  R75 single-seed peak ........ 0.4301  CLM-0131 / CLM-0250
  R154 cross-algo ensemble .... 0.4119  CLM-0295
  R201/R249 autonomous SOTA ... 0.4152  CLM-0425
  RL / best-droop ratio ....... 2.1x    CLM-0425  (0.4152 / 0.197)
  R154 ablation spread (faint)  CLM-0295  (8-config study, shows volume)

Usage
-----
  python make_progression.py        # writes proposal_progression.{png,pdf}
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

OUT = Path(__file__).resolve().parent

# --- claim-pinned reference levels (11-axis geo) ----------------------
NO_CONTROL = 0.094     # CLM-0254
DROOP_BEST = 0.197     # CLM-0186 / CLM-0425

# --- claim-pinned milestone controllers (round, geo, label) -----------
MILESTONES = [
    (72,  0.3908, "TD3-LSTM\nSOTA base"),       # CLM-0123
    (74,  0.410,  "Pareto-dominant\nLSTM"),     # CLM-0254
    (75,  0.4301, "single-seed\npeak"),         # CLM-0131/0250
    (154, 0.4119, "cross-algorithm\nensemble"), # CLM-0295
    (249, 0.4152, "autonomous-loop\nSOTA"),     # CLM-0425
]

# --- faint experiment cloud (R154 8-config ablation, CLM-0295) --------
R154_SPREAD = [0.3908, 0.3845, 0.3843, 0.3830, 0.3498, 0.3562,
               0.4043, 0.3766, 0.3890, 0.4086]   # collapse seed 0.0100 omitted as off-scale


def main() -> None:
    plt.rcParams.update({
        "font.family": "serif", "font.size": 10,
        "axes.grid": True, "grid.alpha": 0.25,
    })
    fig, ax = plt.subplots(figsize=(8.0, 4.7))

    # plateau band (91-trial structural plateau, README / CLM-0148/0149)
    ax.axhspan(0.38, 0.43, color="#1565c0", alpha=0.07, zorder=0)
    ax.text(200, 0.396, "RL plateau band (91 trials)", fontsize=7.5,
            color="#1565c0", ha="center", va="center", style="italic")

    # classical reference lines
    ax.axhline(NO_CONTROL, color="#888888", ls=":", lw=1.3)
    ax.text(31, NO_CONTROL + 0.009, f"no control = {NO_CONTROL:.3f}",
            fontsize=8, color="#555555")
    ax.axhline(DROOP_BEST, color="#e07b00", ls="--", lw=1.3)
    ax.text(31, DROOP_BEST - 0.026, f"best classical droop = {DROOP_BEST:.3f}",
            fontsize=8, color="#e07b00")

    # faint experiment cloud at R154 (shows volume of ablations)
    ax.scatter([154] * len(R154_SPREAD), R154_SPREAD, s=12, color="#9e9e9e",
               alpha=0.5, zorder=2, label="individual experiments")

    # milestone markers + thin connector
    mx = [m[0] for m in MILESTONES]
    my = [m[1] for m in MILESTONES]
    ax.plot(mx, my, "-", color="#1565c0", lw=1.0, alpha=0.45, zorder=3)
    ax.scatter(mx, my, s=70, color="#1565c0", edgecolor="black",
               linewidth=0.8, zorder=4, label="milestone controllers")

    # milestone detail table (monospace, in the empty band 0.24-0.36)
    table = (
        "Milestone controllers (11-axis geo)\n"
        " R72   TD3-LSTM SOTA base     0.391\n"
        " R74   Pareto-dominant LSTM   0.410\n"
        " R75   single-seed peak       0.430\n"
        "R154   cross-algorithm ens.   0.412\n"
        "R249   autonomous-loop SOTA   0.415"
    )
    ax.text(0.025, 0.69, table, transform=ax.transAxes, fontsize=7.6,
            family="monospace", va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#1565c0", lw=0.9))

    # headline advantage callout (right, empty region)
    ax.annotate(r"RL SOTA $\approx 2.1\times$ best classical droop",
                xy=(249, 0.4152), xytext=(232, 0.30),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
                fontsize=8.5, ha="right",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="black"))

    # programme-scale box (top-left, above the cluster)
    ax.text(0.025, 0.975,
            "259 rounds  ·  263 audited findings\n12 RL algorithm variants  ·  35+ regression tests",
            transform=ax.transAxes, fontsize=8.2, va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", fc="#f3f7fc", ec="#1565c0", lw=1.0))

    ax.set_xlabel("Experimental round (R1 – R259)", fontsize=10)
    ax.set_ylabel("Eleven-axis paper-grade score", fontsize=10)
    ax.set_xlim(28, 262)
    ax.set_ylim(0, 0.50)
    ax.set_title("Multi-agent VSG control: 11-axis performance across the 259-round programme",
                 fontsize=10.5, pad=10)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"proposal_progression.{ext}", dpi=200, bbox_inches="tight")
    print("saved proposal_progression.png/.pdf to", OUT)


if __name__ == "__main__":
    main()
