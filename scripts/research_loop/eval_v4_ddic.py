"""V4 DDIC eval — load trained V4 SAC ckpts, run LS1+LS2, generate trace JSON.

Mirrors `eval_v4_no_control.py` format so paper_grade_axes.py + Fig.7/9 plot
can read same dir. Loads 4 SAC actors from --ckpt-dir (agent_{0..3}_<suffix>.pt).

Usage:
    /home/wya/andes_venv/bin/python scripts/research_loop/eval_v4_ddic.py \
        --ckpt-dir results/v4_paper_s42 --suffix best \
        --label ddic_v4_s42 --out-dir results/research_loop/eval_v4_baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.sac import SACAgent  # noqa: E402
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402

SCENARIOS = {
    "load_step_1": {"PQ_Bus14": -2.48},
    "load_step_2": {"PQ_Bus15": 1.88},
}

EVAL_SEED = 42
STEPS = 150  # 30s @ DT=0.6 (V4 ANDES)


def load_actors(ckpt_dir: Path, suffix: str = "best") -> list[SACAgent]:
    from config import HIDDEN_SIZES
    obs_dim = AndesMultiVSGEnvV4.OBS_DIM
    action_dim = 2
    agents = []
    for i in range(AndesMultiVSGEnvV4.N_AGENTS):
        a = SACAgent(obs_dim=obs_dim, action_dim=action_dim,
                     hidden_sizes=HIDDEN_SIZES, device="cpu")
        ckpt_path = ckpt_dir / f"agent_{i}_{suffix}.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(f"No ckpt: {ckpt_path}")
        a.load(str(ckpt_path))
        agents.append(a)
    return agents


def eval_scenario(scen_name: str, delta_u: dict,
                   agents: list | None, label: str,
                   seed: int = EVAL_SEED) -> dict:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(seed)
    env.STEPS_PER_EPISODE = STEPS
    obs = env.reset(delta_u=delta_u)

    N = env.N_AGENTS
    F_NOM = env.FN
    traces: list[dict] = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0

    for step in range(STEPS):
        if agents is not None:
            actions = {i: agents[i].select_action(obs[i], deterministic=True)
                       for i in range(N)}
        else:
            actions = {i: np.zeros(2, dtype=np.float32) for i in range(N)}

        obs, rewards, done, info = env.step(actions)
        if info.get("tds_failed"):
            break

        freq_hz = info["freq_hz"].astype(float).tolist()
        delta_f = [(f - F_NOM) for f in freq_hz]
        f_bar = float(np.mean(freq_hz))
        step_rf = float(np.mean([(d - (f_bar - F_NOM)) ** 2 for d in delta_f]))
        cum_rf -= step_rf
        max_df = max(max_df, float(np.max(np.abs(delta_f))))
        osc_accum += float(np.std(delta_f))

        traces.append({
            "step":       step,
            "t":          float(info["time"]),
            "freq_hz":    freq_hz,
            "f_bar":      f_bar,
            "step_rf":    step_rf,
            "delta_P_es": info["P_es"].astype(float).tolist(),
            "delta_f_es": delta_f,
            "M_es":       info["M_es"].astype(float).tolist(),
            "D_es":       info["D_es"].astype(float).tolist(),
            "delta_M":    info["delta_M"].astype(float).tolist(),
            "delta_D":    info["delta_D"].astype(float).tolist(),
        })
        if done:
            break

    env.close()
    return {
        "controller":   label,
        "scenario":     scen_name,
        "env_version":  "v4",
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "osc":          osc_accum,
        "n_steps":      len(traces),
        "traces":       traces,
    }


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

    for scen, du in SCENARIOS.items():
        print(f"[V4 ddic eval] {args.label} on {scen}...")
        rep = eval_scenario(scen, du, agents, args.label, seed=args.seed)
        out_path = out / f"{args.label}_{scen}.json"
        out_path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(f"  saved {out_path} (max_df={rep['max_df']:.3f}, n_steps={rep['n_steps']})")
    print(f"\n[V4 ddic eval] done. Files in {out}")


if __name__ == "__main__":
    main()
