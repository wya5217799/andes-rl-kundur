"""R69 v3.0 11-axis re-rank — reads existing LS1/LS2 trace JSONs and scores
them under the 11-axis ranker (v3 axes 9-11 included).

Compares against the 8-axis v2 score for the same traces, so we can see
which controllers get demoted (agent collapse / oscillation / P imbalance)
and which hold up.

Usage: python scripts/_r69_rerank_11axis.py [label1 label2 ...]
       (omit args to scan all labels in eval_v4_baseline/)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from andes_rl_kundur.evaluation.aggregation import floor_geo_mean
from andes_rl_kundur.evaluation.paper_grade_axes import PAPER, evaluate_trace

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"

_NO_CTRL_PREFIXES = ("noctrl_", "no_ctrl_", "no_control_", "baseline_")


def _list_labels(args: list[str]) -> list[str]:
    if args:
        return args
    files = os.listdir(EVAL_DIR)
    labels = sorted(set(
        f.replace("_load_step_1.json", "").replace("_load_step_2.json", "")
        for f in files
        if f.endswith("_load_step_1.json") or f.endswith("_load_step_2.json")
        if not any(f.startswith(p) for p in _NO_CTRL_PREFIXES)
    ))
    return labels


def _score_label(label: str, is_ddic: bool = True) -> dict | None:
    """Score a single label across LS1 + LS2, returning v2 + v3 overall."""
    per_scen_v2: dict[str, float] = {}
    per_scen_v3: dict[str, float] = {}
    breakdowns_v3: dict[str, list] = {}

    for scen in ("load_step_1", "load_step_2"):
        p = EVAL_DIR / f"{label}_{scen}.json"
        if not p.exists():
            return None
        ts_v2 = evaluate_trace(p, PAPER[scen], is_ddic=is_ddic,
                               label=label, enable_v3_axes=False)
        ts_v3 = evaluate_trace(p, PAPER[scen], is_ddic=is_ddic,
                               label=label, enable_v3_axes=True)
        per_scen_v2[scen] = ts_v2.overall
        per_scen_v3[scen] = ts_v3.overall
        breakdowns_v3[scen] = ts_v3.axes

    if not per_scen_v2 or not per_scen_v3:
        return None

    geo_v2 = floor_geo_mean(per_scen_v2.values())
    geo_v3 = floor_geo_mean(per_scen_v3.values())

    return {
        "label": label,
        "v2_geo": geo_v2,
        "v3_geo": geo_v3,
        "v3_per_scen": per_scen_v3,
        "breakdowns_v3": breakdowns_v3,
    }


def main() -> None:
    args = sys.argv[1:]
    labels = _list_labels(args)
    print(f"Scoring {len(labels)} labels with v2 (8-axis) AND v3 (11-axis) rankers")
    print("=" * 110)

    results = []
    for lbl in labels:
        r = _score_label(lbl, is_ddic=True)
        if r is not None:
            results.append(r)

    # Sort by v3_geo (true SOTA)
    results.sort(key=lambda x: -x["v3_geo"])

    print(f"{'rank':>4s}  {'label':56s}  {'v2_geo':>8s}  {'v3_geo':>8s}  "
          f"{'delta':>7s}  {'%':>6s}")
    print("-" * 110)
    for i, r in enumerate(results, 1):
        delta = r["v3_geo"] - r["v2_geo"]
        pct = 100 * delta / max(r["v2_geo"], 0.001)
        print(f"{i:4d}  {r['label']:56s}  {r['v2_geo']:8.4f}  {r['v3_geo']:8.4f}  "
              f"{delta:+7.3f}  {pct:+5.1f}%")

    # Top-3 breakdown
    print("\n" + "=" * 110)
    print("TOP 3 v3 BREAKDOWN")
    print("=" * 110)
    for r in results[:3]:
        print(f"\n--- {r['label']} (v3 geo = {r['v3_geo']:.4f}) ---")
        for scen, axes in r["breakdowns_v3"].items():
            print(f"  [{scen}]")
            for a in axes[-3:]:  # show v3-specific axes
                print(f"    {a.name:24s} score={a.score:.3f}  {a.note}")


if __name__ == "__main__":
    main()
