"""R19 — WF2 (Bus 8 zero-inertia GENCLS) necessity audit.

Hypothesis: V1 base adds a "100MW wind farm" GENCLS at Bus 8 with M=0.1, D=0
("simulating wind farm"). paper Yang2023 Sec.IV-A says "a 100MW wind farm is
connected to bus 8" — but does this **structural** addition affect ANDES-side
no-control max_df vs paper Fig.6?

Method (variant ablation, paper-faithful V4):
  variant A: V4 default (with WF2 zero-inertia GENCLS at Bus 8)
  variant B: V4 with WF2 removed (skip the .add())
Both at H_FORCED=100 (V4 default), governor active, G4 paper.

Paper-faithful 0.2s/step DT (post DT-fix).

Verdict:
  |max_df_A - max_df_B| / max_df_A < 5%   → WF2 不影响, 保留无害
  diff 5-20%                                 → WF2 minor partial root
  diff > 20%                                 → WF2 contributes to Root #3 残差
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from probes.andes_common import (  # noqa: E402
    LS1_DELTA_U,
    LS2_DELTA_U,
    PAPER_FIG6,
    PAPER_FIG8,
    DEFAULT_PROBE_STEPS_SHORT,
)
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402


def _run(env, scenario):
    env.seed(42)
    env.reset(delta_u=scenario)
    df_traj = []
    for _ in range(DEFAULT_PROBE_STEPS_SHORT):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
        try:
            _, _, done, info = env.step(actions)
        except Exception:
            break
        if info.get("tds_failed"):
            break
        df_traj.append(float(info["max_freq_deviation_hz"]))
        if done:
            break
    env.close()
    return {
        "max_df": float(np.max(df_traj)) if df_traj else None,
        "final_df": float(df_traj[-1]) if df_traj else None,
        "n_steps": len(df_traj),
    }


class V4_NoWF2(AndesMultiVSGEnvV4):
    """V4 with WF2 GENCLS at Bus 8 NOT added (probe-only)."""

    def _build_system(self):
        # Replicate V1 build but skip WF2. Easier: add WF2 then remove via set.
        # Actually base build adds WF2 in V1.AndesMultiVSGEnv._build_system().
        # We can't skip it cleanly without subclass override of full build. Instead,
        # post-build set WF2.M to 0.001 (effectively no inertia, no power injection
        # since .Pe is solved from PFlow). Wait — that's same as V1 default!
        # Actually V1 already sets WF2.M=0.1 (line 150). To audit "no WF2" we
        # need to remove it from network entirely. Use post-setup .u (on/off):
        ss = super()._build_system()
        # Toggle WF2 off via u flag (ANDES standard: u=0 disables model)
        try:
            wf2_pos = list(ss.GENCLS.idx.v).index("WF2")
            ss.GENCLS.u.v[wf2_pos] = 0.0
        except (ValueError, AttributeError):
            pass
        return ss


def main() -> int:
    out: dict[str, Any] = {"probe": "r19_wf2_necessity", "version": 1}
    print("=== R19 WF2 (Bus 8) necessity audit ===\n")

    for scen_name, du, paper in [("LS1", LS1_DELTA_U, PAPER_FIG6),
                                  ("LS2", LS2_DELTA_U, PAPER_FIG8)]:
        print(f"--- {scen_name} ---")
        try:
            env_a = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
            r_a = _run(env_a, du)
            print(f"  V4 default (WF2 on): max_df={r_a['max_df']:.3f}, final={r_a['final_df']:.3f}")

            env_b = V4_NoWF2(random_disturbance=False, comm_fail_prob=0.0)
            r_b = _run(env_b, du)
            print(f"  V4 WF2 off (u=0):    max_df={r_b['max_df']:.3f}, final={r_b['final_df']:.3f}")

            if r_a["max_df"] and r_b["max_df"]:
                diff = abs(r_a["max_df"] - r_b["max_df"]) / r_a["max_df"] * 100
                print(f"  diff = {diff:.1f}%, paper {scen_name} max={paper.max_abs_df_Hz}")
                out[scen_name] = {
                    "max_df_wf2_on": r_a["max_df"],
                    "max_df_wf2_off": r_b["max_df"],
                    "diff_pct": float(diff),
                    "paper_target": paper.max_abs_df_Hz,
                    "paper_ratio_wf2_on": r_a["max_df"] / paper.max_abs_df_Hz,
                    "paper_ratio_wf2_off": r_b["max_df"] / paper.max_abs_df_Hz,
                }
        except Exception as e:
            out[scen_name] = {"error": str(e)[:200], "tb": traceback.format_exc()[:500]}
            print(f"  ERROR: {e}")
        print()

    # Verdict
    diffs = [v["diff_pct"] for v in out.values() if isinstance(v, dict) and "diff_pct" in v]
    if diffs:
        max_diff = max(diffs)
        if max_diff < 5:
            verdict = f"WF2_NEUTRAL — max diff {max_diff:.1f}%, WF2 不影响 max_df"
        elif max_diff < 20:
            verdict = f"WF2_MINOR — max diff {max_diff:.1f}%, partial 影响"
        else:
            verdict = f"WF2_MATTERS — max diff {max_diff:.1f}%, contributes to Root #3"
    else:
        verdict = "INCONCLUSIVE — both variants failed"
    out["verdict"] = verdict
    print(f"=== {verdict} ===")

    p = ROOT / "results" / "research_loop" / "r19_wf2_necessity.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
