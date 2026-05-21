"""Compute median R-squared from R101 multi-seed MLP results."""
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "results" / "r101_d3_multiseed_mlp" / "summary.json").open() as f:
    d = json.load(f)

print("Per-gamma R2 distribution (40 fits each):")
print(f"  {'gamma':<8}{'mean':>10}{'median':>10}{'p25':>10}{'p75':>10}{'min':>10}{'max':>10}{'fneg':>8}{'f<-1':>8}")
for gk, s in d["per_gamma"].items():
    all_r2 = []
    for ai, vs in s["per_agent_r2_lists"].items():
        all_r2.extend(vs)
    arr = np.array(all_r2)
    print(f"  {gk[1:]:<8}{s['mean']:>+10.3f}{float(np.median(arr)):>+10.3f}{float(np.percentile(arr,25)):>+10.3f}{float(np.percentile(arr,75)):>+10.3f}{float(arr.min()):>+10.3f}{float(arr.max()):>+10.3f}{(arr<0).mean():>8.2f}{(arr<-1).mean():>8.2f}")

print()
print("R2 obs->action (40 fits):")
all_act = []
for ai, vs in d["obs2action"]["per_agent_r2_lists"].items():
    all_act.extend(vs)
arr_act = np.array(all_act)
print(f"  mean={d['obs2action']['mean']:+.3f}  median={float(np.median(arr_act)):+.3f}  p25={float(np.percentile(arr_act,25)):+.3f}  p75={float(np.percentile(arr_act,75)):+.3f}  min={float(arr_act.min()):+.3f}  max={float(arr_act.max()):+.3f}")
