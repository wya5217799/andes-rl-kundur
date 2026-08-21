"""fig2_gate_sequence.pdf — flowchart of the fail-closed gate sequence
(fidelity contract -> canaries -> model gate -> deterministic bridge ->
headroom oracle -> information families -> basis ablation).

Schematic only: stage names and exit criteria follow the manuscript
argument contract (section 6) and the line feeds; no measurements plotted.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

from plot_style import apply_style, savefig, BLUE, ORANGE, GRAY, BLACK, VERMILLION, GREEN

apply_style()

fig = plt.figure(figsize=(5.6, 7.0))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

stages = [
    ("1  Fidelity contract",
     "equation-to-source reconciliation; device / base / limiter semantics "
     "frozen", "R306-R341"),
    ("2  Canaries",
     "Stage-0 zero-input canary + Stage-1 signed-authority probes",
     "R306, R309, R312"),
    ("3  Model gate",
     "finite fresh-bank predictor qualification",
     "R341"),
    ("4  Deterministic bridge",
     "paired endpoints improve vs zero control; 5% no-harm guard",
     "R344"),
    ("5  Headroom oracle",
     "outcome-seeing oracle vs 2% qualifying floor",
     "R350"),
    ("6  Information families",
     "affine / RBF / k-NN / quadratic x 4 information variants",
     "R359-R362"),
    ("7  Basis ablation",
     "common channel restores feasibility 10/16 -> 16/16",
     "R363"),
]

x0, w = 6, 56
y_top, h = 90.5, 8.4
gap = 1.6
box_bottom = y_top - (h + gap) * len(stages) + gap  # bottom of last box

def draw_box(y, title, sub, rounds):
    ax.add_patch(FancyBboxPatch((x0, y), w, h, boxstyle="round,pad=0.5",
                                facecolor="white", edgecolor=BLACK,
                                linewidth=1.1))
    ax.text(x0 + 2, y + h - 2.1, title, fontsize=8.5, fontweight="bold",
            ha="left", va="top")
    ax.text(x0 + 2, y + h - 4.9, sub, fontsize=6.5, ha="left", va="top",
            color=GRAY)
    ax.text(x0 + w - 1.5, y + 1.2, rounds, fontsize=6.5, ha="right",
            va="bottom", color=BLUE)
    # PASS badge (bottom)
    ax.text(x0 + w / 2, y - 0.5, "PASS", fontsize=6.5, ha="center",
            va="bottom", color=GREEN, fontweight="bold")

for i, (title, sub, rounds) in enumerate(stages):
    y = y_top - (h + gap) * i
    draw_box(y, title, sub, rounds)
    # FAIL branch to the right
    fy = y + h / 2
    ax.add_patch(FancyArrowPatch((x0 + w, fy), (x0 + w + 6, fy),
                                 arrowstyle="-|>", mutation_scale=11,
                                 linewidth=1.1, color=VERMILLION,
                                 linestyle=(0, (4, 2))))
    ax.text(x0 + w + 3, fy + 1.0, "FAIL", fontsize=6.5, ha="center",
            color=VERMILLION)
    stop = Circle((x0 + w + 9.5, fy), 2.6, facecolor=VERMILLION,
                  edgecolor="black", linewidth=0.8, zorder=5)
    ax.add_patch(stop)
    ax.text(x0 + w + 9.5, fy - 3.4, "stop", fontsize=5.5, ha="center",
            color=VERMILLION)
    # PASS arrow to the next stage
    if i < len(stages) - 1:
        ax.add_patch(FancyArrowPatch((x0 + w / 2, y - 0.4),
                                     (x0 + w / 2, y - gap + 0.4),
                                     arrowstyle="-|>", mutation_scale=13,
                                     linewidth=1.3, color=BLACK))

# start marker
ax.text(x0 + w / 2, box_bottom - 1.6, "frozen plant contract + sealed inputs",
        fontsize=6.5, ha="center", va="top", color=BLACK)
ax.add_patch(Circle((x0 + w / 2, box_bottom - 1.6 - 2.6), 2.2,
                    facecolor=GREEN, edgecolor="black", linewidth=0.8))
ax.text(x0 + w / 2, box_bottom - 1.6 - 2.6, "IN", fontsize=5.5, ha="center",
        va="center", color="white", fontweight="bold")

ax.text(50, 3.0,
        "Every gate is fail-closed and pre-registered: any guard failure stops "
        "the route and records a bounded verdict;\nno training, distributed "
        "runtime or eval is authorized until the final gate completes.",
        ha="center", fontsize=6.5, color=BLACK)

savefig(fig, "fig2_gate_sequence.pdf")
plt.close(fig)
