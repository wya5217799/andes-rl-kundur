"""R132-W1: Fine-grain α-sweep [0.05, 0.10, 0.15, 0.20, 0.25, 0.30] to locate
warm-h_0 Pareto knee precisely.

[[CLM-0211]] (R121) showed α-curve has 3 regions: smooth trade-off ∈ [0, 0.3],
cliff ∈ (0.3, 0.5), saturated ∈ [0.5, 1.0]. α=0.1 gave -7% geo / +40% cum_rf.
R132 refines the smooth region in 6 points × 2 scen = 12 ANDES evals
to find where geo crosses the −5% / −10% loss thresholds.

Same script structure as R121 but with finer α grid in the safe range.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.evaluation.summary import score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r132_fine_alpha_sweep"
ENV_SEED = 42
STEPS = 150
N_ASCENT_STEPS = 500
LR_H = 0.05
ALPHAS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
DEVICE = torch.device("cpu")


def grad_ascent_h(agent, obs_0_t):
    hidden = agent.actor.hidden
    h = torch.zeros(1, hidden, device=DEVICE, requires_grad=True)
    c = torch.zeros(1, hidden, device=DEVICE, requires_grad=True)
    opt = torch.optim.Adam([h, c], lr=LR_H)
    for _ in range(N_ASCENT_STEPS):
        opt.zero_grad()
        a, _ = agent.actor(obs_0_t, (h, c))
        h0_critic = agent.critic.init_hidden(1, DEVICE)
        q1, q2, _ = agent.critic(obs_0_t, a, h0_critic)
        q = torch.min(q1.squeeze(-1), q2.squeeze(-1))
        (-q.sum()).backward()
        opt.step()
    return h.detach(), c.detach()


def get_obs_0(scen_name, delta_u, n_agents):
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    try:
        env.seed(ENV_SEED)
        obs = env.reset(delta_u=delta_u)
        return {i: obs[i].copy().astype(np.float32) for i in range(n_agents)}
    finally:
        env.close()


def rollout_with_warm_h(scen_name, delta_u, agents, warm_h_per_agent):
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    traces, cum_rf, max_df, osc_accum = [], 0.0, 0.0, 0.0
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        f_nom = env.FN
        h_rollouts = [(w[0].clone(), w[1].clone()) for w in warm_h_per_agent]
        for step in range(STEPS):
            actions = {}
            for i, ag in enumerate(agents):
                obs_t = torch.as_tensor(obs[i], dtype=torch.float32, device=DEVICE).unsqueeze(0)
                with torch.no_grad():
                    a_t, h_new = ag.actor(obs_t, h_rollouts[i])
                h_rollouts[i] = (h_new[0].detach(), h_new[1].detach())
                actions[i] = a_t.cpu().numpy().flatten().astype(np.float32)
            obs, _r, done, info = env.step(actions)
            if info.get("tds_failed"):
                break
            freq_hz = info["freq_hz"].astype(float).tolist()
            delta_f = [(f - f_nom) for f in freq_hz]
            f_bar = float(np.mean(freq_hz))
            step_rf = float(np.mean([(d - (f_bar - f_nom)) ** 2 for d in delta_f]))
            cum_rf -= step_rf
            max_df = max(max_df, float(np.max(np.abs(delta_f))))
            osc_accum += float(np.std(delta_f))
            traces.append({
                "step": step, "t": float(info["time"]),
                "freq_hz": freq_hz, "f_bar": f_bar, "step_rf": step_rf,
                "delta_P_es": info["P_es"].astype(float).tolist(),
                "delta_f_es": delta_f,
                "M_es": info["M_es"].astype(float).tolist(),
                "D_es": info["D_es"].astype(float).tolist(),
                "delta_M": info["delta_M"].astype(float).tolist(),
                "delta_D": info["delta_D"].astype(float).tolist(),
            })
            if done:
                break
    finally:
        env.close()
    return {
        "controller": "r72_w4_warm_h0_fine_alpha", "scenario": scen_name,
        "env_version": "v4", "cum_rf_total": cum_rf, "max_df": max_df,
        "osc": osc_accum, "n_steps": len(traces), "traces": traces,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    traces_dir = OUT_DIR / "traces"
    traces_dir.mkdir(exist_ok=True)
    t0 = time.time()
    agents = load_agents(SOTA_DIR, suffix="best")
    n_agents = len(agents)
    print(f"[R132] {n_agents} agents")

    obs_0 = get_obs_0("load_step_1", SCENARIOS["load_step_1"], n_agents)
    h_star_list = []
    for i, ag in enumerate(agents):
        obs_t = torch.as_tensor(obs_0[i], dtype=torch.float32, device=DEVICE).unsqueeze(0)
        h_s, c_s = grad_ascent_h(ag, obs_t)
        h_star_list.append((h_s, c_s))
    print("[R132] grad-ascent done")

    per_alpha = []
    for alpha in ALPHAS:
        warm_h = [(alpha * h, alpha * c) for h, c in h_star_list]
        scen_paths = {}
        for scen_name, delta_u in SCENARIOS.items():
            rec = rollout_with_warm_h(scen_name, delta_u, agents, warm_h)
            sp = traces_dir / f"alpha_{int(alpha*100):03d}_{scen_name}.json"
            sp.write_text(json.dumps(rec, indent=2))
            scen_paths[scen_name] = sp
        scored = score_trace_files(scen_paths, label=f"r132_alpha_{alpha:.2f}", is_ddic=True)
        print(f"  α={alpha:.2f}: geo={scored['geo']:.4f}  cum_rf={scored['cum_rf']:+.4f}")
        per_alpha.append({"alpha": alpha, **scored})

    # Find knee: largest α where geo > 0.371 (within -0.02 of 0.391)
    baseline_geo = 0.391
    geo_lower_pareto = baseline_geo - 0.02
    geo_lower_10pct = baseline_geo - 0.039  # -10% threshold

    knee_pareto = [p for p in per_alpha if p["geo"] >= geo_lower_pareto]
    knee_10pct = [p for p in per_alpha if p["geo"] >= geo_lower_10pct]

    best_knee_pareto = max(knee_pareto, key=lambda p: p["alpha"]) if knee_pareto else None
    best_knee_10pct = max(knee_10pct, key=lambda p: p["alpha"]) if knee_10pct else None

    summary = {
        "round": "R132",
        "wave": "W1_fine_alpha_sweep",
        "title": "Fine-grain α ∈ {0.05, ..., 0.30} sweep to locate warm-h_0 Pareto knee",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "env_seed": ENV_SEED,
        "steps": STEPS,
        "alphas": ALPHAS,
        "per_alpha": per_alpha,
        "baseline_geo": baseline_geo,
        "baseline_cum_rf": -0.068,
        "knee_pareto_strict_minus002": best_knee_pareto,
        "knee_relaxed_minus10pct": best_knee_10pct,
        "wall_seconds": time.time() - t0,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\n[R132] Done. wall={summary['wall_seconds']:.1f}s")
    print(f"  Pareto knee (geo ≥ {geo_lower_pareto:.4f}): {best_knee_pareto}")
    print(f"  Relaxed knee (geo ≥ {geo_lower_10pct:.4f}): {best_knee_10pct}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
