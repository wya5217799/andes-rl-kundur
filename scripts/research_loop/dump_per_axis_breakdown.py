"""Dump full 7-axis breakdown for the principal post-fix controllers,
for paper Table III / Appendix B residual-budget revision.

Reads cached eval JSONs in `results/research_loop/eval_v4_baseline/`,
runs `evaluate_trace` per controller × scenario, prints a wide table.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.paper_grade_axes import PAPER, evaluate_trace  # noqa: E402

EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"

PRINCIPAL = [
    ("ddic_v4_h50_s49",            "R21 (lucky)"),
    ("ddic_v4_swa_w98",            "SWA 98/2"),
    ("ddic_v4_ens2_R21ws8_w9802",  "HAWE 98/2"),
    ("ddic_v4_ens2_R21ws8_w8515",  "HAWE 85/15"),
    ("ddic_v4_8_R21_best",         "ws8 (single)"),
    ("ddic_v4_paper_s42",          "vanilla SAC s42"),
    ("no_control",                 "no_control"),
]


def main() -> int:
    for label, name in PRINCIPAL:
        is_ddic = "ddic" in label
        for scen in ("load_step_1", "load_step_2"):
            p = EVAL_DIR / f"{label}_{scen}.json"
            if not p.exists():
                continue
            ts = evaluate_trace(p, PAPER[scen], is_ddic=is_ddic, label=label)
            print(f"\n=== {name}  /  {scen}  /  overall = {ts.overall:.3f} ===")
            for a in ts.axes:
                print(
                    f"  {a.name:<22} project={a.project_value:>9.4f}  "
                    f"paper={a.paper_value:>9.4f}  score={a.score:>5.2f}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
