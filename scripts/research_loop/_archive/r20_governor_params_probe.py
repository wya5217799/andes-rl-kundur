"""R20 — IEEEG1 governor params sensitivity (V4 V4 baseline).

Hypothesis: ANDES IEEEG1 default params (K=20, T1-T7 = generic governor) may be
slower than paper Kundur Fig.6 governor. Tuning K higher / T1 lower → faster
primary control → smaller max_df nadir.

Method (post DT-fix paper-faithful 6s window):
  variant A: V4 default (K=20, T1=1.0, T2=1.0, T3=0.1, T4=0.4)
  variant B: V4 fast governor (K=50, T1=0.3)
  variant C: V4 paper-Kundur-like (K=20, T1=2.0, T2=2.0)  — slower bag
  variant D: V4 high-gain (K=100, T1=0.1) — stress test

LS1 only (LS2 redundant for this audit).

Verdict:
  best variant max_df < 0.15 (1.15× paper) → governor tuning closes Root #3
  best 0.15-0.18                            → partial improvement
  best ≥ 0.18                                → governor params not the dominant cause
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
    PAPER_FIG6,
    DEFAULT_PROBE_STEPS_SHORT,
)
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402


def make_v4_with_gov_params(K: float, T1: float, T2: float = 1.0,
                              T3: float = 0.1, T4: float = 0.4):
    """Subclass V4 with custom IEEEG1 params."""

    class V4_GovTuned(AndesMultiVSGEnvV4):
        def _build_system(self):
            ss = super()._build_system()
            # Tune IEEEG1 params on every governor instance
            for i in range(ss.IEEEG1.n):
                ss.IEEEG1.K.v[i] = K
                ss.IEEEG1.T1.v[i] = T1
                ss.IEEEG1.T2.v[i] = T2
                ss.IEEEG1.T3.v[i] = T3
                ss.IEEEG1.T4.v[i] = T4
            return ss

    return V4_GovTuned


def run_one(env, label: str) -> dict:
    out: dict[str, Any] = {"label": label}
    try:
        env.seed(42)
        env.reset(delta_u=LS1_DELTA_U)
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
        if df_traj:
            out["max_df"] = float(np.max(df_traj))
            out["final_df"] = float(df_traj[-1])
            out["paper_ratio"] = out["max_df"] / PAPER_FIG6.max_abs_df_Hz
            out["nadir_step"] = int(np.argmax(df_traj))
            out["nadir_t_s"] = out["nadir_step"] * 0.2
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
    return out


def main() -> int:
    out: dict[str, Any] = {"probe": "r20_governor_params", "version": 1}
    print("=== R20 IEEEG1 governor params sensitivity (V4 LS1) ===\n")

    variants = [
        ("A_default", {"K": 20.0, "T1": 1.0}),
        ("B_fast", {"K": 50.0, "T1": 0.3}),
        ("C_slow", {"K": 20.0, "T1": 2.0, "T2": 2.0}),
        ("D_high_gain", {"K": 100.0, "T1": 0.1}),
    ]

    out["variants"] = {}
    best_max_df = float("inf")
    best_label = None
    for label, params in variants:
        env_cls = make_v4_with_gov_params(**params)
        env = env_cls(random_disturbance=False, comm_fail_prob=0.0)
        r = run_one(env, label)
        r["params"] = params
        out["variants"][label] = r
        max_df = r.get("max_df", "ERR")
        ratio = r.get("paper_ratio", "ERR")
        print(f"  {label:14s} K={params.get('K'):>5} T1={params.get('T1')}: max_df={max_df}, ratio={ratio}")
        if isinstance(max_df, float) and max_df < best_max_df:
            best_max_df = max_df
            best_label = label

    if best_label:
        best_ratio = best_max_df / PAPER_FIG6.max_abs_df_Hz
        if best_ratio < 1.15:
            verdict = f"GOV_FIX — best={best_label} max_df={best_max_df:.3f} ({best_ratio:.2f}× paper)"
        elif best_ratio < 1.4:
            verdict = f"GOV_PARTIAL — best={best_label} max_df={best_max_df:.3f} ({best_ratio:.2f}× paper)"
        else:
            verdict = f"GOV_NOT_CAUSE — best={best_label} max_df={best_max_df:.3f} ({best_ratio:.2f}× paper)"
        out["verdict"] = verdict
        out["best_label"] = best_label
        out["best_max_df"] = best_max_df
        print(f"\n=== {verdict} ===")
    else:
        out["verdict"] = "INCONCLUSIVE — all variants failed"

    p = ROOT / "results" / "research_loop" / "r20_governor_params.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
