"""Q-0015 micro-probe: does TD3LSTMAgent actually use the --gamma value?

Hypothesis A (Q-0015 as filed): `--gamma 0.95` is silently ignored by
TD3LSTMAgent — R81-W9 final_eval 4-decimal identical with R72_w4 baseline.

Hypothesis B (alternative): gamma is correctly applied; R81-W9 hit the
same basin attractor (seed=54, 75 ep, R72_w4 hyper) so eval is identical
within 4-decimal precision even though the TD target differed during
training.

This probe distinguishes A vs B by checking the TD target computation
directly. Constructs two TD3LSTMAgents with gamma=0.95 vs gamma=0.99,
feeds the same synthetic batch through `update()`, and compares:

1. `self.gamma` attribute (the stored discount)
2. critic loss values after one update step
3. weight delta after one update step

If (1) differs but (2)/(3) match → silent ignore is real.
If all differ → gamma is being applied; R81-W9 was a basin-attractor coincidence.

Usage:
    python3 probes/q0015_gamma_silent_ignore_probe.py
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# ANDES stub (probe doesn't touch the env)
if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

import numpy as np
import torch

from andes_rl_kundur.agents.td3_lstm import TD3LSTMAgent


OBS_DIM = 7
ACTION_DIM = 2
HIDDEN = 64
SEED = 1984
BATCH_SEQ = 4   # batch size in sequences
SEQ_LEN = 25    # match TD3LSTMAgent default
BURN_IN = 5


def make_agent(gamma: float, seed: int = SEED) -> TD3LSTMAgent:
    torch.manual_seed(seed)
    np.random.seed(seed)
    return TD3LSTMAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        hidden_sizes=[HIDDEN, HIDDEN, HIDDEN, HIDDEN],
        lr=3e-4,
        gamma=gamma,
        tau=0.001,
        buffer_size=200,
        batch_size=BATCH_SEQ,
        device=torch.device("cpu"),
        seq_len=SEQ_LEN,
        burn_in=BURN_IN,
        lr_warmup_eps=0,
    )


def fill_buffer(agent: TD3LSTMAgent, n_episodes: int = 8, seed: int = SEED) -> None:
    """Synthetic episodes — same RNG seed each agent so buffers are identical."""
    rng = np.random.default_rng(seed)
    for _ in range(n_episodes):
        agent.begin_episode()
        episode_len = SEQ_LEN + BURN_IN + 5
        for t in range(episode_len):
            obs = rng.standard_normal(OBS_DIM).astype(np.float32)
            action = rng.uniform(-1, 1, size=ACTION_DIM).astype(np.float32)
            reward = float(rng.standard_normal())
            next_obs = rng.standard_normal(OBS_DIM).astype(np.float32)
            done = (t == episode_len - 1)
            agent.store_transition(obs, action, reward, next_obs, done)


def actor_weight_snapshot(agent: TD3LSTMAgent) -> torch.Tensor:
    return torch.cat([p.detach().flatten().clone() for p in agent.actor.parameters()])


def critic_weight_snapshot(agent: TD3LSTMAgent) -> torch.Tensor:
    return torch.cat([p.detach().flatten().clone() for p in agent.critic.parameters()])


def run_probe(label: str, gamma: float) -> dict:
    """Build agent, fill buffer with same RNG seed, run one update() call.

    All RNGs (torch.manual_seed, np.random.seed, np.random.default_rng) are
    re-seeded with SEED so the two agents see byte-identical inputs.
    """
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    ag = make_agent(gamma=gamma, seed=SEED)
    fill_buffer(ag, n_episodes=8, seed=SEED)

    # Snapshot critic weights before update
    actor_before = actor_weight_snapshot(ag)
    critic_before = critic_weight_snapshot(ag)

    # Re-seed once more so the torch RNG inside update() matches
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    info = ag.update()

    actor_after = actor_weight_snapshot(ag)
    critic_after = critic_weight_snapshot(ag)

    actor_delta = float((actor_after - actor_before).norm().item())
    critic_delta = float((critic_after - critic_before).norm().item())

    return {
        "label": label,
        "gamma_stored": ag.gamma,
        "update_info": info,
        "actor_weight_delta_L2": actor_delta,
        "critic_weight_delta_L2": critic_delta,
        "critic_weight_after_norm": float(critic_after.norm().item()),
    }


def main() -> int:
    res_095 = run_probe("gamma_0.95", 0.95)
    res_099 = run_probe("gamma_0.99", 0.99)

    print("=" * 70)
    print("Q-0015 probe — does TD3LSTMAgent use the --gamma value?")
    print("=" * 70)
    for r in [res_095, res_099]:
        print(f"\n{r['label']}:")
        print(f"  self.gamma            = {r['gamma_stored']}")
        print(f"  update_info           = {r['update_info']}")
        print(f"  actor_weight_delta_L2 = {r['actor_weight_delta_L2']:.6f}")
        print(f"  critic_weight_delta_L2 = {r['critic_weight_delta_L2']:.6f}")

    print("\n" + "=" * 70)
    print("Comparison:")
    gamma_diff = res_095["gamma_stored"] != res_099["gamma_stored"]
    critic_delta_diff = abs(res_095["critic_weight_delta_L2"] - res_099["critic_weight_delta_L2"])
    actor_delta_diff = abs(res_095["actor_weight_delta_L2"] - res_099["actor_weight_delta_L2"])

    print(f"  self.gamma differs?         {gamma_diff}")
    print(f"  |Δ critic_weight_delta|     {critic_delta_diff:.6e}")
    print(f"  |Δ actor_weight_delta|      {actor_delta_diff:.6e}")
    print()

    if gamma_diff and critic_delta_diff > 1e-9:
        print("VERDICT: gamma IS being applied correctly.")
        print("  → Q-0015 'silent ignore' hypothesis REJECTED.")
        print("  → R81-W9 4-decimal-identical eval was a basin-attractor coincidence.")
        print("  → γ ablation should be safe to run — won't be silently no-op.")
        rc = 0
    elif gamma_diff and critic_delta_diff < 1e-9:
        print("VERDICT: gamma is STORED but NOT USED — silent ignore confirmed.")
        print("  → Q-0015 confirmed. Critic update doesn't depend on gamma.")
        print("  → Fix needed before γ ablation can be run.")
        rc = 1
    else:
        print("VERDICT: probe inconclusive (gammas same or critic doesn't update).")
        rc = 2

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
