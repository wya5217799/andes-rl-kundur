"""V4 Ensemble eval — vote/avg actions across N actors per agent.

Loads 4 SAC actors from each of M ckpt-dirs, then per env step combines their
actions via {mean, median, weighted}. Outputs trace JSON same format as
eval_ddic.py for paper_grade_axes.py + Fig.7/9 ranker.

Usage:
    PY=/home/wya/andes_venv/bin/python
    $PY scripts/eval_ensemble.py \
        --ckpt-dirs results/v4_h50_s49 results/v4_8_warmstart_R21_s49 results/v4_9_ws_phif100_s44 \
        --suffixes  best best best \
        --weights 0.50 0.27 0.23 \
        --agg weighted \
        --label ddic_v4_ens3_weighted \
        --out-dir results/research_loop/eval_v4_baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import run_scenario  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

EVAL_SEED = 42
STEPS = 150


def ensemble_action(all_actors_per_agent: list[list],
                    agent_idx: int, obs_i: np.ndarray,
                    agg: str, weights: np.ndarray) -> np.ndarray:
    """Combine N actors' deterministic actions for this agent (returns 2D array)."""
    acts = np.array([
        actors[agent_idx].select_action(obs_i, deterministic=True)
        for actors in all_actors_per_agent
    ])  # shape (N_actors, 2)
    if agg == "mean":
        return acts.mean(axis=0)
    elif agg == "median":
        return np.median(acts, axis=0)
    elif agg == "weighted":
        return (weights[:, None] * acts).sum(axis=0)
    else:
        raise ValueError(f"unknown agg: {agg}")


def _ensemble_action_fn(
    all_actors_per_agent: list[list],
    agg: str,
    weights: np.ndarray,
) -> Callable[[int, dict[int, np.ndarray], int], dict[int, np.ndarray]]:
    """Build an ``action_fn`` (per ``paper_path.ActionFn``) that returns the
    per-step ensembled action for every agent.

    R57-β: at scenario boundaries (``step == 0``), call ``begin_episode``
    on every recurrent actor across every ckpt set so the LSTM hidden
    states reset. Without this, R56 LSTM ckpts evaluated through this
    closure would silently carry hidden state from a prior scenario,
    corrupting the eval. No-op for MLP actors (no ``is_recurrent``).
    """
    def _fn(step: int, obs: dict[int, np.ndarray], n_agents: int) -> dict[int, np.ndarray]:
        if step == 0:
            for actors in all_actors_per_agent:
                for ag in actors:
                    if getattr(ag, "is_recurrent", False):
                        ag.begin_episode()
        return {
            i: ensemble_action(all_actors_per_agent, i, obs[i], agg, weights)
            for i in range(n_agents)
        }
    return _fn


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt-dirs", nargs="+", required=True, help="N ckpt dirs")
    p.add_argument("--suffixes",  nargs="+", required=True, help="N suffixes (best/final)")
    p.add_argument("--weights",   nargs="+", type=float, default=None,
                   help="N weights for --agg weighted (sum to 1)")
    p.add_argument("--agg",       choices=["mean", "median", "weighted"], default="mean")
    p.add_argument("--label",     required=True)
    p.add_argument("--out-dir",   required=True)
    p.add_argument("--seed",      type=int, default=EVAL_SEED)
    args = p.parse_args()

    assert len(args.ckpt_dirs) == len(args.suffixes), "ckpt-dirs/suffixes mismatch"
    if args.agg == "weighted":
        assert args.weights is not None and len(args.weights) == len(args.ckpt_dirs)
        weights = np.array(args.weights, dtype=np.float64)
        weights = weights / weights.sum()  # normalize
    else:
        weights = np.ones(len(args.ckpt_dirs)) / len(args.ckpt_dirs)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[V4 ensemble eval] N={len(args.ckpt_dirs)} actors/agent, agg={args.agg}")
    for cd, suf in zip(args.ckpt_dirs, args.suffixes):
        print(f"  - {cd} (suffix={suf})")
    if args.agg == "weighted":
        print(f"  weights = {weights}")

    all_actors = [load_agents(Path(cd), suffix=suf) for cd, suf in zip(args.ckpt_dirs, args.suffixes)]
    print(f"[V4 ensemble] loaded {len(all_actors)} actor sets × 4 agents")

    action_fn = _ensemble_action_fn(all_actors, args.agg, weights)
    extra = {"ensemble_agg": args.agg, "n_actors": len(all_actors)}

    for scen, delta_u in SCENARIOS.items():
        print(f"[V4 ensemble] {args.label} on {scen}...")
        res = run_scenario(
            scen, delta_u,
            action_fn=action_fn,
            label=args.label,
            seed=args.seed,
            steps=STEPS,
            extra_keys=extra,
        )
        out_p = out / f"{args.label}_{scen}.json"
        with open(out_p, "w") as f:
            json.dump(res, f)
        print(f"  saved {out_p} (max_df={res['max_df']:.3f}, n_steps={res['n_steps']})")

    print(f"[V4 ensemble eval] done.")


if __name__ == "__main__":
    main()
