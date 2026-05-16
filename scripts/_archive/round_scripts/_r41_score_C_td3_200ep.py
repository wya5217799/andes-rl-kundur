"""R41 part C — score TD3 phi=0 200ep sweep (seeds 49/50/51 + 52/53).

If 6-axis stays ~0.26 (R40 75ep result), the ceiling is at ~0.26
regardless of training length. If 6-axis pushes >0.30, longer
training helps. R21 lucky basin was 0.444 — anything closer is
publishable.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.paper_grade_axes import (  # noqa: E402
    PAPER, evaluate_trace,
)

EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
SEEDS = (49, 50, 51, 52, 53)
SCEN = ("load_step_1", "load_step_2")
PY = "/home/wya/andes_venv/bin/python"


def run_eval_ddic(ckpt_dir: Path, label: str) -> None:
    cmd = [PY, str(ROOT / "scripts" / "eval_ddic.py"),
           "--ckpt-dir", str(ckpt_dir), "--suffix", "best",
           "--label", label, "--out-dir", str(EVAL_OUT)]
    subprocess.run(cmd, check=True)


def score_label(label: str) -> dict:
    per_scen, util = {}, {"dH": [], "dD": []}
    for scen in SCEN:
        path = EVAL_OUT / f"{label}_{scen}.json"
        ts = evaluate_trace(path, PAPER[scen], is_ddic=True, label=label)
        per_scen[scen] = ts.overall
        for ax in ts.axes:
            if ax.name == "dH_utilization":
                util["dH"].append(ax.score)
            elif ax.name == "dD_utilization":
                util["dD"].append(ax.score)
    combined = math.exp(sum(math.log(max(x, 0.01)) for x in per_scen.values()) / len(per_scen))
    return {"per_scenario": per_scen, "combined_6axis": combined,
            "dH_util_mean": sum(util["dH"])/len(util["dH"]),
            "dD_util_mean": sum(util["dD"])/len(util["dD"])}


rows = []
for seed in SEEDS:
    ckpt = ROOT / "results" / f"td3_phi0_200ep_s{seed}"
    if not ckpt.exists():
        print(f"[skip] {ckpt}"); continue
    label = f"td3_phi0_200ep_s{seed}"
    run_eval_ddic(ckpt, label)
    s = score_label(label)
    s["seed"] = seed
    rows.append(s)
    print(f"  seed={seed}  LS1={s['per_scenario']['load_step_1']:.4f}  "
          f"LS2={s['per_scenario']['load_step_2']:.4f}  "
          f"combined={s['combined_6axis']:.4f}  "
          f"dH_util={s['dH_util_mean']:.4f}  dD_util={s['dD_util_mean']:.4f}")

if rows:
    scores = [r["combined_6axis"] for r in rows]
    print(f"\n=== R41-C TD3 phi=0 200ep sweep ({len(rows)} seeds) ===")
    print(f"  6-axis: mean={sum(scores)/len(scores):.4f}  range=[{min(scores):.4f}, {max(scores):.4f}]")
    print("  vs:")
    print("    R40 TD3 phi=0 75ep: 0.2590")
    print("    R21 lucky basin:    0.4440")
    print("    HAWE w9802:         0.4390")

out = ROOT / "results" / "research_loop" / "r41C_td3_200ep_sweep.json"
out.write_text(json.dumps({"r41C": rows}, indent=2), encoding="utf-8")
print(f"\n-> {out}")
