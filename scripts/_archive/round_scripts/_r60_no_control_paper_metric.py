"""One-shot no-control paper-metric eval (R60, Q-0009 scale check).

Runs zero_action_fn against the same 20-scen paper_strict_eval test set
and reports anchor LS1 / LS2 + total_cum_rf vs paper §8.3/§8.4:

  paper no-control LS1 = -1.61
  paper no-control LS2 = -0.80
  paper no-control 50-ep cumulative = -15.2

Apples-to-apples conditions:
  - dt = 0.2 s, M = 50, t_end = 10 s (paper aligned)
  - LS1 = PQ_Bus14 -2.48 pu (paper case 1)
  - LS2 = PQ_Bus15 +1.88 pu (paper case 2)

Output: results/research_loop/r60_no_control_paper_metric.json
"""
from __future__ import annotations

import json
from pathlib import Path

from andes_rl_kundur.env.andes.v4_config import V4Config
from andes_rl_kundur.evaluation.paper_path import (
    run_scenario,
    zero_action_fn,
)
from andes_rl_kundur.evaluation.paper_strict_eval import (
    compute_global_cum_rf,
    generate_test_scenarios,
)


def main() -> int:
    config = V4Config.paper_strict_pure_radsec()
    scenarios = generate_test_scenarios(n=20, seed=2026, include_anchors=True)

    out_dir = Path("results/research_loop/r60_no_control_traces")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = 0.0
    anchor_LS1 = None
    anchor_LS2 = None

    for i, scen in enumerate(scenarios):
        trace = run_scenario(
            scen_name=scen["name"],
            delta_u=scen["delta_u"],
            action_fn=zero_action_fn,
            label="r60_no_control",
            seed=42,
            steps=50,
            config=config,
        )
        cum_rf = compute_global_cum_rf(trace)
        record = {
            "name": scen["name"],
            "delta_u": scen["delta_u"],
            "cum_rf": cum_rf,
            "n_steps": trace.get("n_steps", 0),
        }
        results.append(record)
        total += cum_rf
        if i == 0:
            anchor_LS1 = cum_rf
        elif i == 1:
            anchor_LS2 = cum_rf
        print(f"  [{i+1}/20] {scen['name']}: cum_rf = {cum_rf:.4f}")

    summary = {
        "label": "r60_no_control",
        "n_scenarios": len(scenarios),
        "scenarios": results,
        "total_cum_rf": total,
        "mean_cum_rf": total / max(len(scenarios), 1),
        "anchor_LS1": anchor_LS1,
        "anchor_LS2": anchor_LS2,
    }

    out_path = Path("results/research_loop/r60_no_control_paper_metric.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print("=" * 60)
    print("No-control paper-metric eval (R60 / Q-0009 scale check)")
    print("=" * 60)
    print(f"  anchor LS1 = {anchor_LS1:.4f}   (paper -1.61, no control)")
    print(f"  anchor LS2 = {anchor_LS2:.4f}   (paper -0.80, no control)")
    print(f"  total_cum_rf (20 scen) = {total:.4f}")
    print(f"  50-scen extrapolation  = {total * 2.5:.4f}   (paper -15.2, no control)")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
