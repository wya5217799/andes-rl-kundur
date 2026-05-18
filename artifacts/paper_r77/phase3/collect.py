"""Collect Phase 3 final_eval_summary.json across all e[1234]_* dirs.

Used to populate Sec.VII (Phase 3 stress-test) Table VI in the paper.
Run from the repository root with the WSL ANDES interpreter:

    /home/wya/andes_venv/bin/python artifacts/paper_r77/phase3/collect.py

Outputs a per-directory summary line + per-experiment aggregates.
"""
import json
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "results" / "r77_phase3"

rows = []
for d in sorted(ROOT.iterdir()):
    if not d.is_dir():
        continue
    summary = d / "final_eval_summary.json"
    if not summary.exists():
        print(f"  {d.name:55s}  NO SUMMARY")
        continue
    r = json.loads(summary.read_text())
    rows.append((d.name, r))
    print(f"  {d.name:55s}  geo={r['geo']:.4f}  cum_rf={r['cum_rf']:.4f}  LS1={r['LS1']:.4f}  LS2={r['LS2']:.4f}")

print("\n=== Reference single-seed numbers (Tables I and III) ===")
print("  Single peak s59 wu20  (CLM-0131)            geo=0.4301  cum_rf=-0.087")
print("  Canonical   s54 wu5   (CLM-0123)            geo=0.3908")
print("  R57-alpha   s51 wu5   (CLM-0104 pre-drift)  geo=0.5260 (6-axis)")
print("  R66 era     s51 wu5   (CLM-0104 same code)  geo=0.4259 (6-axis)")


def stats(label, recs):
    if not recs:
        return
    g = [r["geo"] for r in recs]
    line = f"  {label}: n={len(g)}  mean={statistics.mean(g):.4f}  min={min(g):.4f}  max={max(g):.4f}"
    if len(g) > 1:
        line += f"  SD={statistics.stdev(g):.4f}"
    print(line)


e2 = [r for name, r in rows if name.startswith("e2_")]
e4 = [r for name, r in rows if name.startswith("e4_")]
e1 = [r for name, r in rows if name.startswith("e1_")]
e3 = [r for name, r in rows if name.startswith("e3_bisect_")]

print("\n=== Aggregates ===")
stats("E2 within-config variance (target ~0.43)", e2)
stats("E4 dead-seed full-RNG re-roll", e4)
stats("E1 500-ep convergence", e1)
stats("E3 code-drift bisection (per commit)", e3)
