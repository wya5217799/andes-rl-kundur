"""fig1_plant_contract.pdf — schematic of the four-node plant, its three
distinct graphs, and the three power layers (request -> command -> achieved).

Schematic only: all structural facts (node composition, graph edge sets,
B_a incidence, governor/projection and ESD1 semantics) come from
working/implemented_control_and_topology.md sections 2, 4, 5 and 6 and
working/model_contract.md; no measurements are plotted.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, FancyArrowPatch, Polygon
import matplotlib.patheffects as pe

from plot_style import apply_style, savefig, FULL_WIDTH, BLUE, ORANGE, GRAY, BLACK, GREEN, VERMILLION

apply_style()

fig = plt.figure(figsize=(FULL_WIDTH, 5.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

# --------------------------------------------------------------------------
# node geometry helpers
# --------------------------------------------------------------------------
NODE_POS = {1: (18, 80), 2: (40, 80), 3: (60, 80), 4: (82, 80)}
NODE_POS_SMALL = {1: (22, 52), 2: (45, 52), 3: (68, 52), 4: (85, 52)}
BUS = {1: "7", 2: "8", 3: "10", 4: "9"}
DEV_BUS = {1: "12", 2: "16", 3: "14", 4: "15"}
AREA = {1: 1, 2: 1, 3: 2, 4: 2}


def draw_node(ax_, i, pos, r=3.6, small=False):
    x, y = pos
    c = Circle((x, y), r, facecolor="white", edgecolor=BLACK, linewidth=1.1,
               zorder=5)
    ax_.add_patch(c)
    if small:
        ax_.text(x, y + 0.2, f"{i}", ha="center", va="center", fontsize=7,
                 fontweight="bold")
        ax_.text(x, y - r - 1.4, f"bus {BUS[i]}", ha="center", fontsize=6.5,
                 color=GRAY)
    else:
        ax_.text(x, y + 0.8, f"VSG$_{i}$", ha="center", va="center", fontsize=6.5,
                 fontweight="bold")
        ax_.text(x, y - 1.4, f"BESS$_{i}$", ha="center", va="center", fontsize=6.5)
        ax_.text(x, y - r - 1.8, f"bus {BUS[i]}  (dev. {DEV_BUS[i]})",
                 ha="center", fontsize=6.5, color=GRAY)


def draw_edge(ax_, i, j, pos, style="solid", color=BLACK, lw=1.4, zorder=3,
              arrow=False, arrow_color=None):
    x1, y1 = pos[i]
    x2, y2 = pos[j]
    if arrow:
        a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                            mutation_scale=10, linewidth=lw, color=arrow_color or color,
                            linestyle=style, zorder=zorder, shrinkA=5, shrinkB=5)
    else:
        a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-", linewidth=lw,
                            color=color, linestyle=style, zorder=zorder,
                            shrinkA=5, shrinkB=5)
    ax_.add_patch(a)


# --------------------------------------------------------------------------
# Band A: plant
# --------------------------------------------------------------------------
ax.text(2, 95.5, "a)  Modified two-area plant: four controllable nodes "
                 "(each = network bus + VSG proxy + storage plant)",
        fontsize=8.5, fontweight="bold")

for area, x0, x1 in ((1, 4, 49), (2, 51, 96)):
    ax.add_patch(FancyBboxPatch((x0, 66), x1 - x0, 22, boxstyle="round,pad=1",
                                facecolor="#F2F6FA", edgecolor=GRAY,
                                linewidth=0.8, linestyle="--"))
    ax.text((x0 + x1) / 2, 86.5, f"Area {area}", ha="center", fontsize=7,
            color=GRAY)

# electrical edges (stylized): within-area 1-2 and 3-4, inter-area tie 2-4
draw_edge(ax, 1, 2, NODE_POS, color=BLACK, lw=1.8)
draw_edge(ax, 3, 4, NODE_POS, color=BLACK, lw=1.8)
draw_edge(ax, 2, 4, NODE_POS, color=BLACK, lw=1.8)
ax.text(61, 88.6, "tie 8-9", fontsize=6.5, color=GRAY, rotation=38)
ax.text(29, 75.2, "G$_e$: installed network + radial links 7-12, 8-16, "
                  "10-14, 9-15", fontsize=6.5, color=GRAY, rotation=0,
        ha="center")

for i in range(1, 5):
    draw_node(ax, i, NODE_POS[i])

# wind proxy at bus 8 (node 2)
wx, wy = 47, 66
ax.add_patch(Polygon([(wx, wy), (wx + 5, wy), (wx + 2.5, wy + 5)],
                     closed=True, facecolor=GREEN, edgecolor=BLACK, lw=0.8))
ax.text(wx + 2.5, wy - 2, "wind", ha="center", fontsize=6.5, color=GREEN)

ax.text(50, 60.5, "underlying network: 4 x GENROU (IEEEG1 + EXST1); "
                  "4 x GENCLS VSG proxy (M=400, D=200); 4 x ESD1 storage "
                  "(36 MVA, 28 MWh)",
        ha="center", fontsize=6.5, color=BLACK)

# caught fidelity defect callout (MF-01): legacy 60/50 Hz labelling repair
ax.add_patch(FancyBboxPatch((5, 63.2), 90, 4.6, boxstyle="round,pad=0.4",
                            facecolor="#FDF3F3", edgecolor=VERMILLION,
                            linewidth=0.9))
ax.text(50, 66.0, "caught fidelity defect (MF-01): the legacy path labelled "
                  "the 60-Hz ANDES plant as 50 Hz;",
        ha="center", fontsize=6, color=VERMILLION)
ax.text(50, 64.2, "the contract makes the detected 60-Hz base the only "
                  "frequency base in harness, controllers, endpoints, traces",
        ha="center", fontsize=6, color=VERMILLION)

# --------------------------------------------------------------------------
# Band B: three graphs
# --------------------------------------------------------------------------
ax.text(2, 51.5, "b)  Three distinct graphs on the same four nodes "
                 "(G$_e$ $\\neq$ G$_c$ $\\neq$ G$_a$)",
        fontsize=8.5, fontweight="bold")

# G_e panel
for i in range(1, 5):
    draw_node(ax, i, NODE_POS_SMALL[i], small=True)
draw_edge(ax, 1, 2, NODE_POS_SMALL, lw=1.4)
draw_edge(ax, 2, 4, NODE_POS_SMALL, lw=1.4)
draw_edge(ax, 3, 4, NODE_POS_SMALL, lw=1.4)
ax.text(22, 42.5, "G$_e$ electrical", ha="center", fontsize=7, fontweight="bold")
ax.text(22, 40.2, "network + radial links", ha="center", fontsize=6.5,
        color=GRAY)

# G_c panel
draw_edge(ax, 1, 2, NODE_POS_SMALL, style="--", color=BLUE, lw=1.2)
draw_edge(ax, 2, 3, NODE_POS_SMALL, style="--", color=BLUE, lw=1.2)
draw_edge(ax, 3, 4, NODE_POS_SMALL, style="--", color=BLUE, lw=1.2)
draw_edge(ax, 1, 4, NODE_POS_SMALL, style="--", color=BLUE, lw=1.2)
for i in range(1, 5):
    draw_node(ax, i, NODE_POS_SMALL[i], small=True)
ax.text(45, 42.5, "G$_c$ communication ring", ha="center", fontsize=7,
        fontweight="bold", color=BLUE)
ax.text(45, 40.2, "E$_c$ = {(1,2),(2,3),(3,4),(1,4)}", ha="center", fontsize=6.5,
        color=GRAY)

# G_a panel
draw_edge(ax, 1, 2, NODE_POS_SMALL, arrow=True, color=ORANGE, lw=1.4)
draw_edge(ax, 2, 3, NODE_POS_SMALL, arrow=True, color=ORANGE, lw=1.4)
draw_edge(ax, 3, 4, NODE_POS_SMALL, arrow=True, color=ORANGE, lw=1.4)
for i in range(1, 5):
    draw_node(ax, i, NODE_POS_SMALL[i], small=True)
# B_a signs: edge e1=(1,2): +1 at 1, -1 at 2; e2=(2,3): +1 at 2, -1 at 3;
#            e3=(3,4): +1 at 3, -1 at 4
signs = {(1, 2): ("+1", "-1"), (2, 3): ("+1", "-1"), (3, 4): ("+1", "-1")}
for (i, j), (si, sj) in signs.items():
    xi, yi = NODE_POS_SMALL[i]
    xj, yj = NODE_POS_SMALL[j]
    ax.text((xi + xj) / 2 - 1.4, (yi + yj) / 2 + 2.6, si, fontsize=6.5,
            color=ORANGE, fontweight="bold", ha="center")
    ax.text((xi + xj) / 2 + 1.4, (yi + yj) / 2 + 2.6, sj, fontsize=6.5,
            color=ORANGE, fontweight="bold", ha="center")
ax.text(68, 42.5, "G$_a$ action tree (u$^d$ = B$_a$ r)", ha="center",
        fontsize=7, fontweight="bold", color=ORANGE)
ax.text(68, 40.2, "B$_a$ (rows = nodes, cols = edges):\n"
                  "[[1,0,0], [-1,1,0], [0,-1,1], [0,0,-1]]",
        ha="center", fontsize=6.5, color=GRAY)
ax.text(72, 34.2, "edge (1,4) communicates but is not an", ha="center",
        fontsize=6.5, color=GRAY)
ax.text(72, 32.0, "independent differential-action coordinate", ha="center",
        fontsize=6.5, color=GRAY)

# --------------------------------------------------------------------------
# Band C: three power layers
# --------------------------------------------------------------------------
ax.text(2, 27.5, "c)  Three power layers: the controller sets requests only",
        fontsize=8.5, fontweight="bold")

def layer_box(x, y, w, h, title, sub, color=BLACK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6",
                                facecolor="white", edgecolor=color, linewidth=1.2))
    ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center",
            fontsize=7.5, fontweight="bold", color=color)
    ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=6.5,
            color=GRAY)

y0, hb = 8.5, 14.5
layer_box(4, y0, 17, hb, "$p^\\star$", "request\nper node (R$^4$)", BLACK)
layer_box(27, y0, 20, hb, "$\\Pi_{\\mathcal{U}(k)}$", "projection:\n|p|, ramp, "
          "SOC, energy,\ncapability", BLUE)
layer_box(53, y0, 16, hb, "$p^{\\mathrm{cmd}}$", "command\n(projected)",
          BLACK)
layer_box(75, y0, 17, hb, "ESD1", "$T_{ip}\\dot I_p = I_p^{\\mathrm{cmd}} - I_p$\n"
          "$p^{\\mathrm{act}} = v\\, I_p$", GREEN)
layer_box(93.5, y0, 5, hb, "$p^{\\mathrm{act}}$", "achieved", BLACK)

# arrows between layers
for xa, xb in ((21, 27), (47, 53), (69, 75)):
    ax.add_patch(FancyArrowPatch((xa, y0 + hb / 2), (xb, y0 + hb / 2),
                                 arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.3, color=BLACK))
ax.add_patch(FancyArrowPatch((92, y0 + hb / 2), (93.5, y0 + hb / 2),
                             arrowstyle="-|>", mutation_scale=12, linewidth=1.3,
                             color=BLACK))
ax.text(50, 2.5,
        "request $\\neq$ command $\\neq$ achieved: ESD1 realizes the projected command through "
        "the active-current lag;\nedge governor caps |r$_e$| $\\leq$ 0.05 p.u. and "
        "|$\\Delta$r$_e$| $\\leq$ 0.05 p.u./step before projection",
        ha="center", fontsize=6.5, color=BLACK)

savefig(fig, "fig1_plant_contract.pdf")
plt.close(fig)
