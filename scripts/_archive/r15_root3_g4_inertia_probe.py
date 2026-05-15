"""R15 — Root #3 forensic: does V1's G4 inertia zero-out cause platform 2× residual?

Hypothesis: V1 base (`env/andes/andes_vsg_env.py:163-168`) sets G4 GENROU M=0.1
"to simulate wind farm". This removes ~25% of paper Kundur's sync inertia
(paper has 4 sync gens at H=6.175-6.5s; V1 has only 3). Plus an extra WF2
zero-inertia GENCLS at Bus8. **Effective sync inertia 显著减少 → max_df 放大**.

Probe: monkey-patch V3._build_system to skip the G4 zeroing, compare max_df.

Variant A (V3_default): G4 zeroed (current behavior)
Variant B (V3_g4_paper): G4 preserved at 6.175s/900MVA (paper-faithful)

Both at H_FORCED=6.5 (paper Area1), governor active (R10 fix), LS1 zero-action.

Verdict:
  B max_df ≤ 0.20  → Root #3 主因 = G4 zeroing
  B max_df 0.20-0.35 → G4 是 partial 主因, 还有其他平台残差
  B max_df > 0.35  → G4 zeroing 不是 Root #3, 别处找
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


def run_probe(env, label: str) -> dict:
    out: dict[str, Any] = {"label": label}
    try:
        env.seed(42)
        env.M0 = np.full(env.N_AGENTS, 2.0 * H_FORCED)
        env.reset(delta_u=LS1)
        df_traj = []
        # Snapshot GENROU M (post-setup, post-G4-zero)
        out["genrou_M"] = list(env.ss.GENROU.M.v)
        out["genrou_D"] = list(env.ss.GENROU.D.v)
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
        "probe": "r15_root3_g4_inertia",
        "version": 1,
        "hypothesis": "G4 zero-inertia 是 Root #3 平台 2× 残差的主因",
        "h_forced": H_FORCED,
    }
    print("=== R15 Root #3 G4 inertia forensic ===\n")

    print("Variant A: V3_default (G4 M=0.1, paper Kundur 4-gen → 3-gen)")
    env_a = AndesMultiVSGEnvV3(random_disturbance=False, comm_fail_prob=0.0)
    out["variant_a"] = run_probe(env_a, "V3_g4_zero")
    print(f"  GENROU M : {out['variant_a'].get('genrou_M')}")
    print(f"  max_df   : {out['variant_a'].get('max_df')}")
    print(f"  paper_ratio: {out['variant_a'].get('paper_ratio')}")

    print("\nVariant B: V3 + G4 preserved (paper-faithful 4 sync gens)")

    # Make a subclass that suppresses G4 zeroing
    class V3_G4Paper(AndesMultiVSGEnvV3):
        def _build_system(self):
            # Bypass G4 zeroing by removing the marker BEFORE super() runs the
            # post-setup G4 modifications.
            ss = super()._build_system()
            # super() already zeroed G4. Restore paper Kundur M=111.15, D=0
            # (G4 = 4th GENROU in xlsx, M = 6.175 × 900 / 100 = 55.575 × 2 = 111.15)
            ss.GENROU.set("M", 4, 111.15, attr='v')
            ss.GENROU.set("D", 4, 0.0, attr='v')
            return ss

    env_b = V3_G4Paper(random_disturbance=False, comm_fail_prob=0.0)
    out["variant_b"] = run_probe(env_b, "V3_g4_paper")
    print(f"  GENROU M : {out['variant_b'].get('genrou_M')}")
    print(f"  max_df   : {out['variant_b'].get('max_df')}")
    print(f"  paper_ratio: {out['variant_b'].get('paper_ratio')}")

    a_max = out["variant_a"].get("max_df")
    b_max = out["variant_b"].get("max_df")
    if a_max and b_max:
        improvement = (a_max - b_max) / a_max * 100
        out["g4_inertia_effect_pct"] = float(improvement)
        b_ratio = out["variant_b"].get("paper_ratio", 99)

        if b_ratio <= 1.3:
            verdict = (
                f"ROOT3_G4 — V3+G4paper max_df={b_max:.3f} ({b_ratio:.2f}× paper). "
                f"G4 zeroing 是 Root #3 主因, 修了就到 paper 量级."
            )
        elif b_ratio <= 2.0:
            verdict = (
                f"ROOT3_PARTIAL_G4 — V3+G4paper max_df={b_max:.3f} ({b_ratio:.2f}× paper). "
                f"G4 修了显著改善 ({improvement:.0f}%) 但还有别处残差."
            )
        else:
            verdict = (
                f"ROOT3_NOT_G4 — V3+G4paper max_df={b_max:.3f} ({b_ratio:.2f}× paper) 仍高. "
                f"G4 zeroing 不是 Root #3 主因 ({improvement:.0f}% 改善)."
            )
    else:
        verdict = "INCONCLUSIVE — probe failed"
    out["verdict"] = verdict
    print(f"\n=== Verdict: {verdict} ===")

    p = ROOT / "results" / "research_loop" / "r15_root3_g4_inertia_probe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
