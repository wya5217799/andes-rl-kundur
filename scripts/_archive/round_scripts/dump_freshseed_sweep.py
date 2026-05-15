"""Dump 3 × 5 fresh-seed HAWE sweep scores."""
from __future__ import annotations
import math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation.paper_grade_axes import PAPER, evaluate_trace  # noqa: E402

EVAL = ROOT / "results" / "research_loop" / "eval_v4_baseline"

print(f"{'Controller':<36}  LS1     LS2     Overall")
print("-" * 64)
for s in (50, 51, 52):
    for w_pct in (50, 80, 90, 95, 98):
        ws = str(100 - w_pct).zfill(2)
        wstr = str(w_pct).zfill(2) + ws
        label = f"ddic_v4_ens_R21_freshs{s}_w{wstr}"
        rs: dict[str, float] = {}
        for sc in ("load_step_1", "load_step_2"):
            p = EVAL / f"{label}_{sc}.json"
            if p.exists():
                rs[sc] = evaluate_trace(p, PAPER[sc], is_ddic=True, label=label).overall
        if len(rs) == 2:
            scs = list(rs.values())
            ovr = math.exp(sum(math.log(max(x, 0.01)) for x in scs) / len(scs))
            ls1 = rs["load_step_1"]
            ls2 = rs["load_step_2"]
            print(f"{label:<36}  {ls1:.3f}   {ls2:.3f}   {ovr:.3f}")
