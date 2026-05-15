"""R18 — reward decomposition probe for V4 reward divergence root cause.

Question: 4 V4 trainings (s42/s43/s48 pre-DT-fix, s49 H50) all hit
`reward_divergence` STOP @ ep 75-95 with r_d=96.8% of total reward. Hypothesis:
paper action range expand (DM/DD: V2 [-15,45] → paper [-200,600], 17×) without
PHI_D rescale → r_d = PHI_D × mean(ΔD)² explodes 178× vs paper.

Probe (uses generic ``probes/andes_common`` helpers):
  Phase A: V4 zero-action LS1 — record r_f, r_h, r_d trajectories. Compare ratios.
  Phase B: V4 random-action (SAC-like exploration), action ~ U(DM/DD bounds).
           Measure r_d magnitude at typical exploration actions vs zero action.
  Phase C: Per-component scaling estimate. Paper PHI_D=1 with paper ΔD bounds
           gives some "tolerable" r_d. Our V4 PHI_D=1 with paper bounds gives
           XXX× larger. Predict required PHI_D scale to recover.

Run: /home/wya/andes_venv/bin/python scripts/research_loop/r18_reward_decomp_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from probes.andes_common import (  # noqa: E402
    LS1_DELTA_U,
    LS2_DELTA_U,
    run_zero_action_trace,
)

OUT = ROOT / "results" / "research_loop" / "r18_reward_decomp.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(42)


def phase_a_zero_action(label: str, scenario: dict) -> dict:
    """V4 zero-action — measure r_f, r_h, r_d with no SAC interference.

    With zero action: ΔM=0, ΔD=0 → r_h=0, r_d=0 by Eq.17/18.
    r_f and r_abs (= PHI_F*sync + PHI_ABS*absolute) are nonzero from
    physical freq dynamics. This isolates "physics-driven" reward.
    """
    out = run_zero_action_trace(
        env_cls=AndesMultiVSGEnvV4,
        scenario=scenario,
        n_steps=50,
        record_extras=("freq_hz", "r_f", "r_h", "r_d", "delta_M", "delta_D"),
    )
    traj = out["traj"]
    r_f = np.array(traj["r_f"]).flatten() if traj["r_f"] else np.array([])
    r_h = np.array(traj["r_h"]).flatten() if traj["r_h"] else np.array([])
    r_d = np.array(traj["r_d"]).flatten() if traj["r_d"] else np.array([])
    return {
        "label": label,
        "phase": "A_zero_action",
        "scenario": scenario,
        "n_steps": out["n_steps"],
        "r_f_per_step_mean": float(np.mean(r_f)) if r_f.size else None,
        "r_f_per_step_min": float(np.min(r_f)) if r_f.size else None,
        "r_f_per_step_max": float(np.max(r_f)) if r_f.size else None,
        "r_h_per_step_mean": float(np.mean(r_h)) if r_h.size else None,
        "r_d_per_step_mean": float(np.mean(r_d)) if r_d.size else None,
        "r_total_per_step_mean": float(np.mean(r_f + r_h + r_d)) if r_f.size else None,
    }


def phase_b_random_actions(label: str, scenario: dict, n_eps: int = 1) -> dict:
    """V4 random uniform actions in DM/DD bounds — simulate SAC explore.

    Each step: action = U[a_min, a_max] for both ΔM and ΔD per agent.
    Measure r_h, r_d magnitudes — these explode quadratically with action range.
    """
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(42)
    env.reset(delta_u=scenario)

    DM_RANGE_HALF = (env.DM_MAX - env.DM_MIN) / 2.0  # = 400 paper
    DD_RANGE_HALF = (env.DD_MAX - env.DD_MIN) / 2.0  # = 400 paper

    r_f_traj, r_h_traj, r_d_traj = [], [], []
    delta_M_traj, delta_D_traj = [], []
    n_steps = 0
    tds_failed_step = -1

    for step in range(50):
        # SAC-like: tanh-squashed Gaussian, ~U[-1,1] mean 0 std~0.5
        # Actions in normalized [-1, +1] map to [DM_MIN, DM_MAX]/[DD_MIN, DD_MAX].
        # Use uniform [-1, +1] to simulate full exploration.
        actions = {}
        for i in range(env.N_AGENTS):
            actions[i] = RNG.uniform(-1.0, 1.0, size=2).astype(np.float32)
        try:
            _, _, done, info = env.step(actions)
        except Exception as e:
            tds_failed_step = step
            break
        if info.get("tds_failed"):
            tds_failed_step = step
            break
        r_f_traj.append(float(info["r_f"]))
        r_h_traj.append(float(info["r_h"]))
        r_d_traj.append(float(info["r_d"]))
        delta_M_traj.append([float(x) for x in info["delta_M"]])
        delta_D_traj.append([float(x) for x in info["delta_D"]])
        n_steps += 1
        if done:
            break
    env.close()

    r_f_arr = np.array(r_f_traj) if r_f_traj else np.array([])
    r_h_arr = np.array(r_h_traj) if r_h_traj else np.array([])
    r_d_arr = np.array(r_d_traj) if r_d_traj else np.array([])
    dm_arr = np.array(delta_M_traj) if delta_M_traj else np.zeros((0, 4))
    dd_arr = np.array(delta_D_traj) if delta_D_traj else np.zeros((0, 4))

    return {
        "label": label,
        "phase": "B_random_action",
        "scenario": scenario,
        "n_steps": n_steps,
        "tds_failed_step": tds_failed_step,
        "delta_M_max_abs": float(np.max(np.abs(dm_arr))) if dm_arr.size else None,
        "delta_D_max_abs": float(np.max(np.abs(dd_arr))) if dd_arr.size else None,
        "r_f_per_step_mean": float(np.mean(r_f_arr)) if r_f_arr.size else None,
        "r_h_per_step_mean": float(np.mean(r_h_arr)) if r_h_arr.size else None,
        "r_d_per_step_mean": float(np.mean(r_d_arr)) if r_d_arr.size else None,
        "r_total_per_step_mean": float(
            np.mean(r_f_arr + r_h_arr + r_d_arr)
        ) if r_f_arr.size else None,
    }


def phase_c_scaling_predict(zero_a: dict, rand_b: dict) -> dict:
    """Theoretical scaling prediction for PHI_D rescale to recover paper SNR."""
    # Reference: V2 paper-deviated action range
    V2_DM_RANGE = 52.0   # = 40 - (-12)
    V2_DD_RANGE = 60.0   # = 45 - (-15)
    PAPER_DM_RANGE = 800.0  # = 600 - (-200)
    PAPER_DD_RANGE = 800.0  # = 600 - (-200)

    # r_d = PHI_D × mean(ΔD)² where ΔD ~ U[-DD_range/2, +DD_range/2]
    # E[ΔD²] = (DD_range/2)² / 3
    v2_eq_rd = V2_DD_RANGE ** 2 / 12  # E[ΔD²]
    paper_eq_rd = PAPER_DD_RANGE ** 2 / 12
    rd_scale_explode = paper_eq_rd / v2_eq_rd  # (800/60)² = 178

    # r_f baseline (zero-action)
    r_f_baseline = zero_a.get("r_f_per_step_mean")  # ~ negative, abs is signal
    # r_d at random action (Phase B)
    r_d_explore = rand_b.get("r_d_per_step_mean")

    snr_now = (
        abs(r_d_explore / r_f_baseline)
        if (r_d_explore is not None and r_f_baseline)
        else None
    )

    return {
        "phase": "C_scaling_predict",
        "v2_dd_range": V2_DD_RANGE,
        "paper_dd_range": PAPER_DD_RANGE,
        "rd_scale_explode_factor": float(rd_scale_explode),
        "r_f_zero_action_baseline": r_f_baseline,
        "r_d_random_explore_per_step": r_d_explore,
        "abs_ratio_rd_over_rf": snr_now,
        "predicted_phi_d_paper_faithful": float(1.0 / rd_scale_explode),
        "predicted_phi_d_min_safe": 0.005,
        "verdict": (
            f"Paper PHI_D=1 needs ≈ 1/{rd_scale_explode:.0f} = "
            f"{1.0 / rd_scale_explode:.4f} when DD range expands V2→paper "
            f"({V2_DD_RANGE}→{PAPER_DD_RANGE})"
        ),
    }


def main() -> int:
    out: dict[str, Any] = {
        "probe": "r18_reward_decomp",
        "version": 1,
        "env": "AndesMultiVSGEnvV4 (paper-faithful baseline)",
    }
    print("=== R18 Reward decomposition probe (V4) ===\n")

    # Phase A: zero-action (no SAC interference)
    print("Phase A: V4 zero-action LS1 — physics-only reward...")
    out["A_zero_LS1"] = phase_a_zero_action("V4_zero_LS1", LS1_DELTA_U)
    print(f"  r_f/step (zero-action) = {out['A_zero_LS1'].get('r_f_per_step_mean'):.3e}")
    print(f"  r_h/step (zero-action) = {out['A_zero_LS1'].get('r_h_per_step_mean'):.3e} (expect 0)")
    print(f"  r_d/step (zero-action) = {out['A_zero_LS1'].get('r_d_per_step_mean'):.3e} (expect 0)")

    # Phase B: random action (simulate SAC explore)
    print("\nPhase B: V4 random uniform action ([-1,1] → DM/DD bounds)...")
    out["B_rand_LS1"] = phase_b_random_actions("V4_rand_LS1", LS1_DELTA_U)
    print(f"  ΔM_max_abs   = {out['B_rand_LS1'].get('delta_M_max_abs'):.1f} (DM range half = 400)")
    print(f"  ΔD_max_abs   = {out['B_rand_LS1'].get('delta_D_max_abs'):.1f} (DD range half = 400)")
    print(f"  r_f/step     = {out['B_rand_LS1'].get('r_f_per_step_mean'):.3e}")
    print(f"  r_h/step     = {out['B_rand_LS1'].get('r_h_per_step_mean'):.3e}")
    print(f"  r_d/step     = {out['B_rand_LS1'].get('r_d_per_step_mean'):.3e}")
    print(f"  TDS fail @ step {out['B_rand_LS1'].get('tds_failed_step')}")

    # Phase C: scaling prediction
    print("\nPhase C: theoretical PHI_D rescale prediction...")
    out["C_predict"] = phase_c_scaling_predict(out["A_zero_LS1"], out["B_rand_LS1"])
    print(f"  Verdict: {out['C_predict']['verdict']}")
    print(f"  Predicted PHI_D paper-faithful = {out['C_predict']['predicted_phi_d_paper_faithful']:.4f}")

    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
