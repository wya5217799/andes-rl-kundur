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

# E3 cliff detection — sort by TOPOLOGICAL commit order (not round#).
# `git log --topo-order e8427df..43d203b` confirms: R59 (43d203b) was
# committed AFTER R65 (4c5327a), so the bisect.sh ordering by round#
# is NOT the commit history order. Adjacent-pair deltas must use:
TOPO_ORDER = [
    ("R58", "e8427df"),
    ("R60", "2752a8f"),
    ("R61", "1a3a4ad"),
    ("R62", "48c466c"),
    ("R63", "6671e8d"),
    ("R64", "6c27ae1"),
    ("R65", "4c5327a"),
    ("R59", "43d203b"),
]

print("\n=== E3 cliff scan (TOPOLOGICAL order, adjacent-pair deltas) ===")
topo_rows = []
for r_label, sha in TOPO_ORDER:
    match = next((r for name, r in rows if sha in name), None)
    if match is None:
        topo_rows.append((r_label, sha, None))
        print(f"  {r_label} {sha}  (no data yet)")
        continue
    topo_rows.append((r_label, sha, match))
    print(f"  {r_label} {sha}  geo={match['geo']:.4f}  cum_rf={match['cum_rf']:.4f}")

print("\n  --- adjacent-pair deltas (later - earlier) ---")
biggest = (0.0, None, None)
for (la, sa, ra), (lb, sb, rb) in zip(topo_rows, topo_rows[1:]):
    if ra is None or rb is None:
        print(f"  {la}->{lb}  (incomplete)")
        continue
    d_geo = rb["geo"] - ra["geo"]
    d_rf = rb["cum_rf"] - ra["cum_rf"]
    flag = "  <-- CLIFF" if abs(d_geo) > 0.05 else ""
    print(f"  {la} -> {lb}   d_geo={d_geo:+.4f}   d_cum_rf={d_rf:+.4f}{flag}")
    if abs(d_geo) > abs(biggest[0]):
        biggest = (d_geo, la, lb)
if biggest[1] is not None:
    print(f"\n  -> Biggest |d_geo|: {biggest[1]} -> {biggest[2]} ({biggest[0]:+.4f})")
