"""R58 paper-strict eval driver — paper Sec.IV-C metric on N=20 scenarios.

Iterates over a list of ckpt directories (or a single one); for each,
loads the 4 trained actors, runs them through 20 R58 test scenarios
(LS1 + LS2 + 18 random, fixed seed=2026), and computes the paper
Sec.IV-C cumulative global frequency reward
``-Σ_t Σ_i (f_i,t - f̄_t)²``.

Output JSON shape:
    {
        "ckpt_dir": <str>,
        "label": <str>,                # ckpt label (basename)
        "n_scenarios": 20,
        "scenarios": [
            {"name": "load_step_1", "delta_u": {...},
             "cum_rf": <float>, "n_steps": <int>, "tds_failed": <bool>},
            ...
        ],
        "total_cum_rf": <float>,       # sum over all scenarios
        "mean_cum_rf": <float>,        # avg per scenario
        "anchor_LS1": <float>,         # paper-comparable (paper: -0.68 DDIC)
        "anchor_LS2": <float>,         # paper-comparable (paper: -0.52 DDIC)
    }

Per ckpt dir, writes a summary to
``results/research_loop/r58_paper_metric_<label>.json``. Multi-ckpt
batch run also writes an aggregate to
``results/research_loop/r58_paper_metric_all.json``.

Usage:
    /home/wya/andes_venv/bin/python scripts/_r58_paper_strict_eval.py \\
        --ckpt-dirs results/td3_lstm_h64_warmup5_s51 \\
                    results/td3_norm_h64_s51 \\
                    results/sac_norm_h64_s51 \\
        --out-dir results/research_loop
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.evaluation.paper_strict_eval import (  # noqa: E402
    compute_global_cum_rf,
    generate_test_scenarios,
)


def evaluate_ckpt(
    ckpt_dir: Path,
    scenarios: list[dict[str, Any]],
    *,
    label: str | None = None,
    suffix: str = "best",
    env_seed: int = 42,
    steps: int = 50,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a single ckpt across the given scenarios, return summary.

    Args:
        ckpt_dir: Directory holding ``agent_{0..3}_<suffix>.pt``.
        scenarios: List of ``{name, delta_u}`` dicts (from
            ``generate_test_scenarios``).
        label: Human-readable ckpt label. Defaults to ``ckpt_dir.name``.
        suffix: ckpt suffix (``"best"`` or ``"final"``).
        env_seed: ANDES TDS seed (kept fixed across runs for paper
            comparability; paper Sec.IV-A doesn't specify but our
            R56/R57 convention is 42).
        steps: max steps per scenario. Paper M=50; default matches.
        out_dir: optional. If given, writes per-scenario trace JSONs
            here under ``<label>_<scen_name>.json``.

    Returns:
        Summary dict (see module docstring).
    """
    if label is None:
        label = ckpt_dir.name
    agents = load_agents(ckpt_dir, suffix=suffix)
    action_fn = deterministic_actor_action_fn(agents)

    per_scen_records: list[dict[str, Any]] = []
    total_cum_rf = 0.0
    anchor_LS1: float | None = None
    anchor_LS2: float | None = None

    for scen in scenarios:
        name = scen["name"]
        delta_u = scen["delta_u"]
        trace = run_scenario(
            name, delta_u,
            action_fn=action_fn,
            label=label, seed=env_seed, steps=steps,
        )
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{label}_{name}.json").write_text(
                json.dumps(trace), encoding="utf-8"
            )
        cum_rf = compute_global_cum_rf(trace)
        rec = {
            "name": name,
            "delta_u": delta_u,
            "cum_rf": cum_rf,
            "n_steps": trace.get("n_steps", 0),
            "tds_failed": trace.get("n_steps", 0) < steps and not trace.get("traces"),
        }
        per_scen_records.append(rec)
        total_cum_rf += cum_rf
        if name == "load_step_1":
            anchor_LS1 = cum_rf
        elif name == "load_step_2":
            anchor_LS2 = cum_rf

    summary = {
        "ckpt_dir": str(ckpt_dir),
        "label": label,
        "n_scenarios": len(scenarios),
        "scenarios": per_scen_records,
        "total_cum_rf": total_cum_rf,
        "mean_cum_rf": total_cum_rf / max(len(scenarios), 1),
        "anchor_LS1": anchor_LS1,
        "anchor_LS2": anchor_LS2,
    }
    return summary


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ckpt-dirs", nargs="+", type=Path, required=True,
        help="One or more ckpt directories to evaluate.",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=ROOT / "results" / "research_loop",
        help="Output directory for per-ckpt + aggregate summaries.",
    )
    parser.add_argument("--suffix", default="best")
    parser.add_argument(
        "--env-seed", type=int, default=42,
        help="ANDES env seed (matches R56/R57 convention).",
    )
    parser.add_argument(
        "--scen-seed", type=int, default=2026,
        help="Test scenario generation seed (R58 default 2026).",
    )
    parser.add_argument(
        "--n-scen", type=int, default=20,
        help="Number of test scenarios (R58 default 20 = 2 anchors + 18 random).",
    )
    parser.add_argument(
        "--steps", type=int, default=50,
        help="Max steps per scenario (paper M=50).",
    )
    parser.add_argument(
        "--trace-out-dir", type=Path, default=None,
        help="Optional: directory to dump per-scenario trace JSONs. "
             "Useful for off-line analysis; large.",
    )
    args = parser.parse_args()

    scenarios = generate_test_scenarios(
        n=args.n_scen, seed=args.scen_seed, include_anchors=True,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)

    all_summaries = []
    for ckpt_dir in args.ckpt_dirs:
        print(f"[r58-eval] {ckpt_dir.name}")
        summary = evaluate_ckpt(
            ckpt_dir, scenarios,
            suffix=args.suffix,
            env_seed=args.env_seed,
            steps=args.steps,
            out_dir=args.trace_out_dir,
        )
        out_path = args.out_dir / f"r58_paper_metric_{summary['label']}.json"
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(
            f"  total_cum_rf = {summary['total_cum_rf']:.4f}  "
            f"mean = {summary['mean_cum_rf']:.4f}  "
            f"LS1 = {summary['anchor_LS1']:+.4f}  "
            f"LS2 = {summary['anchor_LS2']:+.4f}"
        )
        all_summaries.append(summary)

    if len(all_summaries) > 1:
        agg_path = args.out_dir / "r58_paper_metric_all.json"
        agg_path.write_text(
            json.dumps({"runs": all_summaries}, indent=2), encoding="utf-8"
        )
        print(f"\nAggregate written to {agg_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
