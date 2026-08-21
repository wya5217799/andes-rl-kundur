"""fig4_deterministic_bridge.pdf — R344 paired endpoint improvements.

Data: results/r344_deterministic_bridge/formal_execution.json#/records
      (16 scenarios x two arms: zero_control / frozen_controller; metrics
      common_coordinate_iae and differential_coordinate_energy), and
      results/r344_deterministic_bridge/formal_analysis.json#/paired_mean_improvement_fraction
      (sealed ratio-of-means reductions) and #/guards.
Transformation: per-scenario paired improvement fraction
      (zero - controlled) / zero for each endpoint.
Guards marked: 5% no-harm limit (no scenario may worsen either endpoint by
      more than 5%, i.e. fraction >= -0.05); sealed mean reduction lines.
"""

from plot_style import (apply_style, savefig, load_json, FULL_WIDTH,
                        BLUE, ORANGE, VERMILLION, BLACK)
import matplotlib.pyplot as plt
import numpy as np

apply_style()

exec_json = load_json("results/r344_deterministic_bridge/formal_execution.json")
analysis = load_json("results/r344_deterministic_bridge/formal_analysis.json")

records = exec_json["records"]
by_scen = {}
for rec in records:
    by_scen.setdefault(rec["scenario_id"], {})[rec["arm"]] = rec["metrics"]

scen_ids = sorted(by_scen.keys())
assert len(scen_ids) == 16

def short(sid):
    # development-style id: FVx__PQ_x__sign
    point, ch, sign = sid.split("__")
    return f"{point}/{ch.replace('PQ_','PQ').replace('Bus','B')}{'+' if sign=='positive' else '-'}"

short_ids = [short(s) for s in scen_ids]

def per_scenario_fraction(metric_key):
    out = []
    for sid in scen_ids:
        z = by_scen[sid]["zero_control"][metric_key]
        c = by_scen[sid]["frozen_controller"][metric_key]
        out.append((z - c) / z)
    return np.array(out)

frac_common = per_scenario_fraction("common_coordinate_iae")
frac_diff = per_scenario_fraction("differential_coordinate_energy")

sealed_common = analysis["paired_mean_improvement_fraction"]["common_coordinate_iae"]
sealed_diff = analysis["paired_mean_improvement_fraction"]["differential_coordinate_energy"]
guards = analysis["guards"]

fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.4), sharey=False)
x = np.arange(16)

for ax, frac, sealed, title in (
        (axes[0], frac_common, sealed_common,
         "(a) common-coordinate IAE"),
        (axes[1], frac_diff, sealed_diff,
         "(b) differential-coordinate energy")):
    colors = [BLUE if i < 8 else ORANGE for i in range(16)]
    bars = ax.bar(x, frac, width=0.72, color=colors, edgecolor="black",
                  linewidth=0.4)
    for i, b in enumerate(bars):
        if i >= 8:
            b.set_hatch("///")
    ax.axhline(0.0, color=BLACK, linewidth=0.6)
    ax.axhline(-0.05, color=VERMILLION, linewidth=0.9, linestyle="--")
    ax.text(15.5, -0.065, "5% no-harm limit", fontsize=6.5, color=VERMILLION,
            ha="right", va="top")
    ax.axhline(sealed, color=BLACK, linewidth=1.0, linestyle="-")
    ax.text(15.5, sealed, f" mean {sealed:.4f}", fontsize=6.5,
            ha="right", va="bottom", color=BLACK)
    ax.set_xticks(x)
    ax.set_xticklabels(short_ids, rotation=90, fontsize=6.5)
    ax.set_ylim(-0.14, 1.06)
    ax.set_title(title, fontsize=8)
    ax.set_ylabel("paired improvement fraction\n(zero - controlled) / zero")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)

fig.suptitle("R344 frozen centralized bridge vs paired zero control "
             "(16 scenarios, 2 operating points)",
             fontsize=8.5, y=1.02)
fig.text(0.5, -0.02,
         "5% no-harm guard: no scenario worsens either endpoint by >5% "
         "(guards.maximum_scenario_worsening=true);\n"
         "sealed mean reductions reproduced from formal_analysis.json"
         "#/paired_mean_improvement_fraction",
         ha="center", fontsize=6.5, color=BLACK)

savefig(fig, "fig4_deterministic_bridge.pdf")
plt.close(fig)
