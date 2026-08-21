"""Shared style and data-loading helpers for the decoupling-marl-model-first figures.

All plotted values are read verbatim from the sealed results JSONs under
`results/` (repo root is located via this file's own path, never via cwd).
Derived quantities are only the documented transformations (ratios, log,
percent scaling); nothing is re-simulated or invented.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[4]
FIGURES_DIR = ROOT / "paper" / "decoupling_marl_model_first" / "figures"

# --- colour-blind-safe Okabe-Ito palette (dual-encoded with hatches/markers) ---
BLUE = "#0072B2"        # common coordinate / oracle / affine
ORANGE = "#E69F00"      # edges / local / k-NN
GREEN = "#009E73"       # feasible / RBF
VERMILLION = "#D55E00"  # fail / worsening / quadratic
PURPLE = "#CC79A7"      # quadratic alternative / fourth family
SKY = "#56B4E9"         # secondary accent
BLACK = "#111111"
GRAY = "#8C8C8C"
LIGHT_GRAY = "#E6E6E6"

COLUMN_WIDTH = 3.50    # inches, IEEE single column
FULL_WIDTH = 7.16      # inches, IEEE double column

HATCHES = ["", "///", "xxx", "\\\\", "..."]

PALETTE = {
    "affine": BLUE,
    "rbf_kernel_ridge": GREEN,
    "knn": ORANGE,
    "quadratic_polynomial": VERMILLION,
}
FAMILY_LABELS = {
    "affine": "affine",
    "rbf_kernel_ridge": "RBF",
    "knn": "k-NN",
    "quadratic_polynomial": "quadratic",
}


def apply_style():
    plt.rcParams.update({
        "font.family": "STIXGeneral",
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.labelsize": 8.5,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.0,
        "grid.linewidth": 0.4,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.dpi": 300,
        "savefig.bbox": "tight",
    })


def load_json(rel_path: str):
    """Load a sealed results JSON relative to the repository root."""
    path = ROOT / rel_path
    if not path.is_file():
        raise FileNotFoundError(f"sealed data source not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def savefig(fig, name: str):
    out = FIGURES_DIR / name
    fig.savefig(out, format="pdf", bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    return out
