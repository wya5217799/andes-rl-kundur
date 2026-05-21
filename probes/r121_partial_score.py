"""Score R121 partial alpha-sweep traces while round still running."""
import sys
import json
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.evaluation.summary import score_trace_files  # noqa: E402

TRACE = ROOT / "results" / "r121_constrained_warm_h0" / "traces"

def find_done_alphas():
    seen = {}
    for p in TRACE.glob("alpha_*_load_step_1.json"):
        a = p.stem.split("_")[1]
        if (TRACE / f"alpha_{a}_load_step_2.json").exists():
            seen[a] = (p, TRACE / f"alpha_{a}_load_step_2.json")
    return seen

def main():
    done = find_done_alphas()
    if not done:
        print("No completed alphas yet")
        return
    print(f"{'alpha':<8}{'LS1':<10}{'LS2':<10}{'geo':<10}{'cum_rf':<10}")
    for a in sorted(done):
        scen_paths = {"load_step_1": done[a][0], "load_step_2": done[a][1]}
        s = score_trace_files(scen_paths, label=f"r121_a{a}", is_ddic=True)
        alpha_real = int(a) / 100.0
        print(f"{alpha_real:<8.2f}{s['LS1']:<10.4f}{s['LS2']:<10.4f}{s['geo']:<10.4f}{s['cum_rf']:<+10.4f}")

if __name__ == "__main__":
    main()
