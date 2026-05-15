"""R16 — Root #3 forensic: NEW_LINE_X (Bus 10→14 added line) effect on max_df.

Hypothesis: V1 adds 4 new buses (12, 14, 15, 16) for VSGs, connected to base
Kundur via NEW_LINE (R=0.001-0.002, X=0.10 V1 / X=0.20 V2). LS1 disturbs Bus 14
(NEW bus, not original Kundur load bus), so the freq excursion is LOCAL to the
VSG sub-grid. With long impedance, the VSGs are weakly coupled to original
Kundur sync gens → effective sync inertia at Bus 14 is SMALL (just nearby VSGs)
→ max_df 放大.

Build on R15 (G4 restored to paper Kundur). Sweep NEW_LINE_X:
  X=0.001  (hard-coupled, VSGs effectively AT base buses)
  X=0.01
  X=0.05
  X=0.10   (V1 default)
  X=0.20   (V2 default)
  X=0.30
  X=0.60   (V2 sweep limit, power flow 发散)

V3 governor active, H_FORCED=6.5, LS1 -2.48 sys_pu.

Verdict:
  X=0.001 max_df → 0.13 → strong-couple cure, NEW_LINE 是 Root #3 主因
  X=0.001 max_df > 0.25 → 还有别处残差, 继续 audit (LS1 location, total inertia)
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

from env.andes.andes_vsg_env_v3 import AndesMultiVSGEnvV3  # noqa: E402

LS1 = {"PQ_Bus14": -2.48}
PROBE_STEPS = 30
H_FORCED = 6.5
PAPER_NO_CTRL_MAX_DF = 0.13
LINE_X_GRID = [0.001, 0.01, 0.05, 0.10, 0.20]


class V3_G4Paper(AndesMultiVSGEnvV3):
    """V3 + G4 inertia restored (R15 finding: 26% effect from G4)."""

    def _build_system(self):
        ss = super()._build_system()
        ss.GENROU.set("M", 4, 111.15, attr='v')
        ss.GENROU.set("D", 4, 0.0, attr='v')
        return ss


def run_one(line_x: float) -> dict:
    out: dict[str, Any] = {"line_x": line_x}
    try:
        # Override class-level constant per env instance
        original_x = V3_G4Paper.NEW_LINE_X
        V3_G4Paper.NEW_LINE_X = line_x
        env = V3_G4Paper(random_disturbance=False, comm_fail_prob=0.0)
        env.seed(42)
        env.M0 = np.full(env.N_AGENTS, 2.0 * H_FORCED)
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
        V3_G4Paper.NEW_LINE_X = original_x
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
        "probe": "r16_root3_line_x",
        "version": 1,
        "base": "V3 + G4 paper-restored (per R15)",
        "h_forced": H_FORCED,
        "line_x_grid": LINE_X_GRID,
    }
    print("=== R16 Root #3 NEW_LINE_X forensic ===\n")
    print(f"Base: V3 + G4 restored (paper Kundur 4 SG); LS1 -2.48 sys_pu @ Bus 14")
    print(f"Paper target max_df: {PAPER_NO_CTRL_MAX_DF}\n")

    out["results"] = []
    for x in LINE_X_GRID:
        r = run_one(x)
        out["results"].append(r)
        max_df = r.get("max_df")
        ratio = r.get("paper_ratio")
        print(f"  X={x:5.3f}: max_df={max_df if max_df else 'ERR':>7} ratio={ratio if ratio else 'ERR':>5}")

    # Verdict: best X result
    valid = [r for r in out["results"] if "max_df" in r]
    if valid:
        best = min(valid, key=lambda r: r["max_df"])
        out["best_x"] = best["line_x"]
        out["best_max_df"] = best["max_df"]
        out["best_paper_ratio"] = best["paper_ratio"]
        if best["paper_ratio"] <= 1.3:
            verdict = (
                f"ROOT3_LINE_X — best X={best['line_x']} max_df={best['max_df']:.3f} "
                f"({best['paper_ratio']:.2f}× paper). NEW_LINE_X 是 Root #3 主因."
            )
        elif best["paper_ratio"] <= 2.0:
            verdict = (
                f"ROOT3_PARTIAL_LINE_X — best X={best['line_x']} max_df={best['max_df']:.3f} "
                f"({best['paper_ratio']:.2f}× paper). NEW_LINE_X 显著贡献但还有别处."
            )
        else:
            verdict = (
                f"ROOT3_NOT_LINE_X — best X={best['line_x']} max_df={best['max_df']:.3f} "
                f"({best['paper_ratio']:.2f}× paper) 仍高. NEW_LINE_X 不是 Root #3 主因."
            )
    else:
        verdict = "INCONCLUSIVE — all variants failed"
    out["verdict"] = verdict
    print(f"\n=== Verdict: {verdict} ===")

    p = ROOT / "results" / "research_loop" / "r16_root3_line_x_probe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
