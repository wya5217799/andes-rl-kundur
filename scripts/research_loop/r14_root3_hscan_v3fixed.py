"""R14 — Root #3 forensic H scan on V3 (governor FIXED 2026-05-07).

Question: 修了 R10 Root #2 后, V3 IEEEG1+EXST1 在 DAE 里 active. 那 R08 finding
(H=300 paper Eq.12 上限 max_df 仍 2× paper) 是否仍存在?

Logic:
  R08 实测: V3-with-broken-governor at H={10,30,100,300} → max_df {0.815, 0.539, 0.328, 0.266}, paper 0.13
            H 越大 max_df 越小但永远 ≥ 2× paper.
  现在 V3 governor 实际 active, 重做相同扫描. 如果:
    H=6.5  max_df ≈ 0.13          → governor + 标准 H 完美对齐 paper, R08 Root #3 是 fake (是 Root #2 propagation)
    H=300  max_df ≤ 0.20           → Root #3 mostly resolved by governor fix
    H=300  max_df > 0.25 仍 2×paper → Root #3 真实存在, 需 ANDES system audit

H values: 6.5 (paper Kundur Area1), 6.175 (Area2), 30, 100, 300 (Eq.12 上限)
LS1: PQ_Bus14 -2.48 sys_pu zero-action 30 step (6s, 仅看 max_df 量级)

Run: /home/wya/andes_venv/bin/python scripts/research_loop/r14_root3_hscan_v3fixed.py
Output: results/research_loop/r14_root3_hscan.json
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

from env.andes.andes_vsg_env_v2 import AndesMultiVSGEnvV2  # noqa: E402
from env.andes.andes_vsg_env_v3 import AndesMultiVSGEnvV3  # noqa: E402

LS1 = {"PQ_Bus14": -2.48}
PROBE_STEPS = 30  # 6s, max_df 通常 < 3s 内出现, 6s 已够 nadir
H_GRID = [6.175, 6.5, 30.0, 100.0, 300.0]
PAPER_NO_CTRL_MAX_DF = 0.13


def run_h(env_cls, h_val: float, label: str) -> dict:
    out: dict[str, Any] = {"label": label, "h": h_val}
    try:
        env = env_cls(random_disturbance=False, comm_fail_prob=0.0)
        env.seed(42)
        env.M0 = np.full(env.N_AGENTS, 2.0 * h_val)
        env.reset(delta_u=LS1)
        df_traj = []
        for step in range(PROBE_STEPS):
            actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
            try:
                _, _, done, info = env.step(actions)
            except Exception as e:
                out["step_err"] = f"step {step}: {str(e)[:120]}"
                break
            if info.get("tds_failed"):
                out["tds_failed_step"] = step
                break
            df_traj.append(info["max_freq_deviation_hz"])
            if done:
                break
        env.close()
        if df_traj:
            out["max_df"] = float(np.max(df_traj))
            out["final_df"] = float(df_traj[-1])
            out["paper_ratio"] = float(out["max_df"] / PAPER_NO_CTRL_MAX_DF)
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
    return out


def main() -> int:
    out: dict[str, Any] = {
        "probe": "r14_root3_hscan_v3fixed",
        "version": 1,
        "ls": "LS1 PQ_Bus14 -2.48 sys_pu zero-action 6s",
        "paper_max_df_target": PAPER_NO_CTRL_MAX_DF,
        "h_grid": H_GRID,
    }
    print(f"=== R14 Root #3 H scan on V3 (governor FIXED) ===\n")

    print("Phase A: V2 (no governor, R08 reference baseline)")
    out["v2_results"] = []
    for h in H_GRID:
        r = run_h(AndesMultiVSGEnvV2, h, f"V2_no_gov_h{h}")
        out["v2_results"].append(r)
        print(f"  H={h:6.2f}: max_df={r.get('max_df', 'ERR'):>7} ratio={r.get('paper_ratio', 'ERR'):>5}")

    print("\nPhase B: V3 (governor active after R10 fix)")
    out["v3_results"] = []
    for h in H_GRID:
        r = run_h(AndesMultiVSGEnvV3, h, f"V3_gov_active_h{h}")
        out["v3_results"].append(r)
        print(f"  H={h:6.2f}: max_df={r.get('max_df', 'ERR'):>7} ratio={r.get('paper_ratio', 'ERR'):>5}")

    # Verdict
    v3_h300 = next((r for r in out["v3_results"] if r["h"] == 300.0), None)
    v3_h6_5 = next((r for r in out["v3_results"] if r["h"] == 6.5), None)

    if v3_h300 is None or v3_h6_5 is None or "max_df" not in v3_h300:
        out["verdict"] = "INCONCLUSIVE — H scan failed"
    else:
        h300_ratio = v3_h300["paper_ratio"]
        h6_ratio = v3_h6_5["paper_ratio"]
        if h6_ratio <= 1.2:
            out["verdict"] = (
                f"ROOT3_FAKE — V3 H=6.5 max_df={v3_h6_5['max_df']:.3f} "
                f"({h6_ratio:.2f}× paper). R08 Root #3 是 Root #2 propagation, governor 修了就解决."
            )
        elif h300_ratio <= 1.5:
            out["verdict"] = (
                f"ROOT3_PARTIAL — V3 H=300 max_df={v3_h300['max_df']:.3f} "
                f"({h300_ratio:.2f}× paper). Governor fix 改善但仍不到 paper, 需要 H scaling."
            )
        else:
            out["verdict"] = (
                f"ROOT3_REAL — V3 H=300 max_df={v3_h300['max_df']:.3f} "
                f"({h300_ratio:.2f}× paper) 仍显著高于 paper. 需要 ANDES system audit (line/SBASE/solver)."
            )

    print(f"\n=== Verdict: {out['verdict']} ===")
    p = ROOT / "results" / "research_loop" / "r14_root3_hscan.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
