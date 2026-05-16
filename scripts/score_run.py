"""Consolidated paper-grade scoring driver.

Replaces the ~6 ``_r{N}_score_*.py`` round-driver scripts that accumulated
during R38–R49 and were archived in Codex's R45
(``scripts/_archive/round_scripts/_r{38,40,41,42}_score_*.py``). Those
scripts all did the same dance:

    for seed in SEEDS:
        ckpt = ROOT/"results"/f"<config>_s{seed}"
        eval_ddic on ckpt -> trace JSONs
        evaluate_trace(..., is_ddic=True) -> per-scenario overall
        geo-mean across LS1 + LS2 -> single 6-axis number per seed
    aggregate to mean / range / std

R50 optimization E unifies that pattern. The library API is two functions:

  ``score_seed(ckpt_dir, ...)``  : load actors → run scenarios → per-seed dict
  ``aggregate_scores(per_seed)`` : pure aggregator → summary dict

``aggregate_scores`` is fully unit-testable (no ANDES dependency).
``score_seed`` is exercised by the existing R44 / R47 / R48 / R49
inline-scoring patterns; tests for it would require a real ckpt and an
ANDES session, so it's smoke-tested via the CLI rather than pytest.

Usage (library):

    from score_run import aggregate_scores
    per_seed = {49: {"LS1": 0.28, "LS2": 0.30, "geo": 0.29}}
    summary = aggregate_scores(per_seed)

Usage (CLI):

    $ python scripts/score_run.py \\
        --label td3_norm_h64 \\
        --ckpt-dirs results/td3_norm_h64_s49 results/td3_norm_h64_s50 \\
        --out-dir results/research_loop \\
        --suffix best
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def aggregate_scores(
    per_seed: dict[int, dict[str, float]],
) -> dict[str, Any]:
    """Aggregate per-seed score records into a summary dict.

    ``per_seed`` maps seed -> {"LS1": float, "LS2": float, "geo": float}.
    Returns a dict suitable for JSON serialization with keys:
        n_seeds, mean_geo, min_geo, max_geo, std_geo, per_seed

    Empty input is handled gracefully: ``n_seeds=0`` with ``None`` for
    every aggregate so the result JSON is well-formed.
    """
    geos = [rec["geo"] for rec in per_seed.values()]
    if not geos:
        return {
            "n_seeds": 0,
            "mean_geo": None,
            "min_geo": None,
            "max_geo": None,
            "std_geo": None,
            "per_seed": dict(per_seed),
        }
    return {
        "n_seeds": len(geos),
        "mean_geo": sum(geos) / len(geos),
        "min_geo": min(geos),
        "max_geo": max(geos),
        "std_geo": statistics.stdev(geos) if len(geos) > 1 else 0.0,
        "per_seed": dict(per_seed),
    }


def score_seed(
    ckpt_dir: Path,
    *,
    label: str,
    out_dir: Path,
    suffix: str = "best",
    seed: int = 42,
    steps: int = 150,
    config: Any = None,
) -> dict[str, float]:
    """Run one ckpt's actors across the paper scenarios and return the
    per-scenario overall scores + geo-mean.

    Heavy: imports ANDES via the env, runs TDS for each scenario.
    Returns ``{"LS1": overall_ls1, "LS2": overall_ls2, "geo": geo_mean}``.
    Trace JSONs are written under ``out_dir`` with the standard
    ``<label>_<scenario>.json`` naming so paper_grade_axes can re-score.
    """
    from andes_rl_kundur.agents.checkpoint_loader import load_agents
    from andes_rl_kundur.evaluation.paper_grade_axes import (
        PAPER, evaluate_trace,
    )
    from andes_rl_kundur.evaluation.paper_path import (
        deterministic_actor_action_fn, run_scenario,
    )
    from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS

    out_dir.mkdir(parents=True, exist_ok=True)
    agents = load_agents(ckpt_dir, suffix=suffix)
    action_fn = deterministic_actor_action_fn(agents)

    per_scen: dict[str, float] = {}
    for scen_name, delta_u in SCENARIOS.items():
        rec = run_scenario(
            scen_name, delta_u,
            action_fn=action_fn,
            label=label, seed=seed, steps=steps,
            config=config,
        )
        out_path = out_dir / f"{label}_{scen_name}.json"
        out_path.write_text(json.dumps(rec), encoding="utf-8")
        ts = evaluate_trace(out_path, PAPER[scen_name], is_ddic=True, label=label)
        per_scen[scen_name] = ts.overall

    ls1, ls2 = per_scen.get("load_step_1"), per_scen.get("load_step_2")
    geo = math.exp(
        sum(math.log(max(v, 0.01)) for v in per_scen.values()) / len(per_scen)
    )
    return {"LS1": ls1, "LS2": ls2, "geo": geo}


def _seed_from_ckpt_dir(ckpt_dir: Path) -> int:
    """Best-effort extract of the trailing seed integer from a path like
    ``results/td3_norm_h64_s49`` -> 49. Falls back to dir-index if no match."""
    name = ckpt_dir.name
    suffix = name.rsplit("_s", 1)[-1] if "_s" in name else name
    return int(suffix) if suffix.isdigit() else 0


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True, help="Run label prefix")
    parser.add_argument(
        "--ckpt-dirs", nargs="+", type=Path, required=True,
        help="One or more results/<config>_s<seed>/ dirs",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=ROOT / "results" / "research_loop" / "eval_v4_baseline",
    )
    parser.add_argument("--suffix", default="best")
    parser.add_argument("--seed", type=int, default=42, help="Env seed")
    parser.add_argument("--steps", type=int, default=150)
    args = parser.parse_args()

    per_seed: dict[int, dict[str, float]] = {}
    for ckpt_dir in args.ckpt_dirs:
        seed_id = _seed_from_ckpt_dir(ckpt_dir)
        seed_label = f"{args.label}_s{seed_id}"
        print(f"[score_run] scoring {ckpt_dir} -> {seed_label}")
        rec = score_seed(
            ckpt_dir, label=seed_label, out_dir=args.out_dir,
            suffix=args.suffix, seed=args.seed, steps=args.steps,
        )
        per_seed[seed_id] = rec
        print(
            f"  LS1={rec['LS1']:.4f}  LS2={rec['LS2']:.4f}  geo={rec['geo']:.4f}"
        )

    summary = aggregate_scores(per_seed)
    print()
    print(f"=== {args.label} ({summary['n_seeds']}-seed) ===")
    if summary["n_seeds"] > 0:
        print(
            f"  geo: mean={summary['mean_geo']:.4f}  "
            f"range=[{summary['min_geo']:.4f}, {summary['max_geo']:.4f}]  "
            f"std={summary['std_geo']:.4f}"
        )

    summary_path = args.out_dir / f"{args.label}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n-> {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
