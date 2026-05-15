"""Quick dump of single-actor scores for fresh seeds 50/51/52
(the dump_eval_v4_ranking.py output truncates because head -25 cuts
the middle of the ranking; this targets just the 3 entries we need).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.paper_grade_axes import PAPER, evaluate_trace  # noqa: E402

EVAL = ROOT / "results" / "research_loop" / "eval_v4_baseline"

for s in (49, 50, 51, 52):
    label = f"ddic_v4_h50_s{s}"
    rows: dict[str, float] = {}
    for scen in ("load_step_1", "load_step_2"):
        p = EVAL / f"{label}_{scen}.json"
        if p.exists():
            ts = evaluate_trace(p, PAPER[scen], is_ddic=True, label=label)
            rows[scen] = ts.overall
    if len(rows) == 2:
        scs = list(rows.values())
        ovr = math.exp(
            sum(math.log(max(x, 0.01)) for x in scs) / len(scs)
        )
        ls1 = rows["load_step_1"]
        ls2 = rows["load_step_2"]
        print(f"{label}  ls1={ls1:.3f}  ls2={ls2:.3f}  overall={ovr:.3f}")
