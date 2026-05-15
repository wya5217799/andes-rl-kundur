"""V4 Stochastic Ensemble — sample SAC actor N times per step + average.

Tests whether ensemble effect comes from actor DIVERSITY (different ckpts) or
just from action VARIANCE (stochastic sampling). If stochastic ensemble alone
matches R30 multi-actor ensemble, then variance averaging is the win mechanism.

Usage:
    PY=/home/wya/andes_venv/bin/python
    $PY scripts/research_loop/eval_v4_ensemble_stoch.py \
        --ckpt-dir results/v4_h50_s49 --suffix best \
        --n-samples 10 --label ddic_v4_R21_stoch10 \
        --out-dir results/research_loop/eval_v4_baseline
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
STEPS = 150


def load_actors(ckpt_dir: Path, suffix: str) -> list[SACAgent]:
    from config import HIDDEN_SIZES
    obs_dim = AndesMultiVSGEnvV4.OBS_DIM
    actors = []
    for i in range(AndesMultiVSGEnvV4.N_AGENTS):
        a = SACAgent(obs_dim=obs_dim, action_dim=2,
                     hidden_sizes=HIDDEN_SIZES, device="cpu")
        ckpt_path = ckpt_dir / f"agent_{i}_{suffix}.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(ckpt_path)
        a.load(str(ckpt_path))
        actors.append(a)
    return actors


def stoch_action(actor: SACAgent, obs_i: np.ndarray, n_samples: int) -> np.ndarray:
    """Sample N stochastic actions, return mean."""
    acts = np.array([
        actor.select_action(obs_i, deterministic=False)
        for _ in range(n_samples)
    ])
    return acts.mean(axis=0)


def eval_scenario(scen_name: str, delta_u: dict, actors: list[SACAgent],
                  n_samples: int, label: str, seed: int = EVAL_SEED) -> dict:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(seed)
    env.STEPS_PER_EPISODE = STEPS
    obs = env.reset(delta_u=delta_u)

    N = env.N_AGENTS
    F_NOM = env.FN
    traces: list[dict] = []
    cum_rf = 0.0
    max_df = 0.0

    for step in range(STEPS):
        actions = {i: stoch_action(actors[i], obs[i], n_samples) for i in range(N)}
        obs, rewards, done, info = env.step(actions)
        if info.get("tds_failed"):
            break
        freq_hz = info["freq_hz"].astype(float).tolist()
        delta_f = [(f - F_NOM) for f in freq_hz]
        f_bar = float(np.mean(freq_hz))
        step_rf = float(np.mean([(d - (f_bar - F_NOM)) ** 2 for d in delta_f]))
        cum_rf -= step_rf
        max_df = max(max_df, float(np.max(np.abs(delta_f))))

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
        "ensemble_agg": "stochastic",
        "n_samples":    n_samples,
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "n_steps":      len(traces),
        "traces":       traces,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt-dir", required=True)
    p.add_argument("--suffix",   default="best")
    p.add_argument("--n-samples", type=int, default=10)
    p.add_argument("--label",    required=True)
    p.add_argument("--out-dir",  required=True)
    p.add_argument("--seed",     type=int, default=EVAL_SEED)
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[V4 stoch ensemble] {args.ckpt_dir} (suffix={args.suffix}), N={args.n_samples}")
    actors = load_actors(Path(args.ckpt_dir), args.suffix)

    for scen, delta_u in SCENARIOS.items():
        print(f"  {args.label} on {scen}...")
        res = eval_scenario(scen, delta_u, actors, args.n_samples, args.label, args.seed)
        out_p = out / f"{args.label}_{scen}.json"
        with open(out_p, "w") as f:
            json.dump(res, f)
        print(f"    saved {out_p} (max_df={res['max_df']:.3f})")


if __name__ == "__main__":
    main()
