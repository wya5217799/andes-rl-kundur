"""R125 — paper-quality summary figure: obs-ascent vs h-warm step-0 barrier.

Integrates R104 (CLM-0188) and R117 (CLM-0217) into a single 2D scatter
suitable for paper Sec.IV-D. Each LSTM ckpt is one point:

  X = max obs-ascent ||a|| at h=0 (% of max √2)  [R117 / CLM-0217]
  Y = warm-h_0 ascent ||a|| at obs ||obs||=0.25 (% of max) [R104 / CLM-0188]

Diagonal y=x indicates symmetry. Empirically all points lie far above
the diagonal (h path >> obs path), making the bidirectional asymmetry
of step-0 saturation reachability visually obvious.

Annotated reference lines:
- horizontal "warm-h_0 99% saturation" band (CLM-0188 median)
- vertical "obs-only 50% ceiling" band (CLM-0217 p90)
- diagonal "y=x equality"

Output: results/r125_step0_barrier_figure/{barrier.png, barrier_data.csv,
summary.json}.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "r125_step0_barrier_figure"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Load source data from the two prior rounds' summary.json
R104_SUMMARY = ROOT / "results" / "r104_warm_h0_multickpt" / "summary.json"
R117_SUMMARY = ROOT / "results" / "r117_obs_ascent_multickpt" / "summary.json"


def main():
    r104 = json.loads(R104_SUMMARY.read_text())
    r117 = json.loads(R117_SUMMARY.read_text())

    # Build {ckpt_label: (obs_max_pct, h_warm_pct)} mapping
    obs_by_ckpt = {r["ckpt"]: r["a_star_max_pct"] for r in r117["per_ckpt"]}
    h_warm_by_ckpt = {r["ckpt"]: r["norm_star_pct_max_median"] for r in r104["per_ckpt"]}

    common = sorted(set(obs_by_ckpt) & set(h_warm_by_ckpt))
    rows = [
        {"ckpt": ck,
         "obs_only_max_pct_of_saturation": obs_by_ckpt[ck],
         "h_warm_median_pct_of_saturation": h_warm_by_ckpt[ck]}
        for ck in common
    ]

    # Write CSV for paper appendix
    with open(OUT_DIR / "barrier_data.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ckpt",
                                          "obs_only_max_pct_of_saturation",
                                          "h_warm_median_pct_of_saturation"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Matplotlib figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 5.5))

    # Diagonal y = x
    ax.plot([0, 100], [0, 100], color="lightgray", linewidth=1.0, linestyle="--",
            label="y = x (symmetry)")

    # Reference band: warm-h_0 ~ 95% (median from CLM-0188)
    ax.axhline(95.6, color="tab:green", linewidth=0.8, linestyle=":", alpha=0.7,
               label="warm-h₀ median 95.6% (CLM-0188)")
    # Reference band: obs-only median 21.5%
    ax.axvline(21.5, color="tab:red", linewidth=0.8, linestyle=":", alpha=0.7,
               label="obs-only median 21.5% (CLM-0217)")

    # Scatter points
    xs = [r["obs_only_max_pct_of_saturation"] for r in rows]
    ys = [r["h_warm_median_pct_of_saturation"] for r in rows]
    labels = [r["ckpt"] for r in rows]

    # Color by "round family" — R72 wave bright, R58 wave muted, R62 special
    def _color(label):
        if "r72_w4" in label.lower() and "sota" in label.lower():
            return "tab:red", 90, "★ R72_w4 SOTA"
        if "r72" in label.lower():
            return "tab:orange", 55, "R72 wave"
        if "r62" in label.lower():
            return "tab:purple", 55, "R62 h=128"
        if "r58" in label.lower():
            return "tab:blue", 55, "R58 wave"
        return "gray", 40, "other"

    seen_legends = set()
    for x, y, label in zip(xs, ys, labels):
        c, s, leg = _color(label)
        leg_to_use = leg if leg not in seen_legends else None
        if leg_to_use:
            seen_legends.add(leg_to_use)
        ax.scatter(x, y, c=c, s=s, edgecolor="black", linewidth=0.5,
                   label=leg_to_use, zorder=3)
        # Annotate ckpt short tag
        short = label.replace("_lstm_", "").replace("_SOTA", "")
        ax.annotate(short, (x, y), xytext=(6, -8), textcoords="offset points",
                    fontsize=7, color="dimgray")

    ax.set_xlabel("obs-only ascent at h=0 — max ||a|| (% of saturation)\n"
                  "[R117 / CLM-0217]", fontsize=10)
    ax.set_ylabel("warm-h₀ ascent at ||obs||=0.25 — ||a|| (% of saturation)\n"
                  "[R104 / CLM-0188]", fontsize=10)
    ax.set_title("Step-0 actor saturation reachability across N=9 LSTM checkpoints\n"
                 "h-path universally unlocks 95-99%; obs-path universally blocked < 52%",
                 fontsize=11)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "barrier.png", dpi=200)
    fig.savefig(OUT_DIR / "barrier.pdf")
    print(f"saved: {OUT_DIR / 'barrier.png'} + .pdf + .csv")

    summary = {
        "round": "R125",
        "kind": "step0_barrier_summary_figure",
        "n_ckpts": len(rows),
        "median_obs_only_pct": float(np.median(xs)),
        "median_h_warm_pct": float(np.median(ys)),
        "obs_only_max_across_ckpts": float(np.max(xs)),
        "obs_only_min_across_ckpts": float(np.min(xs)),
        "h_warm_min_across_ckpts": float(np.min(ys)),
        "asymmetry_pp_median": float(np.median(np.array(ys) - np.array(xs))),
        "interpretation": (
            "All 9 LSTM ckpts cluster in the upper-left of the (obs-only, "
            "h-warm) plane — every ckpt has >> 50pp asymmetry between the "
            "two saturation reachability paths."
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
