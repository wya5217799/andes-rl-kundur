"""fig6_family_gates.pdf — R359-R362 information-family endpoint table.

Data:
  results/r359_neighbour_causal_residual/analysis.json#/development/gates/{nominal,mismatch_bounded}/endpoints
  results/r360_flexible_neighbour_residual/analysis.json#/development/family_gates/*/{nominal,mismatch_bounded}/endpoints
  results/r361_neighbour_message_residual/analysis.json#/development/family_gates/*/{nominal,mismatch_bounded}/endpoints
  results/r362_shared_prediction_residual/analysis.json#/development/family_gates/*/{nominal,mismatch_bounded}/endpoints
Transformation: paired_gate.mean_improvement_fraction (panel a, %) and
  paired_gate.mean_signed_relative_change (panel b, positive = worsening,
  log scale). R359 executed only the affine family, so its other three
  family cells are absent by design (no /development/family_gates key).
"""

from plot_style import (apply_style, savefig, load_json, FULL_WIDTH,
                        PALETTE, FAMILY_LABELS, HATCHES, LIGHT_GRAY,
                        BLACK, VERMILLION)
import matplotlib.pyplot as plt
import numpy as np

apply_style()

FAMILIES = ["affine", "rbf_kernel_ridge", "knn", "quadratic_polynomial"]
VARIANTS = [
    ("R359", "endpoint-local causal", "results/r359_neighbour_causal_residual/analysis.json", True),
    ("R360", "flexible families", "results/r360_flexible_neighbour_residual/analysis.json", False),
    ("R361", "one-hop state messages", "results/r361_neighbour_message_residual/analysis.json", False),
    ("R362", "shared predictions", "results/r362_shared_prediction_residual/analysis.json", False),
]
MODE = "nominal"

def get_endpoints(run_json):
    dev = run_json["development"]
    if "family_gates" in dev:
        out = {}
        for fam, famv in dev["family_gates"].items():
            out[fam] = famv[MODE]["endpoints"]
        return out
    # R359 stores the single affine-family gate directly under /development/gates
    return {"affine": dev["gates"][MODE]["endpoints"]}

common_imp = {}   # (variant, family) -> mean_improvement_fraction (common IAE)
diff_worse = {}   # (variant, family) -> mean_signed_relative_change (diff energy)
floor = None
for rlabel, sub, path, _affine_only in VARIANTS:
    data = load_json(path)
    eps = get_endpoints(data)
    for fam, ep in eps.items():
        pg_c = ep["common_coordinate_iae"]["paired_gate"]
        pg_d = ep["differential_coordinate_energy"]["paired_gate"]
        if floor is None:
            floor = pg_c["minimum_improvement_fraction"]
        common_imp[(rlabel, fam)] = pg_c["mean_improvement_fraction"]
        diff_worse[(rlabel, fam)] = pg_d["mean_signed_relative_change"]

fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.5),
                         gridspec_kw={"width_ratios": [1, 1]})

# ---- panel (a): common-coordinate improvement fraction (%) ----
ax = axes[0]
x = np.arange(len(VARIANTS))
n_fam = len(FAMILIES)
w = 0.18
for fi, fam in enumerate(FAMILIES):
    vals = []
    for vi in range(len(VARIANTS)):
        v = common_imp.get((VARIANTS[vi][0], fam))
        vals.append(v * 100.0 if v is not None else np.nan)
    offset = (fi - (n_fam - 1) / 2) * w
    bars = ax.bar(x + offset, vals, width=w * 0.92,
                  color=PALETTE[fam], edgecolor="black", linewidth=0.4,
                  hatch=HATCHES[fi % len(HATCHES)],
                  label=FAMILY_LABELS[fam])
    for b, v in zip(bars, vals):
        if np.isnan(v):
            b.set_facecolor(LIGHT_GRAY)
            b.set_hatch("...")
ax.axhline(floor * 100.0, color=VERMILLION, linewidth=0.9, linestyle="--")
ax.text(len(VARIANTS) - 0.5, floor * 100.0 + 0.05, "2% qualifying floor",
        fontsize=6.5, color=VERMILLION, ha="right", va="bottom")
ax.set_xticks(x)
ax.set_xticklabels([f"{r}\n{sub}" for r, sub, _, _ in VARIANTS], fontsize=6.5)
ax.set_ylim(-1.6, 3.2)
ax.set_ylabel("common-coordinate mean improvement fraction (%)")
ax.set_title("(a) common improvement, nominal endpoints", fontsize=8)
ax.axhline(0.0, color=BLACK, linewidth=0.6)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", alpha=0.25)
ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=6.5, ncol=2)

# ---- panel (b): differential-coordinate worsening (log scale) ----
ax = axes[1]
for fi, fam in enumerate(FAMILIES):
    vals = []
    for vi in range(len(VARIANTS)):
        v = diff_worse.get((VARIANTS[vi][0], fam))
        vals.append(v if v is not None else np.nan)
    offset = (fi - (n_fam - 1) / 2) * w
    bars = ax.bar(x + offset, vals, width=w * 0.92,
                  color=PALETTE[fam], edgecolor="black", linewidth=0.4,
                  hatch=HATCHES[fi % len(HATCHES)])
    for b, v in zip(bars, vals):
        if np.isnan(v):
            b.set_facecolor(LIGHT_GRAY)
            b.set_hatch("...")
ax.set_yscale("log")
ax.axhline(1.0, color=BLACK, linewidth=0.6)
ax.text(len(VARIANTS) - 0.5, 1.08, "no change (x1)", fontsize=6.5,
        ha="right", va="bottom", color=BLACK)
ax.set_xticks(x)
ax.set_xticklabels([f"{r}\n{sub}" for r, sub, _, _ in VARIANTS], fontsize=6.5)
ax.set_ylim(0.5, 2000)
ax.set_ylabel("differential-coordinate mean signed\nrelative change (worsening, log)")
ax.set_title("(b) differential worsening, nominal endpoints", fontsize=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", alpha=0.25, which="both")
ax.set_axisbelow(True)

fig.text(0.5, -0.02,
         "R359 ran only the affine family (gate at /development/gates, not "
         "/development/family_gates); missing cells are absent, not zero.\n"
         "All 16 executed family gates fail the 2% qualifying floor on the "
         "common coordinate.",
         ha="center", fontsize=6.5)

savefig(fig, "fig6_family_gates.pdf")
plt.close(fig)
