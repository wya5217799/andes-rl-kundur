"""R84-W3 (D2-trajectory): Q-landscape on REAL SOTA state distribution.

Companion to ``r84_d2_q_landscape.py`` (which used N(0, I) prior obs).
The prior-obs D2 produced advantage_median ≈ +0.006, argmax_dist ≈ 1.12,
best_random − sota ≈ +0.043 in |Q| ≈ 0.063 units — flagged the critic-actor
inconsistency but with a "synthetic_obs_caveat" the script itself printed:
the critic might be confident on the real SOTA state manifold and only
indecisive on off-manifold N(0, I) samples.

This script removes that caveat. It runs the R72_w4 SOTA on LS1 + LS2,
captures every realised (obs_i, a*_i, h_actor_i, h_critic_i) tuple along
the trajectory, and probes the critic at each — using the **actual**
hidden state the critic carried into that step. Comparable summary
schema so the two results can be diff'd directly.

If the prior-obs finding (critic believes better actions exist far from
a*) replicates on real obs → R85 should pivot to critic-vs-actor
reconciliation (e.g. CACLA, target-network freeze ablation, or actor
gradient steps against the frozen critic).
If the finding **does not** replicate on real obs → the critic is
confident on the SOTA manifold and the prior-obs result reflects only
extrapolation noise → plateau is NOT critic-mediated.

Independent of R83-W3 (concurrent obs-aug training): ANDES is used for
≤ 2 short eval episodes (~60s, 1 WSL slot), well under the 3-slot
hard limit.

Output: results/r84_d2b_q_landscape_trajectory/summary.json
        results/r84_d2b_q_landscape_trajectory/per_step.json

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r84_d2b_q_landscape_trajectory.py
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
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

# ─── Config ───────────────────────────────────────────────────────────
SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r84_d2b_q_landscape_trajectory"
ENV_SEED = 42
STEPS = 50
N_ACTION_SAMPLES = 100  # match the synthetic-obs D2 run for direct comparability
ACTION_DIM = 2
ACTION_BOUND = 1.0
DEVICE = torch.device("cpu")
PROBE_RNG = np.random.default_rng(seed=1984)


def _probe_at(critic, obs_t: torch.Tensor, sota_action_t: torch.Tensor, h_crit) -> dict:
    """Single (s, h) Q-landscape probe.

    h is the critic's hidden state BEFORE this step — same as what the
    critic saw during the SOTA rollout leading into this state. Hidden
    state is broadcast across the N_ACTION_SAMPLES random-action batch.
    """
    with torch.no_grad():
        # SOTA Q values
        q1_s, q2_s, _ = critic(obs_t, sota_action_t, h_crit)
        q1_sota = q1_s.item()
        q2_sota = q2_s.item()

        # Random actions in [-1, 1]^A
        a_rand_np = PROBE_RNG.uniform(
            -ACTION_BOUND, ACTION_BOUND, size=(N_ACTION_SAMPLES, ACTION_DIM)
        ).astype(np.float32)
        a_rand_t = torch.from_numpy(a_rand_np).to(DEVICE)
        obs_batch = obs_t.expand(N_ACTION_SAMPLES, -1)

        # Broadcast hidden state to batch dim
        (h1, c1), (h2, c2) = h_crit
        h_batch = (
            (h1.expand(N_ACTION_SAMPLES, -1), c1.expand(N_ACTION_SAMPLES, -1)),
            (h2.expand(N_ACTION_SAMPLES, -1), c2.expand(N_ACTION_SAMPLES, -1)),
        )
        q1_r, q2_r, _ = critic(obs_batch, a_rand_t, h_batch)
        q1_r = q1_r.squeeze(-1).cpu().numpy()
        q2_r = q2_r.squeeze(-1).cpu().numpy()

    q_sota_mean = 0.5 * (q1_sota + q2_sota)
    q_rand_mean_per = 0.5 * (q1_r + q2_r)
    argmax_idx = int(np.argmax(q_rand_mean_per))
    argmax_a = a_rand_np[argmax_idx]
    sota_a_np = sota_action_t.cpu().numpy().flatten()

    return {
        "q_sota_mean": float(q_sota_mean),
        "q_rand_mean": float(np.mean(q_rand_mean_per)),
        "q_rand_max": float(np.max(q_rand_mean_per)),
        "argmax_dist": float(np.linalg.norm(argmax_a - sota_a_np)),
        "q1q2_disagreement": float(abs(q1_sota - q2_sota)),
        "best_random_minus_sota": float(np.max(q_rand_mean_per) - q_sota_mean),
        "advantage": float(q_sota_mean - np.mean(q_rand_mean_per)),
    }


def _grad_norm_at(critic, obs_t: torch.Tensor, sota_action_t: torch.Tensor, h_crit) -> float:
    """||∂Q/∂a||_2 at (s, a_sota, h)."""
    a = sota_action_t.detach().clone().requires_grad_(True)
    q1, q2, _ = critic(obs_t, a, h_crit)
    q_mean = (q1.squeeze(-1) + q2.squeeze(-1)) / 2
    grad = torch.autograd.grad(q_mean.sum(), a, retain_graph=False)[0]
    return float(grad.detach().norm(dim=-1).cpu().numpy().item())


def run_one_scenario(scen_name: str, delta_u: dict, agents: list) -> list[dict]:
    """Custom rollout: capture (obs, sota_action, h_critic) per (step, agent)."""
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    records: list[dict] = []
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)

        h_actor = [ag.actor.init_hidden(1, DEVICE) for ag in agents]
        h_critic = [ag.critic.init_hidden(1, DEVICE) for ag in agents]

        for step in range(STEPS):
            actions: dict[int, np.ndarray] = {}
            for i, ag in enumerate(agents):
                obs_t = torch.as_tensor(
                    obs[i], dtype=torch.float32, device=DEVICE
                ).unsqueeze(0)

                # Forward actor (advances h_actor)
                with torch.no_grad():
                    sota_action_t, h_actor_new = ag.actor(obs_t, h_actor[i])
                h_actor[i] = h_actor_new

                # Probe critic at (s, a*, h_critic_pre-step)
                probe = _probe_at(ag.critic, obs_t, sota_action_t, h_critic[i])
                grad_norm = _grad_norm_at(ag.critic, obs_t, sota_action_t, h_critic[i])

                # Advance critic h with (s, a*) — keep critic h aligned w/ rollout
                with torch.no_grad():
                    _, _, h_critic_new = ag.critic(
                        obs_t, sota_action_t, h_critic[i]
                    )
                h_critic[i] = h_critic_new

                actions[i] = sota_action_t.cpu().numpy().flatten().astype(np.float32)
                records.append({
                    "scenario": scen_name,
                    "step": step,
                    "agent": i,
                    "obs_norm": float(np.linalg.norm(obs[i])),
                    "sota_action": actions[i].tolist(),
                    "grad_norm": grad_norm,
                    **probe,
                })

            obs, _r, done, info = env.step(actions)
            if info.get("tds_failed"):
                print(f"  [tds_failed @ step {step}]")
                break
            if done:
                break
    finally:
        env.close()
    return records


def _stats_for(records: list[dict]) -> dict:
    if not records:
        return {"n_samples": 0}
    adv = np.array([r["advantage"] for r in records])
    argmax_d = np.array([r["argmax_dist"] for r in records])
    disagree = np.array([r["q1q2_disagreement"] for r in records])
    q_sota = np.array([r["q_sota_mean"] for r in records])
    best_minus = np.array([r["best_random_minus_sota"] for r in records])
    grad_n = np.array([r["grad_norm"] for r in records])

    return {
        "n_samples": len(records),
        "advantage_median": float(np.median(adv)),
        "advantage_mean": float(np.mean(adv)),
        "advantage_p10": float(np.percentile(adv, 10)),
        "advantage_p90": float(np.percentile(adv, 90)),
        "advantage_positive_frac": float(np.mean(adv > 0)),
        "argmax_dist_median": float(np.median(argmax_d)),
        "argmax_dist_p90": float(np.percentile(argmax_d, 90)),
        "q1q2_disagreement_median": float(np.median(disagree)),
        "q_sota_mean_abs_median": float(np.median(np.abs(q_sota))),
        "best_random_minus_sota_median": float(np.median(best_minus)),
        "best_random_minus_sota_p90": float(np.percentile(best_minus, 90)),
        "grad_norm_median": float(np.median(grad_n)),
        "grad_norm_p10": float(np.percentile(grad_n, 10)),
        "grad_norm_p90": float(np.percentile(grad_n, 90)),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[R84-D2b] Loading SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"[R84-D2b] {len(agents)} agents loaded")

    all_records: list[dict] = []
    for scen_name, delta_u in SCENARIOS.items():
        t_scen = time.time()
        print(f"\n[R84-D2b] === {scen_name} ===")
        recs = run_one_scenario(scen_name, delta_u, agents)
        print(f"  {len(recs)} probes in {time.time()-t_scen:.1f}s")
        all_records.extend(recs)

    # Aggregations
    global_stats = _stats_for(all_records)
    by_scen = {
        s: _stats_for([r for r in all_records if r["scenario"] == s])
        for s in SCENARIOS
    }
    by_agent = {
        f"agent_{i}": _stats_for([r for r in all_records if r["agent"] == i])
        for i in range(4)
    }

    # Reference magnitudes from the global stats
    q_mag = global_stats["q_sota_mean_abs_median"]
    eps_grad = 0.01 * max(q_mag, 1e-3)

    # Verdict — apply same thresholds the prior-obs D2 used, plus a check
    # that scales argmax_dist against the action-box diagonal sqrt(2*BOUND^2) ≈ 1.414.
    diag = float(np.sqrt(ACTION_DIM)) * ACTION_BOUND
    rel_argmax = global_stats["argmax_dist_median"] / diag
    rel_best_random = global_stats["best_random_minus_sota_median"] / max(q_mag, 1e-3)

    critic_confident = (
        global_stats["advantage_median"] > 0.05 * q_mag    # ≥ 5% of |Q|
        and rel_argmax < 0.25                              # argmax close to a*
        and rel_best_random < 0.10                         # best random within 10% of |Q|
        and global_stats["grad_norm_median"] > eps_grad    # critic not flat
    )

    if critic_confident:
        gate = "PASS_CRITIC_CONFIDENT_ON_REAL_TRAJ"
        interpretation = (
            "On the real SOTA state distribution, the critic IS confident: "
            "advantage > 5%|Q|, argmax close to a*, best-random within 10%|Q|. "
            "The prior-obs D2 finding (argmax_dist=1.12) was an extrapolation "
            "artefact. Plateau is NOT critic-mediated — pivot to obs ceiling "
            "(D3) or env floor (D4)."
        )
    elif rel_best_random > 0.5:
        gate = "FAIL_CRITIC_FAR_FROM_ACTOR_ON_REAL_TRAJ"
        interpretation = (
            "Confirmed on real SOTA states: critic believes substantially "
            "better actions exist far from a*. Plateau IS critic-actor "
            "inconsistency. R85 candidate: actor gradient ascent against the "
            "frozen critic, or CACLA-style soft replacement of actor with "
            "critic-argmax."
        )
    elif global_stats["advantage_median"] <= 0:
        gate = "FAIL_CRITIC_FLAT_OR_INVERTED"
        interpretation = (
            "SOTA action is worse than mean random on the real trajectory. "
            "Critic gradient signal is degenerated. R85: critic architecture "
            "or training-horizon upgrade."
        )
    else:
        gate = "MIXED"
        interpretation = (
            "Partial inconsistency. Run grad ascent against the frozen "
            "critic from a* for K steps and measure whether the resulting "
            "action gives better env-side cum_rf — that closes the loop."
        )

    summary = {
        "round": "R84",
        "wave": "W3_D2b",
        "title": "Q-landscape on REAL SOTA trajectory (companion to W1_D2)",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "suffix": "best",
        "env_seed": ENV_SEED,
        "steps_per_scenario": STEPS,
        "n_action_samples": N_ACTION_SAMPLES,
        "n_total_probes": len(all_records),
        "action_box_diagonal": diag,
        "q_magnitude_ref": q_mag,
        "eps_grad": eps_grad,
        "rel_argmax_dist": rel_argmax,
        "rel_best_random_minus_sota": rel_best_random,
        "global": global_stats,
        "by_scenario": by_scen,
        "by_agent": by_agent,
        "verdict": {
            "gate": gate,
            "interpretation": interpretation,
            "critic_confident": critic_confident,
        },
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    (OUT_DIR / "per_step.json").write_text(json.dumps(all_records, indent=2))

    print("\n[R84-D2b] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interpretation}")
    print()
    print(f"  q_magnitude_ref         = {q_mag:.4f}")
    print(f"  advantage_median        = {global_stats['advantage_median']:+.4f}  ({global_stats['advantage_median']/max(q_mag,1e-9):+.1%} of |Q|)")
    print(f"  argmax_dist_median      = {global_stats['argmax_dist_median']:.3f}  ({rel_argmax:.1%} of action diagonal {diag:.3f})")
    print(f"  best_random-sota_median = {global_stats['best_random_minus_sota_median']:+.4f}  ({rel_best_random:+.1%} of |Q|)")
    print(f"  grad_norm_median        = {global_stats['grad_norm_median']:.4f}  (eps_grad={eps_grad:.4f})")
    print(f"  q1/q2_disagreement_med  = {global_stats['q1q2_disagreement_median']:.4f}")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
