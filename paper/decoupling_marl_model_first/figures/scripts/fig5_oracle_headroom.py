"""fig5_oracle_headroom.pdf — R350 outcome-seeing oracle: per-scenario
improvements over the deterministic base, against the 2% qualifying floor.

Data: results/r350_smooth_convex_residual/analysis.json#/oracle
      (16 per-scenario records: base_endpoints, nominal_endpoints,
      scenario_id) and #/gates/oracle_nominal/endpoints (sealed mean /
      floor), #/gates/local_nominal/endpoints (neighbour-local means).
Transformation: per-scenario improvement fraction
      (base - nominal) / base per coordinate; mean-of-ratios reproduces the
      sealed /gates/oracle_nominal means exactly. The mean sits 1.7e-9
      fraction-units below the 0.02 floor (1.9999998% vs 2%).
"""

from plot_style import (apply_style, savefig, load_json, FULL_WIDTH,
                        BLUE, ORANGE, GREEN, PURPLE, VERMILLION, BLACK, GRAY)
import matplotlib.pyplot as plt
import numpy as np

apply_style()

r350 = load_json("results/r350_smooth_convex_residual/analysis.json")

oracle = r350["oracle"]
assert len(oracle) == 16

records = {}
for rec in oracle:
    records[rec["scenario_id"]] = rec

points = ["FV0", "FV1"]
channels = ["PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"]
signs = ["negative", "positive"]
order = [f"{p}__{c}__{s}" for p in points for c in channels for s in signs]


def short(sid):
    p, c, s = sid.split("__")
    return f"{p}/{c.replace('PQ_', 'PQ').replace('Bus', 'B')}"
    # sign omitted on purpose (both signs are identical at print precision)


frac = {}
for sid in order:
    b = records[sid]["base_endpoints"]
    n = records[sid]["nominal_endpoints"]
    frac[sid] = {
        "common": (b["common_coordinate_iae"] - n["common_coordinate_iae"])
                  / b["common_coordinate_iae"],
        "diff": (b["differential_coordinate_energy"]
                 - n["differential_coordinate_energy"])
                / b["differential_coordinate_energy"],
    }

common = np.array([frac[s]["common"] * 100.0 for s in order])
diff = np.array([frac[s]["diff"] * 100.0 for s in order])
x = np.arange(16)

sealed_mean_c = r350["gates"]["oracle_nominal"]["endpoints"]["common_coordinate_iae"]["mean_improvement_fraction"]
floor = r350["gates"]["oracle_nominal"]["endpoints"]["common_coordinate_iae"]["minimum_improvement_fraction"]
shortfall = floor - sealed_mean_c   # ~1.7e-9

CH_COLOR = {"PQ_0": BLUE, "PQ_1": ORANGE, "PQ_Bus14": GREEN, "PQ_Bus15": PURPLE}
CH_HATCH = {"PQ_0": "", "PQ_1": "///", "PQ_Bus14": "xxx", "PQ_Bus15": "\\\\"}
chan_of = {}
for i, sid in enumerate(order):
    chan_of[i] = sid.split("__")[1]

fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.5))

for ax, vals, title, ylim in (
        (axes[0], common, "(a) common-coordinate IAE", (0, 2.6)),
        (axes[1], diff, "(b) differential-coordinate energy", (0, 20))):
    colors = [CH_COLOR[chan_of[i]] for i in range(16)]
    hatches = [CH_HATCH[chan_of[i]] for i in range(16)]
    ax.bar(x, vals, width=0.72, color=colors, edgecolor="black",
           linewidth=0.4, hatch=hatches)
    ax.axhline(floor * 100.0, color=VERMILLION, linewidth=1.0, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels([short(s) for s in order], rotation=90, fontsize=6.5)
    ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    # FV0 / FV1 separator
    ax.axvline(7.5, color=BLACK, linewidth=0.5, linestyle=":")

axes[0].set_ylabel("per-scenario oracle improvement over\ndeterministic "
                   "base (%)   (base - nominal) / base")
axes[0].text(7.75, 2.48, "2% qualifying floor", fontsize=6.5,
             color=VERMILLION, ha="center")
axes[0].axhline(sealed_mean_c * 100.0, color=BLACK, linewidth=0.9)
axes[0].text(15.5, sealed_mean_c * 100.0 + 0.02, "mean 1.9999998%",
             fontsize=6.5, color=BLACK, ha="right", va="bottom")

# zoom inset: the 1.7e-9 shortfall
ins = axes[0].inset_axes([0.52, 0.10, 0.44, 0.55])
ins.bar([0.0], [sealed_mean_c * 100.0], width=0.5, color=BLACK,
        edgecolor="black", linewidth=0.5)
ins.axhline(floor * 100.0, color=VERMILLION, linewidth=1.2, linestyle="--")
ins.set_ylim((floor - 2.2e-9) * 100.0, (floor + 1.5e-9) * 100.0)
ins.set_xlim(-0.7, 0.7)
ins.set_xticks([])
ins.set_yticks([])
ins.text(-0.55, floor * 100.0, "floor 2.0000000%", fontsize=5, ha="left",
         va="bottom", color=VERMILLION)
ins.text(-0.55, sealed_mean_c * 100.0, "mean 1.9999998%", fontsize=5,
         ha="left", va="top", color=BLACK)
ins.annotate(f"shortfall\n{shortfall:.2e}", xy=(0.0, sealed_mean_c * 100.0),
             xytext=(0.62, (floor - 1.2e-9) * 100.0),
             fontsize=5.5, ha="left", va="center",
             arrowprops=dict(arrowstyle="->", lw=0.6, color=BLACK))
for s_ in ("top", "right"):
    ins.spines[s_].set_visible(False)

axes[1].set_ylabel("per-scenario oracle improvement over\ndeterministic "
                   "base (%)   (base - nominal) / base")
axes[1].text(7.75, 20.5, "PQ_Bus14 carries the only differential headroom "
             "(11-18%); other channels pin at the 2% bound",
             fontsize=6.5, ha="center", color=BLACK)

from matplotlib.patches import Patch
handles = [Patch(facecolor=CH_COLOR[c], edgecolor="black",
                 hatch=CH_HATCH[c],
                 label=c.replace("PQ_", "PQ").replace("Bus", "B"))
           for c in channels]
axes[0].legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.02),
               frameon=False, fontsize=6, ncol=4, title=None)

fig.text(0.5, -0.02,
         "Neighbour-local causal proxy means (V-B prose): 0.14% (common), "
         "-14.06% (differential) - /gates/local_nominal/endpoints.  "
         "Sealed oracle means reproduced from /gates/oracle_nominal/endpoints.",
         ha="center", fontsize=6.5, color=GRAY)

savefig(fig, "fig5_oracle_headroom.pdf")
plt.close(fig)
