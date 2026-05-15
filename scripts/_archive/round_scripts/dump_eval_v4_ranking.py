"""Dump the post-fix `eval_v4_baseline` ranking to a manifest JSON +
print a top-20 / bottom-5 summary. Used by handoff_v14 / r31.

Run (WSL)::

    /home/wya/andes_venv/bin/python scripts/research_loop/dump_eval_v4_ranking.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.paper_grade_axes import PAPER, evaluate_trace  # noqa: E402

EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT = ROOT / "results" / "research_loop" / "r31_eval_v4_baseline_ranking.json"


def main() -> int:
    labels = sorted(set(
        f.replace("_load_step_1.json", "").replace("_load_step_2.json", "")
        for f in os.listdir(EVAL_DIR) if f.endswith(".json")
    ))

    rows: list[dict] = []
    for lbl in labels:
        scen_scores: dict[str, float] = {}
        for scen in ("load_step_1", "load_step_2"):
            p = EVAL_DIR / f"{lbl}_{scen}.json"
            if not p.exists():
                continue
            ts = evaluate_trace(p, PAPER[scen],
                                is_ddic=("ddic" in lbl), label=lbl)
            scen_scores[scen] = float(ts.overall)
        if len(scen_scores) != 2:
            continue
        scs = list(scen_scores.values())
        overall = math.exp(
            sum(math.log(max(x, 0.01)) for x in scs) / len(scs)
        )
        rows.append({
            "label": lbl,
            "ls1": scen_scores["load_step_1"],
            "ls2": scen_scores["load_step_2"],
            "overall": float(overall),
        })

    rows.sort(key=lambda r: -r["overall"])

    manifest = {
        "generated_ts": "2026-05-07",
        "ranker_version": (
            "post-N1c (B1+B2 settling fix) + post-r30 (C1 geo-mean / "
            "C2 NaN / tds_failed guards)"
        ),
        "n_ckpts": len(rows),
        "axes_per_ddic": 7,
        "axes_per_no_control": 3,
        "aggregation": (
            "geo_mean(max(s,0.01)) over axes; geo_mean(max(s,0.01)) "
            "over scenarios"
        ),
        "ranking": rows,
    }
    OUT.write_text(json.dumps(manifest, indent=2))

    print("=== TOP 20 ===")
    for i, r in enumerate(rows[:20], 1):
        label = r["label"]
        ls1 = r["ls1"]
        ls2 = r["ls2"]
        ov = r["overall"]
        print(f"  {i:>3d}  {label:<48} ls1={ls1:.3f}  ls2={ls2:.3f}  overall={ov:.3f}")

    print("\n=== BOTTOM 5 ===")
    n = len(rows)
    for i, r in list(enumerate(rows, 1))[-5:]:
        label = r["label"]
        ls1 = r["ls1"]
        ls2 = r["ls2"]
        ov = r["overall"]
        print(f"  {i:>3d}  {label:<48} ls1={ls1:.3f}  ls2={ls2:.3f}  overall={ov:.3f}")

    print(f"\nwrote {OUT.relative_to(ROOT)} ({n} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
