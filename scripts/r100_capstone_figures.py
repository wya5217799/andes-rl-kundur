"""R100 paper-capstone figures — side-by-side R72_w4 SOTA vs R100 hreg.

Generates two paper-quality figures comparing the two policies that
achieve approximately equal geo (0.391 vs 0.383) but with radically
different policy structure:

  Fig A: per-agent action trajectories under obs=0 stream (50 steps)
         Shows R72_w4 saturates to ±1; R100 stays in interior.
  Fig B: ||h_actor(t)|| evolution under obs=0 stream
         Shows R72_w4 grows to ~5; R100 stays bounded ~2.

These figures support the R100 capstone claim (CLM-0190): the 0.391
plateau is policy-invariant — bang-bang vs continuous controllers
both achieve ~0.39, so the ceiling is env / reward / observation
structural, not policy pathology.

Output: results/r100_capstone_figs/{action_compare.pdf, h_norm_compare.pdf}.
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

SOTA = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
HREG = ROOT / "results" / "r100_w1_hreg_lambda0p01_s54"
OUT = ROOT / "results" / "r100_capstone_figs"
OUT.mkdir(parents=True, exist_ok=True)

N_STEPS = 50
DEVICE = "cpu"


def roll(agent, obs_stream: torch.Tensor) -> dict:
    h_prev = agent.actor.init_hidden(1, DEVICE)
    h_norms = []
    actions = []
    for t in range(obs_stream.shape[0]):
        with torch.no_grad():
            h_new, c_new = agent.actor.lstm(obs_stream[t:t+1], h_prev)
            z = agent.actor.fc_out(h_new)
            a = torch.tanh(z)
        h_norms.append(float(h_new.norm()))
        actions.append(a[0].cpu().numpy())
        h_prev = (h_new, c_new)
    return {"h_norms": np.array(h_norms), "actions": np.array(actions)}


def collect(ckpt_dir: Path) -> tuple[list[dict], int]:
    agents = load_agents(
        ckpt_dir, suffix="best" if (ckpt_dir / "agent_0_best.pt").exists() else "final"
    )
    obs_dim = agents[0].obs_dim
    obs_zero = torch.zeros(N_STEPS, obs_dim)
    return [roll(ag, obs_zero) for ag in agents], obs_dim


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 7,
        "figure.dpi": 150,
    })

    print("Loading R72_w4 SOTA + R100 hreg ckpts...")
    sota_data, _ = collect(SOTA)
    hreg_data, _ = collect(HREG)

    # ── Figure A: per-agent action trajectories ─────────────────────────
    fig, axes = plt.subplots(2, 4, figsize=(11, 4.5), sharex=True, sharey=True)
    titles_top = ["R72_w4 SOTA (bang-bang, geo=0.391)"] + [""] * 3
    titles_bot = ["R100 hreg (continuous, geo=0.383)"] + [""] * 3
    for ai in range(4):
        # Top row: SOTA
        ax = axes[0][ai]
        ax.plot(sota_data[ai]["actions"][:, 0], label="ΔM_norm", color="C0", lw=1.2)
        ax.plot(sota_data[ai]["actions"][:, 1], label="ΔD_norm", color="C1", lw=1.2)
        ax.axhline(+1.0, color="black", lw=0.4, ls=":")
        ax.axhline(-1.0, color="black", lw=0.4, ls=":")
        ax.set_ylim(-1.1, 1.1)
        ax.set_title(f"Agent {ai}" + (f"  —  {titles_top[ai]}" if ai == 0 else ""))
        if ai == 0:
            ax.set_ylabel("action (R72_w4)")
            ax.legend(loc="upper right")
        # Bottom row: hreg
        ax = axes[1][ai]
        ax.plot(hreg_data[ai]["actions"][:, 0], label="ΔM_norm", color="C0", lw=1.2)
        ax.plot(hreg_data[ai]["actions"][:, 1], label="ΔD_norm", color="C1", lw=1.2)
        ax.axhline(+1.0, color="black", lw=0.4, ls=":")
        ax.axhline(-1.0, color="black", lw=0.4, ls=":")
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlabel("step")
        if ai == 0:
            ax.set_ylabel("action (R100 hreg)")
        if ai == 0:
            # Add side annotation
            ax.text(-12, 0, titles_bot[ai], rotation=90, fontsize=9,
                     va="center", ha="center", transform=ax.transData)
    fig.suptitle(
        "Policy-structural ablation: bang-bang vs continuous controllers "
        "achieve equivalent geo (Δ = 2%)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(OUT / "action_compare.pdf")
    fig.savefig(OUT / "action_compare.png", dpi=140)
    plt.close(fig)

    # ── Figure B: ||h_actor(t)|| evolution ──────────────────────────────
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    for ai in range(4):
        ax.plot(sota_data[ai]["h_norms"], color="C3", lw=1.0, alpha=0.7,
                label=f"R72_w4 SOTA" if ai == 0 else None)
        ax.plot(hreg_data[ai]["h_norms"], color="C2", lw=1.0, alpha=0.7,
                label=f"R100 hreg λ=0.01" if ai == 0 else None)
    ax.set_xlabel("step")
    ax.set_ylabel("||h_actor(t)||")
    ax.set_title("LSTM hidden-state drift under obs = 0 stream (4 agents)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3, lw=0.5)
    fig.tight_layout()
    fig.savefig(OUT / "h_norm_compare.pdf")
    fig.savefig(OUT / "h_norm_compare.png", dpi=140)
    plt.close(fig)

    # ── Stats table ─────────────────────────────────────────────────────
    sota_h_max = np.median([d["h_norms"].max() for d in sota_data])
    hreg_h_max = np.median([d["h_norms"].max() for d in hreg_data])
    sota_sat = np.mean([(np.abs(d["actions"]) > 0.95).mean() for d in sota_data])
    hreg_sat = np.mean([(np.abs(d["actions"]) > 0.95).mean() for d in hreg_data])

    print(f"\n=== R100 capstone figure stats ===")
    print(f"R72_w4 SOTA:  median max-||h||={sota_h_max:.2f}, action saturation={sota_sat*100:.1f}%")
    print(f"R100 hreg:    median max-||h||={hreg_h_max:.2f}, action saturation={hreg_sat*100:.1f}%")
    print(f"\nWritten:")
    print(f"  {OUT}/action_compare.pdf + .png")
    print(f"  {OUT}/h_norm_compare.pdf + .png")


if __name__ == "__main__":
    main()
