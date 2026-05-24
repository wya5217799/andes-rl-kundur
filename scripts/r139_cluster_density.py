"""R139 — Cluster density visualisation of N=91 fresh-scored ckpts.

CLM-0260 (R137) flagged "discrete attractor cluster structure" as one
of three genuinely-novel contributions from R134-R136 chain. R139
quantifies the structure with explicit bin counts + density figure.

Findings (preview):
- Degenerate cluster CORE (geo 0.010-0.052): 29/91 = 32%
- LSTM SOTA cluster CORE (geo 0.346-0.388): 24/91 = 26%
- Mid region (0.10-0.30): 17/91 = 19% — sparse but NOT empty
- LSTM cum_rf narrow [-0.111, -0.067]; degenerate cum_rf wide

Output: results/r139_cluster_density/{density.png, histograms.png,
summary.json}.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "r139_cluster_density"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    d = json.loads((ROOT / "results" / "r135_freshscore" / "summary.json").read_text())
    records = d["all_records"]
    geos = np.array([r["geo"] for r in records])
    cum_rfs = np.array([r["cum_rf"] for r in records])
    labels = [r["label"] for r in records]
    n = len(records)

    # Cluster assignment
    DEG_MAX = 0.10   # degenerate cluster ceiling
    LSTM_MIN = 0.30  # LSTM SOTA cluster floor
    mask_deg = geos < DEG_MAX
    mask_lstm = geos > LSTM_MIN
    mask_mid = ~(mask_deg | mask_lstm)

    stats = {
        "n_total": n,
        "n_degenerate_geo_lt_010": int(mask_deg.sum()),
        "n_mid_010_to_030": int(mask_mid.sum()),
        "n_lstm_sota_geo_gt_030": int(mask_lstm.sum()),
        "deg_pct": float(mask_deg.mean() * 100),
        "mid_pct": float(mask_mid.mean() * 100),
        "lstm_pct": float(mask_lstm.mean() * 100),
        "deg_cum_rf_range": [float(cum_rfs[mask_deg].min()), float(cum_rfs[mask_deg].max())],
        "lstm_cum_rf_range": [float(cum_rfs[mask_lstm].min()), float(cum_rfs[mask_lstm].max())],
        "mid_cum_rf_range": [float(cum_rfs[mask_mid].min()), float(cum_rfs[mask_mid].max())],
    }
    print("Cluster stats:", json.dumps(stats, indent=2))

    # Best-of-cluster identification
    deg_best_idx = np.argmax(cum_rfs * mask_deg + -np.inf * (~mask_deg))
    lstm_best_idx = np.argmax(geos * mask_lstm + -np.inf * (~mask_lstm))
    stats["degenerate_cum_rf_top"] = {
        "label": labels[deg_best_idx],
        "geo": float(geos[deg_best_idx]),
        "cum_rf": float(cum_rfs[deg_best_idx]),
    }
    stats["lstm_geo_top"] = {
        "label": labels[lstm_best_idx],
        "geo": float(geos[lstm_best_idx]),
        "cum_rf": float(cum_rfs[lstm_best_idx]),
    }

    # Density plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: 2D density
    ax1.scatter(cum_rfs[mask_deg], geos[mask_deg], s=30, c="tab:red",
                alpha=0.6, edgecolor="black", linewidth=0.3,
                label=f"Degenerate ({stats['n_degenerate_geo_lt_010']}, {stats['deg_pct']:.0f}%)")
    ax1.scatter(cum_rfs[mask_mid], geos[mask_mid], s=30, c="tab:orange",
                alpha=0.6, edgecolor="black", linewidth=0.3,
                label=f"Mid ({stats['n_mid_010_to_030']}, {stats['mid_pct']:.0f}%)")
    ax1.scatter(cum_rfs[mask_lstm], geos[mask_lstm], s=30, c="tab:blue",
                alpha=0.6, edgecolor="black", linewidth=0.3,
                label=f"LSTM SOTA ({stats['n_lstm_sota_geo_gt_030']}, {stats['lstm_pct']:.0f}%)")
    ax1.axhline(DEG_MAX, color="gray", linewidth=0.5, linestyle=":", alpha=0.5)
    ax1.axhline(LSTM_MIN, color="gray", linewidth=0.5, linestyle=":", alpha=0.5)
    ax1.set_xlabel("cum_rf (less negative = better)")
    ax1.set_ylabel("Fresh 11-axis geo")
    ax1.set_title(f"N={n} cached ckpts — 3-region partition")
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Right: 1D geo histogram
    ax2.hist(geos, bins=20, color="tab:gray", edgecolor="black", linewidth=0.5)
    ax2.axvline(DEG_MAX, color="tab:red", linewidth=0.8, linestyle="--",
                label="degenerate ceiling 0.10")
    ax2.axvline(LSTM_MIN, color="tab:blue", linewidth=0.8, linestyle="--",
                label="LSTM-SOTA floor 0.30")
    ax2.set_xlabel("Fresh 11-axis geo")
    ax2.set_ylabel("Count")
    ax2.set_title("Geo histogram — bimodal: degenerate core (geo≈0.04) + LSTM core (geo≈0.37)")
    ax2.legend(loc="upper center", fontsize=8)
    ax2.grid(True, alpha=0.3)

    fig.suptitle("R139 — discrete cluster structure of N=91 trained policies", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "density.png", dpi=180)
    fig.savefig(OUT_DIR / "density.pdf")
    print("saved: density.png + .pdf")

    (OUT_DIR / "summary.json").write_text(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
