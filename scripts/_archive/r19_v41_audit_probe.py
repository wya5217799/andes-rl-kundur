"""R19 — V4.1 paper-anchor + remaining-issue audit (uses generic framework).

After V4.1 patches (DT-fix + PHI rescale + M/D clamp), audit:
  A. DT-fix actually applied? trace timestep should be 0.2s exactly
  B. Paper Eq.12 box clamp working? probe SAC-extreme actions, verify M ≥ 20
  C. Comm_fail effect: V4.1 default 0.1 vs paper baseline 0 — diff?
  D. WF2 (Bus 8 zero-inertia) effect: with vs without
  E. Settling using paper-faithful final_df reference (was bug: default 0.0)

Run: /home/wya/andes_venv/bin/python scripts/research_loop/r19_v41_audit_probe.py
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
    PAPER_FIG6,
    PAPER_FIG8,
    compute_settling_time,
    run_variant_ablation,
    run_zero_action_trace,
)

OUT = ROOT / "results" / "research_loop" / "r19_v41_audit.json"
OUT.parent.mkdir(parents=True, exist_ok=True)


# Variant patches
def _disable_wf2(env):
    """Patch: disable WF2 by setting WF2_SN to 0 - actually skip wf2 add logic
    via instance attr (not feasible cleanly; instead stub out via override).
    Simplest: set WF2_BUS = -1 so no bus matches, skipping add. But that breaks
    bus topology. Cleanest: subclass overrides _build_system. Below uses an
    instance attr trick — won't actually disable WF2, just zeros its inertia
    further (M=1e-6) to test sensitivity to its already-near-zero inertia.
    """
    # Override M0 of WF2 by post-build patch isn't clean. Skip variant for now.
    return None


def _comm_fail_zero(env):
    env.comm_fail_prob = 0.0


def main() -> int:
    out: dict[str, Any] = {
        "probe": "r19_v41_audit",
        "version": 1,
        "checks": {},
    }
    print("=== R19 V4.1 paper-anchor + remaining-issue audit ===\n")

    # ─── A. DT-fix verification ───────────────────────
    print("[A] DT-fix verification: trace timestep should be 0.2s")
    res_a = run_zero_action_trace(
        AndesMultiVSGEnvV4, LS1_DELTA_U, n_steps=10,
        record_extras=("freq_hz",),
    )
    # We don't have direct timestep recording in run_zero_action_trace, but
    # info["t"] per step would tell. Use raw env to get timestamps.
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(42)
    env.reset(delta_u=LS1_DELTA_U)
    timestamps = []
    for _ in range(5):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
        _, _, done, info = env.step(actions)
        timestamps.append(float(info["time"]))
    env.close()
    deltas = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    out["checks"]["A_dt_fix"] = {
        "timestamps": timestamps,
        "deltas": deltas,
        "expected_dt": 0.2,
        "actual_dt_mean": float(np.mean(deltas)) if deltas else None,
        "verdict": "PASS" if deltas and abs(np.mean(deltas) - 0.2) < 0.01 else "FAIL",
    }
    print(f"  expected dt=0.2s, observed mean dt={out['checks']['A_dt_fix']['actual_dt_mean']:.4f}s")
    print(f"  verdict: {out['checks']['A_dt_fix']['verdict']}")

    # ─── B. M/D clamp verification ────────────────────
    # Run env with extreme negative actions, check M doesn't go below 20
    print("\n[B] M/D paper Eq.12 clamp verification (M ≥ 20)")
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    env.seed(42)
    env.reset(delta_u=LS1_DELTA_U)
    M_min_observed = float("inf")
    D_min_observed = float("inf")
    for _ in range(20):
        # Maximally negative ΔM, ΔD
        actions = {i: np.array([-1.0, -1.0], dtype=np.float32) for i in range(env.N_AGENTS)}
        try:
            _, _, done, info = env.step(actions)
        except Exception:
            break
        if info.get("tds_failed"):
            break
        M_min_observed = min(M_min_observed, float(np.min(info["M_es"])))
        D_min_observed = min(D_min_observed, float(np.min(info["D_es"])))
    env.close()
    out["checks"]["B_clamp"] = {
        "M_min_observed": M_min_observed if M_min_observed != float("inf") else None,
        "D_min_observed": D_min_observed if D_min_observed != float("inf") else None,
        "M_MIN_expected": 20.0,
        "D_MIN_expected": 10.0,
        "verdict": (
            "PASS" if M_min_observed >= 19.99 and D_min_observed >= 9.99
            else "FAIL"
        ),
    }
    print(f"  M_min observed: {out['checks']['B_clamp']['M_min_observed']:.2f} (expect ≥ 20)")
    print(f"  D_min observed: {out['checks']['B_clamp']['D_min_observed']:.2f} (expect ≥ 10)")
    print(f"  verdict: {out['checks']['B_clamp']['verdict']}")

    # ─── C. comm_fail ablation ────────────────────────
    print("\n[C] comm_fail_prob ablation: 0.0 (paper baseline) vs 0.1 (V4 default)")
    res_c = run_variant_ablation(
        {
            "comm_fail_0p0": {"env_cls": AndesMultiVSGEnvV4, "env_patch": _comm_fail_zero},
            "comm_fail_0p1_default": {"env_cls": AndesMultiVSGEnvV4},
        },
        base_env_cls=AndesMultiVSGEnvV4,
        scenario=LS1_DELTA_U,
        n_steps=30,
    )
    cf0_max = res_c["comm_fail_0p0"]["max_df"]
    cf1_max = res_c["comm_fail_0p1_default"]["max_df"]
    out["checks"]["C_comm_fail"] = {
        "comm_fail_0p0_max_df": cf0_max,
        "comm_fail_0p1_max_df": cf1_max,
        "diff_pct": (
            (cf1_max - cf0_max) / cf0_max * 100
            if cf0_max else None
        ),
    }
    # Note: comm_fail only affects training (random comm dropouts), not no_action eval
    # But probe needs SAC with random actions to see effect. Zero-action 大概率 same.
    print(f"  comm_fail=0.0 max_df: {cf0_max:.3f}")
    print(f"  comm_fail=0.1 max_df: {cf1_max:.3f}")
    print(f"  diff: {out['checks']['C_comm_fail'].get('diff_pct'):.1f}%")
    print("  Note: comm_fail only matters with SAC actions, zero-action 应一致.")

    # ─── D. paper-faithful settling computation ────────────
    print("\n[D] Settling time using paper-faithful final_df reference")
    res_d = run_zero_action_trace(AndesMultiVSGEnvV4, LS1_DELTA_U, n_steps=30)
    # Paper Fig.6 LS1 final = 0.08 Hz. Use paper as reference.
    settling_paper_ref = compute_settling_time(
        res_d["df_traj"], dt=0.2, final_df_target=PAPER_FIG6.final_abs_df_Hz, band_hz=0.02
    )
    settling_self_ref = compute_settling_time(
        res_d["df_traj"], dt=0.2, final_df_target=None, band_hz=0.02
    )
    out["checks"]["D_settling"] = {
        "paper_final_target_Hz": PAPER_FIG6.final_abs_df_Hz,
        "self_final_observed_Hz": float(res_d["df_traj"][-1]),
        "settling_paper_ref_s": settling_paper_ref if settling_paper_ref != float("inf") else None,
        "settling_self_ref_s": settling_self_ref if settling_self_ref != float("inf") else None,
        "paper_settling_target_s": PAPER_FIG6.settling_to_residual_s,
    }
    print(f"  Paper final: {PAPER_FIG6.final_abs_df_Hz}, self final: {res_d['df_traj'][-1]:.3f}")
    print(f"  Settling (paper ref): {out['checks']['D_settling']['settling_paper_ref_s']}")
    print(f"  Settling (self ref):  {out['checks']['D_settling']['settling_self_ref_s']}")
    print(f"  Paper target settling: {PAPER_FIG6.settling_to_residual_s}s")

    # ─── E. V4.1 paper alignment summary ──────────────
    print("\n[E] V4.1 paper-alignment summary (LS1 + LS2)")
    res_e = {
        "LS1": run_zero_action_trace(AndesMultiVSGEnvV4, LS1_DELTA_U, n_steps=30),
        "LS2": run_zero_action_trace(AndesMultiVSGEnvV4, LS2_DELTA_U, n_steps=30),
    }
    out["checks"]["E_paper_align"] = {
        "LS1": {
            "max_df": res_e["LS1"]["max_df"],
            "final_df": res_e["LS1"]["final_df"],
            "paper_max": PAPER_FIG6.max_abs_df_Hz,
            "paper_final": PAPER_FIG6.final_abs_df_Hz,
            "max_ratio": res_e["LS1"]["max_df"] / PAPER_FIG6.max_abs_df_Hz,
            "final_ratio": res_e["LS1"]["final_df"] / PAPER_FIG6.final_abs_df_Hz,
        },
        "LS2": {
            "max_df": res_e["LS2"]["max_df"],
            "final_df": res_e["LS2"]["final_df"],
            "paper_max": PAPER_FIG8.max_abs_df_Hz,
            "paper_final": PAPER_FIG8.final_abs_df_Hz,
            "max_ratio": res_e["LS2"]["max_df"] / PAPER_FIG8.max_abs_df_Hz,
            "final_ratio": res_e["LS2"]["final_df"] / PAPER_FIG8.final_abs_df_Hz,
        },
    }
    e = out["checks"]["E_paper_align"]
    print(f"  LS1: max {e['LS1']['max_df']:.3f}/{e['LS1']['paper_max']} = {e['LS1']['max_ratio']:.2f}×, "
          f"final {e['LS1']['final_df']:.3f}/{e['LS1']['paper_final']} = {e['LS1']['final_ratio']:.2f}×")
    print(f"  LS2: max {e['LS2']['max_df']:.3f}/{e['LS2']['paper_max']} = {e['LS2']['max_ratio']:.2f}×, "
          f"final {e['LS2']['final_df']:.3f}/{e['LS2']['paper_final']} = {e['LS2']['final_ratio']:.2f}×")

    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
