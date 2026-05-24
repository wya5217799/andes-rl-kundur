"""R112-W1: Warm-h_0 environment-side test — does CLM-0188 Q-lift translate to 6-axis?

[[CLM-0188]] (R104) showed 9/9 LSTM ckpts have ~80pp action-norm lift
from grad-ascent on (h_0, c_0) at step 0 with ΔQ > 0 universally. But
all of that was **Q-side measurement** — no one tested whether the
warm-h_0 actually produces a better trajectory under real ANDES TDS.
R104 explicitly identifies this gap.

R112 closes it. For each LS1 / LS2 scenario:

1. Reset env, capture obs_0 (paper Sec.IV-C scenario-conditioned).
2. For each agent, grad-ascent (h_0, c_0) starting from zero on 500
   Adam steps with lr=0.05 to maximise critic Q(obs_0, actor(obs_0, h_0, c_0),
   h_critic=0). [Identical to R99 / R104 methodology.]
3. Use the WARMED (h_0, c_0) per (scenario, agent) as the LSTM init
   instead of zeros at episode start. All other rollout steps use the
   normal stateful recurrence.
4. Run 150-step deterministic eval, capture trace, score canonical
   6-axis geo via `evaluation/summary.score_trace_files`.

Compare:
- **baseline_geo**: R72_w4 SOTA with zero h_init → 0.391 (CLM-0144)
- **warm_h0_geo**: R72_w4 SOTA with grad-ascent-warmed h_init

If warm_h0_geo ≥ baseline_geo + 0.05 → warm-h_0 IS a real lever, write
CLM, motivate R113 = train td3_lstm with learned h_init MLP.
If warm_h0_geo ∈ [baseline_geo − 0.05, baseline_geo + 0.05] → no effect;
R104 Q-side lift is "off-trajectory" (over-correction or transient).
If warm_h0_geo < baseline_geo − 0.05 → warm-h_0 HURTS — too aggressive
step-0 action causes oscillation or divergence.

Wall: ~30s ANDES (1 eval × 2 scenarios) + 4 × ~5s grad-ascent = ~80s.

Output: `results/r112_warmh0_env_eval/{summary.json, traces/}`

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r112_warmh0_env_eval.py
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
OUT_DIR = ROOT / "results" / "r112_warmh0_env_eval"
ENV_SEED = 42
STEPS = 150  # canonical 30s window @ DT=0.2
N_ASCENT_STEPS = 500
LR_H = 0.05
DEVICE = torch.device("cpu")


# ─── Grad-ascent for warm h_init ──────────────────────────────────────

def grad_ascent_h(agent, obs_0_t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """500-step Adam ascent on (h, c) from zero, maximising critic min(Q1,Q2).

    Mirrors R99 / R104 methodology. h_critic kept at zero (episode-start).
    Returns optimised (h*, c*) plus diagnostics.
    """
    hidden = agent.actor.hidden

    # Baseline at zero h
    with torch.no_grad():
        h_zero = torch.zeros(1, hidden, device=DEVICE)
        c_zero = torch.zeros(1, hidden, device=DEVICE)
        a_zero, _ = agent.actor(obs_0_t, (h_zero, c_zero))
        h0_critic = agent.critic.init_hidden(1, DEVICE)
        q1_z, q2_z, _ = agent.critic(obs_0_t, a_zero, h0_critic)
        q_zero = float(torch.min(q1_z, q2_z).item())
        a_zero_norm = float(a_zero.norm(dim=-1).item())

    # Grad-ascent
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

    with torch.no_grad():
        a_star, _ = agent.actor(obs_0_t, (h, c))
        h0_critic = agent.critic.init_hidden(1, DEVICE)
        q1_s, q2_s, _ = agent.critic(obs_0_t, a_star, h0_critic)
        q_star = float(torch.min(q1_s, q2_s).item())
        a_star_norm = float(a_star.norm(dim=-1).item())
        h_norm = float(h.norm(dim=-1).item())
        c_norm = float(c.norm(dim=-1).item())

    diag = {
        "q_zero": q_zero,
        "q_star": q_star,
        "q_gain": q_star - q_zero,
        "a_norm_zero": a_zero_norm,
        "a_norm_star": a_star_norm,
        "h_norm_star": h_norm,
        "c_norm_star": c_norm,
    }
    return h.detach(), c.detach(), diag


# ─── Stateful rollout with WARMED h_init per agent ────────────────────

def rollout_with_warm_h(
    scen_name: str,
    delta_u: dict,
    agents: list,
    warm_h_per_agent: list[tuple[torch.Tensor, torch.Tensor]],
) -> dict:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    traces: list[dict] = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS
        f_nom = env.FN

        # Initialise per-agent rollout hidden state with warmed h
        # The TD3LSTMAgent stores rollout h in self._h_rollout; we
        # bypass select_action and do a manual rollout to control h_init.
        h_rollouts = [
            (warm_h_per_agent[i][0].clone(), warm_h_per_agent[i][1].clone())
            for i in range(n_agents)
        ]

        for step in range(STEPS):
            actions: dict[int, np.ndarray] = {}
            for i, ag in enumerate(agents):
                obs_t = torch.as_tensor(
                    obs[i], dtype=torch.float32, device=DEVICE
                ).unsqueeze(0)
                with torch.no_grad():
                    a_t, h_new = ag.actor(obs_t, h_rollouts[i])
                h_rollouts[i] = (h_new[0].detach(), h_new[1].detach())
                actions[i] = a_t.cpu().numpy().flatten().astype(np.float32)

            obs, _rewards, done, info = env.step(actions)
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
                "step": step,
                "t": float(info["time"]),
                "freq_hz": freq_hz,
                "f_bar": f_bar,
                "step_rf": step_rf,
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
        "controller":  "r72_w4_sota_warm_h0",
        "scenario":    scen_name,
        "env_version": "v4",
        "cum_rf_total": cum_rf,
        "max_df":       max_df,
        "osc":          osc_accum,
        "n_steps":      len(traces),
        "traces":       traces,
    }


def get_obs_0(scen_name: str, delta_u: dict, n_agents: int) -> dict[int, np.ndarray]:
    """Reset env, capture obs_0 per agent, close env."""
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    try:
        env.seed(ENV_SEED)
        obs = env.reset(delta_u=delta_u)
        return {i: obs[i].copy().astype(np.float32) for i in range(n_agents)}
    finally:
        env.close()


# ─── Main ─────────────────────────────────────────────────────────────

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "traces").mkdir(exist_ok=True)
    t0 = time.time()

    print(f"[R112] Load SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    n_agents = len(agents)
    print(f"[R112] {n_agents} agents loaded")

    # ── Phase 1: per-scenario grad-ascent on initial obs ──
    print("\n[R112] Phase 1: grad-ascent on real obs_0 per scenario")
    warm_h_per_scen: dict[str, list[tuple[torch.Tensor, torch.Tensor]]] = {}
    grad_diag: dict[str, list[dict]] = {}

    for scen_name, delta_u in SCENARIOS.items():
        t_s = time.time()
        obs_0 = get_obs_0(scen_name, delta_u, n_agents)
        warm_h_list = []
        diag_list = []
        for i, ag in enumerate(agents):
            obs_0_t = torch.as_tensor(
                obs_0[i], dtype=torch.float32, device=DEVICE
            ).unsqueeze(0)
            h_star, c_star, diag = grad_ascent_h(ag, obs_0_t)
            diag["agent"] = i
            warm_h_list.append((h_star, c_star))
            diag_list.append(diag)
            print(f"  {scen_name} agent {i}: ||a||={diag['a_norm_zero']:.3f}→{diag['a_norm_star']:.3f}  "
                  f"Q={diag['q_zero']:+.4f}→{diag['q_star']:+.4f}  ||h*||={diag['h_norm_star']:.2f}")
        warm_h_per_scen[scen_name] = warm_h_list
        grad_diag[scen_name] = diag_list
        print(f"  {scen_name} grad-ascent done in {time.time()-t_s:.1f}s")

    # ── Phase 2: zero-h baseline + warm-h_0 eval ──
    print("\n[R112] Phase 2: env-side rollout (zero-h baseline + warm-h_0)")

    # Zero-h baseline (recreate baseline number for direct comparison)
    zero_h_per_agent = [
        (torch.zeros(1, agents[i].actor.hidden, device=DEVICE),
         torch.zeros(1, agents[i].actor.hidden, device=DEVICE))
        for i in range(n_agents)
    ]
    baseline_paths: dict[str, Path] = {}
    warm_paths: dict[str, Path] = {}
    for scen_name, delta_u in SCENARIOS.items():
        t_s = time.time()
        # Baseline (zero h)
        rec_base = rollout_with_warm_h(scen_name, delta_u, agents, zero_h_per_agent)
        rec_base["controller"] = "r72_w4_sota_zero_h0_baseline"
        bp = OUT_DIR / "traces" / f"baseline_{scen_name}.json"
        bp.write_text(json.dumps(rec_base, indent=2))
        baseline_paths[scen_name] = bp

        # Warm h_0
        rec_warm = rollout_with_warm_h(scen_name, delta_u, agents, warm_h_per_scen[scen_name])
        wp = OUT_DIR / "traces" / f"warmh0_{scen_name}.json"
        wp.write_text(json.dumps(rec_warm, indent=2))
        warm_paths[scen_name] = wp
        print(f"  {scen_name} rollouts done in {time.time()-t_s:.1f}s "
              f"(baseline n_steps={rec_base['n_steps']}, warm n_steps={rec_warm['n_steps']})")

    # Score both via canonical
    baseline_score = score_trace_files(baseline_paths, label="r112_zero_h0_baseline", is_ddic=True)
    warm_score = score_trace_files(warm_paths, label="r112_warm_h0", is_ddic=True)

    delta_geo = warm_score["geo"] - baseline_score["geo"]
    delta_cum_rf = warm_score["cum_rf"] - baseline_score["cum_rf"]

    # Verdict
    if delta_geo >= 0.05:
        gate = "WARM_H0_LIFTS_GEO"
        interp = (
            f"warm_h0 lifts geo by {delta_geo:+.4f} (≥ +0.05 threshold). "
            f"CLM-0188 Q-side architectural slack DOES translate to env-side "
            f"trajectory benefit. R113 candidate: train td3_lstm with learned "
            f"h_init head."
        )
    elif delta_geo <= -0.05:
        gate = "WARM_H0_HURTS_GEO"
        interp = (
            f"warm_h0 HURTS geo by {delta_geo:+.4f}. The 80pp step-0 action lift "
            f"is too aggressive — likely over-correction or transient oscillation. "
            f"R113 must penalise step-0 magnitude or use a smaller warm h."
        )
    else:
        gate = "WARM_H0_NEUTRAL"
        interp = (
            f"warm_h0 changes geo by only {delta_geo:+.4f} (within noise band). "
            f"Q-side lift does NOT translate to env-side: critic's Q gain at "
            f"step 0 is absorbed by the smoothing dynamics of the rest of the "
            f"trajectory. CLM-0188 Q-lift is a forensic curiosity, not a "
            f"plateau lever."
        )

    summary = {
        "round": "R112",
        "wave": "W1_warm_h0_env_eval",
        "title": "Does CLM-0188 warm-h_0 Q-lift translate to 6-axis on ANDES eval?",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "suffix": "best",
        "env_seed": ENV_SEED,
        "steps": STEPS,
        "n_ascent_steps": N_ASCENT_STEPS,
        "lr_h": LR_H,
        "grad_ascent_diagnostics": grad_diag,
        "baseline_score": baseline_score,
        "warm_h0_score": warm_score,
        "delta_geo": delta_geo,
        "delta_cum_rf": delta_cum_rf,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
        },
        "wall_seconds": time.time() - t0,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print("\n[R112] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}\n")
    print(f"  baseline_geo  = {baseline_score['geo']:.4f}  cum_rf = {baseline_score['cum_rf']:+.4f}")
    print(f"  warm_h0_geo   = {warm_score['geo']:.4f}  cum_rf = {warm_score['cum_rf']:+.4f}")
    print(f"  Δgeo          = {delta_geo:+.4f}")
    print(f"  Δcum_rf       = {delta_cum_rf:+.4f}")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
