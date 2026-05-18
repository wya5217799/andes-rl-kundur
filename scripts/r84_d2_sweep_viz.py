"""R84-D2 visualisation — 1-D Q(s, a) landscape sweep along the action axes.

For each agent and a small batch of prior obs samples, freeze obs and one
action component, sweep the other component across [-1, 1], plot Q(s, a)
to confirm/refute the Q-landscape signal from r84_d2_q_landscape.py.

Output: results/r84_d2_q_landscape/action_sweep.png
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402


SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r84_d2_q_landscape"

N_OBS = 6
N_GRID = 51
DEVICE = "cpu"


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    agents = load_agents(SOTA_DIR, suffix="best")
    rng = np.random.default_rng(54)

    # Re-use obs sampling.
    obs_dim = agents[0].obs_dim
    obs_batch = torch.from_numpy(
        rng.normal(0, 1.0, size=(N_OBS, obs_dim)).astype(np.float32)
    ).to(DEVICE)

    grid = torch.linspace(-1.0, 1.0, N_GRID).to(DEVICE)

    fig, axes = plt.subplots(len(agents), 2, figsize=(10, 3.0 * len(agents)),
                              squeeze=False)
    for ai, agent in enumerate(agents):
        h_a = agent.actor.init_hidden(N_OBS, DEVICE)
        with torch.no_grad():
            a_sota, _ = agent.actor(obs_batch, h_a)

        for dim in range(2):
            ax = axes[ai][dim]
            for b in range(N_OBS):
                # Sweep action[dim] across grid; hold other dim at a_sota.
                a_grid = a_sota[b:b+1].repeat(N_GRID, 1)
                a_grid[:, dim] = grid
                obs_rep = obs_batch[b:b+1].repeat(N_GRID, 1)
                h_c = agent.critic.init_hidden(N_GRID, DEVICE)
                with torch.no_grad():
                    q1, q2, _ = agent.critic(obs_rep, a_grid, h_c)
                q = ((q1 + q2) / 2).squeeze(-1).cpu().numpy()
                line, = ax.plot(grid.cpu().numpy(), q, lw=1, alpha=0.7)
                ax.axvline(float(a_sota[b, dim].item()),
                           color=line.get_color(),
                           ls="--", lw=0.5, alpha=0.6)
            ax.set_xlabel(f"action[{dim}]")
            ax.set_ylabel(f"Q (agent {ai})")
            ax.set_title(f"agent {ai} dim {dim}: Q vs action[{dim}] (--) = a_sota[{dim}]")

    fig.suptitle("R84-D2: Q(s, a) action-axis sweep on prior obs (a_sota dashed)")
    fig.tight_layout()
    out = OUT_DIR / "action_sweep.png"
    fig.savefig(out, dpi=110)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
