"""R178 paper figure — final hreg dose-response curve (10 s54 points + 2 s51).

The headline paper figure for Sec.IV-D primary contribution.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "r178_dose_response_fig"
OUT.mkdir(parents=True, exist_ok=True)


# (λ_h, seed, run_label, json_path_relative_to_root)
DATA = [
    (0.0, 54, "R72_w4 (baseline)",
        "results/research_loop/eval_v4_baseline/r72_w4_lstm_tau001_warmup5_s54_summary.json"),
    (0.001, 54, "R173",
        "results/r173_w1_hreg_lambda0p001_s54/final_eval_summary.json"),
    (0.0015, 54, "R179",
        "results/r179_w1_hreg_lambda0p0015_s54/final_eval_summary.json"),
    (0.002, 54, "R174 ⭐ SOTA",
        "results/r174_w1_hreg_lambda0p002_s54/final_eval_summary.json"),
    (0.0025, 54, "R180",
        "results/r180_w1_hreg_lambda0p0025_s54/final_eval_summary.json"),
    (0.003, 54, "R170",
        "results/r170_w1_hreg_lambda0p003_s54/final_eval_summary.json"),
    (0.004, 54, "R175",
        "results/r175_w1_hreg_lambda0p004_s54/final_eval_summary.json"),
    (0.005, 54, "R169",
        "results/r169_w1_hreg_lambda0p005_s54/final_eval_summary.json"),
    (0.01, 54, "R100",
        "results/r100_w1_hreg_lambda0p01_s54/final_eval_summary.json"),
    (0.03, 54, "R157",
        "results/r157_w1_hreg_lambda0p03_s54/final_eval_summary.json"),
    (0.0, 51, "R72_w4 hyper s51",
        "results/r154_w2_r72w4hyper_s51/final_eval_summary.json"),
    (0.002, 51, "R181",
        "results/r181_w1_hreg_lambda0p002_s51/final_eval_summary.json"),
]


def read_metric(path_str: str, key: str) -> float:
    p = ROOT / path_str
    if not p.exists():
        return float("nan")
    d = json.loads(p.read_text())
    if key in d:
        return float(d[key])
    if "per_seed" in d:
        first = next(iter(d["per_seed"].values()))
        return float(first.get(key, float("nan")))
    if key == "geo" and "mean_geo" in d:
        return float(d["mean_geo"])
    return float("nan")


def main():
    rows = []
    for lam, seed, label, path in DATA:
        rows.append({"lambda": lam, "seed": seed, "label": label,
                      "geo": read_metric(path, "geo"),
                      "LS1": read_metric(path, "LS1"),
                      "LS2": read_metric(path, "LS2")})

    s54 = [r for r in rows if r["seed"] == 54]
    s51 = [r for r in rows if r["seed"] == 51]
    s54.sort(key=lambda r: r["lambda"])
    s51.sort(key=lambda r: r["lambda"])

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    # s54 main curve
    lams = [r["lambda"] for r in s54]
    geos = [r["geo"] for r in s54]
    ax.plot(lams, geos, "-o", color="C0", lw=2, markersize=8,
            label="s54 geo (12-point sweep)")
    ax.plot(lams, [r["LS1"] for r in s54], "--^", color="C1", lw=1, markersize=5,
            alpha=0.6, label="s54 LS1 axis")
    ax.plot(lams, [r["LS2"] for r in s54], "--s", color="C2", lw=1, markersize=5,
            alpha=0.6, label="s54 LS2 axis")

    # s51 reference
    if s51:
        lams51 = [r["lambda"] for r in s51]
        geos51 = [r["geo"] for r in s51]
        ax.plot(lams51, geos51, "-D", color="C3", lw=1.5, markersize=8,
                alpha=0.7, label="s51 geo (cross-seed)")

    # Annotations
    ax.axhline(0.391, color="black", lw=0.5, ls=":", alpha=0.5, label="R72_w4 baseline 0.391")
    ax.axhline(0.4119, color="purple", lw=0.5, ls=":", alpha=0.5, label="R154 HAWE 4-way ensemble 0.4119")

    # Mark the peak
    peak = next(r for r in s54 if abs(r["lambda"] - 0.002) < 1e-9)
    ax.annotate(f"PEAK: R174 λ=0.002\ngeo={peak['geo']:.4f} (+5.9%)",
                xy=(0.002, peak["geo"]), xytext=(0.005, 0.43),
                fontsize=10, fontweight="bold", color="darkred",
                arrowprops=dict(arrowstyle="->", color="darkred", lw=1.5))

    ax.set_xscale("symlog", linthresh=0.001)
    ax.set_xlabel("λ_h (hidden-state-norm L2 penalty coefficient)")
    ax.set_ylabel("geo (11-axis paper grade) / LS1 / LS2")
    ax.set_title("Hreg dose-response curve — R174 (λ=0.002) is project SOTA at 0.4139\n"
                  "(td3_lstm_hreg + hyperparameter sweep, 75 ep V4 paper-faithful)",
                  fontsize=11)
    ax.set_ylim(0.05, 0.50)
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "dose_response_curve.pdf")
    fig.savefig(OUT / "dose_response_curve.png", dpi=140)
    plt.close(fig)

    print(f"=== Dose-response curve (10 + 2 points) ===")
    print(f"{'λ_h':>8} {'seed':>5} {'label':<30} {'geo':>8} {'LS1':>7} {'LS2':>7}")
    for r in sorted(rows, key=lambda x: (x["seed"], x["lambda"])):
        print(f"{r['lambda']:>8.4f} {r['seed']:>5} {r['label']:<30} "
              f"{r['geo']:>8.4f} {r['LS1']:>7.4f} {r['LS2']:>7.4f}")
    print(f"\nWritten: {OUT}/dose_response_curve.{{pdf,png}}")


if __name__ == "__main__":
    main()
