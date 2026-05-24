"""R93-W0b — LSTM hidden-state drift forensics, zero ANDES.

R93-W0 surfaced a surprise: actor fc_out weights are small (max_abs ≈
0.15) and pre-tanh logits on prior obs + h=0 cluster around |z| ≈ 0.1
(deep in tanh-linear regime). But R92-W1 / CLM-0170 reports 76%
saturation in real eval. The discrepancy must come from the LSTM
hidden-state h evolving across the 50-step rollout: starting from
h=0 (interior logit), accumulating context until fc_out(h) > 2-5
(tanh-saturated logit).

This script tests the LSTM-drift hypothesis directly:

A. **Drift-from-zero with constant obs**: forward LSTM with a fixed
   obs vector repeated 50 times; track ||h(t)||, fc_out(h(t)), and
   tanh(fc_out(h(t))) per step. If logit growth is the dominant
   effect, this captures it without needing real trajectory.

B. **Drift-from-zero with persistent excitation**: same as A but
   obs alternates sign per step (e.g., +e1, -e1, +e1, ...) — keeps
   the LSTM gates active. Catches whether the drift requires
   continuous excitation or happens from a single push.

C. **Drift on a single noisy obs sequence**: 50 steps of N(0, 0.5)
   obs (smaller scale than R93-W0's σ=1). Estimates how typical
   transient-period drift compares to bound saturation.

Output: results/r93_w0b_lstm_drift/{summary.json, drift_curves.png}.
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

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402

SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r93_w0b_lstm_drift"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_STEPS = 50          # match real episode length
DEVICE = "cpu"


def roll_one_obs_stream(agent, obs_stream: torch.Tensor) -> dict:
    """Forward agent.actor.lstm across obs_stream (N_STEPS, obs_dim).
    Returns h_norm, logit_z, realised_action per step (all 1-D arrays).
    """
    h_prev = agent.actor.init_hidden(1, DEVICE)
    h_norms: list[float] = []
    z_seq: list[np.ndarray] = []           # (N_STEPS, action_dim)
    a_seq: list[np.ndarray] = []
    for t in range(obs_stream.shape[0]):
        obs_t = obs_stream[t:t+1]
        with torch.no_grad():
            h_new, c_new = agent.actor.lstm(obs_t, h_prev)
            z = agent.actor.fc_out(h_new)
            a = torch.tanh(z)
        h_norms.append(float(h_new.norm()))
        z_seq.append(z[0].cpu().numpy())
        a_seq.append(a[0].cpu().numpy())
        h_prev = (h_new, c_new)
    return {
        "h_norms": h_norms,
        "logits": np.array(z_seq),         # (N_STEPS, action_dim)
        "actions": np.array(a_seq),
    }


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print(f"R93-W0b: load SOTA from {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    obs_dim = agents[0].obs_dim
    rng = np.random.default_rng(54)

    # Three obs streams.
    streams = {
        "A_constant_zero": torch.zeros(N_STEPS, obs_dim),
        "A_constant_e1": torch.tensor(
            np.array([[1.0] + [0.0] * (obs_dim - 1)] * N_STEPS, dtype=np.float32)
        ),
        "B_alternating_e1": torch.tensor(
            np.array(
                [[(-1.0) ** t] + [0.0] * (obs_dim - 1) for t in range(N_STEPS)],
                dtype=np.float32,
            )
        ),
        "C_random_sigma0p5": torch.from_numpy(
            rng.normal(0, 0.5, size=(N_STEPS, obs_dim)).astype(np.float32)
        ),
    }

    per_agent_results = []
    for ai, agent in enumerate(agents):
        agent_streams = {}
        for label, stream in streams.items():
            r = roll_one_obs_stream(agent, stream)
            saturated_steps = int(np.sum(
                np.abs(r["actions"]) > 0.95
            ).item())
            agent_streams[label] = {
                "h_norm_first": r["h_norms"][0],
                "h_norm_last": r["h_norms"][-1],
                "h_norm_max": float(np.max(r["h_norms"])),
                "logit_first_abs_max": float(np.max(np.abs(r["logits"][0]))),
                "logit_last_abs_max": float(np.max(np.abs(r["logits"][-1]))),
                "logit_max_abs": float(np.max(np.abs(r["logits"]))),
                "action_max_abs": float(np.max(np.abs(r["actions"]))),
                "saturated_step_action_count": saturated_steps,
                "h_norms_array": r["h_norms"],
                "logits_dim0": r["logits"][:, 0].tolist(),
                "logits_dim1": r["logits"][:, 1].tolist(),
                "actions_dim0": r["actions"][:, 0].tolist(),
                "actions_dim1": r["actions"][:, 1].tolist(),
            }
        per_agent_results.append({"agent_idx": ai, "streams": agent_streams})

    # Aggregate: do logits eventually saturate?
    by_stream: dict[str, list[float]] = {label: [] for label in streams}
    for r in per_agent_results:
        for label in streams:
            by_stream[label].append(r["streams"][label]["logit_max_abs"])
    agg = {
        label: {
            "logit_max_abs_median": float(np.median(by_stream[label])),
            "logit_max_abs_max": float(np.max(by_stream[label])),
            "saturates_predict": bool(np.median(by_stream[label]) > 2.0),
        }
        for label in streams
    }

    summary = {
        "round": "R93",
        "wave": "W0b_lstm_drift",
        "sota": SOTA_DIR.name,
        "n_steps": N_STEPS,
        "obs_streams_tested": list(streams.keys()),
        "per_agent": [
            {
                "agent_idx": r["agent_idx"],
                "streams": {
                    label: {k: v for k, v in stream_pkg.items()
                             if k not in ("h_norms_array", "logits_dim0", "logits_dim1",
                                          "actions_dim0", "actions_dim1")}
                    for label, stream_pkg in r["streams"].items()
                },
            }
            for r in per_agent_results
        ],
        "aggregate_per_stream": agg,
        "interpretation": (
            "If any stream's median logit_max_abs > 2, the LSTM hidden "
            "state alone (no realistic trajectory variation) drives the "
            "fc_out(h) past the tanh saturation point. This would "
            "confirm the LSTM-drift mechanism for R92 saturation; "
            "widen-bound experiment (R93-W1) is still informative but "
            "the root cause is LSTM state evolution, NOT actor weight "
            "magnitude."
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    # Figure: drift curves per agent × stream.
    fig, axes = plt.subplots(4, len(streams), figsize=(4 * len(streams), 12),
                              sharex=True)
    for ai, r in enumerate(per_agent_results):
        for ci, label in enumerate(streams):
            ax = axes[ai][ci]
            pkg = r["streams"][label]
            ax.plot(pkg["actions_dim0"], lw=1, label="action[0]")
            ax.plot(pkg["actions_dim1"], lw=1, label="action[1]", alpha=0.7)
            ax.axhline(+0.95, color="red", lw=0.5, ls="--")
            ax.axhline(-0.95, color="red", lw=0.5, ls="--")
            ax.set_ylim(-1.1, 1.1)
            ax.set_title(f"ag{ai}: {label}")
            ax.set_xlabel("step")
            ax.set_ylabel("action")
            if ai == 0 and ci == 0:
                ax.legend(fontsize=7)
    fig.suptitle("R93-W0b LSTM-driven action drift, no ANDES")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "drift_curves.png", dpi=110)
    plt.close(fig)

    print("\n=== R93-W0b LSTM drift digest ===")
    print("Stream-aggregate logit_max_abs across 4 agents:")
    for label, a in agg.items():
        sat = "SATURATES" if a["saturates_predict"] else "stays interior"
        print(f"  {label:<22} median = {a['logit_max_abs_median']:>6.3f}, "
              f"max = {a['logit_max_abs_max']:>6.3f}  ({sat})")
    print("\nPer-agent terminal h_norms and action magnitudes:")
    for r in per_agent_results:
        for label in streams:
            p = r["streams"][label]
            print(f"  ag{r['agent_idx']} {label}: "
                  f"h_norm 0→last {p['h_norm_first']:.2f}→{p['h_norm_last']:.2f}, "
                  f"|z|_max={p['logit_max_abs']:.2f}, "
                  f"|a|_max={p['action_max_abs']:.3f}, "
                  f"saturated_steps={p['saturated_step_action_count']}/{2*N_STEPS}")
    print(f"\nWritten: {OUT_DIR}/{{summary.json, drift_curves.png}}")


if __name__ == "__main__":
    main()
