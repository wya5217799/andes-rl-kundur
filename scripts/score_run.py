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
    from andes_rl_kundur.evaluation.paper_grade_axes import RANKER_VERSION
    geos = [rec["geo"] for rec in per_seed.values()]
    if not geos:
        return {
            "ranker_version": RANKER_VERSION,
            "n_seeds": 0,
            "mean_geo": None,
            "min_geo": None,
            "max_geo": None,
            "std_geo": None,
            "per_seed": dict(per_seed),
        }
    # Import here (not module top) so a stale circular-import does not
    # break older callers that only need ``aggregate_scores`` without the
    # ranker module loaded.
    from andes_rl_kundur.evaluation.paper_grade_axes import RANKER_VERSION
    out: dict[str, Any] = {
        "ranker_version": RANKER_VERSION,
        "n_seeds": len(geos),
        "mean_geo": sum(geos) / len(geos),
        "min_geo": min(geos),
        "max_geo": max(geos),
        "std_geo": statistics.stdev(geos) if len(geos) > 1 else 0.0,
        "per_seed": dict(per_seed),
    }
    # R74 dual-eval: if records carry cum_rf (paper-metric), aggregate it too
    # so summary reports paper-metric and 6-axis side-by-side.
    cum_rfs = [rec["cum_rf"] for rec in per_seed.values() if "cum_rf" in rec]
    if cum_rfs:
        out["mean_cum_rf"] = sum(cum_rfs) / len(cum_rfs)
        out["min_cum_rf"] = min(cum_rfs)
        out["max_cum_rf"] = max(cum_rfs)
    return out


# R78: ``score_seed`` lives in the library (re-exported here for back-compat
# so existing callers keep working).
from andes_rl_kundur.evaluation.score_seed import score_seed  # noqa: E402, F401


def _seed_from_ckpt_dir(ckpt_dir: Path) -> int:
    """Best-effort extract of the trailing seed integer from a path like
    ``results/td3_norm_h64_s49`` -> 49. Falls back to dir-index if no match."""
    name = ckpt_dir.name
    suffix = name.rsplit("_s", 1)[-1] if "_s" in name else name
    return int(suffix) if suffix.isdigit() else 0


def _derive_label(ckpt_dirs: list[Path]) -> str:
    """Auto-derive ``--label`` from the single ckpt dir's name when the
    caller didn't pass one. Mirrors the historical convention: drop the
    trailing ``_s<seed>`` suffix so the label is config-only.

    Example: ``results/r239_w1_scalar_onlyphiabs_s54`` → ``r239_w1_scalar_onlyphiabs``.

    Refuses to guess when more than one ckpt dir is passed — multi-seed
    aggregation always needs an explicit label so the summary.json file
    is named meaningfully (not after one arbitrary seed's dir).
    """
    if len(ckpt_dirs) != 1:
        raise ValueError(
            f"--label is required for multi-ckpt-dir runs "
            f"(got {len(ckpt_dirs)} dirs); cannot auto-derive."
        )
    name = ckpt_dirs[0].name
    return name.rsplit("_s", 1)[0] if "_s" in name else name


def _derive_out_dir(ckpt_dirs: list[Path]) -> Path:
    """Default out-dir = the single ckpt dir itself, so
    ``<label>_summary.json`` lands alongside the trace JSONs the same
    train.py wrote (this is what every R200+ verdict has been doing
    manually). Falls back to ``results/research_loop/eval_v4_baseline``
    for multi-ckpt-dir aggregations where there's no obvious home.
    """
    if len(ckpt_dirs) == 1:
        return ckpt_dirs[0]
    return ROOT / "results" / "research_loop" / "eval_v4_baseline"


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", default=None,
                        help="Run label prefix. Auto-derived from single "
                             "--ckpt-dirs name (stripping _s<seed>) when omitted.")
    parser.add_argument(
        "--ckpt-dirs", nargs="+", type=Path, required=True,
        help="One or more results/<config>_s<seed>/ dirs",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=None,
        help="Where to write <label>_summary.json. Defaults to the "
             "single ckpt-dir itself; falls back to "
             "results/research_loop/eval_v4_baseline for multi-dir aggregates.",
    )
    parser.add_argument("--suffix", default="best")
    parser.add_argument("--seed", type=int, default=42, help="Env seed")
    parser.add_argument("--steps", type=int, default=150)
    args = parser.parse_args()
    # Apply smart defaults (CLM-0430 audit follow-up: reduce CLI footgun
    # that contributed to skipped scoring in this session)
    if args.label is None:
        args.label = _derive_label(args.ckpt_dirs)
    if args.out_dir is None:
        args.out_dir = _derive_out_dir(args.ckpt_dirs)

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
            f"  cum_rf={rec['cum_rf']:.4f}"
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
        if "mean_cum_rf" in summary:
            print(
                f"  cum_rf: mean={summary['mean_cum_rf']:.4f}  "
                f"range=[{summary['min_cum_rf']:.4f}, {summary['max_cum_rf']:.4f}]"
            )

    summary_path = args.out_dir / f"{args.label}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n-> {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
