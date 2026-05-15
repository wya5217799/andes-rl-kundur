"""N1a — Dump explicit Gini + per-agent ΔH range table for the principal
controllers. Used for paper Table II / §VI-D narrative.

Reads `results/research_loop/r33_gini_vs_score.json` (which is produced
by `probes/andes_kundur/t2_gini_vs_score.py`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "results" / "research_loop" / "r33_gini_vs_score.json"


KEY_LABELS = [
    ("ddic_v4_h50_s49",            "R21 (lucky)"),
    ("ddic_v4_swa_w98",            "SWA 98/2"),
    ("ddic_v4_ens2_R21ws8_w9802",  "HAWE 98/2"),
    ("ddic_v4_ens2_R21ws8_w8515",  "HAWE 85/15"),
    ("ddic_v4_8_R21_best",         "ws8 (single)"),
    ("ddic_v4_9_phif100_s44",      "phif100_s44 (cross-seed)"),
    ("ddic_v4_ctde_R21_s49",       "CTDE"),
    ("ddic_v4_paper_s42",          "vanilla SAC s42"),
    ("no_control",                 "no_control"),
]


def main() -> int:
    data = json.loads(DATA.read_text())
    rows = data["rows"]

    print(
        f"{'Controller':<28} {'score':>7}  "
        f"{'Gini LS1':>9} {'Gini LS2':>9}  "
        f"{'range LS1 (p.u.)':>32}  {'range LS2 (p.u.)':>32}"
    )
    print("-" * 130)
    for label, name in KEY_LABELS:
        ls1 = next(
            (r for r in rows if r["label"] == label and r["scenario"] == "load_step_1"),
            None,
        )
        ls2 = next(
            (r for r in rows if r["label"] == label and r["scenario"] == "load_step_2"),
            None,
        )
        score = ls1["score"] if ls1 else (ls2["score"] if ls2 else None)
        g1 = ls1["gini"] if ls1 else float("nan")
        g2 = ls2["gini"] if ls2 else float("nan")
        r1 = ls1["range_per_agent"] if ls1 else None
        r2 = ls2["range_per_agent"] if ls2 else None
        r1s = (
            "[" + ", ".join(f"{x:5.2f}" for x in r1) + "]" if r1 else "NA"
        )
        r2s = (
            "[" + ", ".join(f"{x:5.2f}" for x in r2) + "]" if r2 else "NA"
        )
        score_str = f"{score:.3f}" if score is not None else "NA"
        print(
            f"{name:<28} {score_str:>7}  "
            f"{g1:>9.3f} {g2:>9.3f}  {r1s:>32}  {r2s:>32}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
