"""R154 paper figure — HAWE ensemble breakthrough bar chart.

Reads all R152 + R154 ensemble summaries + single-policy baselines,
produces paper-quality figure showing:
  - left subplot: geo bar chart (sorted by geo)
  - right subplot: LS1 vs LS2 axis decomposition (scatter)

Saves to results/r154_paper_fig/{ensemble_bar.pdf, axis_scatter.pdf}.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "r154_paper_fig"
OUT.mkdir(parents=True, exist_ok=True)


# (label, json_path, kind)
ENTRIES: list[tuple[str, str, str]] = [
    # Single policies
    ("R72_w4 single",          "results/research_loop/eval_v4_baseline/r72_w4_lstm_tau001_warmup5_s54_summary.json", "single"),
    ("R142 QR",                "results/r142_w1_qr51_s54/final_eval_summary.json", "single"),
    ("R143 QR-fixed",          "results/r143_w1_qr51_s54_fixed/final_eval_summary.json", "single"),
    ("R100 hreg",              "results/r100_w1_hreg_lambda0p01_s54/final_eval_summary.json", "single"),
    ("R150 warmh0+QR",         "results/r150_warmh0_qr_s54/final_eval_summary.json", "single"),
    ("R72_w4 hyper s51",       "results/r154_w2_r72w4hyper_s51/final_eval_summary.json", "single"),
    # Ensembles
    ("R152 3-way",             "results/r152_ensemble/r152_ens3_mean_baselines_summary.json", "ensemble"),
    ("R154 2-way x-seed",      "results/r154_ensemble/r154_ens2_cross_seed_pure_summary.json", "ensemble"),
    ("R154 3-way drop-R143",   "results/r154_ensemble/r154_ens3_xalgo_baseline_qr_hreg_summary.json", "ensemble"),
    ("R154 4-way x-seed mix",  "results/r154_ensemble/r154_ens4_full_summary.json", "ensemble"),
    ("R154 4-way SOTA",        "results/r154_ensemble/r154_ens4_xalgo_quad_summary.json", "sota"),
    ("R154 5-way (+R150)",     "results/r154_ensemble/r154_ens5_full_summary.json", "ensemble"),
]


def read_geo(path: str) -> dict:
    p = ROOT / path
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    # Some files store geo under per_seed; flatten if needed.
    if "geo" in data:
        return data
    if "per_seed" in data:
        first = next(iter(data["per_seed"].values()))
        return first
    return {}


def main() -> None:
    rows = []
    for label, path, kind in ENTRIES:
        d = read_geo(path)
        if not d:
            print(f"WARN: missing {path}")
            continue
        rows.append({"label": label, "kind": kind,
                      "geo": float(d["geo"]),
                      "LS1": float(d.get("LS1", 0)),
                      "LS2": float(d.get("LS2", 0))})

    # Sort by geo descending.
    rows.sort(key=lambda r: -r["geo"])

    # ── Figure 1: bar chart ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    colors = {"single": "#888888", "ensemble": "#2980b9", "sota": "#d35400"}
    xs = np.arange(len(rows))
    bars = ax.bar(xs, [r["geo"] for r in rows],
                  color=[colors[r["kind"]] for r in rows])
    ax.set_xticks(xs)
    ax.set_xticklabels([r["label"] for r in rows], rotation=45, ha="right",
                       fontsize=8)
    ax.set_ylabel("11-axis geo")
    ax.set_title("HAWE ensemble breakthrough — R154 4-way SOTA = 0.4119 (+5.4% baseline)")
    ax.axhline(0.3908, color="red", lw=0.7, ls="--",
               label="R72_w4 baseline 0.391")
    ax.axhline(0.42, color="green", lw=0.7, ls=":",
               label="BREAK gate 0.42")
    for b, r in zip(bars, rows):
        ax.text(b.get_x() + b.get_width()/2, r["geo"] + 0.005,
                f"{r['geo']:.3f}", ha="center", fontsize=7)
    ax.set_ylim(0, 0.46)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3, lw=0.5)
    fig.tight_layout()
    fig.savefig(OUT / "ensemble_bar.pdf")
    fig.savefig(OUT / "ensemble_bar.png", dpi=140)
    plt.close(fig)

    # ── Figure 2: LS1 vs LS2 axis decomposition ────────────────────────
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    for r in rows:
        if r["LS1"] == 0 and r["LS2"] == 0:
            continue
        sz = 200 if r["kind"] == "sota" else 100
        ax.scatter(r["LS1"], r["LS2"], s=sz, c=colors[r["kind"]],
                   edgecolors="black", lw=0.5, alpha=0.85, zorder=3)
        ax.annotate(r["label"], (r["LS1"], r["LS2"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=7)
    ax.set_xlabel("LS1 geo axis")
    ax.set_ylabel("LS2 geo axis")
    ax.set_title("R154 SOTA decomposes into LS1 + LS2 axis gains")
    ax.axvline(0.354, color="red", lw=0.5, ls="--", alpha=0.5)
    ax.axhline(0.431, color="red", lw=0.5, ls="--", alpha=0.5)
    ax.text(0.354, 0.27, "R72_w4 LS1", color="red", fontsize=7, rotation=90,
            va="bottom", ha="right")
    ax.text(0.32, 0.431, "R72_w4 LS2", color="red", fontsize=7, ha="left",
            va="bottom")
    ax.grid(True, alpha=0.3, lw=0.5)
    fig.tight_layout()
    fig.savefig(OUT / "axis_scatter.pdf")
    fig.savefig(OUT / "axis_scatter.png", dpi=140)
    plt.close(fig)

    print("=== R154 paper figure ===")
    print(f"{'config':<32} {'kind':<10} {'geo':>8} {'LS1':>7} {'LS2':>7}")
    for r in rows:
        print(f"  {r['label']:<30} {r['kind']:<10} {r['geo']:>8.4f} "
              f"{r['LS1']:>7.4f} {r['LS2']:>7.4f}")
    print("\nWritten:")
    print(f"  {OUT}/ensemble_bar.{{pdf,png}}")
    print(f"  {OUT}/axis_scatter.{{pdf,png}}")


if __name__ == "__main__":
    main()
