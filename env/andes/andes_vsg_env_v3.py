"""ANDES Kundur 4-VSG env V3 — V2 + IEEEG1 governor + EXST1 AVR.

R10 fix (2026-05-07): IEEEG1 + EXST1 现在通过 V1 base 的 ``_pre_setup_addons``
钩子在 ``ss.setup()`` 之前添加 (一次性 build), 而**不是** R03/R04 旧实现的
"super().build → ss.setup → add → ss.setup() (FAIL, 吞 except)".

Background — old wiring failure (R10 forensic verdict):
  V2a (V2 env, no gov, H=10) max_df = 0.815 Hz
  V2b (R03/R04 V3 env, gov "on", H=10) max_df = 0.815 Hz  ← 完全相同
  Reason: ANDES 不允许 `add()` after `setup()`. 旧 V3 try/except 吞 fatal,
  IEEEG1 introspection 后只有 NumParam (0 Algeb/State) → 模型在 DAE 死.

This V3 fix:
  - 用 base ``_pre_setup_addons(ss)`` hook, IEEEG1+EXST1 在 ss.setup() 之前 add.
  - 单次 setup, 不重 setup.
  - 验证: ``introspect_model(ss, "IEEEG1")`` 应返回 > 0 Algeb/State 字段.
  - R10 forensic probe: ``scripts/research_loop/r10_governor_wiring_forensic.py``.

V1/V2 ckpts NOT compatible (action range, obs encoding identical but env physics
different — frequency response will differ, agents trained on V2 may diverge).
Fresh training required for any V3 SAC run.
"""
from __future__ import annotations

from env.andes.andes_vsg_env_v2 import AndesMultiVSGEnvV2


class AndesMultiVSGEnvV3(AndesMultiVSGEnvV2):
    """V3 = V2 + IEEEG1 governor + EXST1 AVR on every GENROU.

    Governor + AVR are added via ``_pre_setup_addons`` hook (single ss.setup),
    so they are integrated into the DAE solver (R10 fix, 2026-05-07).
    """

    def _pre_setup_addons(self, ss):
        """Add IEEEG1 governor + EXST1 AVR to every GENROU BEFORE ss.setup().

        GENROU is loaded from ``kundur/kundur_full.xlsx`` at ``andes.load``
        (setup=False), so ``ss.GENROU.idx.v`` is already populated from the
        xlsx data table — usable here even before ss.setup().
        """
        # Defer to parent first so V4+ can chain via super() if added later.
        super()._pre_setup_addons(ss)
        # Defensive: pre-setup we expect xlsx-loaded GENROU.idx.v to be
        # populated. If ANDES API changes future-proofed silently, this
        # assertion surfaces it loudly instead of degrading to DAE-inactive.
        assert len(ss.GENROU.idx.v) > 0, (
            "GENROU idx not populated pre-setup; ANDES `andes.load(setup=False)` "
            "API likely changed. See probes/andes_common/utils.py::introspect_model."
        )
        for syn_idx in ss.GENROU.idx.v:
            ss.IEEEG1.add(idx=f"GOV_{syn_idx}", syn=syn_idx)
            ss.EXST1.add(idx=f"AVR_{syn_idx}", syn=syn_idx)

    @classmethod
    def deviation_summary(cls) -> dict:
        base = super().deviation_summary()
        base.update({
            "version": "v3",
            "governor": "IEEEG1 on all GENROU (DAE-active, R10 fix 2026-05-07)",
            "avr":      "EXST1 on all GENROU (DAE-active, R10 fix 2026-05-07)",
            "rationale": (
                "V2 GENCLS-only 无 governor, freq nadir 物理底大. V3 加 IEEEG1+EXST1 "
                "靠近 Kundur [49] 经典. R10 forensic 修了旧 setup-after-setup bug; "
                "现在 governor 在 DAE 里实际激活 (>0 Algeb/State)."
            ),
        })
        return base
