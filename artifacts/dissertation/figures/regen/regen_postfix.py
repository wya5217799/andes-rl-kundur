"""Re-render Stage 2 figures with post-r30-fix scores for the dissertation.

Reads source trajectory JSONs from the project's Multi-Agent VSGs repo
(read-only) and writes new PNGs that overwrite the stale pre-fix versions
under dissertation/figures/.

Outputs:
  dissertation/figures/v4_overlay_compare/overlay_load_step_1_df_mean.png
  dissertation/figures/v4_overlay_compare/overlay_load_step_2_df_mean.png
  dissertation/figures/v4_per_agent_contribution_bars.png

Source: paper/figure_scripts/v4_overlay_compare.py + v4_per_agent_contribution_bars.py
Modifications:
  - ws8 score 0.255 (matches IEEE paper Table I + dissertation Table 3.x)
  - Bar-chart baseline 0.104 (post-fix no_control), not 0.110
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SRC_REPO = Path(r"C:\Users\27443\Desktop\Multi-Agent  VSGs")
sys.path.insert(0, str(SRC_REPO))
from plotting.paper_style import apply_ieee_style  # noqa: E402

EVAL = SRC_REPO / "results" / "research_loop" / "eval_v4_baseline"
DISS_FIGS = Path(r"C:\Users\27443\Desktop\毕业论文\dissertation\figures")
OVERLAY_OUT = DISS_FIGS / "v4_overlay_compare"
OVERLAY_OUT.mkdir(parents=True, exist_ok=True)

# Post-fix scores; pre-fix 0.110/0.419/0.554/0.607/0.613 are retracted.
CONTROLLERS = [
    ("no_control",                "#888888", "--", "No control",                 0.104),
    ("ddic_v4_8_R21_best",        "#2e7d32", "-",  "ws8 (warmstart, 0.255)",     0.255),
    ("ddic_v4_ens2_R21ws8_w8515", "#ff9800", "-",  "Ens 85/15 (0.413)",          0.413),
    ("ddic_v4_ens2_R21ws8_w9802", "#d32f2f", "-",  "Ens 98/2 (0.439, ours)",     0.439),
    ("ddic_v4_h50_s49",           "#1565c0", "-.", "R21 (single-seed, 0.444)",   0.444),
]

PAPER_BENCH = {
    "load_step_1": {"max": 0.13, "final": 0.08, "settle": 3.0, "sign": +1.0},
    "load_step_2": {"max": 0.10, "final": 0.05, "settle": 2.5, "sign": -1.0},
}

ES_NAMES = ["ES1\n(Bus12)", "ES2\n(Bus16)", "ES3\n(Bus14)", "ES4\n(Bus15)"]
F_NOM = 50.0


def load_traj(label: str, scen: str) -> dict | None:
    p = EVAL / f"{label}_{scen}.json"
    if not p.exists():
        return None
    j = json.load(open(p))
    tr = j["traces"]
    return {
        "t":         np.array([s["t"] for s in tr]),
        "freq_hz":   np.array([s["freq_hz"] for s in tr]),
        "delta_M":   np.array([s["delta_M"] for s in tr]),
        "max_df":    j.get("max_df", 0.0),
    }


def plot_overlay_df(scen: str, scen_label: str):
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    bench = PAPER_BENCH[scen]

    for json_label, color, ls, plot_lbl, score in CONTROLLERS:
        traj = load_traj(json_label, scen)
        if traj is None:
            print(f"  SKIP: {json_label} not found")
            continue
        t = traj["t"] - traj["t"][0]
        df_mean = (traj["freq_hz"] - F_NOM).mean(axis=1)
        short = plot_lbl.split(" (")[0]
        ax.plot(t, df_mean, color=color, ls=ls, lw=1.5,
                label=f"{short} | {traj['max_df']:.3f} Hz")

    ax.axhline(bench["sign"] * bench["max"], color="black", lw=0.8, ls=":",
               label=f"paper max {bench['max']} Hz", alpha=0.7)
    ax.axhline(bench["sign"] * bench["final"], color="black", lw=0.8, ls="--",
               label=f"paper final {bench['final']} Hz", alpha=0.7)
    ax.axhline(0, color="gray", lw=0.4, ls=":")
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.25, zorder=-1)

    ax.set_xlabel("Time since disturbance (s)", fontsize=10)
    ax.set_ylabel(r"$\overline{\Delta f}$ (Hz, 4-ESS mean)", fontsize=10)
    ax.set_title(f"{scen_label} — Controller comparison",
                 fontsize=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32),
              fontsize=7, ncol=2, framealpha=0.9, handlelength=2.0,
              columnspacing=1.0, borderaxespad=0.2)
    ax.tick_params(axis="both", labelsize=9)
    ax.grid(True, alpha=0.3)

    out = OVERLAY_OUT / f"overlay_{scen}_df_mean.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def get_dH_range(label: str, scen: str) -> np.ndarray | None:
    traj = load_traj(label, scen)
    if traj is None:
        return None
    dM = traj["delta_M"]
    dH = dM / 2.0
    return dH.max(axis=0) - dH.min(axis=0)


def plot_per_agent_bars():
    apply_ieee_style()
    fig, axes = plt.subplots(1, 2, figsize=(5.0, 2.7))

    legend_handles, legend_labels = [], []
    for ax_idx, scen in enumerate(["load_step_1", "load_step_2"]):
        ax = axes[ax_idx]
        scen_lbl = ("LS1: Bus 14 −2.48 p.u." if scen == "load_step_1"
                    else "LS2: Bus 15 +1.88 p.u.")

        data, labels, colors = [], [], []
        for json_lbl, color, _ls, plt_lbl, score in CONTROLLERS:
            r = get_dH_range(json_lbl, scen)
            if r is None:
                continue
            data.append(r)
            short_lbl = plt_lbl.split(" (")[0]
            labels.append(f"{short_lbl} ({score:.3f})")
            colors.append(color)

        data = np.array(data)
        n_ctrl = len(data)
        x = np.arange(4)
        width = 0.8 / n_ctrl

        for i in range(n_ctrl):
            offset = (i - (n_ctrl - 1) / 2) * width
            bars = ax.bar(x + offset, data[i], width, color=colors[i],
                          edgecolor="black", linewidth=0.5, label=labels[i])
            if ax_idx == 0:
                legend_handles.append(bars[0])
                legend_labels.append(labels[i])

        ax.set_xticks(x)
        ax.set_xticklabels(ES_NAMES, fontsize=8)
        ax.set_ylabel(r"$\Delta H$ range (s)", fontsize=9)
        ax.set_title(scen_lbl, fontsize=9)
        ax.set_yscale("log")
        ax.set_ylim(0.05, 100)
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(True, axis="y", which="both", alpha=0.3)

    fig.suptitle(
        r"Per-agent $\Delta H$ contribution: paper Fig.7 expects ES2 (Bus 16) to dominate LS1",
        fontsize=9, y=0.99)
    fig.legend(legend_handles, legend_labels, loc="lower center",
               bbox_to_anchor=(0.5, -0.02), ncol=5, fontsize=7,
               framealpha=0.92, handlelength=1.5, columnspacing=1.0)
    fig.tight_layout(rect=[0, 0.08, 1, 0.95])

    out = DISS_FIGS / "v4_per_agent_contribution_bars.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def main():
    print(f"[regen] reading source: {EVAL}")
    print(f"[regen] writing to: {DISS_FIGS}")
    for scen, lbl in [("load_step_1", "LS1: Bus14 −2.48 p.u."),
                      ("load_step_2", "LS2: Bus15 +1.88 p.u.")]:
        plot_overlay_df(scen, lbl)
    plot_per_agent_bars()
    print("[regen] done.")


if __name__ == "__main__":
    main()
