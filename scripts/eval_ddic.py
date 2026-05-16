"""V4 DDIC eval — load trained V4 SAC ckpts, run LS1+LS2, generate trace JSON.

Mirrors `eval_no_control.py` format so paper_grade_axes.py + Fig.7/9 plot
can read same dir. Loads 4 SAC actors from --ckpt-dir (agent_{0..3}_<suffix>.pt).

Usage:
    /home/wya/andes_venv/bin/python scripts/eval_ddic.py \
        --ckpt-dir results/v4_paper_s42 --suffix best \
        --label ddic_v4_s42 --out-dir results/research_loop/eval_v4_baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

EVAL_SEED = 42
STEPS = 150  # 30s @ DT=0.6 (V4 ANDES)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt-dir", required=True)
    p.add_argument("--suffix",   default="best",
                   help="ckpt suffix; checks <ckpt-dir>/agent_<i>_<suffix>.pt at runtime")
    p.add_argument("--label",    required=True, help="DDIC label, e.g. ddic_v4_s42")
    p.add_argument("--out-dir",  required=True)
    p.add_argument("--seed",     type=int, default=EVAL_SEED)
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ckpt_dir = Path(args.ckpt_dir)
    print(f"[V4 ddic eval] loading 4 actors from {ckpt_dir} (suffix={args.suffix})")
    agents = load_agents(ckpt_dir, suffix=args.suffix)
    action_fn = deterministic_actor_action_fn(agents)

    for scen, du in SCENARIOS.items():
        print(f"[V4 ddic eval] {args.label} on {scen}...")
        rep = run_scenario(
            scen, du,
            action_fn=action_fn,
            label=args.label,
            seed=args.seed,
            steps=STEPS,
        )
        out_path = out / f"{args.label}_{scen}.json"
        out_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(f"  saved {out_path} (max_df={rep['max_df']:.3f}, n_steps={rep['n_steps']})")
    print(f"\n[V4 ddic eval] done. Files in {out}")


if __name__ == "__main__":
    main()
