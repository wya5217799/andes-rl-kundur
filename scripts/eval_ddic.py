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

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.sac import SACAgent  # noqa: E402
from andes_rl_kundur.agents.td3 import TD3Agent  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
    zero_action_fn,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

EVAL_SEED = 42
STEPS = 150  # 30s @ DT=0.6 (V4 ANDES)


def _detect_algo(ckpt_path: Path) -> str:
    """Inspect the ckpt's self-described algo field. Default to 'sac' for
    pre-2026-05-17 ckpts that don't carry it."""
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    return ckpt.get("algo", "sac")


def load_actors(ckpt_dir: Path, suffix: str = "best") -> list:
    """Load 4 actors. Detects SAC vs TD3 from the ckpt's algo field."""
    from andes_rl_kundur.config import HIDDEN_SIZES
    obs_dim = AndesMultiVSGEnvV4.OBS_DIM
    action_dim = 2
    agents: list = []
    for i in range(AndesMultiVSGEnvV4.N_AGENTS):
        ckpt_path = ckpt_dir / f"agent_{i}_{suffix}.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(f"No ckpt: {ckpt_path}")
        algo = _detect_algo(ckpt_path)
        if algo == "td3":
            a = TD3Agent(obs_dim=obs_dim, action_dim=action_dim,
                         hidden_sizes=HIDDEN_SIZES, device="cpu")
        else:
            a = SACAgent(obs_dim=obs_dim, action_dim=action_dim,
                         hidden_sizes=HIDDEN_SIZES, device="cpu")
        a.load(str(ckpt_path))
        agents.append(a)
    return agents


def eval_scenario(scen_name: str, delta_u: dict,
                   agents: list | None, label: str,
                   seed: int = EVAL_SEED) -> dict:
    """Back-compat thin wrapper around run_scenario.

    Kept so that scripts/eval_all_seeds.py and any external callers that
    still ``from eval_ddic import eval_scenario`` continue to work.
    """
    action_fn = (
        zero_action_fn if agents is None
        else deterministic_actor_action_fn(agents)
    )
    return run_scenario(
        scen_name, delta_u,
        action_fn=action_fn,
        label=label,
        seed=seed,
        steps=STEPS,
    )


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
    agents = load_actors(ckpt_dir, suffix=args.suffix)
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
