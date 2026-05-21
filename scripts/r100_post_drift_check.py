"""R100 post-training drift check — does the regularised actor still drift?

Re-runs R93-W0b LSTM-drift forensics on the R100-W1 hreg ckpt to verify
that adding λ_h * mean(||h_actor||²) to the actor loss actually suppressed
the LSTM-internal drift CLM-0181 documented on R72_w4 SOTA.

Comparison vs R72_w4 baseline:
- ||h(t)|| trajectory under obs=0 stream
- max pre-tanh logit |z| over 50 steps
- saturation count

If R100-W1 ckpt's ||h(50)|| << 5.0 and |z|_max << 2.0, the regularisation
worked; if ckpt yields similar drift, regularisation didn't bite.

Usage: python scripts/r100_post_drift_check.py [<ckpt_dir>]
       default ckpt_dir = results/r100_w1_hreg_lambda0p01_s54
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


def drift_one(agent, obs_stream: torch.Tensor) -> dict:
    h_prev = agent.actor.init_hidden(1, "cpu")
    h_norms: list[float] = []
    z_max_seq: list[float] = []
    a_seq: list[np.ndarray] = []
    for t in range(obs_stream.shape[0]):
        obs_t = obs_stream[t:t+1]
        with torch.no_grad():
            h_new, c_new = agent.actor.lstm(obs_t, h_prev)
            z = agent.actor.fc_out(h_new)
            a = torch.tanh(z)
        h_norms.append(float(h_new.norm()))
        z_max_seq.append(float(z.abs().max().item()))
        a_seq.append(a[0].cpu().numpy())
        h_prev = (h_new, c_new)
    a_arr = np.array(a_seq)
    return {
        "h_norm_first": h_norms[0],
        "h_norm_last": h_norms[-1],
        "h_norm_max": float(np.max(h_norms)),
        "logit_max_abs_over_traj": float(np.max(z_max_seq)),
        "action_max_abs": float(np.max(np.abs(a_arr))),
        "saturation_steps_over_100": int((np.abs(a_arr) > 0.95).sum()),
    }


def main() -> None:
    ckpt_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (
        ROOT / "results" / "r100_w1_hreg_lambda0p01_s54"
    )
    if not ckpt_dir.exists():
        sys.exit(f"FATAL: ckpt dir missing: {ckpt_dir}")

    print(f"R100 post-drift check on {ckpt_dir.name}")
    agents = load_agents(ckpt_dir, suffix="best" if (ckpt_dir / "agent_0_best.pt").exists() else "final")

    obs_dim = agents[0].obs_dim
    obs_zero = torch.zeros(50, obs_dim)
    obs_e1 = torch.tensor(np.array(
        [[1.0] + [0.0] * (obs_dim - 1)] * 50, dtype=np.float32
    ))
    rng = np.random.default_rng(54)
    obs_random = torch.from_numpy(rng.normal(0, 0.5, size=(50, obs_dim)).astype(np.float32))

    results = []
    for ai, agent in enumerate(agents):
        per = {
            "agent_idx": ai,
            "zero": drift_one(agent, obs_zero),
            "constant_e1": drift_one(agent, obs_e1),
            "random": drift_one(agent, obs_random),
        }
        results.append(per)

    # vs R72_w4 baseline (from CLM-0181, hardcoded):
    baseline = {
        "h_norm_last_median_zero_obs": 5.32,
        "logit_max_abs_median_zero_obs": 2.59,
        "saturation_steps_over_100_median": 66.25,
    }
    new = {
        "h_norm_last_median_zero_obs": float(np.median([r["zero"]["h_norm_last"] for r in results])),
        "logit_max_abs_median_zero_obs": float(np.median([r["zero"]["logit_max_abs_over_traj"] for r in results])),
        "saturation_steps_over_100_median": float(np.median([r["zero"]["saturation_steps_over_100"] for r in results])),
    }
    reduction = {
        "h_norm_last": (baseline["h_norm_last_median_zero_obs"] - new["h_norm_last_median_zero_obs"])
                       / baseline["h_norm_last_median_zero_obs"],
        "logit_max_abs": (baseline["logit_max_abs_median_zero_obs"] - new["logit_max_abs_median_zero_obs"])
                          / baseline["logit_max_abs_median_zero_obs"],
        "saturation_steps": (baseline["saturation_steps_over_100_median"] - new["saturation_steps_over_100_median"])
                              / max(baseline["saturation_steps_over_100_median"], 1e-6),
    }

    out_dir = ROOT / "results" / f"{ckpt_dir.name}_drift_check"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(
        {
            "ckpt": ckpt_dir.name,
            "per_agent": results,
            "baseline_r72_w4": baseline,
            "new_ckpt_aggregate": new,
            "reduction_vs_baseline": reduction,
        },
        indent=2,
    ))

    print(f"\n=== Drift comparison: R100 ckpt vs R72_w4 baseline ===")
    print(f"  metric                    | R72_w4 baseline | R100 ckpt | reduction")
    print(f"  --------------------------|-----------------|-----------|----------")
    print(f"  ||h(50)|| (obs=0, median) |     {baseline['h_norm_last_median_zero_obs']:>5.2f}       |  "
          f"{new['h_norm_last_median_zero_obs']:>5.2f}    |   {reduction['h_norm_last']*100:>+5.1f}%")
    print(f"  max |z| (obs=0, median)   |     {baseline['logit_max_abs_median_zero_obs']:>5.2f}       |  "
          f"{new['logit_max_abs_median_zero_obs']:>5.2f}    |   {reduction['logit_max_abs']*100:>+5.1f}%")
    print(f"  sat steps/100 (zero, med) |     {baseline['saturation_steps_over_100_median']:>5.1f}       |  "
          f"{new['saturation_steps_over_100_median']:>5.1f}    |   {reduction['saturation_steps']*100:>+5.1f}%")
    print(f"\nWritten: {out_dir}/summary.json")


if __name__ == "__main__":
    main()
