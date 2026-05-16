"""V4 paper-faithful no-control eval — generate Fig.6/8 baseline trace JSON.

Mirrors eval_paper_spec_v2.py format so paper_grade_axes.py + figs6_9_ls_traces.py
can read directly. No DDIC ckpt needed (zero-action baseline = paper Fig.6/8).

Output: results/research_loop/eval_v4_baseline/no_control_load_step_{1,2}.json

Run: /home/wya/andes_venv/bin/python scripts/eval_no_control.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.paper_path import run_scenario, zero_action_fn  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

OUT_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STEPS = 150  # 30s @ DT=0.2 (settling axis needs ≥10s, 30s safe)
SEED = 42


def main():
    print(f"[V4 eval] no-control baseline → {OUT_DIR}")
    for scen, du in SCENARIOS.items():
        print(f"  running {scen} (delta_u={du})...")
        rep = run_scenario(
            scen, du,
            action_fn=zero_action_fn,
            label="no_control",
            seed=SEED,
            steps=STEPS,
        )
        out_path = OUT_DIR / f"no_control_{scen}.json"
        out_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(f"  saved {out_path} (max_df={rep['max_df']:.3f}, n_steps={rep['n_steps']})")
    print("\n[V4 eval] all done.")


if __name__ == "__main__":
    main()
