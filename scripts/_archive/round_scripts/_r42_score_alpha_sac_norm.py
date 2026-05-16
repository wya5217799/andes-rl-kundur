"""R42 part α — score SAC normalized-mode sweep.

Mirrors `_r41_score_B_normalized.py` but for SAC + --normalize-actions.
Tests whether the right reward shape (normalized action penalty) is
sufficient on its own, or whether algorithm choice (SAC vs TD3) still
matters after the reward asymmetry is fixed.

Predictions (from handoff):
  - If SAC norm >= 0.20: reward shape alone explains everything.
  - If SAC norm ~ 0.13 (at attractor): H3 confirmed — SAC entropy
    variance hurts even at correct reward shape.
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
SEEDS = (49, 50, 51)
SCEN = ("load_step_1", "load_step_2")
PY = "/home/wya/andes_venv/bin/python"


def run_eval(ckpt, label):
    subprocess.run([PY, str(ROOT / "scripts" / "eval_ddic.py"),
                    "--ckpt-dir", str(ckpt), "--suffix", "best",
                    "--label", label, "--out-dir", str(EVAL_OUT)],
                   check=True)


def score(label):
    per_scen, util = {}, {"dH": [], "dD": []}
    for scen in SCEN:
        ts = evaluate_trace(EVAL_OUT/f"{label}_{scen}.json", PAPER[scen],
                            is_ddic=True, label=label)
        per_scen[scen] = ts.overall
        for ax in ts.axes:
            if ax.name == "dH_utilization":
                util["dH"].append(ax.score)
            elif ax.name == "dD_utilization":
                util["dD"].append(ax.score)
    combined = math.exp(sum(math.log(max(x, 0.01)) for x in per_scen.values())/len(per_scen))
    return {"per_scenario": per_scen, "combined_6axis": combined,
            "dH_util_mean": sum(util["dH"])/len(util["dH"]),
            "dD_util_mean": sum(util["dD"])/len(util["dD"])}


rows = []
for seed in SEEDS:
    ckpt = ROOT/"results"/f"sac_norm_s{seed}"
    if not ckpt.exists():
        continue
    label = f"sac_norm_s{seed}"
    run_eval(ckpt, label)
    s = score(label)
    s["seed"] = seed
    rows.append(s)
    print(f"  seed={seed}  LS1={s['per_scenario']['load_step_1']:.4f}  "
          f"LS2={s['per_scenario']['load_step_2']:.4f}  "
          f"combined={s['combined_6axis']:.4f}  "
          f"dH_util={s['dH_util_mean']:.4f}  dD_util={s['dD_util_mean']:.4f}")

if rows:
    sc = [r["combined_6axis"] for r in rows]
    print(f"\n=== R42-α SAC normalized mode 75ep sweep ===")
    print(f"  6-axis: mean={sum(sc)/len(sc):.4f}  range=[{min(sc):.4f}, {max(sc):.4f}]")
    print("  vs:")
    print("    R41-B TD3 norm 75ep:     0.275  (production setting)")
    print("    R41-A SAC phi=0 75ep:    0.117  (algorithm not enough)")
    print("    SAC multi-seed attractor: 0.137  (R23-R27 mean)")
    print("    no_control:               0.104")

out = ROOT/"results"/"research_loop"/"r42_alpha_sac_norm_sweep.json"
out.write_text(json.dumps({"r42_alpha": rows}, indent=2), encoding="utf-8")
print(f"\n-> {out}")
