"""fig7_common_channel.pdf — R363 feasibility expansion on the exposed
development bank: three-edge basis (R358) vs four-channel basis (R363),
with the R356 cone-relaxation status as the relaxed reference row.

Data:
  results/r356_joint_endpoint_feasibility/analysis.json#/development_results
      (per-case status: optimal / primal infeasible)
  results/r358_physical_joint_endpoint_qp/analysis.json#/candidate_results,
      #/inherited_relaxed_infeasible_scenario_ids,
      #/accepted_physical_feasible_candidate_count,
      #/inherited_relaxed_infeasible_count
  results/r363_common_channel_qp/analysis.json#/common_channel_results,
      #/feasible_count, #/r358_baseline_feasible_count,
      #/newly_feasible_scenario_ids
Transformation: per-case feasible/infeasible boolean per gate; no values
  are re-computed.
"""

from plot_style import (apply_style, savefig, load_json, FULL_WIDTH,
                        GREEN, LIGHT_GRAY, ORANGE, BLACK, GRAY)
import matplotlib.pyplot as plt
import numpy as np

apply_style()

r356 = load_json("results/r356_joint_endpoint_feasibility/analysis.json")
r358 = load_json("results/r358_physical_joint_endpoint_qp/analysis.json")
r363 = load_json("results/r363_common_channel_qp/analysis.json")

# column order: FV0 then FV1; PQ_0, PQ_1, PQ_Bus14, PQ_Bus15; negative, positive
points = ["FV0", "FV1"]
channels = ["PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15"]
signs = ["negative", "positive"]
scen_ids = [f"development__{p}__{c}__{s}" for p in points
            for c in channels for s in signs]
short_labels = [f"{p}/{c.replace('PQ_', 'PQ').replace('Bus', 'B')}"
                f"{'+' if s == 'positive' else '-'}"
                for p in points for c in channels for s in signs]

def bools_from_records(run_json, status_key="status", feasible_status=("optimal",)):
    statuses = {}
    for rec in run_json["development_results"]:
        statuses[rec["scenario_id"]] = rec[status_key]
    return [statuses.get(sid, "missing") in feasible_status for sid in scen_ids]

r356_feas = bools_from_records(r356)
r358_feas = [sid in {c["scenario_id"] for c in r358["candidate_results"]}
             for sid in scen_ids]
r363_feas = [sid in {c["scenario_id"] for c in r363["common_channel_results"]
                     if c.get("accepted", False)} for sid in scen_ids]

newly = set(r363["newly_feasible_scenario_ids"])
assert r363["feasible_count"] == 16
assert r363["r358_baseline_feasible_count"] == 10
assert r358["accepted_physical_feasible_candidate_count"] == 10
assert r358["inherited_relaxed_infeasible_count"] == 6

rows = [
    ("R356 cone relaxation", r356_feas, f"{sum(r356_feas)}/16"),
    ("R358 three-edge physical QP", r358_feas, f"{sum(r358_feas)}/16"),
    ("R363 four-channel QP", r363_feas, f"{sum(r363_feas)}/16"),
]

fig, ax = plt.subplots(figsize=(FULL_WIDTH, 2.35))

n_cols = len(scen_ids)
cell = 1.0
for r, (label, feas, count) in enumerate(rows):
    for c, (ok, sid) in enumerate(zip(feas, scen_ids)):
        x0, y0 = c * cell, (len(rows) - 1 - r) * cell
        face = GREEN if ok else LIGHT_GRAY
        hatch = "" if ok else "///"
        edge = "black"
        lw = 0.5
        if ok and sid in newly:
            edge = ORANGE
            lw = 2.2
        rect = plt.Rectangle((x0, y0), cell - 0.06, cell - 0.06,
                             facecolor=face, edgecolor=edge, linewidth=lw,
                             hatch=hatch)
        ax.add_patch(rect)
        if ok and sid in newly:
            ax.text(x0 + 0.5, y0 + 0.5, "*", ha="center", va="center",
                    fontsize=9, color=ORANGE, fontweight="bold")
    ax.text(n_cols + 0.15, (len(rows) - 1 - r) * cell + 0.5, count,
            ha="left", va="center", fontsize=9, fontweight="bold")

ax.set_xlim(-0.4, n_cols + 1.4)
ax.set_ylim(-1.2, len(rows) * cell + 0.2)
ax.set_xticks(np.arange(n_cols) + 0.5)
ax.set_xticklabels(short_labels, rotation=90, fontsize=6.5)
ax.set_yticks(np.arange(len(rows)) * cell + 0.5)
ax.set_yticklabels([label for label, _, _ in rows], fontsize=7.5)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)

# point-group separators
for c in (8, 16):
    ax.axvline(c * cell - 0.03, color=BLACK, linewidth=0.6, linestyle=":")
ax.text(4.0, -0.85, "FV0", ha="center", fontsize=7, fontweight="bold")
ax.text(12.0, -0.85, "FV1", ha="center", fontsize=7, fontweight="bold")

# legend
from matplotlib.patches import Patch
handles = [
    Patch(facecolor=GREEN, edgecolor="black", label="feasible"),
    Patch(facecolor=LIGHT_GRAY, edgecolor="black", hatch="///",
          label="infeasible"),
    Patch(facecolor=GREEN, edgecolor=ORANGE, linewidth=2.2,
          label="newly feasible in R363 (*)"),
]
ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.02),
          frameon=False, fontsize=6.5, ncol=1)

ax.text(-0.4, -1.55,
        "R358: 10 feasible / 6 inherited relaxed-infeasible;  R363: 16/16 "
        "with common channel (headroom_expanded=true).\n"
        "Newly feasible: FV0/PQ0- , FV0/PQ0+ , FV0/PQ1- , FV0/PQ1+ , "
        "FV1/PQ1- , FV1/PQ1+ .",
        fontsize=6.5, color=BLACK, ha="left")

savefig(fig, "fig7_common_channel.pdf")
plt.close(fig)
