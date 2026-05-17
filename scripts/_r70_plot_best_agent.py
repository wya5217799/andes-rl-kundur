"""R70 plot best agent — paper Fig 6/7/8 style.

Generates 3 panels per LS scenario:
  - 4-agent Δf(t) time-domain (paper Fig 6 style)
  - 4-agent ΔP(t) time-domain (paper Fig 7 style — per-agent injection)
  - per-agent ΔH/ΔD bar chart (action authority)

Reads trace JSONs from results/research_loop/eval_v4_baseline/.
Outputs PNG (no LaTeX dependency) to results/r70_paper_figures/.

Usage: python scripts/_r70_plot_best_agent.py [trace_label]
       default: r69_w3_lstm_tau001_warmup20_s50_6axis_s50 (R70 selected SOTA)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR = ROOT / "results" / "r70_paper_figures"

# Paper Fig 6/8 reference benchmarks
PAPER_BENCH = {
    "load_step_1": {"max_df": 0.13, "final_df": 0.08, "settling_s": 3.0,
                    "label": "LS1 (Δu=-2.48 PU @ Bus 14)"},
    "load_step_2": {"max_df": 0.10, "final_df": 0.05, "settling_s": 2.5,
                    "label": "LS2 (Δu=-1.86 PU @ Bus 16)"},
}

ES_NAMES = ["ES1 (Bus 12)", "ES2 (Bus 14)", "ES3 (Bus 15)", "ES4 (Bus 16)"]
ES_COLORS = ["#1565c0", "#2e7d32", "#ef6c00", "#c62828"]


def _load_trace(path: Path) -> dict:
    with open(path, encoding="utf-8") as _f:
        j = json.load(_f)
    traces = j["traces"]
    t = np.array([s["t"] for s in traces], dtype=float)
    df = np.array([s["delta_f_es"] for s in traces], dtype=float)
    P = np.array([s["delta_P_es"] for s in traces], dtype=float)
    M = np.array([s["M_es"] for s in traces], dtype=float)
    D = np.array([s["D_es"] for s in traces], dtype=float)
    dM = np.array([s["delta_M"] for s in traces], dtype=float)
    dD = np.array([s["delta_D"] for s in traces], dtype=float)
    dH = (M - M[0:1]) / 2.0
    dD_state = D - D[0:1]
    return dict(t=t, df=df, P=P, M=M, D=D, dM=dM, dD=dD, dH=dH, dD_state=dD_state,
                scenario=j.get("scenario", ""))


def plot_scenario(label: str, scen: str, ax_df, ax_P, ax_bar) -> None:
    p = EVAL_DIR / f"{label}_{scen}.json"
    if not p.exists():
        for ax in (ax_df, ax_P, ax_bar):
            ax.text(0.5, 0.5, f"missing\n{p.name}", ha="center", va="center",
                    transform=ax.transAxes)
        return
    tr = _load_trace(p)
    bench = PAPER_BENCH[scen]
    t = tr["t"]
    t0 = t[0]
    t_rel = t - t0

    # Subplot 1: 4-agent Δf(t) + paper benchmarks
    for i in range(4):
        ax_df.plot(t_rel, tr["df"][:, i], color=ES_COLORS[i],
                   lw=1.2, label=ES_NAMES[i], alpha=0.85)
    ax_df.axhline(0, color="gray", lw=0.5)
    ax_df.axhline(-bench["max_df"], color="red", lw=0.5, ls="--",
                  label=f"paper |Δf|={bench['max_df']}")
    ax_df.axhline(bench["max_df"], color="red", lw=0.5, ls="--")
    ax_df.axvline(bench["settling_s"], color="green", lw=0.5, ls=":",
                  label=f"paper settle={bench['settling_s']}s")
    ax_df.set_xlabel("t (s, from disturbance)")
    ax_df.set_ylabel("Δf (Hz)")
    ax_df.set_title(f"Δf per generator — {bench['label']}")
    ax_df.legend(loc="lower right", fontsize=7, ncol=2)
    ax_df.grid(alpha=0.3)
    ax_df.set_xlim(0, min(t_rel[-1], 10))

    # Subplot 2: 4-agent ΔP(t) — per-agent injection
    for i in range(4):
        ax_P.plot(t_rel, tr["P"][:, i], color=ES_COLORS[i],
                  lw=1.2, label=ES_NAMES[i], alpha=0.85)
    ax_P.axhline(0, color="gray", lw=0.5)
    ax_P.set_xlabel("t (s, from disturbance)")
    ax_P.set_ylabel("ΔP (pu)")
    ax_P.set_title("ΔP per ESS agent (paper Fig.7 style)")
    ax_P.legend(loc="best", fontsize=7)
    ax_P.grid(alpha=0.3)
    ax_P.set_xlim(0, min(t_rel[-1], 10))

    # Subplot 3: per-agent contribution bar (final 10-step mean abs)
    if tr["P"].shape[0] >= 10:
        P_final = np.abs(tr["P"][-10:].mean(axis=0))
        dH_max = np.max(np.abs(tr["dH"]), axis=0)
        dD_max = np.max(np.abs(tr["dD_state"]), axis=0)
    else:
        P_final = np.abs(tr["P"][-1])
        dH_max = np.max(np.abs(tr["dH"]), axis=0)
        dD_max = np.max(np.abs(tr["dD_state"]), axis=0)
    x = np.arange(4)
    w = 0.27
    ax_bar.bar(x - w, P_final, w, label="|ΔP_final|", color="#1976d2")
    # Normalize dH/dD for visual comparison (scale to similar magnitude as P)
    ax_bar.bar(x, dH_max / max(dH_max.max(), 1e-6) * P_final.max(), w,
               label="|ΔH|_max (norm)", color="#43a047")
    ax_bar.bar(x + w, dD_max / max(dD_max.max(), 1e-6) * P_final.max(), w,
               label="|ΔD|_max (norm)", color="#fb8c00")
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(ES_NAMES, fontsize=7, rotation=10)
    ax_bar.set_ylabel("magnitude")
    ax_bar.set_title("per-agent contribution\n(paper requires ≈1:1:1:1 ΔP)")
    ax_bar.legend(loc="best", fontsize=7)
    ax_bar.grid(alpha=0.3, axis="y")

    # Annotation: P_balance score
    p_min, p_max, p_mean = P_final.min(), P_final.max(), P_final.mean()
    if p_mean > 1e-3:
        p_balance = 1 - (p_max - p_min) / p_mean
        ax_bar.text(0.5, 0.95, f"P_balance = {p_balance:.2f}",
                    transform=ax_bar.transAxes, ha="center", va="top",
                    fontsize=8, bbox=dict(boxstyle="round",
                                           facecolor="lightyellow", alpha=0.8))


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "r69_w3_lstm_tau001_warmup20_s50_6axis_s50"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Plotting {label} ...")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for row, scen in enumerate(["load_step_1", "load_step_2"]):
        plot_scenario(label, scen,
                      axes[row, 0], axes[row, 1], axes[row, 2])

    fig.suptitle(f"R70 paper-figure verification: {label}",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    out = OUT_DIR / f"{label}_paper_figs.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print(f"→ {out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
