"""V4.1 DDIC vs no_control vs paper Fig.7/9 plot.

Overlays:
  - no_control V4 baseline (gray)
  - 3 V4.1 DDIC trained seeds (s42, s43, s44 — color per seed)
  - Paper benchmark dashed lines (max + final magnitudes)

Output: paper/figures/v4_1_baseline/v4_1_ddic_vs_no_control_ls{1,2}.png/.pdf

Reads JSON from `results/research_loop/eval_v4_baseline/`.
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

from plotting.paper_style import apply_ieee_style, save_fig  # noqa: E402

EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR = ROOT / "paper" / "figures" / "v4_1_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAPER = {
    "load_step_1": {"max_df": 0.13, "final_df": 0.08, "settling_s": 3.0,
                    "title": "LS1 (Bus14 -2.48 sys_pu)"},
    "load_step_2": {"max_df": 0.10, "final_df": 0.05, "settling_s": 2.5,
                    "title": "LS2 (Bus15 +1.88 sys_pu)"},
}

DDIC_LABELS = ["ddic_v4_1_paper_s42", "ddic_v4_1_paper_s43", "ddic_v4_1_paper_s44"]
DDIC_COLORS = ["#E8548A", "#F5A623", "#36D7B7"]  # pink, orange, teal


def _load(path: Path) -> dict:
    j = json.load(open(path))
    traces = j["traces"]
    t = np.array([s["t"] for s in traces], dtype=float) - traces[0]["t"]
    freq_hz = np.array([s["freq_hz"] for s in traces], dtype=float)
    P_es = np.array([s["delta_P_es"] for s in traces], dtype=float)
    M_es = np.array([s["M_es"] for s in traces], dtype=float)
    D_es = np.array([s["D_es"] for s in traces], dtype=float)
    return {"t": t, "freq_hz": freq_hz, "P_es": P_es, "M_es": M_es, "D_es": D_es,
            "max_df": j["max_df"]}


def plot_one_scenario(scen: str, paper_bench: dict):
    apply_ieee_style()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.0))
    fig.subplots_adjust(hspace=0.45, wspace=0.32, left=0.10, right=0.97,
                        top=0.91, bottom=0.10)

    sign = +1.0 if "step_1" in scen else -1.0
    F_NOM = 50.0

    # Load no_control
    nc = _load(EVAL_DIR / f"no_control_{scen}.json")

    # Load DDIC seeds
    ddic = {}
    for label in DDIC_LABELS:
        try:
            ddic[label] = _load(EVAL_DIR / f"{label}_{scen}.json")
        except FileNotFoundError:
            pass

    # ─ (a) Δf max over agents per time, no_control vs DDIC ─
    ax = axes[0, 0]
    df_nc = nc["freq_hz"] - F_NOM
    df_nc_max = np.max(np.abs(df_nc), axis=1) * sign  # signed peak
    ax.plot(nc["t"], df_nc_max, color="gray", lw=1.5, ls="--",
            label=f"no_control (max={nc['max_df']:.3f})")
    for i, (label, d) in enumerate(ddic.items()):
        df_d = d["freq_hz"] - F_NOM
        df_d_max = np.max(np.abs(df_d), axis=1) * sign
        seed = label.split("_s")[-1]
        ax.plot(d["t"], df_d_max, color=DDIC_COLORS[i], lw=1.2,
                label=f"DDIC s{seed} (max={d['max_df']:.3f})")
    ax.axhline(sign * paper_bench["max_df"], color="black", lw=0.9, ls=":",
               label=f"paper max=±{paper_bench['max_df']}Hz")
    ax.axhline(sign * paper_bench["final_df"], color="black", lw=0.9, ls="-.",
               label=f"paper final=±{paper_bench['final_df']}Hz")
    ax.axhline(0, color="lightgray", lw=0.4)
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"max $|\Delta f|$ (Hz)", fontsize=9)
    ax.set_xlabel("(a) time since disturbance (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6, ncol=1)

    # ─ (b) ΔP_es 4 VSG mean (per-seed comparison) ─
    ax = axes[0, 1]
    for i, (label, d) in enumerate(ddic.items()):
        dP_mean = (d["P_es"] - d["P_es"][0:1]).mean(axis=1)
        seed = label.split("_s")[-1]
        ax.plot(d["t"], dP_mean, color=DDIC_COLORS[i], lw=1.2, label=f"DDIC s{seed}")
    dP_nc = (nc["P_es"] - nc["P_es"][0:1]).mean(axis=1)
    ax.plot(nc["t"], dP_nc, color="gray", lw=1.5, ls="--", label="no_control")
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"mean $\Delta P_{\rm es}$ (sys_pu)", fontsize=9)
    ax.set_xlabel("(b) time (s)", fontsize=9)
    ax.legend(loc="best", fontsize=6)

    # ─ (c) ΔH (M_es / 2 - H_0) per seed avg ─
    ax = axes[1, 0]
    for i, (label, d) in enumerate(ddic.items()):
        H_traj = d["M_es"] / 2.0
        dH_mean = (H_traj - H_traj[0:1]).mean(axis=1)
        seed = label.split("_s")[-1]
        ax.plot(d["t"], dH_mean, color=DDIC_COLORS[i], lw=1.2, label=f"DDIC s{seed}")
    ax.axhline(0, color="lightgray", lw=0.4)
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"mean $\Delta H$ (s)", fontsize=9)
    ax.set_xlabel("(c) time (s) — paper Eq.12 box ΔH ∈ [-100, +300]", fontsize=8.5)
    ax.legend(loc="best", fontsize=6)

    # ─ (d) ΔD per seed avg ─
    ax = axes[1, 1]
    for i, (label, d) in enumerate(ddic.items()):
        dD_mean = (d["D_es"] - d["D_es"][0:1]).mean(axis=1)
        seed = label.split("_s")[-1]
        ax.plot(d["t"], dD_mean, color=DDIC_COLORS[i], lw=1.2, label=f"DDIC s{seed}")
    ax.axhline(0, color="lightgray", lw=0.4)
    ax.axvspan(0, 6.0, color="lightyellow", alpha=0.3, zorder=-1)
    ax.set_ylabel(r"mean $\Delta D$ (sys_pu)", fontsize=9)
    ax.set_xlabel("(d) time (s) — paper Eq.12 box ΔD ∈ [-200, +600]", fontsize=8.5)
    ax.legend(loc="best", fontsize=6)

    title = (f"V4.1 DDIC vs no_control — {paper_bench['title']}. "
             f"DDIC trained 200 ep, paper-faithful PHI rescale + M/D Eq.12 clamp + DT-fix.")
    fig.suptitle(title, fontsize=8.5, y=0.97)

    save_fig(fig, OUT_DIR, f"v4_1_ddic_vs_nc_{scen}")
    plt.close(fig)
    print(f"  saved v4_1_ddic_vs_nc_{scen}.png/.pdf in {OUT_DIR}")


def main():
    print(f"[V4.1 fig] reading from {EVAL_DIR}, output → {OUT_DIR}\n")
    for scen, bench in PAPER.items():
        plot_one_scenario(scen, bench)


if __name__ == "__main__":
    main()
