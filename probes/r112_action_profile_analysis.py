"""Offline analysis of R112 traces: per-step ||a|| profile baseline vs warm_h0.

R112 found geo crashes -96% but cum_rf improves +54% under warm-h_0. This
script extracts per-step action norm trajectories to identify which steps
contribute most to the geo damage.

Hypothesis: warm-h_0 saturates step 0 (||a||→1.41 from R112 grad-ascent
diag), then either (a) policy recovers to normal at step 1-2, OR
(b) saturation propagates through LSTM h, persisting many steps.

If (a): geo drop is driven by step-0 dD/dM smoothness penalty (a single
jolt is enough to punish smoothness axes substantially).
If (b): the warmed LSTM state breaks the entire trajectory.
"""
import json
import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "results" / "r112_warmh0_env_eval" / "traces"

def load_trace(path):
    with path.open() as f:
        return json.load(f)

def per_step_action_norms(trace_record):
    """Compute ||action|| per step. action = (ΔM, ΔD) per agent, 4 agents."""
    # traces[t] has delta_M (list of 4 values) and delta_D (list of 4 values)
    # ||a_i|| = sqrt(delta_M_i^2 + delta_D_i^2) where both are normalised to
    # the action box. We approximate using delta_M/DM_MAX and delta_D/DD_MAX.
    DM_MAX = 600.0
    DD_MAX = 600.0
    per_step_norms = []
    for step in trace_record["traces"]:
        dm = np.array(step["delta_M"]) / DM_MAX
        dd = np.array(step["delta_D"]) / DD_MAX
        # ||a_i|| per agent
        agent_norms = np.sqrt(dm**2 + dd**2)
        per_step_norms.append(agent_norms)
    return np.array(per_step_norms)  # (T, 4)

def per_step_smoothness(trace_record):
    """Per-step |a_t - a_{t-1}| smoothness violation."""
    DM_MAX = 600.0
    DD_MAX = 600.0
    dms = np.array([s["delta_M"] for s in trace_record["traces"]]) / DM_MAX
    dds = np.array([s["delta_D"] for s in trace_record["traces"]]) / DD_MAX
    a = np.stack([dms, dds], axis=-1)  # (T, 4, 2)
    if a.shape[0] < 2:
        return np.zeros((0, 4))
    diffs = np.linalg.norm(a[1:] - a[:-1], axis=-1)
    return diffs  # (T-1, 4)

def freq_deviation_profile(trace_record):
    """Per-step max|delta_f| across 4 agents."""
    df = np.array([np.abs(s["delta_f_es"]) for s in trace_record["traces"]])
    return df  # (T, 4)


def main():
    for scen in ["load_step_1", "load_step_2"]:
        print(f"\n=== {scen} ===")
        baseline = load_trace(TRACE_DIR / f"baseline_{scen}.json")
        warm = load_trace(TRACE_DIR / f"warmh0_{scen}.json")

        nb = per_step_action_norms(baseline)  # (T, 4)
        nw = per_step_action_norms(warm)

        sb = per_step_smoothness(baseline)
        sw = per_step_smoothness(warm)

        fb = freq_deviation_profile(baseline)
        fw = freq_deviation_profile(warm)

        T = min(nb.shape[0], nw.shape[0])

        print(f"  baseline n_steps={nb.shape[0]}, warm n_steps={nw.shape[0]}")
        print(f"  T_common={T}")

        # Per-step ||a|| mean across 4 agents
        nb_mean = nb.mean(axis=1)
        nw_mean = nw.mean(axis=1)
        print(f"\n  Step-by-step ||a|| mean (baseline / warm):")
        print(f"    step 0  : {nb_mean[0]:.4f} / {nw_mean[0]:.4f}  (warm Δ={nw_mean[0]-nb_mean[0]:+.4f})")
        for k in [1, 2, 5, 10, 25, 50, 100, T-1]:
            if k < T:
                print(f"    step {k:<3}: {nb_mean[k]:.4f} / {nw_mean[k]:.4f}  (warm Δ={nw_mean[k]-nb_mean[k]:+.4f})")

        # Smoothness violation per step (mean across 4 agents)
        sb_mean = sb.mean(axis=1)
        sw_mean = sw.mean(axis=1)
        print(f"\n  Smoothness |a_t - a_{{t-1}}| mean across agents:")
        for k in [0, 1, 2, 4, 9, 24, 49, sb.shape[0]-1]:
            if k < sb.shape[0]:
                print(f"    step {k:<3} (jump from prev): baseline {sb_mean[k]:.4f}, warm {sw_mean[k]:.4f}  (warm Δ={sw_mean[k]-sb_mean[k]:+.4f})")
        print(f"  Total smoothness cost baseline: {sb_mean.sum():.4f}")
        print(f"  Total smoothness cost warm   : {sw_mean.sum():.4f}  (Δ={sw_mean.sum()-sb_mean.sum():+.4f})")

        # Freq deviation profile (max across 4 agents per step)
        fb_max = fb.max(axis=1)
        fw_max = fw.max(axis=1)
        print(f"\n  max |Δf| Hz per step:")
        print(f"    step 0  : {fb_max[0]:.5f} / {fw_max[0]:.5f}  (warm Δ={fw_max[0]-fb_max[0]:+.5f})")
        for k in [1, 5, 10, 25, 50, 100, T-1]:
            if k < T:
                print(f"    step {k:<3}: {fb_max[k]:.5f} / {fw_max[k]:.5f}  (warm Δ={fw_max[k]-fb_max[k]:+.5f})")
        print(f"  peak max |Δf|   baseline: {fb_max.max():.5f}")
        print(f"  peak max |Δf|   warm    : {fw_max.max():.5f}")

        # Action saturation (||a|| close to max)
        sat_b = (nb >= 0.9).mean(axis=1)  # frac of agents at >=90% norm per step
        sat_w = (nw >= 0.9).mean(axis=1)
        print(f"\n  Fraction of agents at ||a||≥0.9 (saturation):")
        print(f"    step 0: baseline {sat_b[0]:.2f}, warm {sat_w[0]:.2f}")
        print(f"    step 1: baseline {sat_b[1]:.2f}, warm {sat_w[1]:.2f}")
        print(f"    mean over all steps: baseline {sat_b.mean():.3f}, warm {sat_w.mean():.3f}")


if __name__ == "__main__":
    main()
