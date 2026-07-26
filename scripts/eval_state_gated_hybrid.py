"""Evaluate the pre-registered R264 mode-ratio gated droop residual.

The controller keeps the frozen learned policy in common-mode states and
injects a bounded droop correction when differential frequency error occupies
a larger share of the observed response:

``a = a_learned + alpha_t * (a_droop - a_learned)``

Use only from WSL with real ANDES. The script refuses to overwrite evidence
unless ``--overwrite`` is explicit.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.hybrid import (  # noqa: E402
    interpolate_static_frontier_geo,
    mode_ratio_gated_blend_action_fn,
    proportional_damping_action_fn,
)
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
    zero_action_fn,
)
from andes_rl_kundur.evaluation.physical_endpoints import (  # noqa: E402
    summarise_physical_trace,
)
from andes_rl_kundur.evaluation.summary import (  # noqa: E402
    format_headline,
    score_trace_files,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

DEFAULT_CAPS = (0.25, 0.5, 1.0)
RATIO_FULL_SCALE = 0.05
STRONG_GEO = 0.41523873085167756
STRONG_CUM_RF = -0.03671170945465312
BALANCED_GEO = 0.35
BALANCED_CUM_RF = -0.055
MECHANISM_LIFT = 0.005


def parse_caps(raw: str) -> tuple[float, ...]:
    """Parse a unique comma-separated capacity grid in ``[0, 1]``."""
    try:
        values = tuple(float(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("caps must be comma-separated numbers") from exc
    if not values:
        raise argparse.ArgumentTypeError("at least one cap is required")
    if any(not 0.0 <= value <= 1.0 for value in values):
        raise argparse.ArgumentTypeError("every cap must be in [0, 1]")
    if len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("cap values must be unique")
    return values


def capacity_label(capacity: float) -> str:
    return f"c{capacity:.3f}".replace(".", "p")


def write_json(path: Path, payload: object, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _load_static_rows(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load static frontier {path}: {exc}") from exc
    rows = payload.get("results")
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError(f"{path}: expected at least two static result rows")
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt-dir", required=True)
    parser.add_argument("--suffix", default="best")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--static-summary",
        default="results/r262_hybrid_blend/hybrid_blend_summary.json",
    )
    parser.add_argument("--caps", type=parse_caps, default=DEFAULT_CAPS)
    parser.add_argument("--ratio-full-scale", type=float, default=RATIO_FULL_SCALE)
    parser.add_argument("--droop-k", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=150)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if tuple(args.caps) != DEFAULT_CAPS:
        raise ValueError(f"R264 requires pre-registered caps {DEFAULT_CAPS}")
    if args.ratio_full_scale != RATIO_FULL_SCALE:
        raise ValueError(f"R264 requires ratio_full_scale={RATIO_FULL_SCALE}")
    if args.droop_k != 10.0 or args.seed != 42 or args.steps != 150:
        raise ValueError("R264 requires droop_k=10, seed=42, and steps=150")

    static_path = Path(args.static_summary)
    static_rows = _load_static_rows(static_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "_no_control_cache"
    cache_dir.mkdir(exist_ok=True)

    print(f"[mode gate] loading actors from {args.ckpt_dir} (suffix={args.suffix})")
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
        print(f"[no control] {scenario}: n={record['n_steps']}")

    rows: list[dict[str, Any]] = []
    for cap in args.caps:
        cap_label = capacity_label(cap)
        label = f"mode_gate_{cap_label}"
        cap_dir = out_dir / cap_label
        cap_dir.mkdir(exist_ok=True)
        for scenario, source in no_control_paths.items():
            destination = cap_dir / f"no_control_{scenario}.json"
            if destination.exists() and not args.overwrite:
                raise FileExistsError(f"refusing to overwrite existing artifact: {destination}")
            shutil.copyfile(source, destination)

        gate = mode_ratio_gated_blend_action_fn(
            learned_fn,
            droop_fn,
            alpha_cap=cap,
            ratio_full_scale=args.ratio_full_scale,
        )
        trace_paths: dict[str, Path] = {}
        physical: dict[str, dict[str, Any]] = {}
        telemetry: dict[str, dict[str, Any]] = {}
        print(f"\n[mode gate] alpha_cap={cap:.3f}")
        for scenario, delta_u in SCENARIOS.items():
            record = run_scenario(
                scenario,
                delta_u,
                action_fn=gate,
                label=label,
                seed=args.seed,
                steps=args.steps,
                extra_keys={
                    "gate_type": "common_differential_mode_ratio",
                    "alpha_cap": cap,
                    "ratio_full_scale": args.ratio_full_scale,
                    "droop_k": args.droop_k,
                    "learned_checkpoint": str(args.ckpt_dir),
                    "learned_checkpoint_suffix": args.suffix,
                },
            )
            record["gate_telemetry"] = gate.telemetry()
            record["physical_endpoints"] = summarise_physical_trace(record)
            path = cap_dir / f"{label}_{scenario}.json"
            write_json(path, record, overwrite=args.overwrite)
            trace_paths[scenario] = path
            physical[scenario] = record["physical_endpoints"]
            telemetry[scenario] = record["gate_telemetry"]
            print(
                f"  {scenario}: n={record['n_steps']} "
                f"alpha_mean={record['gate_telemetry']['alpha_mean']:.4f}"
            )

        summary = score_trace_files(trace_paths, label=label, is_ddic=True)
        frontier_geo = interpolate_static_frontier_geo(
            static_rows,
            cum_rf=float(summary["cum_rf"]),
        )
        lift = float(summary["geo"]) - frontier_geo if frontier_geo is not None else None
        row: dict[str, Any] = {
            "alpha_cap": cap,
            "droop_k": args.droop_k,
            **summary,
            "static_frontier_geo_at_cum_rf": frontier_geo,
            "frontier_geo_lift": lift,
            "strong_dual_win": (
                float(summary["geo"]) > STRONG_GEO and float(summary["cum_rf"]) > STRONG_CUM_RF
            ),
            "balanced_follow_up": (
                float(summary["geo"]) >= BALANCED_GEO
                and float(summary["cum_rf"]) >= BALANCED_CUM_RF
            ),
            "mechanism_signal": lift is not None and lift >= MECHANISM_LIFT,
            "gate_telemetry": telemetry,
            "physical_endpoints": physical,
        }
        rows.append(row)
        write_json(cap_dir / f"{label}_summary.json", row, overwrite=args.overwrite)
        print(f"  -> {format_headline(summary)} frontier_lift={lift if lift is not None else '--'}")

    aggregate = {
        "controller": "common_differential_mode_ratio_gated_residual",
        "checkpoint_dir": str(args.ckpt_dir),
        "checkpoint_suffix": args.suffix,
        "static_frontier_summary": str(static_path),
        "droop_k": args.droop_k,
        "seed": args.seed,
        "steps": args.steps,
        "caps": list(args.caps),
        "ratio_full_scale": args.ratio_full_scale,
        "pre_registered_gates": {
            "strong_geo": STRONG_GEO,
            "strong_cum_rf": STRONG_CUM_RF,
            "balanced_geo": BALANCED_GEO,
            "balanced_cum_rf": BALANCED_CUM_RF,
            "mechanism_frontier_lift": MECHANISM_LIFT,
        },
        "results": rows,
    }
    aggregate_path = out_dir / "mode_gated_residual_summary.json"
    write_json(aggregate_path, aggregate, overwrite=args.overwrite)
    print(f"\n[mode gate] wrote {aggregate_path}")


if __name__ == "__main__":
    main()
