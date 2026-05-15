"""HAWE w9802 — paper Fig.6/8 style 2-panel (Delta P, Delta f) figure.

Generates a tight 2-panel figure matching the visual form factor of
Yang et al. 2023 Figs.6/8 so that the dissertation can render
paper-no-control vs our HAWE-with-control side-by-side at consistent
2-panel form.

Output:
    dissertation/figures/v4_ddic_v4_ens2_R21ws8_w9802/
        v4_ddic_load_step_1_2panel.png/.pdf
        v4_ddic_load_step_2_2panel.png/.pdf
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR  = Path(r"C:\Users\27443\Desktop\毕业论文\dissertation\figures") \
           / "v4_ddic_v4_ens2_R21ws8_w9802"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LABEL = "ddic_v4_ens2_R21ws8_w9802"
F_NOM = 50.0

# Paper Fig.6/8 colour scheme (pink/yellow/green/blue as ES1..ES4).
ES_COLORS = ["#E8548A", "#F5A623", "#36D7B7", "#3B7DD8"]
ES_LABELS = [r"$\Delta P_{es1}$", r"$\Delta P_{es2}$",
             r"$\Delta P_{es3}$", r"$\Delta P_{es4}$"]
ES_FREQ_LABELS = [r"$\Delta f_{es1}$", r"$\Delta f_{es2}$",
                  r"$\Delta f_{es3}$", r"$\Delta f_{es4}$"]


def _load(path: Path) -> dict:
    j = json.load(open(path))
    tr = j["traces"]
    t  = np.array([s["t"]            for s in tr], dtype=float)
    fz = np.array([s["freq_hz"]      for s in tr], dtype=float)
    P  = np.array([s["delta_P_es"]   for s in tr], dtype=float)
    return {"time": t - t[0], "freq_hz": fz, "P_es": P,
            "max_df": j["max_df"], "scenario": j["scenario"]}


def _apply_paper_style():
    plt.rcParams.update({
        "font.family":       "serif",
        "font.size":          9,
        "axes.titlesize":     9,
        "axes.labelsize":     9,
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "legend.fontsize":    7,
        "axes.linewidth":     0.8,
        "lines.linewidth":    1.2,
        "axes.grid":          True,
        "grid.linewidth":     0.4,
        "grid.linestyle":     ":",
        "grid.color":         "0.7",
    })


def plot_2panel(traj: dict, fig_label: str, out_stem: str,
                t_max: float = 15.0) -> None:
    """Render 2-panel (delta P, delta f) figure.

    t_max: x-axis upper bound, in seconds. Default 15.0 covers the
    0-6 s transient window used by Yang et al. 2023 Figs.6/8 plus the
    post-6 s convergence to the paper-target final-|Delta f| floor,
    reached by the ANDES quasi-static phasor backend at approximately
    10-15 s. The 15 s window is a compromise between paper-axis
    alignment (6 s) and full plateau visibility (~30 s).
    """
    _apply_paper_style()
    fig, axes = plt.subplots(2, 1, figsize=(4.5, 3.6), sharex=True)
    fig.subplots_adjust(left=0.16, right=0.96, top=0.96, bottom=0.13,
                        hspace=0.30)
    t = traj["time"]

    # (a) Delta P_es (MW). Convert from p.u. assuming S_base=100MVA per ESS.
    # We display as p.u. to keep units honest and to match the paper-faithful
    # action box of yang2023ddic Eq.12.
    ax = axes[0]
    P0 = traj["P_es"][0:1]
    for i in range(4):
        ax.plot(t, traj["P_es"][:, i] - P0[0, i], color=ES_COLORS[i],
                label=ES_LABELS[i], lw=1.2)
    ax.axhline(0, color="0.5", lw=0.4, ls="--")
    ax.set_ylabel(r"(a) $\Delta P_{es}$ (p.u.)", fontsize=9)
    ax.legend(loc="best", fontsize=7, ncol=2, frameon=True, framealpha=0.85)

    # (b) Delta f_es (Hz)
    ax = axes[1]
    for i in range(4):
        ax.plot(t, traj["freq_hz"][:, i] - F_NOM, color=ES_COLORS[i],
                label=ES_FREQ_LABELS[i], lw=1.2)
    ax.axhline(0, color="0.5", lw=0.4, ls="--")
    ax.set_ylabel(r"(b) $\Delta f_{es}$ (Hz)", fontsize=9)
    ax.set_xlabel("Time (s)", fontsize=9)
    ax.legend(loc="best", fontsize=7, ncol=2, frameon=True, framealpha=0.85)

    # Trim x-axis to paper-aligned window for direct visual comparison.
    for a in axes:
        a.set_xlim(0.0, t_max)

    # Save
    fig.savefig(OUT_DIR / f"{out_stem}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{out_stem}.pdf",          bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out_stem}.png/.pdf in {OUT_DIR}")


def main() -> None:
    print(f"[HAWE 2-panel] reading from {EVAL_DIR}, output -> {OUT_DIR}")
    for scen in ("load_step_1", "load_step_2"):
        path = EVAL_DIR / f"{LABEL}_{scen}.json"
        if not path.exists():
            print(f"  SKIP: {path.name} not found")
            continue
        traj = _load(path)
        plot_2panel(traj, fig_label=scen, out_stem=f"v4_ddic_{scen}_2panel")


if __name__ == "__main__":
    main()
