"""V4 DDIC ckpt Fig.7/9 plot — paper-style 4-panel.

Reads V4 trained ddic trace JSON from `results/research_loop/eval_v4_baseline/`,
plots paper Fig.7/9 (DDIC LS1/LS2) format: Δf, ΔP_es, ΔH (with Havg dashed),
ΔD (with Davg dashed).

Output: paper/figures/v4_ddic_<label>/ls{1,2}.png + .pdf

Run: PAPER_FIG_DDIC_LABEL=ddic_v4_h50_s49 python paper/figure_scripts/v4_ddic_fig7_9.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from plotting.paper_style import (  # noqa: E402
    apply_ieee_style,
    ES_COLORS_4,
    ES_FREQ_LABELS_4,
    save_fig,
)
from probes.andes_common import PAPER_FIG6, PAPER_FIG8  # noqa: E402

LABEL = os.environ.get("PAPER_FIG_DDIC_LABEL", "ddic_v4_h50_s49")
EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR = ROOT / "paper" / "figures" / f"v4_{LABEL}"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path) -> dict:
    j = json.load(open(path))
    tr = j["traces"]
    return {
        "time":    np.array([s["t"] for s in tr]),
        "freq_hz": np.array([s["freq_hz"] for s in tr]),
        "P_es":    np.array([s["delta_P_es"] for s in tr]),
        "M_es":    np.array([s["M_es"] for s in tr]),
        "D_es":    np.array([s["D_es"] for s in tr]),
        "max_df":  j["max_df"],
        "scenario": j["scenario"],
    }


def plot_4panel_ddic(traj: dict, paper_bench, scen_label: str, out_name: str):
    """4-panel paper Fig.7/9 style: Δf | ΔP | ΔH (with Havg dashed) | ΔD (with Davg dashed)."""
    apply_ieee_style()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.0))
    fig.subplots_adjust(hspace=0.45, wspace=0.34, left=0.08, right=0.97, top=0.92, bottom=0.10)

    t = traj["time"] - traj["time"][0]
    fn = 50.0
    sign = +1.0 if "step_1" in traj["scenario"] else -1.0

    H_es = traj["M_es"] / 2.0
    D_es = traj["D_es"]
    H_avg = H_es.mean(axis=1)
    D_avg = D_es.mean(axis=1)

    # (a) Δf with paper benchmark
    ax = axes[0, 0]
    for i in range(4):
        ax.plot(t, traj["freq_hz"][:, i] - fn, color=ES_COLORS_4[i], lw=1.2, label=ES_FREQ_LABELS_4[i])
    ax.axhline(sign * paper_bench.max_abs_df_Hz, color="black", lw=0.9, ls=":",
               label=f"paper max±{paper_bench.max_abs_df_Hz}Hz")
    ax.axhline(sign * paper_bench.final_abs_df_Hz, color="black", lw=0.9, ls="--",
               label=f"paper final±{paper_bench.final_abs_df_Hz}Hz")
    ax.axhline(0, color="gray", lw=0.5, ls="--")
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"$\Delta f$ (Hz)", fontsize=9)
    ax.set_xlabel("(a) Time since disturbance (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6.5, ncol=2)

    # (b) ΔP_es
    ax = axes[0, 1]
    for i in range(4):
        ax.plot(t, traj["P_es"][:, i] - traj["P_es"][0, i], color=ES_COLORS_4[i], lw=1.2,
                label=fr"$\Delta P_{{es{i+1}}}$")
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"$\Delta P_{\rm es}$ (p.u.)", fontsize=9)
    ax.set_xlabel("(b) Time since disturbance (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6.5, ncol=2)

    # (c) ΔH
    ax = axes[1, 0]
    for i in range(4):
        ax.plot(t, H_es[:, i] - H_es[0, i], color=ES_COLORS_4[i], lw=1.2, label=fr"$\Delta H_{i+1}$")
    ax.plot(t, H_avg - H_avg[0], color="black", lw=1.2, ls="--", label=r"$\Delta H_{\rm avg}$")
    ax.set_ylabel(r"$\Delta H$ (s)", fontsize=9)
    ax.set_xlabel("(c) Time since disturbance (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6.5, ncol=2)

    # (d) ΔD
    ax = axes[1, 1]
    for i in range(4):
        ax.plot(t, D_es[:, i] - D_es[0, i], color=ES_COLORS_4[i], lw=1.2, label=fr"$\Delta D_{i+1}$")
    ax.plot(t, D_avg - D_avg[0], color="black", lw=1.2, ls="--", label=r"$\Delta D_{\rm avg}$")
    ax.set_ylabel(r"$\Delta D$ (p.u.)", fontsize=9)
    ax.set_xlabel("(d) Time since disturbance (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6.5, ncol=2)

    title = (f"V4 DDIC ({LABEL}) — {scen_label} (75 ep ckpt). "
             f"max_|df|={traj['max_df']:.3f}Hz / paper {paper_bench.max_abs_df_Hz}Hz "
             f"(ratio {traj['max_df']/paper_bench.max_abs_df_Hz:.2f}×)")
    fig.suptitle(title, fontsize=8, y=0.985)

    save_fig(fig, OUT_DIR, out_name)
    plt.close(fig)
    print(f"  saved {out_name}.png/.pdf in {OUT_DIR}")


def main():
    print(f"[V4 ddic fig] LABEL={LABEL}, output → {OUT_DIR}")
    for scen, bench in [("load_step_1", PAPER_FIG6), ("load_step_2", PAPER_FIG8)]:
        path = EVAL_DIR / f"{LABEL}_{scen}.json"
        if not path.exists():
            print(f"  SKIP: {path} not found")
            continue
        traj = _load(path)
        out_name = f"v4_ddic_{scen}"
        plot_4panel_ddic(traj, bench, scen, out_name)


if __name__ == "__main__":
    main()
