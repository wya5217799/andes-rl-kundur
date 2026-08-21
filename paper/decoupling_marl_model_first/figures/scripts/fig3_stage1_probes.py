"""fig3_stage1_probes.pdf — R312 signed-probe cross/self L2 gain ratios.

Data: results/r312_model_first_stage1/analysis.json#/pair_metrics
      (per-pair cross_gain, self_gain) and /max_all_nonlinearity_ratio.
Transformation: per-pair ratio cross_gain/self_gain, expressed in percent.
Annotation: observed range 1.11 % (OP2/edge_2) to 3.90 % (OP1/common).
"""

from plot_style import (apply_style, savefig, load_json, COLUMN_WIDTH,
                        BLUE, ORANGE, GRAY, HATCHES, BLACK)
import matplotlib.pyplot as plt
import numpy as np

apply_style()

r312 = load_json("results/r312_model_first_stage1/analysis.json")
pm = r312["pair_metrics"]

order = [f"OP{op}/{coord}" for op in range(3) for coord in
         ("common", "edge_0", "edge_1", "edge_2")]
ratios_pct = {p: pm[p]["cross_gain"] / pm[p]["self_gain"] * 100.0 for p in order}

vals = np.array([ratios_pct[p] for p in order])
is_common = np.array([p.endswith("/common") for p in order])

lo = float(vals.min())
hi = float(vals.max())
lo_pair = [p for p in order if ratios_pct[p] == lo][0]
hi_pair = [p for p in order if ratios_pct[p] == hi][0]

fig, ax = plt.subplots(figsize=(COLUMN_WIDTH, 2.15))

x = np.arange(len(order))
colors = np.where(is_common, BLUE, ORANGE)
hatches = np.where(is_common, "", "///")
bars = ax.bar(x, vals, width=0.72, color=colors, edgecolor="black",
              linewidth=0.4, hatch=list(hatches))
for b, common in zip(bars, is_common):
    if not common:
        b.set_hatch("///")

# observed-range band (1.11 % - 3.90 %)
ax.axhspan(lo, hi, color=GRAY, alpha=0.12, zorder=0)
ax.axhline(lo, color=GRAY, linewidth=0.5, linestyle="--", zorder=1)
ax.axhline(hi, color=GRAY, linewidth=0.5, linestyle="--", zorder=1)
ax.annotate(f"observed cross/self L2 range\n{lo:.2f}% - {hi:.2f}%",
            xy=(len(order) - 0.5, (lo + hi) / 2), xycoords="data",
            xytext=(len(order) - 0.45, 4.2), textcoords="data",
            fontsize=6.5, color=GRAY, ha="right", va="top")
ax.annotate(f"{ratios_pct[lo_pair]:.2f}%", xy=(order.index(lo_pair), lo),
            xytext=(0, -9), textcoords="offset points",
            ha="center", fontsize=6.5, color=BLACK)
ax.annotate(f"{ratios_pct[hi_pair]:.2f}%", xy=(order.index(hi_pair), hi),
            xytext=(0, 2), textcoords="offset points",
            ha="center", fontsize=6.5, color=BLACK)

ax.set_xticks(x)
ax.set_xticklabels([p.split("/")[1].replace("edge_", "e") for p in order],
                   fontsize=6.5)
for op in range(3):
    ax.text(op * 4 + 1.5, -0.62, f"OP{op}", ha="center", va="top",
            fontsize=7.5, color="black", fontweight="bold")
ax.set_xlim(-0.7, len(order) - 0.3)
ax.set_ylim(0, 4.6)
ax.set_ylabel("cross/self L2 gain ratio (%)")
ax.set_xlabel("signed-probe pair  (e0-e2 = differential edges)")

from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(facecolor=BLUE, edgecolor="black", label="common coordinate (c)"),
    Patch(facecolor=ORANGE, edgecolor="black", hatch="///", label="differential edges (e0-e2)"),
], loc="upper left", frameon=False, fontsize=6.5)

# non-linearity ceiling annotation from /max_all_nonlinearity_ratio
ax.text(0.0, 4.42, f"max midpoint nonlinearity ratio "
        f"{r312['max_all_nonlinearity_ratio']*100:.3f}%",
        fontsize=6.5, color=GRAY, va="top", ha="left")

for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", alpha=0.25)
ax.set_axisbelow(True)

savefig(fig, "fig3_stage1_probes.pdf")
plt.close(fig)
