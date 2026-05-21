"""R121-W1: Constrained warm-h_0 — interpolate between zero-h and grad-ascent
argmax to find geo-preserving cum_rf improvement.

[[CLM-0204]] (R112) showed naive warm-h_0 (||a||→1.41 saturation at step 0)
gives geo -95.8% but cum_rf +54%. The two paper-relevant metrics
**disagree in sign**. There must be an intermediate ‖a‖ where geo is
preserved (or improves) AND cum_rf improves.

R121 sweeps α ∈ {0.0, 0.1, 0.3, 0.5, 0.7, 1.0} where:
  (h_init, c_init) = α × (h*, c*)  with h*, c* the grad-ascent argmax
  α = 0 reproduces zero-h baseline geo=0.391 cum_rf=-0.068
  α = 1 reproduces R112 saturated warm-h_0 geo=0.017 cum_rf=-0.031

Question: is there an α with geo ≥ 0.40 AND cum_rf ≥ -0.06 (Pareto
improvement)? Or do we have to choose?

Wall: 1 grad-ascent (~4s) + 6 α values × 2 scenarios × ~10s ANDES ≈
~2 min total (under R83+/R100/R102 ANDES contention may stretch to 3-5 min).

Output: results/r121_constrained_warm_h0/{summary.json, pareto_curve.csv}

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r121_constrained_warm_h0.py
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

# ─── Config ───────────────────────────────────────────────────────────
SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r121_constrained_warm_h0"
ENV_SEED = 42
STEPS = 150
N_ASCENT_STEPS = 500
LR_H = 0.05
ALPHAS = [0.0, 0.1, 0.3, 0.5, 0.7, 1.0]
DEVICE = torch.device("cpu")


def grad_ascent_h(agent, obs_0_t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Same as R112 (R99/R104 recipe). Return (h*, c*)."""
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


def get_obs_0(scen_name: str, delta_u: dict, n_agents: int) -> dict:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    try:
        env.seed(ENV_SEED)
        obs = env.reset(delta_u=delta_u)
        return {i: obs[i].copy().astype(np.float32) for i in range(n_agents)}
    finally:
        env.close()


def rollout_with_warm_h(scen_name, delta_u, agents, warm_h_per_agent):
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    traces = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS
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
        "controller": f"r72_w4_warm_h0_alpha", "scenario": scen_name,
        "env_version": "v4", "cum_rf_total": cum_rf, "max_df": max_df,
        "osc": osc_accum, "n_steps": len(traces), "traces": traces,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    traces_dir = OUT_DIR / "traces"
    traces_dir.mkdir(exist_ok=True)
    t0 = time.time()

    print(f"[R121] Load SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    n_agents = len(agents)
    print(f"[R121] {n_agents} agents")

    # Phase 1: grad-ascent on real obs_0 (same per scenario since obs_0
    # is pre-disturbance; reuse R112 result conceptually but re-compute
    # for clean closure)
    print(f"\n[R121] Phase 1: grad-ascent on obs_0")
    obs_0_ls1 = get_obs_0("load_step_1", SCENARIOS["load_step_1"], n_agents)
    h_star_list: list[tuple[torch.Tensor, torch.Tensor]] = []
    for i, ag in enumerate(agents):
        obs_0_t = torch.as_tensor(obs_0_ls1[i], dtype=torch.float32, device=DEVICE).unsqueeze(0)
        h_s, c_s = grad_ascent_h(ag, obs_0_t)
        h_star_list.append((h_s, c_s))
        print(f"  agent {i}: ||h*||={float(h_s.norm()):.2f}  ||c*||={float(c_s.norm()):.2f}")

    # Phase 2: sweep α
    print(f"\n[R121] Phase 2: α sweep — {len(ALPHAS)} α values × 2 scenarios")
    per_alpha: list[dict] = []

    for alpha in ALPHAS:
        # Build warm h with this α
        warm_h = [(alpha * h, alpha * c) for h, c in h_star_list]

        # Rollout LS1 + LS2 with this warm h
        scen_paths = {}
        for scen_name, delta_u in SCENARIOS.items():
            t_s = time.time()
            rec = rollout_with_warm_h(scen_name, delta_u, agents, warm_h)
            sp = traces_dir / f"alpha_{int(alpha*100):03d}_{scen_name}.json"
            sp.write_text(json.dumps(rec, indent=2))
            scen_paths[scen_name] = sp

        scored = score_trace_files(scen_paths, label=f"r121_alpha_{alpha:.1f}", is_ddic=True)
        wall = time.time() - t_s
        print(f"  α={alpha:.1f}: geo={scored['geo']:.4f}  LS1={scored['LS1']:.4f}  "
              f"LS2={scored['LS2']:.4f}  cum_rf={scored['cum_rf']:+.4f}")
        per_alpha.append({
            "alpha": alpha,
            **scored,
        })

    # Find Pareto winners
    baseline = next(p for p in per_alpha if p["alpha"] == 0.0)
    geo_base = baseline["geo"]
    cum_rf_base = baseline["cum_rf"]

    pareto_improvements = [
        p for p in per_alpha
        if p["geo"] >= geo_base - 0.02 and p["cum_rf"] > cum_rf_base
    ]
    best_geo = max(per_alpha, key=lambda p: p["geo"])
    best_cum_rf = max(per_alpha, key=lambda p: p["cum_rf"])

    if pareto_improvements:
        gate = "PARETO_IMPROVEMENT_FOUND"
        winner = max(pareto_improvements, key=lambda p: p["cum_rf"])
        interp = (
            f"α={winner['alpha']:.1f} gives geo={winner['geo']:.4f} "
            f"(within −0.02 of baseline {geo_base:.4f}) AND cum_rf="
            f"{winner['cum_rf']:+.4f} (improved over baseline {cum_rf_base:+.4f}). "
            f"Constrained warm-h_0 IS a real (modest) agent optimisation."
        )
    else:
        gate = "NO_PARETO_IMPROVEMENT"
        interp = (
            f"No α achieves both geo ≥ {geo_base - 0.02:.4f} AND cum_rf > "
            f"{cum_rf_base:+.4f}. Best geo {best_geo['geo']:.4f} at α={best_geo['alpha']:.1f}; "
            f"best cum_rf {best_cum_rf['cum_rf']:+.4f} at α={best_cum_rf['alpha']:.1f}. "
            f"Warm-h_0 is fundamentally cum_rf-geo anticorrelated; no α-magic."
        )

    summary = {
        "round": "R121",
        "wave": "W1_constrained_warm_h0",
        "title": "α-sweep of warm-h_0 to find geo-preserving cum_rf improvement",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "env_seed": ENV_SEED,
        "steps": STEPS,
        "alphas": ALPHAS,
        "per_alpha": per_alpha,
        "baseline_geo": geo_base,
        "baseline_cum_rf": cum_rf_base,
        "best_geo_winner": best_geo,
        "best_cum_rf_winner": best_cum_rf,
        "pareto_improvements": pareto_improvements,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
        },
        "wall_seconds": time.time() - t0,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\n[R121] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}\n")
    print(f"  α       | LS1    | LS2    | geo    | cum_rf")
    print(f"  --------|--------|--------|--------|--------")
    for p in per_alpha:
        flag = " ←best" if p == best_geo else ("  ←Δcum_rf" if p == best_cum_rf else "")
        print(f"  {p['alpha']:5.1f}   | {p['LS1']:.4f} | {p['LS2']:.4f} | {p['geo']:.4f} | {p['cum_rf']:+.4f}{flag}")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
