"""R41 part A — score SAC phi=0 sweep, compare against R40 TD3 phi=0."""
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
SEEDS = (49, 50, 51)
SCEN = ("load_step_1", "load_step_2")
PY = "/home/wya/andes_venv/bin/python"


def run_eval_ddic(ckpt_dir: Path, label: str) -> None:
    cmd = [PY, str(ROOT / "scripts" / "eval_ddic.py"),
           "--ckpt-dir", str(ckpt_dir), "--suffix", "best",
           "--label", label, "--out-dir", str(EVAL_OUT)]
    print(f"[eval_ddic] {label} ← {ckpt_dir}")
    subprocess.run(cmd, check=True)


def score_label(label: str) -> dict:
    per_scen = {}
    util = {"dH": [], "dD": []}
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
    label = f"sac_noactioncost_s{seed}"
    ckpt_dir = ROOT / "results" / f"sac_noactioncost_s{seed}"
    if not ckpt_dir.exists():
        print(f"[skip] {ckpt_dir}"); continue
    run_eval_ddic(ckpt_dir, label)
    score = score_label(label)
    score["seed"] = seed
    rows.append(score)
    print(f"  seed={seed}  LS1={score['per_scenario']['load_step_1']:.4f}  "
          f"LS2={score['per_scenario']['load_step_2']:.4f}  "
          f"combined={score['combined_6axis']:.4f}  "
          f"dH_util={score['dH_util_mean']:.4f}  "
          f"dD_util={score['dD_util_mean']:.4f}")

print("\n=== R41-A SAC phi=0 sweep ===")
if rows:
    scores = [r["combined_6axis"] for r in rows]
    print(f"  SAC phi=0  6-axis: mean={sum(scores)/len(scores):.4f}  range=[{min(scores):.4f}, {max(scores):.4f}]")
print("  vs reference:")
print("    TD3 phi=0  (R40):  0.2590 mean (range 0.253-0.266)")
print("    TD3 phi=paper (R38): 0.0841 mean")
print("    SAC attractor:       0.137")
print("    no_control:          0.104")

out_path = ROOT / "results" / "research_loop" / "r41A_sac_phi0_sweep.json"
out_path.write_text(json.dumps({"r41A_sac_phi0_sweep": rows}, indent=2), encoding="utf-8")
print(f"\n-> {out_path}")
