"""R242 paper figure — gauge invariance of paper Eq.14 reward.

Side-by-side phase portraits showing:
  - R201 hreg + full reward (SOTA): converges to common-mode mean_df ≈ 0.027 Hz
  - R239 scalar + only phi_abs: same common-mode (gauge-fix sufficient)
  - R218 hreg + paper-strict: synchronizes at common-mode 0.059 Hz (gauge unfixed)

The signature is "all three synchronize tightly (spread → 0) but
paper-strict lands at a higher common-mode drift because no
reward term penalizes the common mode" — empirical confirmation of
the gauge-invariance argument in
docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "r242_gauge_invariance_fig"
OUT.mkdir(parents=True, exist_ok=True)


def load_trajectory(run_dir: str, scenario: str = "load_step_1"):
    run = ROOT / "results" / run_dir
    eval_dir = run / "final_eval"
    p = next(eval_dir.glob(f"final_eval_*_{scenario}.json"))
    data = json.loads(p.read_text())
    t = np.array([s["t"] for s in data["traces"]])
    f = np.array([s["freq_hz"] for s in data["traces"]])  # (T, 4)
    df = f - 50.0
    return t, df, data.get("max_df"), data.get("cum_rf_total")


def load_summary(run_dir: str):
    """Read both `geo` (11-axis v3.1) and `cum_rf` (paper §IV-C)
    from final_eval_summary.json for dual-metric annotation."""
    p = ROOT / "results" / run_dir / "final_eval_summary.json"
    if not p.exists():
        # score_run.py output naming variant
        for alt in (ROOT / "results" / run_dir).glob("*_summary.json"):
            p = alt
            break
    if not p.exists():
        return None, None
    j = json.loads(p.read_text())
    if "per_seed" in j:
        # score_run aggregate format — dive into first seed
        first = next(iter(j["per_seed"].values()))
        return first.get("geo"), first.get("cum_rf")
    return j.get("geo"), j.get("cum_rf")


CONFIGS = [
    ("r201_w1_hreg_tau005_s54", "R201 hreg + full reward (SOTA)", "#1f77b4"),
    ("r239_w1_scalar_onlyphiabs_s54", "R239 scalar + only phi_abs", "#2ca02c"),
    ("r218_w1_hreg_paperstrict_s54", "R218 hreg + paper-strict (collapsed)", "#d62728"),
    ("r240_w1_scalar_paperstrict_s54", "R240 scalar + paper-strict (collapsed)", "#ff7f0e"),
]


def main() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1]})

    # Top: per-agent Δf trajectories for all three controllers, distinguished by colour
    ax = axes[0]
    for run_dir, label, color in CONFIGS:
        t, df, max_df, cum_rf = load_trajectory(run_dir)
        geo_sum, cum_rf_sum = load_summary(run_dir)
        # plot mean (thick) and per-agent envelope (thin)
        mean_df = df.mean(axis=1)
        gs = f"geo={geo_sum:.3f}" if geo_sum is not None else ""
        cs = f"cum_rf={cum_rf_sum:+.3f}" if cum_rf_sum is not None else ""
        ax.plot(t, mean_df, color=color, linewidth=2.5,
                label=f"{label}\n{gs}  {cs}  mean_df={mean_df[-1]:+.4f} Hz")
        # thin lines per agent
        for k in range(df.shape[1]):
            ax.plot(t, df[:, k], color=color, linewidth=0.6, alpha=0.35)
    ax.axhline(0.0, color="black", linewidth=0.5, linestyle="--")
    ax.set_ylabel("Δf (Hz) — per-agent (thin) and mean (thick)")
    ax.set_title("LS1 (-2.48 pu load step at Bus 14): paper-strict synchronizes\n"
                 "but at a higher common-mode drift than gauge-fixed controllers")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Bottom: spread vs time (max_i Δf - min_i Δf), log scale
    ax = axes[1]
    for run_dir, label, color in CONFIGS:
        t, df, _, _ = load_trajectory(run_dir)
        spread = df.max(axis=1) - df.min(axis=1)
        ax.semilogy(t, spread + 1e-6, color=color, linewidth=1.8, label=label)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("spread = max_i Δf − min_i Δf (Hz, log)")
    ax.set_title("All three controllers synchronize tightly (spread → 1e-4 Hz simulator noise floor)")
    ax.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    out_pdf = OUT / "gauge_invariance_phase_portrait.pdf"
    out_png = OUT / "gauge_invariance_phase_portrait.png"
    plt.savefig(out_pdf, bbox_inches="tight")
    plt.savefig(out_png, bbox_inches="tight", dpi=180)
    print(f"-> {out_pdf}")
    print(f"-> {out_png}")

    # Quantitative summary — DUAL-METRIC (geo 11-axis + cum_rf paper §IV-C)
    print("\n=== Final-step summary (LS1) + DUAL-METRIC (CLM-0430 audit) ===")
    print(f"  {'run':32s}  {'geo':>7s}  {'cum_rf':>9s}  {'mean_df':>9s}  {'spread':>10s}  {'max_df':>7s}")
    for run_dir, label, _ in CONFIGS:
        t, df, max_df, cum_rf_LS1 = load_trajectory(run_dir)
        mean_df = df.mean(axis=1)
        spread = df.max(axis=1) - df.min(axis=1)
        geo_sum, cum_rf_sum = load_summary(run_dir)
        gs = f"{geo_sum:.4f}" if geo_sum is not None else "n/a"
        cs = f"{cum_rf_sum:+.4f}" if cum_rf_sum is not None else "n/a"
        print(f"  {label:32s}  {gs:>7s}  {cs:>9s}  {mean_df[-1]:+8.4f}  {spread[-1]:.3e}  {max_df:7.4f}")


if __name__ == "__main__":
    main()
