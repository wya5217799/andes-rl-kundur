"""R84-D2 — Q-function epistemic landscape on R72_w4 SOTA, zero-ANDES.

Reads `results/r72_w4_lstm_tau001_warmup5_s54/agent_*_best.pt` and runs Q(s, a)
forensics on the centralised critic of each agent. The R83 obs-space refactor
is running concurrently and holds the WSL ANDES session lock; this script
deliberately does **not** instantiate the env. All `obs` samples are drawn
from the standard-normal prior on the observation manifold — the conservative
"lower-bound" reading of the Q landscape's action-discriminability.

Three measurements per agent:

1.  **SOTA-action advantage A(s)** =  Q(s, a_sota) − mean_{a ~ U} Q(s, a)
    A(s) > 0 means the critic distinguishes the policy's action from a
    random baseline. A(s) ≈ 0 across many s ⇒ critic is flat ⇒ plateau
    candidate origin is the Q-function.

2.  **Q1/Q2 disagreement σ_Q1Q2** = mean |Q1 − Q2| at a_sota.
    R72_w4 trains twin critics; their disagreement is an epistemic
    uncertainty proxy. High σ → critic still has not converged on
    that region of action space.

3.  **action-axis sensitivity ∂Q/∂a** = ||∇_a Q(s, a)||_2 at a_sota.
    Computed via autograd. Low gradient → flat Q landscape (saturated).

Output: results/r84_d2_q_landscape/{summary.json, per_agent_landscape.csv}.

Pass criterion (plateau is **not** the critic):
    median A(s) > 0  AND  argmax_a Q ≈ a_sota AND  median ||∂Q/∂a|| > ε
where ε is chosen vs Q magnitude (printed in summary).
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# ANDES is WSL-only (CLAUDE.md / NOTES_ANDES.md). This forensics script never
# instantiates the env, but the package-level `__init__.py` does `import
# andes` transitively. Inject a stub so the package can finish loading; any
# attribute access on the stub at runtime would error loudly.
if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402

SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r84_d2_q_landscape"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Forensics knobs. Conservative defaults — small enough to run in ~30 s
# on CPU, large enough for stable median statistics.
N_OBS_SAMPLES: int = 200       # synthetic obs per agent
N_ACTION_SAMPLES: int = 100    # random actions per obs (Q comparison)
N_GRID_PER_DIM: int = 21       # 1-D action-axis sweep around a_sota
OBS_PRIOR_STD: float = 1.0     # obs ~ N(0, σ I), normalised obs convention
ACTION_BOUND: float = 1.0      # actions ∈ [-1, 1]^action_dim
DEVICE = "cpu"                 # critic is tiny, GPU-not-helpful


def _sample_obs(n: int, obs_dim: int, rng: np.random.Generator) -> torch.Tensor:
    arr = rng.normal(0.0, OBS_PRIOR_STD, size=(n, obs_dim)).astype(np.float32)
    return torch.from_numpy(arr).to(DEVICE)


def _sample_actions(n: int, action_dim: int, rng: np.random.Generator) -> torch.Tensor:
    arr = rng.uniform(-ACTION_BOUND, ACTION_BOUND, size=(n, action_dim)).astype(np.float32)
    return torch.from_numpy(arr).to(DEVICE)


def _h0_actor(agent, batch: int) -> tuple[torch.Tensor, torch.Tensor]:
    return agent.actor.init_hidden(batch, DEVICE)


def _h0_critic(agent, batch: int):
    return agent.critic.init_hidden(batch, DEVICE)


def _q_at(agent, obs: torch.Tensor, action: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Critic Q1 / Q2 at episode-start hidden state (zeros). Shape (B,)."""
    h = _h0_critic(agent, obs.shape[0])
    q1, q2, _ = agent.critic(obs, action, h)
    return q1.squeeze(-1), q2.squeeze(-1)


def _sota_actions(agent, obs: torch.Tensor) -> torch.Tensor:
    """Deterministic actor at episode-start hidden state. Shape (B, A)."""
    h = _h0_actor(agent, obs.shape[0])
    with torch.no_grad():
        a, _ = agent.actor(obs, h)
    return a


def _advantage_and_consistency(agent, obs: torch.Tensor, rng: np.random.Generator) -> dict:
    a_sota = _sota_actions(agent, obs)                                   # (B, A)
    q1_sota, q2_sota = _q_at(agent, obs, a_sota)                          # (B,)
    q_sota_mean = (q1_sota + q2_sota) / 2

    # Random action baseline: K samples per obs, then mean over K.
    B, A = a_sota.shape
    a_rand = _sample_actions(N_ACTION_SAMPLES * B, A, rng).view(N_ACTION_SAMPLES, B, A)
    q_rand_means: list[torch.Tensor] = []
    a_rand_argmax_buf = torch.empty_like(a_sota)
    best_q = torch.full((B,), -1e9, device=DEVICE)
    with torch.no_grad():
        for k in range(N_ACTION_SAMPLES):
            q1_k, q2_k = _q_at(agent, obs, a_rand[k])
            q_k = (q1_k + q2_k) / 2
            q_rand_means.append(q_k)
            # Track argmax_a over the random sample (cheap discrete approx).
            mask = q_k > best_q
            best_q = torch.where(mask, q_k, best_q)
            a_rand_argmax_buf = torch.where(mask.unsqueeze(-1), a_rand[k], a_rand_argmax_buf)

    q_rand_stack = torch.stack(q_rand_means, dim=0)        # (K, B)
    q_rand_mean = q_rand_stack.mean(dim=0)                 # (B,)

    # SOTA advantage (per obs).
    advantage = q_sota_mean - q_rand_mean                  # (B,)
    # Argmax consistency = L2 distance between sampled-argmax action and a_sota.
    argmax_dist = torch.norm(a_rand_argmax_buf - a_sota, dim=-1)
    # Q1/Q2 disagreement at a_sota.
    q1q2_disagreement = (q1_sota - q2_sota).abs()

    return {
        "q_sota_mean": q_sota_mean.detach().cpu().numpy(),
        "q_rand_mean": q_rand_mean.detach().cpu().numpy(),
        "advantage":   advantage.detach().cpu().numpy(),
        "argmax_dist": argmax_dist.detach().cpu().numpy(),
        "q1q2_disagree": q1q2_disagreement.detach().cpu().numpy(),
        "best_random_q": best_q.detach().cpu().numpy(),
    }


def _grad_norm_at_sota(agent, obs: torch.Tensor) -> np.ndarray:
    """||∇_a Q(s, a_sota)||_2 via autograd. Shape (B,)."""
    a_sota = _sota_actions(agent, obs).clone().requires_grad_(True)
    h = _h0_critic(agent, obs.shape[0])
    q1, q2, _ = agent.critic(obs, a_sota, h)
    q_mean = (q1.squeeze(-1) + q2.squeeze(-1)) / 2
    grad = torch.autograd.grad(q_mean.sum(), a_sota, retain_graph=False)[0]
    return grad.detach().norm(dim=-1).cpu().numpy()


def _agent_landscape(agent_idx: int, agent, rng: np.random.Generator) -> dict:
    obs_dim = agent.obs_dim
    action_dim = agent.action_dim
    obs = _sample_obs(N_OBS_SAMPLES, obs_dim, rng)

    adv_pkg = _advantage_and_consistency(agent, obs, rng)
    grad_norms = _grad_norm_at_sota(agent, obs)

    return {
        "agent_idx": agent_idx,
        "obs_dim": obs_dim,
        "action_dim": action_dim,
        "n_obs": N_OBS_SAMPLES,
        "n_action_samples": N_ACTION_SAMPLES,
        "advantage_median": float(np.median(adv_pkg["advantage"])),
        "advantage_p10": float(np.percentile(adv_pkg["advantage"], 10)),
        "advantage_p90": float(np.percentile(adv_pkg["advantage"], 90)),
        "advantage_positive_frac": float((adv_pkg["advantage"] > 0).mean()),
        "argmax_dist_median": float(np.median(adv_pkg["argmax_dist"])),
        "argmax_dist_max": float(np.max(adv_pkg["argmax_dist"])),
        "q1q2_disagreement_median": float(np.median(adv_pkg["q1q2_disagree"])),
        "q_sota_mean_abs_median": float(np.median(np.abs(adv_pkg["q_sota_mean"]))),
        "grad_norm_median": float(np.median(grad_norms)),
        "grad_norm_p10": float(np.percentile(grad_norms, 10)),
        "grad_norm_p90": float(np.percentile(grad_norms, 90)),
        "best_random_minus_sota_median": float(
            np.median(adv_pkg["best_random_q"] - adv_pkg["q_sota_mean"])
        ),
    }


def main() -> None:
    print(f"R84-D2: load SOTA from {SOTA_DIR}")
    if not SOTA_DIR.exists():
        sys.exit(f"FATAL: SOTA dir missing: {SOTA_DIR}")

    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"  loaded {len(agents)} agents")
    for i, ag in enumerate(agents):
        print(f"    agent {i}: obs_dim={ag.obs_dim} action_dim={ag.action_dim} "
              f"is_recurrent={getattr(ag, 'is_recurrent', False)}")

    rng = np.random.default_rng(54)
    per_agent = [_agent_landscape(i, ag, rng) for i, ag in enumerate(agents)]

    # Cross-agent aggregate.
    agg = {
        "advantage_median": float(np.median([a["advantage_median"] for a in per_agent])),
        "advantage_positive_frac_mean": float(
            np.mean([a["advantage_positive_frac"] for a in per_agent])
        ),
        "argmax_dist_median": float(np.median([a["argmax_dist_median"] for a in per_agent])),
        "q1q2_disagreement_median": float(
            np.median([a["q1q2_disagreement_median"] for a in per_agent])
        ),
        "grad_norm_median": float(np.median([a["grad_norm_median"] for a in per_agent])),
        "best_random_minus_sota_median": float(
            np.median([a["best_random_minus_sota_median"] for a in per_agent])
        ),
    }

    # Pass/fail relative to a magnitude reference (median |Q_sota|).
    q_mag = float(np.median([a["q_sota_mean_abs_median"] for a in per_agent]))
    eps_grad = 0.01 * q_mag   # 1% of Q magnitude per unit action change
    pass_critic = (
        agg["advantage_median"] > 0
        and agg["argmax_dist_median"] < 0.5
        and agg["grad_norm_median"] > eps_grad
    )

    summary = {
        "round": "R84",
        "wave": "W1_D2",
        "sota": SOTA_DIR.name,
        "n_agents": len(agents),
        "per_agent": per_agent,
        "agg": agg,
        "q_magnitude_ref": q_mag,
        "eps_grad": eps_grad,
        "pass_plateau_not_critic": pass_critic,
        "interpretation": (
            "PASS (plateau NOT from critic): Q discriminates SOTA from random, "
            "argmax_a Q ≈ a_sota, ∂Q/∂a non-trivial."
            if pass_critic
            else "FAIL (critic-mediated plateau): one or more diagnostics flat."
        ),
        "synthetic_obs_caveat": (
            "Obs sampled from N(0, I) prior, NOT SOTA state distribution. "
            "PASS rules out 'critic flat everywhere'; does NOT rule out "
            "'critic flat on SOTA state manifold'. ANDES-trajectory variant "
            "needed to upgrade to sufficient condition."
        ),
    }

    out_path = OUT_DIR / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print("\n--- R84-D2 summary ---")
    print(json.dumps(agg, indent=2))
    print(f"q_magnitude_ref = {q_mag:.4f}, eps_grad = {eps_grad:.4f}")
    print(f"PASS (plateau NOT from critic): {pass_critic}")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
