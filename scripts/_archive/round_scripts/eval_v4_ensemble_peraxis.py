"""V4 Per-Axis Ensemble — pick action dim from different actors.

Each agent's action is 2D: (ΔH, ΔD). Per-axis ensemble assembles each dim from
different actors, e.g. ΔH from R21 (conservative inertia) + ΔD from ws8 (responsive damping).

Usage:
    PY=/home/wya/andes_venv/bin/python
    $PY scripts/research_loop/eval_v4_ensemble_peraxis.py \
        --ckpt-dir-h results/v4_h50_s49 --suffix-h best \
        --ckpt-dir-d results/v4_8_warmstart_R21_s49 --suffix-d best \
        --label ddic_v4_peraxis_R21h_ws8d --out-dir results/research_loop/eval_v4_baseline
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.sac import SACAgent  # noqa: E402
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from probes.andes_common.paper_constants import SCENARIOS  # noqa: E402
EVAL_SEED = 42
STEPS = 150


def load_actors(ckpt_dir: Path, suffix: str) -> list[SACAgent]:
    from config import HIDDEN_SIZES
    obs_dim = AndesMultiVSGEnvV4.OBS_DIM
    actors = []
    for i in range(AndesMultiVSGEnvV4.N_AGENTS):
        a = SACAgent(obs_dim=obs_dim, action_dim=2,
                     hidden_sizes=HIDDEN_SIZES, device="cpu")
        a.load(str(ckpt_dir / f"agent_{i}_{suffix}.pt"))
        actors.append(a)
    return actors


def peraxis_action(actor_h: SACAgent, actor_d: SACAgent, obs_i: np.ndarray) -> np.ndarray:
    """ΔH (action[0]) from actor_h, ΔD (action[1]) from actor_d."""
    a_h = actor_h.select_action(obs_i, deterministic=True)
    a_d = actor_d.select_action(obs_i, deterministic=True)
    return np.array([a_h[0], a_d[1]])


def eval_scenario(scen_name: str, delta_u: dict,
                  actors_h: list[SACAgent], actors_d: list[SACAgent],
                  label: str, seed: int = EVAL_SEED) -> dict:
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
        actions = {i: peraxis_action(actors_h[i], actors_d[i], obs[i]) for i in range(N)}
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
        "ensemble_agg": "per-axis",
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "n_steps":      len(traces),
        "traces":       traces,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt-dir-h", required=True, help="ckpt dir for ΔH (action[0])")
    p.add_argument("--suffix-h",   default="best")
    p.add_argument("--ckpt-dir-d", required=True, help="ckpt dir for ΔD (action[1])")
    p.add_argument("--suffix-d",   default="best")
    p.add_argument("--label",      required=True)
    p.add_argument("--out-dir",    required=True)
    p.add_argument("--seed",       type=int, default=EVAL_SEED)
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[V4 per-axis] ΔH from {args.ckpt_dir_h}, ΔD from {args.ckpt_dir_d}")
    actors_h = load_actors(Path(args.ckpt_dir_h), args.suffix_h)
    actors_d = load_actors(Path(args.ckpt_dir_d), args.suffix_d)

    for scen, delta_u in SCENARIOS.items():
        print(f"  {args.label} on {scen}...")
        res = eval_scenario(scen, delta_u, actors_h, actors_d, args.label, args.seed)
        out_p = out / f"{args.label}_{scen}.json"
        with open(out_p, "w") as f:
            json.dump(res, f)
        print(f"    saved {out_p} (max_df={res['max_df']:.3f})")


if __name__ == "__main__":
    main()
