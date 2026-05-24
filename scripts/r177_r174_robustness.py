"""R177 — robustness check for new SOTA R174 (hreg λ=0.002).

Mirror R160 disturbance magnitude sweep on R174 SINGLE policy
(not ensemble) to confirm 0.4139 is robust across ±20% disturbance.

Output: results/r177_r174_robustness/{summary.csv, magnitude_curve.png}.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa
from andes_rl_kundur.evaluation.paper_path import (  # noqa
    deterministic_actor_action_fn, run_scenario,
)
from andes_rl_kundur.evaluation.summary import score_trace_files  # noqa


CKPT_DIR = ROOT / "results" / "r174_w1_hreg_lambda0p002_s54"
OUT = ROOT / "results" / "r177_r174_robustness"
OUT.mkdir(parents=True, exist_ok=True)

SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]
LS1_BASE = -2.48
LS2_BASE = +1.88


def main():
    print("Loading R174 ckpt...")
    agents = load_agents(CKPT_DIR, suffix="best")
    action_fn = deterministic_actor_action_fn(agents)

    rows = []
    for scale in SCALES:
        ls1_du = {"PQ_Bus14": LS1_BASE * scale}
        ls2_du = {"PQ_Bus15": LS2_BASE * scale}
        label = f"r177_r174_scale{scale:.2f}"

        rep_ls1 = run_scenario("load_step_1", ls1_du, action_fn=action_fn,
                                label=label, seed=42, steps=150)
        rep_ls2 = run_scenario("load_step_2", ls2_du, action_fn=action_fn,
                                label=label, seed=42, steps=150)
        ls1_path = OUT / f"{label}_load_step_1.json"
        ls2_path = OUT / f"{label}_load_step_2.json"
        ls1_path.write_text(json.dumps(rep_ls1))
        ls2_path.write_text(json.dumps(rep_ls2))

        scores = score_trace_files(
            {"load_step_1": ls1_path, "load_step_2": ls2_path}, label=label
        )
        rows.append({"scale": scale,
                      "ls1_mag": LS1_BASE * scale, "ls2_mag": LS2_BASE * scale,
                      "geo": scores["geo"], "LS1": scores["LS1"], "LS2": scores["LS2"],
                      "cum_rf": scores["cum_rf"]})
        print(f"  scale={scale:.2f} geo={scores['geo']:.4f} LS1={scores['LS1']:.4f} LS2={scores['LS2']:.4f}")

    with open(OUT / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    scales = [r["scale"] for r in rows]
    ax.plot(scales, [r["geo"] for r in rows], "-o", color="C3", label="R174 single (λ=0.002)")
    ax.plot(scales, [r["LS1"] for r in rows], "-^", color="C1", label="LS1 axis", alpha=0.6)
    ax.plot(scales, [r["LS2"] for r in rows], "-s", color="C2", label="LS2 axis", alpha=0.6)
    ax.axvline(1.0, color="red", lw=0.7, ls="--", label="paper disturbance")
    ax.axhline(0.4119, color="black", lw=0.5, ls=":", label="R154 4-way ensemble SOTA 0.4119")
    ax.set_xlabel("disturbance magnitude scale (1.0 = paper)")
    ax.set_ylabel("eval score")
    ax.set_title("R177 R174 single (λ_h=0.002) disturbance-magnitude robustness")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "magnitude_curve.pdf")
    fig.savefig(OUT / "magnitude_curve.png", dpi=140)
    plt.close(fig)

    geos = [r["geo"] for r in rows]
    import statistics
    print("\n=== R177 R174 robustness ===")
    print(f"  N={len(rows)}, mean(geo)={statistics.mean(geos):.4f}, "
          f"std={statistics.stdev(geos):.5f}, range=[{min(geos):.4f}, {max(geos):.4f}]")
    print(f"  Written: {OUT}/")


if __name__ == "__main__":
    main()
