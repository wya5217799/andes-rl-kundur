"""R38 — score the TD3 multi-seed sweep against the SAC smoke + R23-R27
reference attractor.

Loads each results/td3_s{49,50,51}/agent_*_best.pt via eval_ddic + writes
results/research_loop/eval_v4_baseline/ddic_td3_s{seed}_load_step_{1,2}.json
files, then computes the paper_grade_axes 6-axis geometric mean per
seed. Prints a comparison table against:

- no_control (0.104)               — paper Fig 6/8 baseline
- multi-seed SAC attractor (~0.137) — R23-R27 22-ckpt sweep
- R21 lucky basin (0.444)          — single-seed SAC outlier
- HAWE w9802 (0.439)               — Asset 5 inference-time ensemble
- post-refactor SAC smoke (0.0454) — single-seed sanity from earlier today

Writes results/research_loop/r38_td3_sweep.json with the full per-seed
breakdown for archival.

Run after all three td3_s{49,50,51}/ ckpt dirs are populated.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.paper_grade_axes import (  # noqa: E402
    PAPER, evaluate_trace,
)

EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
SEEDS = (49, 50, 51)
SCEN = ("load_step_1", "load_step_2")
PY = "/home/wya/andes_venv/bin/python"


def run_eval_ddic(ckpt_dir: Path, label: str) -> None:
    """Invoke scripts/eval_ddic.py to produce the trace JSONs."""
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
    """Run paper_grade_axes on the two scenarios for one label."""
    per_scen = {}
    for scen in SCEN:
        path = EVAL_OUT / f"{label}_{scen}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        ts = evaluate_trace(path, PAPER[scen], is_ddic=True, label=label)
        per_scen[scen] = ts.overall
    combined = math.exp(
        sum(math.log(max(x, 0.01)) for x in per_scen.values()) / len(per_scen)
    )
    return {"per_scenario": per_scen, "combined_6axis": combined}


def main() -> None:
    rows = []
    for seed in SEEDS:
        ckpt_dir = ROOT / "results" / f"td3_s{seed}"
        if not ckpt_dir.exists():
            print(f"[skip] {ckpt_dir} not present")
            continue
        label = f"td3_s{seed}"
        run_eval_ddic(ckpt_dir, label)
        score = score_label(label)
        score["seed"] = seed
        rows.append(score)
        print(
            f"  seed={seed}  LS1={score['per_scenario']['load_step_1']:.4f}  "
            f"LS2={score['per_scenario']['load_step_2']:.4f}  "
            f"combined={score['combined_6axis']:.4f}"
        )

    # Comparison table
    ref = {
        "no_control":              0.104,
        "multi_seed_sac_attractor": 0.137,
        "post_refactor_sac_smoke": 0.0454,
        "r21_lucky":               0.444,
        "hawe_w9802":              0.439,
    }
    print("\n=== TD3 sweep summary ===")
    if rows:
        scores = [r["combined_6axis"] for r in rows]
        print(f"  TD3 seeds {SEEDS}:  6-axis = {scores}")
        print(f"  mean = {sum(scores)/len(scores):.4f}")
        print(f"  max  = {max(scores):.4f}")
        print(f"  min  = {min(scores):.4f}")
    print("\n  Reference points:")
    for k, v in ref.items():
        print(f"    {k:<28s} {v:.4f}")

    out = {
        "td3_sweep": rows,
        "reference": ref,
        "command": "scripts/train.py --algo td3 --episodes 75 --seed {49,50,51}",
    }
    out_path = ROOT / "results" / "research_loop" / "r38_td3_sweep.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nFull breakdown -> {out_path}")


if __name__ == "__main__":
    main()
