"""Decompose R112 baseline vs warm_h0 trace into 11-axis components.

CLM-0204 reports geo crash -95.8% but per-step ||a|| / smoothness /
max |Δf| analyses (probes/r112_action_profile_analysis.py) all show
warm-h_0 is comparable or BETTER on smoothness and frequency suppression.
So which paper_grade_axes axis is at floor for warm-h_0?
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# ANDES stub since we only use paper_grade_axes
import types
if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.evaluation.paper_grade_axes import evaluate_trace, PAPER  # noqa: E402

TRACE_DIR = ROOT / "results" / "r112_warmh0_env_eval" / "traces"


def main():
    for scen in ["load_step_1", "load_step_2"]:
        print(f"\n=== {scen} ===")
        paper_bench = PAPER[scen]
        for label in ["baseline", "warmh0"]:
            p = TRACE_DIR / f"{label}_{scen}.json"
            result = evaluate_trace(p, paper_bench, is_ddic=True, label=label)
            print(f"\n  {label}:  overall={result.overall:.4f}")
            for a in result.axes:
                print(f"    {a.name:<28s} proj={a.project_value:+9.4f}  paper={a.paper_value:+9.4f}  score={a.score:.4f}")


if __name__ == "__main__":
    main()
