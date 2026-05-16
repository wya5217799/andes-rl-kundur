"""R40 — score the TD3 phi-zero (action-cost = 0) multi-seed sweep
against the R38 paper-phi TD3 baseline.

Tests CLM-0043's hypothesis: if the action-vs-frequency reward
asymmetry causes the 0.137 attractor, then PHI_H=PHI_D=0 should let
the actor use a meaningful action range and improve the
dH/dD_utilization axes — and therefore lift the 6-axis geo-mean.
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


def run_eval_ddic(ckpt_dir: Path, label: str) -> None:
    cmd = [
        PY, str(ROOT / "scripts" / "eval_ddic.py"),
        "--ckpt-dir", str(ckpt_dir),
        "--suffix", "best",
        "--label", label,
        "--out-dir", str(EVAL_OUT),
    ]
    print(f"[eval_ddic] {label} ← {ckpt_dir}")
    subprocess.run(cmd, check=True)


def score_label(label: str) -> dict:
    """Per-scenario + combined + utilization (the diagnostic axis)."""
    per_scen = {}
    util = {"dH": [], "dD": []}
    for scen in SCEN:
        path = EVAL_OUT / f"{label}_{scen}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        ts = evaluate_trace(path, PAPER[scen], is_ddic=True, label=label)
        per_scen[scen] = ts.overall
        for ax in ts.axes:
            if ax.name == "dH_utilization":
                util["dH"].append(ax.score)
            elif ax.name == "dD_utilization":
                util["dD"].append(ax.score)
    combined = math.exp(
        sum(math.log(max(x, 0.01)) for x in per_scen.values()) / len(per_scen)
    )
    return {
        "per_scenario": per_scen,
        "combined_6axis": combined,
        "dH_util_mean": sum(util["dH"]) / len(util["dH"]),
        "dD_util_mean": sum(util["dD"]) / len(util["dD"]),
    }


def main() -> None:
    rows = []
    for seed in SEEDS:
        ckpt_dir = ROOT / "results" / f"td3_noactioncost_s{seed}"
        if not ckpt_dir.exists():
            print(f"[skip] {ckpt_dir} not present")
            continue
        label = f"td3_noactioncost_s{seed}"
        run_eval_ddic(ckpt_dir, label)
        score = score_label(label)
        score["seed"] = seed
        rows.append(score)
        print(
            f"  seed={seed}  LS1={score['per_scenario']['load_step_1']:.4f}  "
            f"LS2={score['per_scenario']['load_step_2']:.4f}  "
            f"combined={score['combined_6axis']:.4f}  "
            f"dH_util={score['dH_util_mean']:.4f}  "
            f"dD_util={score['dD_util_mean']:.4f}"
        )

    print("\n=== R40 phi=0 TD3 sweep ===")
    if rows:
        scores = [r["combined_6axis"] for r in rows]
        h_util = [r["dH_util_mean"] for r in rows]
        d_util = [r["dD_util_mean"] for r in rows]
        print(f"  6-axis  mean={sum(scores)/len(scores):.4f}  "
              f"range=[{min(scores):.4f}, {max(scores):.4f}]")
        print(f"  dH_util mean={sum(h_util)/len(h_util):.4f}  "
              f"range=[{min(h_util):.4f}, {max(h_util):.4f}]")
        print(f"  dD_util mean={sum(d_util)/len(d_util):.4f}  "
              f"range=[{min(d_util):.4f}, {max(d_util):.4f}]")
    print("\n  vs R38 baseline (TD3 phi_paper):")
    print(f"    6-axis  = 0.0841 (R38)")
    print(f"    dH_util ≈ 0.005 (R38)")
    print(f"    dD_util ≈ 0.005 (R38)")
    print("\n  Decision rule (R40/plan.md):")
    print("    6-axis > 0.20 AND util > 0.20  → strongly confirm CLM-0043, build R41")
    print("    6-axis ∈ [0.11, 0.20]          → weakly confirm, proceed to R41")
    print("    6-axis < 0.11 AND util < 0.05  → falsify, search elsewhere")

    out = {"r40_phi_zero_sweep": rows}
    out_path = ROOT / "results" / "research_loop" / "r40_phi_zero_sweep.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nFull breakdown -> {out_path}")


if __name__ == "__main__":
    main()
