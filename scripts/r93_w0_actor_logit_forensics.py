"""R93-W0 — zero-ANDES actor pre-tanh logit + fc_out weight forensics.

Corroborates R92-W1 / CLM-0170 ("R72_w4 SOTA pins 76% of every step at
±1 action boundary") by examining the actor's MLP pre-tanh logits.

If the policy were genuinely operating in the action interior (CLM-0149/
0153/0154 framing), pre-tanh logits would cluster around |z| < 2
(tanh(2) = 0.96). If the policy is structurally pushed past tanh
saturation, logits would cluster at |z| > 2-5, with the tanh squash
clipping the realised action to ±1.

Two measurements per agent:

A. **fc_out (actor output head) weight + bias magnitudes**: a TD3
   LSTMCell-actor outputs `a = tanh(fc_out(h))`, where fc_out is
   Linear(hidden, action_dim). Magnitudes show how aggressively the
   actor was trained to push outputs to the boundary.

B. **Pre-tanh logit distribution over prior obs**: 200 obs ~ N(0, I),
   forward LSTM with h0=zeros, compute z = fc_out(h) before tanh.
   Median, P10, P90, |z| > 2 fraction, |z| > 5 fraction.

Caveat from CLM-0160: prior obs is off-manifold. But actor logits
have a different OOD behaviour than critic Q — they're a deterministic
function of obs, not of (obs, h_critic). The h_critic=0 artefact
documented in CLM-0160 / CLM-0165 affects the critic, not the actor's
output head. So this forensics is **more defensible** than R84-W2/W3
critic forensics, even if obs is sampled from a synthetic prior.

Output: results/r93_w0_logit_forensics/{summary.json, logit_histogram.png}.
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
OUT_DIR = ROOT / "results" / "r93_w0_logit_forensics"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_OBS = 200
DEVICE = "cpu"


def actor_pre_tanh(agent, obs: torch.Tensor) -> torch.Tensor:
    """Forward LSTMCell to h, then fc_out(h) WITHOUT tanh squash."""
    h_prev = agent.actor.init_hidden(obs.shape[0], DEVICE)
    h, c = agent.actor.lstm(obs, h_prev)
    z = agent.actor.fc_out(h)            # (B, action_dim)
    return z


def fc_out_stats(agent) -> dict:
    W = agent.actor.fc_out.weight.detach().cpu().numpy()
    b = agent.actor.fc_out.bias.detach().cpu().numpy()
    return {
        "fc_out_weight_max_abs": float(np.max(np.abs(W))),
        "fc_out_weight_l2_norm": float(np.linalg.norm(W)),
        "fc_out_weight_spectral": float(np.linalg.svd(W, compute_uv=False)[0]),
        "fc_out_bias_max_abs": float(np.max(np.abs(b))),
        "fc_out_bias": b.tolist(),
    }


def per_agent(agent_idx: int, agent, rng: np.random.Generator) -> dict:
    obs = torch.from_numpy(
        rng.normal(0, 1.0, size=(N_OBS, agent.obs_dim)).astype(np.float32)
    ).to(DEVICE)
    with torch.no_grad():
        z = actor_pre_tanh(agent, obs)      # (N_OBS, action_dim)
    z_np = z.cpu().numpy()
    abs_z = np.abs(z_np).flatten()
    return {
        "agent_idx": agent_idx,
        **fc_out_stats(agent),
        "logit_median_abs": float(np.median(abs_z)),
        "logit_p10_abs": float(np.percentile(abs_z, 10)),
        "logit_p90_abs": float(np.percentile(abs_z, 90)),
        "logit_max_abs": float(np.max(abs_z)),
        "frac_abs_gt_2": float((abs_z > 2.0).mean()),
        "frac_abs_gt_5": float((abs_z > 5.0).mean()),
        "frac_abs_gt_10": float((abs_z > 10.0).mean()),
        "logits_dim0": z_np[:, 0].tolist(),
        "logits_dim1": z_np[:, 1].tolist(),
    }


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print(f"R93-W0: load SOTA from {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")

    rng = np.random.default_rng(54)
    per = [per_agent(i, ag, rng) for i, ag in enumerate(agents)]

    # Cross-agent aggregate.
    agg = {
        "fc_out_weight_max_abs_median": float(
            np.median([a["fc_out_weight_max_abs"] for a in per])
        ),
        "fc_out_weight_spectral_median": float(
            np.median([a["fc_out_weight_spectral"] for a in per])
        ),
        "logit_median_abs_cross_agent": float(
            np.median([a["logit_median_abs"] for a in per])
        ),
        "frac_abs_gt_2_cross_agent": float(
            np.mean([a["frac_abs_gt_2"] for a in per])
        ),
        "frac_abs_gt_5_cross_agent": float(
            np.mean([a["frac_abs_gt_5"] for a in per])
        ),
    }

    # Verdict: if median |z| > 2, tanh is saturating most outputs.
    saturated_predict = bool(agg["logit_median_abs_cross_agent"] > 2.0)
    very_saturated = bool(agg["frac_abs_gt_5_cross_agent"] > 0.50)

    summary = {
        "round": "R93",
        "wave": "W0_actor_logit_forensics",
        "sota": SOTA_DIR.name,
        "n_obs_samples": N_OBS,
        "per_agent": [{k: v for k, v in a.items() if k not in ("logits_dim0", "logits_dim1")}
                       for a in per],
        "agg": agg,
        "tanh_saturation_predicted": saturated_predict,
        "deep_saturation_predicted": very_saturated,
        "interpretation": (
            "PRE-TANH LOGITS SATURATE THE TANH SQUASH. Actor is "
            "structurally pushed beyond ±1; widening DM_MAX / DD_MAX "
            "would let the policy express the additional authority "
            "the network is already trying to command."
            if saturated_predict else
            "Pre-tanh logits stay below tanh saturation point. "
            "R92-W1 saturation finding is NOT due to actor pushing "
            "beyond bound; must be due to environment dynamics naturally "
            "driving the realised actions to ±1. Widen-bound experiment "
            "may not help."
        ),
        "caveat_obs_distribution": (
            "Obs sampled from N(0, I) prior. Per CLM-0160 caveat, this "
            "is off-manifold; but actor logits are a function of obs "
            "+ h_actor (not h_critic), and h_actor here is also zeros "
            "at episode start. The on-manifold logit distribution may "
            "differ; ANDES-trajectory follow-up (R93-W1 indirectly "
            "tests this by retraining with wider bounds)."
        ),
    }

    out_path = OUT_DIR / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2))

    # Figure: per-agent histograms of pre-tanh logits.
    fig, axes = plt.subplots(2, 4, figsize=(16, 6), sharex=True, sharey=True)
    for ai, agent_pkg in enumerate(per):
        for dim in (0, 1):
            ax = axes[dim][ai]
            data = agent_pkg[f"logits_dim{dim}"]
            ax.hist(data, bins=40, color="C0", alpha=0.7)
            ax.axvline(+2.0, color="orange", ls="--", lw=0.7, label="tanh sat (|z|=2)")
            ax.axvline(-2.0, color="orange", ls="--", lw=0.7)
            ax.axvline(+5.0, color="red",    ls="--", lw=0.7, label="deep sat (|z|=5)")
            ax.axvline(-5.0, color="red",    ls="--", lw=0.7)
            ax.set_title(f"agent {ai} dim {dim}")
            ax.set_xlabel("pre-tanh logit z")
            if ai == 0 and dim == 0:
                ax.legend(fontsize=7)
    fig.suptitle("R93-W0 pre-tanh logit distribution per agent × action dim "
                  "(prior obs ~ N(0, I), h_actor = 0)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "logit_histogram.png", dpi=110)
    plt.close(fig)

    # Digest
    print(f"\n=== R93-W0 actor logit forensics ===")
    print(f"Cross-agent median |logit| = {agg['logit_median_abs_cross_agent']:.3f}")
    print(f"  fraction |z| > 2 (tanh sat) = {agg['frac_abs_gt_2_cross_agent']*100:.1f}%")
    print(f"  fraction |z| > 5 (deep sat) = {agg['frac_abs_gt_5_cross_agent']*100:.1f}%")
    print(f"fc_out_weight median: max_abs = {agg['fc_out_weight_max_abs_median']:.3f}, "
          f"spectral = {agg['fc_out_weight_spectral_median']:.3f}")
    print(f"\nPer-agent breakdown:")
    print(f"  {'ag':>3} {'med|z|':>10} {'p90|z|':>10} {'|z|>2%':>9} "
          f"{'|z|>5%':>9} {'fc_out_max_W':>14}")
    for a in per:
        print(f"  {a['agent_idx']:>3} {a['logit_median_abs']:>10.3f} "
              f"{a['logit_p90_abs']:>10.3f} "
              f"{a['frac_abs_gt_2']*100:>8.1f}% "
              f"{a['frac_abs_gt_5']*100:>8.1f}% "
              f"{a['fc_out_weight_max_abs']:>14.4f}")
    print(f"\nPredicted tanh saturation: {saturated_predict}")
    print(f"Predicted DEEP saturation:  {very_saturated}")
    print(f"\nWritten: {OUT_DIR}/{{summary.json, logit_histogram.png}}")


if __name__ == "__main__":
    main()
