"""R160 disturbance magnitude sweep — robustness of R154 SOTA across
load step magnitudes.

Paper scenarios use LS1 = -2.48 (248 MW reduction at Bus 14) and LS2 =
+1.88 (188 MW increase at Bus 15). R160 sweeps each ±20% to test if
the 4-way HAWE ensemble generalises beyond the exact training-time
disturbance magnitudes.

Output: results/r160_disturbance_sweep/{summary.csv, magnitude_curve.png}.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    # we need ANDES for env eval; let it fail naturally if not WSL-side
    pass

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa
from andes_rl_kundur.evaluation.ensemble import build_ensemble_action_fn  # noqa
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa
from andes_rl_kundur.evaluation.summary import score_trace_files  # noqa


CKPTS = [
    ("r72_w4_lstm_tau001_warmup5_s54", "best"),
    ("r142_w1_qr51_s54", "best"),
    ("r143_w1_qr51_s54_fixed", "best"),
    ("r100_w1_hreg_lambda0p01_s54", "best"),
]

# Magnitude sweep — paper is at -2.48 / +1.88. Test ±20%.
# Map to magnitude scale 1.0 = paper exact.
SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]
LS1_BASE = -2.48
LS2_BASE = +1.88

OUT = ROOT / "results" / "r160_disturbance_sweep"
OUT.mkdir(parents=True, exist_ok=True)


def build_actor_pools():
    pools = []
    for name, suffix in CKPTS:
        ckpt_dir = ROOT / "results" / name
        actors = load_agents(ckpt_dir, suffix=suffix)
        pools.append(actors)
    return pools


def eval_one_scen(pools, scen_name, delta_u, scale, label):
    """Run one scenario at a given magnitude."""
    action_fn = build_ensemble_action_fn(pools, agg="mean", weights=None)
    rep = run_scenario(scen_name, delta_u, action_fn=action_fn, label=label,
                       seed=42, steps=150)
    return rep


def main():
    print(f"Loading 4 ckpt pools...")
    pools = build_actor_pools()
    print(f"  {len(pools)} pools loaded.")

    rows = []
    for scale in SCALES:
        ls1_mag = LS1_BASE * scale
        ls2_mag = LS2_BASE * scale
        label = f"r160_sota_scale{scale:.2f}"
        ls1_du = {"PQ_Bus14": ls1_mag}
        ls2_du = {"PQ_Bus15": ls2_mag}

        # Write traces, then score
        rep_ls1 = eval_one_scen(pools, "load_step_1", ls1_du, scale, label)
        rep_ls2 = eval_one_scen(pools, "load_step_2", ls2_du, scale, label)
        ls1_path = OUT / f"{label}_load_step_1.json"
        ls2_path = OUT / f"{label}_load_step_2.json"
        ls1_path.write_text(json.dumps(rep_ls1))
        ls2_path.write_text(json.dumps(rep_ls2))

        # Score
        from andes_rl_kundur.evaluation.summary import score_trace_files
        scores = score_trace_files(
            {"load_step_1": ls1_path, "load_step_2": ls2_path}, label=label
        )
        geo = scores.get("geo", scores.get("mean_geo", 0.0))
        ls1 = scores.get("LS1", scores.get("per_seed", {}).get("42", {}).get("LS1", 0.0))
        ls2 = scores.get("LS2", scores.get("per_seed", {}).get("42", {}).get("LS2", 0.0))
        cum_rf = scores.get("cum_rf", 0.0)
        rows.append({"scale": scale, "ls1_mag": ls1_mag, "ls2_mag": ls2_mag,
                      "geo": geo, "LS1": ls1, "LS2": ls2, "cum_rf": cum_rf})
        print(f"  scale={scale:.2f} LS1={ls1_mag:+.3f}/{ls1:.4f} "
              f"LS2={ls2_mag:+.3f}/{ls2:.4f} geo={geo:.4f}")

    # Save summary
    import csv
    with open(OUT / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    scales = [r["scale"] for r in rows]
    ax.plot(scales, [r["geo"] for r in rows], "-o", color="C0", label="geo")
    ax.plot(scales, [r["LS1"] for r in rows], "-^", color="C1", label="LS1 axis")
    ax.plot(scales, [r["LS2"] for r in rows], "-s", color="C2", label="LS2 axis")
    ax.axvline(1.0, color="red", lw=0.7, ls="--", label="paper disturbance")
    ax.set_xlabel("disturbance magnitude scale (1.0 = paper)")
    ax.set_ylabel("eval score")
    ax.set_title("R160 R154 SOTA ensemble disturbance-magnitude robustness")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "magnitude_curve.pdf")
    fig.savefig(OUT / "magnitude_curve.png", dpi=140)
    plt.close(fig)

    geos = [r["geo"] for r in rows]
    import statistics
    print(f"\n=== R160 summary ===")
    print(f"  N={len(rows)}, mean(geo)={statistics.mean(geos):.4f}, "
          f"std(geo)={statistics.stdev(geos):.5f}")
    print(f"  min={min(geos):.4f}, max={max(geos):.4f}")
    print(f"\nWritten: {OUT}/{{summary.csv, magnitude_curve.{{pdf,png}}}}")


if __name__ == "__main__":
    main()
