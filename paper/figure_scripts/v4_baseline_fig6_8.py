"""V4 paper-faithful baseline Fig.6/8 plot — no-control LS1/LS2 vs paper.

Direct paper-style 2x2 time-domain plot (Δf, ΔP, ΔH, ΔD) for V4 baseline,
using same plotting/paper_style.plot_time_domain_2x2 as Simulink Fig.6/7 pipe.

Reads V4 trace JSON from `results/research_loop/eval_v4_baseline/`,
produced by `scripts/research_loop/eval_v4_no_control.py`.

Output: paper/figures/v4_baseline/no_control_ls{1,2}.png + .pdf
"""
from __future__ import annotations

import json
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
    plot_time_domain_2x2,
    save_fig,
)

EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR = ROOT / "paper" / "figures" / "v4_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Paper benchmarks (same as paper_grade_axes.py PAPER constants)
PAPER_BENCH = {
    "load_step_1": {"max_df": 0.13, "final_df": 0.08, "settling_s": 3.0},
    "load_step_2": {"max_df": 0.10, "final_df": 0.05, "settling_s": 2.5},
}


def _load_trace(path: Path) -> dict:
    j = json.load(open(path))
    traces = j["traces"]
    n_agents = 4
    t = np.array([s["t"] for s in traces], dtype=float)
    freq_hz = np.array([s["freq_hz"] for s in traces], dtype=float)
    P_es = np.array([s["delta_P_es"] for s in traces], dtype=float)
    M_es = np.array([s["M_es"] for s in traces], dtype=float)
    D_es = np.array([s["D_es"] for s in traces], dtype=float)
    return {
        "time": t,
        "freq_hz": freq_hz,
        "P_es": P_es,
        "M_es": M_es,
        "D_es": D_es,
        "scenario": j["scenario"],
        "max_df": j["max_df"],
    }


def plot_no_control_2panel(traj: dict, scen: str, paper_bench: dict, out_name: str):
    """Plot 2-panel (Δf + ΔP) like paper Fig.6/8 (no-control).

    LS1 (load -2.48 @ Bus14) → freq ↑ → Δf > 0
    LS2 (load +1.88 @ Bus15) → freq ↓ → Δf < 0
    Paper benchmarks 0.13/0.08 (LS1) / 0.10/0.05 (LS2) are |Δf| magnitudes.

    Plot shows signed Δf with sign-aware paper benchmark dashed lines + a
    truncated "paper window" (first 6s post-disturbance, since paper Fig.6
    uses 6s window).
    """
    apply_ieee_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.8))
    fig.subplots_adjust(wspace=0.32, left=0.08, right=0.97, top=0.88, bottom=0.18)

    # Trace t starts at ~1s (T_warmup). Disturbance is at t[0]. Re-zero to "time
    # since disturbance" for paper-comparable axis.
    t = traj["time"] - traj["time"][0]
    fn = 50.0

    # Determine sign: positive for LS1 (load drop → freq up), negative for LS2
    sign = +1.0 if "step_1" in scen else -1.0

    # (a) Δf — show signed Δf + sign-aware paper benchmarks
    ax = axes[0]
    n_agents = 4
    for i in range(n_agents):
        df_i = traj["freq_hz"][:, i] - fn
        ax.plot(t, df_i, color=ES_COLORS_4[i], lw=1.2, label=ES_FREQ_LABELS_4[i])
    ax.axhline(sign * paper_bench["max_df"], color="black", lw=0.9, ls=":",
               label=f"paper max=±{paper_bench['max_df']}Hz")
    ax.axhline(sign * paper_bench["final_df"], color="black", lw=0.9, ls="--",
               label=f"paper final=±{paper_bench['final_df']}Hz")
    ax.axhline(0, color="gray", lw=0.5, ls="--")
    # Paper window 6s (paper Fig.6 default window)
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1, label="paper 6s window")
    ax.set_ylabel(r"$\Delta f$ (Hz)", fontsize=9)
    ax.set_xlabel(f"(a) Time since disturbance (s) — {scen} no-control", fontsize=9)
    ax.legend(loc="best", fontsize=6.5, ncol=2)

    # (b) ΔP_es
    ax = axes[1]
    for i in range(n_agents):
        ax.plot(t, traj["P_es"][:, i] - traj["P_es"][0, i],
                color=ES_COLORS_4[i], lw=1.2, label=f"$\\Delta P_{{es{i+1}}}$")
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"$\Delta P_{\rm es}$ (p.u.)", fontsize=9)
    ax.set_xlabel("(b) Time since disturbance (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6.5, ncol=2)

    title = (f"V4 paper-faithful baseline — {scen} (no-control). "
             f"max_|df|={traj['max_df']:.3f}Hz / paper {paper_bench['max_df']}Hz "
             f"(ratio {traj['max_df'] / paper_bench['max_df']:.2f}×); "
             f"DT={traj['time'][1]-traj['time'][0]:.2f}s/step (paper 0.2s)")
    fig.suptitle(title, fontsize=7.5, y=0.97)

    save_fig(fig, OUT_DIR, out_name)
    plt.close(fig)
    print(f"  saved {out_name}.png/.pdf in {OUT_DIR}")


def main():
    print(f"[V4 fig] reading from {EVAL_DIR}, output → {OUT_DIR}\n")
    for scen, bench in PAPER_BENCH.items():
        path = EVAL_DIR / f"no_control_{scen}.json"
        if not path.exists():
            print(f"  SKIP: {path} not found")
            continue
        traj = _load_trace(path)
        out_name = f"v4_baseline_no_control_{scen}"
        plot_no_control_2panel(traj, scen, bench, out_name)
        print(f"  scen={scen} max_df_proj={traj['max_df']:.3f} (paper {bench['max_df']}, ratio {traj['max_df']/bench['max_df']:.2f}×)")


if __name__ == "__main__":
    main()
