"""Compose 2x3 montage comparing Yang 2023 paper figures vs ANDES reproduction.

Reads six pre-rendered PNGs (3 from the paper figure folder, 3 from the
dissertation figures folder) and lays them out as a publication-grade 2-row
montage with row banners and per-subplot captions.

Output:
  dissertation/figures/fig_paper_vs_andes_comparison.png

Numbers in captions are post-r30 ranker fix (HAWE 0.439 = 99.3% R21,
no_ctrl 0.104). Pre-fix 0.110 / 0.554 / 0.607 / 0.613 are retracted.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

PAPER_DIR = Path(r"C:\Users\27443\Desktop\一切\论文\Figure.paper")
DISS_FIGS = Path(r"C:\Users\27443\Desktop\毕业论文\dissertation\figures")
OUT_PATH = DISS_FIGS / "fig_paper_vs_andes_comparison.png"

# Column 1: cumulative reward 50ep | Column 2: per-agent / system dynamics
# | Column 3: training curves
ROWS = (
    {
        "label": "(a) Yang 2023 [33] reference (Simulink, 2000 ep, single-seed)",
        "panels": (
            (
                PAPER_DIR / "5.png",
                "Fig. 5: Cum. reward (50 ep)\n"
                "no_ctrl=-15.2 / adapt=-12.93 / proposed=-8.04",
            ),
            (
                PAPER_DIR / "7.png",
                "Fig. 7: LS1 with proposed control\n"
                r"$\Delta H$ range $\sim$250, $\Delta D$ range $\sim$600",
            ),
            (
                PAPER_DIR / "4.png",
                "Fig. 4: Training curves (2000 ep)\n"
                "Total + ES1-ES4 episode reward",
            ),
        ),
    },
    {
        "label": "(b) This work — ANDES reproduction (Python, 500 ep, multi-seed)",
        "panels": (
            (
                DISS_FIGS / "fig5_cum_reward_50ep.png",
                "Cum. reward (50 ep, post-fix)\n"
                "no_ctrl=-3.7 / adapt=-1.06 / proposed=-0.94 (TIED)",
            ),
            (
                DISS_FIGS / "v4_per_agent_contribution_bars.png",
                r"Per-agent $\Delta H$ range — R21 best $\sim$0.2-3"
                "\n"
                r"vs paper $\sim$250 (lucky-basin no-action policy)",
            ),
            (
                DISS_FIGS / "fig4_training_curves.png",
                "Training curves (500 ep, 4x shorter)\n"
                "Total + ES1-ES4 episode reward",
            ),
        ),
    },
)

HEADLINE_BANNER = (
    "HAWE post-fix: 0.439 = 99.3% R21 = 5.52x no_ctrl (0.104)  |  "
    "Paper headline 1.89x cum_rf  |  6-axis geo-mean reveals "
    "single-axis cherry-pick"
)


def _load_image(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing source PNG: {path}")
    return mpimg.imread(path)


def compose() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 9,
            "axes.titlesize": 9,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.08,
        }
    )

    fig = plt.figure(figsize=(12.0, 8.6), dpi=300)
    gs = GridSpec(
        nrows=2,
        ncols=3,
        figure=fig,
        wspace=0.08,
        hspace=0.40,
        left=0.06,
        right=0.985,
        top=0.86,
        bottom=0.06,
    )

    for r_idx, row in enumerate(ROWS):
        for c_idx, (img_path, caption) in enumerate(row["panels"]):
            ax = fig.add_subplot(gs[r_idx, c_idx])
            ax.imshow(_load_image(img_path))
            ax.set_axis_off()
            ax.set_title(caption, fontsize=9, pad=4)

        # Row banner — vertical strip at far left, centred on the row band.
        y_band = 0.660 if r_idx == 0 else 0.260
        fig.text(
            0.018,
            y_band,
            row["label"],
            rotation=90,
            ha="center",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color="#222",
        )

    fig.suptitle(
        "Paper vs ANDES reproduction — three orthogonal views",
        fontsize=12.5,
        fontweight="bold",
        y=0.965,
    )
    fig.text(
        0.5,
        0.915,
        HEADLINE_BANNER,
        ha="center",
        va="top",
        fontsize=8.5,
        style="italic",
        color="#444",
        wrap=True,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH)
    plt.close(fig)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    compose()
