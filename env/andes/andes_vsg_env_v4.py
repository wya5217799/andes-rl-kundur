"""ANDES Kundur 4-VSG env V4 — paper-faithful baseline (2026-05-07 ANDES fixes).

V4 consolidates 4 fixes found by R10-R16 forensic audits:

1. **Governor + AVR DAE-active** (inherits V3 fix via _pre_setup_addons hook).
   IEEEG1 + EXST1 added BEFORE ss.setup() so ANDES integrates them into DAE.
   R10 verdict: 0 → 7 Algeb/State on IEEEG1, governor effect visible.

2. **G4 inertia preserved** (V1 default change, ZERO_G4_INERTIA=False).
   R15 verdict: G4 paper-restoration drops max_df 26% (0.514 → 0.380 at H=6.5).

3. **VSG_M0 = 200 (H₀ = 100s)** — paper Eq.12 box [10, 300] middle.
   R14 + 30s trace (2026-05-07): only at H ≥ 100 does settled_df ≈ paper 0.13.
   Default V2 H₀=15s gives settled_df 0.077 (0.59× paper, too low) and large
   transient overshoot. Paper Q-D undocumented but Eq.12 box [10, 300] is
   strong evidence H₀ is mid-box (paper 未给具体值, see fact doc Q-D).

4. **D₀ paper-faithful uniform** (V2 [20,16,4,8] hetero is V2 sweep finding,
   not paper convention). Paper Q-D 未给 D₀, 但 Eq.12 box [10, 300] 同 H₀,
   middle = 100. 这里默认 100, 跟 H₀ 同量级.

V4 vs V2/V3:
  - V2 ckpts NOT compatible (M0/D0 量级变 6.7×, action range 同).
  - V4 用 V2 hetero D₀ 不可逆 (V2 sweep 是 paper-deviation, 不是 paper-faithful).
  - V4 是 paper-faithful baseline; V2 保留作 hetero-D sweep variant.

Downstream usage:
  scenarios/kundur/train_andes.py 加 ENV_VERSION=v4 选项, 用 V4 重训.

For ANDES forensic / closure context, see
  - quality_reports/handoff/2026-05-07_andes_path_closure.md (老 closure decision, 现在重新打开)
  - quality_reports/research_loop/round_10_verdict.md (R10 governor wiring forensic)
  - quality_reports/research_loop/round_11_13_mvv_verdict.md (R11-R13 method MVVs)
"""
from __future__ import annotations

import numpy as np

from env.andes.andes_vsg_env_v3 import AndesMultiVSGEnvV3


class AndesMultiVSGEnvV4(AndesMultiVSGEnvV3):
    """V4 = V3 (governor active) + paper-faithful G4 + paper-magnitude H₀, D₀."""

    # paper Eq.12 box [10, 300]; middle ≈ 100. R14 30s trace verdict: H=100-300
    # settled_df ≈ paper 0.13 (0.91-1.07×). H=6.5 (V2 default) settled_df 0.077
    # (0.59× paper, too damped, overshoots transiently).
    VSG_M0 = 200.0   # 2H, H₀ = 100s
    VSG_D0 = 100.0   # fallback (V2.reset 用 D0_HETEROGENEOUS 覆盖, 见下)

    # V4 paper-faithful uniform D₀ (V2 hetero [20,16,4,8] 是 paper-deviation sweep
    # finding, 不是 paper baseline). 每 VSG D₀=100 跟 H₀ 同量级, 在 Eq.12 box 中段.
    D0_HETEROGENEOUS = np.array([100.0, 100.0, 100.0, 100.0])

    # Action ranges paper-faithful per Sec.IV-B:
    #   ΔH ∈ [-100, +300] → ΔM = 2 × ΔH ∈ [-200, +600]
    #   ΔD ∈ [-200, +600]
    # V2 had [-12, 40] / [-15, 45] (paper-deviation 17× too narrow, Class A boundary).
    # V4 fixes this; trained policies must be retrained for V4 (V2 ckpts incompatible).
    DM_MIN = -200.0
    DM_MAX = 600.0
    DD_MIN = -200.0
    DD_MAX = 600.0

    # G4 default already paper-faithful via V1 ZERO_G4_INERTIA=False.

    # ─── V4.1 PHI rescale (R18 finding 2026-05-07) ───────────────────────
    # Paper Eq.14 says φ_h = φ_d = 1.0 with paper Eq.13 ΔH/ΔD ranges
    # (V2 implicitly 17× narrower → paper-deviation hidden Class A).
    # V4 expanding to paper Sec.IV-B [-200,+600] without rescale → r_d / r_h
    # quadratic 178× explosion vs r_f physics signal. R18 measured
    # r_d/r_f ratio = 36000:1 at SAC explore → reward divergence inevitable.
    # Rescale: PHI = 1 / 178 = 0.0056 keeps reward SNR equivalent to
    # paper-deviated V2 baseline. This is "paper Eq.14 effective scaling"
    # (paper assumes implicit narrow ΔH/ΔD; V4 expands → must compensate).
    PHI_H = 0.0056   # was 1.0 (paper Eq.14 nominal, see V2 baseline 17× narrow)
    PHI_D = 0.0056   # was 1.0
    # PHI_F (frequency sync) keeps paper Eq.14 = 100 — r_f magnitude is
    # action-range-INDEPENDENT (= mean(Δω - mean(Δω))² ≈ O(0.01)).
    # PHI_ABS (Kundur tight-coupling补丁) leaves base default 50; users can
    # override via --phi-abs CLI for paper-strict (Eq.14 doesn't include it).

    # ─── V4.1 Action-box clamp (s49 H₀=50 forensic 2026-05-07) ──────────
    # Paper Eq.12 box: H ∈ [10, 300] → M ∈ [20, 600], D ∈ [10, 300].
    # base_env clamp is M_MIN_PHYSICAL / D_MIN_PHYSICAL (default 20 / 10).
    # V4 inherits paper Eq.12 lower bounds. Subclasses can override.
    M_MIN_PHYSICAL = 20.0
    D_MIN_PHYSICAL = 10.0

    @classmethod
    def deviation_summary(cls) -> dict:
        base = super().deviation_summary()
        base.update({
            "version": "v4",
            "vsg_m0": cls.VSG_M0,
            "vsg_d0": cls.VSG_D0,
            "g4_inertia": "preserved (paper Kundur 4 SG)",
            "governor": "IEEEG1 DAE-active (R10 fix)",
            "action_range_dm": (cls.DM_MIN, cls.DM_MAX),
            "action_range_dd": (cls.DD_MIN, cls.DD_MAX),
            "rationale": (
                "V4 consolidates R10-R16 forensic fixes: "
                "governor wiring (Root #2), G4 paper-restoration (26% Root #3 share), "
                "H₀=100s (paper Eq.12 box middle, gives settled_df ≈ paper 0.13), "
                "action range paper-faithful per Sec.IV-B (ΔM=[-200,600], ΔD=[-200,600])."
            ),
        })
        return base
