"""Evaluate a learned-controller / droop action blend on canonical LS1+LS2.

Motivation
----------
R252-R259 showed that learned recurrent control wins the project 11-axis
``geo`` metric while proportional droop wins the paper ``cum_rf`` metric.
This reusable evaluator scans a pre-declared set of convex action blends:

``action = (1 - alpha) * learned_action + alpha * droop_action``

Every alpha receives fresh real-ANDES trajectories and the canonical dual
score.  Failed or incomplete traces are rejected by ``score_trace_files``.

Usage (WSL)
-----------
::

    /home/wya/andes_venv/bin/python scripts/eval_hybrid.py \
      --ckpt-dir results/r201_w1_hreg_tau005_s54 \
      --suffix best \
      --alphas 0,0.1,0.25,0.5,0.75,0.9,1 \
      --droop-k 10 \
      --out-dir results/r262_hybrid_blend

The command refuses to overwrite controller traces unless ``--overwrite`` is
provided.  No-control reference traces are generated once and copied beside
each controller trace because the 11-axis scorer discovers them as siblings.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.hybrid import (  # noqa: E402
    convex_blend_action_fn,
    proportional_damping_action_fn,
)
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
    zero_action_fn,
)
from andes_rl_kundur.evaluation.summary import (  # noqa: E402
    format_headline,
    score_trace_files,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

DEFAULT_ALPHAS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)


def parse_alphas(raw: str) -> tuple[float, ...]:
    """Parse a comma-separated alpha grid, rejecting duplicates and drift."""
    try:
        values = tuple(float(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("alphas must be comma-separated numbers") from exc
    if not values:
        raise argparse.ArgumentTypeError("at least one alpha is required")
    if any(not 0.0 <= value <= 1.0 for value in values):
        raise argparse.ArgumentTypeError("every alpha must be in [0, 1]")
    if len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("alpha values must be unique")
    return values


def alpha_label(alpha: float) -> str:
    """Stable filesystem-safe label, e.g. ``0.25 -> a0p250``."""
    return f"a{alpha:.3f}".replace(".", "p")


def write_json(path: Path, payload: object, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt-dir", required=True)
    parser.add_argument("--suffix", default="best")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--alphas",
        type=parse_alphas,
        default=DEFAULT_ALPHAS,
        help="comma-separated blend weights (default: 0,.1,.25,.5,.75,.9,1)",
    )
    parser.add_argument("--droop-k", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=150)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "_no_control_cache"
    cache_dir.mkdir(exist_ok=True)

    print(f"[hybrid eval] loading actors from {args.ckpt_dir} (suffix={args.suffix})")
    agents = load_agents(Path(args.ckpt_dir), suffix=args.suffix)
    learned_fn = deterministic_actor_action_fn(agents)
    droop_fn = proportional_damping_action_fn(args.droop_k)

    no_control_paths: dict[str, Path] = {}
    for scenario, delta_u in SCENARIOS.items():
        path = cache_dir / f"no_control_{scenario}.json"
        record = run_scenario(
            scenario,
            delta_u,
            action_fn=zero_action_fn,
            label="no_control",
            seed=args.seed,
            steps=args.steps,
        )
        write_json(path, record, overwrite=args.overwrite)
        no_control_paths[scenario] = path
        print(f"[no control] {scenario}: n={record['n_steps']} max_df={record['max_df']:.4f}")

    rows: list[dict[str, object]] = []
    for alpha in args.alphas:
        label = f"hybrid_{alpha_label(alpha)}"
        alpha_dir = out_dir / alpha_label(alpha)
        alpha_dir.mkdir(exist_ok=True)
        for scenario, source in no_control_paths.items():
            destination = alpha_dir / f"no_control_{scenario}.json"
            if destination.exists() and not args.overwrite:
                raise FileExistsError(f"refusing to overwrite existing artifact: {destination}")
            shutil.copyfile(source, destination)

        action_fn = convex_blend_action_fn(learned_fn, droop_fn, alpha=alpha)
        trace_paths: dict[str, Path] = {}
        print(f"\n[hybrid eval] alpha={alpha:.3f}")
        for scenario, delta_u in SCENARIOS.items():
            record = run_scenario(
                scenario,
                delta_u,
                action_fn=action_fn,
                label=label,
                seed=args.seed,
                steps=args.steps,
                extra_keys={
                    "hybrid_alpha": alpha,
                    "droop_k": args.droop_k,
                    "learned_checkpoint": str(args.ckpt_dir),
                    "learned_checkpoint_suffix": args.suffix,
                },
            )
            path = alpha_dir / f"{label}_{scenario}.json"
            write_json(path, record, overwrite=args.overwrite)
            trace_paths[scenario] = path
            print(f"  {scenario}: n={record['n_steps']} max_df={record['max_df']:.4f}")

        summary = score_trace_files(trace_paths, label=label, is_ddic=True)
        row: dict[str, object] = {"alpha": alpha, "droop_k": args.droop_k, **summary}
        rows.append(row)
        write_json(alpha_dir / f"{label}_summary.json", row, overwrite=args.overwrite)
        print(f"  -> {format_headline(summary)}")

    aggregate = {
        "controller": "convex_learned_droop_blend",
        "checkpoint_dir": str(args.ckpt_dir),
        "checkpoint_suffix": args.suffix,
        "droop_k": args.droop_k,
        "seed": args.seed,
        "steps": args.steps,
        "alphas": list(args.alphas),
        "results": rows,
    }
    aggregate_path = out_dir / "hybrid_blend_summary.json"
    write_json(aggregate_path, aggregate, overwrite=args.overwrite)
    print(f"\n[hybrid eval] wrote {aggregate_path}")


if __name__ == "__main__":
    main()
