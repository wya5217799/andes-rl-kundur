"""R61 Track A — SAC HAWE ensemble on R58 strict_radsec ckpts under paper metric.

Reuses R58 paper_strict_pure_radsec config (PHI_ABS=0, PHI=1.0, rad/s) and
the 20-scen paper_strict_eval test set. Aggregates 3 SAC actors per agent
(s49/s50/s51) via {mean, median, weighted} HAWE schemes.

Output: results/research_loop/r61_sac_hawe_paper_metric.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.evaluation.paper_strict_eval import (  # noqa: E402
    compute_global_cum_rf,
    generate_test_scenarios,
)


def _ensemble_action_fn(all_actors, agg, weights):
    def _fn(step, obs, n_agents):
        if step == 0:
            for actors in all_actors:
                for ag in actors:
                    if getattr(ag, "is_recurrent", False):
                        ag.begin_episode()
        out = {}
        for i in range(n_agents):
            acts = np.array([
                actors[i].select_action(obs[i], deterministic=True)
                for actors in all_actors
            ])
            if agg == "mean":
                out[i] = acts.mean(axis=0)
            elif agg == "median":
                out[i] = np.median(acts, axis=0)
            elif agg == "weighted":
                out[i] = (weights[:, None] * acts).sum(axis=0)
        return out
    return _fn


def run_config(label, all_actors, agg, weights, scenarios, config):
    action_fn = _ensemble_action_fn(all_actors, agg, weights)
    total = 0.0
    a1 = None
    a2 = None
    per_scen = []
    for i, scen in enumerate(scenarios):
        trace = run_scenario(
            scen_name=scen["name"],
            delta_u=scen["delta_u"],
            action_fn=action_fn,
            label=label,
            seed=42,
            steps=50,
            config=config,
        )
        cum_rf = compute_global_cum_rf(trace)
        per_scen.append({"name": scen["name"], "cum_rf": cum_rf})
        total += cum_rf
        if i == 0:
            a1 = cum_rf
        elif i == 1:
            a2 = cum_rf
    return {
        "label": label,
        "agg": agg,
        "weights": weights.tolist() if weights is not None else None,
        "total_cum_rf": total,
        "mean_cum_rf": total / len(scenarios),
        "anchor_LS1": a1,
        "anchor_LS2": a2,
        "per_scenario": per_scen,
    }


def main() -> int:
    ckpt_dirs = [
        Path("results/r58_paper_strict_pure_radsec_sac_s49"),
        Path("results/r58_paper_strict_pure_radsec_sac_s50"),
        Path("results/r58_paper_strict_pure_radsec_sac_s51"),
    ]
    print(f"[r61 HAWE-SAC] loading 3 SAC actor sets × 4 agents from R58 radsec ckpts")
    all_actors = [load_agents(cd, suffix="best") for cd in ckpt_dirs]

    config = V4Config.paper_strict_pure_radsec()
    scenarios = generate_test_scenarios(n=20, seed=2026, include_anchors=True)
    print(f"[r61 HAWE-SAC] 20-scen paper_strict_eval test set, paper_strict_pure_radsec config")

    configs = [
        ("hawe_sac_mean",          "mean",     np.array([1/3, 1/3, 1/3])),
        ("hawe_sac_median",        "median",   None),
        ("hawe_sac_s50_anchor",    "weighted", np.array([0.2, 0.6, 0.2])),
        ("hawe_sac_top2_s50s51",   "weighted", np.array([0.0, 0.6, 0.4])),
        ("hawe_sac_top2_s50s49",   "weighted", np.array([0.4, 0.6, 0.0])),
    ]

    results = {}
    for label, agg, weights in configs:
        print(f"\n=== {label} (agg={agg}) ===")
        res = run_config(label, all_actors, agg, weights, scenarios, config)
        results[label] = res
        print(f"  total_cum_rf = {res['total_cum_rf']:.4f}")
        print(f"  mean_cum_rf  = {res['mean_cum_rf']:.4f}")
        print(f"  anchor_LS1   = {res['anchor_LS1']:.4f}")
        print(f"  anchor_LS2   = {res['anchor_LS2']:.4f}")

    out_path = Path("results/research_loop/r61_sac_hawe_paper_metric.json")
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n-> {out_path}")

    # Summary table
    print()
    print("=" * 75)
    print("R61 HAWE-SAC paper-metric summary")
    print("=" * 75)
    print(f"{'config':<26}  {'total':>10}  {'mean':>10}  {'LS1':>10}  {'LS2':>10}")
    print(f"{'-'*26}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")
    # Baselines for comparison
    print(f"{'(R58 SAC s50 single)':<26}  {-0.397:>10.4f}  {-0.0198:>10.4f}  {-0.054:>10.4f}  {-0.042:>10.4f}")
    print(f"{'(R58 SAC 3-seed mean)':<26}  {-0.518:>10.4f}  {-0.0259:>10.4f}  {'--':>10}  {'--':>10}")
    for label, agg, _ in configs:
        r = results[label]
        print(f"{label:<26}  {r['total_cum_rf']:>10.4f}  {r['mean_cum_rf']:>10.4f}  "
              f"{r['anchor_LS1']:>10.4f}  {r['anchor_LS2']:>10.4f}")
    print()
    print("Reference — paper §8.4 LS1=-0.68 LS2=-0.52 (DDIC, paper MADRL SOTA)")
    print("            our no-control LS1=-0.118 LS2=-0.097 (R60 scale check)")
    print("            paper no-control LS1=-1.61 LS2=-0.80")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
